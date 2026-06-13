from pathlib import Path

from scripts.runtime_chances import (
    BACKEND_PID_FILE,
    FRONTEND_PID_FILE,
    build_backend_command,
    build_frontend_command,
)


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_commands_use_production_servers_without_reload():
    backend = build_backend_command()
    frontend = build_frontend_command()

    assert backend[:3] == ["-m", "uvicorn", "backend.server:app"]
    assert "--reload" not in backend
    assert frontend[:3] == ["-m", "streamlit", "run"]
    assert "frontend/app.py" in frontend


def test_runtime_uses_separate_recorded_pid_files():
    assert BACKEND_PID_FILE.name == ".uvicorn.pid"
    assert FRONTEND_PID_FILE.name == ".streamlit.pid"


def test_powershell_wrappers_delegate_to_runtime_manager():
    start = (ROOT / "scripts" / "start_chances.ps1").read_text(encoding="utf-8")
    stop = (ROOT / "scripts" / "stop_chances.ps1").read_text(encoding="utf-8")
    status = (ROOT / "scripts" / "status_chances.ps1").read_text(encoding="utf-8")

    assert "runtime_chances.py" in start and "start" in start
    assert "runtime_chances.py" in stop and "stop" in stop
    assert "runtime_chances.py" in status and "status" in status
