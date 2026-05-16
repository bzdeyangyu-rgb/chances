# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "jobs.db"
FRONTEND_APP = ROOT / "frontend" / "app.py"
BACKEND_APP = ROOT / "backend" / "server.py"
EXPORT_PATH = ROOT / "data"


def _database_status() -> dict[str, object]:
    if not DB_PATH.exists():
        return {"ok": False, "detail": f"数据库文件不存在：{DB_PATH}"}

    try:
        connection = sqlite3.connect(DB_PATH)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        connection.close()
    except sqlite3.Error as exc:
        return {"ok": False, "detail": f"数据库连接失败：{exc}"}

    required = {"jobs", "candidate_profile", "job_actions"}
    missing = sorted(required - tables)
    if missing:
        return {"ok": False, "detail": f"缺少数据表：{', '.join(missing)}"}
    return {"ok": True, "detail": "数据库和核心表正常"}


def run_checks() -> dict[str, object]:
    return {
        "database": _database_status(),
        "frontend": {"ok": FRONTEND_APP.exists(), "detail": str(FRONTEND_APP)},
        "api": {"ok": BACKEND_APP.exists(), "detail": str(BACKEND_APP)},
        "export_path": {"ok": EXPORT_PATH.exists(), "detail": str(EXPORT_PATH)},
    }


if __name__ == "__main__":
    from pprint import pprint

    pprint(run_checks())
