from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.db import (
    get_connection,
    get_job_materials,
    list_application_events,
    list_import_review_candidates,
    list_job_tasks,
    list_jobs,
)
from scripts.seed_demo_workflow import build_demo_records


def test_build_demo_records_describes_complete_workflow() -> None:
    records = build_demo_records()

    assert {job["key"] for job in records["jobs"]} == {"high_match", "active_followup"}
    assert {material["job_key"] for material in records["materials"]} == {"high_match"}
    assert {event["job_key"] for event in records["application_events"]} == {
        "high_match",
        "active_followup",
    }
    assert {task["job_key"] for task in records["tasks"]} == {"high_match", "active_followup"}
    assert len(records["import_candidates"]) >= 2
    assert all(candidate["job_url"].startswith("https://") for candidate in records["import_candidates"])


def test_cli_is_dry_run_until_apply_and_db_are_explicit(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.db"

    dry_run = subprocess.run(
        [sys.executable, "scripts/seed_demo_workflow.py", "--db", str(db_path)],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        check=False,
    )

    assert dry_run.returncode == 0
    assert "dry-run" in dry_run.stdout
    assert not db_path.exists()

    apply_run = subprocess.run(
        [sys.executable, "scripts/seed_demo_workflow.py", "--apply", "--db", str(db_path)],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        check=False,
    )

    assert apply_run.returncode == 0
    assert "seeded demo workflow" in apply_run.stdout
    assert db_path.exists()

    jobs = list_jobs(db_path)
    assert len(jobs) == 2

    jobs_by_title = {job["job_title"]: job for job in jobs}
    high_match = jobs_by_title["AI 产品工作流负责人"]
    active_followup = jobs_by_title["AIGC 解决方案顾问"]

    assert get_job_materials(high_match["id"], db_path)["resume_angle"]
    assert list_application_events(high_match["id"], db_path)
    assert list_application_events(active_followup["id"], db_path)
    assert list_job_tasks(db_path, job_id=high_match["id"])
    assert list_job_tasks(db_path, job_id=active_followup["id"])
    assert len(list_import_review_candidates(db_path)) >= 2

    with get_connection(db_path) as connection:
        score_count = connection.execute("SELECT COUNT(*) FROM job_score_snapshots").fetchone()[0]
    assert score_count >= 1
