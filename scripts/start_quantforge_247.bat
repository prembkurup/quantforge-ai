@echo off
setlocal

cd /d "%~dp0\.."
if not exist "var\log" mkdir "var\log"

if exist "var\quantforge_247.pid" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$qfPid = Get-Content 'var\quantforge_247.pid' -ErrorAction SilentlyContinue; if ($qfPid -and (Get-Process -Id $qfPid -ErrorAction SilentlyContinue)) { exit 10 }"
  if errorlevel 10 (
    echo QuantForge AI 24/7 supervisor is already running.
    echo Status: var\quantforge_247_status.json
    exit /b 0
  )
)

set PYTHONPATH=%CD%\backend
start "QuantForge AI 24-7" /min ".venv\Scripts\python.exe" ".\scripts\quantforge_247.py" %*

echo QuantForge AI 24/7 supervisor starting.
echo Status: var\quantforge_247_status.json
echo Logs: var\log\
