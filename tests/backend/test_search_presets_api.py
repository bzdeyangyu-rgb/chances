from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_search_preset_can_be_saved_listed_and_deleted(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    payload = {
        "name": "南京 AI 产品经理",
        "platform": "boss",
        "city": "南京",
        "query": "AI产品经理",
        "salary": "15K+",
        "filters_json": '{"city_code":"101190100","salary":"405"}',
    }

    created = client.post("/api/search-presets", json=payload)
    listed = client.get("/api/search-presets")

    assert created.status_code == 200
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "南京 AI 产品经理"
    assert listed.json()[0]["is_active"] is True

    deleted = client.delete(f"/api/search-presets/{created.json()['id']}")
    listed_after_delete = client.get("/api/search-presets")

    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert listed_after_delete.json() == []


def test_search_preset_requires_unique_name(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    payload = {
        "name": "南京 AI 产品经理",
        "platform": "boss",
        "city": "南京",
        "query": "AI产品经理",
    }

    first = client.post("/api/search-presets", json=payload)
    duplicate = client.post("/api/search-presets", json=payload)

    assert first.status_code == 200
    assert duplicate.status_code == 409


def test_search_preset_can_run_boss_search_into_review_inbox(tmp_path: Path, monkeypatch):
    calls = []

    def fake_run_boss_search(preset: dict[str, object], limit: int = 20) -> dict[str, object]:
        calls.append((preset, limit))
        return {
            "ok": True,
            "command": "search",
            "data": {
                "jobs": [
                    {
                        "title": "AI产品经理",
                        "company": "示例科技",
                        "salary": "15-25K",
                        "location": "南京",
                        "url": "https://www.zhipin.com/job_detail/run-search.html?ka=search",
                        "description": "负责 AI 产品规划。",
                    }
                ]
            },
        }

    monkeypatch.setattr("backend.server.run_boss_search", fake_run_boss_search)
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)
    preset = client.post(
        "/api/search-presets",
        json={
            "name": "南京 AI 产品经理",
            "platform": "boss",
            "city": "南京",
            "query": "AI产品经理",
        },
    ).json()

    response = client.post(f"/api/search-presets/{preset['id']}/run", json={"limit": 5})
    candidates = client.get("/api/import-review/candidates").json()
    jobs = client.get("/api/jobs").json()

    assert response.status_code == 200
    assert response.json()["created_count"] == 1
    assert candidates[0]["job_title"] == "AI产品经理"
    assert candidates[0]["canonical_url"] == "https://www.zhipin.com/job_detail/run-search.html"
    assert jobs == []
    assert calls[0][0]["query"] == "AI产品经理"
    assert calls[0][1] == 5


def test_search_preset_run_reports_missing_boss_cli(tmp_path: Path, monkeypatch):
    def fake_run_boss_search(preset: dict[str, object], limit: int = 20) -> dict[str, object]:
        raise FileNotFoundError("boss-agent-cli not found")

    monkeypatch.setattr("backend.server.run_boss_search", fake_run_boss_search)
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)
    preset = client.post(
        "/api/search-presets",
        json={
            "name": "南京 AI 产品经理",
            "platform": "boss",
            "city": "南京",
            "query": "AI产品经理",
        },
    ).json()

    response = client.post(f"/api/search-presets/{preset['id']}/run", json={"limit": 5})

    assert response.status_code == 503
    assert response.json()["detail"] == "boss-agent-cli not found"
