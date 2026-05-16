# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from backend.browser_import import normalize_text


PROFILE_FIELDS = (
    "target_roles",
    "target_cities",
    "remote_preference",
    "salary_min",
    "salary_ideal",
    "core_skills",
    "project_highlights",
    "no_go_rules",
)

KEYWORD_CANDIDATES = [
    "AI产品经理",
    "AI应用工程师",
    "AIGC",
    "UE5",
    "Maya",
    "3DGS",
    "Codex",
    "Claude Code",
    "PRD",
    "需求分析",
    "产品规划",
    "商业化",
    "LangChain",
    "RAG",
    "BIM",
    "CAD",
    "游戏场景",
]


def extract_resume_text(resume_path: str) -> str:
    path = Path(resume_path).expanduser()
    if not path.exists():
        raise ValueError("简历文件不存在，请检查路径。")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        cleaned = normalize_resume_text(text)
        if not cleaned:
            raise ValueError("这份 PDF 没有可提取文本，请先换成可复制文字的 PDF。")
        return cleaned

    if suffix in {".txt", ".md"}:
        return normalize_resume_text(path.read_text(encoding="utf-8", errors="ignore"))

    raise ValueError("当前只支持导入 PDF、TXT 或 Markdown 简历。")


def normalize_resume_text(text: str) -> str:
    lines = [normalize_text(line) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _search(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    return normalize_text(match.group(1)) if match else ""


def _extract_highlights(text: str) -> list[str]:
    lines = [normalize_text(line) for line in text.splitlines() if normalize_text(line)]
    highlights: list[str] = []
    for line in lines:
        if line.startswith("●") or line.startswith("-") or line.startswith("•"):
            content = normalize_text(line.lstrip("●-• "))
            if len(content) > 12:
                highlights.append(content)
        elif any(token in line for token in ["主导", "负责", "交付", "报告", "路线图", "落地", "提效"]):
            if len(line) > 16:
                highlights.append(line)
        if len(highlights) >= 4:
            break
    return highlights


def extract_keywords_from_text(text: str) -> list[str]:
    found: list[str] = []
    lowered = text.lower()
    for keyword in KEYWORD_CANDIDATES:
        if keyword.lower() in lowered and keyword not in found:
            found.append(keyword)
    return found


def derive_profile_from_resume(text: str, existing: dict[str, str] | None = None) -> tuple[dict[str, str], list[str]]:
    existing = existing or {}
    target_roles = _search(r"求职意向[:：]\s*([^\n|]+)", text) or existing.get("target_roles", "")
    target_cities = _search(r"期望城市[:：]\s*([^\n|]+)", text) or existing.get("target_cities", "")
    salary_ideal = _search(r"期望薪资[:：]\s*([^\n|]+)", text) or existing.get("salary_ideal", "")
    salary_min = existing.get("salary_min", "")
    if salary_ideal and not salary_min:
        salary_min = salary_ideal.split("-")[0].strip()
    remote_preference = existing.get("remote_preference", "")
    if not remote_preference:
        remote_preference = "可接受远程或混合办公，但优先本地合适机会"

    keywords = extract_keywords_from_text(text)
    if not target_roles and keywords:
        role_keywords = [item for item in keywords if "经理" in item or "工程师" in item or "AIGC" in item]
        target_roles = "、".join(role_keywords[:3])

    core_skills = existing.get("core_skills", "")
    if not core_skills:
        core_skills = "、".join(keywords[:8])

    highlights = _extract_highlights(text)
    project_highlights = existing.get("project_highlights", "")
    if not project_highlights:
        project_highlights = "；".join(highlights[:4])

    no_go_rules = existing.get("no_go_rules") or "与 AI 应用/产品方向明显无关、长期缺乏成长空间、低于目标薪资且上升路径不清晰的岗位"

    profile = {
        "target_roles": target_roles,
        "target_cities": target_cities,
        "remote_preference": remote_preference,
        "salary_min": salary_min,
        "salary_ideal": salary_ideal,
        "core_skills": core_skills,
        "project_highlights": project_highlights,
        "no_go_rules": no_go_rules,
    }
    return profile, keywords


def extract_profile_keywords(profile: dict[str, str]) -> list[str]:
    source_text = " ".join(
        normalize_text(profile.get(field, "")) for field in ("target_roles", "core_skills", "project_highlights")
    )
    keywords = extract_keywords_from_text(source_text)

    manual_tokens = re.split(r"[、，,；;/\s]+", source_text)
    for token in manual_tokens:
        cleaned = normalize_text(token)
        if 2 <= len(cleaned) <= 20 and cleaned not in keywords:
            if any(marker in cleaned for marker in ["AI", "UE5", "AIGC", "PRD", "需求", "产品", "3DGS", "Maya"]):
                keywords.append(cleaned)
    return keywords[:12]


def _parse_salary_floor(text: str) -> int | None:
    normalized = normalize_text(text)
    if not normalized:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*[Kk万]?", normalized)
    if not match:
        return None
    value = float(match.group(1))
    if "万" in normalized and value < 100:
        return int(value * 10)
    return int(value)


def _parse_job_salary_max(text: str) -> int | None:
    normalized = normalize_text(text)
    if not normalized:
        return None
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*[Kk万]?", normalized)
    if not matches:
        return None
    value = max(float(item) for item in matches)
    if "万" in normalized and value < 100:
        return int(value * 10)
    return int(value)


def build_profile_match(profile: dict[str, str], job: dict[str, Any]) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []
    risks: list[str] = []
    suggestions: list[str] = []

    title = normalize_text(str(job.get("job_title", "")))
    main_text = normalize_text(str(job.get("main_text", "")))
    job_text = f"{title} {main_text}"
    profile_keywords = extract_profile_keywords(profile)

    role_tokens = [token for token in re.split(r"[、，,/\s]+", profile.get("target_roles", "")) if normalize_text(token)]
    if any(token in title for token in role_tokens):
        score += 35
        reasons.append("岗位名称与目标岗位方向直接匹配")
    elif any(token in job_text for token in role_tokens):
        score += 20
        reasons.append("岗位正文与目标岗位方向较为接近")
    else:
        risks.append("岗位名称与当前目标岗位的直接匹配度一般")

    matched_keywords = [keyword for keyword in profile_keywords if keyword and keyword in job_text]
    if matched_keywords:
        score += min(35, 8 * len(matched_keywords))
        reasons.append(f"命中关键词：{'、'.join(matched_keywords[:5])}")
    else:
        risks.append("岗位正文里没有明显命中你的核心关键词")

    target_city = normalize_text(profile.get("target_cities", ""))
    job_city = normalize_text(str(job.get("location", "")))
    if target_city and job_city and target_city in job_city:
        score += 15
        reasons.append("工作城市符合当前偏好")
    elif target_city and job_city:
        risks.append(f"当前目标城市是 {target_city}，岗位城市为 {job_city}")

    salary_min = _parse_salary_floor(profile.get("salary_min", ""))
    job_salary_max = _parse_job_salary_max(str(job.get("salary_raw", "")))
    if salary_min and job_salary_max:
        if job_salary_max >= salary_min:
            score += 15
            reasons.append("岗位薪资上限覆盖你的当前底线")
        else:
            risks.append("岗位薪资上限低于你的当前底线")

    score = max(0, min(score, 100))
    if score >= 85:
        recommendation = "建议优先投递"
    elif score >= 65:
        recommendation = "建议投递"
    elif score >= 45:
        recommendation = "可先观察"
    else:
        recommendation = "暂不建议投入"

    if "AI产品经理" in title and "PRD" not in main_text and "需求" in main_text:
        suggestions.append("准备一版强调需求分析、产品规划和跨团队推进的简历表述")
    elif "工程师" in title:
        suggestions.append("补强工程落地、工具链和项目交付方面的亮点表达")
    else:
        suggestions.append("先根据岗位关键词微调项目经历，再决定是否投递")

    return {
        "score": score,
        "recommendation": recommendation,
        "strengths": reasons,
        "risks": risks,
        "suggestions": suggestions,
    }
