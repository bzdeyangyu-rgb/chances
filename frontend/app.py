# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
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
    CAPTURE_ASSET_LABELS,
    DEFAULT_PROFILE_FORM,
    PRIORITY_OPTIONS,
    STATUS_OPTIONS,
    STATUS_TEXT,
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


def fetch_jobs() -> list[dict[str, Any]]:
    return api_get("/api/jobs")


def fetch_job_detail(job_id: int) -> dict[str, Any]:
    return api_get(f"/api/jobs/{job_id}")


def fetch_profile() -> dict[str, str]:
    profile = api_get("/api/profile")
    return {**default_profile_form(), **profile}


def fetch_weekly_review() -> dict[str, Any]:
    return api_get("/api/reviews/weekly")


def save_profile_form(payload: dict[str, Any]) -> dict[str, Any]:
    return api_post("/api/profile", payload)


def import_resume_profile(resume_path: str) -> dict[str, Any]:
    return api_post("/api/profile/import-resume", {"resume_path": resume_path})


def save_job_status(job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return api_post(f"/api/jobs/{job_id}/status", payload)


def save_bulk_job_status(payload: dict[str, Any]) -> dict[str, Any]:
    return api_post("/api/jobs/bulk-status", payload)


def render_api_error(error: Exception) -> None:
    st.error(UI_TEXT["api_error"])
    st.caption(str(error))


def inject_app_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --surface: rgba(255, 252, 247, 0.92);
            --surface-strong: #fffdf9;
            --border: rgba(126, 92, 69, 0.14);
            --text: #1f2937;
            --muted: #6b7280;
            --accent: #0f766e;
            --accent-soft: rgba(15, 118, 110, 0.12);
            --warm: #d97706;
            --shadow: 0 18px 40px rgba(104, 74, 50, 0.08);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(217, 119, 6, 0.08), transparent 28%),
                radial-gradient(circle at top right, rgba(15, 118, 110, 0.12), transparent 26%),
                linear-gradient(180deg, #fbf8f2 0%, #f4ede3 100%);
            color: var(--text);
        }

        [data-testid="stSidebar"] {
            background: rgba(255, 251, 245, 0.86);
            border-right: 1px solid var(--border);
        }

        .hero-card {
            background: linear-gradient(135deg, #12343b 0%, #205c61 46%, #d97706 100%);
            color: #fffdf8;
            border-radius: 26px;
            padding: 1.6rem 1.7rem;
            box-shadow: 0 22px 50px rgba(18, 52, 59, 0.22);
            margin-bottom: 1rem;
        }

        .hero-eyebrow {
            font-size: 0.82rem;
            letter-spacing: 0.08em;
            opacity: 0.78;
            text-transform: uppercase;
        }

        .hero-title {
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.18;
            margin: 0.35rem 0 0.5rem;
        }

        .hero-copy {
            font-size: 0.98rem;
            max-width: 56rem;
            color: rgba(255, 250, 240, 0.92);
        }

        .entry-card, .metric-card, .panel-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 22px;
            box-shadow: var(--shadow);
            padding: 1.1rem 1.2rem;
            backdrop-filter: blur(10px);
        }

        .metric-card {
            background: var(--surface-strong);
            min-height: 118px;
        }

        .entry-title, .section-title {
            font-size: 1.14rem;
            font-weight: 800;
            color: #13232f;
            margin: 0 0 0.35rem;
        }

        .entry-copy, .section-copy {
            color: var(--muted);
            font-size: 0.93rem;
        }

        .metric-label {
            font-size: 0.86rem;
            color: var(--muted);
        }

        .metric-value {
            font-size: 2rem;
            line-height: 1;
            font-weight: 800;
            margin-top: 0.65rem;
            color: var(--text);
        }

        .metric-hint {
            font-size: 0.86rem;
            color: var(--muted);
            margin-top: 0.55rem;
        }

        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin: 0.3rem 0 0.2rem;
        }

        .chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.42rem 0.72rem;
            border-radius: 999px;
            background: var(--accent-soft);
            color: var(--accent);
            font-size: 0.86rem;
            font-weight: 600;
        }

        .chip.warm {
            background: rgba(217, 119, 6, 0.12);
            color: #b45309;
        }

        .list-note {
            background: rgba(255, 255, 255, 0.72);
            border: 1px dashed rgba(126, 92, 69, 0.25);
            border-radius: 16px;
            padding: 0.85rem 1rem;
            color: var(--muted);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(title: str, copy: str = "") -> None:
    st.markdown(f'<div class="section-title">{escape(title)}</div>', unsafe_allow_html=True)
    if copy:
        st.markdown(f'<div class="section-copy">{escape(copy)}</div>', unsafe_allow_html=True)


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


def render_home(jobs: list[dict[str, Any]], profile: dict[str, str]) -> None:
    metrics = build_home_metrics(jobs)
    snapshot = build_profile_snapshot(profile)
    actions = build_entry_actions(metrics, profile)

    headline = profile.get("target_roles") or "先完善你的求职方向"
    city = profile.get("target_cities") or "城市待补充"
    salary = profile.get("salary_min") or "薪资底线待补充"

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-eyebrow">今日入口</div>
            <div class="hero-title">围绕 {escape(headline)} 的求职入口</div>
            <div class="hero-copy">
                当前重点城市是 <strong>{escape(city)}</strong>，最低薪资预期为 <strong>{escape(salary)}</strong>。
                这里先帮你判断今天该去哪一页、先推进什么，再进入具体操作。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_cols = st.columns(3)
    for index, action in enumerate(actions):
        with action_cols[index]:
            st.markdown(
                f"""
                <div class="entry-card">
                    <div class="entry-title">{escape(action['title'])}</div>
                    <div class="entry-copy">{escape(action['copy'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"进入{action['target_page']}", key=f"entry-{index}", use_container_width=True):
                set_active_page(action["target_page"])
                st.rerun()

    render_chip_row([f"{label}：{value}" for label, value in snapshot], warm=True)

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


def render_job_detail_panel(detail: dict[str, Any]) -> None:
    job = detail["job"]
    evaluation = detail.get("evaluation")
    timeline = detail.get("timeline", [])
    capture_assets = present_capture_assets(detail.get("assets", []))
    profile_match = detail.get("profile_match")

    render_section_title(UI_TEXT["job_detail_title"], f"{job.get('company_name', '公司待补充')} · {job.get('job_title', '岗位待补充')}")
    render_chip_row(
        [
            job.get("platform_label", "未知来源"),
            job.get("salary_raw", "薪资待补充"),
            job.get("location", "地点待补充"),
            job.get("status", "状态待补充"),
        ]
    )

    st.write(f"**优先级：** {job.get('priority', '普通')}")
    st.write(f"**下一步动作：** {job.get('next_action', '待补充')}")

    if job.get("visual_summary"):
        st.text_area("视觉提要", value=job["visual_summary"], height=180, disabled=True)
    if job.get("main_text"):
        st.text_area("岗位正文", value=job["main_text"], height=220, disabled=True)

    if capture_assets:
        render_section_title("页面证据", "保留原始截图，方便核对提取质量。")
        tabs = st.tabs([asset["label"] for asset in capture_assets])
        for tab, asset in zip(tabs, capture_assets):
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


def render_jobs_board(jobs: list[dict[str, Any]]) -> None:
    render_section_title(UI_TEXT["jobs_board_title"], "筛选、批量推进和详情判断都在这里完成。")
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

    bulk_rows = [{"selected": False, **row} for row in filtered]
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
        render_section_title("批量更新", "适合统一标记一组岗位的推进动作。")
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
        for row in filtered
    }
    selected_label = st.selectbox("选择要查看和更新的岗位", list(job_options.keys()))
    selected_job_id = job_options[selected_label]

    detail = fetch_job_detail(int(selected_job_id))
    selected_job = detail["job"]
    edit_col, detail_col = st.columns([0.92, 1.25])
    with edit_col:
        render_section_title("状态更新", "左边负责推进动作，右边负责判断。")
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
        render_job_detail_panel(detail)


def render_profile_page(profile: dict[str, str]) -> None:
    render_section_title(UI_TEXT["profile_title"], "把目标、技能和边界条件说明白，岗位判断会更稳。")
    snapshot = build_profile_snapshot(profile)
    render_chip_row([f"{label}：{value}" for label, value in snapshot], warm=True)

    import_col, keyword_col = st.columns([1.1, 0.9])
    with import_col:
        render_section_title("从简历导入", "用现成简历快速补全画像，后续再手动微调。")
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
    st.title(UI_TEXT["page_title"])
    render_download()

    page_options = [UI_TEXT["nav_home"], UI_TEXT["nav_jobs"], UI_TEXT["nav_profile"]]
    current_page = get_active_page(UI_TEXT["nav_home"])
    default_index = page_options.index(current_page) if current_page in page_options else 0
    page = st.sidebar.radio("页面", page_options, index=default_index)
    set_active_page(page)
    if st.sidebar.button(UI_TEXT["refresh_jobs"]):
        st.rerun()

    try:
        jobs = fetch_jobs()
        profile = fetch_profile()
    except Exception as error:  # pragma: no cover
        render_api_error(error)
        return

    if page == UI_TEXT["nav_home"]:
        render_home(jobs, profile)
    elif page == UI_TEXT["nav_jobs"]:
        render_jobs_board(jobs)
    else:
        render_profile_page(profile)


if __name__ == "__main__":
    main()
