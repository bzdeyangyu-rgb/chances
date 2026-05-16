# 求职作战台第一阶段实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把现有项目从“岗位采集表格”升级为“可运营的岗位池”，完成第一阶段所需的数据层重构、个人画像基础能力、岗位状态流转和首页/岗位池基础界面。

**Architecture:** 保留现有 Python + FastAPI + Streamlit + 浏览器扩展整体形态，但将 Excel 从主存储降级为导出层，新增 SQLite 作为主存储。第一阶段不追求完整的材料生成和周报能力，只完成支撑后续扩展的核心骨架：个人画像、岗位主表、状态流转、下一步动作、基础管理台。

**Tech Stack:** Python 3.13, FastAPI, SQLite, Streamlit, pandas, pytest

---

### Task 1: 建立第一阶段数据模型

**Files:**
- Create: `backend/db.py`
- Create: `tests/backend/test_db.py`
- Modify: `requirements.txt`

**Step 1: 写失败测试**

```python
from pathlib import Path

from backend.db import initialize_database


def test_initialize_database_creates_core_tables(tmp_path: Path):
    db_path = tmp_path / "jobs.db"

    initialize_database(db_path)

    assert db_path.exists()
```

**Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_db.py -q`
Expected: FAIL，因为 `backend.db` 尚不存在

**Step 3: 最小实现**

实现数据库初始化，至少创建以下表：
- `candidate_profile`
- `jobs`
- `job_actions`

表职责：
- `candidate_profile`：存储你的求职画像
- `jobs`：存储岗位事实和当前状态
- `job_actions`：存储状态变化、下一步动作和时间记录

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_db.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/db.py tests/backend/test_db.py requirements.txt
git commit -m "feat: add sqlite core schema for phase 1"
```

### Task 2: 增加个人画像基础存取接口

**Files:**
- Modify: `backend/server.py`
- Create: `tests/backend/test_profile_api.py`

**Step 1: 写失败测试**

```python
from fastapi.testclient import TestClient

from backend.server import create_app


def test_profile_api_supports_get_and_post(tmp_path):
    app = create_app(workbook_path=tmp_path / "jobs.xlsx", db_path=tmp_path / "jobs.db")
    client = TestClient(app)

    payload = {
        "target_roles": "AI产品经理, AI应用工程师",
        "target_cities": "南京, 上海",
        "salary_min": "25k",
    }

    created = client.post("/api/profile", json=payload)
    fetched = client.get("/api/profile")

    assert created.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["target_roles"] == "AI产品经理, AI应用工程师"
```

**Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_profile_api.py -q`
Expected: FAIL，因为接口不存在

**Step 3: 最小实现**

新增：
- `GET /api/profile`
- `POST /api/profile`

首版画像字段建议：
- `target_roles`
- `target_cities`
- `remote_preference`
- `salary_min`
- `salary_ideal`
- `core_skills`
- `project_highlights`
- `no_go_rules`

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_profile_api.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/server.py tests/backend/test_profile_api.py
git commit -m "feat: add candidate profile api"
```

### Task 3: 重构岗位主表为可运营机会池

**Files:**
- Modify: `backend/db.py`
- Modify: `backend/server.py`
- Create: `tests/backend/test_jobs_api.py`

**Step 1: 写失败测试**

```python
def test_post_job_sets_default_status_and_next_action(client):
    payload = {
        "platform": "manual",
        "job_title": "AI 应用工程师",
        "company_name": "示例科技",
        "job_url": "https://example.com/jobs/1",
    }

    created = client.post("/api/jobs", json=payload)
    listing = client.get("/api/jobs")

    assert created.status_code == 200
    assert listing.json()[0]["status"] == "待评估"
    assert listing.json()[0]["next_action"] == "补充岗位信息并完成评估"
```

**Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_jobs_api.py -q`
Expected: FAIL，因为当前岗位记录不含状态与动作字段

**Step 3: 最小实现**

新增岗位字段：
- `status`
- `priority`
- `next_action`
- `notes`
- `source_type`
- `created_at`
- `updated_at`

默认值：
- `status = 待评估`
- `priority = 普通`
- `next_action = 补充岗位信息并完成评估`

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_jobs_api.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/db.py backend/server.py tests/backend/test_jobs_api.py
git commit -m "feat: upgrade jobs into opportunity pipeline records"
```

### Task 4: 增加岗位状态流转接口

**Files:**
- Modify: `backend/server.py`
- Modify: `backend/db.py`
- Create: `tests/backend/test_job_actions_api.py`

**Step 1: 写失败测试**

```python
def test_update_job_status_creates_action_log(client):
    created = client.post("/api/jobs", json={
        "platform": "manual",
        "job_title": "AI 应用工程师",
        "company_name": "示例科技",
        "job_url": "https://example.com/jobs/1",
    }).json()

    response = client.post(f"/api/jobs/{created['id']}/status", json={
        "status": "建议推进",
        "next_action": "生成岗位定制简历建议",
    })

    timeline = client.get(f"/api/jobs/{created['id']}/timeline")

    assert response.status_code == 200
    assert timeline.status_code == 200
    assert timeline.json()[0]["status"] == "建议推进"
```

**Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_job_actions_api.py -q`
Expected: FAIL，因为状态更新接口和时间线接口不存在

**Step 3: 最小实现**

新增：
- `POST /api/jobs/{id}/status`
- `GET /api/jobs/{id}/timeline`

每次状态变更都写入 `job_actions`。

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_job_actions_api.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/server.py backend/db.py tests/backend/test_job_actions_api.py
git commit -m "feat: add job status transition and timeline api"
```

### Task 5: 增加 Excel 到 SQLite 的首次迁移能力

**Files:**
- Create: `scripts/migrate_excel_to_sqlite.py`
- Create: `tests/backend/test_migration.py`

**Step 1: 写失败测试**

```python
from pathlib import Path

from scripts.migrate_excel_to_sqlite import migrate_workbook


def test_migrate_workbook_imports_existing_rows(tmp_path: Path):
    workbook = tmp_path / "jobs.xlsx"
    db_path = tmp_path / "jobs.db"

    # 预先写入一行 Excel 测试数据
    # 运行迁移
    result = migrate_workbook(workbook, db_path)

    assert result["imported"] == 1
```

**Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_migration.py -q`
Expected: FAIL，因为迁移脚本不存在

**Step 3: 最小实现**

实现：
- 从 `data/jobs.xlsx` 读取旧数据
- 映射到新 `jobs` 表
- 默认补 `status=待评估`
- 默认补 `source_type=legacy_import`
- 按 `job_url` 去重

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_migration.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/migrate_excel_to_sqlite.py tests/backend/test_migration.py
git commit -m "feat: add excel to sqlite migration script"
```

### Task 6: 重做首页为求职运营总览

**Files:**
- Modify: `frontend/app.py`
- Create: `tests/frontend/test_dashboard_home.py`

**Step 1: 写失败测试**

```python
from frontend.app import build_home_metrics


def test_build_home_metrics_returns_core_counts():
    metrics = build_home_metrics([
        {"status": "待评估"},
        {"status": "建议推进"},
        {"status": "已投递"},
    ])

    assert metrics["total_jobs"] == 3
    assert metrics["todo_jobs"] >= 1
```

**Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/frontend/test_dashboard_home.py -q`
Expected: FAIL，因为首页指标构建函数不存在

**Step 3: 最小实现**

首页展示：
- 岗位总数
- 待评估数
- 建议推进数
- 已投递数
- 长时间未推进岗位数

并显示：
- 今日待办列表
- 高优先级岗位列表

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/frontend/test_dashboard_home.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/app.py tests/frontend/test_dashboard_home.py
git commit -m "feat: add dashboard home metrics and todo summary"
```

### Task 7: 重做岗位池页面与筛选能力

**Files:**
- Modify: `frontend/app.py`
- Create: `tests/frontend/test_jobs_board.py`

**Step 1: 写失败测试**

```python
from frontend.app import filter_opportunities


def test_filter_opportunities_supports_status_priority_and_keyword():
    rows = [
        {"job_title": "AI 产品经理", "status": "建议推进", "priority": "高"},
        {"job_title": "后端工程师", "status": "待评估", "priority": "普通"},
    ]

    result = filter_opportunities(rows, status="建议推进", priority="高", keyword="AI")

    assert len(result) == 1
```

**Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/frontend/test_jobs_board.py -q`
Expected: FAIL，因为岗位池筛选函数不存在

**Step 3: 最小实现**

岗位池页面支持：
- 按状态筛选
- 按优先级筛选
- 按关键词筛选
- 批量更新状态
- 批量设置下一步动作

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/frontend/test_jobs_board.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/app.py tests/frontend/test_jobs_board.py
git commit -m "feat: add opportunity board filters and batch actions"
```

### Task 8: 新增个人画像页面

**Files:**
- Modify: `frontend/app.py`
- Create: `tests/frontend/test_profile_page.py`

**Step 1: 写失败测试**

```python
from frontend.app import default_profile_form


def test_default_profile_form_contains_phase1_fields():
    form = default_profile_form()

    assert "target_roles" in form
    assert "salary_min" in form
```

**Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/frontend/test_profile_page.py -q`
Expected: FAIL，因为画像页面辅助函数不存在

**Step 3: 最小实现**

画像页支持：
- 编辑目标岗位
- 编辑目标城市
- 编辑薪资区间
- 编辑核心技能
- 编辑项目亮点
- 编辑禁投条件

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/frontend/test_profile_page.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/app.py tests/frontend/test_profile_page.py
git commit -m "feat: add candidate profile page"
```

### Task 9: 保留扩展录入链路并接入新岗位模型

**Files:**
- Modify: `extension/popup.js`
- Modify: `backend/server.py`
- Create: `tests/extension/test_popup_phase1.py`

**Step 1: 写失败测试**

```python
from pathlib import Path


def test_popup_posts_to_import_endpoint_for_opportunity_pipeline():
    source = Path("extension/popup.js").read_text(encoding="utf-8")

    assert "/api/import-page" in source
    assert "next_action" in source or "待评估" in source
```

**Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/extension/test_popup_phase1.py -q`
Expected: FAIL，因为扩展尚未适配新模型

**Step 3: 最小实现**

要求：
- 扩展录入的岗位自动进入 `待评估`
- 自动设置默认下一步动作
- 保留现有页面抓取能力，但输出写入新岗位模型

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/extension/test_popup_phase1.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add extension/popup.js backend/server.py tests/extension/test_popup_phase1.py
git commit -m "feat: adapt browser capture to phase 1 opportunity model"
```

### Task 10: 增加阶段验收与环境检查

**Files:**
- Create: `scripts/doctor.py`
- Create: `tests/backend/test_doctor.py`
- Modify: `docs/plans/2026-04-09-phase-1-job-ops-rebuild.md`

**Step 1: 写失败测试**

```python
from scripts.doctor import run_checks


def test_run_checks_reports_required_services():
    result = run_checks()

    assert "database" in result
    assert "api" in result
```

**Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_doctor.py -q`
Expected: FAIL，因为诊断脚本不存在

**Step 3: 最小实现**

检查项：
- SQLite 文件是否存在
- 核心表是否存在
- API 是否能启动
- Excel 导出路径是否可写
- Streamlit 入口是否存在

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/backend/test_doctor.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/doctor.py tests/backend/test_doctor.py docs/plans/2026-04-09-phase-1-job-ops-rebuild.md
git commit -m "chore: add phase 1 doctor checks and acceptance guardrails"
```

### 第一阶段完成标准

- 已建立 SQLite 主存储
- 已完成旧 Excel 数据迁移
- 已具备个人画像基础页与接口
- 已完成岗位池主表升级
- 已具备状态流转和时间线
- 已完成首页与岗位池基础改造
- 已保留扩展录入能力并接入新模型
- 已具备基础环境诊断能力

### 第一阶段建议执行顺序

1. Task 1-2：先搭好数据库和画像基础
2. Task 3-5：完成岗位模型升级和旧数据迁移
3. Task 6-8：完成首页、岗位池、画像页
4. Task 9：接回扩展录入
5. Task 10：补诊断和验收
