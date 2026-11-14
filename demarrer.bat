@echo off
chcp 65001 >nul
title MediAI
cd /d "%~dp0"
rem Opens the browser once the interface has had time to start, then runs both servers here.
start "" /b cmd /c "timeout /t 12 /nobreak >nul && start http://localhost:3000"
npm run dev
pause
