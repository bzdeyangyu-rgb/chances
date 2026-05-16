from pathlib import Path

from playwright.sync_api import sync_playwright


SCRIPT = Path("extension/content.js").read_text(encoding="utf-8")


def evaluate_with_content(html: str, expression: str, url: str = "https://www.liepin.com/job/test.shtml"):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route(url, lambda route: route.fulfill(body="<html><body></body></html>", content_type="text/html"))
        page.goto(url)
        page.set_content(html)
        page.evaluate("window.chrome = { runtime: { onMessage: { addListener: () => {} } } };")
        page.add_script_tag(content=SCRIPT)
        result = page.evaluate(expression)
        browser.close()
        return result


def test_capture_current_page_returns_snapshot_and_liepin_job():
    html = """
    <html>
      <head>
        <title>【南京AI Agent开发工程师招聘】南京争锋信息科技有限公司南京招聘信息-猎聘</title>
      </head>
      <body>
        <div class="name-box">
          <span class="name ellipsis-2"><span class="job-title ellipsis-2">AI Agent开发工程师</span></span>
          <span class="salary">14-21k</span>
        </div>
        <div class="job-other">南京  1-3年 本科 招2人 3月3日更新</div>
        <div class="job-benefits-box">
          <span>五险一金</span>
          <span>带薪年假</span>
        </div>
        <div class="job-tags-box">
          <span>Python</span>
          <span>LangChain</span>
          <span>RAG</span>
        </div>
        <div>公司信息</div>
        <div>南京争锋信息科技有限公司</div>
        <div>企业行业：计算机软件</div>
        <div>融资阶段：A轮</div>
        <div>人数规模：100-499人</div>
      </body>
    </html>
    """

    result = evaluate_with_content(html, "captureCurrentPage()")

    assert result["snapshot"]["platform"] == "liepin"
    assert result["snapshot"]["url"] == "https://www.liepin.com/job/test.shtml"
    assert any("AI Agent开发工程师" in line for line in result["snapshot"]["body_lines"])
    assert result["job"]["job_title"] == "AI Agent开发工程师"
    assert result["job"]["company_name"] == "南京争锋信息科技有限公司"
    assert result["job"]["location"] == "南京"
    assert result["job"]["experience"] == "1-3年"
    assert result["job"]["education"] == "本科"
    assert result["job"]["skills"] == "Python, LangChain, RAG"
    assert result["job"]["industry"] == "计算机软件"


def test_is_verification_page_detects_common_security_pages():
    html = """
    <html>
      <head><title>Security Verification</title></head>
      <body>正在验证连接安全性，请勾选下方复选框。</body>
    </html>
    """

    result = evaluate_with_content(html, "isVerificationPage()", url="https://www.zhaopin.com/jobdetail/1.htm")

    assert result is True


def test_is_verification_page_detects_lagou_retry_variant():
    html = """
    <html>
      <head><title>访问验证</title></head>
      <body>验证失败，点击框体重试(error:TL2hp)</body>
    </html>
    """

    result = evaluate_with_content(html, "isVerificationPage()", url="https://www.lagou.com/wn/jobs/12161662.html")

    assert result is True


def test_parse_zhaopin_extracts_summary_fields_from_visible_lines():
    html = """
    <html>
      <head>
        <title>「南京浦口区 AI应用工程师（企业智能化方向）招聘」_2026年南京壹诺吉医疗科技有限公司招聘-智联招聘</title>
      </head>
      <body>
        <h1>AI应用工程师（企业智能化方向）</h1>
        <div>1-1.5万·13薪</div>
        <div>南京浦口区</div>
        <div>1-3年</div>
        <div>本科</div>
        <div>全职</div>
        <div>招2人</div>
        <div>更新于 3月3日</div>
      </body>
    </html>
    """

    result = evaluate_with_content(html, "parseZhaopin()", "https://www.zhaopin.com/jobdetail/test.htm")

    assert result["job_title"] == "AI应用工程师（企业智能化方向）"
    assert result["company_name"] == "南京壹诺吉医疗科技有限公司"
    assert result["salary_raw"] == "1-1.5万·13薪"
    assert result["location"] == "南京浦口区"
    assert result["experience"] == "1-3年"
    assert result["education"] == "本科"


def test_capture_current_page_exposes_segment_targets_for_boss_page():
    html = """
    <html>
      <body style="height: 2600px;">
        <section class="job-banner">
          <h1 class="job-name">AI产品经理</h1>
          <span class="salary">12-24K</span>
        </section>
        <div style="height: 900px;"></div>
        <section class="job-sec">
          <h2>职位描述</h2>
          <div class="job-detail">负责 AI 产品规划与落地</div>
        </section>
        <div style="height: 900px;"></div>
        <aside class="company-info">
          <h2>公司基本信息</h2>
          <div class="company-name">赛宁网安</div>
        </aside>
      </body>
    </html>
    """

    result = evaluate_with_content(html, "captureCurrentPage()", url="https://www.zhipin.com/job_detail/test.html")

    asset_types = [item["asset_type"] for item in result["snapshot"]["capture_targets"]]

    assert asset_types[0] == "visible"
    assert "description" in asset_types
    assert "company" in asset_types
    description_target = next(item for item in result["snapshot"]["capture_targets"] if item["asset_type"] == "description")
    company_target = next(item for item in result["snapshot"]["capture_targets"] if item["asset_type"] == "company")
    assert "负责 AI 产品规划与落地" in description_target["text_preview"]
    assert "赛宁网安" in company_target["text_preview"]
