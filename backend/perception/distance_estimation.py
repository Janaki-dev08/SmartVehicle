"""
Distance Estimation Module for Autonomous Vehicle Perception.
Computes 3D relative coordinates (X=forward, Y=right, Z=up) and Euclidean distance
using CARLA Depth buffers with a geometric pinhole fallback model.
"""

import numpy as np
from typing import Dict, Tuple, Optional


class DistanceEstimator:
    """
    Calculates spatial distance and 3D relative positions of detected road objects.
    """

    # Typical real-world heights (in meters) for standard and Indian road actors
    REAL_WORLD_HEIGHTS: Dict[str, float] = {
        "pedestrian": 1.70,
        "bicycle": 1.10,
        "motorcycle": 1.20,
        "car": 1.50,
        "auto_rickshaw": 1.80,
        "bus": 3.20,
        "truck": 3.50,
        "animal": 1.10,
        "obstacle": 0.60,
        "debris": 0.40,
    }

    def __init__(self, camera_width: int = 800, camera_height: int = 600, camera_fov: float = 90.0):
        self.width = camera_width
        self.height = camera_height
        self.fov = camera_fov
        
        fov_rad = np.deg2rad(self.fov)
        self.fx = (self.width / 2.0) / np.tan(fov_rad / 2.0)
        self.fy = self.fx
        self.cx = self.width / 2.0
        self.cy = self.height / 2.0

    def estimate_distance(
        self,
        bbox: Tuple[int, int, int, int], # (x1, y1, x2, y2) in pixels
        class_name: str,
        depth_map: Optional[np.ndarray] = None
    ) -> Tuple[float, Tuple[float, float, float]]:
        """
        Calculates distance and relative position (forward_x, lateral_y, vertical_z) in meters.
        Returns:
            (distance_meters, (rel_x, rel_y, rel_z))
        """
        x1, y1, x2, y2 = bbox
        box_w = max(1, x2 - x1)
        box_h = max(1, y2 - y1)
        u_center = (x1 + x2) / 2.0
        v_center = (y1 + y2) / 2.0

        forward_x = 0.0

        # Method 1: Direct CARLA Depth Buffer Query
        if depth_map is not None and depth_map.shape[0] == self.height and depth_map.shape[1] == self.width:
            # Sample central 40% of bounding box to eliminate background bleed
            ymin = int(y1 + 0.3 * box_h)
            ymax = int(y1 + 0.7 * box_h)
            xmin = int(x1 + 0.3 * box_w)
            xmax = int(x1 + 0.7 * box_w)
            
            ymin = max(0, min(self.height - 1, ymin))
            ymax = max(ymin + 1, min(self.height, ymax))
            xmin = max(0, min(self.width - 1, xmin))
            xmax = max(xmin + 1, min(self.width, xmax))

            depth_patch = depth_map[ymin:ymax, xmin:xmax]
            valid_depths = depth_patch[depth_patch > 0.5]
            if len(valid_depths) > 0:
                forward_x = float(np.median(valid_depths))

        # Method 2: Pinhole Geometric Fallback (if depth_map unavailable or uninformative)
        if forward_x <= 0.5 or forward_x > 150.0:
            target_real_h = self.REAL_WORLD_HEIGHTS.get(class_name.lower(), 1.5)
            # Optical formula: Z = (fy * H_real) / h_pixels
            forward_x = (self.fy * target_real_h) / box_h

        # Clamp forward distance to realistic operational range
        forward_x = max(1.0, min(120.0, forward_x))

        # Compute lateral (Y) and vertical (Z) coordinates via camera intrinsics
        # Camera frame: X_cam = right, Y_cam = down, Z_cam = forward
        # Vehicle frame: X_veh = forward (Z_cam), Y_veh = right (X_cam), Z_veh = up (-Y_cam)
        lateral_y = ((u_center - self.cx) * forward_x) / self.fx
        vertical_z = -((v_center - self.cy) * forward_x) / self.fy

        # Euclidean distance
        distance = float(np.sqrt(forward_x**2 + lateral_y**2 + vertical_z**2))

        return distance, (round(forward_x, 2), round(lateral_y, 2), round(vertical_z, 2))
