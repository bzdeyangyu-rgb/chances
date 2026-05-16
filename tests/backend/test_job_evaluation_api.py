from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_job_evaluation_can_be_saved_and_loaded(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    created = client.post(
        "/api/jobs",
        json={
            "platform": "manual",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "job_url": "https://example.com/jobs/pm-1",
        },
    ).json()

    saved = client.post(
        f"/api/jobs/{created['id']}/evaluate",
        json={
            "match_score": 82,
            "recommendation": "建议推进",
            "reasoning": "岗位方向与个人目标一致",
            "highlights": "AI产品经验匹配",
            "risks": "缺少行业经验",
        },
    )
    detail = client.get(f"/api/jobs/{created['id']}")

    assert saved.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["evaluation"]["match_score"] == 82
