# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path

try:
    from backend.boss_agent_bridge import boss_agent_available
except ImportError:

    def boss_agent_available() -> bool:
        return shutil.which("boss-agent-cli") is not None


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "jobs.db"
FRONTEND_APP = ROOT / "frontend" / "app.py"
BACKEND_APP = ROOT / "backend" / "server.py"
EXPORT_PATH = ROOT / "data"
CAPTURES_DIR = ROOT / "data" / "captures"
BACKUP_ROOT = ROOT / "backups"
PRACTICAL_PLAN = ROOT / "docs" / "plans" / "2026-06-08-practical-job-hunting-foundation.md"
BOSSZHIPIN_SKILL = ROOT / ".claude" / "skills" / "bosszhipin"
BACKEND_HEALTH_URL = "http://127.0.0.1:8000/api/health"
FRONTEND_URL = "http://127.0.0.1:8501"

WORKFLOW_COUNT_QUERIES = {
    "jobs": "SELECT COUNT(*) FROM jobs",
    "search_presets": "SELECT COUNT(*) FROM search_presets",
    "application_events": "SELECT COUNT(*) FROM application_events",
    "open_tasks": "SELECT COUNT(*) FROM job_tasks WHERE status = 'open'",
    "pending_import_reviews": (
        "SELECT COUNT(*) FROM job_review_decisions WHERE decision = 'pending'"
    ),
}


def _database_status() -> dict[str, object]:
    if not DB_PATH.exists():
        return {"ok": False, "detail": f"数据库文件不存在：{DB_PATH}"}

    try:
        with closing(sqlite3.connect(DB_PATH)) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                return {"ok": False, "detail": f"数据库完整性检查失败：{integrity}"}
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
    except sqlite3.Error as exc:
        return {"ok": False, "detail": f"数据库连接失败或完整性异常：{exc}"}

    required = {"jobs", "candidate_profile", "job_actions"}
    missing = sorted(required - tables)
    if missing:
        return {"ok": False, "detail": f"缺少数据表：{', '.join(missing)}"}
    return {"ok": True, "detail": "数据库完整性和核心表正常"}


def _data_counts_status() -> dict[str, object]:
    if not DB_PATH.exists():
        return {"ok": False, "detail": "database file missing"}

    try:
        with closing(sqlite3.connect(DB_PATH)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            missing_tables = []
            counts = {}
            for name, query in WORKFLOW_COUNT_QUERIES.items():
                table_name = _table_name_from_count_query(query)
                if table_name not in tables:
                    missing_tables.append(table_name)
                    continue
                counts[name] = int(connection.execute(query).fetchone()[0])
    except sqlite3.Error as exc:
        return {"ok": False, "detail": f"database query failed: {exc}"}

    if missing_tables:
        return {
            "ok": False,
            "detail": {"missing_tables": sorted(set(missing_tables)), "counts": counts},
        }
    return {"ok": True, "detail": counts}


def _table_name_from_count_query(query: str) -> str:
    parts = query.split()
    return parts[3] if len(parts) > 3 else ""


def _captures_count_status() -> dict[str, object]:
    if not CAPTURES_DIR.exists():
        return {"ok": True, "detail": 0}
    count = sum(1 for path in CAPTURES_DIR.rglob("*") if path.is_file())
    return {"ok": True, "detail": count}


def _boss_agent_status() -> dict[str, object]:
    if boss_agent_available():
        return {
            "ok": True,
            "available": True,
            "detail": "boss-agent-cli found",
        }
    return {
        "ok": True,
        "available": False,
        "detail": "boss-agent-cli not found (optional)",
    }


def _http_status(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def _runtime_status() -> dict[str, object]:
    backend = _http_status(BACKEND_HEALTH_URL)
    frontend = _http_status(FRONTEND_URL)
    return {
        "ok": backend and frontend,
        "detail": {
            "backend": "ready" if backend else "stopped",
            "frontend": "ready" if frontend else "stopped",
        },
    }


def _writable_directory_status(path: Path) -> dict[str, object]:
    probe_path: Path | None = None
    try:
        path.mkdir(parents=True, exist_ok=True)
        file_descriptor, probe_name = tempfile.mkstemp(prefix=".doctor-", dir=path)
        os.close(file_descriptor)
        probe_path = Path(probe_name)
        probe_path.unlink()
        return {"ok": True, "detail": str(path)}
    except OSError as exc:
        return {"ok": False, "detail": f"{path}: {exc}"}
    finally:
        if probe_path is not None:
            probe_path.unlink(missing_ok=True)


def _backup_status() -> dict[str, object]:
    if not BACKUP_ROOT.exists():
        return {"ok": False, "detail": "尚未创建数据备份"}
    manifests = sorted(
        BACKUP_ROOT.glob("*/manifest.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not manifests:
        return {"ok": False, "detail": "备份目录中没有有效清单"}
    return {"ok": True, "detail": str(manifests[0].parent)}


def _path_status(path: Path) -> dict[str, object]:
    return {"ok": path.exists(), "detail": str(path)}


def _bosszhipin_skill_status() -> dict[str, object]:
    if not BOSSZHIPIN_SKILL.exists():
        return {"ok": True, "available": False, "detail": "optional skill not installed"}

    is_junction = False
    junction_check = getattr(BOSSZHIPIN_SKILL, "is_junction", None)
    if callable(junction_check):
        is_junction = bool(junction_check())

    if is_junction:
        kind = "junction"
    elif BOSSZHIPIN_SKILL.is_symlink():
        kind = "symlink"
    elif BOSSZHIPIN_SKILL.is_dir():
        kind = "directory"
    else:
        kind = "file"
    return {
        "ok": BOSSZHIPIN_SKILL.is_dir(),
        "available": BOSSZHIPIN_SKILL.is_dir(),
        "detail": f"{kind}: {BOSSZHIPIN_SKILL}",
    }


def run_checks() -> dict[str, object]:
    return {
        "database": _database_status(),
        "frontend": {"ok": FRONTEND_APP.exists(), "detail": str(FRONTEND_APP)},
        "api": {"ok": BACKEND_APP.exists(), "detail": str(BACKEND_APP)},
        "export_path": {"ok": EXPORT_PATH.exists(), "detail": str(EXPORT_PATH)},
        "data_writable": _writable_directory_status(EXPORT_PATH),
        "backup": _backup_status(),
        "runtime": _runtime_status(),
        "boss_agent_cli": _boss_agent_status(),
        "data_counts": _data_counts_status(),
        "captures_count": _captures_count_status(),
        "practical_plan": _path_status(PRACTICAL_PLAN),
        "bosszhipin_skill": _bosszhipin_skill_status(),
    }


def core_checks_ok(checks: dict[str, object]) -> bool:
    required = (
        "database",
        "frontend",
        "api",
        "export_path",
        "data_writable",
        "backup",
        "runtime",
        "data_counts",
    )
    return all(bool(checks[name]["ok"]) for name in required)  # type: ignore[index]


def _format_report_detail(name: str, result: dict[str, object]) -> object:
    detail = result.get("detail", "")
    if name == "runtime" and isinstance(detail, dict):
        backend = "正常" if detail.get("backend") == "ready" else "未运行"
        frontend = "正常" if detail.get("frontend") == "ready" else "未运行"
        return f"后端 {backend}，前端 {frontend}"
    if name == "data_counts" and isinstance(detail, dict):
        labels = {
            "jobs": "岗位",
            "search_presets": "搜索预设",
            "application_events": "投递事件",
            "open_tasks": "待办任务",
            "pending_import_reviews": "待审查导入",
        }
        return "，".join(f"{labels.get(key, key)} {value}" for key, value in detail.items())
    if name == "boss_agent_cli":
        return "已安装" if result.get("available") else "未安装，不影响核心功能"
    if name == "bosszhipin_skill":
        return "已安装" if result.get("available") else "未安装，不影响核心功能"
    return detail


def print_report(checks: dict[str, object]) -> None:
    labels = {
        "database": "数据库完整性",
        "frontend": "前端程序",
        "api": "后端程序",
        "export_path": "数据目录",
        "data_writable": "数据写入权限",
        "backup": "最近备份",
        "runtime": "前后端运行状态",
        "boss_agent_cli": "BOSS 导入命令行（可选）",
        "data_counts": "业务数据统计",
        "captures_count": "本地截图数量",
        "practical_plan": "实施文档",
        "bosszhipin_skill": "BOSS 操作技能（可选）",
    }
    print("Chances 健康检查")
    print("=" * 40)
    for name, result in checks.items():
        status = "通过" if result["ok"] else "失败"  # type: ignore[index]
        detail = _format_report_detail(name, result)  # type: ignore[arg-type]
        print(f"[{status}] {labels.get(name, name)}：{detail}")
    print("=" * 40)
    print("核心检查全部通过。" if core_checks_ok(checks) else "核心检查存在失败项。")


if __name__ == "__main__":
    results = run_checks()
    print_report(results)
    raise SystemExit(0 if core_checks_ok(results) else 1)
