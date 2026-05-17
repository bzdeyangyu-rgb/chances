---
name: boss-import-flow
description: 当用户需要把 BOSS直聘岗位页面采集并导入当前项目本地岗位库时使用。覆盖“打开本地API、扩展采集、导入结果核验、失败排障”全流程，适用于 zhipin.com 职位页。
---

# Boss 页面采集导入流程（本项目专用）

## 何时使用

当用户表达以下意图时触发：

- “把这个 Boss 岗位导入作战台”
- “采集当前招聘页面并入库”
- “扩展抓岗位信息后写入本地 DB/Excel”
- “Boss 采集失败，帮我排障”

## 固定前提（先检查）

1. 后端 API 已启动：`python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload`
2. Chrome 扩展已加载 `extension/` 目录（开发者模式）
3. 当前页面是 BOSS 职位详情或职位列表（`zhipin.com`）

## 执行主流程

### Step 1：健康检查 API

请求：`GET http://127.0.0.1:8000/api/jobs`

- 可返回 JSON 列表：继续
- 连接失败：先启动后端，再继续

### Step 2：触发扩展采集

在扩展弹窗点击“采集/导入”按钮（由 `extension/popup.js` 驱动）：

- content script 提取结构化字段：`capture-page`
- 分段截图：`capture_targets`
- 调用本地接口：`POST /api/import-visual-page`

请求体核心字段：

- `url`
- `title`
- `body_lines`
- `extracted_job`
- `screenshots[]`

## 导入结果判定

按扩展返回状态文案判断：

- `created`：新岗位已入库
- `duplicate`：岗位已存在，仅补充截图
- `updated`：岗位存在，字段已按最新页面更新
- `visual_fallback`：结构化标题缺失，走视觉兜底生成岗位

## 结果核验

1. 访问 `GET /api/jobs`，确认岗位出现或更新时间变化
2. 访问 `GET /api/jobs/{id}`，确认：
   - `job` 基本字段存在
   - `assets` 有截图记录
   - `timeline` 有“通过视觉截图导入岗位”或同类动作

## 常见故障与处理

### 1) “未能从当前页面提取岗位信息”

处理：

- 刷新目标页后重试
- 确认当前 tab 是 Boss 页面，而不是验证页/空白页
- 确认 content script 已成功注入（扩展重载后重试）

### 2) 接口报错 `本地接口返回 xxx` 或连接失败

处理：

- 先确认 `uvicorn` 在 8000 端口运行
- 检查 `popup.js` 的 API 地址是否仍是 `http://127.0.0.1:8000/api/import-visual-page`
- 若端口变化，修改扩展常量并重载扩展

### 3) 命中 Boss 安全校验页（`/security-check`、`/verify-slider`）

处理：

- 立即切换人工处理验证
- 验证通过后回到职位页再触发采集

## 与项目代码的对应关系

- 扩展入口与导入调用：`extension/popup.js`
- 页面提取规则：`extension/content.js`
- 视觉导入接口：`backend/server.py` 中 `/api/import-visual-page`
- 截图与资产落库：`backend/db.py` 的 `save_job_capture_assets`

## 交付准则

只要满足以下三点，即视为流程成功：

1. `/api/import-visual-page` 返回成功（created/duplicate/updated/visual_fallback）
2. `/api/jobs/{id}` 可查询到岗位
3. `assets` 非空或状态明确说明无需新增截图
