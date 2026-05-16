from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_update_job_status_creates_action_log(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    created = client.post(
        "/api/jobs",
        json={
            "platform": "manual",
            "job_title": "AI 应用工程师",
            "company_name": "示例科技",
            "job_url": "https://example.com/jobs/1",
        },
    ).json()

    response = client.post(
        f"/api/jobs/{created['id']}/status",
        json={
            "status": "建议推进",
            "next_action": "生成岗位定制简历建议",
        },
    )
    timeline = client.get(f"/api/jobs/{created['id']}/timeline")
    listing = client.get("/api/jobs")

    assert response.status_code == 200
    assert timeline.status_code == 200
    assert timeline.json()[0]["status"] == "建议推进"
    assert timeline.json()[0]["next_action"] == "生成岗位定制简历建议"
    assert listing.json()[0]["status"] == "建议推进"
