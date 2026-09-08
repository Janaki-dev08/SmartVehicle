"""
Unit Tests for Collision Risk Estimation and TTC Calculations.
"""

import pytest
from backend.collision.risk_estimation import RiskEstimator, RiskLevel
from backend.collision.collision_avoidance import CollisionAvoidanceSupervisor


def test_risk_estimation_no_obstacles():
    """Test risk evaluation when no obstacles are present."""
    estimator = RiskEstimator()
    report = estimator.calculate_risk(ego_speed=10.0, tracked_obstacles=[])

    assert report["risk_level"] == RiskLevel.LOW.value
    assert report["nearest_distance"] > 50.0
    assert report["threat_count"] == 0


def test_risk_estimation_critical_proximity():
    """Test critical risk triggered when obstacle is within 2.5m."""
    estimator = RiskEstimator()
    obstacles = [
        {"object_id": 1, "class_name": "pedestrian", "relative_position": (2.0, 0.2, 0.0), "vx": 0.0}
    ]
    report = estimator.calculate_risk(ego_speed=8.0, tracked_obstacles=obstacles)

    assert report["risk_level"] == RiskLevel.CRITICAL.value
    assert report["nearest_distance"] == pytest.approx(2.01, abs=0.05)


def test_risk_estimation_ttc():
    """Test TTC calculation with closing vehicle."""
    estimator = RiskEstimator()
    # Obstacle is 15m ahead, moving at 2 m/s. Ego vehicle is at 10 m/s. Closing speed = 8 m/s.
    # Expected TTC = 15 / 8 = 1.875s (which is < 2.5s -> HIGH RISK)
    obstacles = [
        {"object_id": 2, "class_name": "auto_rickshaw", "relative_position": (15.0, 0.0, 0.0), "vx": 2.0}
    ]
    report = estimator.calculate_risk(ego_speed=10.0, tracked_obstacles=obstacles)

    assert report["risk_level"] in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]
    assert report["min_ttc"] is not None
    assert 1.5 <= report["min_ttc"] <= 2.2


def test_collision_avoidance_actions():
    """Test supervisor action transitions."""
    supervisor = CollisionAvoidanceSupervisor()

    # Critical risk -> Emergency Brake
    action, target_spd, brake = supervisor.evaluate_action({"risk_level": "CRITICAL", "nearest_distance": 2.0}, 30.0)
    assert action == "EMERGENCY_BRAKE"
    assert brake == 1.0
    assert target_spd == 0.0

    # Low risk -> Cruising
    action, target_spd, brake = supervisor.evaluate_action({"risk_level": "LOW", "nearest_distance": 40.0}, 30.0)
    assert action == "CRUISING"
    assert brake == 0.0
