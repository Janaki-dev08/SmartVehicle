"""
obstacle.py — Unstructured Indian Road Obstacle Models.

Defines realistic static and dynamic obstacles frequently encountered on Indian roads:
- Static: Potholes, parked vehicles, road debris, construction barricades.
- Dynamic: Jaywalking pedestrians, erratic autorickshaws, lane-splitting motorcycles,
           wrong-side two-wheelers, stray animals.
"""

from __future__ import annotations
import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List


class ObstacleType(str, Enum):
    POTHOLE = "pothole"
    PARKED_VEHICLE = "parked_vehicle"
    DEBRIS = "debris"
    PEDESTRIAN = "pedestrian"
    AUTORICKSHAW = "autorickshaw"
    MOTORCYCLE = "motorcycle"
    WRONG_WAY = "wrong_way"
    STRAY_ANIMAL = "stray_animal"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ObstacleConfig:
    radius: float          # Collision radius in meters
    length: float          # Bounding length (m)
    width: float           # Bounding width (m)
    color: str             # Visualizer color
    base_speed: float      # Typical speed (m/s)
    is_dynamic: bool       # Whether it moves


# Characteristic dimensions and profiles for Indian road entities
OBSTACLE_PROFILES: Dict[ObstacleType, ObstacleConfig] = {
    ObstacleType.POTHOLE: ObstacleConfig(
        radius=0.7, length=0.8, width=0.8, color="#8B4513", base_speed=0.0, is_dynamic=False
    ),
    ObstacleType.PARKED_VEHICLE: ObstacleConfig(
        radius=1.8, length=4.0, width=1.8, color="#708090", base_speed=0.0, is_dynamic=False
    ),
    ObstacleType.DEBRIS: ObstacleConfig(
        radius=0.6, length=0.6, width=0.6, color="#A0522D", base_speed=0.0, is_dynamic=False
    ),
    ObstacleType.PEDESTRIAN: ObstacleConfig(
        radius=0.6, length=0.6, width=0.6, color="#FF4500", base_speed=1.2, is_dynamic=True
    ),
    ObstacleType.AUTORICKSHAW: ObstacleConfig(
        radius=1.3, length=2.6, width=1.4, color="#FFD700", base_speed=4.5, is_dynamic=True
    ),
    ObstacleType.MOTORCYCLE: ObstacleConfig(
        radius=0.9, length=2.0, width=0.8, color="#1E90FF", base_speed=8.0, is_dynamic=True
    ),
    ObstacleType.WRONG_WAY: ObstacleConfig(
        radius=1.0, length=2.2, width=0.9, color="#DC143C", base_speed=-5.0, is_dynamic=True
    ),
    ObstacleType.STRAY_ANIMAL: ObstacleConfig(
        radius=0.9, length=1.8, width=0.9, color="#8FBC8F", base_speed=0.8, is_dynamic=True
    ),
}


class Obstacle:
    """Represents a single obstacle on or near the road corridor."""

    def __init__(
        self,
        obstacle_id: int,
        obstacle_type: ObstacleType,
        x: float,
        y: float,
        vx: float = 0.0,
        vy: float = 0.0,
        road_width: float = 7.0
    ):
        self.id = obstacle_id
        if isinstance(obstacle_type, str) and not isinstance(obstacle_type, ObstacleType):
            obstacle_type = ObstacleType(obstacle_type)
        self.type = obstacle_type
        self.profile = OBSTACLE_PROFILES[obstacle_type]
        
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.radius = self.profile.radius
        self.road_width = road_width
        
        # State history for visualization/replay
        self.history: List[Tuple[float, float]] = [(self.x, self.y)]

    def step(self, dt: float = 0.1) -> None:
        """Updates obstacle position over time step dt."""
        if not self.profile.is_dynamic:
            return

        self.x += self.vx * dt
        self.y += self.vy * dt

        # Pedestrians or animals reversing direction when reaching road boundary
        half_w = self.road_width / 2.0 + 1.0
        if self.type in (ObstacleType.PEDESTRIAN, ObstacleType.STRAY_ANIMAL):
            if abs(self.y) > half_w:
                self.vy = -self.vy
                self.y = np.clip(self.y, -half_w, half_w)

        self.history.append((self.x, self.y))

    def distance_to(self, x: float, y: float) -> float:
        """Euclidean distance from obstacle center to a given point."""
        return float(np.hypot(self.x - x, self.y - y))

    def compute_risk(self, ego_x: float, ego_y: float, ego_v: float) -> RiskLevel:
        """Evaluates situational risk based on time-to-collision and proximity."""
        dist = self.distance_to(ego_x, ego_y)
        rel_vx = ego_v - self.vx

        # Check critical distance
        if dist < (self.radius + 1.2):
            return RiskLevel.CRITICAL

        # Time To Collision (TTC) in seconds if in front
        dx = self.x - ego_x
        if dx > 0 and rel_vx > 0.5:
            ttc = dx / rel_vx
            if ttc < 1.5 and abs(self.y - ego_y) < 2.0:
                return RiskLevel.HIGH
            elif ttc < 3.0:
                return RiskLevel.MEDIUM

        if dist < 6.0:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        """Serializes obstacle properties for API / frontend JSON."""
        return {
            "id": self.id,
            "type": self.type.value,
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "vx": round(self.vx, 3),
            "vy": round(self.vy, 3),
            "radius": self.radius,
            "is_dynamic": self.profile.is_dynamic,
            "color": self.profile.color
        }
