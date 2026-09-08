"""
Unit Tests for Adaptive A* Path Planner.
"""

import pytest
import numpy as np
from backend.planning.astar import AStarPlanner
from backend.perception.obstacle_detection import OccupancyGridBuilder


def test_astar_free_space():
    """Test A* planner finds a valid straight path in free space."""
    grid_builder = OccupancyGridBuilder(resolution=0.5, width_meters=20.0, length_meters=40.0)
    costmap = np.zeros((grid_builder.nx, grid_builder.ny), dtype=np.float32)

    planner = AStarPlanner()
    start_pos = (0.0, 0.0)
    goal_pos = (30.0, 0.0)

    path, success, latency = planner.plan(costmap, start_pos, goal_pos, grid_builder)

    assert success is True
    assert len(path) > 5
    assert latency >= 0.0
    # Start and end proximity
    assert abs(path[0][0] - start_pos[0]) < 1.0
    assert abs(path[-1][0] - goal_pos[0]) < 2.0


def test_astar_obstacle_avoidance():
    """Test A* successfully routes around a center obstacle."""
    grid_builder = OccupancyGridBuilder(resolution=0.5, width_meters=20.0, length_meters=40.0)
    
    # Place obstacle directly in center of path at x=15m, y=0m
    obstacles = [
        {"class_name": "car", "relative_position": (15.0, 0.0, 0.0), "predicted_trajectory": []}
    ]
    costmap = grid_builder.build_grid(obstacles, road_half_width=6.0, safety_margin_m=2.0)

    planner = AStarPlanner()
    path, success, latency = planner.plan(costmap, (0.0, 0.0), (30.0, 0.0), grid_builder)

    assert success is True
    assert len(path) > 5

    # Verify that the path deviates laterally around x=15m to avoid the obstacle
    mid_points = [pt for pt in path if 12.0 <= pt[0] <= 18.0]
    assert len(mid_points) > 0
    # Lateral offset should be non-zero
    max_lateral_offset = max(abs(pt[1]) for pt in mid_points)
    assert max_lateral_offset > 1.0, f"Expected lateral detour, got max offset {max_lateral_offset}"
