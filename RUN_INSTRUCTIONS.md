# Quickstart Run Instructions

## Autonomous Vehicle Simulation Platform
**Adaptive Path Planning and Collision Avoidance for Autonomous Vehicles on Unstructured Indian Roads**

---

> [!IMPORTANT]
> **MODE: DRIVERLESS AUTONOMOUS MODE**  
> **Human Control: DISABLED**  
> (The autonomous system directly commands steering, throttle, braking, path planning, and dynamic replanning).

---

## 10-Step Execution Guide

### STEP 1 - (Optional) Install CARLA Simulator
Download CARLA Simulator (v0.9.13 / 0.9.14 / 0.9.15) for Windows from the [CARLA GitHub Releases](https://github.com/carla-simulator/carla/releases) and extract it to a folder (e.g. `C:\CARLA_0.9.14`).

*(Note: CARLA installation is optional. If CARLA is not running, the platform's integrated standalone high-fidelity simulation engine runs automatically without crashing!)*

### STEP 2 - (Optional) Start CARLA Server
Open Command Prompt in your CARLA directory and run:
```cmd
CarlaUE4.exe -carla-server -fps=20 -quality-level=Low
```

### STEP 3 - Install Python Dependencies
Open PowerShell or Command Prompt in `d:\smartvechicles` and run:
```powershell
.\install.bat
# Or manually:
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### STEP 4 - (Optional) Install Frontend Dependencies
If you have Node.js installed:
```powershell
cd frontend
npm install
cd ..
```
*(Note: If Node.js is not installed, the backend automatically serves the complete built web application directly at `http://localhost:8000`!)*

### STEP 5 - Configure Environment Variables
Copy `.env.example` to `.env` if you haven't already:
```cmd
copy .env.example .env
```
Ensure `CARLA_HOST=localhost` and `CARLA_PORT=2000`.

### STEP 6 - Start Backend Server
Run the backend startup script:
```cmd
start_backend.bat
# Or manually:
.\venv\Scripts\activate
python main.py
```

### STEP 7 - Start Frontend Server
If using Vite dev server:
```cmd
start_frontend.bat
```
*(Or simply open `http://localhost:8000` which is served by the backend!)*

### STEP 8 - Open Autonomous Driving Dashboard
Open your browser and navigate to:
**[http://localhost:8000](http://localhost:8000)** (or [http://localhost:5173](http://localhost:5173))

### STEP 9 - Select Indian Road Scenario
In the **LEFT PANEL** of the dashboard:
- Choose from the 10 Indian road scenarios (e.g., *Scenario 2: Sudden Motorcycle Cut-In*, *Scenario 5: Auto-Rickshaw Lateral Weaving*, or *Scenario 7: Stray Animal*).
- Click **Load Scenario**.

### STEP 10 - Start Autonomous Vehicle Simulation
Click the green **START SIMULATION** button in the dashboard:
- Watch the vehicle autonomously accelerate, track obstacles with YOLO, estimate 3D distance and TTC, calculate Adaptive A* paths, execute dynamic replanning maneuvers, and come to safe emergency stops when critical threats are detected!
