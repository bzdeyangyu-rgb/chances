# -*- coding: utf-8 -*-
from __future__ import annotations

from backend.boss_agent_bridge import (
    boss_agent_available,
    build_boss_search_command,
    parse_boss_agent_envelope,
    resolve_boss_cli_name,
    run_boss_search,
    validate_boss_command,
)


def test_parse_boss_agent_envelope_extracts_jobs_as_job_payloads():
    raw = {
        "ok": True,
        "schema_version": "1.0",
        "command": "search",
        "data": {
            "jobs": [
                {
                    "title": "AI产品经理",
                    "company": "示例科技",
                    "salary": "15-25K",
                    "location": "南京",
                    "url": "https://www.zhipin.com/job_detail/example.html?ka=search_list",
                    "description": "负责 AI 产品规划、需求分析和落地推进。",
                }
            ]
        },
    }

    jobs = parse_boss_agent_envelope(raw)

    assert jobs == [
        {
            "platform": "boss",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "salary_raw": "15-25K",
            "location": "南京",
            "job_url": "https://www.zhipin.com/job_detail/example.html?ka=search_list",
            "main_text": "负责 AI 产品规划、需求分析和落地推进。",
        }
    ]


def test_validate_boss_command_allows_only_read_only_commands():
    for command in ["search", "detail", "export", "stats"]:
        assert validate_boss_command(command) is True

    for command in ["greet", "apply", "chat", "contact", "bulk-greet"]:
        assert validate_boss_command(command) is False


def test_build_boss_search_command_includes_query_city_and_limit(monkeypatch):
    monkeypatch.setattr("backend.boss_agent_bridge.resolve_boss_cli_name", lambda: "boss-agent-cli")
    preset = {
        "query": "AI产品经理",
        "city": "南京",
    }

    command = build_boss_search_command(preset, limit=12)

    assert command == [
        "boss-agent-cli",
        "search",
        "--query",
        "AI产品经理",
        "--city",
        "南京",
        "--limit",
        "12",
    ]


def test_build_boss_search_command_supports_installed_boss_entrypoint(monkeypatch):
    monkeypatch.setattr("backend.boss_agent_bridge.resolve_boss_cli_name", lambda: "boss")
    preset = {
        "query": "AI产品经理",
        "city": "南京",
        "salary": "15-25K",
    }

    command = build_boss_search_command(preset, limit=12)

    assert command == [
        "boss",
        "--json",
        "search",
        "AI产品经理",
        "--city",
        "南京",
        "--salary",
        "15-25K",
    ]


def test_boss_agent_available_checks_cli_on_path(monkeypatch):
    monkeypatch.setattr("backend.boss_agent_bridge.shutil.which", lambda name: None)

    assert boss_agent_available() is False


def test_resolve_boss_cli_name_accepts_installed_boss_entrypoint(monkeypatch):
    monkeypatch.setattr("backend.boss_agent_bridge.shutil.which", lambda name: name if name == "boss" else None)

    assert resolve_boss_cli_name() == "boss"


def test_run_boss_search_invokes_cli_and_parses_json(monkeypatch):
    calls = []

    class Completed:
        returncode = 0
        stdout = '{"ok": true, "data": {"jobs": [{"title": "AI产品经理"}]}}'
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setattr("backend.boss_agent_bridge.boss_agent_available", lambda: True)
    monkeypatch.setattr("backend.boss_agent_bridge.resolve_boss_cli_name", lambda: "boss-agent-cli")
    monkeypatch.setattr("backend.boss_agent_bridge.subprocess.run", fake_run)

    result = run_boss_search({"query": "AI产品经理", "city": "南京"}, limit=3)

    assert result["ok"] is True
    assert result["data"]["jobs"][0]["title"] == "AI产品经理"
    assert calls[0][0] == [
        "boss-agent-cli",
        "search",
        "--query",
        "AI产品经理",
        "--city",
        "南京",
        "--limit",
        "3",
    ]
    assert calls[0][1]["capture_output"] is True
    assert calls[0][1]["timeout"] == 60
