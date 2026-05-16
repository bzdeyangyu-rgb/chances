import json

import pytest

from backend.browser_import import (
    BOSS_DETAIL_FIXTURE,
    is_verification_page,
    parse_boss_detail_json,
    parse_lagou_visible_lines,
    parse_liepin_visible_lines,
    parse_zhaopin_visible_lines,
)


def test_parse_boss_detail_json_extracts_core_fields():
    payload = parse_boss_detail_json(BOSS_DETAIL_FIXTURE)

    assert payload["platform"] == "boss"
    assert payload["job_title"] == "AI应用工程师"
    assert payload["company_name"] == "南京示例科技有限公司"
    assert payload["salary_raw"] == "20-35K·14薪"
    assert payload["location"] == "南京"
    assert payload["experience"] == "3-5年"
    assert payload["education"] == "本科"
    assert payload["skills"] == "Python, LangChain, RAG"
    assert payload["job_url"] == "https://www.zhipin.com/job_detail/example.html"


@pytest.mark.parametrize(
    ("title", "text", "url"),
    [
        ("滑动验证页面", "请按住滑块，拖动到最右边", "https://www.lagou.com/wn/jobs/1.html"),
        ("访问验证", "验证失败，点击框体重试(error:TL2hp)", "https://www.lagou.com/wn/jobs/1.html"),
        ("Security Verification", "Protected by Tencent Cloud EdgeOne", "https://www.zhaopin.com/jobdetail/1.htm"),
        ("任意标题", "正文", "https://www.zhipin.com/web/common/security-check.html"),
    ],
)
def test_is_verification_page_detects_common_platform_blocks(title, text, url):
    assert is_verification_page(title, text, url) is True


def test_parse_zhaopin_visible_lines_prefers_human_readable_summary():
    lines = [
        "更新于 3月6日",
        "AI应用工程师（企业智能化方向）",
        "1-1.5万·13薪",
        "南京浦口区",
        "1-3年",
        "本科",
        "全职",
        "招1人",
        "智能医疗",
        "人工智能",
    ]

    payload = parse_zhaopin_visible_lines(
        "「南京浦口区 AI应用工程师（企业智能化方向）招聘」_2026年南京壹诺吉医疗科技有限公司招聘-智联招聘",
        lines,
        "https://www.zhaopin.com/jobdetail/example.htm",
    )

    assert payload["platform"] == "zhaopin"
    assert payload["job_title"] == "AI应用工程师（企业智能化方向）"
    assert payload["company_name"] == "南京壹诺吉医疗科技有限公司"
    assert payload["salary_raw"] == "1-1.5万·13薪"
    assert payload["location"] == "南京浦口区"
    assert payload["experience"] == "1-3年"
    assert payload["education"] == "本科"
    assert payload["job_url"] == "https://www.zhaopin.com/jobdetail/example.htm"


def test_parse_liepin_visible_lines_splits_summary_and_company_info_section():
    lines = [
        "AI Agent开发工程师‌‌",
        "14-21k",
        "南京 1-3年 本科 招1人 3月2日更新",
        "五险一金 带薪年假",
        "公司信息",
        "南京争锋信息科技有限公司",
        "企业行业： 计算机软件",
        "融资阶段： A轮",
        "人数规模： 100-499人",
    ]

    payload = parse_liepin_visible_lines(lines, "https://www.liepin.com/job/example.shtml")

    assert payload["platform"] == "liepin"
    assert payload["job_title"] == "AI Agent开发工程师‌‌"
    assert payload["salary_raw"] == "14-21k"
    assert payload["company_name"] == "南京争锋信息科技有限公司"
    assert payload["location"] == "南京"
    assert payload["experience"] == "1-3年"
    assert payload["education"] == "本科"
    assert payload["published_at"] == "3月2日更新"
    assert payload["industry"] == "计算机软件"
    assert payload["financing_stage"] == "A轮"
    assert payload["company_size"] == "100-499人"


def test_parse_lagou_visible_lines_prefers_title_company_and_compact_summary():
    lines = [
        "AI产品经理",
        "12k-20k",
        "南京经验3-5年本科及以上产品经理全职",
    ]

    payload = parse_lagou_visible_lines(
        "AI产品经理招聘-2026年天珑AI产品经理招聘求职信息-AI产品经理岗位职责介绍-拉勾招聘",
        lines,
        "https://www.lagou.com/wn/jobs/example.html",
    )

    assert payload["platform"] == "lagou"
    assert payload["job_title"] == "AI产品经理"
    assert payload["company_name"] == "天珑"
    assert payload["salary_raw"] == "12k-20k"
    assert payload["location"] == "南京"
    assert payload["experience"] == "3-5年"
    assert payload["education"] == "本科及以上"
