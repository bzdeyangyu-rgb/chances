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
