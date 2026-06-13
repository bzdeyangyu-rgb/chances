from frontend.app import (
    build_focus_jobs,
    build_materials_completion,
    build_resume_advice,
    build_score_history_summary,
    get_status_badge_variant,
    group_capture_assets,
    present_capture_assets,
    present_job_rows,
)


def test_build_focus_jobs_prioritizes_high_priority_pending_work():
    rows = [
        {"job_title": "A", "priority": "高", "status": "建议推进", "next_action": "生成简历"},
        {"job_title": "B", "priority": "普通", "status": "待评估", "next_action": "补充信息"},
    ]

    focus = build_focus_jobs(rows)

    assert focus[0]["job_title"] == "A"


def test_present_job_rows_uses_chinese_column_titles():
    rows = [
        {
            "id": 1,
            "company_name": "示例科技",
            "job_title": "AI 产品经理",
            "platform_label": "Boss直聘",
            "salary_raw": "15K-22K",
            "location": "南京",
            "status": "待评估",
            "priority": "普通",
            "next_action": "补充岗位信息并完成评估",
            "updated_at": "2026-04-09 12:00:00",
        }
    ]

    frame = present_job_rows(rows)

    assert "公司名称" in frame.columns
    assert "岗位名称" in frame.columns
    assert "招聘平台" in frame.columns


def test_present_capture_assets_uses_chinese_labels():
    assets = [
        {"asset_type": "visible", "file_path": "C:/captures/1/visible.png"},
        {"asset_type": "company", "file_path": "C:/captures/1/company.png"},
    ]

    rows = present_capture_assets(assets)

    assert rows[0]["label"] == "页面截图"
    assert rows[1]["label"] == "公司信息截图"


def test_get_status_badge_variant_groups_operational_states():
    assert get_status_badge_variant("建议推进") == "progress"
    assert get_status_badge_variant("已拒绝") == "risk"
    assert get_status_badge_variant("待评估") == ""


def test_build_resume_advice_prioritizes_workflow_product_positioning():
    profile = {
        "target_roles": "AI产品经理",
        "core_skills": "Codex / Claude Code、AI工作流、Agent工具、3DGS、UE5",
        "project_highlights": "Codex / Claude Code 辅助排障、脚本和插件开发；主笔 AI 效能与业务拓展报告",
    }
    job = {
        "job_title": "AI产品经理",
        "main_text": "负责企业内部 AI 工具、Agent 工作流和业务流程提效产品设计。",
    }

    advice = build_resume_advice(profile, job, {"score": 82, "suggestions": ["补充岗位关键词"]})

    assert advice["positioning"] == "AI产品经理 / 企业提效 / AI工作流"
    assert any("Codex / Claude Code" in item for item in advice["case_focus"])
    assert any("AI效能" in item for item in advice["case_focus"])
    assert any("Agent" in item for item in advice["rewrite_points"])
    assert "补充岗位关键词" in advice["next_steps"]


def test_build_materials_completion_counts_required_fields():
    result = build_materials_completion(
        {
            "resume_angle": "突出 AI 产品规划",
            "project_highlights": "",
            "recruiter_questions": "团队 AI 产品在哪个阶段？",
        }
    )

    assert result["completed"] == 2
    assert result["total"] == 6
    assert result["percent"] == 33


def test_build_score_history_summary_uses_latest_snapshot():
    summary = build_score_history_summary(
        [
            {"total_score": 62, "created_at": "2026-06-08 10:00:00"},
            {"total_score": 83, "created_at": "2026-06-09 10:00:00"},
        ]
    )

    assert summary["latest_score"] == 83
    assert summary["count"] == 2


def test_group_capture_assets_orders_key_assets():
    assets = [
        {"asset_type": "company", "file_path": "company.png"},
        {"asset_type": "visible", "file_path": "visible.png"},
        {"asset_type": "hero", "file_path": "hero.png"},
    ]

    grouped = group_capture_assets(assets)

    assert [asset["asset_type"] for asset in grouped] == ["hero", "visible", "company"]
