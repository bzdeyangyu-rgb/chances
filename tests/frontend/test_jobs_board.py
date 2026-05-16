from frontend.app import filter_opportunities


def test_filter_opportunities_supports_status_priority_and_keyword():
    rows = [
        {"job_title": "AI 产品经理", "company_name": "示例科技", "status": "建议推进", "priority": "高"},
        {"job_title": "后端工程师", "company_name": "普通公司", "status": "待评估", "priority": "普通"},
    ]

    result = filter_opportunities(rows, status="建议推进", priority="高", keyword="AI")

    assert len(result) == 1
    assert result[0]["job_title"] == "AI 产品经理"
