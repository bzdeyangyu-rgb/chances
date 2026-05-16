# 求职作战台第二阶段实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现有“岗位运营台”基础上，补齐岗位评估、岗位详情、批量运营、周报复盘和系统诊断，让项目从可用骨架升级为真正可推进的个人求职助手。

**Architecture:** 保留现有 FastAPI + SQLite + Streamlit + 浏览器扩展结构，不重写项目。第二阶段优先增强后端数据结构与 API，再在 Streamlit 中补岗位详情、评估结果、批量更新和周报页面；Excel 继续保留为导出层，但逐步淡出主业务流程。

**Tech Stack:** Python 3.13, FastAPI, SQLite, Streamlit, pandas, httpx, pytest

---

### Task 1: 增加岗位评估存储与接口

**Files:**
- Modify: `backend/db.py`
- Modify: `backend/server.py`
- Create: `tests/backend/test_job_evaluation_api.py`

**Step 1: Write the failing test**

```python
def test_job_evaluation_can_be_saved_and_loaded(client):
    created = client.post("/api/jobs", json={
        "platform": "manual",
        "job_title": "AI产品经理",
        "company_name": "示例科技",
        "job_url": "https://example.com/jobs/pm-1",
    }).json()

    saved = client.post(f"/api/jobs/{created['id']}/evaluate", json={
        "match_score": 82,
        "recommendation": "建议推进",
        "reasoning": "岗位方向与个人目标一致",
        "highlights": "AI产品经验匹配",
        "risks": "缺少行业经验",
    })
    detail = client.get(f"/api/jobs/{created['id']}")

    assert saved.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["evaluation"]["match_score"] == 82
```

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_job_evaluation_api.py -q`
Expected: FAIL，因为评估接口和存储尚不存在

**Step 3: Write minimal implementation**

实现：
- 新增 `job_evaluations` 表
- 新增 `POST /api/jobs/{id}/evaluate`
- 新增 `GET /api/jobs/{id}`，返回岗位详情、评估、时间线

首版评估字段：
- `match_score`
- `recommendation`
- `reasoning`
- `highlights`
- `risks`
- `next_step_hint`

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_job_evaluation_api.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/db.py backend/server.py tests/backend/test_job_evaluation_api.py
git commit -m "feat: add job evaluation storage and api"
```

### Task 2: 增加岗位详情聚合接口

**Files:**
- Modify: `backend/server.py`
- Modify: `backend/db.py`
- Create: `tests/backend/test_job_detail_api.py`

**Step 1: Write the failing test**

```python
def test_job_detail_returns_job_timeline_and_evaluation(client):
    created = client.post("/api/jobs", json={
        "platform": "manual",
        "job_title": "AI应用工程师",
        "company_name": "示例科技",
        "job_url": "https://example.com/jobs/ai-1",
    }).json()

    client.post(f"/api/jobs/{created['id']}/status", json={
        "status": "建议推进",
        "next_action": "生成简历建议",
    })

    detail = client.get(f"/api/jobs/{created['id']}")

    assert detail.status_code == 200
    assert detail.json()["job"]["status"] == "建议推进"
    assert isinstance(detail.json()["timeline"], list)
```

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_job_detail_api.py -q`
Expected: FAIL，因为详情接口未聚合返回

**Step 3: Write minimal implementation**

在 `GET /api/jobs/{id}` 中返回：
- `job`
- `timeline`
- `evaluation`

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_job_detail_api.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/server.py backend/db.py tests/backend/test_job_detail_api.py
git commit -m "feat: add aggregated job detail endpoint"
```

### Task 3: 增强首页待办与岗位详情视图

**Files:**
- Modify: `frontend/app.py`
- Modify: `frontend/labels.py`
- Create: `tests/frontend/test_job_detail_view.py`

**Step 1: Write the failing test**

```python
from frontend.app import build_focus_jobs


def test_build_focus_jobs_prioritizes_high_priority_pending_work():
    rows = [
        {"job_title": "A", "priority": "高", "status": "建议推进", "next_action": "生成简历"},
        {"job_title": "B", "priority": "普通", "status": "待评估", "next_action": "补充信息"},
    ]

    focus = build_focus_jobs(rows)

    assert focus[0]["job_title"] == "A"
```

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/frontend/test_job_detail_view.py -q`
Expected: FAIL，因为首页聚焦逻辑不存在

**Step 3: Write minimal implementation**

实现：
- 首页“今日重点推进”按优先级和状态排序
- 岗位池中增加岗位详情区域
- 详情区展示岗位正文、评估摘要、时间线

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/frontend/test_job_detail_view.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/app.py frontend/labels.py tests/frontend/test_job_detail_view.py
git commit -m "feat: add focus jobs and detail panel"
```

### Task 4: 增加批量状态更新能力

**Files:**
- Modify: `backend/server.py`
- Modify: `frontend/app.py`
- Create: `tests/backend/test_bulk_status_api.py`
- Create: `tests/frontend/test_bulk_actions.py`

**Step 1: Write the failing tests**

```python
def test_bulk_status_update_updates_multiple_jobs(client):
    # 创建两条岗位后批量更新状态
    ...
```

```python
from frontend.app import collect_bulk_job_ids


def test_collect_bulk_job_ids_returns_selected_ids():
    rows = [{"id": 1, "selected": True}, {"id": 2, "selected": False}]
    assert collect_bulk_job_ids(rows) == [1]
```

**Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_bulk_status_api.py tests/frontend/test_bulk_actions.py -q`
Expected: FAIL，因为批量接口和前端辅助函数不存在

**Step 3: Write minimal implementation**

实现：
- `POST /api/jobs/bulk-status`
- 岗位池支持多选
- 批量更新状态和下一步动作

**Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_bulk_status_api.py tests/frontend/test_bulk_actions.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/server.py frontend/app.py tests/backend/test_bulk_status_api.py tests/frontend/test_bulk_actions.py
git commit -m "feat: add bulk status actions"
```

### Task 5: 增加周报复盘与系统诊断

**Files:**
- Create: `scripts/doctor.py`
- Modify: `backend/server.py`
- Modify: `frontend/app.py`
- Create: `tests/backend/test_weekly_review_api.py`
- Create: `tests/backend/test_doctor.py`

**Step 1: Write the failing tests**

```python
def test_weekly_review_returns_summary_counts(client):
    response = client.get("/api/reviews/weekly")
    assert response.status_code == 200
    assert "total_jobs" in response.json()
```

```python
from scripts.doctor import run_checks


def test_run_checks_reports_required_services():
    result = run_checks()
    assert "database" in result
    assert "frontend" in result
```

**Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_weekly_review_api.py tests/backend/test_doctor.py -q`
Expected: FAIL，因为周报接口和诊断脚本不存在

**Step 3: Write minimal implementation**

实现：
- `GET /api/reviews/weekly`
- 周报统计：总岗位数、待推进、已投递、高优岗位、状态分布
- `scripts/doctor.py` 检查数据库、前端入口、后端入口、导出路径

**Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_weekly_review_api.py tests/backend/test_doctor.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/doctor.py backend/server.py frontend/app.py tests/backend/test_weekly_review_api.py tests/backend/test_doctor.py
git commit -m "feat: add weekly review and doctor checks"
```
