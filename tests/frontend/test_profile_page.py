from frontend.app import build_profile_snapshot, default_profile_form, extract_profile_keywords


def test_default_profile_form_contains_phase1_fields():
    form = default_profile_form()

    assert "target_roles" in form
    assert "target_cities" in form
    assert "salary_min" in form


def test_extract_profile_keywords_prefers_distinct_skill_terms():
    profile = {
        "target_roles": "AI产品经理、AIGC产品",
        "core_skills": "UE5、AIGC、需求分析、PRD、AI产品规划、UE5",
        "project_highlights": "负责 AIGC 工作流搭建和 AI 产品规划",
    }

    keywords = extract_profile_keywords(profile)

    assert "AIGC" in keywords
    assert "UE5" in keywords
    assert "需求分析" in keywords


def test_build_profile_snapshot_returns_compact_overview_cards():
    snapshot = build_profile_snapshot(
        {
            "target_roles": "AI产品经理、AIGC产品",
            "target_cities": "南京",
            "salary_min": "15K/月",
            "core_skills": "AIGC、工作流设计、需求分析",
        }
    )

    assert snapshot[0] == ("目标方向", "AI产品经理、AIGC产品")
    assert snapshot[1] == ("工作城市", "南京")
    assert snapshot[2] == ("薪资底线", "15K/月")
