@echo off
title Autonomous Vehicle Platform - Installation
echo ==============================================================================
echo Installing Dependencies for Autonomous Vehicle Simulation Platform
echo Project: Adaptive Path Planning and Collision Avoidance on Indian Roads
echo ==============================================================================

cd /d "%~dp0"

:: 1. Check Python
echo [1/3] Checking Python Installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH! Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)
python --version

:: 2. Setup Virtual Environment
echo [2/3] Setting up Python Virtual Environment (venv)...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
echo Installing Python dependencies from requirements.txt...
pip install -r requirements.txt

:: 3. Setup Frontend (if Node.js exists)
echo [3/3] Checking Node.js for Frontend Build...
node --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Node.js detected. Installing frontend npm packages...
    cd frontend
    npm install
    cd ..
) else (
    echo [NOTE] Node.js is not installed. 
    echo The backend will automatically serve the built web dashboard directly at http://localhost:8000!
)

:: Copy .env.example if .env does not exist
if not exist ".env" (
    copy .env.example .env
    echo Created .env configuration file from template.
)

echo ==============================================================================
echo Installation Complete!
echo You can now run 'start_project.bat' or 'start_backend.bat'.
echo ==============================================================================
pause
