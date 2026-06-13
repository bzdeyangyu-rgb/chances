from backend.evaluation import evaluate_job_against_profile


def test_high_match_ai_product_manager_scores_at_least_80_and_recommends_progress():
    profile = {
        "target_roles": "AI产品经理、AIGC产品",
        "target_cities": "南京",
        "salary_min": "15K",
        "core_skills": "AIGC、PRD、AI工作流、需求分析",
        "preferred_industries": "人工智能、企业服务",
        "no_go_rules": "纯销售、电话销售",
    }
    job = {
        "job_title": "AI产品经理",
        "location": "南京",
        "salary_raw": "18-25K",
        "industry": "人工智能",
        "financing_stage": "B轮",
        "company_size": "100-499人",
        "skills": "AIGC, PRD, AI工作流",
        "main_text": "负责 AIGC 产品规划、需求分析、PRD 输出和 AI 工作流落地。",
    }

    result = evaluate_job_against_profile(profile, job)

    assert result["score"] >= 80
    assert result["recommendation"] in {"强烈推进", "建议推进"}
    assert result["rubric_version"] == "v1"
    assert result["strengths"]
    assert result["next_step_hint"]


def test_no_go_rule_significantly_reduces_score_and_reports_risk():
    profile = {
        "target_roles": "AI产品经理",
        "target_cities": "南京",
        "salary_min": "15K",
        "core_skills": "AIGC、PRD、AI工作流",
        "no_go_rules": "纯销售、电话销售",
    }
    job = {
        "job_title": "AI产品经理",
        "location": "南京",
        "salary_raw": "18-25K",
        "skills": "AIGC, PRD",
        "main_text": "岗位以纯销售和电话销售为主，兼顾少量 AI 产品资料整理。",
    }

    result = evaluate_job_against_profile(profile, job)

    assert result["score"] <= 60
    assert any("纯销售" in risk for risk in result["risks"])


def test_missing_key_information_is_reported():
    profile = {
        "target_roles": "AI产品经理",
        "target_cities": "南京",
        "salary_min": "15K",
        "core_skills": "AIGC、PRD",
    }
    job = {
        "job_title": "AI产品经理",
        "main_text": "负责 AI 产品规划。",
    }

    result = evaluate_job_against_profile(profile, job)

    assert "location" in result["missing_information"]
    assert "salary_raw" in result["missing_information"]
