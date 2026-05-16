from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def build_payload(**overrides):
    payload = {
        "platform": "boss",
        "job_title": "算法工程师",
        "company_name": "示例科技",
        "salary_raw": "25K-45K",
        "location": "南京",
        "education": "本科",
        "experience": "3-5年",
        "financing_stage": "B轮",
        "company_size": "100-499人",
        "industry": "人工智能",
        "benefits": "六险一金",
        "published_at": "2026-03-23",
        "job_url": "https://example.com/jobs/1",
        "skills": "Python, LLM",
        "main_text": "算法工程师 25K-45K 南京 Python LLM",
    }
    payload.update(overrides)
    return payload


def build_page_capture(**overrides):
    payload = {
        "url": "https://www.liepin.com/job/example.shtml",
        "title": "【南京 AI Agent开发工程师招聘】-南京争锋信息科技有限公司南京招聘信息-猎聘",
        "body_lines": [
            "AI Agent开发工程师",
            "14-21k",
            "南京 1-3年 本科 招1人 3月2日更新",
            "公司信息",
            "南京争锋信息科技有限公司",
            "企业行业： 计算机软件",
            "融资阶段： A轮",
            "人数规模： 100-499人",
        ],
        "extracted_job": {
            "platform": "liepin",
            "job_title": "AI Agent开发工程师",
            "company_name": "南京争锋信息科技有限公司",
            "salary_raw": "14-21k",
            "location": "南京",
            "education": "本科",
            "experience": "1-3年",
            "financing_stage": "",
            "company_size": "",
            "industry": "",
            "benefits": "",
            "published_at": "",
            "job_url": "https://www.liepin.com/job/example.shtml",
            "skills": "",
        },
    }
    payload.update(overrides)
    return payload


def test_get_jobs_returns_empty_list_and_initializes_workbook(tmp_path: Path):
    workbook_path = tmp_path / "jobs.xlsx"
    client = TestClient(create_app(workbook_path))

    response = client.get("/api/jobs")

    assert response.status_code == 200
    assert response.json() == []
    assert workbook_path.exists()


def test_post_job_persists_excel_row_and_exposes_it_via_get(tmp_path: Path):
    workbook_path = tmp_path / "jobs.xlsx"
    client = TestClient(create_app(workbook_path))

    created = client.post("/api/jobs", json=build_payload())
    listing = client.get("/api/jobs")

    assert created.status_code == 200
    assert created.json()["result"] == "created"
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["job_title"] == "算法工程师"
    assert listing.json()[0]["platform_label"] == "Boss直聘"
    assert listing.json()[0]["main_text"] == "算法工程师 25K-45K 南京 Python LLM"


def test_post_job_deduplicates_by_job_url_and_updates_changed_fields(tmp_path: Path):
    workbook_path = tmp_path / "jobs.xlsx"
    client = TestClient(create_app(workbook_path))

    first = client.post("/api/jobs", json=build_payload())
    second = client.post("/api/jobs", json=build_payload())
    third = client.post(
        "/api/jobs",
        json=build_payload(salary_raw="30K-50K", benefits="六险一金 年终奖"),
    )
    listing = client.get("/api/jobs")

    assert first.json()["result"] == "created"
    assert second.json()["result"] == "duplicate"
    assert third.json()["result"] == "updated"
    assert len(listing.json()) == 1
    assert listing.json()[0]["salary_raw"] == "30K-50K"
    assert listing.json()[0]["benefits"] == "六险一金 年终奖"


def test_post_job_canonicalizes_tracking_query_before_dedup(tmp_path: Path):
    workbook_path = tmp_path / "jobs.xlsx"
    client = TestClient(create_app(workbook_path))

    first = client.post(
        "/api/jobs",
        json=build_payload(platform="liepin", job_url="https://www.liepin.com/job/1.shtml?pgRef=abc&foo=bar"),
    )
    second = client.post(
        "/api/jobs",
        json=build_payload(platform="liepin", job_url="https://www.liepin.com/job/1.shtml"),
    )
    listing = client.get("/api/jobs")

    assert first.json()["result"] == "created"
    assert second.json()["result"] == "duplicate"
    assert len(listing.json()) == 1
    assert listing.json()[0]["job_url"] == "https://www.liepin.com/job/1.shtml"


def test_post_import_page_uses_extracted_job_and_fallback_fields(tmp_path: Path):
    workbook_path = tmp_path / "jobs.xlsx"
    client = TestClient(create_app(workbook_path))

    imported = client.post("/api/import-page", json=build_page_capture())
    listing = client.get("/api/jobs")

    assert imported.status_code == 200
    assert imported.json()["result"] == "created"
    assert imported.json()["job"]["job_title"] == "AI Agent开发工程师"
    assert imported.json()["job"]["location"] == "南京"
    assert imported.json()["job"]["company_size"] == "100-499人"
    assert "AI Agent开发工程师" in imported.json()["job"]["main_text"]
    assert "公司信息" in imported.json()["job"]["main_text"]
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["company_name"] == "南京争锋信息科技有限公司"
    assert listing.json()[0]["industry"] == "计算机软件"
    assert "AI Agent开发工程师" in listing.json()[0]["main_text"]


def test_post_import_page_rejects_verification_pages(tmp_path: Path):
    workbook_path = tmp_path / "jobs.xlsx"
    client = TestClient(create_app(workbook_path))

    response = client.post(
        "/api/import-page",
        json=build_page_capture(
            url="https://www.lagou.com/wn/jobs/1.html",
            title="滑动验证页面",
            body_lines=["请按住滑块，拖动到最右边"],
            extracted_job=None,
        ),
    )
    listing = client.get("/api/jobs")

    assert response.status_code == 400
    assert "验证" in response.json()["detail"]
    assert listing.json() == []
