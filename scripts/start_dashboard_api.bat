@echo off
setlocal

cd /d "%~dp0\.."
if not exist "var\log" mkdir "var\log"

set PYTHONPATH=%CD%\backend
".venv\Scripts\python.exe" ".\scripts\serve_dashboard_api.py" >> "var\log\dashboard-api.log" 2>&1
