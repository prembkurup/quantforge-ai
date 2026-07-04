@echo off
setlocal

cd /d "%~dp0\.."
if not exist "var\log" mkdir "var\log"

set PYTHONPATH=%CD%\backend
".venv\Scripts\python.exe" ".\scripts\full_history_research_worker.py" --max-jobs 3 --sleep-seconds 30 --error-sleep-seconds 300 --idle-sleep-seconds 900 >> "var\log\full-history-research-worker.log" 2>&1
