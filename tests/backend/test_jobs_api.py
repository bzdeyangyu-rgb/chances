from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_post_job_sets_default_status_and_next_action(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    payload = {
        "platform": "manual",
        "job_title": "AI 应用工程师",
        "company_name": "示例科技",
        "job_url": "https://example.com/jobs/1",
    }

    created = client.post("/api/jobs", json=payload)
    listing = client.get("/api/jobs")

    assert created.status_code == 200
    assert listing.json()[0]["status"] == "待评估"
    assert listing.json()[0]["next_action"] == "补充岗位信息并完成评估"
