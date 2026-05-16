import base64
from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


PNG_DATA_URL = (
    "data:image/png;base64,"
    + base64.b64encode(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
            "0000000D49444154789C6360606060000000050001A5F645400000000049454E44AE426082"
        )
    ).decode("ascii")
)


def test_import_visual_page_persists_capture_assets_and_summary(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    response = client.post(
        "/api/import-visual-page",
        json={
            "url": "https://www.zhipin.com/job_detail/example.html",
            "title": "AI产品经理 - 赛宁网安",
            "body_lines": ["AI产品经理", "12-24K", "南京", "本科"],
            "extracted_job": {
                "platform": "boss",
                "job_title": "AI产品经理",
                "company_name": "赛宁网安",
                "salary_raw": "12-24K",
                "location": "南京",
                "education": "本科",
                "experience": "经验不限",
                "job_url": "https://www.zhipin.com/job_detail/example.html",
            },
            "screenshots": [
                {"asset_type": "visible", "data_url": PNG_DATA_URL, "mime_type": "image/png"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["result"] == "created"
    assert response.json()["job"]["capture_mode"] == "visual"
    assert response.json()["job"]["visual_summary_status"] == "ready"
    assert "AI产品经理" in response.json()["job"]["visual_summary"]
    assert len(response.json()["assets"]) == 1
    assert Path(response.json()["assets"][0]["file_path"]).exists()


def test_job_detail_includes_visual_assets(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    created = client.post(
        "/api/import-visual-page",
        json={
            "url": "https://www.zhipin.com/job_detail/example-2.html",
            "title": "AI产品经理 - 赛宁网安",
            "body_lines": ["AI产品经理", "12-24K", "南京"],
            "screenshots": [
                {"asset_type": "visible", "data_url": PNG_DATA_URL},
            ],
        },
    ).json()

    detail = client.get(f"/api/jobs/{created['id']}")

    assert detail.status_code == 200
    assert detail.json()["job"]["capture_mode"] == "visual"
    assert isinstance(detail.json()["assets"], list)
    assert detail.json()["assets"][0]["asset_type"] == "visible"


def test_import_visual_page_supports_multiple_segment_screenshots(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    response = client.post(
        "/api/import-visual-page",
        json={
            "url": "https://www.zhipin.com/job_detail/example-3.html",
            "title": "AI产品经理 - 赛宁网安",
            "body_lines": ["AI产品经理", "12-24K", "南京"],
            "screenshots": [
                {"asset_type": "visible", "data_url": PNG_DATA_URL, "text_excerpt": "AI产品经理 12-24K 南京"},
                {"asset_type": "description", "data_url": PNG_DATA_URL, "text_excerpt": "负责 AI 产品规划、需求分析、推进商业化落地"},
                {"asset_type": "company", "data_url": PNG_DATA_URL, "text_excerpt": "赛宁网安 C轮 100-499人 信息安全"},
            ],
        },
    )

    assert response.status_code == 200
    assert [item["asset_type"] for item in response.json()["assets"]] == ["visible", "description", "company"]
    assert "职位描述" in response.json()["job"]["visual_summary"]
    assert "公司信息" in response.json()["job"]["visual_summary"]
    assert "需求分析" in response.json()["job"]["visual_summary"]
