# -*- coding: utf-8 -*-
from backend.materials import build_preparation_pack


REQUIRED_FIELDS = {
    "resume_angle",
    "project_highlights",
    "recruiter_questions",
    "interview_prep",
    "communication_draft",
    "risk_response",
}


def test_build_preparation_pack_returns_all_required_sections():
    profile = {
        "project_highlights": "AI工作流；UE5管线；PRD输出",
        "core_skills": "PRD、AIGC、需求分析",
    }
    job = {
        "job_title": "AI产品经理",
        "company_name": "示例科技",
        "main_text": "负责需求分析、产品规划和AI落地",
    }
    score = {"risks": ["缺少医疗行业经验"], "strengths": ["AI方向匹配"]}

    pack = build_preparation_pack(profile, job, score)

    assert set(pack) == REQUIRED_FIELDS
    assert all(isinstance(value, str) and value.strip() for value in pack.values())


def test_build_preparation_pack_uses_profile_highlights_and_score_risks():
    profile = {
        "project_highlights": "AI工作流；UE5管线；PRD输出",
        "core_skills": "PRD、AIGC、需求分析",
    }
    job = {
        "job_title": "AI产品经理",
        "company_name": "示例科技",
        "main_text": "负责需求分析、产品规划和AI落地",
    }
    score = {"risks": ["缺少医疗行业经验"], "strengths": ["AI方向匹配"]}

    pack = build_preparation_pack(profile, job, score)

    assert "AI工作流" in pack["project_highlights"]
    assert "UE5管线" in pack["project_highlights"]
    assert "医疗行业经验" in pack["risk_response"]
    assert "AI产品经理" in pack["resume_angle"]


def test_build_preparation_pack_returns_useful_placeholders_for_empty_fields():
    pack = build_preparation_pack({}, {}, None)

    assert set(pack) == REQUIRED_FIELDS
    assert "通用岗位" in pack["resume_angle"]
    assert "补充" in pack["project_highlights"]
    assert "确认" in pack["recruiter_questions"]
    assert "准备" in pack["interview_prep"]
    assert "您好" in pack["communication_draft"]
    assert "暂无明确风险" in pack["risk_response"]
