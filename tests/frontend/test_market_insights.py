from frontend.app import build_job_value_signal, build_market_summary


def test_build_market_summary_extracts_salary_city_and_keyword_signals():
    jobs = [
        {
            "job_title": "AI产品经理",
            "salary_raw": "18-25K",
            "location": "南京",
            "main_text": "负责 AI 工作流、Agent 工具和 PRD 输出。",
        },
        {
            "job_title": "AI数字化产品经理",
            "salary_raw": "25-40K",
            "location": "南京",
            "main_text": "负责企业提效、AIGC 应用和流程自动化。",
        },
        {
            "job_title": "算法工程师",
            "salary_raw": "30K-50K",
            "location": "上海",
            "main_text": "负责算法模型训练。",
        },
    ]

    summary = build_market_summary(jobs)

    assert summary["salary_sample_count"] == 3
    assert summary["salary_floor"] == 18
    assert summary["salary_ceiling"] == 50
    assert summary["salary_average_mid"] == 31
    assert summary["city_counts"]["南京"] == 2
    assert summary["top_keywords"][0]["keyword"] in {"AI工作流", "Agent", "AIGC", "企业提效"}


def test_build_job_value_signal_combines_match_salary_and_market_terms():
    market_summary = {"salary_average_mid": 25}
    job = {
        "job_title": "AI产品经理",
        "salary_raw": "25-40K",
        "location": "南京",
        "main_text": "负责 Agent 工具、AI 工作流和企业提效产品。",
    }

    signal = build_job_value_signal(job, market_summary, {"score": 78, "recommendation": "建议推进"})

    assert signal["value_level"] == "高价值"
    assert signal["value_score"] >= 75
    assert any("匹配分" in item for item in signal["signals"])
    assert any("薪资" in item for item in signal["signals"])
    assert any("AI 工作流" in item for item in signal["signals"])
