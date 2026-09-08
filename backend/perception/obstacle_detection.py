"""
Obstacle Detection & Occupancy Representation Module.
Synthesizes tracked objects into multi-layer 2D occupancy grids and future trajectory predictions.
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from config import config


class ObstaclePredictor:
    """
    Predicts future trajectories of dynamic obstacles over a time horizon.
    """

    def __init__(self, horizon_seconds: float = 3.0, step_seconds: float = 0.5):
        self.horizon = horizon_seconds
        self.step = step_seconds

    def predict_trajectories(self, tracked_objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generates multi-step predicted trajectory for each tracked dynamic object.
        Returns:
            List of obstacle dicts with 'predicted_path': [[x0,y0], [x1,y1], ...]
        """
        time_steps = np.arange(self.step, self.horizon + self.step, self.step)
        augmented_objects = []

        for obj in tracked_objects:
            obj_copy = dict(obj)
            rel_pos = obj.get("relative_position", (0.0, 0.0, 0.0))
            curr_x = rel_pos[0]
            curr_y = rel_pos[1]
            
            vx = obj.get("vx", 0.0)
            vy = obj.get("vy", 0.0)
            speed = obj.get("velocity", 0.0)

            predicted_points = [[round(curr_x, 2), round(curr_y, 2)]]
            
            # Predict future positions linearly with velocity damping
            for t in time_steps:
                fut_x = curr_x + vx * t
                fut_y = curr_y + vy * t
                predicted_points.append([round(fut_x, 2), round(fut_y, 2)])

            obj_copy["predicted_trajectory"] = predicted_points
            augmented_objects.append(obj_copy)

        return augmented_objects


class OccupancyGridBuilder:
    """
    Constructs a 2D local costmap / occupancy grid for A* path planning.
    Grid coordinate system:
        - Center lateral Y=0 is in the middle of grid_width
        - Vehicle bumper is at X=0 (bottom of grid_length)
    """

    def __init__(
        self,
        resolution: float = 0.5, # meters per cell
        width_meters: float = 30.0, # -15m to +15m lateral
        length_meters: float = 60.0 # 0m to 60m longitudinal
    ):
        self.resolution = resolution
        self.width_m = width_meters
        self.length_m = length_meters
        
        self.nx = int(length_meters / resolution) # Longitudinal cells
        self.ny = int(width_meters / resolution)  # Lateral cells
        self.origin_y_idx = self.ny // 2

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """Converts vehicle-relative coordinates (x_forward, y_lateral) to grid indices (row_x, col_y)."""
        row_x = int(x / self.resolution)
        col_y = int((y + self.width_m / 2.0) / self.resolution)
        return row_x, col_y

    def grid_to_world(self, row_x: int, col_y: int) -> Tuple[float, float]:
        """Converts grid indices to vehicle-relative coordinates in meters."""
        x = row_x * self.resolution
        y = (col_y * self.resolution) - (self.width_m / 2.0)
        return round(x, 2), round(y, 2)

    def is_inside(self, row_x: int, col_y: int) -> bool:
        """Checks if cell is within grid boundaries."""
        return 0 <= row_x < self.nx and 0 <= col_y < self.ny

    def build_grid(
        self,
        obstacles: List[Dict[str, Any]],
        road_half_width: float = 5.0,
        safety_margin_m: float = 1.8
    ) -> np.ndarray:
        """
        Builds normalized 2D costmap where:
            0.0 = completely free drivable space
            0.1 - 0.9 = proximity buffer / risk zone
            1.0 = impassable obstacle / off-road boundary
        """
        grid = np.zeros((self.nx, self.ny), dtype=np.float32)

        # 1. Road Boundary Constraints (Unstructured Indian roads often have soft edges/curbs)
        for c in range(self.ny):
            _, y_m = self.grid_to_world(0, c)
            if abs(y_m) > road_half_width:
                # Off-road cost
                dist_off = abs(y_m) - road_half_width
                grid[:, c] = min(1.0, 0.6 + dist_off * 0.4)

        # 2. Obstacle Inflation & Proximity Costs
        safety_cells = max(1, int(safety_margin_m / self.resolution))
        
        for obs in obstacles:
            rel_pos = obs.get("relative_position", (0.0, 0.0, 0.0))
            ox, oy = rel_pos[0], rel_pos[1]
            
            # Map object size
            cls_name = obs.get("class_name", "obstacle")
            if cls_name in ["truck", "bus"]:
                obs_radius_cells = max(2, int(2.5 / self.resolution))
            elif cls_name in ["car", "auto_rickshaw"]:
                obs_radius_cells = max(2, int(1.8 / self.resolution))
            else:
                obs_radius_cells = max(1, int(1.0 / self.resolution))

            row_o, col_o = self.world_to_grid(ox, oy)

            # Inflate obstacle footprint and safety gradient
            total_radius = obs_radius_cells + safety_cells
            for dr in range(-total_radius, total_radius + 1):
                for dc in range(-total_radius, total_radius + 1):
                    r = row_o + dr
                    c = col_o + dc
                    if self.is_inside(r, c):
                        cell_dist_m = np.sqrt((dr * self.resolution)**2 + (dc * self.resolution)**2)
                        
                        if cell_dist_m <= (obs_radius_cells * self.resolution):
                            grid[r, c] = 1.0 # Solid obstacle
                        elif cell_dist_m <= (total_radius * self.resolution):
                            # Proximity cost gradient from 0.8 down to 0.0
                            cost_val = 0.8 * (1.0 - (cell_dist_m - obs_radius_cells * self.resolution) / (safety_margin_m))
                            grid[r, c] = max(grid[r, c], float(cost_val))

            # Include future predicted points as dynamic threat zones
            for pt in obs.get("predicted_trajectory", [])[1:4]: # Next 1.5 seconds
                p_row, p_col = self.world_to_grid(pt[0], pt[1])
                for dr in range(-obs_radius_cells, obs_radius_cells + 1):
                    for dc in range(-obs_radius_cells, obs_radius_cells + 1):
                        r = p_row + dr
                        c = p_col + dc
                        if self.is_inside(r, c):
                            grid[r, c] = max(grid[r, c], 0.75) # High threat

        return grid
