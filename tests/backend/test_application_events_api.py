from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_application_event_can_be_added_to_job_detail(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)
    created = client.post(
        "/api/jobs",
        json={
            "platform": "manual",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "job_url": "https://example.com/jobs/application",
        },
    ).json()

    event = client.post(
        f"/api/jobs/{created['id']}/application-events",
        json={
            "event_type": "applied",
            "channel": "BOSS直聘",
            "note": "已手动投递",
        },
    )
    detail = client.get(f"/api/jobs/{created['id']}")

    assert event.status_code == 200
    assert detail.json()["application_events"][0]["event_type"] == "applied"
    assert detail.json()["application_events"][0]["channel"] == "BOSS直聘"


def test_application_event_for_missing_job_returns_404(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    response = client.post(
        "/api/jobs/999/application-events",
        json={"event_type": "applied", "channel": "BOSS直聘"},
    )

    assert response.status_code == 404
