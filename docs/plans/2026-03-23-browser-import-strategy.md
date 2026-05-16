# Browser Import Strategy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Python-side browser import pipeline that reuses logged-in Chrome profile data, applies light anti-detection for Boss, prefers API responses over fragile DOM parsing, and writes imported jobs into the local workbook served by the existing app.

**Architecture:** Keep the existing FastAPI + Excel workflow, but move multi-site import into a dedicated Python module under `backend/`. The importer launches Playwright against a copied Chrome profile, injects a Boss stealth script, captures Boss detail JSON when available, falls back to per-site DOM parsing when needed, and upserts results through shared workbook persistence helpers.

**Tech Stack:** Python 3.13, Playwright Python, FastAPI, pandas, pytest

---

### Task 1: Define Importer Contracts

**Files:**
- Create: `tests/backend/test_browser_import.py`
- Modify: `requirements.txt`

**Step 1: Write the failing tests**

Add tests for:
- Boss detail JSON -> normalized job payload
- Verification page detection
- Zhilian visible text parsing
- Workbook upsert behavior through shared helpers

**Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_browser_import.py -q`
Expected: FAIL because `backend.browser_import` does not exist

**Step 3: Commit**

```bash
git add tests/backend/test_browser_import.py requirements.txt
git commit -m "test: define browser import contracts"
```

### Task 2: Implement Shared Import Module

**Files:**
- Create: `backend/browser_import.py`
- Modify: `backend/server.py`

**Step 1: Write minimal implementation**

Implement:
- UTF-8 safe platform label mapping
- `is_verification_page(title, text, url)`
- `parse_boss_detail_json(raw_json)`
- `parse_zhaopin_visible_lines(title, lines)`
- workbook upsert helper reused by API and importer

**Step 2: Run tests to verify they pass**

Run: `pytest tests/backend/test_browser_import.py -q`
Expected: PASS

**Step 3: Commit**

```bash
git add backend/browser_import.py backend/server.py
git commit -m "feat: add shared browser import helpers"
```

### Task 3: Add Real-Browser Import Runner

**Files:**
- Create: `scripts/import_urls_with_chrome.py`
- Modify: `requirements.txt`

**Step 1: Write minimal implementation**

Implement:
- copy current Chrome `Default` profile to temp workspace dir
- launch Playwright persistent context on copied profile
- inject Boss anti-detection JS
- visit URL list, prefer Boss detail API response, fall back to DOM parsers
- upsert successful jobs into workbook
- save per-URL results JSON for verification

**Step 2: Run focused verification**

Run: `pytest -q`
Expected: PASS

**Step 3: Commit**

```bash
git add scripts/import_urls_with_chrome.py requirements.txt
git commit -m "feat: add real browser import runner"
```

### Task 4: Run End-to-End Import Verification

**Files:**
- Modify: `data/jobs.xlsx` (runtime output)
- Create: `tmp_import_results.json` (runtime output)

**Step 1: Run import against supplied URLs**

Run:

```bash
python scripts/import_urls_with_chrome.py "<url1>" "<url2>" "<url3>" "<url4>"
```

**Step 2: Verify workbook and local app**

Run:
- `Invoke-WebRequest http://127.0.0.1:8000/api/jobs`
- `streamlit run frontend/app.py` or refresh existing local app

Expected:
- successful URLs written into workbook
- blocked URLs explicitly reported as verification or navigation failures
- local dashboard reflects imported rows

