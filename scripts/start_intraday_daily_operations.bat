@echo off
setlocal
cd /d "%~dp0\.."
".venv\Scripts\python.exe" ".\scripts\intraday_daily_operations.py" %*
