import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

from scripts.backup_chances import create_backup, verify_database
from scripts.restore_chances import restore_backup


def create_database(path: Path, job_title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(
            """
            CREATE TABLE jobs (
                id INTEGER PRIMARY KEY,
                job_title TEXT NOT NULL
            );
            CREATE TABLE candidate_profile (
                id INTEGER PRIMARY KEY,
                target_roles TEXT NOT NULL
            );
            CREATE TABLE job_actions (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL
            );
            """
        )
        connection.execute("INSERT INTO jobs (job_title) VALUES (?)", (job_title,))
        connection.execute(
            "INSERT INTO candidate_profile (target_roles) VALUES (?)",
            ("AI产品经理",),
        )
        connection.commit()


def read_job_title(path: Path) -> str:
    with closing(sqlite3.connect(path)) as connection:
        return str(connection.execute("SELECT job_title FROM jobs").fetchone()[0])


def test_create_backup_uses_sqlite_backup_and_copies_captures(tmp_path: Path):
    db_path = tmp_path / "data" / "jobs.db"
    captures_dir = tmp_path / "data" / "captures"
    backup_root = tmp_path / "backups"
    create_database(db_path, "原始岗位")
    captures_dir.mkdir(parents=True)
    (captures_dir / "evidence.png").write_bytes(b"image-data")

    backup_dir = create_backup(
        db_path=db_path,
        captures_dir=captures_dir,
        backup_root=backup_root,
        config_paths=[],
    )

    assert verify_database(backup_dir / "jobs.db")["jobs"] == 1
    assert (backup_dir / "captures" / "evidence.png").read_bytes() == b"image-data"
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["table_counts"]["jobs"] == 1
    assert manifest["capture_files"] == 1


def test_backup_cli_reports_progress_and_completion(tmp_path: Path):
    db_path = tmp_path / "data" / "jobs.db"
    captures_dir = tmp_path / "data" / "captures"
    backup_root = tmp_path / "backups"
    create_database(db_path, "测试岗位")
    captures_dir.mkdir(parents=True)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/backup_chances.py",
            "--db",
            str(db_path),
            "--captures",
            str(captures_dir),
            "--backup-root",
            str(backup_root),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )

    assert result.returncode == 0
    assert "正在检查数据库完整性" in result.stdout
    assert "备份完成，用时" in result.stdout
    assert "备份位置：" in result.stdout


def test_restore_backup_preserves_current_state_before_replacing_it(tmp_path: Path):
    db_path = tmp_path / "data" / "jobs.db"
    captures_dir = tmp_path / "data" / "captures"
    backup_root = tmp_path / "backups"

    create_database(db_path, "备份岗位")
    captures_dir.mkdir(parents=True)
    (captures_dir / "old.png").write_bytes(b"old")
    source_backup = create_backup(
        db_path=db_path,
        captures_dir=captures_dir,
        backup_root=backup_root,
        config_paths=[],
    )

    db_path.unlink()
    create_database(db_path, "当前岗位")
    (captures_dir / "old.png").write_bytes(b"current")

    safety_backup = restore_backup(
        backup_dir=source_backup,
        target_db=db_path,
        target_captures=captures_dir,
        backup_root=backup_root,
        config_targets={},
    )

    assert read_job_title(db_path) == "备份岗位"
    assert (captures_dir / "old.png").read_bytes() == b"old"
    assert safety_backup is not None
    assert read_job_title(safety_backup / "jobs.db") == "当前岗位"


def test_restore_rejects_invalid_backup_without_replacing_current_database(tmp_path: Path):
    db_path = tmp_path / "data" / "jobs.db"
    captures_dir = tmp_path / "data" / "captures"
    backup_root = tmp_path / "backups"
    invalid_backup = tmp_path / "invalid"
    create_database(db_path, "当前岗位")
    invalid_backup.mkdir()
    (invalid_backup / "jobs.db").write_bytes(b"not-a-database")
    (invalid_backup / "manifest.json").write_text("{}", encoding="utf-8")

    try:
        restore_backup(
            backup_dir=invalid_backup,
            target_db=db_path,
            target_captures=captures_dir,
            backup_root=backup_root,
            config_targets={},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid backup must be rejected")

    assert read_job_title(db_path) == "当前岗位"
