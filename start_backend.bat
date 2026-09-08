@echo off
title Autonomous Vehicle Platform - Backend Server
echo ==============================================================================
echo Starting Autonomous Vehicle FastAPI & WebSocket Server (Port 8000)...
echo ==============================================================================

cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python main.py
pause
