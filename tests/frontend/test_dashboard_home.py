from frontend.app import build_entry_actions, build_home_metrics, build_status_rows


def test_build_home_metrics_returns_core_counts():
    metrics = build_home_metrics(
        [
            {"status": "待评估", "priority": "普通", "next_action": "补充岗位信息"},
            {"status": "建议推进", "priority": "高", "next_action": "生成简历"},
            {"status": "已投递", "priority": "普通", "next_action": ""},
        ]
    )

    assert metrics["total_jobs"] == 3
    assert metrics["todo_jobs"] == 2
    assert metrics["high_priority_jobs"] == 1
    assert metrics["applied_jobs"] == 1


def test_build_status_rows_orders_statuses_by_count_descending():
    rows = build_status_rows({"待评估": 3, "建议推进": 5, "已投递": 1})

    assert rows[0] == {"状态": "建议推进", "数量": 5}
    assert rows[1] == {"状态": "待评估", "数量": 3}


def test_build_entry_actions_prioritizes_profile_and_evaluation_work():
    profile = {"target_roles": "", "target_cities": "南京", "salary_min": "15K/月"}
    metrics = {"total_jobs": 6, "todo_jobs": 4, "high_priority_jobs": 0, "applied_jobs": 1}

    cards = build_entry_actions(metrics, profile)

    assert cards[0]["title"] == "先完善个人画像"
    assert cards[1]["title"] == "优先处理待评估岗位"
    assert cards[2]["target_page"] == "岗位池"
