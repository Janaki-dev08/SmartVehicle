@echo off
title Autonomous Vehicle Platform - Frontend Development Server
echo ==============================================================================
echo Starting React Vite Frontend Server (Port 5173)...
echo ==============================================================================

cd /d "%~dp0\frontend"

node -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Node.js is not detected on this system.
    echo Opening the integrated web dashboard hosted directly by the backend at http://localhost:8000 ...
    start http://localhost:8000
    pause
    exit /b 0
)

npm run dev
pause
