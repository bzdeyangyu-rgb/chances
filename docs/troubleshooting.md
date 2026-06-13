# Chances 故障排查

## 页面地址

- 产品页面：`http://127.0.0.1:8501`
- 后端健康接口：`http://127.0.0.1:8000/api/health`
- `8000` 返回 JSON 是正常现象，但它不是前端页面。

## 前端显示“接口未连接”

1. 关闭旧的前后端窗口。
2. 双击项目根目录的 `Start-Chances.cmd`。
3. 等待浏览器打开 `http://127.0.0.1:8501`。
4. 仍然失败时，运行 `Check-Chances.cmd`。
5. 查看 `runtime/uvicorn.stderr.log` 和 `runtime/streamlit.stderr.log`。

## 扩展显示“本地服务未启动”

1. 先双击 `Start-Chances.cmd`。
2. 浏览器访问 `http://127.0.0.1:8000/api/health`。
3. 确认返回 `"status": "ok"`。
4. 在 Chrome 扩展管理页重新加载扩展。
5. 回到受支持的岗位详情页重试。

## `8501` 页面打不开

运行：

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts\status_chances.ps1
```

如果前端显示 `stopped`，查看 `runtime/streamlit.stderr.log`。

## 数据库锁定

1. 双击 `Stop-Chances.cmd`。
2. 确认没有其他工具打开 `data/jobs.db`。
3. 再次双击 `Start-Chances.cmd`。

不要直接用文件复制覆盖正在运行的数据库。备份请使用 `Backup-Chances.cmd`。

## 截图无法显示

- 检查 `data/captures/` 是否存在。
- 检查岗位详情返回的截图路径是否仍指向该目录。
- 从最近的 `backups/` 备份恢复时，截图会和数据库一起恢复。

## 备份和恢复

备份：

```text
Backup-Chances.cmd
```

恢复前先停止项目：

```powershell
.\.venv\Scripts\python.exe scripts\restore_chances.py `
  backups\chances-YYYYMMDD-HHMMSS-ffffff --yes
```

恢复脚本会先保存当前状态。如果备份无效，当前数据库不会被替换。

## 完整健康检查

先启动项目，再运行：

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
```

`boss-agent-cli` 是可选能力，未安装不会影响核心系统健康。
