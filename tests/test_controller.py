"""
Unit Tests for Vehicle Controller (Pure Pursuit and PID).
"""

import pytest
from backend.control.vehicle_controller import VehicleController, PurePursuitController, PIDController


def test_pure_pursuit_steering():
    """Test steering bounds and directional response."""
    pp = PurePursuitController(wheelbase=2.875, max_steer_rad=0.7)

    # Point straight ahead -> Steer should be near 0
    steer_straight = pp.compute_steer((10.0, 0.0))
    assert abs(steer_straight) < 0.05

    # Point to the right (positive Y) -> Steer should be positive
    pp.reset()
    steer_right = pp.compute_steer((10.0, 3.0))
    assert steer_right > 0.1
    assert steer_right <= 1.0

    # Point to the left (negative Y) -> Steer should be negative
    pp.reset()
    steer_left = pp.compute_steer((10.0, -3.0))
    assert steer_left < -0.1
    assert steer_left >= -1.0


def test_pid_speed_control():
    """Test longitudinal throttle and braking calculation."""
    pid = PIDController(kp=0.5, ki=0.0, kd=0.1)

    # Current speed 0 m/s, target 10 m/s -> Throttle demand
    throttle, brake = pid.compute(target_speed_ms=10.0, current_speed_ms=0.0, dt=0.05)
    assert throttle > 0.3
    assert brake == 0.0

    # Current speed 15 m/s, target 5 m/s -> Brake demand
    pid.reset()
    throttle, brake = pid.compute(target_speed_ms=5.0, current_speed_ms=15.0, dt=0.05)
    assert throttle == 0.0
    assert brake > 0.4
