@echo off
setlocal
cd /d "%~dp0\.."
".venv\Scripts\python.exe" ".\scripts\intraday_decision_intelligence.py" %*
