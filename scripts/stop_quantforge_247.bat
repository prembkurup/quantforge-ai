@echo off
setlocal

cd /d "%~dp0\.."

if not exist "var\quantforge_247.pid" (
  echo QuantForge 24/7 supervisor PID file not found.
  goto stop_children
)

set /p QF_PID=<"var\quantforge_247.pid"
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-Process -Id %QF_PID% -ErrorAction SilentlyContinue) { Stop-Process -Id %QF_PID% -Force; Write-Output 'Stopped QuantForge 24/7 supervisor PID %QF_PID%.' } else { Write-Output 'QuantForge 24/7 supervisor PID %QF_PID% is not running.' }"

:stop_children
powershell -NoProfile -ExecutionPolicy Bypass -Command "$repo=(Resolve-Path '.').Path; $patterns='quantforge_247.py|serve_dashboard_api|vite|full_history_research_worker|historical_validation_worker|always_on_research_orchestrator|live_trading.py|intraday_daily_scheduler.py|portfolio_intelligence.py|performance_learning.py|strategy_lifecycle.py'; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like ('*' + $repo + '*') -and $_.CommandLine -match $patterns -and $_.Name -notmatch 'powershell|cmd' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; 8000,5175 | ForEach-Object { Get-NetTCPConnection -LocalPort $_ -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }"
