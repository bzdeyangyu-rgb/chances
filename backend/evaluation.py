from __future__ import annotations

import re
from typing import Any


RUBRIC_VERSION = "v1"


def evaluate_job_against_profile(profile: dict[str, str], job: dict[str, object]) -> dict[str, object]:
    """Evaluate a job with the deterministic v1 rubric."""
    strengths: list[str] = []
    risks: list[str] = []
    missing_information = _missing_job_information(job)

    searchable_text = _normalized(
        " ".join(
            str(job.get(field, "") or "")
            for field in (
                "job_title",
                "company_name",
                "location",
                "salary_raw",
                "industry",
                "financing_stage",
                "company_size",
                "benefits",
                "skills",
                "main_text",
                "work_mode",
            )
        )
    )

    role_score = _score_role_match(profile, job, searchable_text, strengths, risks)
    skill_score = _score_skill_match(profile, searchable_text, strengths, risks)
    city_score = _score_city_and_work_mode(profile, job, searchable_text, strengths, risks)
    salary_score = _score_salary(profile, job, strengths, risks)
    growth_score = _score_industry_and_growth(profile, job, searchable_text, strengths)

    no_go_deduction = _score_no_go_rules(profile, searchable_text, risks)
    missing_deduction = min(15, len(missing_information) * 5)

    raw_score = role_score + skill_score + city_score + salary_score + growth_score
    score = max(0, min(100, round(raw_score - no_go_deduction - missing_deduction)))
    recommendation = _recommendation_for(score)

    return {
        "score": score,
        "recommendation": recommendation,
        "strengths": strengths,
        "risks": risks,
        "missing_information": missing_information,
        "next_step_hint": _next_step_hint(recommendation, risks, missing_information),
        "rubric_version": RUBRIC_VERSION,
    }


def _score_role_match(
    profile: dict[str, str],
    job: dict[str, object],
    searchable_text: str,
    strengths: list[str],
    risks: list[str],
) -> int:
    roles = _split_terms(profile.get("target_roles", ""))
    title = _normalized(job.get("job_title"))
    if not roles:
        risks.append("个人画像缺少目标岗位方向")
        return 0

    for role in roles:
        normalized_role = _normalized(role)
        if normalized_role and normalized_role in title:
            strengths.append(f"岗位方向匹配：{role}")
            return 30

    for role in roles:
        normalized_role = _normalized(role)
        if normalized_role and normalized_role in searchable_text:
            strengths.append(f"岗位内容包含目标方向：{role}")
            return 24

    risks.append("岗位方向与目标岗位不够直接")
    return 0


def _score_skill_match(
    profile: dict[str, str],
    searchable_text: str,
    strengths: list[str],
    risks: list[str],
) -> int:
    skills = _split_terms(profile.get("core_skills", ""))
    if not skills:
        risks.append("个人画像缺少核心技能关键词")
        return 0

    matched = [skill for skill in skills if _normalized(skill) in searchable_text]
    if matched:
        strengths.append("技能关键词匹配：" + "、".join(matched[:5]))
    else:
        risks.append("未命中个人画像中的核心技能关键词")

    return round(25 * len(matched) / len(skills))


def _score_city_and_work_mode(
    profile: dict[str, str],
    job: dict[str, object],
    searchable_text: str,
    strengths: list[str],
    risks: list[str],
) -> int:
    target_cities = _split_terms(profile.get("target_cities", ""))
    location = _normalized(job.get("location"))
    if not target_cities:
        return 0

    for city in target_cities:
        normalized_city = _normalized(city)
        if normalized_city and (normalized_city in location or normalized_city in searchable_text):
            strengths.append(f"城市匹配：{city}")
            return 15

    risks.append("城市或办公地点与目标城市不匹配")
    return 0


def _score_salary(
    profile: dict[str, str],
    job: dict[str, object],
    strengths: list[str],
    risks: list[str],
) -> int:
    salary_min = _first_salary_number(profile.get("salary_min", ""))
    offered_range = _salary_numbers(job.get("salary_raw"))
    if salary_min is None:
        return 0
    if not offered_range:
        return 0

    offered_low = min(offered_range)
    offered_high = max(offered_range)
    if offered_low >= salary_min:
        strengths.append("薪资下限达到目标")
        return 15
    if offered_high >= salary_min:
        strengths.append("薪资上限覆盖目标")
        return 10

    risks.append("薪资区间低于目标下限")
    return 0


def _score_industry_and_growth(
    profile: dict[str, str],
    job: dict[str, object],
    searchable_text: str,
    strengths: list[str],
) -> int:
    score = 0
    preferred_industries = _split_terms(profile.get("preferred_industries", ""))
    matched_industries = [
        industry for industry in preferred_industries if _normalized(industry) in searchable_text
    ]
    if matched_industries:
        strengths.append("行业方向匹配：" + "、".join(matched_industries[:3]))
        score += 6
    elif _normalized(job.get("industry")):
        score += 3

    growth_terms = ("人工智能", "ai", "aigc", "agent", "大模型", "成长", "融资", "a轮", "b轮", "c轮")
    matched_growth = [term for term in growth_terms if _normalized(term) in searchable_text]
    if matched_growth:
        strengths.append("存在成长信号：" + "、".join(matched_growth[:3]))
        score += 4

    return min(10, score)


def _score_no_go_rules(profile: dict[str, str], searchable_text: str, risks: list[str]) -> int:
    matched_rules = [
        rule for rule in _split_terms(profile.get("no_go_rules", "")) if _normalized(rule) in searchable_text
    ]
    for rule in matched_rules:
        risks.append(f"命中禁投规则：{rule}")
    return min(40, len(matched_rules) * 20)


def _missing_job_information(job: dict[str, object]) -> list[str]:
    required_fields = ("job_title", "location", "salary_raw", "main_text")
    return [field for field in required_fields if not str(job.get(field, "") or "").strip()]


def _recommendation_for(score: int) -> str:
    if score >= 85:
        return "强烈推进"
    if score >= 70:
        return "建议推进"
    if score >= 50:
        return "观察补充"
    return "暂不投入"


def _next_step_hint(recommendation: str, risks: list[str], missing_information: list[str]) -> str:
    if any("禁投规则" in risk for risk in risks):
        return "先人工复核禁投风险，确认后再决定是否继续投入。"
    if missing_information:
        return "先补充关键信息：" + "、".join(missing_information)
    if recommendation == "强烈推进":
        return "优先准备简历角度和沟通问题，尽快推进投递。"
    if recommendation == "建议推进":
        return "补齐岗位细节后进入准备包和投递队列。"
    if recommendation == "观察补充":
        return "继续收集岗位信息，重点核对风险项。"
    return "暂不投入时间，除非后续信息显著改善。"


def _split_terms(value: str) -> list[str]:
    return [
        term.strip()
        for term in re.split(r"[、,，;；/|\n]+", value or "")
        if term.strip()
    ]


def _salary_numbers(value: object) -> list[float]:
    text = str(value or "")
    return [float(number) for number in re.findall(r"(\d+(?:\.\d+)?)\s*[kK]", text)]


def _first_salary_number(value: object) -> float | None:
    numbers = _salary_numbers(value)
    if numbers:
        return numbers[0]

    match = re.search(r"(\d+(?:\.\d+)?)", str(value or ""))
    return float(match.group(1)) if match else None


def _normalized(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").lower())
