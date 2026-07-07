@echo off
setlocal

cd /d "%~dp0\.."

if not exist "var\quantforge_247_status.json" (
  echo QuantForge 24/7 status file not found.
  exit /b 1
)

type "var\quantforge_247_status.json"
