from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.backup_chances import (
    DEFAULT_BACKUP_ROOT,
    DEFAULT_CAPTURES,
    DEFAULT_DB,
    ROOT,
    create_backup,
    verify_database,
)


def _safe_capture_target(path: Path) -> Path:
    resolved = path.resolve()
    if resolved == Path(resolved.anchor) or resolved == ROOT.resolve():
        raise ValueError(f"Unsafe capture restore target: {resolved}")
    return resolved


def _load_manifest(backup_dir: Path) -> dict[str, object]:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Backup manifest is missing: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError(f"Backup manifest is invalid: {manifest_path}") from error
    if manifest.get("format_version") != 1:
        raise ValueError("Unsupported backup format")
    return manifest


def restore_backup(
    backup_dir: Path | str,
    target_db: Path | str = DEFAULT_DB,
    target_captures: Path | str = DEFAULT_CAPTURES,
    backup_root: Path | str = DEFAULT_BACKUP_ROOT,
    config_targets: dict[str, Path | str] | None = None,
) -> Path | None:
    source_dir = Path(backup_dir).resolve()
    manifest = _load_manifest(source_dir)
    source_database = source_dir / str(manifest.get("database", "jobs.db"))
    source_captures = source_dir / "captures"
    verify_database(source_database)

    database = Path(target_db).resolve()
    captures = _safe_capture_target(Path(target_captures))
    root = Path(backup_root).resolve()

    safety_backup: Path | None = None
    if database.exists():
        safety_backup = create_backup(
            db_path=database,
            captures_dir=captures,
            backup_root=root,
            config_paths=[],
            prefix="pre-restore",
        )

    database.parent.mkdir(parents=True, exist_ok=True)
    temporary_fd, temporary_name = tempfile.mkstemp(
        prefix="chances-restore-",
        suffix=".db",
        dir=database.parent,
    )
    os.close(temporary_fd)
    temporary_database = Path(temporary_name)
    temporary_database.unlink(missing_ok=True)
    shutil.copy2(source_database, temporary_database)
    verify_database(temporary_database)

    temporary_captures = captures.parent / f".captures-restore-{uuid.uuid4().hex}"
    previous_captures = captures.parent / f".captures-previous-{uuid.uuid4().hex}"
    if source_captures.exists():
        shutil.copytree(source_captures, temporary_captures)
    else:
        temporary_captures.mkdir(parents=True)

    captures_moved = False
    try:
        if captures.exists():
            os.replace(captures, previous_captures)
            captures_moved = True
        os.replace(temporary_captures, captures)
        os.replace(temporary_database, database)
        verify_database(database)
    except Exception:
        temporary_database.unlink(missing_ok=True)
        if captures.exists():
            shutil.rmtree(captures)
        if captures_moved and previous_captures.exists():
            os.replace(previous_captures, captures)
        if safety_backup is not None:
            rollback_database = safety_backup / "jobs.db"
            if rollback_database.exists():
                shutil.copy2(rollback_database, database)
        raise
    else:
        if previous_captures.exists():
            shutil.rmtree(previous_captures)

    targets = config_targets or {}
    for entry in manifest.get("configs", []):
        if not isinstance(entry, dict):
            continue
        source_name = str(entry.get("source", ""))
        destination = targets.get(source_name)
        if destination is None:
            continue
        config_backup = source_dir / str(entry.get("backup_relative_path", ""))
        config_target = Path(destination)
        config_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config_backup, config_target)

    return safety_backup


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a Chances local backup")
    parser.add_argument("backup_dir", type=Path)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--captures", type=Path, default=DEFAULT_CAPTURES)
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    if not args.yes:
        parser.error("Restore requires --yes because it replaces the active local database")

    safety_backup = restore_backup(
        backup_dir=args.backup_dir,
        target_db=args.db,
        target_captures=args.captures,
        backup_root=args.backup_root,
        config_targets={},
    )
    print(f"Restored backup: {args.backup_dir.resolve()}")
    if safety_backup is not None:
        print(f"Previous state saved to: {safety_backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
