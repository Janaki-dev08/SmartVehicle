# Complete Installation & Setup Guide

This guide provides exact step-by-step instructions for running the autonomous vehicle simulation platform on a Windows computer.

---

## 1. Prerequisites

- **Operating System**: Windows 10 / 11 (64-bit)
- **Python**: Version 3.10, 3.11, 3.12, or 3.14
- **Node.js** (Optional for building frontend): Version 18+ (Node.js is optional because the backend includes an integrated high-performance web dashboard served directly at `http://localhost:8000`)
- **CARLA Simulator** (Optional): Version 0.9.13, 0.9.14, or 0.9.15

---

## 2. Fast Installation via Script

Run the automated installer script:

```bat
install.bat
```

This script will:
1. Validate Python installation.
2. Create and activate a Python virtual environment (`venv`).
3. Install all required packages from `requirements.txt`.
4. Install frontend npm dependencies if Node.js is present.
5. Create `.env` from `.env.example`.

---

## 3. Manual Installation Steps

### Step 3.1: Python Virtual Environment
Open PowerShell or Command Prompt in the project folder:
```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.2: Frontend Setup (Optional)
```powershell
cd frontend
npm install
cd ..
```

---

## 4. CARLA Simulator Integration (Optional)

1. Download CARLA Simulator from [CARLA Releases](https://github.com/carla-simulator/carla/releases) (e.g. `CARLA_0.9.14.zip`).
2. Extract the archive (e.g. to `C:\CARLA_0.9.14`).
3. Start the CARLA server:
   ```cmd
   CarlaUE4.exe -carla-server -quality-level=Low -fps=20
   ```
4. Install CARLA Python API client matching your Python version:
   ```cmd
   pip install carla
   ```

> [!NOTE]
> If CARLA Simulator is not running, the platform automatically switches to its **Integrated Standalone Simulation Engine**, allowing full testing of YOLO detection, A* planning, dynamic replanning, TTC risk estimation, and 10 Indian road scenarios without installing CARLA.

---

## 5. Starting the Platform

### Option A: One-Click Launcher (Recommended)
Double-click `start_project.bat` or run:
```cmd
start_project.bat
```

### Option B: Separate Terminals

**Terminal 1: Backend Server**
```cmd
start_backend.bat
# Or manually:
.\venv\Scripts\activate
python main.py
```

**Terminal 2: Frontend Server (if Node.js installed)**
```cmd
start_frontend.bat
```

---

## 6. Accessing the Dashboard

Open your web browser and navigate to:
- **Integrated Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Vite Dev Server** (if running): [http://localhost:5173](http://localhost:5173)
- **Interactive REST API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **WebSocket Telemetry Stream**: `ws://localhost:8000/ws/telemetry`
