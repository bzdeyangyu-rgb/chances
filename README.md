# Chances 求职作战台

Chances 是一个本地优先的个人求职工作台。它不是简单保存岗位链接，而是把招聘网站里的岗位机会整理成可导入、可审查、可评分、可准备、可追踪、可复盘的个人机会池。

当前项目服务的主线是：**AI 产品经理 / 企业提效 / AI 工作流 / Agent 工具方向求职**。工程能力、AIGC 内容生产、UE5/Maya/3DGS 和建筑/BIM 经验作为差异化补充。

## 当前状态

更新时间：2026-06-13

- 当前版本：`1.0.0-local`
- 产品状态：个人自用稳定版，功能冻结，只进行缺陷修复和必要维护。
- 技术架构：FastAPI + SQLite + Streamlit + Chrome MV3 扩展。
- 数据策略：SQLite 是主数据源，Excel 是导出层，截图是岗位证据层。
- 前端入口：`frontend/app.py`
- 后端入口：`backend/server.py`
- 数据库默认路径：`data/jobs.db`
- Excel 默认路径：`data/jobs.xlsx`
- 截图默认目录：`data/captures/`
- 稳定启动入口：`Start-Chances.cmd`
- 停止入口：`Stop-Chances.cmd`
- 备份入口：`Backup-Chances.cmd`
- 最近一次完整测试：见发布验收记录。

## 核心流程

Chances 的日常使用流程是：

1. 从招聘网站采集岗位，或手动录入岗位。
2. 外部导入的岗位先进入审查区，人工接受或拒绝。
3. 进入岗位池后，对岗位做筛选、分页、状态更新和优先级管理。
4. 打开岗位详情，查看画像匹配、岗位价值信号、评分历史、截图证据和简历改写建议。
5. 为值得推进的岗位生成准备包，包括简历角度、项目亮点、HR 问题、面试准备、沟通草稿和风险回应。
6. 记录投递事件、沟通事件、面试事件和跟进任务。
7. 每周复盘岗位状态、停滞项、未完成任务和下一步动作。

## 已实现能力

### 1. 岗位采集与导入

支持三种岗位进入方式：

- Chrome 扩展在招聘网站详情页采集正文、结构化字段和截图。
- 手动通过后端 API 或前端录入岗位。
- 通过导入审查区接收外部候选岗位，例如 BOSS 只读导入桥。

当前支持的平台识别包括：

- BOSS 直聘
- 猎聘
- 拉勾
- 智联招聘
- 手动录入

所有外部导入岗位都建议先进入审查区，由用户确认后再写入正式岗位池。

### 2. 岗位池

岗位池支持：

- 状态筛选
- 优先级筛选
- 关键词搜索
- 分页显示
- 批量状态更新
- 详情查看
- 状态时间线
- Excel 导出

当前岗位状态包括：

- 待评估、建议推进、暂缓、不推荐
- 待准备材料、待沟通、已沟通
- 待投递、已投递
- 待约面、一面、二面、三面、人事面、终面、待结果
- 已拿到意向、已拿到录用、已拒绝、已放弃、已归档

### 3. 个人画像与简历导入

个人画像保存这些信息：

- 目标岗位
- 目标城市
- 远程偏好
- 薪资底线
- 理想薪资
- 核心技能
- 项目亮点
- 禁投条件

支持从 PDF、TXT、Markdown 简历中提取画像字段。当前默认简历方向聚焦 AI 产品经理，并把 AI 应用工程、AIGC 工作流、UE5/Maya、3DGS、Codex/Claude Code、BIM/CAD 等作为能力标签。

### 4. 岗位匹配与统一评分

项目里现在有两层判断：

- `profile_match`：基于个人画像的即时匹配，返回匹配分、推荐结论、优势、风险和建议动作。
- `job_score_snapshots`：统一评分历史，适合反复评估和复盘。

评分考虑：

- 岗位名称和目标方向是否匹配
- 技能关键词是否命中
- 城市和办公方式是否符合偏好
- 薪资是否覆盖底线
- 行业和成长信号
- 禁投规则
- 岗位信息是否缺失

相关文件：

- `backend/profile_tools.py`
- `backend/evaluation.py`

### 5. 岗位价值信号与市场摘要

项目吸收了 `ai-job-seeker` 的市场分析思路，但保留现有本地架构。

首页会从当前岗位池提取市场摘要：

- 薪资样本数
- 薪资均值
- 薪资上限
- 高频关键词
- 城市分布

岗位详情会显示岗位价值信号：

- 画像匹配分
- 岗位薪资中位数与当前岗位池均值对比
- 是否命中 AI 工作流、Agent、企业提效等主线关键词
- 是否符合南京优先策略
- 是否存在偏算法工程、偏离 AI 产品主线的风险

相关文件：

- `frontend/app.py`
- `tests/frontend/test_market_insights.py`

### 6. 简历改写建议

岗位详情里会根据岗位文本和个人画像生成项目内简历建议。

当前简历主定位：

```text
AI产品经理 / 企业提效 / AI工作流
```

主打案例方向：

- Codex / Claude Code 辅助排障、脚本/插件开发、自动化检查。
- AI 效能与业务拓展报告，包含 3DGS + UE5 + AI 视频模型路线图。

输出内容包括：

- 主定位
- 主打案例
- 改写方向
- 证据缺口
- 下一步补充材料

后续如果需要，可以再扩展成 Markdown、Word 或 PDF 简历版本。

### 7. 岗位准备包

准备包用于把“这个岗位该怎么投”沉淀下来。

内容包括：

- 简历投递角度
- 项目亮点
- HR 沟通问题
- 面试准备
- 沟通草稿
- 风险回应

相关文件：

- `backend/materials.py`
- `tests/backend/test_materials_generator.py`

### 8. 投递事件和跟进任务

岗位详情支持记录：

- 已投递
- 已打招呼
- HR 回复
- 已约面
- 已面试
- 拒绝
- Offer
- 放弃

也可以为每个岗位创建跟进任务，例如：

- 明天跟进 HR 回复
- 补一版简历角度
- 准备面试问题
- 判断是否归档

周复盘会聚合未完成任务和停滞岗位。

### 9. 周复盘

周复盘页面会汇总：

- 岗位总数
- 待推进岗位
- 高优岗位
- 已投递岗位
- 状态分布
- 投递事件统计
- 未完成任务
- 停滞岗位
- 推荐下一步动作

相关文件：

- `backend/db.py`
- `frontend/app.py`
- `tests/backend/test_weekly_review_api.py`
- `tests/frontend/test_weekly_review_view.py`

### 10. 搜索预设与导入审查区

搜索预设用于固定常用搜索条件，例如：

```text
南京 AI 产品经理 15K+
南京 Agent 工具 产品经理
杭州 AI 工作流 产品
```

导入审查区用于承接外部候选岗位。候选岗位可以被：

- 接受：写入正式岗位池。
- 拒绝：记录拒绝原因。
- 标记疑似重复：避免重复写入。

相关文件：

- `backend/boss_agent_bridge.py`
- `tests/backend/test_import_review_api.py`
- `tests/frontend/test_search_and_import_view.py`

### 11. 视觉截图和视觉摘要

Chrome 扩展会保存岗位页面截图。后端可以基于岗位字段、截图摘要和页面标题生成确定性视觉摘要。

当前版本还没有接入 OCR 或多模态模型，因此视觉摘要只能作为辅助线索，不能替代原始岗位文本和截图。

相关文件：

- `backend/visual_summary.py`
- `tests/backend/test_visual_summary_regeneration.py`

## 页面说明

Streamlit 前端包含这些页面：

- 首页总览：求职画像、今日动作、机会总览、市场摘要、重点岗位、跟进提醒。
- 岗位池：岗位筛选、分页、批量更新、岗位详情、评分、准备包、投递事件和任务。
- 搜索与导入：搜索预设、导入候选岗位、重复审查、接受或拒绝。
- 周复盘：统计、停滞岗位、未完成任务、下一步建议。
- 个人画像：简历导入、关键词画像、画像编辑。

## 项目结构

```text
backend/
  server.py              FastAPI 入口和 API 路由
  db.py                  SQLite 表结构、迁移、查询和业务写入
  browser_import.py      招聘页面文本解析、URL 规范化和 Excel 写入
  profile_tools.py       简历提取、画像推导、基础岗位匹配
  evaluation.py          统一岗位评分规则
  materials.py           岗位准备包生成
  visual_summary.py      视觉摘要生成
  boss_agent_bridge.py   BOSS 只读导入桥

frontend/
  app.py                 Streamlit 工作台
  labels.py              中文 UI 文案、状态枚举、字段顺序
  data_store.py          Excel 兼容层

extension/
  manifest.json          Chrome MV3 扩展配置
  popup.html             扩展弹窗
  popup.js               扩展采集流程
  content.js             页面字段提取

scripts/
  doctor.py              本地健康检查
  seed_demo_workflow.py  演示数据生成脚本
  import_urls_with_chrome.py
  generate_excel_template.ps1

docs/plans/
  2026-06-08-practical-job-hunting-foundation.md
  其他历史规划文档

tests/
  backend/
  frontend/
  extension/
```

## 主要 API

### 岗位

- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs`
- `POST /api/jobs/{job_id}/status`
- `POST /api/jobs/bulk-status`
- `GET /api/jobs/{job_id}/timeline`

### 评分和评估

- `POST /api/jobs/{job_id}/evaluate`
- `POST /api/jobs/{job_id}/score`
- `GET /api/jobs/{job_id}/score-history`

### 准备包

- `POST /api/jobs/{job_id}/materials`
- `POST /api/jobs/{job_id}/materials/generate`

### 投递事件和任务

- `POST /api/jobs/{job_id}/application-events`
- `GET /api/jobs/{job_id}/application-events`
- `POST /api/jobs/{job_id}/tasks`
- `GET /api/tasks`
- `POST /api/tasks/{task_id}/complete`

### 画像和简历

- `GET /api/profile`
- `POST /api/profile`
- `POST /api/profile/import-resume`

### 导入

- `POST /api/import-page`
- `POST /api/import-visual-page`
- `POST /api/import-review/candidates`
- `POST /api/import-review/boss-agent-envelope`
- `GET /api/import-review/candidates`
- `POST /api/import-review/candidates/{candidate_id}/accept`
- `POST /api/import-review/candidates/{candidate_id}/reject`

### 搜索预设

- `GET /api/search-presets`
- `POST /api/search-presets`
- `DELETE /api/search-presets/{preset_id}`

### 周复盘

- `GET /api/reviews/weekly`

## 运行方式

### 1. 准备环境

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 一键启动

双击项目根目录下的：

```text
Start-Chances.cmd
```

脚本会先启动并检查后端，再启动前端。日常使用只打开：

```text
http://127.0.0.1:8501
```

`http://127.0.0.1:8000` 是后端接口，不是产品页面。

也可以在 PowerShell 中启动：

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts\start_chances.ps1
```

### 3. 停止和状态检查

停止项目：

```text
Stop-Chances.cmd
```

检查运行状态：

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts\status_chances.ps1
```

### 4. 数据备份与恢复

创建备份：

```text
Backup-Chances.cmd
```

备份保存在 `backups/`，包含 SQLite 数据库、截图和必要配置。

恢复前请先停止项目，然后选择一个备份目录：

```powershell
.\.venv\Scripts\python.exe scripts\restore_chances.py `
  backups\chances-YYYYMMDD-HHMMSS-ffffff --yes
```

恢复脚本会先自动备份当前数据，再验证备份完整性，最后才替换本地数据。

### 5. 加载 Chrome 扩展

1. 打开 Chrome 的 `chrome://extensions`。
2. 打开“开发者模式”。
3. 点击“加载已解压的扩展程序”。
4. 选择本仓库的 `extension/` 目录。
5. 先启动后端 API，再在支持的招聘网站岗位页点击扩展采集。

### 6. 健康检查

先启动项目，再执行：

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
```

### 7. 自动化测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 演示数据

演示脚本：

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo_workflow.py
```

默认是 dry-run，不会写数据库。

写入独立演示库：

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo_workflow.py --apply --db data\demo_jobs.db
```

脚本会拒绝直接写入真实默认库 `data/jobs.db`。

## 安全边界

项目必须坚持：

- 不自动点击“立即沟通”。
- 不自动批量打招呼。
- 不自动投递。
- 不自动聊天。
- 不自动交换联系方式。
- 不绕过招聘网站安全校验。
- 不把截图摘要当成唯一事实来源。
- 不把 CLI 当作主系统，CLI 只能作为导入通道。

人工确认仍然是正式投递、沟通和接受岗位的边界。

## 当前限制

- 岗位价值信号和市场摘要基于当前本地岗位池，样本少时只能作为参考。
- 视觉摘要还没有 OCR 或多模态模型。
- Word/PDF 简历导出还没有正式实现，目前优先在项目内展示简历改写建议。
- 邮件、日历、外部自动提醒还没有接入项目内部；当前提醒主要依赖 Codex 自动化和周复盘。
- BOSS 只读导入桥需要本机额外安装 `boss-agent-cli` 才能接入；没有安装时不影响主流程。

## 维护边界

`1.0.0-local` 已冻结功能范围。后续只处理：

- 阻断日常使用的缺陷。
- 招聘网站页面变化导致的扩展兼容问题。
- 数据备份、恢复和迁移问题。
- Python、Streamlit、FastAPI 等依赖升级造成的兼容问题。
- 中文文案、错误提示和易用性问题。

当前不继续增加招聘网站、OCR、多模态模型、邮件日历、React 前端或新的分析功能。

遇到问题请先查看 `docs/troubleshooting.md`，完整自测步骤见
`docs/acceptance/personal-workflow-checklist.md`。
