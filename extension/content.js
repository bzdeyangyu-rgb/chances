function normalizeText(value) {
  return (value || "")
    .replace(/[\u200b-\u200d\ufeff]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function bodyLines() {
  return (document.body?.innerText || "")
    .split("\n")
    .map((line) => normalizeText(line))
    .filter(Boolean);
}

function detectPlatform(hostname = window.location.hostname) {
  if (hostname.includes("zhipin.com")) return "boss";
  if (hostname.includes("liepin.com")) return "liepin";
  if (hostname.includes("lagou.com")) return "lagou";
  if (hostname.includes("zhaopin.com")) return "zhaopin";
  return "";
}

function firstElement(selectors) {
  for (const selector of selectors) {
    const node = document.querySelector(selector);
    if (node) return node;
  }
  return null;
}

function textFromSelectors(selectors) {
  for (const selector of selectors) {
    const node = document.querySelector(selector);
    const text = normalizeText(node?.textContent || "");
    if (text) {
      return text;
    }
  }
  return "";
}

function collectTexts(selectors) {
  const values = [];
  for (const selector of selectors) {
    for (const node of document.querySelectorAll(selector)) {
      const text = normalizeText(node.textContent || "");
      if (text && !values.includes(text)) {
        values.push(text);
      }
    }
  }
  return values;
}

function joinTexts(values, separator = "、") {
  return values.filter(Boolean).join(separator);
}

function lineValueAfterPrefix(lines, prefix) {
  const line = lines.find((item) => item.startsWith(prefix));
  if (!line) {
    return "";
  }
  return normalizeText(line.includes("：") ? line.split("：", 2)[1] : line.slice(prefix.length));
}

function isVerificationPage() {
  const title = normalizeText(document.title);
  const text = normalizeText(document.body?.innerText || "").slice(0, 600);
  const url = window.location.href;

  return (
    url.includes("security-check") ||
    title === "滑动验证页面" ||
    title === "访问验证" ||
    title === "Security Verification" ||
    text.includes("滑动滑块进行验证") ||
    text.includes("请按住滑块，拖动到最右边") ||
    text.includes("验证失败，点击框体重试") ||
    text.includes("访问验证") ||
    text.includes("正在验证连接安全性") ||
    text.includes("Protected by Tencent Cloud EdgeOne")
  );
}

function baseJob(platform = detectPlatform()) {
  return {
    platform,
    job_title: "",
    company_name: "",
    salary_raw: "",
    location: "",
    education: "",
    experience: "",
    financing_stage: "",
    company_size: "",
    industry: "",
    benefits: "",
    published_at: "",
    job_url: window.location.href,
    skills: ""
  };
}

function parseSummaryFields(summary) {
  const tokens = normalizeText(summary)
    .split(/[|/·\s]+/)
    .map((item) => normalizeText(item))
    .filter(Boolean);

  const result = {
    location: "",
    experience: "",
    education: "",
    published_at: ""
  };

  const experienceIndex = tokens.findIndex((item) => /(\d+[-~]\d+年|\d+年(?:以上)?|经验不限|应届)/.test(item));
  const educationIndex = tokens.findIndex((item) => /(本科及以上|本科|大专|硕士|博士|学历不限)/.test(item));
  const publishedIndex = tokens.findIndex((item) => /(\d{1,2}月\d{1,2}日更新|更新于 ?\d{1,2}月\d{1,2}日|\d{1,2}月\d{1,2}日)/.test(item));

  if (experienceIndex >= 0) {
    result.experience = tokens[experienceIndex];
    result.location = tokens.slice(0, experienceIndex).join(" ");
  }
  if (educationIndex >= 0) {
    result.education = tokens[educationIndex];
  }
  if (publishedIndex >= 0) {
    result.published_at = tokens[publishedIndex];
  }

  return result;
}

function parseBoss() {
  const job = baseJob("boss");
  const lines = bodyLines();

  job.job_title = textFromSelectors([
    ".job-name",
    ".name",
    ".info-primary h1",
    "h1"
  ]);
  job.salary_raw = textFromSelectors([
    ".salary",
    ".job-salary",
    ".info-primary .salary"
  ]);
  job.company_name = textFromSelectors([
    ".company-name",
    ".brand-name",
    ".company-info .name",
    ".job-company .name"
  ]);

  const summary =
    textFromSelectors([
      ".job-area-wrapper",
      ".info-primary p",
      ".job-primary p"
    ]) || lines.find((line) => /(本科|大专|硕士|博士|学历不限)/.test(line) && /(\d+[-~]\d+年|\d+年|经验不限)/.test(line)) || "";

  Object.assign(job, parseSummaryFields(summary));

  const companyTags = collectTexts([
    ".company-tag-list li",
    ".job-detail-company .company-tag-list li",
    ".company-tab .company-info-tag li"
  ]);
  job.financing_stage = companyTags[0] || "";
  job.company_size = companyTags[1] || "";
  job.industry = companyTags[2] || "";
  job.benefits = joinTexts(collectTexts([
    ".job-card-footer .tag-list li",
    ".welfare-tab-box span",
    ".job-benefits li"
  ]));
  job.skills = collectTexts([
    ".job-tags span",
    ".job-keyword span",
    ".tag-container span"
  ]).join(", ");
  job.published_at =
    textFromSelectors([
      ".job-author span",
      ".job-banner .job-author span"
    ]) || job.published_at;

  return job;
}

function parseLiepin() {
  const job = baseJob("liepin");
  const lines = bodyLines();

  job.job_title = textFromSelectors([
    ".job-title",
    ".name.ellipsis-2",
    ".name",
    "h1"
  ]);
  job.salary_raw = textFromSelectors([
    ".salary",
    ".title-info .salary"
  ]);

  const companyInfoIndex = lines.indexOf("公司信息");
  if (companyInfoIndex >= 0 && lines[companyInfoIndex + 1]) {
    job.company_name = lines[companyInfoIndex + 1];
  } else {
    const recruiterLine = lines.find((line) => line.includes("·") && line.includes("公司"));
    job.company_name = recruiterLine ? normalizeText(recruiterLine.split("·").pop()) : "";
  }

  const summary = lines.find((line) => /(本科|大专|硕士|博士|学历不限)/.test(line) && /(\d+[-~]\d+年|\d+年|经验不限|应届)/.test(line)) || "";
  Object.assign(job, parseSummaryFields(summary));

  job.industry = lineValueAfterPrefix(lines, "企业行业：");
  job.financing_stage = lineValueAfterPrefix(lines, "融资阶段：");
  job.company_size = lineValueAfterPrefix(lines, "人数规模：");
  job.benefits = joinTexts(collectTexts([
    ".job-benefits-box span",
    ".job-benefits span",
    ".tag-box span"
  ]));
  job.skills = collectTexts([
    ".job-tags-box span",
    ".tag-list span"
  ]).join(", ");

  return job;
}

function parseLagou() {
  const job = baseJob("lagou");
  const lines = bodyLines();
  const title = normalizeText(document.title);

  job.job_title = textFromSelectors([
    ".position-head-wrap-name",
    ".job-name",
    ".position_name",
    "h1"
  ]);
  job.salary_raw = textFromSelectors([
    ".salary",
    ".job_request .salary",
    ".position-head-wrap-salary"
  ]);

  const titleMatch = title.match(new RegExp(`${job.job_title || ".+?"}招聘-\\d{4}年(.+?)${job.job_title || ".+?"}招聘求职信息`));
  job.company_name = normalizeText(titleMatch?.[1] || "") || textFromSelectors([
    ".company_info a[title]",
    ".company h2",
    ".company-name"
  ]);

  const summary =
    textFromSelectors([
      ".job_request",
      ".position-label",
      ".job-detail__info",
      ".position-head-wrap"
    ]) || lines.find((line) => /(本科|大专|硕士|博士|学历不限)/.test(line) && /(经验|\d+[-~]\d+年|\d+年)/.test(line)) || "";

  const compactMatch = normalizeText(summary).match(
    /^(.*?)(?:经验)?(\d+[-~]\d+年|\d+年|经验不限|应届)(本科及以上|本科|大专|硕士|博士|学历不限)/
  );
  if (compactMatch) {
    job.location = normalizeText(compactMatch[1]);
    job.experience = normalizeText(compactMatch[2]);
    job.education = normalizeText(compactMatch[3]);
  } else {
    Object.assign(job, parseSummaryFields(summary));
  }

  job.industry = textFromSelectors([
    ".industry",
    ".c_feature li:nth-child(1)"
  ]);
  job.company_size = textFromSelectors([
    ".company-size",
    ".c_feature li:nth-child(2)"
  ]);
  job.benefits = joinTexts(collectTexts([
    ".position-label li",
    ".job-advantage p",
    ".job-detail dd.job-advantage span"
  ]));

  return job;
}

function parseZhaopin() {
  const job = baseJob("zhaopin");
  const lines = bodyLines();
  const title = normalizeText(document.title);

  job.job_title = textFromSelectors([
    "[class^='job-title']",
    ".job-header h1",
    "h1"
  ]);

  const topIndex = lines.findIndex((line) => line === job.job_title);
  const tail = topIndex >= 0 ? lines.slice(topIndex + 1, topIndex + 8) : lines;
  job.salary_raw = tail.find((line) => /[0-9].*(万|K|k|薪)/.test(line)) || "";
  job.location = tail.find((line) => /(.+(市|区|县)$)|南京|上海|北京|苏州|杭州|深圳|广州/.test(line)) || "";
  job.experience = tail.find((line) => /(\d+[-~]\d+年|\d+年|经验不限|应届)/.test(line)) || "";
  job.education = tail.find((line) => /(本科|大专|硕士|博士|学历不限)/.test(line)) || "";
  job.published_at = lines.find((line) => /(更新于|发布于|\d{1,2}月\d{1,2}日)/.test(line)) || "";

  const titleMatch = title.match(/_\d{4}年(.+?)招聘-智联招聘$/);
  job.company_name = normalizeText(titleMatch?.[1] || "");
  job.company_size = textFromSelectors([
    "[class*='company-size']",
    ".company-tag span:nth-child(1)"
  ]);
  job.industry = textFromSelectors([
    "[class*='company-industry']",
    ".company-tag span:nth-child(2)"
  ]);
  job.benefits = joinTexts(collectTexts([
    "[class*='welfare-tag'] span",
    ".welfare-list span"
  ]));
  job.skills = collectTexts([
    "[class*='job-require-skill'] span",
    ".job-tags span"
  ]).join(", ");

  return job;
}

function extractJob() {
  const platform = detectPlatform();
  if (!platform) {
    throw new Error("当前页面不在支持的网站范围内。");
  }
  if (isVerificationPage()) {
    throw new Error("当前页面触发了网站验证，请先手动完成验证后再采集。");
  }

  const parser = {
    boss: parseBoss,
    liepin: parseLiepin,
    lagou: parseLagou,
    zhaopin: parseZhaopin
  }[platform];

  const job = parser();
  if (!job.job_title) {
    throw new Error("未提取到岗位名称，请确认当前是岗位详情页。");
  }
  return job;
}

function findCaptureTargets() {
  const platform = detectPlatform();
  const selectorsByPlatform = {
    boss: {
      description: [".job-sec", ".job-detail", ".job-detail-box"],
      company: [".company-info", ".job-detail-company", ".company-tab"]
    },
    liepin: {
      description: [".job-detail-content", ".job-description", ".content-word"],
      company: [".company-info", ".company-other", ".inner-right"]
    },
    lagou: {
      description: [".job-detail", ".job_bt", ".position-content-l"],
      company: [".job_company", ".position-content-r", ".company_info"]
    },
    zhaopin: {
      description: ["[class*='job-detail']", "[class*='job-description']", ".describtion__detail-content"],
      company: ["[class*='company-content']", "[class*='company-box']", ".company-card"]
    }
  };

  const selectors = selectorsByPlatform[platform] || { description: [], company: [] };
  const targets = [{ asset_type: "visible", label: "页面截图" }];

  for (const [assetType, label] of [["description", "职位描述截图"], ["company", "公司信息截图"]]) {
    const node = firstElement(selectors[assetType] || []);
    if (node) {
      targets.push({
        asset_type: assetType,
        label,
        selector_found: true,
        text_preview: normalizeText(node.innerText || node.textContent || "").slice(0, 500)
      });
    }
  }

  return targets;
}

function scrollToCaptureTarget(assetType) {
  const platform = detectPlatform();
  const selectorsByPlatform = {
    boss: {
      description: [".job-sec", ".job-detail", ".job-detail-box"],
      company: [".company-info", ".job-detail-company", ".company-tab"]
    },
    liepin: {
      description: [".job-detail-content", ".job-description", ".content-word"],
      company: [".company-info", ".company-other", ".inner-right"]
    },
    lagou: {
      description: [".job-detail", ".job_bt", ".position-content-l"],
      company: [".job_company", ".position-content-r", ".company_info"]
    },
    zhaopin: {
      description: ["[class*='job-detail']", "[class*='job-description']", ".describtion__detail-content"],
      company: ["[class*='company-content']", "[class*='company-box']", ".company-card"]
    }
  };

  const selectors = selectorsByPlatform[platform] || {};
  const node = firstElement((selectors[assetType] || []));
  if (!node) {
    return false;
  }

  const top = Math.max(0, Math.floor(node.getBoundingClientRect().top + window.scrollY - 24));
  window.scrollTo({ top, behavior: "instant" });
  return true;
}

function restoreScrollPosition(top) {
  window.scrollTo({ top: Math.max(0, Number(top) || 0), behavior: "instant" });
  return true;
}

function buildPageSnapshot() {
  return {
    platform: detectPlatform(),
    url: window.location.href,
    title: document.title,
    body_lines: bodyLines().slice(0, 400),
    scroll_y: window.scrollY,
    capture_targets: findCaptureTargets()
  };
}

function captureCurrentPage() {
  return {
    snapshot: buildPageSnapshot(),
    job: extractJob()
  };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "capture-page") {
    try {
      sendResponse({ ok: true, ...captureCurrentPage() });
    } catch (error) {
      sendResponse({ ok: false, error: error.message || "页面提取失败。" });
    }
    return false;
  }

  if (message?.type === "scroll-to-capture-target") {
    sendResponse({ ok: scrollToCaptureTarget(message.assetType) });
    return false;
  }

  if (message?.type === "restore-scroll-position") {
    sendResponse({ ok: restoreScrollPosition(message.top) });
    return false;
  }

  return false;
});
