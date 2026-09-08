"""
Hierarchical Path Planner.
Bridges Global Route (CARLA / Google Maps) with Local Adaptive A* Path Generator.
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from config import config
from backend.planning.astar import AStarPlanner
from backend.perception.obstacle_detection import OccupancyGridBuilder


class PathPlanner:
    """
    Manages global waypoint sequences, local costmap alignment,
    and adaptive trajectory generation.
    """

    def __init__(self):
        self.astar = AStarPlanner(
            weight_distance=config.planning.weight_distance,
            weight_obstacle=config.planning.weight_obstacle_proximity,
            weight_smoothness=config.planning.weight_smoothness,
            weight_road_boundary=config.planning.weight_road_boundary
        )
        self.grid_builder = OccupancyGridBuilder(
            resolution=config.planning.grid_resolution,
            width_meters=config.planning.grid_width * config.planning.grid_resolution,
            length_meters=config.planning.grid_length * config.planning.grid_resolution
        )
        self.global_route: List[Tuple[float, float]] = []
        self.current_local_path: List[Tuple[float, float]] = []
        self.current_global_path: List[Tuple[float, float]] = []

    def set_global_route(self, waypoints: List[Tuple[float, float]]):
        """Sets target global route waypoints."""
        self.global_route = list(waypoints)

    def plan_local_trajectory(
        self,
        vehicle_pos: Tuple[float, float, float], # (x, y, heading_rad)
        costmap: np.ndarray,
        lookahead_distance: float = 35.0
    ) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]], bool, float]:
        """
        Plans collision-free local path and transforms it to global coordinates.
        Returns:
            (local_path_pts, global_path_pts, success, planning_time_ms)
        """
        vx, vy, v_heading = vehicle_pos

        # Local start is vehicle bumper: (0.0, 0.0)
        start_local = (0.0, 0.0)
        
        # Local goal is forward along road centerline / global route direction
        goal_local = (lookahead_distance, 0.0)

        # Run Adaptive A*
        local_path, success, plan_time = self.astar.plan(
            costmap=costmap,
            start_world=start_local,
            goal_world=goal_local,
            grid_builder=self.grid_builder,
            smooth_path=True
        )

        # If A* fails, provide default smooth forward path
        if not local_path or len(local_path) < 2:
            local_path = [(x, 0.0) for x in np.linspace(0, lookahead_distance, 20)]

        self.current_local_path = local_path

        # Transform local coordinates to global map coordinates
        cos_h = np.cos(v_heading)
        sin_h = np.sin(v_heading)

        global_path = []
        for lx, ly in local_path:
            # Standard 2D rotation & translation: X_global = vx + (lx*cos - ly*sin)
            gx = vx + (lx * cos_h - ly * sin_h)
            gy = vy + (lx * sin_h + ly * cos_h)
            global_path.append((round(float(gx), 2), round(float(gy), 2)))

        self.current_global_path = global_path
        return local_path, global_path, success, plan_time

    def get_lookahead_target(
        self,
        current_speed: float,
        lookahead_base: float = 5.0
    ) -> Tuple[float, float]:
        """
        Extracts lookahead target point $(x_{\text{local}}, y_{\text{local}})$ for Pure Pursuit controller.
        Scales lookahead distance with vehicle speed: $L_d = L_{\text{min}} + k \cdot v$.
        """
        ld = max(config.planning.lookahead_distance_min, min(config.planning.lookahead_distance_max, lookahead_base + 0.4 * current_speed))
        
        if not self.current_local_path:
            return (ld, 0.0)

        # Find closest path point to lookahead distance
        for pt in self.current_local_path:
            dist = np.sqrt(pt[0]**2 + pt[1]**2)
            if dist >= ld:
                return pt

        return self.current_local_path[-1]
