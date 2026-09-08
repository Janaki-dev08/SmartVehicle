@echo off
title Autonomous Vehicle Platform - Launcher
echo ==============================================================================
echo Launching Autonomous Vehicle Simulation Platform
echo Project: Adaptive Path Planning and Collision Avoidance on Indian Roads
echo ==============================================================================

cd /d "%~dp0"

echo Launching Backend Server...
start "AV Backend (FastAPI)" cmd /c "start_backend.bat"

echo Waiting for backend initialization...
timeout /t 3 /nobreak >nul

echo Opening Autonomous Vehicle Dashboard in Browser...
start http://localhost:8000

echo ==============================================================================
echo System running! 
echo Dashboard URL: http://localhost:8000
echo WebSocket Stream: ws://localhost:8000/ws/telemetry
echo ==============================================================================
