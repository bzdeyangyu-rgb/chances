# 求职基石落地实施计划

> **给 Codex/Claude：** 实施本计划时必须使用 `executing-plans` skill，按任务逐项执行、逐项验证，不要跳步。

**目标：** 把 Chances 从“已经能用的本地岗位看板”升级成一个能长期支撑真实求职的基础系统，覆盖搜索、导入、筛选、评估、准备材料、投递追踪和周复盘。

**架构：** 保留当前 FastAPI + SQLite + Streamlit + Chrome 扩展架构。SQLite 继续作为主数据源，Excel 作为导出层，截图作为岗位证据层，BOSS 相关能力作为可选导入通道，不替代现有扩展和本地工作台。

**技术栈：** Python 3.13、FastAPI、SQLite、Streamlit、pandas、httpx、pytest、Chrome Extension MV3、可选 `boss-agent-cli`

---

## 为什么这份计划要覆盖旧计划

现有阶段计划已经完成了很多基础：

- 第一阶段已经完成 SQLite、个人画像、岗位主表、状态流转和首页/岗位池骨架。
- 第二阶段已经完成岗位详情、岗位评估存储、批量状态、周复盘和诊断脚本。
- 视觉采集方案已经落下了截图保存和 `/api/import-visual-page`。
- README 已经整理了当前状态：6 条岗位、1 条画像、3 条动作记录、0 条正式评估、9 个截图资产，以及现有测试通过。

下一步的核心问题不再是“能不能存岗位”，而是“这个系统能不能成为真实求职期间每天打开、每天推进、每周复盘的基石”。

所以这份计划把后续工作收束成一个闭环：

1. 用搜索预设发现岗位。
2. 从 BOSS、Chrome 扩展、手动录入等来源导入候选岗位。
3. 进入导入审查区，先去重、筛掉明显不合适的岗位。
4. 对活跃岗位使用统一评分规则。
5. 为高价值岗位生成投递准备包。
6. 记录投递、沟通、面试、拒信、offer 等事件。
7. 每周复盘：哪些岗位该推进，哪些该放弃，哪些需要准备材料。

## 参考来源

外部参考：

- `can4hou6joeng4/boss-agent-cli`：作为 BOSS 模块的一号参考，重点参考只读搜索、详情、导出、JSON 输出协议、诊断能力和安全边界。
- `lastsunday/job-hunting`：作为国内招聘插件参考，重点参考 BOSS 页面行为、插件体验、列表性能、标签/备注和大数据量风险。
- `DaKheera47/job-ops`：作为长期产品路线参考，重点参考 Search -> Score -> Tailor -> Export -> Track 的完整求职流程。

本地参考：

- `README.md`：当前项目状态和已完成能力。
- `docs/plans/2026-04-09-phase-1-job-ops-rebuild.md`：已完成的岗位运营数据基础。
- `docs/plans/2026-04-09-phase-2-personal-job-assistant.md`：已完成的岗位详情、评估和周复盘基础。
- `docs/plans/2026-04-09-visual-job-capture-plan.md`：截图优先、证据优先的采集策略。
- `.agents/skills/bosszhipin/SKILL.md`：BOSS 求职者视角操作规则、URL 优先搜索、安全页兜底和人工确认边界。

## 产品边界

这些边界不能破：

- 不自动点击 BOSS 的“立即沟通”。
- 不自动批量打招呼。
- 不自动投递。
- 不自动聊天。
- 不自动交换联系方式。
- 不绕过 `/security-check`、滑块验证或其他安全校验。
- 不把截图摘要当成唯一真相，必须保留原图证据和原始字段。
- 不把当前项目重写成 CLI；CLI 只能作为导入通道，工作台仍然是主界面。
- 不做复杂公司 CRM，只做个人求职者真正需要的推进工具。

## 目标日常流程

最终系统应该支持这个真实使用路径：

1. 打开本地工作台。
2. 选择搜索预设，例如“南京 AI 产品经理 15K+”或“杭州 Agent 工程师”。
3. 从 BOSS 或扩展导入 10-30 个候选岗位。
4. 在导入审查区快速拒绝明显不合适的岗位。
5. 把值得看的岗位加入活跃机会池。
6. 对活跃岗位执行统一评分。
7. 为高分岗位生成准备包：简历角度、项目亮点、HR 问题、风险回应、下一步动作。
8. 记录投递、沟通、面试、拒信、offer、放弃等事件。
9. 每周复盘，决定下周该继续找、该投、该跟进、该放弃的岗位。

## 数据模型方向

保留现有表：

- `candidate_profile`
- `jobs`
- `job_actions`
- `job_evaluations`
- `job_capture_assets`

新增工作流表：

- `search_presets`：搜索预设。
- `search_runs`：每次搜索执行记录。
- `job_import_events`：导入批次和原始数据。
- `job_review_decisions`：导入审查决策。
- `evaluation_rubrics`：评分规则版本。
- `job_score_snapshots`：每次评分快照。
- `job_materials`：岗位准备包。
- `application_events`：投递和沟通事件。
- `job_tasks`：跟进任务。

`jobs` 表继续表示岗位当前状态；新增表负责记录历史、过程、材料和后续行动。

## 推荐执行顺序

1. 先做岗位池分页和真实数据量支持。
2. 再做统一评分规则。
3. 再做岗位准备包。
4. 再做投递事件和跟进任务。
5. 再做周复盘。
6. 再接 BOSS 导入桥和导入审查区。
7. 最后强化视觉摘要、诊断脚本和演示数据。

原因：如果先大量导入 BOSS 岗位，但没有评分、材料和追踪能力，只会得到一个更大的岗位堆。求职基石的重点不是“采得多”，而是“能判断、能准备、能推进”。

---

## 里程碑 0：固定计划和基线

### 任务 0.1：把本计划写入 README 索引

**文件：**

- 修改：`README.md`
- 验证：`docs/plans/2026-06-08-practical-job-hunting-foundation.md`

**步骤 1：更新 README 的规划文档列表**

加入：

```markdown
- `2026-06-08-practical-job-hunting-foundation.md`：可实际应用的求职基石总计划。
```

**步骤 2：检查 diff 范围**

运行：

```powershell
git diff -- README.md docs/plans/2026-06-08-practical-job-hunting-foundation.md --stat
```

预期：只包含 README 和本计划文件。

**步骤 3：提交**

```powershell
git add README.md docs/plans/2026-06-08-practical-job-hunting-foundation.md
git commit -m "docs: add practical job hunting foundation plan"
```

---

## 里程碑 1：让岗位池能承载真实数据量

### 任务 1.1：后端增加分页和稳定查询

**文件：**

- 修改：`backend/db.py`
- 修改：`backend/server.py`
- 新增：`tests/backend/test_job_list_query_api.py`

**步骤 1：写失败测试**

```python
def test_jobs_api_supports_pagination_and_status_filter(client):
    for index in range(25):
        client.post("/api/jobs", json={
            "platform": "manual",
            "job_title": f"AI产品经理 {index}",
            "company_name": "示例科技",
            "job_url": f"https://example.com/jobs/{index}",
        })

    response = client.get("/api/jobs", params={
        "page": 2,
        "page_size": 10,
        "status": "待评估",
    })

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 25
    assert payload["page"] == 2
    assert len(payload["items"]) == 10
```

**步骤 2：确认失败**

运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_job_list_query_api.py -q
```

预期：失败，因为 `GET /api/jobs` 当前还是直接返回列表。

**步骤 3：实现查询层**

在 `backend/db.py` 增加：

- `list_jobs_page(...)`
- 支持 `page`
- 支持 `page_size`
- 支持 `status`
- 支持 `priority`
- 支持 `keyword`
- 支持 `platform`
- 支持 `has_screenshots`

返回结构：

```python
{
    "items": [...],
    "total": 25,
    "page": 2,
    "page_size": 10,
}
```

**步骤 4：更新 API**

在 `backend/server.py` 更新 `GET /api/jobs`：

- 增加查询参数。
- 返回分页 envelope。
- 同步更新前端读取逻辑。

**步骤 5：运行测试**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_job_list_query_api.py tests/backend/test_jobs_api.py -q
```

预期：通过。

**步骤 6：提交**

```powershell
git add backend/db.py backend/server.py tests/backend/test_job_list_query_api.py
git commit -m "feat: add paginated job list queries"
```

### 任务 1.2：前端岗位池支持分页和快速审查

**文件：**

- 修改：`frontend/app.py`
- 新增：`tests/frontend/test_jobs_pagination_view.py`

**步骤 1：写失败测试**

```python
from frontend.app import normalize_jobs_response


def test_normalize_jobs_response_accepts_paginated_envelope():
    payload = {
        "items": [{"id": 1, "job_title": "AI产品经理"}],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }

    rows, meta = normalize_jobs_response(payload)

    assert rows[0]["job_title"] == "AI产品经理"
    assert meta["total"] == 1
```

**步骤 2：确认失败**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/frontend/test_jobs_pagination_view.py -q
```

预期：失败。

**步骤 3：实现前端辅助函数**

在 `frontend/app.py` 增加：

- `normalize_jobs_response(payload)`
- `build_page_options(total, page_size)`
- `build_review_queue(rows)`

**步骤 4：更新岗位池 UI**

`render_jobs_board(...)` 增加：

- 每页数量。
- 页码选择。
- “待评估优先”快捷筛选。
- 搜索、状态、优先级筛选保留。
- 详情面板继续按岗位 ID 加载。

**步骤 5：运行测试**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/frontend/test_jobs_pagination_view.py tests/frontend/test_jobs_board.py -q
```

预期：通过。

**步骤 6：提交**

```powershell
git add frontend/app.py tests/frontend/test_jobs_pagination_view.py
git commit -m "feat: add paginated job pool view"
```

---

## 里程碑 2：增加搜索预设和 BOSS 导入桥

### 任务 2.1：增加搜索预设存储

**文件：**

- 修改：`backend/db.py`
- 修改：`backend/server.py`
- 新增：`tests/backend/test_search_presets_api.py`

**步骤 1：写失败测试**

```python
def test_search_preset_can_be_saved_and_listed(client):
    payload = {
        "name": "南京 AI 产品经理",
        "platform": "boss",
        "city": "南京",
        "query": "AI产品经理",
        "salary": "15K+",
        "filters_json": "{\"city_code\":\"101190100\"}",
    }

    created = client.post("/api/search-presets", json=payload)
    listed = client.get("/api/search-presets")

    assert created.status_code == 200
    assert listed.json()[0]["name"] == "南京 AI 产品经理"
```

**步骤 2：确认失败**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_search_presets_api.py -q
```

预期：失败。

**步骤 3：新增表**

在 `initialize_database(...)` 增加 `search_presets`：

- `id`
- `name`
- `platform`
- `city`
- `query`
- `salary`
- `filters_json`
- `is_active`
- `created_at`
- `updated_at`

**步骤 4：新增 DB 函数**

- `save_search_preset(payload, db_path)`
- `list_search_presets(db_path)`
- `delete_search_preset(preset_id, db_path)`

**步骤 5：新增 API**

- `GET /api/search-presets`
- `POST /api/search-presets`
- `DELETE /api/search-presets/{preset_id}`

**步骤 6：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_search_presets_api.py -q
git add backend/db.py backend/server.py tests/backend/test_search_presets_api.py
git commit -m "feat: add job search presets"
```

### 任务 2.2：增加只读 BOSS Agent CLI 桥

**文件：**

- 新增：`backend/boss_agent_bridge.py`
- 新增：`tests/backend/test_boss_agent_bridge.py`
- 视情况修改：`requirements.txt`

**步骤 1：写失败测试**

```python
from backend.boss_agent_bridge import parse_boss_agent_envelope


def test_parse_boss_agent_envelope_extracts_jobs():
    raw = {
        "ok": True,
        "schema_version": "1.0",
        "command": "search",
        "data": {
            "jobs": [{
                "title": "AI产品经理",
                "company": "示例科技",
                "salary": "15-25K",
                "location": "南京",
                "url": "https://www.zhipin.com/job_detail/example.html",
            }]
        },
    }

    jobs = parse_boss_agent_envelope(raw)

    assert jobs[0]["job_title"] == "AI产品经理"
    assert jobs[0]["platform"] == "boss"
```

**步骤 2：确认失败**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_boss_agent_bridge.py -q
```

预期：失败。

**步骤 3：实现解析和命令构造**

实现：

- `parse_boss_agent_envelope(raw)`
- `boss_agent_available()`
- `build_boss_search_command(preset, limit)`
- `validate_boss_command(command)`

单元测试里不要真的调用外部 CLI。

**步骤 4：加入安全边界测试**

```python
from backend.boss_agent_bridge import validate_boss_command


def test_boss_bridge_blocks_contact_actions():
    assert validate_boss_command("search") is True
    assert validate_boss_command("detail") is True
    assert validate_boss_command("greet") is False
    assert validate_boss_command("apply") is False
    assert validate_boss_command("chat") is False
```

**步骤 5：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_boss_agent_bridge.py -q
git add backend/boss_agent_bridge.py tests/backend/test_boss_agent_bridge.py
git commit -m "feat: add read-only boss agent bridge"
```

### 任务 2.3：增加导入审查区

**文件：**

- 修改：`backend/db.py`
- 修改：`backend/server.py`
- 新增：`tests/backend/test_import_review_api.py`

**步骤 1：写失败测试**

```python
def test_import_candidates_are_reviewed_before_activation(client):
    response = client.post("/api/import-review/candidates", json={
        "source": "boss_agent",
        "items": [{
            "platform": "boss",
            "job_title": "AI产品经理",
            "company_name": "示例科技",
            "job_url": "https://www.zhipin.com/job_detail/example.html",
        }],
    })

    inbox = client.get("/api/import-review/candidates")

    assert response.status_code == 200
    assert inbox.json()[0]["decision"] == "pending"
```

**步骤 2：新增表**

增加：

- `job_import_events`
- `job_review_decisions`

字段包括：

- `source`
- `raw_payload_json`
- `normalized_job_json`
- `canonical_url`
- `duplicate_job_id`
- `decision`
- `reason`
- `created_at`
- `decided_at`

**步骤 3：新增 API**

- `POST /api/import-review/candidates`
- `GET /api/import-review/candidates`
- `POST /api/import-review/candidates/{id}/accept`
- `POST /api/import-review/candidates/{id}/reject`

接受候选岗位时，写入或更新 `jobs`。

**步骤 4：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_import_review_api.py -q
git add backend/db.py backend/server.py tests/backend/test_import_review_api.py
git commit -m "feat: add import review inbox"
```

### 任务 2.4：前端增加搜索预设和导入审查页面

**文件：**

- 修改：`frontend/app.py`
- 修改：`frontend/labels.py`
- 新增：`tests/frontend/test_search_and_import_view.py`

**步骤 1：写失败测试**

```python
from frontend.app import build_import_candidate_summary


def test_build_import_candidate_summary_marks_duplicates():
    row = {
        "job_title": "AI产品经理",
        "company_name": "示例科技",
        "duplicate_job_id": 12,
    }

    summary = build_import_candidate_summary(row)

    assert "重复" in summary
```

**步骤 2：实现前端辅助函数**

在 `frontend/app.py` 增加：

- `build_import_candidate_summary(row)`
- `group_import_candidates(rows)`
- `build_preset_display_name(preset)`

**步骤 3：增加 UI**

增加“搜索预设 / 导入审查”视图：

- 展示搜索预设。
- 新建/编辑预设。
- 展示导入候选岗位。
- 显示重复提示。
- 支持接受/拒绝。
- 不在 UI 中默认自动运行 BOSS CLI，除非 doctor 检查通过且用户主动触发。

**步骤 4：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/frontend/test_search_and_import_view.py -q
git add frontend/app.py frontend/labels.py tests/frontend/test_search_and_import_view.py
git commit -m "feat: add search preset and import review UI"
```

---

## 里程碑 3：让岗位评估可重复、可解释、可追踪

### 任务 3.1：增加版本化评分规则

**文件：**

- 新增：`backend/evaluation.py`
- 修改：`backend/db.py`
- 修改：`backend/server.py`
- 新增：`tests/backend/test_evaluation_rubric.py`

**步骤 1：写失败测试**

```python
from backend.evaluation import evaluate_job_against_profile


def test_evaluation_rubric_scores_role_city_salary_and_no_go_rules():
    profile = {
        "target_roles": "AI产品经理",
        "target_cities": "南京",
        "salary_min": "15K",
        "core_skills": "AIGC、PRD、AI工作流",
        "no_go_rules": "纯销售",
    }
    job = {
        "job_title": "AI产品经理",
        "location": "南京",
        "salary_raw": "18-25K",
        "main_text": "负责 AIGC 产品规划和 PRD 输出",
    }

    result = evaluate_job_against_profile(profile, job)

    assert result["score"] >= 80
    assert result["recommendation"] in {"强烈推进", "建议推进"}
```

**步骤 2：实现评分规则 v1**

评分维度：

- 岗位方向匹配：30 分。
- 技能关键词匹配：25 分。
- 城市和办公方式：15 分。
- 薪资匹配：15 分。
- 行业/成长信号：10 分。
- 禁投规则命中：最高扣 40 分。
- 关键信息缺失：最高扣 15 分。

返回字段：

- `score`
- `recommendation`
- `strengths`
- `risks`
- `missing_information`
- `next_step_hint`
- `rubric_version`

**步骤 3：新增评分快照表**

新增 `job_score_snapshots`：

- `id`
- `job_id`
- `score`
- `recommendation`
- `result_json`
- `rubric_version`
- `created_at`

**步骤 4：新增 API**

- `POST /api/jobs/{job_id}/score`
- `GET /api/jobs/{job_id}/score-history`

**步骤 5：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_evaluation_rubric.py tests/backend/test_job_evaluation_api.py -q
git add backend/evaluation.py backend/db.py backend/server.py tests/backend/test_evaluation_rubric.py
git commit -m "feat: add versioned job evaluation rubric"
```

### 任务 3.2：前端增加评分复核视图

**文件：**

- 修改：`frontend/app.py`
- 新增：`tests/frontend/test_evaluation_view.py`

**步骤 1：写失败测试**

```python
from frontend.app import build_score_badge


def test_build_score_badge_maps_score_to_label():
    assert build_score_badge(88)["label"] == "强烈推进"
    assert build_score_badge(35)["label"] == "暂不投入"
```

**步骤 2：实现 UI**

岗位详情页增加：

- 评分 badge。
- 优势列表。
- 风险列表。
- 缺失信息列表。
- “重新评分”按钮。
- “生成准备包”下一步入口。

**步骤 3：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/frontend/test_evaluation_view.py tests/frontend/test_job_detail_view.py -q
git add frontend/app.py tests/frontend/test_evaluation_view.py
git commit -m "feat: add evaluation review UI"
```

---

## 里程碑 4：建立岗位准备包

### 任务 4.1：增加岗位准备包存储

**文件：**

- 修改：`backend/db.py`
- 修改：`backend/server.py`
- 新增：`tests/backend/test_job_materials_api.py`

**步骤 1：写失败测试**

```python
def test_job_material_pack_can_be_saved_and_loaded(client):
    created = client.post("/api/jobs", json={
        "platform": "manual",
        "job_title": "AI产品经理",
        "company_name": "示例科技",
        "job_url": "https://example.com/jobs/materials",
    }).json()

    saved = client.post(f"/api/jobs/{created['id']}/materials", json={
        "resume_angle": "突出 AIGC 产品规划和跨团队推进",
        "project_highlights": "AI 工作流、UE5 管线、PRD 输出",
        "recruiter_questions": "团队 AI 产品目前在哪个阶段？",
        "interview_prep": "准备一个 AI 工作流落地案例",
    })

    detail = client.get(f"/api/jobs/{created['id']}")

    assert saved.status_code == 200
    assert detail.json()["materials"]["resume_angle"].startswith("突出")
```

**步骤 2：新增表**

新增 `job_materials`：

- `job_id`
- `resume_angle`
- `project_highlights`
- `recruiter_questions`
- `interview_prep`
- `communication_draft`
- `risk_response`
- `updated_at`

**步骤 3：新增 API**

- `POST /api/jobs/{job_id}/materials`
- `GET /api/jobs/{job_id}` 中包含 `materials`

**步骤 4：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_job_materials_api.py -q
git add backend/db.py backend/server.py tests/backend/test_job_materials_api.py
git commit -m "feat: add job materials storage"
```

### 任务 4.2：增加确定性准备包生成器

**文件：**

- 新增：`backend/materials.py`
- 修改：`backend/server.py`
- 新增：`tests/backend/test_materials_generator.py`

**步骤 1：写失败测试**

```python
from backend.materials import build_preparation_pack


def test_build_preparation_pack_uses_profile_and_job():
    profile = {"project_highlights": "AI工作流；UE5管线", "core_skills": "PRD、AIGC"}
    job = {"job_title": "AI产品经理", "main_text": "负责需求分析、产品规划和AI落地"}
    score = {"risks": ["缺少医疗行业经验"], "strengths": ["AI方向匹配"]}

    pack = build_preparation_pack(profile, job, score)

    assert "AI工作流" in pack["project_highlights"]
    assert "医疗行业经验" in pack["risk_response"]
```

**步骤 2：实现生成器**

第一版不接外部 AI，先做确定性模板：

- 简历投递角度。
- 3 条项目亮点。
- HR 问题。
- 面试准备清单。
- 风险回应。
- 沟通草稿占位。

**步骤 3：新增 API**

新增：

- `POST /api/jobs/{job_id}/materials/generate`

该接口读取：

- 个人画像。
- 岗位详情。
- 最新评分。

然后生成并保存准备包。

**步骤 4：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_materials_generator.py tests/backend/test_job_materials_api.py -q
git add backend/materials.py backend/server.py tests/backend/test_materials_generator.py
git commit -m "feat: generate job preparation packs"
```

### 任务 4.3：前端增加准备包视图

**文件：**

- 修改：`frontend/app.py`
- 新增：`tests/frontend/test_materials_view.py`

**步骤 1：写失败测试**

```python
from frontend.app import build_materials_completion


def test_build_materials_completion_counts_required_fields():
    materials = {
        "resume_angle": "A",
        "project_highlights": "",
        "recruiter_questions": "Q",
    }

    result = build_materials_completion(materials)

    assert result["completed"] == 2
```

**步骤 2：实现 UI**

岗位详情页增加：

- 准备包完成度。
- 可编辑字段。
- “生成准备包”按钮。
- “复制投递准备摘要”文本区。

**步骤 3：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/frontend/test_materials_view.py -q
git add frontend/app.py tests/frontend/test_materials_view.py
git commit -m "feat: add job preparation materials UI"
```

---

## 里程碑 5：增加投递事件和跟进任务

### 任务 5.1：增加投递事件时间线

**文件：**

- 修改：`backend/db.py`
- 修改：`backend/server.py`
- 新增：`tests/backend/test_application_events_api.py`

**步骤 1：写失败测试**

```python
def test_application_event_can_be_added_to_job(client):
    created = client.post("/api/jobs", json={
        "platform": "manual",
        "job_title": "AI产品经理",
        "company_name": "示例科技",
        "job_url": "https://example.com/jobs/application",
    }).json()

    event = client.post(f"/api/jobs/{created['id']}/application-events", json={
        "event_type": "applied",
        "channel": "BOSS直聘",
        "note": "已手动投递",
    })

    detail = client.get(f"/api/jobs/{created['id']}")

    assert event.status_code == 200
    assert detail.json()["application_events"][0]["event_type"] == "applied"
```

**步骤 2：新增表**

新增 `application_events`：

- `id`
- `job_id`
- `event_type`
- `channel`
- `note`
- `event_at`
- `created_at`

`event_type` 可选：

- `applied`
- `greeted`
- `replied`
- `interview_scheduled`
- `interview_done`
- `rejected`
- `offer`
- `abandoned`

**步骤 3：新增 API**

- `POST /api/jobs/{job_id}/application-events`
- `GET /api/jobs/{job_id}/application-events`
- `GET /api/jobs/{job_id}` 中包含 `application_events`

**步骤 4：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_application_events_api.py -q
git add backend/db.py backend/server.py tests/backend/test_application_events_api.py
git commit -m "feat: add application event timeline"
```

### 任务 5.2：增加跟进任务

**文件：**

- 修改：`backend/db.py`
- 修改：`backend/server.py`
- 新增：`tests/backend/test_job_tasks_api.py`

**步骤 1：写失败测试**

```python
def test_job_task_can_be_created_and_completed(client):
    created = client.post("/api/jobs", json={
        "platform": "manual",
        "job_title": "AI产品经理",
        "company_name": "示例科技",
        "job_url": "https://example.com/jobs/task",
    }).json()

    task = client.post(f"/api/jobs/{created['id']}/tasks", json={
        "title": "明天跟进 HR 回复",
        "due_date": "2026-06-09",
    }).json()

    done = client.post(f"/api/tasks/{task['id']}/complete")

    assert done.status_code == 200
    assert done.json()["status"] == "done"
```

**步骤 2：新增表**

新增 `job_tasks`：

- `id`
- `job_id`
- `title`
- `due_date`
- `status`
- `created_at`
- `completed_at`

`status` 可选：

- `open`
- `done`
- `canceled`

**步骤 3：新增 API**

- `POST /api/jobs/{job_id}/tasks`
- `GET /api/tasks`
- `POST /api/tasks/{task_id}/complete`

**步骤 4：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_job_tasks_api.py -q
git add backend/db.py backend/server.py tests/backend/test_job_tasks_api.py
git commit -m "feat: add job follow-up tasks"
```

### 任务 5.3：前端增加投递追踪视图

**文件：**

- 修改：`frontend/app.py`
- 修改：`frontend/labels.py`
- 新增：`tests/frontend/test_application_tracker_view.py`

**步骤 1：写失败测试**

```python
from frontend.app import build_application_stage_summary


def test_build_application_stage_summary_counts_events():
    events = [
        {"event_type": "applied"},
        {"event_type": "replied"},
        {"event_type": "applied"},
    ]

    summary = build_application_stage_summary(events)

    assert summary["applied"] == 2
```

**步骤 2：实现 UI**

岗位详情页增加：

- 投递事件表单。
- 投递事件时间线。
- 跟进任务列表。
- 完成任务按钮。

首页增加：

- 今日到期任务。
- 逾期任务。
- 超过 7 天未推进岗位。

**步骤 3：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/frontend/test_application_tracker_view.py -q
git add frontend/app.py frontend/labels.py tests/frontend/test_application_tracker_view.py
git commit -m "feat: add application tracker UI"
```

---

## 里程碑 6：让视觉证据从“保存”升级成“可复核”

### 任务 6.1：增加视觉摘要重生成接口

**文件：**

- 新增：`backend/visual_summary.py`
- 修改：`backend/db.py`
- 修改：`backend/server.py`
- 新增：`tests/backend/test_visual_summary_regeneration.py`

**步骤 1：写失败测试**

```python
from backend.visual_summary import build_structured_visual_summary


def test_build_structured_visual_summary_has_fixed_sections():
    job = {"job_title": "AI产品经理", "company_name": "示例科技"}
    screenshots = [{"asset_type": "description", "excerpt": "负责 AI 产品规划"}]

    summary = build_structured_visual_summary(job, screenshots)

    assert "岗位摘要" in summary
    assert "风险提示" in summary
```

**步骤 2：实现第一版摘要生成**

第一版不接 OCR，只使用：

- 岗位字段。
- 截图 `excerpt`。
- 页面标题。

输出固定结构：

- 岗位摘要。
- 核心职责。
- 任职要求。
- 公司概况。
- 福利与亮点。
- 风险提示。

**步骤 3：新增 API**

- `POST /api/jobs/{job_id}/visual-summary/regenerate`

接口职责：

- 读取岗位。
- 读取截图资产。
- 重建摘要。
- 更新 `jobs.visual_summary`。
- 设置 `visual_summary_status = ready`。

**步骤 4：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_visual_summary_regeneration.py tests/backend/test_visual_import_api.py -q
git add backend/visual_summary.py backend/db.py backend/server.py tests/backend/test_visual_summary_regeneration.py
git commit -m "feat: add visual summary regeneration"
```

### 任务 6.2：前端优化截图复核视图

**文件：**

- 修改：`frontend/app.py`
- 新增：`tests/frontend/test_visual_assets_view.py`

**步骤 1：写失败测试**

```python
from frontend.app import group_capture_assets


def test_group_capture_assets_orders_key_assets():
    assets = [
        {"asset_type": "company", "file_path": "company.png"},
        {"asset_type": "hero", "file_path": "hero.png"},
    ]

    grouped = group_capture_assets(assets)

    assert grouped[0]["asset_type"] == "hero"
```

**步骤 2：实现 UI**

岗位详情页展示顺序：

1. 视觉摘要。
2. 岗位截图。
3. 职责截图。
4. 公司截图。
5. 原始字段。
6. 时间线。

增加：

- “重新生成视觉提要”按钮。
- 没有截图时的清晰空状态。

**步骤 3：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/frontend/test_visual_assets_view.py tests/frontend/test_job_detail_view.py -q
git add frontend/app.py tests/frontend/test_visual_assets_view.py
git commit -m "feat: improve visual evidence review UI"
```

---

## 里程碑 7：让周复盘能指导下一步行动

### 任务 7.1：扩展周复盘 API

**文件：**

- 修改：`backend/db.py`
- 修改：`backend/server.py`
- 修改：`tests/backend/test_weekly_review_api.py`

**步骤 1：扩展测试**

```python
def test_weekly_review_returns_actionable_sections(client):
    response = client.get("/api/reviews/weekly")

    assert response.status_code == 200
    payload = response.json()
    assert "pipeline_counts" in payload
    assert "stalled_jobs" in payload
    assert "open_tasks" in payload
    assert "recommendations" in payload
```

**步骤 2：实现复盘字段**

新增：

- 本周导入数。
- 本周评估数。
- 本周投递数。
- 回复/面试/offer/拒信统计。
- 未完成任务。
- 逾期任务。
- 7 天未推进岗位。
- 高分待推进岗位。
- 下周建议动作。

**步骤 3：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_weekly_review_api.py -q
git add backend/db.py backend/server.py tests/backend/test_weekly_review_api.py
git commit -m "feat: expand weekly review insights"
```

### 任务 7.2：前端增加周复盘页面

**文件：**

- 修改：`frontend/app.py`
- 修改：`frontend/labels.py`
- 新增：`tests/frontend/test_weekly_review_view.py`

**步骤 1：写失败测试**

```python
from frontend.app import build_weekly_review_recommendations


def test_build_weekly_review_recommendations_mentions_stalled_jobs():
    payload = {"stalled_jobs": [{"job_title": "AI产品经理"}], "open_tasks": []}

    result = build_weekly_review_recommendations(payload)

    assert any("AI产品经理" in item for item in result)
```

**步骤 2：实现 UI**

新增“周复盘”视图：

- 本周漏斗。
- 本周动作。
- 待办和逾期任务。
- 停滞岗位。
- 高价值机会。
- 建议下一步动作。

**步骤 3：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/frontend/test_weekly_review_view.py -q
git add frontend/app.py frontend/labels.py tests/frontend/test_weekly_review_view.py
git commit -m "feat: add weekly review UI"
```

---

## 里程碑 8：强化诊断和真实操作能力

### 任务 8.1：扩展 doctor 检查

**文件：**

- 修改：`scripts/doctor.py`
- 修改：`tests/backend/test_doctor.py`

**步骤 1：扩展测试**

```python
from scripts.doctor import run_checks


def test_doctor_reports_boss_bridge_and_data_counts():
    result = run_checks()

    assert "boss_agent_cli" in result
    assert "data_counts" in result
```

**步骤 2：实现检查项**

增加：

- 数据库表存在性。
- 各表数据量。
- 截图目录数量。
- README 和主计划是否存在。
- 可选 `boss-agent-cli` 是否可用。
- `.claude/skills/bosszhipin/` Junction 是否存在。

**步骤 3：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_doctor.py -q
git add scripts/doctor.py tests/backend/test_doctor.py
git commit -m "chore: expand doctor checks for practical workflow"
```

### 任务 8.2：增加端到端演示数据脚本

**文件：**

- 新增：`scripts/seed_demo_workflow.py`
- 新增：`tests/backend/test_seed_demo_workflow.py`
- 修改：`README.md`

**步骤 1：写失败测试**

```python
from scripts.seed_demo_workflow import build_demo_records


def test_build_demo_records_contains_full_workflow():
    records = build_demo_records()

    assert records["jobs"]
    assert records["materials"]
    assert records["application_events"]
    assert records["tasks"]
```

**步骤 2：实现脚本**

生成一个完整演示流程：

- 一个导入候选岗位。
- 一个已接受岗位。
- 一个已评分岗位。
- 一个准备包。
- 一个投递事件。
- 一个跟进任务。

默认不覆盖真实 `data/jobs.db`，只有传入 `--apply` 时才写入指定数据库。

**步骤 3：补 README**

加入：

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo_workflow.py --db data/demo_jobs.db --apply
```

**步骤 4：运行测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_seed_demo_workflow.py -q
git add scripts/seed_demo_workflow.py tests/backend/test_seed_demo_workflow.py README.md
git commit -m "chore: add demo workflow seed"
```

---

## 里程碑 9：最终验收

### 任务 9.1：完整验证

**文件：**

- 只验证，不改文件。

**步骤 1：运行健康检查**

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
```

预期：

- 数据库正常。
- 前端入口正常。
- 后端入口正常。
- 导出路径正常。
- 数据量统计存在。
- BOSS 桥状态有明确结果。

**步骤 2：运行完整测试**

```powershell
.\.venv\Scripts\python.exe -m pytest
```

预期：全部通过。

**步骤 3：手动烟测**

启动后端：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload
```

启动前端：

```powershell
.\.venv\Scripts\streamlit.exe run frontend\app.py
```

手动检查：

- 首页能打开。
- 岗位池能分页。
- 岗位详情能打开。
- 评分能生成。
- 准备包能生成。
- 投递事件能新增。
- 跟进任务能完成。
- 周复盘能给出下一步建议。

## 完成标准

这份计划完成时，项目应该达到：

- 可以导入或审查 BOSS 候选岗位，但不会自动沟通或自动投递。
- 岗位池能承载至少 500 条岗位，筛选和分页不卡。
- 每个活跃岗位都能用统一版本规则评分。
- 每个值得推进的岗位都有准备包。
- 投递事件和跟进任务能在岗位详情和首页看到。
- 周复盘能给出具体下一步，而不是只显示数字。
- 完整测试通过。
- `scripts/doctor.py` 能报告实际求职工作流状态。

## 第一批执行建议

优先做这三块：

1. **岗位池分页和快速审查**：解决未来数据量问题。
2. **评分规则 v1**：让每个岗位能用同一把尺判断。
3. **准备包生成**：让系统真正帮你投前准备，而不是只存信息。

BOSS 导入桥建议放在这三块之后，因为导入更多岗位只有在下游能消化时才有价值。
