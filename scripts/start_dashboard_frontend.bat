@echo off
setlocal

cd /d "%~dp0\..\frontend"
if not exist "..\var\log" mkdir "..\var\log"

npm run dev >> "..\var\log\dashboard-frontend.log" 2>&1
