@echo off
setlocal

cd /d "%~dp0\.."
if not exist "var\log" mkdir "var\log"

set PYTHONPATH=%CD%\backend
".venv\Scripts\python.exe" ".\scripts\full_history_research_worker.py" >> "var\log\full-history-research-worker.log" 2>&1
