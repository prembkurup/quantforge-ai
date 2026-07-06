@echo off
setlocal
cd /d "%~dp0\.."
".venv\Scripts\python.exe" "scripts\always_on_research_orchestrator.py"
