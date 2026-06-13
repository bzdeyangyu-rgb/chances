from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_job_can_be_scored_and_score_history_is_saved(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)
    client.post(
        "/api/profile",
        json={
            "target_roles": "AI产品经理",
            "target_cities": "南京",
            "salary_min": "15K",
            "core_skills": "AIGC、PRD、AI工作流",
            "no_go_rules": "纯销售",
        },
    )
    created = client.post(
        "/api/jobs",
        json={
            "platform": "manual",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "location": "南京",
            "salary_raw": "18-25K",
            "skills": "AIGC、PRD",
            "main_text": "负责 AIGC 产品规划、需求分析和 AI 工作流落地。",
            "job_url": "https://example.com/jobs/score",
        },
    ).json()

    scored = client.post(f"/api/jobs/{created['id']}/score")
    history = client.get(f"/api/jobs/{created['id']}/score-history")

    assert scored.status_code == 200
    assert scored.json()["score"] >= 70
    assert scored.json()["rubric_version"] == "v1"
    assert history.status_code == 200
    assert history.json()[0]["score"] == scored.json()["score"]


def test_scoring_missing_job_returns_404(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    response = client.post("/api/jobs/999/score")

    assert response.status_code == 404
