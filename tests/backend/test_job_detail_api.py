from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_job_detail_returns_job_timeline_evaluation_and_profile_match(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    client.post(
        "/api/profile",
        json={
            "target_roles": "AI产品经理、AIGC产品",
            "target_cities": "南京",
            "salary_min": "15K/月",
            "core_skills": "AIGC、需求分析、PRD、UE5",
        },
    )

    created = client.post(
        "/api/jobs",
        json={
            "platform": "manual",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "location": "南京",
            "salary_raw": "15K-25K",
            "main_text": "负责 AIGC 产品规划、需求分析和跨团队推进",
            "job_url": "https://example.com/jobs/ai-1",
        },
    ).json()

    client.post(
        f"/api/jobs/{created['id']}/status",
        json={
            "status": "建议推进",
            "next_action": "生成简历建议",
        },
    )

    detail = client.get(f"/api/jobs/{created['id']}")

    assert detail.status_code == 200
    assert detail.json()["job"]["status"] == "建议推进"
    assert isinstance(detail.json()["timeline"], list)
    assert detail.json()["profile_match"]["recommendation"] in {"建议优先投递", "建议投递"}
    assert detail.json()["profile_match"]["score"] >= 70
