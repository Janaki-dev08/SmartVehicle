"""
vehicle.py — Ego Vehicle Kinematic Model for Indian Road Simulation.

Implements a 2D kinematic bicycle model with bounded steering, acceleration,
and discrete motion primitives suited for Reinforcement Learning.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Tuple


@dataclass
class VehicleState:
    """Represents the instantaneous physical state of the vehicle."""
    x: float          # Longitudinal position along corridor (m)
    y: float          # Lateral position relative to centerline (m)
    v: float          # Forward velocity (m/s)
    theta: float      # Heading angle relative to road longitudinal axis (rad)
    steer: float      # Steering angle (rad)
    accel: float      # Acceleration (m/s^2)


class Vehicle:
    """
    Kinematic vehicle model operating in a local road corridor.
    
    Coordinate System:
      - x-axis: Longitudinal axis along the road corridor (0 to length_corridor)
      - y-axis: Lateral axis across the road (-width/2 [right] to +width/2 [left])
      - theta:  Heading angle (0 = aligned with road, >0 = facing left, <0 = facing right)
    """

    # Physical vehicle dimensions (representative Indian compact car / sedan)
    LENGTH: float = 4.2      # meters
    WIDTH: float = 1.8       # meters
    WHEELBASE: float = 2.5   # meters (L)
    
    # Dynamic operational limits
    MAX_SPEED: float = 16.0       # ~60 km/h (m/s)
    MIN_SPEED: float = 0.0        # No reverse in standard forward corridor (m/s)
    MAX_ACCEL: float = 3.0        # m/s^2
    MAX_BRAKE: float = -6.5       # m/s^2 (emergency brake)
    MAX_STEER: float = np.radians(28.0)   # Max steering angle (~0.488 rad)
    MAX_HEADING: float = np.radians(45.0) # Maximum allowable yaw deviation

    # Discrete Action Map (8 motion primitives)
    ACTION_CRUISE: int = 0
    ACTION_STEER_LEFT: int = 1
    ACTION_STEER_RIGHT: int = 2
    ACTION_ACCELERATE: int = 3
    ACTION_BRAKE: int = 4
    ACTION_SWERVE_LEFT: int = 5
    ACTION_SWERVE_RIGHT: int = 6
    ACTION_EMERGENCY_STOP: int = 7

    ACTION_NAMES = [
        "CRUISE",
        "STEER_LEFT",
        "STEER_RIGHT",
        "ACCELERATE",
        "BRAKE",
        "SWERVE_LEFT",
        "SWERVE_RIGHT",
        "EMERGENCY_STOP"
    ]

    def __init__(self, x: float = 0.0, y: float = 0.0, v: float = 6.0, theta: float = 0.0):
        self.state = VehicleState(
            x=float(x),
            y=float(y),
            v=float(v),
            theta=float(theta),
            steer=0.0,
            accel=0.0
        )
        self.trajectory_history = []
        self._record_history()

    def reset(self, x: float = 0.0, y: float = 0.0, v: float = 6.0, theta: float = 0.0) -> None:
        """Reset vehicle to initial state."""
        self.state = VehicleState(
            x=float(x),
            y=float(y),
            v=float(v),
            theta=float(theta),
            steer=0.0,
            accel=0.0
        )
        self.trajectory_history = []
        self._record_history()

    def apply_action(self, action: int, dt: float = 0.1) -> VehicleState:
        """
        Translates a discrete action ID into target control inputs (accel, steer)
        and integrates kinematics over time step dt.
        """
        target_accel = 0.0
        target_steer = 0.0

        if action == self.ACTION_CRUISE:
            # Maintain speed, decay steering back toward center
            target_accel = 0.0
            target_steer = self.state.steer * 0.5

        elif action == self.ACTION_STEER_LEFT:
            # Steer left slightly, maintain speed
            target_accel = 0.0
            target_steer = 0.20  # ~11.5 deg

        elif action == self.ACTION_STEER_RIGHT:
            # Steer right slightly, maintain speed
            target_accel = 0.0
            target_steer = -0.20

        elif action == self.ACTION_ACCELERATE:
            # Boost speed forward, center steering
            target_accel = 2.0
            target_steer = self.state.steer * 0.5

        elif action == self.ACTION_BRAKE:
            # Controlled deceleration
            target_accel = -3.0
            target_steer = self.state.steer * 0.5

        elif action == self.ACTION_SWERVE_LEFT:
            # Aggressive lateral shift left with forward thrust
            target_accel = 1.2
            target_steer = 0.35

        elif action == self.ACTION_SWERVE_RIGHT:
            # Aggressive lateral shift right with forward thrust
            target_accel = 1.2
            target_steer = -0.35

        elif action == self.ACTION_EMERGENCY_STOP:
            # Maximum braking force, zero steer
            target_accel = self.MAX_BRAKE
            target_steer = 0.0

        else:
            raise ValueError(f"Unknown action index: {action}")

        # Smooth steering and acceleration changes (low-pass filter)
        self.state.accel = float(np.clip(target_accel, self.MAX_BRAKE, self.MAX_ACCEL))
        self.state.steer = float(np.clip(target_steer, -self.MAX_STEER, self.MAX_STEER))

        # Kinematic state integration
        self._integrate_kinematics(dt)
        self._record_history()
        return self.state

    def _integrate_kinematics(self, dt: float) -> None:
        """
        Integrates kinematic bicycle equations:
          x' = x + v * cos(theta) * dt
          y' = y + v * sin(theta) * dt
          theta' = theta + (v / L) * tan(steer) * dt
          v' = v + a * dt
        """
        # Velocity update bounded between MIN_SPEED and MAX_SPEED
        new_v = np.clip(self.state.v + self.state.accel * dt, self.MIN_SPEED, self.MAX_SPEED)
        avg_v = (self.state.v + new_v) / 2.0  # Midpoint integration for accuracy

        # Position updates
        dx = avg_v * np.cos(self.state.theta) * dt
        dy = avg_v * np.sin(self.state.theta) * dt

        # Yaw/heading update
        dtheta = (avg_v / self.WHEELBASE) * np.tan(self.state.steer) * dt
        new_theta = float(np.clip(self.state.theta + dtheta, -self.MAX_HEADING, self.MAX_HEADING))

        self.state.x += float(dx)
        self.state.y += float(dy)
        self.state.theta = new_theta
        self.state.v = float(new_v)

    def _record_history(self) -> None:
        """Saves current state for trajectory visualization and metric logging."""
        self.trajectory_history.append((self.state.x, self.state.y, self.state.v, self.state.theta))

    @property
    def bounding_box(self) -> Tuple[float, float, float, float]:
        """Returns approximate axis-aligned bounding box (min_x, max_x, min_y, max_y)."""
        half_l = self.LENGTH / 2.0
        half_w = self.WIDTH / 2.0
        return (
            self.state.x - half_l,
            self.state.x + half_l,
            self.state.y - half_w,
            self.state.y + half_w
        )

    def to_dict(self) -> dict:
        """Serializes vehicle state to dict for API & logging."""
        return {
            "x": round(self.state.x, 3),
            "y": round(self.state.y, 3),
            "v": round(self.state.v, 3),
            "theta": round(self.state.theta, 4),
            "steer": round(self.state.steer, 4),
            "accel": round(self.state.accel, 3),
            "speed_kmh": round(self.state.v * 3.6, 2)
        }
