# Job Automation Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local end-to-end job collection system with a FastAPI backend, a Manifest V3 Chrome extension, and a Streamlit dashboard for managing cross-platform recruiting data.

**Architecture:** The backend owns SQLite initialization, deduplicated persistence, and query APIs. The Chrome extension extracts normalized job data from platform-specific DOM structures and posts that payload to the local API. The Streamlit app reads the same database, supports filtering, and writes row-level status changes back into SQLite.

**Tech Stack:** Python 3, FastAPI, SQLite, Uvicorn, Chrome Extension Manifest V3, JavaScript, Streamlit, Pandas, pytest

---

### Task 1: Scaffold Runtime and Shared Conventions

**Files:**
- Create: `backend/server.py`
- Create: `extension/manifest.json`
- Create: `extension/popup.html`
- Create: `extension/popup.js`
- Create: `extension/content.js`
- Create: `frontend/app.py`
- Create: `README.md`
- Create: `requirements.txt`
- Create: `tests/backend/test_server.py`

**Step 1: Write the failing dependency smoke test**

```python
from fastapi.testclient import TestClient

from backend.server import app


def test_health_of_jobs_endpoint_contract():
    client = TestClient(app)
    response = client.get("/api/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_server.py::test_health_of_jobs_endpoint_contract -v`
Expected: FAIL with `ModuleNotFoundError` for `backend.server` or missing `app`

**Step 3: Write minimal implementation**

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/api/jobs")
def get_jobs():
    return []
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backend/test_server.py::test_health_of_jobs_endpoint_contract -v`
Expected: PASS

**Step 5: Commit**

```bash
git add requirements.txt backend/server.py tests/backend/test_server.py
git commit -m "chore: scaffold job automation project"
```

### Task 2: Implement Backend Persistence and Deduplicated Upsert

**Files:**
- Modify: `backend/server.py`
- Modify: `tests/backend/test_server.py`
- Create: `tests/backend/test_filters.py`

**Step 1: Write the failing POST deduplication test**

```python
def test_post_job_deduplicates_by_job_url(client):
    payload = {
        "platform": "boss",
        "job_title": "AI Engineer",
        "salary_raw": "20k-35k",
        "company_name": "Acme",
        "location": "Nanjing",
        "job_url": "https://example.com/job/1"
    }

    first = client.post("/api/jobs", json=payload)
    second = client.post("/api/jobs", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["result"] in {"duplicate", "updated"}

    listing = client.get("/api/jobs").json()
    assert len(listing) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_server.py::test_post_job_deduplicates_by_job_url -v`
Expected: FAIL because `POST /api/jobs` is missing or raises uniqueness errors

**Step 3: Write minimal implementation**

```python
CREATE TABLE IF NOT EXISTS job_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    job_title TEXT NOT NULL,
    salary_raw TEXT,
    company_name TEXT,
    location TEXT,
    job_url TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT '未投递',
    created_at TEXT NOT NULL
)
```

```python
INSERT INTO job_listings (...)
VALUES (...)
ON CONFLICT(job_url)
DO UPDATE SET created_at = excluded.created_at
```

Add:
- startup-time SQLite initialization
- permissive local CORS for `chrome-extension://*` and `http://localhost:*`
- `POST /api/jobs` response payload with `created`, `duplicate`, or `updated`
- optional filters on `platform`, `status`, and `location` in `GET /api/jobs`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/backend -v`
Expected: PASS for endpoint contract, deduplication, and filtering scenarios

**Step 5: Commit**

```bash
git add backend/server.py tests/backend/test_server.py tests/backend/test_filters.py
git commit -m "feat: add backend job storage and query API"
```

### Task 3: Build Chrome Extension Capture Flow

**Files:**
- Modify: `extension/manifest.json`
- Modify: `extension/popup.html`
- Modify: `extension/popup.js`
- Modify: `extension/content.js`
- Create: `tests/extension/content-parser-notes.md`

**Step 1: Write the failing parser contract notes**

Document in `tests/extension/content-parser-notes.md` the required normalized payload:

```json
{
  "platform": "boss|liepin|lagou|zhaopin",
  "job_title": "string",
  "salary_raw": "string",
  "company_name": "string",
  "location": "string",
  "job_url": "string"
}
```

List one selector fallback chain per supported host and the expected duplicate-safe POST behavior.

**Step 2: Verify the extension is incomplete**

Run: load unpacked extension in Chrome
Expected: popup button missing or no payload reaches `http://localhost:8000/api/jobs`

**Step 3: Write minimal implementation**

Implement:
- `manifest.json` with `action`, `activeTab`, `scripting`, and `host_permissions` for all four platforms and `http://localhost:8000/*`
- `popup.html` with one primary button and status text
- `popup.js` that injects or messages `content.js`, receives normalized job data, and posts to backend
- `content.js` parser router:
  - `zhipin.com`: use structural traversal near `h1` and adjacent spans
  - `liepin.com`: prefer `data-selector` anchors, then stable container text blocks
  - `lagou.com`: extract tags and append them into a `notes` or derived title string if no dedicated field exists
  - `zhaopin.com`: use prefix selectors such as `[class^="job-title"]`

For robustness, implement helper utilities:
- `textFromSelectors(selectors)`
- `textNearHeading(heading)`
- `firstHref(selectors)`
- `normalizeLocation(text)`
- `detectPlatform(hostname)`

**Step 4: Verify the capture flow**

Run:
1. `uvicorn backend.server:app --reload`
2. Load unpacked `extension/`
3. Open a supported job detail page
4. Click the popup button

Expected:
- popup shows `抓取成功` or `重复抓取`
- backend log shows one POST
- repeated clicks do not create duplicate rows

**Step 5: Commit**

```bash
git add extension/manifest.json extension/popup.html extension/popup.js extension/content.js tests/extension/content-parser-notes.md
git commit -m "feat: add cross-platform job capture extension"
```

### Task 4: Build Streamlit Dashboard and Status Sync

**Files:**
- Modify: `frontend/app.py`
- Create: `tests/frontend/test_dashboard_notes.md`

**Step 1: Write the failing dashboard behavior notes**

Describe the required behaviors in `tests/frontend/test_dashboard_notes.md`:
- page config title is `AI 岗位智能追踪看板`
- layout is `wide`
- sidebar filters `platform`, `status`, `location`
- metrics show total jobs and submitted jobs
- `st.data_editor` exposes editable `status`
- row status changes are written back to SQLite immediately

**Step 2: Verify the dashboard is incomplete**

Run: `streamlit run frontend/app.py`
Expected: app fails to load or lacks editable status persistence

**Step 3: Write minimal implementation**

Implement in `frontend/app.py`:
- SQLite read function returning a Pandas DataFrame
- sidebar filtering with multiselects and a text input
- metrics derived from the filtered or full DataFrame as required by UX decision
- `st.data_editor` with a `SelectboxColumn` for `status`
- change detection by comparing edited rows against the original DataFrame indexed by `id`
- per-row `UPDATE job_listings SET status = ? WHERE id = ?`
- refresh after writes using Streamlit rerun behavior

**Step 4: Verify the dashboard flow**

Run: `streamlit run frontend/app.py`
Expected:
- dashboard loads in browser
- editing a row status persists after refresh
- filters narrow the data set correctly

**Step 5: Commit**

```bash
git add frontend/app.py tests/frontend/test_dashboard_notes.md
git commit -m "feat: add streamlit job tracking dashboard"
```

### Task 5: Write Deployment README and Final Verification

**Files:**
- Modify: `README.md`
- Create: `tests/integration/test_manual_checklist.md`

**Step 1: Write the failing manual verification checklist**

Add to `tests/integration/test_manual_checklist.md`:
- backend starts cleanly and creates `jobs.db`
- extension can post one supported job payload
- duplicate click path does not create extra rows
- dashboard edits status and persists to database
- README answers the three required technical questions with the minimum length

**Step 2: Verify docs are incomplete**

Run: inspect `README.md`
Expected: missing startup steps, missing architecture explanation, or missing directory tree

**Step 3: Write minimal implementation**

`README.md` must include:
- directory tree with `backend/`, `extension/`, `frontend/`, `docs/`, and `tests/`
- startup guide for FastAPI, Chrome unpacked extension loading, and Streamlit
- detailed sections for:
  - anti-scraping and DOM parsing resilience
  - SQLite duplicate-safe consistency handling
  - Streamlit row-edit capture and database sync

Also add:
- install command such as `pip install -r requirements.txt`
- run commands:
  - `uvicorn backend.server:app --reload`
  - `streamlit run frontend/app.py`

**Step 4: Run final verification**

Run:
- `pytest tests/backend -v`
- manual Chrome extension smoke test
- `streamlit run frontend/app.py`

Expected:
- backend tests pass
- extension POST succeeds
- dashboard persists edits

**Step 5: Commit**

```bash
git add README.md tests/integration/test_manual_checklist.md
git commit -m "docs: add deployment guide and verification checklist"
```

### Task 6: Wrap Up and Handoff

**Files:**
- Modify: `docs/plans/2026-03-23-job-automation-workflow.md`

**Step 1: Record actual deviations**

Append a short implementation log with:
- environment limitations such as missing `git`
- selector adjustments required during testing
- any schema changes beyond the original SOP

**Step 2: Verify the handoff is explicit**

Run: read this plan top to bottom
Expected: a new engineer can implement without asking for missing context

**Step 3: Write minimal implementation**

Update the plan status section with:
- `Not Started`
- `In Progress`
- `Done`

Track completed tasks during execution.

**Step 4: Verify readability**

Run: open the plan markdown in the editor
Expected: headings, commands, and file paths are easy to follow

**Step 5: Commit**

```bash
git add docs/plans/2026-03-23-job-automation-workflow.md
git commit -m "docs: finalize implementation plan handoff"
```
