@echo off
setlocal

cd /d "%~dp0\.."
if not exist "var\log" mkdir "var\log"

set PYTHONPATH=%CD%\backend
".venv\Scripts\python.exe" ".\scripts\full_history_research_scheduler.py" --max-jobs 3 >> "var\log\full-history-research-scheduler.log" 2>&1
