"""
simulation_service.py — Backend Simulation Service & Real-Time Model Inference Engine.

Loads the offline trained SB3 PPO model at startup, handles active driving sessions,
orchestrates RL inference + Safety Layer validation, and projects positions to GPS.
"""

from __future__ import annotations
import os
import uuid
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from stable_baselines3 import PPO

from rl.environment.road_env import IndianRoadEnv
from rl.environment.vehicle import Vehicle, VehicleState
from rl.environment.obstacle import Obstacle
from safety.safety_controller import SafetyController, SafetyDecision
from mapping.route import local_to_gps
from backend.schemas.models import (
    SimulationStartRequest,
    SimulationStartResponse,
    SimulationStepRequest,
    SimulationStepResponse,
    ObstacleDTO,
    VehicleStateDTO,
    SafetyDecisionDTO,
    MetricsResponse
)


class SimulationSession:
    """Encapsulates state for an active driving simulation session."""

    def __init__(
        self,
        session_id: str,
        difficulty: int = 1,
        corridor_length: float = 100.0,
        road_width: float = 7.0,
        seed: Optional[int] = None,
        waypoints: Optional[List[List[float]]] = None
    ):
        self.session_id = session_id
        self.difficulty = difficulty
        self.corridor_length = corridor_length
        self.road_width = road_width
        self.waypoints = waypoints or []
        
        # Initialize Simulation Environment & Safety Controller
        self.env = IndianRoadEnv(
            corridor_length=corridor_length,
            road_width=road_width,
            difficulty=difficulty
        )
        self.safety_controller = SafetyController(corridor_half_width=road_width / 2.0)
        self.current_obs, self.last_info = self.env.reset(seed=seed)
        self.step_count = 0
        self.interventions = 0
        self.history: List[Dict[str, Any]] = []


class SimulationService:
    """Singleton service managing model serving and active simulation loops."""

    MODEL_PATH = "rl/checkpoints/ppo_indian_road.zip"

    def __init__(self):
        self.model: Optional[PPO] = None
        self.model_loaded = False
        self.sessions: Dict[str, SimulationSession] = {}
        
        # Global Aggregate Telemetry Metrics
        self.total_sessions_created = 0
        self.total_steps_executed = 0
        self.total_interventions = 0
        self.total_collisions = 0
        self.total_goals_reached = 0
        self.speed_history: List[float] = []

        self._load_model()

    def _load_model(self) -> None:
        """Loads the pre-trained PPO policy checkpoint into memory."""
        if os.path.exists(self.MODEL_PATH):
            try:
                print(f"[SimulationService] Loading pre-trained PPO model from {self.MODEL_PATH}...")
                self.model = PPO.load(self.MODEL_PATH)
                self.model_loaded = True
                print("[SimulationService] PPO Model loaded successfully for zero-delay inference!")
            except Exception as e:
                print(f"[SimulationService] Error loading PPO model: {e}")
                self.model = None
                self.model_loaded = False
        else:
            print(f"[SimulationService] Warning: Checkpoint {self.MODEL_PATH} not found. Running with baseline controller.")

    def start_session(self, req: SimulationStartRequest) -> SimulationStartResponse:
        """Initializes a new autonomous simulation session."""
        session_id = uuid.uuid4().hex[:8]
        session = SimulationSession(
            session_id=session_id,
            difficulty=req.difficulty,
            corridor_length=req.corridor_length,
            road_width=req.road_width,
            seed=req.seed,
            waypoints=req.waypoints
        )
        self.sessions[session_id] = session
        self.total_sessions_created += 1

        # Format vehicle state
        v_state = self._format_vehicle_dto(session.env.vehicle, session.waypoints, req.corridor_length)
        obs_dtos = self._format_obstacle_dtos(session.env.obstacles, session.waypoints, req.corridor_length)

        return SimulationStartResponse(
            session_id=session_id,
            status="INITIALIZED",
            difficulty=req.difficulty,
            corridor_length=req.corridor_length,
            road_width=req.road_width,
            vehicle=v_state,
            obstacles=obs_dtos,
            target_x=session.env.target_x,
            num_obstacles=len(obs_dtos)
        )

    def step_session(self, req: SimulationStepRequest) -> SimulationStepResponse:
        """Executes one simulation tick: RL Inference -> Safety Controller -> Env Step."""
        session = self.sessions.get(req.session_id)
        if not session:
            raise KeyError(f"Simulation session {req.session_id} not found or expired.")

        session.step_count += 1
        self.total_steps_executed += 1

        # 1. Action Decision (Manual Override OR RL Policy Prediction)
        if req.override_action is not None:
            proposed_action = req.override_action
        elif self.model_loaded and self.model is not None:
            action, _ = self.model.predict(session.current_obs, deterministic=True)
            proposed_action = int(action)
        else:
            # Fallback cruise / sample
            proposed_action = Vehicle.ACTION_CRUISE

        # 2. Pass Proposed Action through Deterministic Safety Controller
        safety_decision: SafetyDecision = session.safety_controller.evaluate(
            vehicle_state=session.env.vehicle.state,
            obstacles=session.env.obstacles,
            proposed_action=proposed_action
        )

        if safety_decision.intervened:
            session.interventions += 1
            self.total_interventions += 1

        # 3. Step Environment using the Guaranteed Safe Action
        obs, reward, terminated, truncated, info = session.env.step(safety_decision.action)
        session.current_obs = obs
        session.last_info = info

        # 4. Telemetry tracking
        speed_kmh = session.env.vehicle.state.v * 3.6
        self.speed_history.append(speed_kmh)
        if len(self.speed_history) > 1000:
            self.speed_history.pop(0)

        if info["collision"]:
            self.total_collisions += 1
        elif info["goal_reached"]:
            self.total_goals_reached += 1

        # 5. Status determination
        status = "RUNNING"
        if info["collision"]:
            status = f"COLLISION ({info.get('collision_type', 'obstacle')})"
        elif info["goal_reached"]:
            status = "GOAL_REACHED"
        elif info["off_road"]:
            status = "OFF_ROAD"
        elif truncated:
            status = "TIMEOUT"

        # Format DTOs
        v_dto = self._format_vehicle_dto(session.env.vehicle, session.waypoints, session.corridor_length)
        obs_dtos = self._format_obstacle_dtos(session.env.obstacles, session.waypoints, session.corridor_length)

        safety_dto = SafetyDecisionDTO(
            action=safety_decision.action,
            original_action=safety_decision.original_action,
            intervened=safety_decision.intervened,
            reason=safety_decision.reason,
            hazard_obstacle_id=safety_decision.hazard_obstacle_id,
            hazard_type=safety_decision.hazard_type,
            hazard_distance=safety_decision.hazard_distance,
            ttc=safety_decision.ttc
        )

        return SimulationStepResponse(
            session_id=session.session_id,
            step=session.step_count,
            done=bool(terminated or truncated),
            terminated=terminated,
            truncated=truncated,
            status=status,
            vehicle=v_dto,
            action_proposed=proposed_action,
            action_proposed_name=Vehicle.ACTION_NAMES[proposed_action],
            action_executed=safety_decision.action,
            action_executed_name=Vehicle.ACTION_NAMES[safety_decision.action],
            safety=safety_dto,
            step_reward=round(reward, 3),
            total_reward=round(float(info["total_reward"]), 2),
            reward_breakdown=info.get("reward_breakdown", {}),
            obstacles=obs_dtos
        )

    def get_metrics(self) -> MetricsResponse:
        """Returns aggregate server-wide metrics."""
        avg_speed = float(np.mean(self.speed_history)) if self.speed_history else 0.0
        return MetricsResponse(
            total_sessions=self.total_sessions_created,
            total_steps=self.total_steps_executed,
            total_interventions=self.total_interventions,
            total_collisions=self.total_collisions,
            total_goals_reached=self.total_goals_reached,
            average_speed_kmh=round(avg_speed, 2),
            model_loaded=self.model_loaded,
            model_path=self.MODEL_PATH
        )

    def _format_vehicle_dto(self, vehicle: Vehicle, waypoints: List[List[float]], corridor_len: float) -> VehicleStateDTO:
        v = vehicle.state
        lat, lon, heading = (None, None, None)
        if waypoints and len(waypoints) >= 2:
            lat, lon, heading = local_to_gps(v.x, v.y, waypoints, corridor_len)

        return VehicleStateDTO(
            x=round(v.x, 3),
            y=round(v.y, 3),
            v=round(v.v, 3),
            theta=round(v.theta, 4),
            steer=round(v.steer, 4),
            accel=round(v.accel, 3),
            speed_kmh=round(v.v * 3.6, 2),
            lat=lat,
            lon=lon,
            heading_deg=heading
        )

    def _format_obstacle_dtos(self, obstacles: List[Obstacle], waypoints: List[List[float]], corridor_len: float) -> List[ObstacleDTO]:
        dtos = []
        for ob in obstacles:
            lat, lon, _ = (None, None, None)
            if waypoints and len(waypoints) >= 2:
                lat, lon, _ = local_to_gps(ob.x, ob.y, waypoints, corridor_len)

            dtos.append(
                ObstacleDTO(
                    id=ob.id,
                    type=ob.type.value,
                    x=round(ob.x, 3),
                    y=round(ob.y, 3),
                    vx=round(ob.vx, 3),
                    vy=round(ob.vy, 3),
                    radius=ob.radius,
                    is_dynamic=ob.profile.is_dynamic,
                    color=ob.profile.color,
                    lat=lat,
                    lon=lon
                )
            )
        return dtos


# Singleton global instance
simulation_service = SimulationService()
