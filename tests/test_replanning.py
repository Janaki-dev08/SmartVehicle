"""
Unit Tests for Dynamic Replanning Engine.
"""

import pytest
from backend.planning.replanning import ReplanningEngine


def test_replanning_triggered_by_pedestrian():
    """Test replanning engine detects pedestrian directly on planned path."""
    replanner = ReplanningEngine()
    
    # Path straight along centerline
    current_path = [(float(x), 0.0) for x in range(0, 30, 2)]
    
    # Pedestrian at x=10m, y=0.5m (directly in corridor)
    obstacles = [
        {"class_name": "pedestrian", "relative_position": (10.0, 0.5, 0.0), "velocity": 1.2, "predicted_trajectory": []}
    ]

    needed, reason = replanner.check_replan_needed(current_path, obstacles, safety_clearance=1.8)

    assert needed is True
    assert "Pedestrian" in reason


def test_no_replan_when_path_is_clear():
    """Test replanning engine does not trigger when obstacles are far off to the side."""
    replanner = ReplanningEngine()
    current_path = [(float(x), 0.0) for x in range(0, 30, 2)]

    # Obstacle is on sidewalk at y=6.0m
    obstacles = [
        {"class_name": "pedestrian", "relative_position": (10.0, 6.0, 0.0), "velocity": 0.0, "predicted_trajectory": []}
    ]

    needed, reason = replanner.check_replan_needed(current_path, obstacles, safety_clearance=1.8)

    assert needed is False
    assert reason == "Path safe"
