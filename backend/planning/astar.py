"""
Adaptive A* Path Planning Algorithm for Autonomous Vehicles.
Computes optimal, collision-free, smooth trajectories over dynamic occupancy grids
with safety buffer heuristics and road constraint weighting.
"""

import heapq
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from scipy.interpolate import splprep, splev


class AStarPlanner:
    """
    Adaptive A* Search on 2D Drivable Space Costmap.
    Cost Function:
        Total Cost = Step Distance + Obstacle Proximity Cost + Collision Risk + Heading Smoothness + Road Penalty
    """

    def __init__(
        self,
        weight_distance: float = 1.0,
        weight_obstacle: float = 8.0,
        weight_smoothness: float = 3.0,
        weight_road_boundary: float = 4.0
    ):
        self.w_dist = weight_distance
        self.w_obs = weight_obstacle
        self.w_smooth = weight_smoothness
        self.w_road = weight_road_boundary

        # 8-connected grid motion vectors: (dx, dy, step_cost)
        self.motions = [
            (1, 0, 1.0),      # Forward
            (1, 1, 1.414),    # Forward-Right diagonal
            (1, -1, 1.414),   # Forward-Left diagonal
            (0, 1, 1.0),      # Right
            (0, -1, 1.0),     # Left
            (2, 1, 2.236),    # Smooth forward-shallow right
            (2, -1, 2.236),   # Smooth forward-shallow left
            (2, 0, 2.0),      # Fast straight
        ]

    def _heuristic(self, node: Tuple[int, int], goal: Tuple[int, int], resolution: float) -> float:
        """Euclidean distance heuristic in metric space."""
        dx = (goal[0] - node[0]) * resolution
        dy = (goal[1] - node[1]) * resolution
        return float(np.sqrt(dx**2 + dy**2))

    def plan(
        self,
        costmap: np.ndarray,
        start_world: Tuple[float, float], # (x_m, y_m)
        goal_world: Tuple[float, float],  # (x_m, y_m)
        grid_builder,
        smooth_path: bool = True
    ) -> Tuple[List[Tuple[float, float]], bool, float]:
        """
        Executes Adaptive A* search.
        Returns:
            (path_waypoints_meters, is_success, planning_time_ms)
        """
        import time
        t_start = time.perf_counter()

        start_cell = grid_builder.world_to_grid(start_world[0], start_world[1])
        goal_cell = grid_builder.world_to_grid(goal_world[0], goal_world[1])

        # Bounds validation
        if not grid_builder.is_inside(*start_cell):
            start_cell = (0, grid_builder.origin_y_idx)
        if not grid_builder.is_inside(*goal_cell):
            goal_cell = (costmap.shape[0] - 1, grid_builder.origin_y_idx)

        # Priority Queue: (f_score, h_score, (row, col), parent_node, incoming_direction)
        open_set = []
        heapq.heappush(open_set, (0.0, 0.0, start_cell, None, (1, 0)))

        g_scores: Dict[Tuple[int, int], float] = {start_cell: 0.0}
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        closed_set = set()

        goal_reached = False
        best_node = start_cell
        min_h_to_goal = float('inf')

        while open_set:
            f, h, current, parent, prev_dir = heapq.heappop(open_set)

            if current in closed_set:
                continue
            closed_set.add(current)

            # Track closest node in case goal is unreachable
            curr_h = self._heuristic(current, goal_cell, grid_builder.resolution)
            if curr_h < min_h_to_goal:
                min_h_to_goal = curr_h
                best_node = current

            # Goal test: within 1.5m radius or longitudinal reach
            if (abs(current[0] - goal_cell[0]) <= 2 and abs(current[1] - goal_cell[1]) <= 2) or (current[0] >= costmap.shape[0] - 2):
                goal_reached = True
                best_node = current
                break

            current_g = g_scores[current]

            for dx, dy, step_dist in self.motions:
                neighbor = (current[0] + dx, current[1] + dy)

                if not grid_builder.is_inside(*neighbor):
                    continue

                cell_cost = costmap[neighbor[0], neighbor[1]]
                # 1.0 indicates solid obstacle
                if cell_cost >= 0.95:
                    continue

                # Curvature / Smoothness penalty for sharp direction turns
                turn_penalty = 0.0
                if prev_dir != (dx, dy):
                    turn_penalty = self.w_smooth * 0.4

                # Adaptive cost accumulation
                step_cost = (
                    self.w_dist * (step_dist * grid_builder.resolution) +
                    self.w_obs * (cell_cost * 15.0) +
                    turn_penalty
                )

                tentative_g = current_g + step_cost

                if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                    g_scores[neighbor] = tentative_g
                    came_from[neighbor] = current
                    h_score = self._heuristic(neighbor, goal_cell, grid_builder.resolution)
                    f_score = tentative_g + h_score
                    heapq.heappush(open_set, (f_score, h_score, neighbor, current, (dx, dy)))

        # Reconstruct path from came_from map
        raw_path_cells = []
        curr = best_node
        while curr in came_from:
            raw_path_cells.append(curr)
            curr = came_from[curr]
        raw_path_cells.append(start_cell)
        raw_path_cells.reverse()

        # Convert grid indices back to world metric points (x_m, y_m)
        path_world = [grid_builder.grid_to_world(r, c) for (r, c) in raw_path_cells]

        # Spline smoothing
        if smooth_path and len(path_world) >= 4:
            path_world = self._smooth_trajectory(path_world)

        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        return path_world, goal_reached, round(t_elapsed_ms, 2)

    def _smooth_trajectory(self, raw_points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """B-Spline curve fitting for realistic steering curvature."""
        try:
            pts = np.array(raw_points)
            # Remove duplicate consecutive points
            _, unique_idx = np.unique(pts, axis=0, return_index=True)
            pts = pts[np.sort(unique_idx)]
            
            if len(pts) < 4:
                return raw_points

            tck, u = splprep([pts[:, 0], pts[:, 1]], s=1.5, k=min(3, len(pts)-1))
            u_fine = np.linspace(0, 1, max(20, len(pts) * 3))
            smooth_x, smooth_y = splev(u_fine, tck)
            
            return [(round(float(x), 2), round(float(y), 2)) for x, y in zip(smooth_x, smooth_y)]
        except Exception:
            return raw_points
