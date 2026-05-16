# Manual Browser Capture Flow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a semi-automatic browser capture flow so the user can manually clear site verification in Chrome, then click the extension to import the current job page into the local workbook.

**Architecture:** Keep extraction lightweight in the extension: gather the current page URL, title, visible text lines, and any direct field guesses from DOM. Send that snapshot to the local FastAPI backend, which performs verification-page checks, parser fallback, and workbook upsert so parsing logic stays centralized.

**Tech Stack:** Chrome extension (Manifest V3), FastAPI, pandas/openpyxl, Playwright-based tests.

---

### Task 1: Define backend snapshot import behavior

**Files:**
- Modify: `backend/browser_import.py`
- Modify: `backend/server.py`
- Test: `tests/backend/test_server.py`

**Step 1: Write the failing test**
- Add an API test for a new snapshot import endpoint that accepts `url`, `title`, `body_lines`, and an optional pre-extracted `job` payload.

**Step 2: Run test to verify it fails**
- Run: `pytest tests/backend/test_server.py -q`

**Step 3: Write minimal implementation**
- Add snapshot payload models and a backend helper that:
- rejects verification pages,
- prefers the provided structured job when valid,
- falls back to per-platform parsers based on the snapshot.

**Step 4: Run test to verify it passes**
- Run: `pytest tests/backend/test_server.py -q`

### Task 2: Move extension capture to snapshot submission

**Files:**
- Modify: `extension/content.js`
- Modify: `extension/popup.js`
- Modify: `extension/popup.html`
- Test: `tests/extension/test_content_parser.py`

**Step 1: Write the failing test**
- Add a content-script test that verifies the script can produce a page snapshot and structured job data from supported job markup.

**Step 2: Run test to verify it fails**
- Run: `pytest tests/extension/test_content_parser.py -q`

**Step 3: Write minimal implementation**
- Make the content script return `{ snapshot, job }` for the current tab.
- Make the popup call the new backend snapshot endpoint and surface created/updated/duplicate/verifying states clearly.

**Step 4: Run test to verify it passes**
- Run: `pytest tests/extension/test_content_parser.py -q`

### Task 3: Verify end-to-end local behavior

**Files:**
- Modify: `tests/backend/test_browser_import.py`
- Verify: `data/jobs.xlsx`

**Step 1: Write the failing test**
- Add parser coverage for snapshot-based fallback behavior that mirrors the current supported sites.

**Step 2: Run test to verify it fails**
- Run: `pytest tests/backend/test_browser_import.py -q`

**Step 3: Write minimal implementation**
- Fill the missing parser gaps needed by the new manual flow.

**Step 4: Run test to verify it passes**
- Run: `pytest tests/backend/test_browser_import.py -q`

### Task 4: Run full verification

**Files:**
- Verify only

**Step 1: Run targeted suites**
- Run: `pytest tests/backend/test_server.py tests/backend/test_browser_import.py tests/extension/test_content_parser.py -q`

**Step 2: Run full suite**
- Run: `pytest -q`

**Step 3: Smoke-test local services**
- Verify `http://127.0.0.1:8000/api/jobs`
- Verify `http://127.0.0.1:8501`
