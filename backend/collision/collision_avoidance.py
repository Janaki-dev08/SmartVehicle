"""
Collision Avoidance & Supervisory Safety Controller.
Enforces multi-layer safety envelopes, speed modulation, and emergency evasive overrides.
"""

from typing import Dict, Any, Tuple
from config import config
from backend.collision.risk_estimation import RiskLevel


class CollisionAvoidanceSupervisor:
    """
    Supervises vehicle state and modulates target speed & braking
    to guarantee vehicle and pedestrian safety on unpredictable roads.
    """

    def __init__(self):
        self.max_speed_kmh = config.vehicle.max_speed_kmh
        self.emergency_stop_count = 0

    def evaluate_action(
        self,
        risk_report: Dict[str, Any],
        current_speed_kmh: float
    ) -> Tuple[str, float, float]:
        """
        Determines autonomous driving supervisor action and target speed/braking.
        Returns:
            (action_name: str, target_speed_kmh: float, brake_demand: float)
        """
        risk_level = risk_report.get("risk_level", RiskLevel.LOW.value)
        min_dist = risk_report.get("nearest_distance", 50.0)
        ttc = risk_report.get("min_ttc")

        if risk_level == RiskLevel.CRITICAL.value or min_dist < 2.5:
            self.emergency_stop_count += 1
            return "EMERGENCY_BRAKE", 0.0, 1.0

        elif risk_level == RiskLevel.HIGH.value:
            # Slow down significantly and prepare for maneuver
            safe_speed = max(8.0, min(15.0, min_dist * 2.5))
            return "EVASIVE_REPLAN", safe_speed, 0.45

        elif risk_level == RiskLevel.MEDIUM.value:
            # Gentle deceleration to maintain safe following distance
            safe_speed = max(18.0, min(25.0, min_dist * 3.0))
            return "SLOWING", safe_speed, 0.15

        else:
            # Clear road ahead: cruise at nominal target speed
            return "CRUISING", config.vehicle.target_speed_kmh, 0.0
