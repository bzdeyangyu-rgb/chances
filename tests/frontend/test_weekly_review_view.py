from frontend.app import build_application_stage_summary, build_weekly_review_recommendations


def test_build_application_stage_summary_counts_events():
    events = [
        {"event_type": "applied"},
        {"event_type": "replied"},
        {"event_type": "applied"},
        {"event_type": ""},
    ]

    summary = build_application_stage_summary(events)

    assert summary["applied"] == 2
    assert summary["replied"] == 1
    assert summary["未分类"] == 1


def test_build_weekly_review_recommendations_mentions_stalled_jobs_and_tasks():
    payload = {
        "stalled_jobs": [{"job_title": "AI产品经理"}],
        "open_tasks": [{"title": "跟进 HR 回复"}],
        "recommendations": ["优先处理 1 个高优岗位。"],
    }

    result = build_weekly_review_recommendations(payload)

    assert "优先处理 1 个高优岗位。" in result
    assert any("AI产品经理" in item for item in result)
    assert any("跟进 HR 回复" in item for item in result)
