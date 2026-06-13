from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_weekly_review_returns_summary_counts(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    client.post(
        "/api/jobs",
        json={
            "platform": "manual",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "job_url": "https://example.com/jobs/review-1",
        },
    )

    response = client.get("/api/reviews/weekly")

    assert response.status_code == 200
    assert "total_jobs" in response.json()


def test_weekly_review_returns_actionable_sections(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)
    created = client.post(
        "/api/jobs",
        json={
            "platform": "manual",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "job_url": "https://example.com/jobs/review-actionable",
            "priority": "高",
        },
    ).json()
    client.post(
        f"/api/jobs/{created['id']}/application-events",
        json={"event_type": "applied", "channel": "BOSS直聘", "note": "已手动投递"},
    )
    client.post(
        f"/api/jobs/{created['id']}/tasks",
        json={"title": "跟进 HR 回复", "due_date": "2026-06-09"},
    )

    response = client.get("/api/reviews/weekly")

    assert response.status_code == 200
    payload = response.json()
    assert "pipeline_counts" in payload
    assert "application_event_counts" in payload
    assert "stalled_jobs" in payload
    assert "open_tasks" in payload
    assert "recommendations" in payload
    assert payload["application_event_counts"]["applied"] == 1
    assert payload["open_tasks"][0]["title"] == "跟进 HR 回复"
    assert payload["recommendations"]
