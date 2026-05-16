# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.browser_import import (
    BOSS_ANTI_DETECTION_SCRIPT,
    build_main_text,
    is_verification_page,
    parse_boss_detail_json,
    parse_lagou_visible_lines,
    parse_liepin_visible_lines,
    parse_zhaopin_visible_lines,
    upsert_job,
)


RESULTS_PATH = ROOT / "tmp_import_results.json"
PROFILE_COPY_PATH = ROOT / "tmp_chrome_profile_run"


def body_lines(page: Page) -> list[str]:
    raw_text = page.evaluate("(document.body && document.body.innerText) || ''")
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def clone_chrome_profile() -> Path:
    source_root = Path.home() / "AppData/Local/Google/Chrome/User Data"
    source_default = source_root / "Default"

    if PROFILE_COPY_PATH.exists():
        shutil.rmtree(PROFILE_COPY_PATH)
    PROFILE_COPY_PATH.mkdir(parents=True, exist_ok=True)

    destination_default = PROFILE_COPY_PATH / "Default"
    ignored_names = set(shutil.ignore_patterns("lockfile", "Singleton*", "LOCK")("", os.listdir(source_default)))
    for root, dirs, files in os.walk(source_default):
        source_dir = Path(root)
        relative_dir = source_dir.relative_to(source_default)
        target_dir = destination_default / relative_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        dirs[:] = [name for name in dirs if name not in ignored_names]
        for filename in files:
            if filename in ignored_names:
                continue
            source_file = source_dir / filename
            target_file = target_dir / filename
            try:
                shutil.copy2(source_file, target_file)
            except OSError:
                continue

    for name in ("Local State", "First Run", "Last Version"):
        source = source_root / name
        if source.exists():
            try:
                shutil.copy2(source, PROFILE_COPY_PATH / name)
            except OSError:
                continue
    return PROFILE_COPY_PATH


def detect_platform(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    if "zhipin.com" in hostname:
        return "boss"
    if "liepin.com" in hostname:
        return "liepin"
    if "lagou.com" in hostname:
        return "lagou"
    if "zhaopin.com" in hostname:
        return "zhaopin"
    return ""


def extract_job_from_page(page: Page, source_url: str) -> dict[str, Any]:
    platform = detect_platform(page.url or source_url)
    title = page.title()
    text = page.evaluate("(document.body && document.body.innerText) || ''")
    lines = body_lines(page)

    if not platform:
        return {"ok": False, "final_url": page.url, "title": title, "error": "当前页面不在支持的网站范围内。"}
    if is_verification_page(title, text, page.url):
        return {"ok": False, "final_url": page.url, "title": title, "error": "当前页面触发了网站验证，无法可靠提取岗位数据。"}

    if platform == "liepin":
        job = parse_liepin_visible_lines(lines, page.url)
    elif platform == "lagou":
        job = parse_lagou_visible_lines(title, lines, page.url)
    elif platform == "zhaopin":
        job = parse_zhaopin_visible_lines(title, lines, page.url)
    else:
        return {"ok": False, "final_url": page.url, "title": title, "error": "Boss 需要先命中详情接口响应。"}

    job["main_text"] = build_main_text(lines)

    if not job["job_title"]:
        return {"ok": False, "final_url": page.url, "title": title, "error": "未提取到岗位名称，请确认当前是岗位详情页。"}

    return {"ok": True, "final_url": page.url, "title": title, "job": job}


def import_urls(urls: list[str]) -> list[dict[str, Any]]:
    profile_path = clone_chrome_profile()
    results: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_path),
            channel="chrome",
            headless=False,
            args=["--profile-directory=Default", "--disable-blink-features=AutomationControlled"],
        )
        context.add_init_script(BOSS_ANTI_DETECTION_SCRIPT)

        for source_url in urls:
            boss_detail_payload: dict[str, str] | None = None

            def handle_response(response) -> None:
                nonlocal boss_detail_payload
                try:
                    if "/wapi/zpgeek/job/detail.json" not in response.url:
                        return
                    if response.request.method.lower() != "get":
                        return
                    body = response.text()
                    if not body:
                        return
                    boss_detail_payload = parse_boss_detail_json(body, source_url)
                except Exception:
                    return

            page = context.new_page()
            page.on("response", handle_response)
            record: dict[str, Any] = {"source_url": source_url}

            try:
                page.goto(source_url, wait_until="domcontentloaded", timeout=120000)
                page.wait_for_timeout(10000)
                if detect_platform(source_url) == "boss" and boss_detail_payload:
                    boss_detail_payload["main_text"] = build_main_text(body_lines(page))
                    record.update({"ok": True, "final_url": page.url, "title": page.title(), "job": boss_detail_payload})
                else:
                    record.update(extract_job_from_page(page, source_url))

                if record.get("ok"):
                    record["api_result"] = upsert_job(record["job"])
            except Exception as exc:
                record.update(
                    {
                        "ok": False,
                        "final_url": page.url,
                        "title": page.title() if page.url else "",
                        "error": str(exc),
                    }
                )
            finally:
                results.append(record)
                page.close()

        context.close()

    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def main() -> int:
    urls = sys.argv[1:]
    if not urls:
        print("Usage: python scripts/import_urls_with_chrome.py <url1> <url2> ...")
        return 1

    results = import_urls(urls)
    print(json.dumps(results, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
