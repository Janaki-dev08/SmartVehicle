"""
Collision Risk Estimation & Time-To-Collision (TTC) Calculation.
Assesses spatial proximity, relative velocities, and path intersections
to classify operational safety levels: LOW, MEDIUM, HIGH, CRITICAL.
"""

import numpy as np
from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
from config import config


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskEstimator:
    """
    Computes deterministic Time-To-Collision (TTC), minimum obstacle clearance,
    and multi-tier risk classification.
    """

    def __init__(self):
        self.ttc_warning = config.collision.ttc_warning_threshold
        self.ttc_high = config.collision.ttc_high_threshold
        self.ttc_critical = config.collision.ttc_critical_threshold

    def calculate_risk(
        self,
        ego_speed: float, # m/s
        tracked_obstacles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates risk against all tracked obstacles.
        Returns detailed risk assessment report.
        """
        if not tracked_obstacles:
            return {
                "risk_level": RiskLevel.LOW.value,
                "min_ttc": 99.9,
                "nearest_obstacle": None,
                "nearest_distance": 99.9,
                "threat_count": 0,
                "lateral_clearance": 10.0,
                "risk_score": 0.0
            }

        min_ttc = 99.9
        min_dist = 99.9
        nearest_obs: Optional[Dict[str, Any]] = None
        high_threats = 0

        for obs in tracked_obstacles:
            rel = obs.get("relative_position", (100.0, 0.0, 0.0))
            dx = rel[0]  # Forward distance in meters
            dy = rel[1]  # Lateral offset in meters
            dist = float(np.sqrt(dx**2 + dy**2))

            if dist < min_dist:
                min_dist = dist
                nearest_obs = obs

            # In-corridor check: only consider obstacles in driving envelope (-3.5m to +3.5m)
            if abs(dy) < 3.5 and dx > 0.0:
                obs_vx = obs.get("vx", 0.0)
                # Relative closing speed (positive when closing in)
                rel_speed = ego_speed - obs_vx

                # TTC = dx / closing_speed
                if rel_speed > 0.2:
                    ttc = dx / rel_speed
                elif dx < 4.0:
                    ttc = 1.0 # Imminent proximity even if static/moving slowly
                else:
                    ttc = 99.9

                if ttc < min_ttc:
                    min_ttc = ttc

                if ttc < self.ttc_high or dist < 6.0:
                    high_threats += 1

        # Classify overall Risk Level based on thresholds
        if min_ttc <= self.ttc_critical or min_dist <= 2.8:
            risk_level = RiskLevel.CRITICAL
            risk_score = 1.0
        elif min_ttc <= self.ttc_high or min_dist <= 6.5:
            risk_level = RiskLevel.HIGH
            risk_score = 0.75
        elif min_ttc <= self.ttc_warning or min_dist <= 12.0:
            risk_level = RiskLevel.MEDIUM
            risk_score = 0.45
        else:
            risk_level = RiskLevel.LOW
            risk_score = 0.10

        return {
            "risk_level": risk_level.value,
            "min_ttc": round(min_ttc, 2) if min_ttc < 90 else None,
            "nearest_obstacle": {
                "id": nearest_obs.get("object_id"),
                "class_name": nearest_obs.get("class_name"),
                "distance": round(min_dist, 2),
                "relative_position": nearest_obs.get("relative_position")
            } if nearest_obs else None,
            "nearest_distance": round(min_dist, 2),
            "threat_count": high_threats,
            "lateral_clearance": round(abs(nearest_obs.get("relative_position", (0, 10, 0))[1]), 2) if nearest_obs else 10.0,
            "risk_score": round(risk_score, 2)
        }
