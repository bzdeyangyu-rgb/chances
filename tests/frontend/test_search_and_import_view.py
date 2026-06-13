from frontend.app import (
    build_import_candidate_summary,
    build_preset_display_name,
    group_import_candidates,
    run_search_preset,
)


def test_build_import_candidate_summary_marks_duplicates():
    row = {
        "job_title": "AI产品经理",
        "company_name": "示例科技",
        "salary_raw": "15-25K",
        "location": "南京",
        "duplicate_job_id": 12,
    }

    summary = build_import_candidate_summary(row)

    assert "AI产品经理" in summary
    assert "示例科技" in summary
    assert "重复" in summary
    assert "#12" in summary


def test_group_import_candidates_splits_pending_duplicates_and_decided():
    rows = [
        {"id": 1, "decision": "pending", "duplicate_job_id": None},
        {"id": 2, "decision": "pending", "duplicate_job_id": 7},
        {"id": 3, "decision": "accepted", "duplicate_job_id": None},
        {"id": 4, "decision": "rejected", "duplicate_job_id": None},
    ]

    grouped = group_import_candidates(rows)

    assert [row["id"] for row in grouped["pending"]] == [1]
    assert [row["id"] for row in grouped["duplicates"]] == [2]
    assert [row["id"] for row in grouped["accepted"]] == [3]
    assert [row["id"] for row in grouped["rejected"]] == [4]


def test_build_preset_display_name_uses_name_or_query_parts():
    assert build_preset_display_name({"name": "南京 AI 产品经理"}) == "南京 AI 产品经理"
    assert (
        build_preset_display_name(
            {
                "platform": "boss",
                "city": "杭州",
                "query": "Agent 工程师",
                "salary": "20K+",
            }
        )
        == "BOSS · 杭州 · Agent 工程师 · 20K+"
    )


def test_run_search_preset_posts_limit(monkeypatch):
    captured = {}

    def fake_api_post(path: str, payload: dict[str, object]) -> dict[str, object]:
        captured["path"] = path
        captured["payload"] = payload
        return {"created_count": 2}

    monkeypatch.setattr("frontend.app.api_post", fake_api_post)

    result = run_search_preset(7, limit=12)

    assert result == {"created_count": 2}
    assert captured == {
        "path": "/api/search-presets/7/run",
        "payload": {"limit": 12},
    }
