from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_jobs_api_supports_pagination_and_status_filter(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    for index in range(25):
        client.post(
            "/api/jobs",
            json={
                "platform": "manual",
                "job_title": f"AI产品经理 {index}",
                "company_name": "示例科技",
                "job_url": f"https://example.com/jobs/{index}",
            },
        )

    response = client.get(
        "/api/jobs",
        params={
            "page": 2,
            "page_size": 10,
            "status": "待评估",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 25
    assert payload["page"] == 2
    assert payload["page_size"] == 10
    assert len(payload["items"]) == 10
    assert {row["status"] for row in payload["items"]} == {"待评估"}


def test_jobs_api_pagination_supports_keyword_priority_platform_and_screenshot_filters(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    first = client.post(
        "/api/jobs",
        json={
            "platform": "boss",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "job_url": "https://example.com/jobs/match",
            "priority": "高",
            "main_text": "负责 AIGC 产品规划",
        },
    ).json()
    client.post(
        "/api/jobs",
        json={
            "platform": "liepin",
            "job_title": "后端工程师",
            "company_name": "普通科技",
            "job_url": "https://example.com/jobs/skip",
            "priority": "普通",
        },
    )
    client.post(
        "/api/import-visual-page",
        json={
            "url": "https://www.zhipin.com/job_detail/visual.html?query=1",
            "title": "AI产品经理 - 示例科技",
            "body_lines": ["AI产品经理", "18-25K", "南京"],
            "screenshots": [
                {
                    "asset_type": "hero",
                    "data_url": "data:image/png;base64,iVBORw0KGgo=",
                    "mime_type": "image/png",
                    "text_excerpt": "AI产品经理 18-25K",
                }
            ],
        },
    )

    response = client.get(
        "/api/jobs",
        params={
            "page": 1,
            "page_size": 5,
            "keyword": "AIGC",
            "priority": "高",
            "platform": "boss",
            "has_screenshots": "false",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == first["id"]
