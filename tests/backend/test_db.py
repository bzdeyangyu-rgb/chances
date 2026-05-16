from pathlib import Path

from backend.db import initialize_database


def test_initialize_database_creates_core_tables(tmp_path: Path):
    db_path = tmp_path / "jobs.db"

    initialize_database(db_path)

    assert db_path.exists()
