"""
routes.py — REST API Endpoints for Routing, Autonomous Simulation & Telemetry.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import csv
import io

from mapping.route import RouteManager
from backend.services.simulation_service import simulation_service
from backend.simulation.simulation_engine import SimulationEngine
from backend.schemas.models import (
    RouteRequest,
    RouteResponse,
    SimulationStartRequest,
    SimulationStartResponse,
    SimulationStepRequest,
    SimulationStepResponse,
    MetricsResponse,
    HealthResponse
)

router = APIRouter(prefix="/api", tags=["Autonomous Driving API"])
route_manager = RouteManager()

# Shared SimulationEngine instance (used by WebSocket loop & REST endpoints)
sim_engine = SimulationEngine()


# ---------------------------------------------------------------------------
# Route Planning Endpoint (OSRM Global Route)
# ---------------------------------------------------------------------------

@router.post(
    "/route",
    response_model=RouteResponse,
    summary="Fetch OSRM Route Waypoints",
    description="Computes driving route and waypoints between source and destination GPS coordinates."
)
async def get_route(req: RouteRequest) -> RouteResponse:
    result = route_manager.get_route(
        source_lat=req.source_lat,
        source_lon=req.source_lon,
        dest_lat=req.dest_lat,
        dest_lon=req.dest_lon
    )
    return RouteResponse(**result)



# ---------------------------------------------------------------------------
# CARLA Endpoints
# ---------------------------------------------------------------------------

class CarlaConnectRequest(BaseModel):
    host: str = "localhost"
    port: int = 2000


@router.get(
    "/carla/status",
    summary="CARLA Connection Status",
    description="Returns the current CARLA simulator connection state."
)
async def get_carla_status():
    return sim_engine.carla_conn.get_status()


@router.post(
    "/carla/connect",
    summary="Connect to CARLA",
    description="Attempts (or re-attempts) connection to the CARLA simulator server."
)
async def connect_carla(req: CarlaConnectRequest):
    sim_engine.carla_conn.host = req.host
    sim_engine.carla_conn.port = req.port
    success = sim_engine.try_carla_connect()
    return {
        **sim_engine.carla_conn.get_status(),
        "connected": success,
        "message": "CARLA connected successfully." if success else (
            "CARLA not reachable. Running in standalone simulation mode — "
            "full autonomous driving works without CARLA."
        )
    }


# ---------------------------------------------------------------------------
# Driver Endpoints
# ---------------------------------------------------------------------------

class DriverSetRequest(BaseModel):
    driver: str  # NONE | META | CARLA


@router.post(
    "/driver/set",
    summary="Set Active Driver Mode",
    description="Switches the active driver: NONE (driverless), META (PPO RL model), or CARLA (hardware-in-loop)."
)
async def set_driver(req: DriverSetRequest):
    valid = {"NONE", "META", "CARLA"}
    if req.driver.upper() not in valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid driver type '{req.driver}'. Must be one of: {', '.join(valid)}"
        )
    success = sim_engine.set_driver(req.driver)
    return {
        "success": success,
        "driver": sim_engine.active_driver,
        "message": f"Driver set to '{sim_engine.active_driver}'."
    }


@router.get(
    "/driver/status",
    summary="Get Active Driver Mode",
    description="Returns the currently active driver mode."
)
async def get_driver():
    return {
        "driver": sim_engine.active_driver,
        "carla_connected": sim_engine.carla_conn.is_connected
    }



# ---------------------------------------------------------------------------
# Scenario Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/scenarios",
    summary="List all available scenarios",
    description="Returns the list of 10 predefined Indian road scenarios."
)
async def get_scenarios():
    scenarios = [s.to_dict() for s in sim_engine.scenario_manager.scenarios.values()]
    return {"scenarios": scenarios, "count": len(scenarios)}


class ScenarioLoadRequest(BaseModel):
    scenario_id: str


@router.post(
    "/scenarios/load",
    summary="Load a scenario",
    description="Loads the selected scenario and resets the simulation."
)
async def load_scenario(req: ScenarioLoadRequest):
    success = sim_engine.load_scenario(req.scenario_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{req.scenario_id}' not found."
        )
    sc = sim_engine.scenario_manager.current_scenario
    return {
        "success": True,
        "scenario": sc.to_dict() if sc else None,
        "message": f"Scenario '{sc.name if sc else req.scenario_id}' loaded successfully."
    }


# ---------------------------------------------------------------------------
# Simulation Control Endpoints (Engine-level: drives the WS telemetry loop)
# ---------------------------------------------------------------------------

@router.post(
    "/simulation/engine/start",
    summary="Start the simulation engine loop",
    description="Starts the autonomous driving simulation engine."
)
async def engine_start():
    sim_engine.start_simulation()
    return {"running": sim_engine.is_running, "message": "Simulation started."}


@router.post(
    "/simulation/engine/stop",
    summary="Stop the simulation engine loop",
    description="Pauses the autonomous driving simulation engine."
)
async def engine_stop():
    sim_engine.stop_simulation()
    return {"running": sim_engine.is_running, "message": "Simulation paused."}


@router.post(
    "/simulation/engine/reset",
    summary="Reset the simulation engine",
    description="Resets vehicle state, planner, and scenario actors to initial conditions."
)
async def engine_reset():
    sim_engine.reset_simulation()
    return {"running": sim_engine.is_running, "message": "Simulation reset."}


@router.get(
    "/simulation/engine/state",
    summary="Get current simulation engine telemetry",
    description="Returns the latest telemetry snapshot from the simulation engine."
)
async def engine_state():
    return sim_engine.latest_telemetry if sim_engine.latest_telemetry else {
        "running": sim_engine.is_running,
        "message": "No telemetry yet — start the simulation first."
    }


# ---------------------------------------------------------------------------
# RL Session Endpoints (PPO model-based session management)
# ---------------------------------------------------------------------------

@router.post(
    "/simulation/start",
    response_model=SimulationStartResponse,
    summary="Start RL Simulation Session",
    description="Initializes road corridor, vehicle starting pose, and procedural Indian road obstacles."
)
async def start_simulation(req: SimulationStartRequest) -> SimulationStartResponse:
    try:
        return simulation_service.start_session(req)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start simulation session: {str(e)}"
        )


@router.post(
    "/simulation/step",
    response_model=SimulationStepResponse,
    summary="Step RL Simulation (Inference & Safety)",
    description="Advances simulation by one timestep using trained PPO policy and deterministic safety layer."
)
async def step_simulation(req: SimulationStepRequest) -> SimulationStepResponse:
    try:
        return simulation_service.step_session(req)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation step failed: {str(e)}"
        )


@router.post(
    "/simulation/stop",
    summary="Stop active RL session",
    description="Signals the current session to stop stepping."
)
async def stop_simulation():
    return {"message": "Simulation stop acknowledged.", "sessions_active": len(simulation_service.sessions)}


@router.post(
    "/simulation/reset",
    summary="Reset all RL sessions",
    description="Clears all active simulation sessions."
)
async def reset_simulation():
    simulation_service.sessions.clear()
    return {"message": "All simulation sessions reset.", "sessions_active": 0}


@router.get(
    "/simulation/state",
    summary="Get current simulation state",
    description="Returns latest engine telemetry plus RL service metrics."
)
async def simulation_state():
    return {
        "engine": sim_engine.latest_telemetry if sim_engine.latest_telemetry else {},
        "rl_service": simulation_service.get_metrics().model_dump(),
        "running": sim_engine.is_running
    }


# ---------------------------------------------------------------------------
# Metrics, Events, Results
# ---------------------------------------------------------------------------

@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Get System Metrics",
    description="Retrieves aggregate driving statistics, safety layer interventions, and model status."
)
async def get_metrics() -> MetricsResponse:
    return simulation_service.get_metrics()


@router.get(
    "/events",
    summary="Get Recent Simulation Events",
    description="Returns recent replan events and risk alerts from the engine."
)
async def get_events():
    telemetry = sim_engine.latest_telemetry
    if not telemetry:
        return {"events": [], "message": "No simulation running."}
    return {
        "events": telemetry.get("latest_replans", []),
        "risk_level": telemetry.get("risk", {}).get("level", "UNKNOWN"),
        "action": telemetry.get("action", "IDLE"),
        "step": telemetry.get("step", 0)
    }


@router.get(
    "/results",
    summary="Get Benchmark Results",
    description="Returns full metrics summary and benchmark comparison from the engine."
)
async def get_results():
    telemetry = sim_engine.latest_telemetry
    metrics = simulation_service.get_metrics()
    return {
        "engine_metrics": telemetry.get("metrics", {}) if telemetry else {},
        "benchmark": telemetry.get("benchmark", {}) if telemetry else {},
        "rl_metrics": metrics.model_dump(),
        "carla": sim_engine.carla_conn.get_status()
    }


@router.get(
    "/results/export",
    summary="Export Results as CSV",
    description="Downloads the latest simulation metrics as a CSV file."
)
async def export_results_csv():
    metrics = simulation_service.get_metrics()
    telemetry = sim_engine.latest_telemetry or {}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Sessions", metrics.total_sessions])
    writer.writerow(["Total Steps", metrics.total_steps])
    writer.writerow(["Total Interventions", metrics.total_interventions])
    writer.writerow(["Total Collisions", metrics.total_collisions])
    writer.writerow(["Goals Reached", metrics.total_goals_reached])
    writer.writerow(["Average Speed (km/h)", metrics.average_speed_kmh])
    writer.writerow(["Model Loaded", metrics.model_loaded])

    if telemetry:
        vehicle = telemetry.get("vehicle", {})
        writer.writerow(["Engine Step", telemetry.get("step", 0)])
        writer.writerow(["Engine Speed (km/h)", vehicle.get("speed_kmh", 0)])
        writer.writerow(["Total Distance (m)", telemetry.get("metrics", {}).get("total_distance_m", 0)])
        writer.writerow(["Total Replans", telemetry.get("planner", {}).get("total_replans", 0)])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=av_simulation_results.csv"}
    )


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check"
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        model_ready=simulation_service.model_loaded
    )
