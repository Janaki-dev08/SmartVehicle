"""
Dynamic Replanning Engine.
Continuously audits planned trajectory safety against real-time perception updates,
triggering instantaneous A* replanning when obstacles intersect the path envelope.
"""

import time
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from config import config


class ReplanningEngine:
    """
    Dynamic Safety Monitor and Replan Controller.
    """

    def __init__(self, check_interval: float = 0.1):
        self.check_interval = check_interval
        self.last_check_time = 0.0
        self.replan_count = 0
        self.replan_history: List[Dict[str, Any]] = []

    def check_replan_needed(
        self,
        current_local_path: List[Tuple[float, float]],
        tracked_obstacles: List[Dict[str, Any]],
        safety_clearance: float = 1.8
    ) -> Tuple[bool, str]:
        """
        Determines whether current path is compromised by any detected obstacle.
        Returns:
            (replan_needed: bool, trigger_reason: str)
        """
        if not current_local_path or len(current_local_path) < 2:
            return True, "Path empty or truncated"

        for obs in tracked_obstacles:
            rel = obs.get("relative_position", (0.0, 0.0, 0.0))
            ox, oy = rel[0], rel[1]
            cls_name = obs.get("class_name", "obstacle")
            speed = obs.get("velocity", 0.0)

            # Class-based collision radius
            if cls_name in ["truck", "bus"]:
                obs_radius = 2.4
            elif cls_name in ["car", "auto_rickshaw"]:
                obs_radius = 1.8
            else:
                obs_radius = 1.1

            threat_radius = obs_radius + safety_clearance

            # Check intersection with static position
            for px, py in current_local_path:
                dist = np.sqrt((px - ox)**2 + (py - oy)**2)
                if dist < threat_radius:
                    if cls_name == "pedestrian":
                        return True, f"Pedestrian crossed into path ({ox:.1f}m ahead)"
                    elif cls_name == "motorcycle":
                        return True, f"Motorcycle cut into vehicle corridor ({ox:.1f}m ahead)"
                    elif cls_name == "auto_rickshaw":
                        return True, f"Auto-rickshaw shifted position ({ox:.1f}m ahead)"
                    elif cls_name == "animal":
                        return True, f"Stray animal detected on road ({ox:.1f}m ahead)"
                    else:
                        return True, f"{cls_name.capitalize()} blocking path ({ox:.1f}m ahead)"

            # Check intersection with predicted dynamic trajectory
            pred_pts = obs.get("predicted_trajectory", [])
            for pred in pred_pts[1:4]: # Lookahead 0.5 to 1.5 sec
                p_ox, p_oy = pred[0], pred[1]
                for px, py in current_local_path:
                    dist = np.sqrt((px - p_ox)**2 + (py - p_oy)**2)
                    if dist < (threat_radius * 0.9):
                        return True, f"Dynamic threat: {cls_name} predicted collision ({p_ox:.1f}m)"

        return False, "Path safe"

    def record_replan_event(
        self,
        reason: str,
        planning_time_ms: float,
        prev_path_len: int,
        new_path_len: int
    ) -> Dict[str, Any]:
        """Logs dynamic replanning event."""
        self.replan_count += 1
        event = {
            "id": self.replan_count,
            "timestamp": round(time.time(), 3),
            "reason": reason,
            "latency_ms": round(planning_time_ms, 2),
            "prev_points": prev_path_len,
            "new_points": new_path_len,
            "status": "SUCCESS"
        }
        self.replan_history.append(event)
        if len(self.replan_history) > 50:
            self.replan_history.pop(0)
        return event
