# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import sys
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.data_store import DEFAULT_WORKBOOK
from frontend.labels import (
    APPLICATION_EVENT_LABELS,
    CAPTURE_ASSET_LABELS,
    DEFAULT_PROFILE_FORM,
    PRIORITY_OPTIONS,
    STATUS_OPTIONS,
    STATUS_TEXT,
    TASK_STATUS_LABELS,
    UI_TEXT,
)


API_BASE_URL = os.getenv("CHANCES_API_BASE_URL", "http://127.0.0.1:8000")
TODO_STATUSES = {"待评估", "建议推进", "待准备材料", "待沟通", "待投递"}
FOCUS_STATUS_ORDER = {
    "建议推进": 0,
    "待准备材料": 1,
    "待沟通": 2,
    "待投递": 3,
    "待评估": 4,
}
FOCUS_PRIORITY_ORDER = {"高": 0, "普通": 1, "低": 2}
PLATFORM_DISPLAY = {
    "boss": "BOSS",
    "zhipin": "BOSS",
    "manual": "手动",
    "liepin": "猎聘",
    "lagou": "拉勾",
    "zhaopin": "智联",
}
MARKET_SIGNAL_KEYWORDS = [
    "AI工作流",
    "Agent",
    "AIGC",
    "企业提效",
    "自动化",
    "PRD",
    "需求分析",
    "数字化",
    "大模型",
    "RAG",
    "低代码",
]
JOB_TABLE_COLUMNS = [
    "id",
    "company_name",
    "job_title",
    "platform_label",
    "salary_raw",
    "location",
    "status",
    "priority",
    "next_action",
    "updated_at",
]
JOB_TABLE_LABELS = {
    "id": "编号",
    "company_name": "公司名称",
    "job_title": "岗位名称",
    "platform_label": "招聘平台",
    "salary_raw": "薪资",
    "location": "工作地点",
    "status": "状态",
    "priority": "优先级",
    "next_action": "下一步动作",
    "updated_at": "更新时间",
}
TIMELINE_LABELS = {
    "created_at": "记录时间",
    "status": "状态",
    "next_action": "下一步动作",
    "note": "备注",
}


st.set_page_config(page_title=UI_TEXT["page_title"], layout="wide")


def default_profile_form() -> dict[str, str]:
    return DEFAULT_PROFILE_FORM.copy()


def build_home_metrics(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_jobs": len(rows),
        "todo_jobs": sum(1 for row in rows if row.get("status") in TODO_STATUSES),
        "high_priority_jobs": sum(1 for row in rows if row.get("priority") == "高"),
        "applied_jobs": sum(1 for row in rows if row.get("status") == "已投递"),
    }


def build_status_rows(status_counts: dict[str, int]) -> list[dict[str, Any]]:
    ordered = sorted(status_counts.items(), key=lambda item: (-int(item[1]), str(item[0])))
    return [{"状态": status, "数量": count} for status, count in ordered]


def build_entry_actions(metrics: dict[str, int], profile: dict[str, str]) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []

    if not profile.get("target_roles"):
        actions.append(
            {
                "title": "先完善个人画像",
                "copy": "目标岗位和薪资边界越清楚，后面的匹配建议越靠谱。",
                "target_page": UI_TEXT["nav_profile"],
            }
        )
    else:
        actions.append(
            {
                "title": "复核当前求职方向",
                "copy": "确认画像是否仍然聚焦 AI 应用、AIGC 与产品方向。",
                "target_page": UI_TEXT["nav_profile"],
            }
        )

    if metrics.get("todo_jobs", 0) > 0:
        actions.append(
            {
                "title": "优先处理待评估岗位",
                "copy": f"当前还有 {metrics['todo_jobs']} 个岗位待推进，先把最有价值的机会挑出来。",
                "target_page": UI_TEXT["nav_jobs"],
            }
        )
    else:
        actions.append(
            {
                "title": "补充新的岗位机会",
                "copy": "当前没有待推进岗位，可以继续从扩展导入或手动录入。",
                "target_page": UI_TEXT["nav_jobs"],
            }
        )

    actions.append(
        {
            "title": "打开岗位池",
            "copy": "在岗位池里做筛选、批量更新和详情判断，是日常推进的主工作区。",
            "target_page": UI_TEXT["nav_jobs"],
        }
    )

    return actions[:3]


def build_focus_jobs(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    pending_rows = [row for row in rows if row.get("status") in TODO_STATUSES]
    ordered = sorted(
        pending_rows,
        key=lambda row: (
            FOCUS_PRIORITY_ORDER.get(str(row.get("priority", "")), 9),
            FOCUS_STATUS_ORDER.get(str(row.get("status", "")), 9),
            str(row.get("updated_at", "")),
        ),
    )
    return ordered[:limit]


def build_application_stage_summary(events: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for event in events:
        event_type = str(event.get("event_type") or "未分类").strip() or "未分类"
        summary[event_type] = summary.get(event_type, 0) + 1
    return summary


def build_weekly_review_recommendations(payload: dict[str, Any]) -> list[str]:
    recommendations = [str(item) for item in payload.get("recommendations", []) if str(item).strip()]
    for job in payload.get("stalled_jobs", []) or []:
        title = str(job.get("job_title") or "未命名岗位").strip()
        if title:
            recommendations.append(f"复核停滞岗位：{title}")
    for task in payload.get("open_tasks", []) or []:
        title = str(task.get("title") or "").strip()
        if title:
            recommendations.append(f"处理跟进任务：{title}")
    return recommendations or ["本周暂无明确阻塞，继续保持岗位补充和推进节奏。"]


def build_home_followup_summary(review: dict[str, Any]) -> list[str]:
    summary: list[str] = []
    for task in review.get("open_tasks", []) or []:
        title = str(task.get("title") or "").strip()
        if title:
            summary.append(f"待办：{title}")
    for job in review.get("stalled_jobs", []) or []:
        title = str(job.get("job_title") or "").strip()
        if title:
            summary.append(f"停滞岗位：{title}")
    return summary[:6] or ["当前没有明显逾期任务或停滞岗位。"]


def filter_opportunities(
    rows: list[dict[str, Any]],
    status: str = "",
    priority: str = "",
    keyword: str = "",
) -> list[dict[str, Any]]:
    filtered = list(rows)

    if status:
        filtered = [row for row in filtered if row.get("status") == status]
    if priority:
        filtered = [row for row in filtered if row.get("priority") == priority]
    if keyword:
        token = keyword.strip().lower()
        filtered = [
            row
            for row in filtered
            if token in str(row.get("job_title", "")).lower()
            or token in str(row.get("company_name", "")).lower()
            or token in str(row.get("main_text", "")).lower()
            or token in str(row.get("visual_summary", "")).lower()
        ]

    return filtered


def collect_bulk_job_ids(rows: list[dict[str, Any]]) -> list[int]:
    return [int(row["id"]) for row in rows if row.get("selected")]


def as_frame(rows: list[dict[str, Any]], columns: list[str] | None = None) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if columns:
        for column in columns:
            if column not in frame.columns:
                frame[column] = ""
        frame = frame[columns]
    return frame.fillna("")


def present_application_events(events: list[dict[str, Any]]) -> pd.DataFrame:
    frame = as_frame(events, ["event_at", "event_type", "channel", "note"])
    frame["event_type"] = frame["event_type"].map(
        lambda value: APPLICATION_EVENT_LABELS.get(str(value), str(value) or "未分类")
    )
    return frame.rename(
        columns={
            "event_at": "发生时间",
            "event_type": "事件",
            "channel": "渠道",
            "note": "备注",
        }
    )


def present_open_tasks(tasks: list[dict[str, Any]]) -> pd.DataFrame:
    frame = as_frame(tasks, ["id", "title", "due_date", "status"])
    frame["status"] = frame["status"].map(
        lambda value: TASK_STATUS_LABELS.get(str(value), str(value))
    )
    return frame.rename(
        columns={
            "id": "编号",
            "title": "任务",
            "due_date": "截止日期",
            "status": "状态",
        }
    )


def present_job_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = as_frame(rows, JOB_TABLE_COLUMNS)
    return frame.rename(columns=JOB_TABLE_LABELS)


def present_capture_assets(assets: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "asset_type": str(asset.get("asset_type", "")),
            "label": CAPTURE_ASSET_LABELS.get(str(asset.get("asset_type", "")), "岗位截图"),
            "file_path": str(asset.get("file_path", "")),
        }
        for asset in assets
        if asset.get("file_path")
    ]


def group_capture_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {"hero": 0, "visible": 1, "description": 2, "company": 3, "fullpage": 4}
    return sorted(
        list(assets or []),
        key=lambda asset: (
            order.get(str(asset.get("asset_type") or ""), 99),
            str(asset.get("created_at") or ""),
            str(asset.get("file_path") or ""),
        ),
    )


def build_materials_completion(materials: dict[str, Any] | None) -> dict[str, int]:
    required_fields = [
        "resume_angle",
        "project_highlights",
        "recruiter_questions",
        "interview_prep",
        "communication_draft",
        "risk_response",
    ]
    values = materials or {}
    completed = sum(1 for field in required_fields if str(values.get(field) or "").strip())
    total = len(required_fields)
    percent = int(completed * 100 / total) if total else 0
    return {"completed": completed, "total": total, "percent": percent}


def build_score_history_summary(history: list[dict[str, Any]]) -> dict[str, Any]:
    if not history:
        return {"latest_score": 0, "count": 0, "latest_at": ""}
    latest = sorted(history, key=lambda item: str(item.get("created_at") or ""), reverse=True)[0]
    latest_score = latest.get("score", latest.get("total_score", 0))
    return {
        "latest_score": int(latest_score or 0),
        "count": len(history),
        "latest_at": str(latest.get("created_at") or ""),
    }


def get_status_badge_variant(status: str) -> str:
    if status in {"建议推进", "待准备材料", "待沟通", "待投递", "待约面", "一面", "二面", "三面", "人事面", "终面"}:
        return "progress"
    if status in {"暂缓", "不推荐", "已拒绝", "已放弃", "已归档"}:
        return "risk"
    return ""


def text_contains_any(text: str, tokens: list[str]) -> bool:
    lowered = text.lower()
    return any(token.lower() in lowered for token in tokens)


def build_resume_advice(
    profile: dict[str, str],
    job: dict[str, Any],
    profile_match: dict[str, Any] | None = None,
) -> dict[str, list[str] | str]:
    job_text = " ".join(
        str(job.get(field, "") or "") for field in ("job_title", "main_text", "visual_summary", "industry")
    )
    profile_text = " ".join(
        str(profile.get(field, "") or "") for field in ("target_roles", "core_skills", "project_highlights")
    )
    combined_text = f"{job_text} {profile_text}"

    case_focus = [
        "把 Codex / Claude Code 辅助排障、脚本/插件开发、自动化检查作为第一案例，强调从一线问题到流程固化。",
        "把 AI效能与业务拓展报告作为第二案例，强调调研判断、路线图设计、预算约束和业务落地路径。",
    ]
    if text_contains_any(combined_text, ["3DGS", "UE5", "AI视频", "AIGC"]):
        case_focus.append("用 3DGS + UE5 + AI 视频模型路线作为差异化补充，证明你能把内容生产流程产品化。")

    rewrite_points = [
        "简历开头直接写成 AI 产品经理，主打企业提效、AI 工作流和 Agent 工具，而不是泛泛写跨界转型。",
    ]
    if text_contains_any(job_text, ["agent", "智能体", "工作流", "自动化", "提效", "工具"]):
        rewrite_points.append("项目经历中增加 Agent / 工作流 / 自动化检查等岗位关键词，并说明它们解决了什么业务流程问题。")
    if text_contains_any(job_text, ["产品", "需求", "规划", "路线图", "商业化"]):
        rewrite_points.append("把 B+C 案例改写成产品语言：用户/业务痛点、方案设计、推进路径、验收方式和结果。")
    if text_contains_any(job_text, ["工程师", "开发", "api", "python", "rag"]):
        rewrite_points.append("保留工程理解作为加分项，但要补充代码、脚本、插件或自动化工具的可证明产出。")

    evidence_gaps: list[str] = []
    if not text_contains_any(combined_text, ["节省", "提升", "缩短", "%", "小时", "天", "成本"]):
        evidence_gaps.append("缺少量化结果：最好补充节省时间、减少返工、降低成本或交付周期变化。")
    if not text_contains_any(profile_text, ["SOP", "标准化", "沉淀"]):
        evidence_gaps.append("缺少沉淀物证据：建议补 SOP、检查清单、脚本说明或报告目录。")
    if text_contains_any(job_text, ["agent", "智能体"]) and not text_contains_any(profile_text, ["Agent", "智能体"]):
        evidence_gaps.append("岗位强调 Agent，但当前画像里的 Agent 证据还不够明确。")

    next_steps = list((profile_match or {}).get("suggestions") or [])
    next_steps.append("补齐 B+C 两个核心案例的具体背景、动作、工具、结果和可证明材料。")

    return {
        "positioning": "AI产品经理 / 企业提效 / AI工作流",
        "case_focus": case_focus,
        "rewrite_points": rewrite_points,
        "evidence_gaps": evidence_gaps,
        "next_steps": next_steps,
    }


def extract_salary_numbers(value: object) -> list[float]:
    text = str(value or "")
    if not text.strip():
        return []

    range_with_unit = re.search(r"(\d+(?:\.\d+)?)\s*[Kk万]?\s*[-~至]\s*(\d+(?:\.\d+)?)\s*([Kk万])", text)
    if range_with_unit:
        low = float(range_with_unit.group(1))
        high = float(range_with_unit.group(2))
        if range_with_unit.group(3) == "万":
            low *= 10
            high *= 10
        return [low, high]

    range_in_wan = re.search(r"(\d+(?:\.\d+)?)\s*[-~至]\s*(\d+(?:\.\d+)?)\s*万", text)
    if range_in_wan:
        return [float(range_in_wan.group(1)) * 10, float(range_in_wan.group(2)) * 10]

    values: list[float] = []
    for number, unit in re.findall(r"(\d+(?:\.\d+)?)\s*([Kk万])", text):
        value_number = float(number)
        if unit == "万":
            value_number *= 10
        values.append(value_number)
    return values


def salary_midpoint(value: object) -> float | None:
    numbers = extract_salary_numbers(value)
    if not numbers:
        return None
    return (min(numbers) + max(numbers)) / 2


def build_market_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    salary_ranges: list[tuple[float, float]] = []
    city_counts: Counter[str] = Counter()
    keyword_counts: Counter[str] = Counter()

    for row in rows:
        numbers = extract_salary_numbers(row.get("salary_raw"))
        if numbers:
            salary_ranges.append((min(numbers), max(numbers)))

        location = str(row.get("location") or "").strip() or "地点待补充"
        city_counts[location] += 1

        searchable_text = " ".join(
            str(row.get(field, "") or "") for field in ("job_title", "skills", "main_text", "visual_summary")
        )
        for keyword in MARKET_SIGNAL_KEYWORDS:
            if text_contains_any(searchable_text, [keyword]):
                keyword_counts[keyword] += 1

    midpoints = [(low + high) / 2 for low, high in salary_ranges]
    return {
        "salary_sample_count": len(salary_ranges),
        "salary_floor": int(min((low for low, _ in salary_ranges), default=0)),
        "salary_ceiling": int(max((high for _, high in salary_ranges), default=0)),
        "salary_average_mid": int(round(sum(midpoints) / len(midpoints))) if midpoints else 0,
        "city_counts": dict(city_counts),
        "top_keywords": [
            {"keyword": keyword, "count": count}
            for keyword, count in keyword_counts.most_common(8)
        ],
    }


def build_job_value_signal(
    job: dict[str, Any],
    market_summary: dict[str, Any],
    profile_match: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score = 0
    signals: list[str] = []
    risks: list[str] = []

    match_score = int((profile_match or {}).get("score") or 0)
    if match_score >= 75:
        score += 35
        signals.append(f"画像匹配分 {match_score}，达到优先评估线。")
    elif match_score >= 60:
        score += 22
        signals.append(f"画像匹配分 {match_score}，值得继续补信息。")
    elif match_score:
        risks.append(f"画像匹配分 {match_score} 偏低，需要人工复核是否偏离主线。")

    job_midpoint = salary_midpoint(job.get("salary_raw"))
    market_midpoint = int(market_summary.get("salary_average_mid") or 0)
    if job_midpoint and market_midpoint:
        if job_midpoint >= market_midpoint:
            score += 25
            signals.append(f"薪资中位约 {job_midpoint:g}K，高于当前岗位池均值 {market_midpoint}K。")
        else:
            score += 10
            risks.append(f"薪资中位约 {job_midpoint:g}K，低于当前岗位池均值 {market_midpoint}K。")

    job_text = " ".join(str(job.get(field, "") or "") for field in ("job_title", "main_text", "visual_summary", "skills"))
    if text_contains_any(job_text, ["AI工作流", "AI 工作流", "Agent", "企业提效", "自动化"]):
        score += 25
        signals.append("岗位文本命中 AI 工作流 / Agent / 企业提效方向。")
    if text_contains_any(str(job.get("location") or ""), ["南京"]):
        score += 10
        signals.append("城市符合南京优先策略。")
    if text_contains_any(job_text, ["算法工程师", "纯算法", "模型训练"]) and not text_contains_any(job_text, ["产品", "工作流", "工具"]):
        score -= 15
        risks.append("岗位更偏算法工程，可能偏离 AI 产品主线。")

    value_score = max(0, min(100, score))
    if value_score >= 75:
        value_level = "高价值"
    elif value_score >= 55:
        value_level = "值得观察"
    else:
        value_level = "低投入"

    return {
        "value_score": value_score,
        "value_level": value_level,
        "signals": signals,
        "risks": risks,
    }


def extract_profile_keywords(profile: dict[str, str]) -> list[str]:
    source = " ".join(
        str(profile.get(field, "") or "")
        for field in ("target_roles", "core_skills", "project_highlights")
    )
    keywords: list[str] = []
    normalized = (
        source.replace("，", "、")
        .replace("；", "、")
        .replace(",", "、")
        .replace("/", "、")
        .replace("\n", "、")
        .replace(" ", "、")
    )
    for token in normalized.split("、"):
        cleaned = str(token).strip()
        if not cleaned or cleaned in keywords:
            continue
        if 2 <= len(cleaned) <= 20:
            keywords.append(cleaned)
    return keywords[:12]


def build_profile_snapshot(profile: dict[str, str]) -> list[tuple[str, str]]:
    keywords = extract_profile_keywords(profile)
    return [
        ("目标方向", profile.get("target_roles", "") or "待补充"),
        ("工作城市", profile.get("target_cities", "") or "待补充"),
        ("薪资底线", profile.get("salary_min", "") or "待补充"),
        ("核心关键词", " / ".join(keywords[:4]) if keywords else "待补充"),
    ]


def set_active_page(page: str) -> None:
    st.session_state["active_page"] = page


def get_active_page(default_page: str) -> str:
    return st.session_state.get("active_page", default_page)


def api_get(path: str) -> Any:
    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
        response = client.get(path)
        response.raise_for_status()
        return response.json()


def api_post(path: str, payload: dict[str, Any]) -> Any:
    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
        response = client.post(path, json=payload)
        response.raise_for_status()
        return response.json()


def api_delete(path: str) -> Any:
    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
        response = client.delete(path)
        response.raise_for_status()
        return response.json()


def fetch_health() -> dict[str, str]:
    return api_get("/api/health")


def fetch_jobs() -> list[dict[str, Any]]:
    return api_get("/api/jobs")


def normalize_jobs_response(payload: Any) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if isinstance(payload, dict) and "items" in payload:
        rows = list(payload.get("items") or [])
        total = int(payload.get("total", len(rows)) or 0)
        page = int(payload.get("page", 1) or 1)
        page_size = int(payload.get("page_size", len(rows) or 1) or 1)
        return rows, {"total": total, "page": page, "page_size": page_size}

    rows = list(payload or []) if isinstance(payload, list) else []
    return rows, {"total": len(rows), "page": 1, "page_size": max(1, len(rows))}


def build_page_options(total: int, page_size: int) -> list[int]:
    safe_total = max(0, int(total or 0))
    safe_page_size = max(1, int(page_size or 1))
    page_count = max(1, (safe_total + safe_page_size - 1) // safe_page_size)
    return list(range(1, page_count + 1))


def paginate_rows(rows: list[dict[str, Any]], page: int, page_size: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    safe_page_size = max(1, int(page_size or 1))
    total = len(rows)
    max_page = max(1, (total + safe_page_size - 1) // safe_page_size)
    safe_page = min(max(1, int(page or 1)), max_page)
    start = (safe_page - 1) * safe_page_size
    end = start + safe_page_size
    return rows[start:end], {"total": total, "page": safe_page, "page_size": safe_page_size}


def build_review_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_focus_jobs(rows, limit=len(rows) or 1)


def build_preset_display_name(preset: dict[str, Any]) -> str:
    name = str(preset.get("name") or "").strip()
    if name:
        return name

    platform = str(preset.get("platform") or "").strip().lower()
    platform_label = PLATFORM_DISPLAY.get(platform, platform.upper() if platform else "全平台")
    parts = [
        platform_label,
        str(preset.get("city") or "").strip(),
        str(preset.get("query") or "").strip(),
        str(preset.get("salary") or "").strip(),
    ]
    return " · ".join(part for part in parts if part) or "未命名搜索预设"


def build_import_candidate_summary(row: dict[str, Any]) -> str:
    title = str(row.get("job_title") or row.get("title") or "未命名岗位").strip()
    company = str(row.get("company_name") or row.get("company") or "未知公司").strip()
    salary = str(row.get("salary_raw") or row.get("salary") or "").strip()
    location = str(row.get("location") or "").strip()
    source = str(row.get("source") or "").strip()
    parts = [company, title, salary, location]
    summary = " / ".join(part for part in parts if part)
    if source:
        summary = f"{summary} · 来源：{source}"
    duplicate_job_id = row.get("duplicate_job_id")
    if duplicate_job_id:
        summary = f"{summary} · 重复：#{duplicate_job_id}"
    return summary


def group_import_candidates(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "pending": [],
        "duplicates": [],
        "accepted": [],
        "rejected": [],
    }
    for row in rows:
        decision = str(row.get("decision") or "pending").strip()
        if decision == "pending" and row.get("duplicate_job_id"):
            grouped["duplicates"].append(row)
        elif decision in grouped:
            grouped[decision].append(row)
        else:
            grouped["pending"].append(row)
    return grouped


def fetch_job_detail(job_id: int) -> dict[str, Any]:
    return api_get(f"/api/jobs/{job_id}")


def fetch_profile() -> dict[str, str]:
    profile = api_get("/api/profile")
    return {**default_profile_form(), **profile}


def fetch_weekly_review() -> dict[str, Any]:
    return api_get("/api/reviews/weekly")


def fetch_search_presets() -> list[dict[str, Any]]:
    return api_get("/api/search-presets")


def save_search_preset(payload: dict[str, Any]) -> dict[str, Any]:
    return api_post("/api/search-presets", payload)


def delete_search_preset_by_id(preset_id: int) -> dict[str, Any]:
    return api_delete(f"/api/search-presets/{preset_id}")


def run_search_preset(preset_id: int, limit: int = 20) -> dict[str, Any]:
    return api_post(f"/api/search-presets/{preset_id}/run", {"limit": int(limit)})


def fetch_import_candidates(decision: str = "") -> list[dict[str, Any]]:
    suffix = f"?decision={decision}" if decision else "?decision="
    return api_get(f"/api/import-review/candidates{suffix}")


def accept_import_candidate(candidate_id: int) -> dict[str, Any]:
    return api_post(f"/api/import-review/candidates/{candidate_id}/accept", {})


def reject_import_candidate(candidate_id: int, reason: str) -> dict[str, Any]:
    return api_post(f"/api/import-review/candidates/{candidate_id}/reject", {"reason": reason})


def save_profile_form(payload: dict[str, Any]) -> dict[str, Any]:
    return api_post("/api/profile", payload)


def import_resume_profile(resume_path: str) -> dict[str, Any]:
    return api_post("/api/profile/import-resume", {"resume_path": resume_path})


def save_job_status(job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return api_post(f"/api/jobs/{job_id}/status", payload)


def save_bulk_job_status(payload: dict[str, Any]) -> dict[str, Any]:
    return api_post("/api/jobs/bulk-status", payload)


def generate_job_score(job_id: int) -> dict[str, Any]:
    return api_post(f"/api/jobs/{job_id}/score", {})


def generate_job_materials(job_id: int) -> dict[str, Any]:
    return api_post(f"/api/jobs/{job_id}/materials/generate", {})


def save_job_materials(job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return api_post(f"/api/jobs/{job_id}/materials", payload)


def regenerate_visual_summary(job_id: int) -> dict[str, Any]:
    return api_post(f"/api/jobs/{job_id}/visual-summary/regenerate", {})


def create_application_event(job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return api_post(f"/api/jobs/{job_id}/application-events", payload)


def create_job_task(job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return api_post(f"/api/jobs/{job_id}/tasks", payload)


def complete_job_task_by_id(task_id: int) -> dict[str, Any]:
    return api_post(f"/api/tasks/{task_id}/complete", {})


def render_api_error(error: Exception) -> None:
    st.error(UI_TEXT["api_error"])
    st.markdown(
        "请先运行项目根目录下的 `Start-Chances.cmd`，"
        "然后打开 [http://127.0.0.1:8501](http://127.0.0.1:8501)。"
    )
    st.caption("提示：`http://127.0.0.1:8000` 是后端接口，不是求职作战台页面。")
    with st.expander("查看技术错误"):
        st.code(str(error))


def build_app_styles() -> str:
    return """
        <style>
        :root {
            --brand-ink: #121722;
            --brand-accent: #0b7a65;
            --brand-action: #315f9f;
            --brand-warning: #b85c00;
            --surface-app: #f5f7fb;
            --surface-panel: #ffffff;
            --surface-subtle: #eef2f6;
            --surface-rail: #e8edf4;
            --border: #d8dee8;
            --border-strong: #b8c1cf;
            --text: #17202f;
            --muted: #667085;
            --faint: #8a94a6;
            --status-focus: #0b7a65;
            --status-progress: #315f9f;
            --status-warn: #b85c00;
            --status-risk: #b42318;
            --shadow: 0 14px 32px rgba(22, 31, 48, 0.08);
        }

        .stApp {
            background: var(--surface-app);
            color: var(--text);
        }

        .block-container {
            max-width: 1380px;
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }

        [data-testid="stHeader"] {
            display: none;
        }

        [data-testid="stToolbar"] {
            display: none;
        }

        [data-testid="stSidebar"] {
            background: #111827;
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] * {
            color: #f8fafc;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label,
        [data-testid="stSidebar"] .stButton button {
            border-radius: 8px;
        }

        [data-testid="stSidebar"] .stButton button {
            background: #22304a;
            border: 1px solid rgba(255, 255, 255, 0.14);
            color: #ffffff;
        }

        .app-frame {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .top-command-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.9rem 1rem;
            background: var(--surface-panel);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(22, 31, 48, 0.04);
        }

        .app-mark {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            min-width: 0;
        }

        .app-logo {
            width: 2.4rem;
            height: 2.4rem;
            border-radius: 8px;
            background: #111827;
            color: #ffffff;
            display: grid;
            place-items: center;
            font-weight: 800;
            letter-spacing: 0;
        }

        .app-title {
            color: var(--brand-ink);
            font-size: 1.08rem;
            font-weight: 800;
            line-height: 1.2;
            margin: 0;
        }

        .app-subtitle {
            color: var(--muted);
            font-size: 0.84rem;
            margin-top: 0.16rem;
        }

        .top-meta {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
            justify-content: flex-end;
        }

        .ops-hero {
            background: var(--surface-panel);
            border: 1px solid var(--border);
            border-left: 4px solid var(--brand-accent);
            border-radius: 8px;
            padding: 1.25rem;
            box-shadow: var(--shadow);
            margin-bottom: 0.65rem;
        }

        .hero-eyebrow {
            font-size: 0.76rem;
            color: var(--brand-accent);
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .hero-title {
            color: var(--brand-ink);
            font-size: clamp(1.55rem, 3vw, 2.2rem);
            font-weight: 800;
            line-height: 1.15;
            margin: 0;
        }

        .hero-copy {
            color: var(--muted);
            font-size: 0.96rem;
            max-width: 64rem;
            margin-top: 0.55rem;
        }

        .hero-rail {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.75rem;
            margin-top: 1rem;
        }

        .rail-cell {
            background: var(--surface-subtle);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.75rem;
        }

        .rail-label {
            color: var(--faint);
            font-size: 0.75rem;
            font-weight: 700;
        }

        .rail-value {
            color: var(--brand-ink);
            font-size: 0.98rem;
            font-weight: 800;
            margin-top: 0.25rem;
            overflow-wrap: anywhere;
        }

        .command-grid, .density-grid {
            display: grid;
            gap: 0.75rem;
        }

        .command-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .density-grid {
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .command-tile, .metric-card, .panel-card, .signal-card {
            background: var(--surface-panel);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(22, 31, 48, 0.04);
        }

        .command-tile {
            min-height: 124px;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 0.8rem;
        }

        .command-index {
            width: 1.65rem;
            height: 1.65rem;
            border-radius: 6px;
            display: grid;
            place-items: center;
            background: #e3f5ef;
            color: var(--status-focus);
            font-size: 0.78rem;
            font-weight: 800;
        }

        .entry-title, .section-title {
            font-size: 1rem;
            font-weight: 800;
            color: var(--brand-ink);
            margin: 0 0 0.25rem;
        }

        .entry-copy, .section-copy {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.6;
        }

        .workspace-section {
            margin-top: 1.25rem;
            margin-bottom: 0.65rem;
        }

        .section-title {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .section-title::before {
            content: "";
            width: 0.48rem;
            height: 0.48rem;
            border-radius: 2px;
            background: var(--brand-accent);
        }

        .metric-card, .signal-card {
            min-height: 110px;
            padding: 1rem;
            position: relative;
            overflow: hidden;
        }

        .metric-card::after {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            bottom: 0;
            height: 3px;
            background: var(--brand-accent);
        }

        .metric-label {
            font-size: 0.78rem;
            color: var(--muted);
            font-weight: 700;
        }

        .metric-value {
            font-size: 1.9rem;
            line-height: 1;
            font-weight: 800;
            margin-top: 0.55rem;
            color: var(--brand-ink);
        }

        .metric-hint {
            font-size: 0.82rem;
            color: var(--muted);
            margin-top: 0.48rem;
        }

        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0.45rem 0 0.2rem;
        }

        .chip, .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.32rem;
            padding: 0.34rem 0.62rem;
            border-radius: 999px;
            background: #e6f4ef;
            color: var(--status-focus);
            border: 1px solid #bfe3d5;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .chip.warm {
            background: #fff4e5;
            color: var(--status-warn);
            border-color: #fed7aa;
        }

        .status-pill.progress {
            background: #e8f0ff;
            color: var(--status-progress);
            border-color: #c7d7fe;
        }

        .status-pill.risk {
            background: #fff1f1;
            color: var(--status-risk);
            border-color: #f8c7c7;
        }

        .panel-card {
            padding: 1rem;
            margin-bottom: 0.75rem;
        }

        .list-note {
            background: #ffffff;
            border: 1px dashed var(--border-strong);
            border-radius: 8px;
            padding: 0.85rem 1rem;
            color: var(--muted);
        }

        .detail-heading {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--surface-panel);
            padding: 1rem;
            margin-bottom: 0.75rem;
        }

        .detail-title {
            color: var(--brand-ink);
            font-size: 1.08rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }

        .summary-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.5rem;
            margin: 0.65rem 0 0.9rem;
        }

        .summary-item {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--surface-panel);
            padding: 0.72rem;
        }

        .summary-label {
            color: var(--faint);
            font-size: 0.74rem;
            font-weight: 700;
        }

        .summary-value {
            color: var(--brand-ink);
            font-size: 0.88rem;
            font-weight: 750;
            margin-top: 0.22rem;
            overflow-wrap: anywhere;
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] button {
            border-radius: 8px;
            border: 1px solid var(--border-strong);
            font-weight: 700;
        }

        .stButton > button[kind="primary"],
        [data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: var(--brand-ink);
            border-color: var(--brand-ink);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
            background: var(--surface-panel);
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {
            border-radius: 8px;
            background: #ffffff;
            border-color: var(--border);
            color: var(--text);
        }

        .stSelectbox div[data-baseweb="select"] span,
        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {
            color: var(--muted);
        }

        .stTextInput input:disabled,
        .stTextArea textarea:disabled {
            color: var(--text);
            -webkit-text-fill-color: var(--text);
            opacity: 1;
        }

        @media (max-width: 900px) {
            .top-command-bar,
            .app-mark {
                align-items: flex-start;
            }

            .top-command-bar {
                flex-direction: column;
            }

            .top-meta {
                justify-content: flex-start;
            }

            .hero-rail,
            .command-grid,
            .density-grid,
            .summary-strip {
                grid-template-columns: 1fr;
            }
        }
        </style>
    """


def inject_app_styles() -> None:
    st.markdown(build_app_styles(), unsafe_allow_html=True)


def render_section_title(title: str, copy: str = "") -> None:
    copy_html = f'<div class="section-copy">{escape(copy)}</div>' if copy else ""
    st.markdown(
        f'<div class="workspace-section"><div class="section-title">{escape(title)}</div>{copy_html}</div>',
        unsafe_allow_html=True,
    )


def build_app_header_html(active_page: str, api_connected: bool) -> str:
    connection_label = "接口已连接" if api_connected else "接口未连接"
    connection_variant = "progress" if api_connected else "risk"
    return f"""
        <div class="top-command-bar">
            <div class="app-mark">
                <div class="app-logo">C</div>
                <div>
                    <div class="app-title">{escape(UI_TEXT["page_title"])}</div>
                    <div class="app-subtitle">本地机会池 · 画像匹配 · 推进记录</div>
                </div>
            </div>
            <div class="top-meta">
                <span class="status-pill progress">{escape(active_page)}</span>
                <span class="status-pill {connection_variant}">{connection_label}</span>
            </div>
        </div>
        """


def render_app_header(active_page: str, api_connected: bool) -> None:
    st.markdown(
        build_app_header_html(active_page, api_connected),
        unsafe_allow_html=True,
    )


def build_summary_strip_html(items: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<div class="summary-item"><div class="summary-label">{escape(label)}</div>'
        f'<div class="summary-value">{escape(value)}</div></div>'
        for label, value in items
    )
    return f'<div class="summary-strip">{cells}</div>'


def render_summary_strip(items: list[tuple[str, str]]) -> None:
    st.markdown(build_summary_strip_html(items), unsafe_allow_html=True)


def render_metric_card(label: str, value: Any, hint: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{escape(str(label))}</div>
            <div class="metric-value">{escape(str(value))}</div>
            <div class="metric-hint">{escape(str(hint))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chip_row(values: list[str], warm: bool = False) -> None:
    if not values:
        return
    variant = "warm" if warm else ""
    chips = "".join(f'<span class="chip {variant}">{escape(value)}</span>' for value in values if value)
    st.markdown(f'<div class="chip-row">{chips}</div>', unsafe_allow_html=True)


def render_advice_list(title: str, items: list[str]) -> None:
    if not items:
        return
    st.write(f"**{title}**")
    for item in items:
        st.write(f"- {item}")


def render_market_summary(summary: dict[str, Any]) -> None:
    top_keywords = summary.get("top_keywords", []) or []
    keyword_text = " / ".join(str(item.get("keyword")) for item in top_keywords[:4]) if top_keywords else "待积累"
    render_section_title("市场摘要", "从当前岗位池提取薪资、城市和技能需求信号。")
    market_cols = st.columns(4)
    market_cols[0].metric("薪资样本", int(summary.get("salary_sample_count", 0)))
    market_cols[1].metric("薪资均值", f"{int(summary.get('salary_average_mid', 0))}K")
    market_cols[2].metric("薪资上限", f"{int(summary.get('salary_ceiling', 0))}K")
    market_cols[3].metric("高频关键词", keyword_text)


def render_job_value_signal(signal: dict[str, Any]) -> None:
    render_section_title("岗位价值信号", "综合画像匹配、薪资竞争力和市场关键词。")
    score_col, level_col = st.columns(2)
    score_col.metric("价值分", int(signal.get("value_score", 0)))
    level_col.metric("价值判断", str(signal.get("value_level", "")))
    render_advice_list("正向信号", list(signal.get("signals", []) or []))
    render_advice_list("风险信号", list(signal.get("risks", []) or []))


def render_home(jobs: list[dict[str, Any]], profile: dict[str, str]) -> None:
    metrics = build_home_metrics(jobs)
    snapshot = build_profile_snapshot(profile)
    actions = build_entry_actions(metrics, profile)

    headline = profile.get("target_roles") or "先完善你的求职方向"
    city = profile.get("target_cities") or "城市待补充"
    salary = profile.get("salary_min") or "薪资底线待补充"

    st.markdown(
        f"""
        <div class="ops-hero">
            <div class="hero-eyebrow">今日求职推进</div>
            <div class="hero-title">{escape(headline)}</div>
            <div class="hero-copy">
                今天先看画像边界、机会质量和推进动作，再进入具体岗位。界面按可扫描的工作台组织，方便每天打开就接着处理。
            </div>
            <div class="hero-rail">
                <div class="rail-cell">
                    <div class="rail-label">目标方向</div>
                    <div class="rail-value">{escape(headline)}</div>
                </div>
                <div class="rail-cell">
                    <div class="rail-label">重点城市</div>
                    <div class="rail-value">{escape(city)}</div>
                </div>
                <div class="rail-cell">
                    <div class="rail-label">薪资底线</div>
                    <div class="rail-value">{escape(salary)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_section_title("今日动作", "先处理最可能带来结果的三个入口。")
    action_cols = st.columns(3)
    for index, action in enumerate(actions):
        with action_cols[index]:
            st.markdown(
                f"""
                <div class="command-tile">
                    <div>
                        <div class="command-index">{index + 1}</div>
                        <div class="entry-title">{escape(action['title'])}</div>
                    </div>
                    <div class="entry-copy">{escape(action['copy'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"打开{action['target_page']}", key=f"entry-{index}", use_container_width=True):
                set_active_page(action["target_page"])
                st.rerun()

    render_summary_strip(snapshot)

    render_section_title(UI_TEXT["home_metrics_title"], "先看总量，再决定下一步动作。")
    total_col, todo_col, priority_col, applied_col = st.columns(4)
    with total_col:
        render_metric_card(UI_TEXT["total_jobs"], metrics["total_jobs"], "机会池已收录岗位")
    with todo_col:
        render_metric_card(UI_TEXT["todo_jobs"], metrics["todo_jobs"], "等待整理或推进")
    with priority_col:
        render_metric_card(UI_TEXT["high_priority_jobs"], metrics["high_priority_jobs"], "适合优先投入时间")
    with applied_col:
        render_metric_card(UI_TEXT["applied_jobs"], metrics["applied_jobs"], "已经完成投递")

    render_market_summary(build_market_summary(jobs))

    todo_jobs = build_focus_jobs(jobs)
    high_priority_jobs = [row for row in jobs if row.get("priority") == "高"][:8]

    left, right = st.columns([1.2, 1])
    with left:
        render_section_title(UI_TEXT["today_focus"], "先处理最靠近结果的岗位。")
        if todo_jobs:
            st.dataframe(present_job_rows(todo_jobs), hide_index=True, width="stretch")
        else:
            st.markdown('<div class="list-note">当前没有待推进岗位，可以去岗位池继续筛选或补录。</div>', unsafe_allow_html=True)
    with right:
        render_section_title("高优先级岗位", "这块适合优先做简历和沟通准备。")
        if high_priority_jobs:
            st.dataframe(present_job_rows(high_priority_jobs), hide_index=True, width="stretch")
        else:
            st.markdown('<div class="list-note">当前还没有高优先级岗位，可以先从待评估岗位里挑出最匹配的机会。</div>', unsafe_allow_html=True)

    try:
        review = fetch_weekly_review()
    except Exception:
        review = {}
    status_rows = build_status_rows(review.get("status_counts", {})) if review.get("status_counts") else []
    if status_rows:
        render_section_title("状态分布", "看一下岗位目前集中在哪些阶段。")
        st.dataframe(as_frame(status_rows, ["状态", "数量"]), hide_index=True, width="stretch")
    if review:
        render_section_title("跟进提醒", "把任务和停滞岗位提前暴露出来。")
        for item in build_home_followup_summary(review):
            st.markdown(f"- {item}")


def render_job_detail_panel(detail: dict[str, Any], profile: dict[str, str], market_summary: dict[str, Any]) -> None:
    job = detail["job"]
    evaluation = detail.get("evaluation")
    timeline = detail.get("timeline", [])
    capture_assets = present_capture_assets(detail.get("assets", []))
    profile_match = detail.get("profile_match")

    status = str(job.get("status", "状态待补充"))
    badge_variant = get_status_badge_variant(status)
    st.markdown(
        f"""
        <div class="detail-heading">
            <div class="hero-eyebrow">{escape(UI_TEXT["job_detail_title"])}</div>
            <div class="detail-title">{escape(job.get('company_name', '公司待补充'))} · {escape(job.get('job_title', '岗位待补充'))}</div>
            <span class="status-pill {escape(badge_variant)}">{escape(status)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_chip_row(
        [
            job.get("platform_label", "未知来源"),
            job.get("salary_raw", "薪资待补充"),
            job.get("location", "地点待补充"),
            job.get("priority", "普通"),
        ]
    )

    st.write(f"**下一步动作：** {job.get('next_action', '待补充')}")

    if job.get("visual_summary"):
        st.text_area("视觉提要", value=job["visual_summary"], height=180, disabled=True)
    if st.button("重新生成视觉摘要", key=f"regen-visual-{job['id']}"):
        regenerate_visual_summary(int(job["id"]))
        st.success("视觉摘要已重新生成。")
        st.rerun()
    if job.get("main_text"):
        st.text_area("岗位正文", value=job["main_text"], height=220, disabled=True)

    if capture_assets:
        render_section_title("页面证据", "保留原始截图，方便核对提取质量。")
        ordered_assets = present_capture_assets(group_capture_assets(detail.get("assets", [])))
        tabs = st.tabs([asset["label"] for asset in ordered_assets])
        for tab, asset in zip(tabs, ordered_assets):
            with tab:
                st.image(asset["file_path"], use_container_width=True)

    if profile_match:
        render_section_title("岗位匹配建议", "这里的建议基于你的个人画像生成。")
        score_col, recommendation_col = st.columns(2)
        score_col.metric("匹配分", profile_match.get("score", 0))
        recommendation_col.metric("建议结论", profile_match.get("recommendation", ""))
        if profile_match.get("strengths"):
            st.write(f"**匹配亮点：** {'；'.join(profile_match['strengths'])}")
        if profile_match.get("risks"):
            st.write(f"**风险提示：** {'；'.join(profile_match['risks'])}")
        if profile_match.get("suggestions"):
            st.write(f"**建议动作：** {'；'.join(profile_match['suggestions'])}")

    render_job_value_signal(build_job_value_signal(job, market_summary, profile_match))

    render_section_title("评分与准备", "把判断和投递材料沉淀成可复用资产。")
    score_history = list(detail.get("score_history", []) or [])
    score_summary = build_score_history_summary(score_history)
    score_col, material_col = st.columns(2)
    with score_col:
        st.metric("最新评分", score_summary["latest_score"])
        st.caption(f"历史评分 {score_summary['count']} 次")
        if st.button("生成岗位评分", type="primary", key=f"score-job-{job['id']}"):
            generate_job_score(int(job["id"]))
            st.success("岗位评分已生成。")
            st.rerun()
        if score_history:
            st.dataframe(
                as_frame(score_history, ["created_at", "score", "recommendation", "rubric_version"]),
                hide_index=True,
                width="stretch",
            )
    with material_col:
        materials = dict(detail.get("materials") or {})
        completion = build_materials_completion(materials)
        st.metric("准备包完成度", f"{completion['percent']}%")
        st.caption(f"{completion['completed']} / {completion['total']} 项已填写")
        if st.button("生成准备包", key=f"generate-materials-{job['id']}"):
            generate_job_materials(int(job["id"]))
            st.success("准备包已生成。")
            st.rerun()

    materials = dict(detail.get("materials") or {})
    with st.expander("编辑准备包", expanded=bool(materials)):
        resume_angle = st.text_area("简历投递角度", value=str(materials.get("resume_angle") or ""), height=90, key=f"materials-resume-{job['id']}")
        project_highlights = st.text_area("项目亮点", value=str(materials.get("project_highlights") or ""), height=100, key=f"materials-projects-{job['id']}")
        recruiter_questions = st.text_area("HR 问题", value=str(materials.get("recruiter_questions") or ""), height=90, key=f"materials-questions-{job['id']}")
        interview_prep = st.text_area("面试准备", value=str(materials.get("interview_prep") or ""), height=100, key=f"materials-interview-{job['id']}")
        communication_draft = st.text_area("沟通草稿", value=str(materials.get("communication_draft") or ""), height=90, key=f"materials-draft-{job['id']}")
        risk_response = st.text_area("风险回应", value=str(materials.get("risk_response") or ""), height=90, key=f"materials-risk-{job['id']}")
        if st.button("保存准备包", type="primary", key=f"save-materials-{job['id']}"):
            save_job_materials(
                int(job["id"]),
                {
                    "resume_angle": resume_angle,
                    "project_highlights": project_highlights,
                    "recruiter_questions": recruiter_questions,
                    "interview_prep": interview_prep,
                    "communication_draft": communication_draft,
                    "risk_response": risk_response,
                },
            )
            st.success("准备包已保存。")
            st.rerun()

    render_section_title("投递追踪", "记录已经发生的动作和下一步提醒。")
    event_col, task_col = st.columns(2)
    with event_col:
        event_type = st.selectbox(
            "新增事件",
            list(APPLICATION_EVENT_LABELS),
            format_func=lambda value: APPLICATION_EVENT_LABELS[value],
            key=f"event-type-{job['id']}",
        )
        channel = st.text_input("渠道", value=str(job.get("platform_label") or ""), key=f"event-channel-{job['id']}")
        note = st.text_area("事件备注", key=f"event-note-{job['id']}", height=80)
        if st.button("记录投递事件", key=f"add-event-{job['id']}"):
            create_application_event(int(job["id"]), {"event_type": event_type, "channel": channel, "note": note})
            st.success("投递事件已记录。")
            st.rerun()
        events = list(detail.get("application_events", []) or [])
        if events:
            st.dataframe(present_application_events(events), hide_index=True, width="stretch")
    with task_col:
        task_title = st.text_input("跟进任务", placeholder="明天跟进 HR 回复", key=f"task-title-{job['id']}")
        due_date = st.text_input("截止日期", placeholder="2026-06-10", key=f"task-due-{job['id']}")
        if st.button("新增任务", key=f"add-task-{job['id']}"):
            create_job_task(int(job["id"]), {"title": task_title, "due_date": due_date})
            st.success("跟进任务已新增。")
            st.rerun()
        tasks = list(detail.get("tasks", []) or [])
        open_tasks = [task for task in tasks if task.get("status") == "open"]
        if open_tasks:
            st.dataframe(present_open_tasks(open_tasks), hide_index=True, width="stretch")
            task_options = {f"#{task['id']} · {task.get('title', '')}": int(task["id"]) for task in open_tasks}
            selected_task = st.selectbox("选择完成的任务", list(task_options.keys()), key=f"complete-task-select-{job['id']}")
            if st.button("完成任务", key=f"complete-task-{job['id']}"):
                complete_job_task_by_id(task_options[selected_task])
                st.success("任务已完成。")
                st.rerun()

    resume_advice = build_resume_advice(profile, job, profile_match)
    render_section_title("简历改写建议", "先在项目内给出改写方向，后续再生成 Markdown 或 PDF 版本。")
    render_summary_strip([("主定位", str(resume_advice["positioning"]))])
    render_advice_list("主打案例", list(resume_advice["case_focus"]))
    render_advice_list("改写方向", list(resume_advice["rewrite_points"]))
    render_advice_list("证据缺口", list(resume_advice["evidence_gaps"]))
    render_advice_list("下一步", list(resume_advice["next_steps"]))

    render_section_title(UI_TEXT["job_evaluation_title"])
    if evaluation:
        score_col, recommendation_col = st.columns(2)
        score_col.metric("匹配分", evaluation.get("match_score", 0))
        recommendation_col.metric("建议", evaluation.get("recommendation", ""))
        st.write(f"**判断依据：** {evaluation.get('reasoning', '')}")
        st.write(f"**亮点：** {evaluation.get('highlights', '')}")
        st.write(f"**风险：** {evaluation.get('risks', '')}")
        st.write(f"**建议动作：** {evaluation.get('next_step_hint', '')}")
    else:
        st.info(UI_TEXT["no_evaluation"])

    render_section_title(UI_TEXT["jobs_timeline"])
    if timeline:
        timeline_frame = as_frame(timeline, ["created_at", "status", "next_action", "note"]).rename(columns=TIMELINE_LABELS)
        st.dataframe(timeline_frame, hide_index=True, width="stretch")
    else:
        st.info(UI_TEXT["no_timeline"])


def render_jobs_board(jobs: list[dict[str, Any]], profile: dict[str, str]) -> None:
    metrics = build_home_metrics(jobs)
    market_summary = build_market_summary(jobs)
    st.markdown(
        f"""
        <div class="ops-hero">
            <div class="hero-eyebrow">岗位推进流程</div>
            <div class="hero-title">{escape(UI_TEXT["jobs_board_title"])}</div>
            <div class="hero-copy">把岗位列表当成一条推进流水线：先筛选，再批量标记，最后进入单个岗位判断。</div>
            <div class="hero-rail">
                <div class="rail-cell">
                    <div class="rail-label">收录岗位</div>
                    <div class="rail-value">{metrics["total_jobs"]}</div>
                </div>
                <div class="rail-cell">
                    <div class="rail-label">待推进</div>
                    <div class="rail-value">{metrics["todo_jobs"]}</div>
                </div>
                <div class="rail-cell">
                    <div class="rail-label">高优先级</div>
                    <div class="rail-value">{metrics["high_priority_jobs"]}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_section_title("筛选器", "先缩小范围，再做批量动作。")
    filter_col, priority_col, keyword_col = st.columns([1, 1, 1.2])
    with filter_col:
        status = st.selectbox("按状态筛选", [""] + STATUS_OPTIONS, format_func=lambda value: value or "全部")
    with priority_col:
        priority = st.selectbox("按优先级筛选", [""] + PRIORITY_OPTIONS, format_func=lambda value: value or "全部")
    with keyword_col:
        keyword = st.text_input("关键词", placeholder="岗位 / 公司 / 正文摘要")

    filtered = filter_opportunities(jobs, status=status, priority=priority, keyword=keyword)
    if not filtered:
        st.markdown('<div class="list-note">当前筛选条件下没有岗位，可以放宽条件试试。</div>', unsafe_allow_html=True)
        return

    page_col, page_size_col, queue_col = st.columns([1, 1, 1.2])
    with page_size_col:
        page_size = st.selectbox("每页数量", [10, 20, 50, 100], index=1)
    page_options = build_page_options(len(filtered), page_size)
    with page_col:
        page = st.selectbox("页码", page_options, index=0, format_func=lambda value: f"第 {value} 页")
    page_rows, page_meta = paginate_rows(filtered, page=page, page_size=page_size)
    with queue_col:
        review_queue = build_review_queue(filtered)
        st.metric("快速审查队列", len(review_queue))
        st.caption(f"共 {page_meta['total']} 条，当前显示 {len(page_rows)} 条")

    bulk_rows = [{"selected": False, **row} for row in page_rows]
    bulk_frame = as_frame(bulk_rows, ["selected"] + JOB_TABLE_COLUMNS)
    display_bulk = bulk_frame.rename(columns={"selected": "选择", **JOB_TABLE_LABELS})
    disabled_columns = list(JOB_TABLE_LABELS.values())

    edited_bulk = st.data_editor(
        display_bulk,
        hide_index=True,
        width="stretch",
        disabled=disabled_columns,
        key="bulk-job-editor",
    )

    selected_records = edited_bulk.rename(columns={"选择": "selected", **{value: key for key, value in JOB_TABLE_LABELS.items()}})
    selected_ids = collect_bulk_job_ids(selected_records.to_dict(orient="records"))
    if selected_ids:
        render_section_title("批量更新", f"已选中 {len(selected_ids)} 个岗位。")
        bulk_status_col, bulk_action_col = st.columns(2)
        bulk_status = bulk_status_col.selectbox("批量新状态", STATUS_OPTIONS, key="bulk-status")
        bulk_next_action = bulk_action_col.text_input("批量下一步动作", value="统一推进这批岗位", key="bulk-next-action")
        bulk_note = st.text_area("批量备注", placeholder="记录这次批量推进的背景", key="bulk-note")
        if st.button("执行批量更新", type="primary"):
            save_bulk_job_status(
                {
                    "job_ids": selected_ids,
                    "status": bulk_status,
                    "next_action": bulk_next_action,
                    "note": bulk_note,
                }
            )
            st.success(f"已批量更新 {len(selected_ids)} 个岗位。")
            st.rerun()

    job_options = {
        f"#{row['id']} · {row['company_name']} / {row['job_title']} / {row['status']}": row["id"]
        for row in page_rows
    }
    selected_label = st.selectbox("选择要查看和更新的岗位", list(job_options.keys()))
    selected_job_id = job_options[selected_label]

    detail = fetch_job_detail(int(selected_job_id))
    selected_job = detail["job"]
    edit_col, detail_col = st.columns([0.92, 1.25])
    with edit_col:
        render_section_title("推进动作", "记录这一次状态变化和下一步动作。")
        current_status = selected_job.get("status", "")
        default_index = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
        new_status = st.selectbox("新状态", STATUS_OPTIONS, index=default_index)
        next_action = st.text_input(UI_TEXT["next_action"], value=selected_job.get("next_action", ""))
        note = st.text_area(UI_TEXT["status_note"], placeholder="记录这次推进的上下文")
        if st.button(UI_TEXT["update_status"], type="primary"):
            save_job_status(selected_job["id"], {"status": new_status, "next_action": next_action, "note": note})
            st.success(UI_TEXT["status_saved"])
            st.rerun()
    with detail_col:
        render_job_detail_panel(detail, profile, market_summary)


def render_search_and_import() -> None:
    try:
        presets = fetch_search_presets()
        candidates = fetch_import_candidates()
    except Exception as error:  # pragma: no cover
        render_api_error(error)
        return

    grouped = group_import_candidates(candidates)
    st.markdown(
        f"""
        <div class="ops-hero">
            <div class="hero-eyebrow">搜索与导入</div>
            <div class="hero-title">{escape(UI_TEXT["import_review_title"])}</div>
            <div class="hero-copy">把搜索条件固定下来，把外部导入先放进审查区，再决定是否进入正式岗位池。</div>
            <div class="hero-rail">
                <div class="rail-cell">
                    <div class="rail-label">搜索预设</div>
                    <div class="rail-value">{len(presets)}</div>
                </div>
                <div class="rail-cell">
                    <div class="rail-label">待审查</div>
                    <div class="rail-value">{len(grouped["pending"])}</div>
                </div>
                <div class="rail-cell">
                    <div class="rail-label">疑似重复</div>
                    <div class="rail-value">{len(grouped["duplicates"])}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    preset_col, inbox_col = st.columns([0.9, 1.15])
    with preset_col:
        render_section_title("搜索预设", "固定常用搜索条件，后续用于导入候选岗位。")
        with st.form("search-preset-form"):
            name = st.text_input("预设名称", placeholder="南京 AI 产品经理 15K+")
            platform = st.selectbox("平台", ["boss", "manual", "liepin", "lagou", "zhaopin"], format_func=lambda value: PLATFORM_DISPLAY.get(value, value))
            city = st.text_input("城市", placeholder="南京")
            query = st.text_input("关键词", placeholder="AI产品经理")
            salary = st.text_input("薪资", placeholder="15K+")
            filters_json = st.text_area("高级筛选 JSON", value="{}", height=90)
            if st.form_submit_button("保存搜索预设", type="primary"):
                save_search_preset(
                    {
                        "name": name or build_preset_display_name(
                            {"platform": platform, "city": city, "query": query, "salary": salary}
                        ),
                        "platform": platform,
                        "city": city,
                        "query": query,
                        "salary": salary,
                        "filters_json": filters_json,
                    }
                )
                st.success("搜索预设已保存。")
                st.rerun()

        if presets:
            st.dataframe(
                as_frame(
                    [
                        {
                            "名称": build_preset_display_name(preset),
                            "平台": PLATFORM_DISPLAY.get(str(preset.get("platform", "")).lower(), preset.get("platform", "")),
                            "城市": preset.get("city", ""),
                            "关键词": preset.get("query", ""),
                            "薪资": preset.get("salary", ""),
                        }
                        for preset in presets
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            run_options = {
                build_preset_display_name(preset): int(preset["id"])
                for preset in presets
                if preset.get("id") and str(preset.get("platform") or "").lower() == "boss"
            }
            if run_options:
                run_col, limit_col = st.columns([0.72, 0.28])
                with run_col:
                    selected_run_preset = st.selectbox("选择要运行的预设", list(run_options.keys()), key="run-search-preset")
                with limit_col:
                    search_limit = st.number_input("数量", min_value=1, max_value=100, value=20, step=1)
                if st.button("运行搜索", type="primary"):
                    try:
                        result = run_search_preset(run_options[selected_run_preset], int(search_limit))
                    except httpx.HTTPStatusError as error:
                        try:
                            detail = error.response.json().get("detail", str(error))
                        except ValueError:
                            detail = str(error)
                        st.error(detail)
                    except Exception as error:  # pragma: no cover
                        render_api_error(error)
                    else:
                        st.success(f"已导入 {result.get('created_count', 0)} 个候选岗位。")
                        st.rerun()

            preset_options = {build_preset_display_name(preset): int(preset["id"]) for preset in presets if preset.get("id")}
            selected_preset = st.selectbox("选择要删除的预设", list(preset_options.keys()))
            if st.button("删除预设", type="secondary"):
                delete_search_preset_by_id(preset_options[selected_preset])
                st.success("搜索预设已删除。")
                st.rerun()
        else:
            st.markdown('<div class="list-note">当前还没有搜索预设。</div>', unsafe_allow_html=True)

    with inbox_col:
        render_section_title("导入审查", "外部来源先进入审查区，接受后才会写入正式岗位池。")
        review_tabs = st.tabs(
            [
                f"待审查 {len(grouped['pending'])}",
                f"疑似重复 {len(grouped['duplicates'])}",
                f"已接受 {len(grouped['accepted'])}",
                f"已拒绝 {len(grouped['rejected'])}",
            ]
        )

        for tab, key, allow_actions in [
            (review_tabs[0], "pending", True),
            (review_tabs[1], "duplicates", True),
            (review_tabs[2], "accepted", False),
            (review_tabs[3], "rejected", False),
        ]:
            with tab:
                rows = grouped[key]
                if not rows:
                    st.markdown('<div class="list-note">当前没有候选岗位。</div>', unsafe_allow_html=True)
                    continue
                for row in rows:
                    candidate_id = int(row["id"])
                    st.write(f"**{build_import_candidate_summary(row)}**")
                    st.caption(str(row.get("canonical_url") or row.get("job_url") or ""))
                    main_text = str(row.get("main_text") or "").strip()
                    if main_text:
                        st.text_area("岗位摘要", value=main_text[:800], height=120, disabled=True, key=f"candidate-text-{candidate_id}")
                    if allow_actions:
                        action_col, reason_col = st.columns([0.35, 0.65])
                        with action_col:
                            if st.button("接受", type="primary", key=f"accept-candidate-{candidate_id}"):
                                accept_import_candidate(candidate_id)
                                st.success("已加入岗位池。")
                                st.rerun()
                        with reason_col:
                            reason = st.text_input("拒绝原因", key=f"reject-reason-{candidate_id}", placeholder="不匹配 / 重复 / 薪资不合适")
                            if st.button("拒绝", key=f"reject-candidate-{candidate_id}"):
                                reject_import_candidate(candidate_id, reason)
                                st.success("已拒绝候选岗位。")
                                st.rerun()


def render_weekly_review(review: dict[str, Any]) -> None:
    recommendations = build_weekly_review_recommendations(review)
    st.markdown(
        f"""
        <div class="ops-hero">
            <div class="hero-eyebrow">每周复盘</div>
            <div class="hero-title">{escape(UI_TEXT["weekly_review_title"])}</div>
            <div class="hero-copy">把本周机会、投递、任务和停滞项收束成下一步动作。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric(UI_TEXT["total_jobs"], int(review.get("total_jobs", 0)))
    metric_cols[1].metric(UI_TEXT["todo_jobs"], int(review.get("todo_jobs", 0)))
    metric_cols[2].metric(UI_TEXT["high_priority_jobs"], int(review.get("high_priority_jobs", 0)))
    metric_cols[3].metric(UI_TEXT["applied_jobs"], int(review.get("applied_jobs", 0)))

    left, right = st.columns([1, 1])
    with left:
        render_section_title("建议动作", "优先处理这些事项。")
        for item in recommendations:
            st.markdown(f"- {item}")

        render_section_title("未完成任务", "需要进入日常推进节奏。")
        open_tasks = review.get("open_tasks", []) or []
        if open_tasks:
            st.dataframe(as_frame(open_tasks), hide_index=True, width="stretch")
        else:
            st.markdown('<div class="list-note">当前没有未完成任务。</div>', unsafe_allow_html=True)

    with right:
        render_section_title("投递事件", "观察本周推进结果。")
        event_counts = review.get("application_event_counts", {}) or {}
        if event_counts:
            st.dataframe(
                as_frame(
                    [
                        {
                            "事件": APPLICATION_EVENT_LABELS.get(key, key or "未分类"),
                            "数量": value,
                        }
                        for key, value in event_counts.items()
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
        else:
            st.markdown('<div class="list-note">还没有投递事件记录。</div>', unsafe_allow_html=True)

        render_section_title("停滞岗位", "需要决定推进或归档。")
        stalled_jobs = review.get("stalled_jobs", []) or []
        if stalled_jobs:
            st.dataframe(present_job_rows(stalled_jobs), hide_index=True, width="stretch")
        else:
            st.markdown('<div class="list-note">当前没有明显停滞岗位。</div>', unsafe_allow_html=True)


def render_profile_page(profile: dict[str, str]) -> None:
    snapshot = build_profile_snapshot(profile)
    st.markdown(
        f"""
        <div class="ops-hero">
            <div class="hero-eyebrow">个人求职画像</div>
            <div class="hero-title">{escape(UI_TEXT["profile_title"])}</div>
            <div class="hero-copy">目标、技能、项目亮点和禁投条件会共同决定岗位匹配建议，尽量保持这里的信息清晰、可复核。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_summary_strip(snapshot)

    import_col, keyword_col = st.columns([1.1, 0.9])
    with import_col:
        render_section_title("简历导入", "用现成简历快速补全画像，后续再手动微调。")
        resume_path = st.text_input(
            "简历文件路径",
            value=st.session_state.get("resume_path", "C:/Users/39859/Downloads/倪展鹏-AI产品经理.pdf"),
            key="resume_path",
        )
        if st.button("从简历导入画像", type="secondary"):
            result = import_resume_profile(resume_path)
            st.session_state["imported_resume_excerpt"] = result.get("resume_excerpt", "")
            st.session_state["imported_resume_keywords"] = result.get("keywords", [])
            st.success("已根据简历更新个人画像。")
            st.rerun()
        if st.session_state.get("imported_resume_excerpt"):
            st.text_area("简历提取预览", value=st.session_state["imported_resume_excerpt"], height=180, disabled=True)

    with keyword_col:
        render_section_title("关键词画像", "优先展示最有辨识度的能力词。")
        keywords = st.session_state.get("imported_resume_keywords") or extract_profile_keywords(profile)
        if keywords:
            render_chip_row(keywords)
        else:
            st.markdown('<div class="list-note">当前还没有可提炼的关键词，先补充技能和项目亮点会更有帮助。</div>', unsafe_allow_html=True)

    render_section_title("画像编辑", "这些字段会进入岗位匹配与后续判断。")
    with st.form("candidate-profile-form"):
        left, right = st.columns(2)
        with left:
            target_roles = st.text_input("目标岗位", value=profile.get("target_roles", ""))
            target_cities = st.text_input("目标城市", value=profile.get("target_cities", ""))
            remote_preference = st.text_input("远程偏好", value=profile.get("remote_preference", ""))
            salary_min = st.text_input("薪资最低要求", value=profile.get("salary_min", ""))
            salary_ideal = st.text_input("理想薪资", value=profile.get("salary_ideal", ""))
        with right:
            core_skills = st.text_area("核心技能", value=profile.get("core_skills", ""), height=140)
            project_highlights = st.text_area("项目亮点", value=profile.get("project_highlights", ""), height=140)
            no_go_rules = st.text_area("禁投条件", value=profile.get("no_go_rules", ""), height=110)

        if st.form_submit_button(UI_TEXT["save_profile"], type="primary"):
            save_profile_form(
                {
                    "target_roles": target_roles,
                    "target_cities": target_cities,
                    "remote_preference": remote_preference,
                    "salary_min": salary_min,
                    "salary_ideal": salary_ideal,
                    "core_skills": core_skills,
                    "project_highlights": project_highlights,
                    "no_go_rules": no_go_rules,
                }
            )
            st.success(UI_TEXT["profile_saved"])
            st.rerun()


def render_download() -> None:
    with st.expander("导出与兼容层", expanded=False):
        st.caption(f"{STATUS_TEXT['workbook_caption_prefix']}{DEFAULT_WORKBOOK}")
        if DEFAULT_WORKBOOK.exists():
            with open(DEFAULT_WORKBOOK, "rb") as workbook:
                st.download_button(
                    UI_TEXT["download_excel"],
                    data=workbook.read(),
                    file_name=DEFAULT_WORKBOOK.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )


def main() -> None:
    inject_app_styles()
    page_options = [
        UI_TEXT["nav_home"],
        UI_TEXT["nav_jobs"],
        UI_TEXT["nav_import"],
        UI_TEXT["nav_weekly"],
        UI_TEXT["nav_profile"],
    ]
    current_page = get_active_page(UI_TEXT["nav_home"])
    default_index = page_options.index(current_page) if current_page in page_options else 0
    st.sidebar.markdown("### Chances")
    st.sidebar.caption("本地个人求职工作台")
    page = st.sidebar.radio("页面", page_options, index=default_index)
    set_active_page(page)
    if st.sidebar.button(UI_TEXT["refresh_jobs"]):
        st.rerun()

    health_error: Exception | None = None
    try:
        health = fetch_health()
        api_connected = health.get("status") == "ok"
    except Exception as error:  # pragma: no cover
        health_error = error
        api_connected = False

    render_app_header(page, api_connected)
    render_download()

    if not api_connected:
        render_api_error(health_error or RuntimeError("本地接口未就绪"))
        return

    try:
        jobs = fetch_jobs()
        profile = fetch_profile()
    except Exception as error:  # pragma: no cover
        render_api_error(error)
        return

    if page == UI_TEXT["nav_home"]:
        render_home(jobs, profile)
    elif page == UI_TEXT["nav_jobs"]:
        render_jobs_board(jobs, profile)
    elif page == UI_TEXT["nav_import"]:
        render_search_and_import()
    elif page == UI_TEXT["nav_weekly"]:
        try:
            weekly_review = fetch_weekly_review()
        except Exception as error:  # pragma: no cover
            render_api_error(error)
            return
        render_weekly_review(weekly_review)
    else:
        render_profile_page(profile)


if __name__ == "__main__":
    main()
