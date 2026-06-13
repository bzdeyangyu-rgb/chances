from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "jobs.db"
DEFAULT_CAPTURES = ROOT / "data" / "captures"
DEFAULT_BACKUP_ROOT = ROOT / "backups"
DEFAULT_CONFIG_PATHS = (ROOT / ".streamlit" / "config.toml",)
REQUIRED_TABLES = {"jobs", "candidate_profile", "job_actions"}


def _table_names(connection: sqlite3.Connection) -> list[str]:
    return [
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]


def verify_database(db_path: Path | str) -> dict[str, int]:
    path = Path(db_path)
    if not path.exists():
        raise ValueError(f"Database does not exist: {path}")

    try:
        with closing(sqlite3.connect(path)) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise ValueError(f"Database integrity check failed: {integrity}")

            table_names = _table_names(connection)
            missing = sorted(REQUIRED_TABLES - set(table_names))
            if missing:
                raise ValueError(f"Database is missing required tables: {', '.join(missing)}")

            counts: dict[str, int] = {}
            for table_name in table_names:
                quoted = table_name.replace('"', '""')
                counts[table_name] = int(
                    connection.execute(f'SELECT COUNT(*) FROM "{quoted}"').fetchone()[0]
                )
            return counts
    except sqlite3.Error as error:
        raise ValueError(f"Invalid SQLite database: {path}") from error


def _backup_database(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source)) as source_connection:
        with closing(sqlite3.connect(destination)) as destination_connection:
            source_connection.backup(destination_connection)


def _count_files(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for path in directory.rglob("*") if path.is_file())


def create_backup(
    db_path: Path | str = DEFAULT_DB,
    captures_dir: Path | str = DEFAULT_CAPTURES,
    backup_root: Path | str = DEFAULT_BACKUP_ROOT,
    config_paths: Iterable[Path | str] = DEFAULT_CONFIG_PATHS,
    prefix: str = "chances",
    progress: Callable[[str], None] | None = None,
) -> Path:
    report = progress or (lambda _message: None)
    database = Path(db_path).resolve()
    captures = Path(captures_dir).resolve()
    root = Path(backup_root).resolve()
    report("正在检查数据库完整性...")
    table_counts = verify_database(database)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_dir = root / f"{prefix}-{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    backup_database = backup_dir / "jobs.db"
    report("正在备份岗位数据库...")
    _backup_database(database, backup_database)
    verify_database(backup_database)

    captures_backup = backup_dir / "captures"
    report("正在备份岗位截图...")
    if captures.exists():
        shutil.copytree(captures, captures_backup)
    else:
        captures_backup.mkdir()

    config_entries: list[dict[str, str]] = []
    report("正在备份本地配置...")
    for config_path in config_paths:
        source = Path(config_path).resolve()
        if not source.exists():
            continue
        try:
            relative = source.relative_to(ROOT)
        except ValueError:
            relative = Path(source.name)
        destination = backup_dir / "config" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        config_entries.append(
            {
                "source": str(source),
                "backup_relative_path": destination.relative_to(backup_dir).as_posix(),
            }
        )

    manifest = {
        "format_version": 1,
        "created_at": datetime.now().astimezone().isoformat(),
        "database": "jobs.db",
        "table_counts": table_counts,
        "capture_files": _count_files(captures_backup),
        "configs": config_entries,
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report("正在完成备份清单...")
    return backup_dir


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="备份求职助手本地数据")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--captures", type=Path, default=DEFAULT_CAPTURES)
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    args = parser.parse_args()

    started_at = time.perf_counter()
    print("开始备份求职助手数据...", flush=True)
    try:
        backup_dir = create_backup(
            db_path=args.db,
            captures_dir=args.captures,
            backup_root=args.backup_root,
            progress=lambda message: print(f"[备份] {message}", flush=True),
        )
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"备份失败：{error}", file=sys.stderr, flush=True)
        return 1

    elapsed = time.perf_counter() - started_at
    print(f"备份完成，用时 {elapsed:.2f} 秒。", flush=True)
    print(f"备份位置：{backup_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
