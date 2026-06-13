import sqlite3
from pathlib import Path

import scripts.doctor as doctor
from backend.db import initialize_database


def test_run_checks_reports_required_services():
    result = doctor.run_checks()

    assert "database" in result
    assert "frontend" in result
    assert "runtime" in result
    assert "backup" in result
    assert "data_writable" in result


def test_doctor_reports_boss_bridge_and_workflow_state(
    tmp_path: Path, monkeypatch
):
    db_path = tmp_path / "jobs.db"
    captures_dir = tmp_path / "captures"
    plan_path = tmp_path / "docs" / "plans" / "2026-06-08-practical-job-hunting-foundation.md"
    boss_skill_path = tmp_path / ".claude" / "skills" / "bosszhipin"

    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO jobs (platform, job_title, company_name, job_url, status)
            VALUES ('boss', 'AI product manager', 'Example Tech', 'https://example.test/job', 'watching')
            """
        )
        job_id = connection.execute("SELECT id FROM jobs").fetchone()[0]
        connection.execute(
            "INSERT INTO job_capture_assets (job_id, asset_type, file_path) VALUES (?, 'visible', ?)",
            (job_id, str(captures_dir / "1" / "visible.png")),
        )
        connection.execute(
            "INSERT INTO application_events (job_id, event_type, channel) VALUES (?, 'applied', 'BOSS')",
            (job_id,),
        )
        connection.execute(
            "INSERT INTO job_tasks (job_id, title, status) VALUES (?, 'Follow up HR', 'open')",
            (job_id,),
        )
        connection.execute(
            "INSERT INTO search_presets (name, platform, city, query) VALUES ('BOSS PM', 'boss', 'Hangzhou', 'product manager')"
        )
        connection.execute(
            "INSERT INTO job_import_events (source) VALUES ('boss_agent')"
        )
        import_event_id = connection.execute("SELECT id FROM job_import_events").fetchone()[0]
        connection.execute(
            """
            INSERT INTO job_review_decisions (import_event_id, source, decision)
            VALUES (?, 'boss_agent', 'pending')
            """,
            (import_event_id,),
        )

    captures_dir.mkdir()
    (captures_dir / "1").mkdir()
    (captures_dir / "1" / "visible.png").write_bytes(b"png")
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text("# plan", encoding="utf-8")
    boss_skill_path.parent.mkdir(parents=True)
    boss_skill_path.mkdir()

    monkeypatch.setattr(doctor, "DB_PATH", db_path)
    monkeypatch.setattr(doctor, "CAPTURES_DIR", captures_dir)
    monkeypatch.setattr(doctor, "PRACTICAL_PLAN", plan_path)
    monkeypatch.setattr(doctor, "BOSSZHIPIN_SKILL", boss_skill_path)
    monkeypatch.setattr(doctor, "boss_agent_available", lambda: True)

    result = doctor.run_checks()

    assert result["boss_agent_cli"] == {
        "ok": True,
        "available": True,
        "detail": "boss-agent-cli found",
    }
    assert result["data_counts"]["ok"] is True
    assert result["data_counts"]["detail"] == {
        "jobs": 1,
        "search_presets": 1,
        "application_events": 1,
        "open_tasks": 1,
        "pending_import_reviews": 1,
    }
    assert result["captures_count"] == {"ok": True, "detail": 1}
    assert result["practical_plan"]["ok"] is True
    assert result["bosszhipin_skill"]["ok"] is True
    assert "directory" in result["bosszhipin_skill"]["detail"]


def test_missing_optional_boss_cli_does_not_fail_health(monkeypatch):
    monkeypatch.setattr(doctor, "boss_agent_available", lambda: False)

    result = doctor._boss_agent_status()

    assert result["ok"] is True
    assert result["available"] is False
    assert "optional" in str(result["detail"])


def test_database_status_runs_integrity_check(tmp_path: Path, monkeypatch):
    broken_db = tmp_path / "jobs.db"
    broken_db.write_bytes(b"not sqlite")
    monkeypatch.setattr(doctor, "DB_PATH", broken_db)

    result = doctor._database_status()

    assert result["ok"] is False
    assert "完整性" in str(result["detail"]) or "连接失败" in str(result["detail"])


def test_print_report_uses_chinese_labels(capsys):
    checks = {
        "database": {"ok": True, "detail": "正常"},
        "frontend": {"ok": True, "detail": "存在"},
        "api": {"ok": True, "detail": "存在"},
        "export_path": {"ok": True, "detail": "存在"},
        "data_writable": {"ok": True, "detail": "可写"},
        "backup": {"ok": True, "detail": "存在"},
        "runtime": {"ok": True, "detail": "正常"},
        "data_counts": {"ok": True, "detail": {"jobs": 1}},
    }

    doctor.print_report(checks)

    output = capsys.readouterr().out
    assert "Chances 健康检查" in output
    assert "[通过] 数据库完整性" in output
    assert "核心检查全部通过" in output


def test_print_report_translates_internal_runtime_and_optional_values(capsys):
    checks = {
        "database": {"ok": True, "detail": "正常"},
        "frontend": {"ok": True, "detail": "存在"},
        "api": {"ok": True, "detail": "存在"},
        "export_path": {"ok": True, "detail": "存在"},
        "data_writable": {"ok": True, "detail": "可写"},
        "backup": {"ok": True, "detail": "存在"},
        "runtime": {
            "ok": True,
            "detail": {"backend": "ready", "frontend": "ready"},
        },
        "data_counts": {
            "ok": True,
            "detail": {"jobs": 6, "open_tasks": 0},
        },
        "boss_agent_cli": {
            "ok": True,
            "available": False,
            "detail": "not found (optional)",
        },
    }

    doctor.print_report(checks)

    output = capsys.readouterr().out
    assert "后端 正常，前端 正常" in output
    assert "岗位 6，待办任务 0" in output
    assert "未安装，不影响核心功能" in output
    assert "ready" not in output
    assert "optional" not in output
