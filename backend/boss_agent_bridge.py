# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


CLI_NAME = "boss-agent-cli"
CLI_ENTRYPOINTS = (CLI_NAME, "boss")
READ_ONLY_COMMANDS = {"search", "detail", "export", "stats"}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(_text(item) for item in value if _text(item))
    if isinstance(value, dict):
        return "\n".join(f"{key}: {_text(item)}" for key, item in value.items() if _text(item))
    return str(value).strip()


def _first_text(mapping: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _text(mapping.get(key))
        if value:
            return value
    return ""


def _envelope_jobs(raw: dict[str, Any]) -> list[Any]:
    data = raw.get("data")
    if isinstance(data, dict):
        jobs = data.get("jobs") or data.get("results") or data.get("items")
        if isinstance(jobs, list):
            return jobs

    jobs = raw.get("jobs") or raw.get("results") or raw.get("items")
    return jobs if isinstance(jobs, list) else []


def parse_boss_agent_envelope(raw: dict[str, Any]) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []
    for item in _envelope_jobs(raw):
        if not isinstance(item, dict):
            continue

        jobs.append(
            {
                "platform": "boss",
                "job_title": _first_text(item, "job_title", "title", "name", "position", "jobName"),
                "company_name": _first_text(
                    item,
                    "company_name",
                    "company",
                    "brand_name",
                    "brandName",
                    "companyName",
                ),
                "salary_raw": _first_text(item, "salary_raw", "salary", "salaryDesc", "salary_text"),
                "location": _first_text(item, "location", "city", "locationName", "address"),
                "job_url": _first_text(item, "job_url", "url", "link", "detail_url", "detailUrl"),
                "main_text": _first_text(
                    item,
                    "main_text",
                    "description",
                    "job_description",
                    "jobDescription",
                    "detail",
                    "content",
                    "text",
                ),
            }
        )
    return jobs


def validate_boss_command(command: str) -> bool:
    return command.strip().lower() in READ_ONLY_COMMANDS


def build_boss_search_command(preset: dict[str, Any], limit: int = 20) -> list[str]:
    safe_limit = max(1, int(limit))
    cli_name = resolve_boss_cli_name() or CLI_NAME
    if cli_name == "boss":
        command = [cli_name, "--json", "search"]
        query = _text(preset.get("query"))
        if query:
            command.append(query)
        city = _text(preset.get("city"))
        if city:
            command.extend(["--city", city])
        salary = _text(preset.get("salary"))
        if salary:
            command.extend(["--salary", salary])
        return command

    return [cli_name, "search", "--query", _text(preset.get("query")), "--city", _text(preset.get("city")), "--limit", str(safe_limit)]


def resolve_boss_cli_name() -> str | None:
    for name in CLI_ENTRYPOINTS:
        if shutil.which(name):
            return name
    return None


def boss_agent_available() -> bool:
    return resolve_boss_cli_name() is not None


def run_boss_search(preset: dict[str, Any], limit: int = 20, timeout: int = 60) -> dict[str, Any]:
    if not boss_agent_available():
        raise FileNotFoundError(f"{CLI_NAME} not found")

    completed = subprocess.run(
        build_boss_search_command(preset, limit=limit),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        detail = _text(completed.stderr) or _text(completed.stdout) or f"{CLI_NAME} exited with {completed.returncode}"
        raise RuntimeError(detail)

    try:
        parsed = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"{CLI_NAME} output is not valid JSON") from exc

    return parsed if isinstance(parsed, dict) else {"data": {"jobs": []}}
