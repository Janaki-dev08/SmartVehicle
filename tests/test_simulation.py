"""
tests/test_simulation.py — Unit Tests for Mission 1 Simulation Core.
"""

import pytest
import numpy as np
from rl.environment.vehicle import Vehicle, VehicleState
from rl.environment.obstacle import Obstacle, ObstacleType, RiskLevel
from rl.environment.road_env import IndianRoadEnv


def test_vehicle_kinematics():
    v = Vehicle(x=0.0, y=0.0, v=10.0, theta=0.0)
    # Accelerate
    state = v.apply_action(Vehicle.ACTION_ACCELERATE, dt=0.1)
    assert state.x > 0.0
    assert state.v >= 10.0
    assert len(v.trajectory_history) == 2


def test_obstacle_step():
    obs = Obstacle(
        obstacle_id=1,
        obstacle_type=ObstacleType.PEDESTRIAN,
        x=30.0,
        y=2.0,
        vx=0.0,
        vy=-1.0,
        road_width=7.0
    )
    obs.step(dt=0.5)
    assert obs.y == pytest.approx(1.5, abs=1e-3)
    assert obs.distance_to(30.0, 1.5) == pytest.approx(0.0, abs=1e-3)


def test_road_env_reset_and_step():
    env = IndianRoadEnv(corridor_length=100.0, road_width=7.0, difficulty=1)
    obs, info = env.reset(seed=123)
    
    assert obs.shape == (24,)
    assert info["step"] == 0
    assert "vehicle" in info
    assert len(env.obstacles) > 0

    # Step through all discrete actions
    for action in range(8):
        obs, reward, term, trunc, info = env.step(action)
        assert obs.shape == (24,)
        assert isinstance(reward, float)
        assert isinstance(term, bool)
        assert isinstance(trunc, bool)
        if term or trunc:
            break
