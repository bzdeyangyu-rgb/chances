# -*- coding: utf-8 -*-
from __future__ import annotations

import re


SECTION_LABELS = (
    "岗位摘要",
    "核心职责",
    "任职要求",
    "公司概况",
    "福利与亮点",
    "风险提示",
)

RESPONSIBILITY_KEYWORDS = (
    "负责",
    "主导",
    "推动",
    "推进",
    "落地",
    "搭建",
    "优化",
    "协同",
    "跟进",
    "分析",
    "策划",
    "设计",
    "维护",
)

REQUIREMENT_KEYWORDS = (
    "要求",
    "需要",
    "本科",
    "学历",
    "经验",
    "熟悉",
    "掌握",
    "具备",
    "能力",
    "优先",
    "了解",
)

COMPANY_KEYWORDS = (
    "公司",
    "团队",
    "规模",
    "人数",
    "融资",
    "轮",
    "成立",
    "行业",
    "业务",
    "专注",
    "办公",
)

BENEFIT_KEYWORDS = (
    "福利",
    "五险",
    "公积金",
    "年终",
    "奖金",
    "补贴",
    "弹性",
    "远程",
    "双休",
    "年假",
    "下午茶",
    "团建",
)


def build_structured_visual_summary(
    job: dict[str, object],
    screenshots: list[dict[str, object]] | None = None,
) -> str:
    job = job or {}
    screenshot_texts = _collect_screenshot_texts(screenshots)

    title = _field(job, "job_title", "title", "position_name") or "待补充岗位名称"
    company = _field(job, "company_name", "company", "employer_name") or "待补充公司名称"
    location = _field(job, "location", "city", "work_city") or "待补充地点"
    salary = _field(job, "salary_raw", "salary", "salary_text") or "待补充薪资"
    experience = _field(job, "experience", "work_years", "years_experience") or "待补充经验要求"
    education = _field(job, "education", "degree", "education_level") or "待补充学历要求"

    responsibility_text = _best_sentences(
        _merge_texts(
            _field(job, "main_text", "job_description", "description", "responsibilities"),
            *[text for text in screenshot_texts if _contains_any(text, RESPONSIBILITY_KEYWORDS)],
        ),
        RESPONSIBILITY_KEYWORDS,
    )
    requirement_text = _best_sentences(
        _merge_texts(
            _field(job, "requirements", "qualifications", "job_requirements", "main_text"),
            *[text for text in screenshot_texts if _contains_any(text, REQUIREMENT_KEYWORDS)],
        ),
        REQUIREMENT_KEYWORDS,
    )
    company_text = _best_sentences(
        _merge_texts(
            _field(
                job,
                "company_description",
                "company_profile",
                "company_intro",
                "industry",
                "company_size",
                "financing_stage",
                "company_stage",
            ),
            *[text for text in screenshot_texts if _contains_any(text, COMPANY_KEYWORDS)],
        ),
        COMPANY_KEYWORDS,
    )
    benefit_text = _best_sentences(
        _merge_texts(
            _field(job, "benefits", "welfare", "perks", "salary_raw", "main_text"),
            *[text for text in screenshot_texts if _contains_any(text, BENEFIT_KEYWORDS)],
        ),
        BENEFIT_KEYWORDS,
    )

    summary = [
        _section(
            "岗位摘要",
            _compose_overview(title, company, location, salary, experience, education),
        ),
        _section("核心职责", _compose_section_body(responsibility_text, "当前截图和岗位正文里还没有清晰拆出的职责，建议继续补充职责截图或岗位正文。")),
        _section("任职要求", _compose_section_body(requirement_text, "当前材料里还没有清晰的任职门槛，建议补充学历、经验和技能要求。")),
        _section("公司概况", _compose_company_profile(company, company_text)),
        _section("福利与亮点", _compose_section_body(benefit_text, "当前未看到明确福利或亮点，建议补充薪资、福利、团队亮点或成长信息。")),
        _section("风险提示", _compose_risk_hint(job, screenshots, responsibility_text, requirement_text, company_text, benefit_text)),
    ]
    return "\n\n".join(summary)


def _compose_overview(
    title: str,
    company: str,
    location: str,
    salary: str,
    experience: str,
    education: str,
) -> str:
    return (
        f"{title}，来自{company}，工作地点{location}，薪资{salary}，"
        f"经验{experience}，学历{education}。"
        "这段摘要只基于岗位字段和截图摘录，适合先快速判断是否匹配。"
    )


def _compose_company_profile(company: str, company_text: str) -> str:
    if company_text:
        return f"{company}。{company_text}。"
    return f"{company}。当前公司信息不足，建议补充公司规模、行业、融资阶段和团队介绍。"


def _compose_section_body(primary_text: str, fallback_text: str) -> str:
    if primary_text:
        return f"{primary_text}。"
    return fallback_text


def _compose_risk_hint(
    job: dict[str, object],
    screenshots: list[dict[str, object]] | None,
    responsibility_text: str,
    requirement_text: str,
    company_text: str,
    benefit_text: str,
) -> str:
    missing_items = []
    if not _field(job, "job_title", "title", "position_name"):
        missing_items.append("岗位名称待补充")
    if not _field(job, "company_name", "company", "employer_name"):
        missing_items.append("公司名称待补充")
    if not _field(job, "salary_raw", "salary", "salary_text"):
        missing_items.append("薪资待补充")
    if not _field(job, "experience", "work_years", "years_experience"):
        missing_items.append("经验要求待补充")
    if not _field(job, "education", "degree", "education_level"):
        missing_items.append("学历要求待补充")
    if not screenshots:
        missing_items.append("缺少截图摘录")
    if not responsibility_text:
        missing_items.append("职责信息偏少")
    if not requirement_text:
        missing_items.append("任职要求偏少")
    if not company_text:
        missing_items.append("公司背景偏少")
    if not benefit_text:
        missing_items.append("福利信息偏少")

    if missing_items:
        return "信息不足，" + "；".join(missing_items[:5]) + "。建议继续核对原始页面与截图。"
    return "当前信息较完整，但仍建议对照原始页面核实职责、要求、福利和公司背景是否一致。"


def _best_sentences(text: str, keywords: tuple[str, ...]) -> str:
    sentences = _sentences(text)
    picked = [sentence for sentence in sentences if _contains_any(sentence, keywords)]
    if not picked:
        picked = sentences[:2]
    return _unique_join(picked[:2])


def _collect_screenshot_texts(screenshots: list[dict[str, object]] | None) -> list[str]:
    if not screenshots:
        return []
    texts = []
    for screenshot in screenshots:
        if not isinstance(screenshot, dict):
            continue
        text = _text(screenshot.get("excerpt")) or _text(screenshot.get("text_excerpt"))
        if text:
            texts.append(text)
    return texts


def _field(job: dict[str, object], *keys: str) -> str:
    for key in keys:
        text = _text(job.get(key))
        if text:
            return text
    return ""


def _merge_texts(*parts: str) -> str:
    return _unique_join([part for part in parts if part])


def _section(label: str, body: str) -> str:
    return f"{label}：{body}"


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _sentences(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[。！？!?；;\n]+", text)
    return [part.strip() for part in parts if part and part.strip()]


def _unique_join(parts: list[str]) -> str:
    seen = set()
    unique_parts = []
    for part in parts:
        cleaned = part.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique_parts.append(cleaned)
    return "；".join(unique_parts)


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
