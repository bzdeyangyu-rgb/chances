from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_job_material_pack_can_be_saved_and_loaded(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)
    created = client.post(
        "/api/jobs",
        json={
            "platform": "manual",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "job_url": "https://example.com/jobs/materials",
        },
    ).json()

    saved = client.post(
        f"/api/jobs/{created['id']}/materials",
        json={
            "resume_angle": "突出 AIGC 产品规划和跨团队推进",
            "project_highlights": "AI 工作流、UE5 管线、PRD 输出",
            "recruiter_questions": "团队 AI 产品目前在哪个阶段？",
            "interview_prep": "准备一个 AI 工作流落地案例",
            "communication_draft": "您好，我想了解岗位目标。",
            "risk_response": "行业经验不足时用相近项目回应。",
        },
    )
    detail = client.get(f"/api/jobs/{created['id']}")

    assert saved.status_code == 200
    assert detail.json()["materials"]["resume_angle"].startswith("突出")


def test_job_material_pack_can_be_generated_from_profile_job_and_score(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)
    client.post(
        "/api/profile",
        json={
            "target_roles": "AI产品经理",
            "target_cities": "南京",
            "salary_min": "15K",
            "core_skills": "PRD、AIGC、需求分析",
            "project_highlights": "AI工作流；UE5管线；PRD输出",
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
            "main_text": "负责需求分析、产品规划和 AI 落地",
            "job_url": "https://example.com/jobs/generated-materials",
        },
    ).json()
    client.post(f"/api/jobs/{created['id']}/score")

    generated = client.post(f"/api/jobs/{created['id']}/materials/generate")

    assert generated.status_code == 200
    assert "AI工作流" in generated.json()["project_highlights"]
    assert "AI产品经理" in generated.json()["resume_angle"]


def test_saving_materials_for_missing_job_returns_404(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    response = client.post("/api/jobs/999/materials", json={"resume_angle": "test"})

    assert response.status_code == 404
