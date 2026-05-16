# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import binascii
import mimetypes
import sqlite3
from pathlib import Path
from typing import Any

from backend.browser_import import canonicalize_job_url, normalize_main_text, normalize_text


DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "jobs.db"
DEFAULT_CAPTURES_DIR = Path(__file__).resolve().parents[1] / "data" / "captures"
DEFAULT_STATUS = "待评估"
DEFAULT_PRIORITY = "普通"
DEFAULT_NEXT_ACTION = "补充岗位信息并完成评估"
PLATFORM_LABELS = {
    "boss": "Boss直聘",
    "zhipin": "Boss直聘",
    "liepin": "猎聘",
    "lagou": "拉勾",
    "zhaopin": "智联招聘",
    "manual": "手动录入",
}
CAPTURE_ASSET_LABELS = {
    "visible": "页面截图",
    "hero": "岗位摘要截图",
    "description": "职位描述截图",
    "company": "公司信息截图",
    "fullpage": "整页截图",
}
DEFAULT_PROFILE = {
    "target_roles": "AI产品经理、AI应用工程师、AIGC产品/工作流相关岗位",
    "target_cities": "南京",
    "remote_preference": "可接受远程或混合办公，但优先南京本地机会",
    "salary_min": "15K/月，优秀前景岗位可接受 10K 起步",
    "salary_ideal": "15K-22K/月",
    "core_skills": (
        "AI产品规划与落地、AIGC工作流设计、UE5/Maya 场景与地编流程、"
        "Codex/Claude Code 辅助开发、3DGS/AI视频工作流调研、复杂项目统筹、"
        "建筑/城市综合体方案设计、BIM/CAD"
    ),
    "project_highlights": (
        "将 AI 接入 UE5 地编与美术管线并沉淀 SOP；"
        "主笔《AI效能与业务拓展报告》，提出 3DGS + UE5 + AI视频模型 三阶段路线；"
        "交付多个次世代游戏关卡并解决材质融合 Bug；"
        "主导许昌 190万㎡与溧阳长山等大型项目统筹。"
    ),
    "no_go_rules": "与 AI 应用/产品方向明显无关、长期缺乏成长空间、薪资长期低于 10K 且无清晰上升路径的岗位",
}
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
JOB_FIELDS = (
    "platform",
    "job_title",
    "company_name",
    "salary_raw",
    "location",
    "education",
    "experience",
    "financing_stage",
    "company_size",
    "industry",
    "benefits",
    "published_at",
    "job_url",
    "skills",
    "main_text",
    "status",
    "priority",
    "next_action",
    "notes",
    "source_type",
    "capture_mode",
    "visual_summary",
    "visual_summary_status",
    "raw_capture_title",
)
JOB_SELECT_FIELDS = (
    "id",
    "platform",
    "job_title",
    "company_name",
    "salary_raw",
    "location",
    "education",
    "experience",
    "financing_stage",
    "company_size",
    "industry",
    "benefits",
    "published_at",
    "job_url",
    "skills",
    "main_text",
    "status",
    "priority",
    "next_action",
    "notes",
    "source_type",
    "capture_mode",
    "visual_summary",
    "visual_summary_status",
    "raw_capture_title",
    "created_at",
    "updated_at",
)


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_jobs_columns(connection: sqlite3.Connection) -> None:
    existing_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
    }
    required_columns = {
        "capture_mode": "TEXT NOT NULL DEFAULT 'dom'",
        "visual_summary": "TEXT NOT NULL DEFAULT ''",
        "visual_summary_status": "TEXT NOT NULL DEFAULT 'pending'",
        "raw_capture_title": "TEXT NOT NULL DEFAULT ''",
    }
    for name, ddl in required_columns.items():
        if name not in existing_columns:
            connection.execute(f"ALTER TABLE jobs ADD COLUMN {name} {ddl}")


def _ensure_capture_asset_columns(connection: sqlite3.Connection) -> None:
    existing_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(job_capture_assets)").fetchall()
    }
    if "excerpt" not in existing_columns:
        connection.execute("ALTER TABLE job_capture_assets ADD COLUMN excerpt TEXT NOT NULL DEFAULT ''")


def initialize_database(db_path: Path | str = DEFAULT_DB_PATH) -> Path:
    path = Path(db_path)

    with get_connection(path) as connection:
        connection.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS candidate_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                target_roles TEXT NOT NULL DEFAULT '',
                target_cities TEXT NOT NULL DEFAULT '',
                remote_preference TEXT NOT NULL DEFAULT '',
                salary_min TEXT NOT NULL DEFAULT '',
                salary_ideal TEXT NOT NULL DEFAULT '',
                core_skills TEXT NOT NULL DEFAULT '',
                project_highlights TEXT NOT NULL DEFAULT '',
                no_go_rules TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            INSERT INTO candidate_profile (id)
            VALUES (1)
            ON CONFLICT(id) DO NOTHING;

            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL DEFAULT '',
                job_title TEXT NOT NULL DEFAULT '',
                company_name TEXT NOT NULL DEFAULT '',
                salary_raw TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL DEFAULT '',
                education TEXT NOT NULL DEFAULT '',
                experience TEXT NOT NULL DEFAULT '',
                financing_stage TEXT NOT NULL DEFAULT '',
                company_size TEXT NOT NULL DEFAULT '',
                industry TEXT NOT NULL DEFAULT '',
                benefits TEXT NOT NULL DEFAULT '',
                published_at TEXT NOT NULL DEFAULT '',
                job_url TEXT NOT NULL UNIQUE,
                skills TEXT NOT NULL DEFAULT '',
                main_text TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '{DEFAULT_STATUS}',
                priority TEXT NOT NULL DEFAULT '{DEFAULT_PRIORITY}',
                next_action TEXT NOT NULL DEFAULT '{DEFAULT_NEXT_ACTION}',
                notes TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'manual',
                capture_mode TEXT NOT NULL DEFAULT 'dom',
                visual_summary TEXT NOT NULL DEFAULT '',
                visual_summary_status TEXT NOT NULL DEFAULT 'pending',
                raw_capture_title TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS job_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT '',
                next_action TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS job_evaluations (
                job_id INTEGER PRIMARY KEY,
                match_score INTEGER NOT NULL DEFAULT 0,
                recommendation TEXT NOT NULL DEFAULT '',
                reasoning TEXT NOT NULL DEFAULT '',
                highlights TEXT NOT NULL DEFAULT '',
                risks TEXT NOT NULL DEFAULT '',
                next_step_hint TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS job_capture_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                asset_type TEXT NOT NULL DEFAULT 'visible',
                file_path TEXT NOT NULL DEFAULT '',
                mime_type TEXT NOT NULL DEFAULT 'image/png',
                excerpt TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );
            """
        )
        _ensure_jobs_columns(connection)
        _ensure_capture_asset_columns(connection)

    ensure_default_profile(db_path)
    return path


def ensure_default_profile(db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, str]:
    path = Path(db_path)
    if not path.exists():
        initialize_database(path)

    with get_connection(path) as connection:
        row = connection.execute(
            f"SELECT {', '.join(PROFILE_FIELDS)} FROM candidate_profile WHERE id = 1"
        ).fetchone()
        current = {field: normalize_text(row[field] if row else "") for field in PROFILE_FIELDS}
        if any(current.values()):
            return current

        assignments = ", ".join(f"{field} = ?" for field in PROFILE_FIELDS)
        connection.execute(
            f"""
            UPDATE candidate_profile
            SET {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            [DEFAULT_PROFILE[field] for field in PROFILE_FIELDS],
        )
    return DEFAULT_PROFILE.copy()


def load_profile(db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, str]:
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        row = connection.execute(
            f"SELECT {', '.join(PROFILE_FIELDS)} FROM candidate_profile WHERE id = 1"
        ).fetchone()

    if row is None:
        return DEFAULT_PROFILE.copy()
    return {field: str(row[field] or "") for field in PROFILE_FIELDS}


def save_profile(payload: dict[str, str], db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, str]:
    initialize_database(db_path)
    normalized = {field: str(payload.get(field, "") or "") for field in PROFILE_FIELDS}

    with get_connection(db_path) as connection:
        assignments = ", ".join(f"{field} = ?" for field in PROFILE_FIELDS)
        connection.execute(
            f"""
            UPDATE candidate_profile
            SET {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            [normalized[field] for field in PROFILE_FIELDS],
        )

    return normalized


def normalize_job_payload(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "platform": normalize_text(payload.get("platform")),
        "job_title": normalize_text(payload.get("job_title")),
        "company_name": normalize_text(payload.get("company_name")),
        "salary_raw": normalize_text(payload.get("salary_raw")),
        "location": normalize_text(payload.get("location")),
        "education": normalize_text(payload.get("education")),
        "experience": normalize_text(payload.get("experience")),
        "financing_stage": normalize_text(payload.get("financing_stage")),
        "company_size": normalize_text(payload.get("company_size")),
        "industry": normalize_text(payload.get("industry")),
        "benefits": normalize_text(payload.get("benefits")),
        "published_at": normalize_text(payload.get("published_at")),
        "job_url": canonicalize_job_url(payload.get("job_url", "")),
        "skills": normalize_text(payload.get("skills")),
        "main_text": normalize_main_text(payload.get("main_text")),
        "status": normalize_text(payload.get("status")) or DEFAULT_STATUS,
        "priority": normalize_text(payload.get("priority")) or DEFAULT_PRIORITY,
        "next_action": normalize_text(payload.get("next_action")) or DEFAULT_NEXT_ACTION,
        "notes": normalize_text(payload.get("notes")),
        "source_type": normalize_text(payload.get("source_type")) or "manual",
        "capture_mode": normalize_text(payload.get("capture_mode")) or "dom",
        "visual_summary": normalize_text(payload.get("visual_summary")),
        "visual_summary_status": normalize_text(payload.get("visual_summary_status")) or "pending",
        "raw_capture_title": normalize_text(payload.get("raw_capture_title")),
    }


def _job_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    platform = normalize_text(row["platform"])
    return {
        "id": row["id"],
        "platform": platform,
        "platform_label": PLATFORM_LABELS.get(platform, platform or "未知来源"),
        "job_title": normalize_text(row["job_title"]),
        "company_name": normalize_text(row["company_name"]),
        "salary_raw": normalize_text(row["salary_raw"]),
        "location": normalize_text(row["location"]),
        "education": normalize_text(row["education"]),
        "experience": normalize_text(row["experience"]),
        "financing_stage": normalize_text(row["financing_stage"]),
        "company_size": normalize_text(row["company_size"]),
        "industry": normalize_text(row["industry"]),
        "benefits": normalize_text(row["benefits"]),
        "published_at": normalize_text(row["published_at"]),
        "job_url": normalize_text(row["job_url"]),
        "skills": normalize_text(row["skills"]),
        "main_text": normalize_main_text(row["main_text"]),
        "status": normalize_text(row["status"]),
        "priority": normalize_text(row["priority"]),
        "next_action": normalize_text(row["next_action"]),
        "notes": normalize_text(row["notes"]),
        "source_type": normalize_text(row["source_type"]),
        "capture_mode": normalize_text(row["capture_mode"]),
        "visual_summary": normalize_text(row["visual_summary"]),
        "visual_summary_status": normalize_text(row["visual_summary_status"]),
        "raw_capture_title": normalize_text(row["raw_capture_title"]),
        "created_at": normalize_text(row["created_at"]),
        "updated_at": normalize_text(row["updated_at"]),
    }


def list_jobs(db_path: Path | str = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT {', '.join(JOB_SELECT_FIELDS)}
            FROM jobs
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()

    return [_job_row_to_dict(row) for row in rows]


def get_job(job_id: int, db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        row = connection.execute(
            f"""
            SELECT {', '.join(JOB_SELECT_FIELDS)}
            FROM jobs
            WHERE id = ?
            """,
            (job_id,),
        ).fetchone()

    return _job_row_to_dict(row) if row else None


def list_job_actions(job_id: int, db_path: Path | str = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, job_id, status, next_action, note, created_at
            FROM job_actions
            WHERE job_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (job_id,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "job_id": row["job_id"],
            "status": normalize_text(row["status"]),
            "next_action": normalize_text(row["next_action"]),
            "note": normalize_text(row["note"]),
            "created_at": normalize_text(row["created_at"]),
        }
        for row in rows
    ]


def get_job_evaluation(job_id: int, db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT job_id, match_score, recommendation, reasoning, highlights, risks,
                   next_step_hint, updated_at
            FROM job_evaluations
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

    if row is None:
        return None
    return {
        "job_id": row["job_id"],
        "match_score": int(row["match_score"]),
        "recommendation": normalize_text(row["recommendation"]),
        "reasoning": normalize_text(row["reasoning"]),
        "highlights": normalize_text(row["highlights"]),
        "risks": normalize_text(row["risks"]),
        "next_step_hint": normalize_text(row["next_step_hint"]),
        "updated_at": normalize_text(row["updated_at"]),
    }


def save_job_evaluation(job_id: int, payload: dict[str, Any], db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    initialize_database(db_path)

    normalized = {
        "match_score": int(payload.get("match_score", 0) or 0),
        "recommendation": normalize_text(payload.get("recommendation")),
        "reasoning": normalize_text(payload.get("reasoning")),
        "highlights": normalize_text(payload.get("highlights")),
        "risks": normalize_text(payload.get("risks")),
        "next_step_hint": normalize_text(payload.get("next_step_hint")),
    }

    with get_connection(db_path) as connection:
        existing_job = connection.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if existing_job is None:
            return None

        connection.execute(
            """
            INSERT INTO job_evaluations (
                job_id, match_score, recommendation, reasoning, highlights, risks, next_step_hint
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                match_score = excluded.match_score,
                recommendation = excluded.recommendation,
                reasoning = excluded.reasoning,
                highlights = excluded.highlights,
                risks = excluded.risks,
                next_step_hint = excluded.next_step_hint,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                job_id,
                normalized["match_score"],
                normalized["recommendation"],
                normalized["reasoning"],
                normalized["highlights"],
                normalized["risks"],
                normalized["next_step_hint"],
            ),
        )

    return get_job_evaluation(job_id, db_path)


def add_job_action(
    job_id: int,
    status: str,
    next_action: str,
    note: str = "",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO job_actions (job_id, status, next_action, note)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, normalize_text(status), normalize_text(next_action), normalize_text(note)),
        )
        row = connection.execute(
            """
            SELECT id, job_id, status, next_action, note, created_at
            FROM job_actions
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "status": normalize_text(row["status"]),
        "next_action": normalize_text(row["next_action"]),
        "note": normalize_text(row["note"]),
        "created_at": normalize_text(row["created_at"]),
    }


def update_job_status(
    job_id: int,
    status: str,
    next_action: str,
    note: str = "",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    initialize_database(db_path)
    normalized_status = normalize_text(status) or DEFAULT_STATUS
    normalized_next_action = normalize_text(next_action) or DEFAULT_NEXT_ACTION
    normalized_note = normalize_text(note)

    with get_connection(db_path) as connection:
        existing = connection.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if existing is None:
            return None

        connection.execute(
            """
            UPDATE jobs
            SET status = ?,
                next_action = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (normalized_status, normalized_next_action, job_id),
        )
        connection.execute(
            """
            INSERT INTO job_actions (job_id, status, next_action, note)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, normalized_status, normalized_next_action, normalized_note),
        )

    return get_job(job_id, db_path)


def bulk_update_job_status(
    job_ids: list[int],
    status: str,
    next_action: str,
    note: str = "",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    updated_jobs: list[dict[str, Any]] = []

    for job_id in job_ids:
        updated = update_job_status(job_id, status, next_action, note, db_path)
        if updated is not None:
            updated_jobs.append(updated)

    return {
        "updated_count": len(updated_jobs),
        "job_ids": [job["id"] for job in updated_jobs],
    }


def build_weekly_review(db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, Any]:
    jobs = list_jobs(db_path)
    status_counts: dict[str, int] = {}
    for job in jobs:
        status = str(job.get("status", "") or "未分类")
        status_counts[status] = status_counts.get(status, 0) + 1

    todo_statuses = {"待评估", "建议推进", "待准备材料", "待沟通", "待投递"}
    return {
        "total_jobs": len(jobs),
        "todo_jobs": sum(1 for job in jobs if job.get("status") in todo_statuses),
        "applied_jobs": sum(1 for job in jobs if job.get("status") == "已投递"),
        "high_priority_jobs": sum(1 for job in jobs if job.get("priority") == "高"),
        "status_counts": status_counts,
    }


def build_visual_summary(job: dict[str, Any], screenshots: list[dict[str, Any]] | None = None) -> str:
    description_excerpt = ""
    company_excerpt = ""
    visible_excerpt = ""
    for shot in screenshots or []:
        asset_type = normalize_text(shot.get("asset_type"))
        excerpt = normalize_text(shot.get("text_excerpt") or shot.get("excerpt"))
        if not excerpt:
            continue
        if asset_type == "description" and not description_excerpt:
            description_excerpt = excerpt
        elif asset_type == "company" and not company_excerpt:
            company_excerpt = excerpt
        elif asset_type == "visible" and not visible_excerpt:
            visible_excerpt = excerpt

    role_summary = " / ".join(
        part
        for part in [
            normalize_text(job.get("job_title")),
            normalize_text(job.get("salary_raw")),
            normalize_text(job.get("location")),
            normalize_text(job.get("experience")),
            normalize_text(job.get("education")),
        ]
        if part
    )

    company_summary = company_excerpt or " / ".join(
        part
        for part in [
            normalize_text(job.get("company_name")),
            normalize_text(job.get("financing_stage")),
            normalize_text(job.get("company_size")),
            normalize_text(job.get("industry")),
        ]
        if part
    )

    detail_summary = description_excerpt or visible_excerpt or ""
    if not detail_summary and normalize_text(job.get("main_text")):
        detail_summary = normalize_main_text(job.get("main_text")).splitlines()[0]

    lines = []
    if role_summary:
        lines.append(f"岗位摘要：{role_summary}")
    if detail_summary:
        lines.append(f"职位描述：{detail_summary}")
    if company_summary:
        lines.append(f"公司信息：{company_summary}")
    if normalize_text(job.get("benefits")):
        lines.append(f"福利亮点：{normalize_text(job.get('benefits'))}")
    lines.append("查看建议：请结合页面截图核对完整岗位原文。")
    return "\n".join(lines)


def list_job_capture_assets(job_id: int, db_path: Path | str = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    initialize_database(db_path)
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, job_id, asset_type, file_path, mime_type, excerpt, created_at
            FROM job_capture_assets
            WHERE job_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (job_id,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "job_id": row["job_id"],
            "asset_type": normalize_text(row["asset_type"]),
            "label": CAPTURE_ASSET_LABELS.get(normalize_text(row["asset_type"]), "岗位截图"),
            "file_path": normalize_text(row["file_path"]),
            "mime_type": normalize_text(row["mime_type"]),
            "excerpt": normalize_text(row["excerpt"]),
            "created_at": normalize_text(row["created_at"]),
        }
        for row in rows
    ]


def _decode_data_url(data_url: str) -> tuple[bytes, str]:
    if not data_url.startswith("data:") or "," not in data_url:
        raise ValueError("截图数据格式不正确")
    header, encoded = data_url.split(",", 1)
    mime_type = header.split(";", 1)[0].replace("data:", "").strip() or "image/png"
    try:
        payload = base64.b64decode(encoded)
    except binascii.Error as exc:
        raise ValueError("截图数据无法解析") from exc
    return payload, mime_type


def save_job_capture_assets(
    job_id: int,
    screenshots: list[dict[str, Any]],
    db_path: Path | str = DEFAULT_DB_PATH,
    captures_dir: Path | str = DEFAULT_CAPTURES_DIR,
) -> list[dict[str, Any]]:
    initialize_database(db_path)
    root = Path(captures_dir) / str(job_id)
    root.mkdir(parents=True, exist_ok=True)

    saved_assets: list[dict[str, Any]] = []
    with get_connection(db_path) as connection:
        for index, shot in enumerate(screenshots, start=1):
            data_url = str(shot.get("data_url") or "")
            if not data_url:
                continue
            binary, mime_type = _decode_data_url(data_url)
            asset_type = normalize_text(shot.get("asset_type")) or "visible"
            suffix = mimetypes.guess_extension(mime_type) or ".png"
            file_path = root / f"{asset_type}-{index}{suffix}"
            file_path.write_bytes(binary)
            cursor = connection.execute(
                """
                INSERT INTO job_capture_assets (job_id, asset_type, file_path, mime_type, excerpt)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    asset_type,
                    str(file_path),
                    mime_type,
                    normalize_text(shot.get("text_excerpt")),
                ),
            )
            saved_assets.append(
                {
                    "id": int(cursor.lastrowid),
                    "job_id": job_id,
                    "asset_type": asset_type,
                    "label": CAPTURE_ASSET_LABELS.get(asset_type, "岗位截图"),
                    "file_path": str(file_path),
                    "mime_type": mime_type,
                    "excerpt": normalize_text(shot.get("text_excerpt")),
                }
            )
    return saved_assets


def upsert_job_record(payload: dict[str, Any], db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, str | int]:
    initialize_database(db_path)
    normalized = normalize_job_payload(payload)

    with get_connection(db_path) as connection:
        existing = connection.execute(
            "SELECT id, * FROM jobs WHERE job_url = ?",
            (normalized["job_url"],),
        ).fetchone()

        if existing is None:
            columns = ", ".join(JOB_FIELDS)
            placeholders = ", ".join("?" for _ in JOB_FIELDS)
            cursor = connection.execute(
                f"INSERT INTO jobs ({columns}) VALUES ({placeholders})",
                [normalized[field] for field in JOB_FIELDS],
            )
            return {"id": int(cursor.lastrowid), "result": "created", "job_url": normalized["job_url"]}

        unchanged = all(normalize_text(existing[field]) == normalized[field] for field in JOB_FIELDS)
        if unchanged:
            return {"id": int(existing["id"]), "result": "duplicate", "job_url": normalized["job_url"]}

        assignments = ", ".join(f"{field} = ?" for field in JOB_FIELDS)
        connection.execute(
            f"""
            UPDATE jobs
            SET {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            [normalized[field] for field in JOB_FIELDS] + [existing["id"]],
        )
        return {"id": int(existing["id"]), "result": "updated", "job_url": normalized["job_url"]}
