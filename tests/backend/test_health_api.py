from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_health_api_reports_ready_database(tmp_path: Path):
    client = TestClient(create_app(db_path=tmp_path / "jobs.db"))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "chances-api",
        "database": "ready",
    }
