"""
models.py — Pydantic Schemas for Autonomous Vehicle Simulation Backend.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple


class RouteRequest(BaseModel):
    """Request payload to query global OSRM route."""
    source_lat: float = Field(..., description="Starting latitude", example=16.3067)
    source_lon: float = Field(..., description="Starting longitude", example=80.4365)
    dest_lat: float = Field(..., description="Destination latitude", example=16.5062)
    dest_lon: float = Field(..., description="Destination longitude", example=80.6480)


class RouteResponse(BaseModel):
    """Response payload containing global route waypoints."""
    status: str
    source: List[float]
    destination: List[float]
    distance_m: float
    duration_s: float
    waypoints: List[List[float]]
    geometry: Dict[str, Any]
    source_type: str


class SimulationStartRequest(BaseModel):
    """Request payload to initialize an autonomous driving simulation episode."""
    difficulty: int = Field(1, ge=1, le=3, description="Difficulty level (1: low, 2: medium, 3: high/chaos)")
    corridor_length: float = Field(100.0, ge=50.0, le=500.0)
    road_width: float = Field(7.0, ge=4.0, le=14.0)
    seed: Optional[int] = Field(None, description="Random seed for reproducible obstacles")
    waypoints: Optional[List[List[float]]] = Field(None, description="Optional GPS waypoints from /route")


class ObstacleDTO(BaseModel):
    """Data transfer object for rendered obstacles."""
    id: int
    type: str
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    is_dynamic: bool
    color: str
    lat: Optional[float] = None
    lon: Optional[float] = None


class VehicleStateDTO(BaseModel):
    """Vehicle physical state snapshot."""
    x: float
    y: float
    v: float
    theta: float
    steer: float
    accel: float
    speed_kmh: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    heading_deg: Optional[float] = None


class SafetyDecisionDTO(BaseModel):
    """Safety controller intervention details."""
    action: int
    original_action: int
    intervened: bool
    reason: str
    hazard_obstacle_id: Optional[int] = None
    hazard_type: Optional[str] = None
    hazard_distance: Optional[float] = None
    ttc: Optional[float] = None


class SimulationStartResponse(BaseModel):
    """Response returned upon starting a simulation session."""
    session_id: str
    status: str
    difficulty: int
    corridor_length: float
    road_width: float
    vehicle: VehicleStateDTO
    obstacles: List[ObstacleDTO]
    target_x: float
    num_obstacles: int


class SimulationStepRequest(BaseModel):
    """Request payload to advance the simulation by one time step."""
    session_id: str
    override_action: Optional[int] = Field(None, ge=0, le=7, description="Optional manual action override (0-7)")


class SimulationStepResponse(BaseModel):
    """High-frequency telemetry returned per simulation step."""
    session_id: str
    step: int
    done: bool
    terminated: bool
    truncated: bool
    status: str
    vehicle: VehicleStateDTO
    action_proposed: int
    action_proposed_name: str
    action_executed: int
    action_executed_name: str
    safety: SafetyDecisionDTO
    step_reward: float
    total_reward: float
    reward_breakdown: Dict[str, float]
    obstacles: List[ObstacleDTO]


class MetricsResponse(BaseModel):
    """Aggregate metrics and performance telemetry."""
    total_sessions: int
    total_steps: int
    total_interventions: int
    total_collisions: int
    total_goals_reached: int
    average_speed_kmh: float
    model_loaded: bool
    model_path: str


class HealthResponse(BaseModel):
    """Health check payload."""
    status: str
    version: str
    model_ready: bool
