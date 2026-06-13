const API_URL = "http://127.0.0.1:8000/api/import-visual-page";

const captureButton = document.getElementById("capture");
const statusElement = document.getElementById("status");

function setStatus(message, isError = false) {
  statusElement.textContent = message;
  statusElement.style.color = isError ? "#b42318" : "#1f2937";
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatCaptureError(error) {
  const message = String(error?.message || error || "").trim();
  if (
    message.includes("Failed to fetch") ||
    message.includes("NetworkError") ||
    message.includes("ERR_CONNECTION_REFUSED")
  ) {
    return "本地服务未启动。请先双击项目目录中的 Start-Chances.cmd，再重新采集。";
  }
  return message || "采集失败，请刷新岗位页面后重试。";
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) {
    throw new Error("未找到当前标签页。");
  }
  return tab;
}

async function sendTabMessage(tabId, payload) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, payload, (response) => {
      const messageError = chrome.runtime.lastError;
      if (messageError) {
        reject(new Error(messageError.message));
        return;
      }
      resolve(response);
    });
  });
}

async function injectContentScript(tabId) {
  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["content.js"]
  });
}

async function captureVisibleScreenshot(windowId) {
  return new Promise((resolve, reject) => {
    chrome.tabs.captureVisibleTab(windowId, { format: "png" }, (dataUrl) => {
      const messageError = chrome.runtime.lastError;
      if (messageError) {
        reject(new Error(messageError.message));
        return;
      }
      if (!dataUrl) {
        reject(new Error("当前页面截图失败。"));
        return;
      }
      resolve(dataUrl);
    });
  });
}

async function captureActiveTab() {
  const tab = await getActiveTab();

  try {
    const response = await sendTabMessage(tab.id, { type: "capture-page" });
    if (!response || !response.ok) {
      throw new Error(response?.error || "未能从当前页面提取岗位信息。");
    }
    return { tab, capture: response };
  } catch (error) {
    if (!String(error.message || "").includes("Receiving end does not exist")) {
      throw error;
    }

    await injectContentScript(tab.id);
    const response = await sendTabMessage(tab.id, { type: "capture-page" });
    if (!response || !response.ok) {
      throw new Error(response?.error || "未能从当前页面提取岗位信息。");
    }
    return { tab, capture: response };
  }
}

async function collectSegmentScreenshots(tab, capture) {
  const screenshots = [];
  const targets = capture.snapshot.capture_targets || [{ asset_type: "visible", label: "页面截图" }];

  for (const target of targets) {
    if (target.asset_type !== "visible") {
      await sendTabMessage(tab.id, {
        type: "scroll-to-capture-target",
        assetType: target.asset_type
      });
      await delay(250);
    }

    const dataUrl = await captureVisibleScreenshot(tab.windowId);
    screenshots.push({
      asset_type: target.asset_type,
      data_url: dataUrl,
      mime_type: "image/png",
      text_excerpt: target.text_preview || ""
    });
  }

  await sendTabMessage(tab.id, {
    type: "restore-scroll-position",
    top: capture.snapshot.scroll_y || 0
  });

  return screenshots;
}

async function postCapture(capture, screenshots) {
  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      url: capture.snapshot.url,
      title: capture.snapshot.title,
      body_lines: capture.snapshot.body_lines,
      extracted_job: capture.job,
      screenshots
    })
  });

  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_error) {
      detail = await response.text();
    }
    throw new Error(detail || `本地接口返回 ${response.status}`);
  }

  return response.json();
}

captureButton.addEventListener("click", async () => {
  captureButton.disabled = true;
  setStatus("正在读取当前岗位页面…");

  try {
    const { tab, capture } = await captureActiveTab();
    setStatus("正在按模块生成截图…");
    const screenshots = await collectSegmentScreenshots(tab, capture);

    setStatus("截图已完成，正在写入本地岗位库…");
    const result = await postCapture(capture, screenshots);
    const resultMessage = {
      created: "导入成功，截图与岗位信息已写入本地。",
      duplicate: "当前岗位已存在，已补充最新截图。",
      updated: "当前岗位已存在，已按最新页面内容更新。"
    }[result.result] || `接口已返回 ${result.result}`;

    const title = result.job?.job_title || capture.job.job_title;
    const company = result.job?.company_name || capture.job.company_name;
    setStatus(`${resultMessage}\n\n${title}\n${company}`);
  } catch (error) {
    setStatus(formatCaptureError(error), true);
  } finally {
    captureButton.disabled = false;
  }
});
