from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_bulk_status_update_updates_multiple_jobs(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    first = client.post(
        "/api/jobs",
        json={
            "platform": "manual",
            "job_title": "AI产品经理",
            "company_name": "示例科技A",
            "job_url": "https://example.com/jobs/a",
        },
    ).json()
    second = client.post(
        "/api/jobs",
        json={
            "platform": "manual",
            "job_title": "AI应用工程师",
            "company_name": "示例科技B",
            "job_url": "https://example.com/jobs/b",
        },
    ).json()

    response = client.post(
        "/api/jobs/bulk-status",
        json={
            "job_ids": [first["id"], second["id"]],
            "status": "建议推进",
            "next_action": "批量生成简历建议",
            "note": "本轮统一推进",
        },
    )
    jobs = client.get("/api/jobs").json()

    assert response.status_code == 200
    assert response.json()["updated_count"] == 2
    assert all(job["status"] == "建议推进" for job in jobs)
