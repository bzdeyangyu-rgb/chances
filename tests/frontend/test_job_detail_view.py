from frontend.app import build_focus_jobs, present_capture_assets, present_job_rows


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
