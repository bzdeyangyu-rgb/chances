from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_job_task_can_be_created_listed_and_completed(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)
    created = client.post(
        "/api/jobs",
        json={
            "platform": "manual",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "job_url": "https://example.com/jobs/task",
        },
    ).json()

    task = client.post(
        f"/api/jobs/{created['id']}/tasks",
        json={"title": "明天跟进 HR 回复", "due_date": "2026-06-09"},
    ).json()
    tasks = client.get("/api/tasks")
    done = client.post(f"/api/tasks/{task['id']}/complete")
    detail = client.get(f"/api/jobs/{created['id']}")

    assert tasks.status_code == 200
    assert tasks.json()[0]["title"] == "明天跟进 HR 回复"
    assert done.status_code == 200
    assert done.json()["status"] == "done"
    assert detail.json()["tasks"][0]["status"] == "done"


def test_job_task_for_missing_job_returns_404(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    response = client.post("/api/jobs/999/tasks", json={"title": "跟进"})

    assert response.status_code == 404
