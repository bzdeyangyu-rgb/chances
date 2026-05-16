from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app


def test_profile_api_returns_seeded_profile_when_empty(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    fetched = client.get("/api/profile")

    assert fetched.status_code == 200
    assert fetched.json()["target_roles"] == "AI产品经理、AI应用工程师、AIGC产品/工作流相关岗位"
    assert fetched.json()["target_cities"] == "南京"
    assert fetched.json()["salary_min"] == "15K/月，优秀前景岗位可接受 10K 起步"
    assert "UE5" in fetched.json()["core_skills"]
    assert "3DGS" in fetched.json()["project_highlights"]


def test_profile_api_supports_get_and_post(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    payload = {
        "target_roles": "AI产品经理, AI应用工程师",
        "target_cities": "南京, 上海",
        "salary_min": "25k",
    }

    created = client.post("/api/profile", json=payload)
    fetched = client.get("/api/profile")

    assert created.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["target_roles"] == "AI产品经理, AI应用工程师"


def test_import_resume_updates_profile_and_returns_keywords(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    response = client.post(
        "/api/profile/import-resume",
        json={"resume_path": "C:/Users/39859/Downloads/倪展鹏-AI产品经理.pdf"},
    )

    assert response.status_code == 200
    assert response.json()["profile"]["target_roles"] == "AI产品经理"
    assert response.json()["profile"]["target_cities"] == "南京"
    assert response.json()["profile"]["salary_ideal"] == "15-22K"
    assert "UE5" in response.json()["profile"]["core_skills"]
    assert "AIGC" in response.json()["keywords"]
