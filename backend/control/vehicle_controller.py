"""
Vehicle Controller for Autonomous Driving.
Implements Pure Pursuit lateral steering and PID longitudinal speed control
generating actuation commands (Steer, Throttle, Brake) for CARLA simulator.
"""

import numpy as np
from typing import Tuple, Dict, Any, Optional
from config import config


class PIDController:
    """Longitudinal PID Speed Controller."""

    def __init__(self, kp: float = 0.45, ki: float = 0.05, kd: float = 0.1):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, target_speed_ms: float, current_speed_ms: float, dt: float = 0.05) -> Tuple[float, float]:
        """
        Computes throttle [0, 1] or brake [0, 1] based on velocity error.
        """
        error = target_speed_ms - current_speed_ms
        self.integral = max(-5.0, min(5.0, self.integral + error * dt))
        derivative = (error - self.prev_error) / max(0.001, dt)
        self.prev_error = error

        output = self.kp * error + self.ki * self.integral + self.kd * derivative

        if output >= 0:
            throttle = float(np.clip(output, 0.0, 1.0))
            brake = 0.0
        else:
            throttle = 0.0
            brake = float(np.clip(-output * 1.5, 0.0, 1.0))

        return throttle, brake

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0


class PurePursuitController:
    """Lateral Pure Pursuit Steering Controller with Rate Limiting."""

    def __init__(self, wheelbase: float = 2.875, max_steer_rad: float = 0.7):
        self.wheelbase = wheelbase
        self.max_steer_rad = max_steer_rad
        self.prev_steer = 0.0
        self.max_steer_rate = 0.15 # Max steer change per tick (~3.0 rad/s)

    def compute_steer(self, target_local_point: Tuple[float, float]) -> float:
        """
        Computes normalized CARLA steering value in range [-1.0, 1.0].
        Point is in local frame: x=forward, y=right.
        """
        tx, ty = target_local_point
        ld_sq = tx**2 + ty**2
        ld = np.sqrt(ld_sq)

        if ld < 0.5:
            return 0.0

        # Curvature kappa = 2 * y / (ld^2)
        # Note: in CARLA, positive steer turns Right (positive Y)
        curvature = (2.0 * ty) / ld_sq
        raw_steer_angle_rad = np.arctan(curvature * self.wheelbase)

        # Normalize to [-1.0, 1.0]
        normalized_steer = float(raw_steer_angle_rad / self.max_steer_rad)
        normalized_steer = np.clip(normalized_steer, -1.0, 1.0)

        # Smooth steering rate limiter to prevent oscillation
        delta_steer = np.clip(normalized_steer - self.prev_steer, -self.max_steer_rate, self.max_steer_rate)
        smoothed_steer = self.prev_steer + delta_steer
        self.prev_steer = smoothed_steer

        return float(round(smoothed_steer, 3))

    def reset(self):
        self.prev_steer = 0.0


class VehicleController:
    """
    Combined Autonomous Vehicle Controller.
    """

    def __init__(self):
        self.pid = PIDController()
        self.pure_pursuit = PurePursuitController(
            wheelbase=config.vehicle.wheelbase,
            max_steer_rad=config.vehicle.max_steer_angle
        )

    def control_step(
        self,
        current_speed_kmh: float,
        target_speed_kmh: float,
        target_local_point: Tuple[float, float],
        emergency_brake_demand: float = 0.0,
        dt: float = 0.05
    ) -> Dict[str, float]:
        """
        Calculates steering, throttle, and braking values for current control tick.
        """
        # Speed in m/s
        curr_ms = current_speed_kmh / 3.6
        target_ms = max(0.0, target_speed_kmh / 3.6)

        # Lateral steering
        steer = self.pure_pursuit.compute_steer(target_local_point)

        # Longitudinal control
        throttle, brake = self.pid.compute(target_ms, curr_ms, dt)

        # Emergency override
        if emergency_brake_demand > 0.0:
            throttle = 0.0
            brake = max(brake, emergency_brake_demand)

        return {
            "steer": steer,
            "throttle": round(throttle, 3),
            "brake": round(brake, 3)
        }

    def reset(self):
        self.pid.reset()
        self.pure_pursuit.reset()
