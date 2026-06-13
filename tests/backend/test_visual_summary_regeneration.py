# -*- coding: utf-8 -*-
from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import create_app
from backend.visual_summary import build_structured_visual_summary


SECTION_LABELS = (
    "岗位摘要",
    "核心职责",
    "任职要求",
    "公司概况",
    "福利与亮点",
    "风险提示",
)


def test_build_structured_visual_summary_has_fixed_sections():
    job = {
        "job_title": "AI产品经理",
        "company_name": "示例科技",
        "location": "南京",
        "salary_raw": "15-25K",
        "main_text": "负责 AI 产品规划、需求落地和跨团队协作。",
        "requirements": "本科以上，3 年经验，熟悉 AI 产品。",
        "benefits": "五险一金、年终奖、弹性办公。",
    }
    screenshots = [
        {"asset_type": "description", "excerpt": "负责 AI 产品规划，推动需求落地"},
        {"asset_type": "company", "text_excerpt": "示例科技，100-499 人，A 轮，专注企业服务"},
        {"asset_type": "benefit", "excerpt": "五险一金 年终奖 弹性办公"},
    ]

    summary = build_structured_visual_summary(job, screenshots)

    for label in SECTION_LABELS:
        assert label in summary
    assert summary.index("岗位摘要") < summary.index("核心职责") < summary.index("任职要求")
    assert "AI产品经理" in summary
    assert "示例科技" in summary
    assert "需求落地" in summary
    assert "五险一金" in summary


def test_build_structured_visual_summary_uses_placeholders_when_inputs_are_sparse():
    summary = build_structured_visual_summary({"job_title": "数据分析师"}, None)

    for label in SECTION_LABELS:
        assert label in summary
    assert "数据分析师" in summary
    assert summary.count("待补充") >= 2
    assert "信息不足" in summary


def test_visual_summary_can_be_regenerated_for_job_with_assets(tmp_path: Path):
    app = create_app(
        workbook_path=tmp_path / "jobs.xlsx",
        db_path=tmp_path / "jobs.db",
        captures_dir=tmp_path / "captures",
    )
    client = TestClient(app)
    imported = client.post(
        "/api/import-visual-page",
        json={
            "url": "https://www.zhipin.com/job_detail/visual-summary.html",
            "title": "AI产品经理 - 示例科技",
            "body_lines": ["AI产品经理", "示例科技", "负责 AI 产品规划", "五险一金"],
            "screenshots": [
                {
                    "asset_type": "description",
                    "data_url": "data:image/png;base64,iVBORw0KGgo=",
                    "mime_type": "image/png",
                    "text_excerpt": "负责 AI 产品规划，推动需求落地",
                }
            ],
        },
    ).json()

    regenerated = client.post(f"/api/jobs/{imported['id']}/visual-summary/regenerate")
    detail = client.get(f"/api/jobs/{imported['id']}")

    assert regenerated.status_code == 200
    assert "岗位摘要" in regenerated.json()["visual_summary"]
    assert detail.json()["job"]["visual_summary_status"] == "ready"
    assert "核心职责" in detail.json()["job"]["visual_summary"]


def test_visual_summary_regeneration_for_missing_job_returns_404(tmp_path: Path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    response = client.post("/api/jobs/999/visual-summary/regenerate")

    assert response.status_code == 404
