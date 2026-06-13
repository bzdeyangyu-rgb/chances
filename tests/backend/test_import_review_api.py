from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_import_candidates_are_reviewed_before_activation(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    response = client.post(
        "/api/import-review/candidates",
        json={
            "source": "boss_agent",
            "items": [
                {
                    "platform": "boss",
                    "job_title": "AI产品经理",
                    "company_name": "示例科技",
                    "job_url": "https://www.zhipin.com/job_detail/example.html?lid=1",
                }
            ],
        },
    )
    inbox = client.get("/api/import-review/candidates")

    assert response.status_code == 200
    assert response.json()["created_count"] == 1
    assert inbox.json()[0]["decision"] == "pending"
    assert inbox.json()[0]["canonical_url"] == "https://www.zhipin.com/job_detail/example.html"


def test_import_candidate_accept_creates_job_and_marks_decision(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)
    client.post(
        "/api/import-review/candidates",
        json={
            "source": "boss_agent",
            "items": [
                {
                    "platform": "boss",
                    "job_title": "AI产品经理",
                    "company_name": "示例科技",
                    "job_url": "https://www.zhipin.com/job_detail/example.html",
                }
            ],
        },
    )
    candidate_id = client.get("/api/import-review/candidates").json()[0]["id"]

    accepted = client.post(f"/api/import-review/candidates/{candidate_id}/accept")
    listed_jobs = client.get("/api/jobs")
    inbox = client.get("/api/import-review/candidates")

    assert accepted.status_code == 200
    assert accepted.json()["decision"] == "accepted"
    assert accepted.json()["job_id"] == listed_jobs.json()[0]["id"]
    assert inbox.json() == []


def test_import_candidate_reject_marks_decision_without_creating_job(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)
    client.post(
        "/api/import-review/candidates",
        json={
            "source": "manual",
            "items": [
                {
                    "platform": "boss",
                    "job_title": "纯销售",
                    "company_name": "示例科技",
                    "job_url": "https://www.zhipin.com/job_detail/sales.html",
                }
            ],
        },
    )
    candidate_id = client.get("/api/import-review/candidates").json()[0]["id"]

    rejected = client.post(
        f"/api/import-review/candidates/{candidate_id}/reject",
        json={"reason": "命中禁投规则"},
    )
    jobs = client.get("/api/jobs")

    assert rejected.status_code == 200
    assert rejected.json()["decision"] == "rejected"
    assert jobs.json() == []


def test_import_candidate_marks_duplicate_job(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)
    existing = client.post(
        "/api/jobs",
        json={
            "platform": "boss",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "job_url": "https://www.zhipin.com/job_detail/example.html",
        },
    ).json()

    client.post(
        "/api/import-review/candidates",
        json={
            "source": "boss_agent",
            "items": [
                {
                    "platform": "boss",
                    "job_title": "AI产品经理",
                    "company_name": "示例科技",
                    "job_url": "https://www.zhipin.com/job_detail/example.html?securityId=abc",
                }
            ],
        },
    )

    candidate = client.get("/api/import-review/candidates").json()[0]

    assert candidate["duplicate_job_id"] == existing["id"]


def test_boss_agent_envelope_can_be_imported_to_review_inbox(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    response = client.post(
        "/api/import-review/boss-agent-envelope",
        json={
            "ok": True,
            "command": "search",
            "data": {
                "jobs": [
                    {
                        "title": "AI产品经理",
                        "company": "示例科技",
                        "salary": "15-25K",
                        "location": "南京",
                        "url": "https://www.zhipin.com/job_detail/boss-agent.html?ka=search",
                        "description": "负责 AI 产品规划",
                    }
                ]
            },
        },
    )
    candidate = client.get("/api/import-review/candidates").json()[0]

    assert response.status_code == 200
    assert response.json()["created_count"] == 1
    assert candidate["source"] == "boss_agent"
    assert candidate["job_title"] == "AI产品经理"
    assert candidate["canonical_url"] == "https://www.zhipin.com/job_detail/boss-agent.html"
