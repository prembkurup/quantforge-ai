@echo off
setlocal

cd /d "%~dp0\.."

if not exist "var\quantforge_247_status.json" (
  echo QuantForge 24/7 status file not found.
  exit /b 1
)

type "var\quantforge_247_status.json"

echo.
echo Supervisor log:
if exist "var\log\quantforge-247-supervisor.log" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Content 'var\log\quantforge-247-supervisor.log' -Tail 40"
) else (
  echo var\log\quantforge-247-supervisor.log not found
)
