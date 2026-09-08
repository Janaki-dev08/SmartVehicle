"""
safety_controller.py — Deterministic Rule-Based Safety Layer.

Sits strictly between RL Policy Output and Vehicle Actuation:
  RL Agent Proposes Action -> Safety Controller Validates -> Guaranteed Safe Actuation

Enforces kinematic stopping distances, Time-To-Collision (TTC) bounds,
and corridor boundaries.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple
from rl.environment.vehicle import Vehicle, VehicleState
from rl.environment.obstacle import Obstacle


@dataclass
class SafetyDecision:
    """Encapsulates the verdict of the safety controller."""
    action: int                   # Final executed action (either original or safe override)
    original_action: int          # The action proposed by the RL policy/driver
    intervened: bool              # True if an unsafe action was overridden
    reason: str                   # Human-readable justification for the decision
    hazard_obstacle_id: Optional[int] = None
    hazard_type: Optional[str] = None
    hazard_distance: Optional[float] = None
    ttc: Optional[float] = None


class SafetyController:
    """
    Deterministic Safety Controller for Indian Autonomous Vehicle Navigation.
    
    Guarantees that regardless of RL exploration mistakes or edge-case network outputs,
    the vehicle maintains physical stopping clearance.
    """

    def __init__(
        self,
        reaction_time: float = 0.35,        # Driver / system perception-reaction delay (s)
        emergency_decel: float = 6.0,       # Emergency deceleration capacity (m/s^2)
        min_clearance_gap: float = 3.0,     # Absolute minimum stopping margin from obstacle (m)
        ttc_emergency_threshold: float = 1.4,# Time-To-Collision danger threshold (s)
        corridor_half_width: float = 3.5    # Road boundary limit from centerline (m)
    ):
        self.reaction_time = reaction_time
        self.emergency_decel = emergency_decel
        self.min_clearance_gap = min_clearance_gap
        self.ttc_emergency_threshold = ttc_emergency_threshold
        self.corridor_half_width = corridor_half_width
        self.total_interventions = 0

    def compute_stopping_distance(self, speed: float) -> float:
        """
        Calculates theoretical emergency stopping distance using Newtonian kinematics:
          d_stop = (v * t_reaction) + (v^2 / (2 * a_brake)) + d_gap
        """
        reaction_dist = max(0.0, speed) * self.reaction_time
        braking_dist = (max(0.0, speed) ** 2) / (2.0 * self.emergency_decel)
        return float(self.min_clearance_gap + reaction_dist + braking_dist)

    def evaluate(
        self,
        vehicle_state: VehicleState,
        obstacles: List[Obstacle],
        proposed_action: int
    ) -> SafetyDecision:
        """
        Evaluates the proposed action against real-time physical safety envelopes.
        Overrides with EMERGENCY_STOP or BRAKE if a collision risk is imminent.
        """
        ego_x = vehicle_state.x
        ego_y = vehicle_state.y
        ego_v = vehicle_state.v
        ego_half_w = Vehicle.WIDTH / 2.0
        
        required_safe_dist = self.compute_stopping_distance(ego_v)

        # 1. Road Boundary Check (Prevent driving off road)
        if proposed_action in (Vehicle.ACTION_STEER_LEFT, Vehicle.ACTION_SWERVE_LEFT):
            if ego_y >= (self.corridor_half_width - 0.5):
                self.total_interventions += 1
                return SafetyDecision(
                    action=Vehicle.ACTION_STEER_RIGHT,
                    original_action=proposed_action,
                    intervened=True,
                    reason=f"Prevented off-road boundary breach (y={ego_y:.2f}m)"
                )

        if proposed_action in (Vehicle.ACTION_STEER_RIGHT, Vehicle.ACTION_SWERVE_RIGHT):
            if ego_y <= (-self.corridor_half_width + 0.5):
                self.total_interventions += 1
                return SafetyDecision(
                    action=Vehicle.ACTION_STEER_LEFT,
                    original_action=proposed_action,
                    intervened=True,
                    reason=f"Prevented off-road boundary breach (y={ego_y:.2f}m)"
                )

        # 2. Obstacle Collision Hazard Scan in Forward Corridor
        imminent_hazard: Optional[Obstacle] = None
        min_bumper_gap = float("inf")
        hazard_ttc = None

        ego_front_x = ego_x + (Vehicle.LENGTH / 2.0)

        for obs in obstacles:
            obs_rear_x = obs.x - obs.radius
            bumper_gap = obs_rear_x - ego_front_x
            
            # Only consider obstacles in front of the vehicle bumper
            if bumper_gap <= -0.5:
                continue

            # Lateral corridor overlap check (vehicle width + obstacle radius + buffer)
            lateral_overlap = abs(obs.y - ego_y) <= (ego_half_w + obs.radius + 0.4)
            
            if lateral_overlap:
                # Relative closing speed
                rel_v = ego_v - obs.vx
                ttc = (bumper_gap / rel_v) if rel_v > 0.2 else float("inf")

                if bumper_gap < min_bumper_gap:
                    min_bumper_gap = bumper_gap
                    imminent_hazard = obs
                    hazard_ttc = ttc

        # 3. Intervene if hazard violates stopping distance or TTC
        if imminent_hazard is not None:
            is_unsafe_gap = min_bumper_gap < required_safe_dist
            is_unsafe_ttc = (hazard_ttc is not None) and (hazard_ttc < self.ttc_emergency_threshold)

            if is_unsafe_gap or is_unsafe_ttc:
                forward_actions = (
                    Vehicle.ACTION_ACCELERATE,
                    Vehicle.ACTION_CRUISE,
                    Vehicle.ACTION_SWERVE_LEFT,
                    Vehicle.ACTION_SWERVE_RIGHT
                )
                
                # Intervene if policy proposes forward movement into danger, or if gap is already critical
                if proposed_action in forward_actions or min_bumper_gap < (self.min_clearance_gap + 1.0):
                    self.total_interventions += 1
                    ttc_str = f"{hazard_ttc:.2f}s" if hazard_ttc and hazard_ttc != float("inf") else "N/A"
                    
                    # Force EMERGENCY_STOP to guarantee stopping within kinematic envelope
                    override_action = Vehicle.ACTION_EMERGENCY_STOP

                    return SafetyDecision(
                        action=override_action,
                        original_action=proposed_action,
                        intervened=True,
                        reason=(
                            f"Safety Override: {imminent_hazard.type.value} ahead at bumper gap {min_bumper_gap:.2f}m "
                            f"(Req Safe Gap: {required_safe_dist:.2f}m, TTC: {ttc_str}). "
                            f"Overriding {Vehicle.ACTION_NAMES[proposed_action]} -> {Vehicle.ACTION_NAMES[override_action]}"
                        ),
                        hazard_obstacle_id=imminent_hazard.id,
                        hazard_type=imminent_hazard.type.value,
                        hazard_distance=round(min_bumper_gap, 2),
                        ttc=round(hazard_ttc, 2) if hazard_ttc and hazard_ttc != float("inf") else None
                    )

        # No hazard detected or action is already safe
        return SafetyDecision(
            action=proposed_action,
            original_action=proposed_action,
            intervened=False,
            reason="Action within safe envelope"
        )
