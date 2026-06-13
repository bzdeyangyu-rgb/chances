from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = ROOT / ".venv" / "Scripts" / "python.exe"
RUNTIME_DIR = ROOT / "runtime"
DATABASE_PATH = ROOT / "data" / "jobs.db"
BACKEND_PID_FILE = ROOT / ".uvicorn.pid"
FRONTEND_PID_FILE = ROOT / ".streamlit.pid"
BACKEND_HEALTH_URL = "http://127.0.0.1:8000/api/health"
FRONTEND_URL = "http://127.0.0.1:8501"


def build_backend_command() -> list[str]:
    return [
        "-m",
        "uvicorn",
        "backend.server:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]


def build_frontend_command() -> list[str]:
    return [
        "-m",
        "streamlit",
        "run",
        "frontend/app.py",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        "8501",
    ]


def endpoint_ready(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def wait_for_endpoint(url: str, timeout_seconds: int) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if endpoint_ready(url):
            return True
        time.sleep(0.5)
    return False


def _creation_flags() -> int:
    if os.name != "nt":
        return 0
    return (
        subprocess.CREATE_NEW_PROCESS_GROUP
        | subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NO_WINDOW
    )


def _spawn(command: list[str], stdout_name: str, stderr_name: str) -> subprocess.Popen[bytes]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    stdout_path = RUNTIME_DIR / stdout_name
    stderr_path = RUNTIME_DIR / stderr_name
    stdout_handle = stdout_path.open("ab")
    stderr_handle = stderr_path.open("ab")
    try:
        return subprocess.Popen(
            [str(PYTHON_EXE), *command],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=_creation_flags(),
            close_fds=True,
        )
    finally:
        stdout_handle.close()
        stderr_handle.close()


def _write_pid(path: Path, process_id: int) -> None:
    path.write_text(str(process_id), encoding="ascii")


def _read_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="ascii").strip())
    except ValueError:
        path.unlink(missing_ok=True)
        return None


def _process_command_line(process_id: int) -> str:
    if os.name != "nt":
        return ""
    command = (
        f"(Get-CimInstance Win32_Process -Filter \"ProcessId = {process_id}\" "
        "-ErrorAction SilentlyContinue).CommandLine"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=5,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    return result.stdout.strip()


def _stop_recorded_process(pid_file: Path, expected_token: str, display_name: str) -> None:
    process_id = _read_pid(pid_file)
    if process_id is None:
        print(f"{display_name}：没有记录到运行进程")
        return

    command_line = _process_command_line(process_id)
    if not command_line:
        pid_file.unlink(missing_ok=True)
        print(f"{display_name}：已经停止")
        return
    if expected_token not in command_line:
        raise RuntimeError(
            f"{display_name} 的进程号 {process_id} 属于其他程序，已拒绝停止"
        )

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process_id), "/T", "/F"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
    else:
        os.kill(process_id, signal.SIGTERM)
    pid_file.unlink(missing_ok=True)
    print(f"{display_name}：已停止")


def start(wait_seconds: int = 40, open_browser: bool = True) -> int:
    if not PYTHON_EXE.exists():
        raise FileNotFoundError(f"未找到项目虚拟环境：{PYTHON_EXE}")

    if not endpoint_ready(BACKEND_HEALTH_URL):
        print("正在启动后端服务...")
        backend = _spawn(
            build_backend_command(),
            "uvicorn.stdout.log",
            "uvicorn.stderr.log",
        )
        _write_pid(BACKEND_PID_FILE, backend.pid)
        if not wait_for_endpoint(BACKEND_HEALTH_URL, wait_seconds):
            raise RuntimeError("后端启动失败，请查看 runtime/uvicorn.stderr.log")
    print(f"后端服务已就绪：{BACKEND_HEALTH_URL}")

    if not endpoint_ready(FRONTEND_URL):
        print("正在启动前端页面...")
        frontend = _spawn(
            build_frontend_command(),
            "streamlit.stdout.log",
            "streamlit.stderr.log",
        )
        _write_pid(FRONTEND_PID_FILE, frontend.pid)
        if not wait_for_endpoint(FRONTEND_URL, wait_seconds):
            raise RuntimeError("前端启动失败，请查看 runtime/streamlit.stderr.log")
    print(f"前端页面已就绪：{FRONTEND_URL}")

    if open_browser:
        webbrowser.open(FRONTEND_URL)
    return 0


def stop() -> int:
    _stop_recorded_process(FRONTEND_PID_FILE, "streamlit", "前端")
    _stop_recorded_process(BACKEND_PID_FILE, "backend.server:app", "后端")
    return 0


def status() -> int:
    backend_ready = endpoint_ready(BACKEND_HEALTH_URL)
    frontend_ready = endpoint_ready(FRONTEND_URL)
    database_ready = DATABASE_PATH.exists()

    print("Chances 运行状态")
    print(f"后端接口：{'正常' if backend_ready else '未运行'}")
    print(f"前端页面：{'正常' if frontend_ready else '未运行'}")
    print(f"本地数据库：{'存在' if database_ready else '缺失'}")
    print(f"产品页面：{FRONTEND_URL}")
    return 0 if backend_ready and frontend_ready and database_ready else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="管理 Chances 本地求职助手")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--no-browser", action="store_true")
    start_parser.add_argument("--wait-seconds", type=int, default=40)
    subparsers.add_parser("stop")
    subparsers.add_parser("status")

    args = parser.parse_args()
    if args.command == "start":
        return start(wait_seconds=args.wait_seconds, open_browser=not args.no_browser)
    if args.command == "stop":
        return stop()
    return status()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError) as error:
        print(f"错误：{error}", file=sys.stderr)
        raise SystemExit(1)
