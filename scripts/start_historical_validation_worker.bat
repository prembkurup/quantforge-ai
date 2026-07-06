@echo off
setlocal
cd /d "%~dp0\.."
".venv\Scripts\python.exe" "scripts\historical_validation_worker.py"
