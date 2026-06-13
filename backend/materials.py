# -*- coding: utf-8 -*-
from __future__ import annotations

import re


REQUIRED_FIELDS = (
    "resume_angle",
    "project_highlights",
    "recruiter_questions",
    "interview_prep",
    "communication_draft",
    "risk_response",
)


def build_preparation_pack(
    profile: dict[str, str],
    job: dict[str, object],
    score: dict[str, object] | None = None,
) -> dict[str, str]:
    """Build a deterministic job preparation pack from local inputs."""
    score = score or {}
    title = _text(job.get("job_title")) or "通用岗位"
    company = _text(job.get("company_name")) or "目标公司"
    job_text = _text(job.get("main_text")) or "岗位信息尚未补充完整"
    core_skills = _text(profile.get("core_skills")) or "可迁移能力、学习能力、跨团队协作"
    strengths = _items(score.get("strengths")) or ["与岗位方向存在可迁移匹配点"]
    risks = _items(score.get("risks"))
    highlights = _project_highlights(profile.get("project_highlights"))

    return {
        "resume_angle": _build_resume_angle(title, company, core_skills, strengths),
        "project_highlights": _build_project_highlights(highlights, title),
        "recruiter_questions": _build_recruiter_questions(title, company),
        "interview_prep": _build_interview_prep(title, job_text, core_skills),
        "communication_draft": _build_communication_draft(title, company, core_skills),
        "risk_response": _build_risk_response(risks),
    }


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _items(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [item for item in (_text(item) for item in value) if item]
    text = _text(value)
    if not text:
        return []
    return [item for item in re.split(r"[；;、,\n]+", text) if item.strip()]


def _project_highlights(value: str | None) -> list[str]:
    highlights = _items(value)
    placeholders = [
        "补充一个最能证明岗位匹配度的项目，写清目标、动作和结果",
        "补充一个体现沟通推进或需求分析能力的案例",
        "补充一个能量化产出或业务价值的成果",
    ]
    return (highlights + placeholders)[:3]


def _build_resume_angle(
    title: str,
    company: str,
    core_skills: str,
    strengths: list[str],
) -> str:
    strength_text = "；".join(strengths[:2])
    return (
        f"投递 {company} 的 {title} 时，简历优先突出“{core_skills}”。"
        f"开头摘要建议围绕 {strength_text} 展开，把经历包装成能直接支撑该岗位交付的证据。"
    )


def _build_project_highlights(highlights: list[str], title: str) -> str:
    lines = []
    for index, highlight in enumerate(highlights[:3], start=1):
        lines.append(f"{index}. {highlight}：对应 {title} 的需求，准备说明背景、个人贡献和结果。")
    return "\n".join(lines)


def _build_recruiter_questions(title: str, company: str) -> str:
    questions = [
        f"1. 想确认一下 {company} 这个 {title} 当前最核心的业务目标是什么？",
        "2. 团队更看重候选人的行业经验、产品方法，还是 AI/工具落地能力？",
        "3. 这个岗位后续面试会重点考察哪些项目案例或作品材料？",
    ]
    return "\n".join(questions)


def _build_interview_prep(title: str, job_text: str, core_skills: str) -> str:
    return "\n".join(
        [
            f"1. 准备 1 个与 {title} 最相关的完整项目复盘，覆盖问题、方案、协作和结果。",
            f"2. 对照岗位描述梳理关键词：{job_text[:80]}。",
            f"3. 把核心技能“{core_skills}”各准备一个可追问的例子。",
            "4. 准备薪资、到岗时间、求职动机和长期方向的简洁回答。",
        ]
    )


def _build_communication_draft(title: str, company: str, core_skills: str) -> str:
    return (
        f"您好，我关注到 {company} 的 {title} 岗位。我的经历主要集中在 {core_skills}，"
        "希望能结合过往项目聊聊这个岗位的实际目标和团队期待。若方便，我可以进一步发送简历和项目说明。"
    )


def _build_risk_response(risks: list[str]) -> str:
    if not risks:
        return "暂无明确风险。建议先补充岗位细节和个人项目证据，再根据招聘方反馈更新回应。"

    lines = []
    for index, risk in enumerate(risks[:3], start=1):
        lines.append(f"{index}. 针对“{risk}”：主动承认边界，并用相近项目、快速学习计划和可验证产出降低顾虑。")
    return "\n".join(lines)
