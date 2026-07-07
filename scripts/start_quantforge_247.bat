@echo off
setlocal

cd /d "%~dp0\.."
if not exist "var\log" mkdir "var\log"
echo [%DATE% %TIME%] start_quantforge_247 invoked >> "var\log\quantforge-247-launcher.log"

if exist "var\quantforge_247.pid" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$qfPid = Get-Content 'var\quantforge_247.pid' -ErrorAction SilentlyContinue; if ($qfPid -and (Get-Process -Id $qfPid -ErrorAction SilentlyContinue)) { exit 10 }"
  if errorlevel 10 (
    echo [%DATE% %TIME%] supervisor already running >> "var\log\quantforge-247-launcher.log"
    echo QuantForge AI 24/7 supervisor is already running.
    echo Status: var\quantforge_247_status.json
    exit /b 0
  )
)

set PYTHONPATH=%CD%\backend
start "QuantForge AI 24-7" /min ".venv\Scripts\python.exe" ".\scripts\quantforge_247.py" %*
echo [%DATE% %TIME%] supervisor start command issued >> "var\log\quantforge-247-launcher.log"

echo QuantForge AI 24/7 supervisor starting.
echo Status: var\quantforge_247_status.json
echo Logs: var\log\
