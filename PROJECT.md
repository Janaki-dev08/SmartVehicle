# PROJECT.md — SIH: Adaptive Path Planning & Collision Avoidance on Unstructured Indian Roads

## GLOBAL CONTEXT (Pinned)

Smart India Hackathon Prototype:
**"Adaptive Path Planning and Collision Avoidance for Autonomous Vehicles on Unstructured Indian Roads"**

*Working, demoable, end-to-end prototype — simulation/prototype for Indian road conditions.*

---

## Locked Architecture Decisions

1. **Frontend:** React + TypeScript + Leaflet + OpenStreetMap tiles (responsive dashboard, interactive map, live animated vehicle marker, colored obstacle markers, scenario selector).
2. **Backend:** Python 3.11 + FastAPI, Pydantic models for all request/response schemas.
3. **Global Routing:** OSRM public demo server (or OpenRouteService fallback) for source → destination road route waypoints.
4. **Local Adaptive Navigation:** RL agent operating on a simulated local corridor/grid around the global route waypoints (handling dynamic obstacles, jaywalkers, potholes, cutting vehicles).
5. **RL Algorithm:** PPO (Proximal Policy Optimization), discrete action space via Stable-Baselines3 + Gymnasium environment.
6. **Safety Layer:** Deterministic rule-based safety controller (distance-threshold emergency braking/stop override) sitting between RL output and vehicle actuation ("AI decides, safety layer guarantees").
7. **Obstacles:** Fully simulated realistic Indian road entities (jaywalking pedestrians, aggressive autorickshaws, wrong-side motorcycles, stray cattle, potholes, parked vehicles).
8. **Model Serving:** Train offline → save `.zip` policy via SB3 → FastAPI loads model at startup → pure inference at demo time.

---

## Repository Structure
```
adaptive-nav-sih/
├── frontend/                 # React + TS + Leaflet
├── backend/
│   ├── main.py
│   ├── api/                  # route, simulation, predict, metrics
│   ├── schemas/              # Pydantic models
│   └── services/
├── rl/
│   ├── environment/          # road_env.py, vehicle.py, obstacle.py, reward.py
│   ├── train.py
│   └── checkpoints/
├── safety/
│   └── safety_controller.py
├── mapping/
│   └── route.py              # OSRM client
├── scenarios/
│   └── scenarios.py          # Indian-road scenarios as structured data presets
├── tests/
├── PROJECT.md
└── README.md
```

---

## Phased Missions Roadmap

- [ ] **Mission 1:** Simulation core (`vehicle.py`, `obstacle.py`, `road_env.py` Gymnasium env + rollout test & plot)
- [ ] **Mission 2:** Reward function (`reward.py`) + Safety Controller (`safety/safety_controller.py`)
- [ ] **Mission 3:** Train PPO agent (`rl/train.py` + SB3 checkpoint + training curves & comparison artifact)
- [ ] **Mission 4:** FastAPI backend (`backend/main.py`, `api/`, `mapping/route.py` OSRM client, simulation endpoints)
- [ ] **Mission 5:** React + Leaflet frontend (Map, Waypoint Picker, Dashboard, Live WebSocket / REST Telemetry Animation)
- [ ] **Mission 6:** Indian-road scenario pack (5 presets: motorcycle cut-in, jaywalker, parked blockage, pothole, multi-obstacle)
- [ ] **Mission 7:** Baseline comparison suite (Shortest path vs Rule-based vs PPO RL agent)
- [ ] **Mission 8:** SIH presentation pack & summary artifacts
