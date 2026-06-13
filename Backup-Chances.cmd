@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" scripts\backup_chances.py
if errorlevel 1 pause
