# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

这是一个本地求职作战台，采用单仓结构，包含三个协作模块：

- `frontend/`：Streamlit 前端（主入口 `frontend/app.py`），负责岗位池、画像、评估与周复盘页面。
- `backend/`：FastAPI 接口层（主入口 `backend/server.py`），负责岗位导入、状态流转、画像管理、评估与复盘聚合。
- `extension/`：Chrome MV3 扩展（`popup.js` + `content.js`），负责在招聘网站页面抓取结构化字段与截图，并调用本地 API 导入。

数据层采用“双写”模型：

- SQLite：主业务库（默认 `data/jobs.db`），保存岗位主表、时间线、评估、截图资产、候选人画像。
- Excel：兼容导入导出链路（默认 `data/jobs.xlsx`），在 API 导入时同步写入。

## 常用命令

### 环境准备

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

### 启动服务

```bash
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload
```

```bash
streamlit run frontend/app.py
```

前端默认通过 `CHANCES_API_BASE_URL` 访问 API（默认 `http://127.0.0.1:8000`）。

### 测试

先确保已激活虚拟环境；若未激活，可直接使用 `.venv` 解释器运行。

运行全部测试：

```bash
python -m pytest
```

按模块运行：

```bash
python -m pytest tests/backend
python -m pytest tests/frontend
python -m pytest tests/extension
```

运行单个测试文件：

```bash
python -m pytest tests/backend/test_visual_import_api.py
```

运行单个测试用例：

```bash
python -m pytest tests/backend/test_server.py::test_post_import_page_rejects_verification_pages
```

未激活虚拟环境时可用：

```bash
.venv/Scripts/python -m pytest tests/backend/test_server.py::test_post_import_page_rejects_verification_pages
```

### 本地健康检查

```bash
python scripts/doctor.py
```

### Chrome 扩展调试

扩展为纯静态 MV3 目录，无打包步骤。通过 Chrome `chrome://extensions` -> 开发者模式 -> “加载已解压的扩展程序”，选择 `extension/` 目录。

## 高层架构与关键流

### 1) 视觉导入主链路（扩展 -> API -> DB/Excel）

1. 扩展 `popup.js` 给当前页面发送 `capture-page` 消息；若 content script 尚未注入，先通过 `chrome.scripting.executeScript` 注入 `content.js`。
2. `content.js` 按站点（Boss/Liepin/Lagou/Zhaopin）解析 DOM，产出 `extracted_job` 与 `capture_targets`。
3. `popup.js` 逐段滚动并截图，组装 `screenshots` 后调用 `POST /api/import-visual-page`。
4. `backend/server.py` 在 `/api/import-visual-page` 中先复用 `import_page_capture` 做文本导入；若岗位标题缺失则走 `build_visual_fallback_job` 兜底。
5. `backend/db.py` 的 `upsert_job_record` 去重写入 `jobs`，`save_job_capture_assets` 落盘截图到 `data/captures/` 并写入 `job_capture_assets`。
6. 同时生成 `visual_summary`，前端岗位详情页读取 `/api/jobs/{id}` 时展示岗位、时间线、评估、截图资产与画像匹配结果。

### 2) 数据模型与职责边界

- `backend/db.py`：唯一数据库访问层，负责建表/迁移、upsert、状态流转、批量更新、评估、周复盘统计。
- `backend/browser_import.py`：招聘页面文本解析与标准化（URL canonicalize、反爬/验证页识别、站点字段抽取）。
- `backend/profile_tools.py`：简历文本抽取（PDF/TXT/MD）、关键词提取、画像生成、岗位匹配打分。
- `frontend/data_store.py`：Excel 初始化与标准化读写，保障列顺序和缺失列补齐。

### 3) 状态与评估系统

- 岗位主状态、优先级、下一步动作保存在 `jobs` 表。
- 每次状态更新会写入 `job_actions` 时间线，供详情页与复盘使用。
- 评估结果保存在 `job_evaluations`，画像匹配由 `build_profile_match` 动态计算。

## 修改时的注意点

- 涉及导入流程时，优先同时查看：`extension/popup.js`、`extension/content.js`、`backend/server.py`、`backend/browser_import.py`、`backend/db.py`，这几处是强耦合链路。
- `backend/server.py` 的 `create_app()` 会根据 `workbook_path` 推导 `db_path`；测试通过临时路径隔离数据，不要破坏该行为。
- URL 去重依赖 `canonicalize_job_url()` 去掉 query；改动去重规则时要同步关注 `tests/backend/test_server.py` 与 `tests/backend/test_browser_import.py`。
- 新增截图类型时，需同步更新：`extension/content.js` 目标生成、`extension/popup.js` 分段截图、`backend/db.py` 的 `CAPTURE_ASSET_LABELS` 与摘要生成逻辑。
