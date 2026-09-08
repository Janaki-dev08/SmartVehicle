"""
Camera Sensor Interface for RGB and Depth Streams.
Supports real CARLA camera sensors and synthetic fallback generation.
"""

import numpy as np
import cv2
import base64
import time
from typing import Optional, Tuple, Dict, Any


class CameraSensor:
    """
    Manages CARLA RGB and Depth camera feeds, image decoding,
    and synthetic frame generation for computer vision pipelines.
    """

    def __init__(self, width: int = 800, height: int = 600, fov: float = 90.0):
        self.width = width
        self.height = height
        self.fov = fov
        
        # Pinhole camera intrinsic matrix parameters
        # focal length f = (width / 2) / tan(fov_rad / 2)
        fov_rad = np.deg2rad(self.fov)
        self.fx = (self.width / 2.0) / np.tan(fov_rad / 2.0)
        self.fy = self.fx
        self.cx = self.width / 2.0
        self.cy = self.height / 2.0
        self.intrinsics = np.array([
            [self.fx, 0, self.cx],
            [0, self.fy, self.cy],
            [0, 0, 1]
        ], dtype=np.float32)

        # Buffers
        self.latest_rgb: Optional[np.ndarray] = None
        self.latest_depth: Optional[np.ndarray] = None  # Float depth in meters
        self.latest_timestamp: float = 0.0
        self._carla_rgb_sensor = None
        self._carla_depth_sensor = None

    def carla_rgb_callback(self, carla_image) -> None:
        """Callback for CARLA RGB sensor listener."""
        try:
            array = np.frombuffer(carla_image.raw_data, dtype=np.dtype("uint8"))
            array = np.reshape(array, (carla_image.height, carla_image.width, 4))
            # Extract BGR / RGB
            rgb = array[:, :, :3]
            self.latest_rgb = rgb
            self.latest_timestamp = time.time()
        except Exception as e:
            print(f"[Camera] Error decoding CARLA RGB: {e}")

    def carla_depth_callback(self, carla_image) -> None:
        """
        Callback for CARLA Depth sensor listener.
        CARLA encodes normalized depth in 24 bits: (R + G*256 + B*256*256) / (256^3 - 1) * 1000m
        """
        try:
            array = np.frombuffer(carla_image.raw_data, dtype=np.dtype("uint8"))
            array = np.reshape(array, (carla_image.height, carla_image.width, 4))
            array = array[:, :, :3].astype(np.float32)
            # Normalized depth calculation (in meters, max 1000m)
            depth = (array[:, :, 0] + array[:, :, 1] * 256.0 + array[:, :, 2] * 256.0 * 256.0) / (256.0**3 - 1.0) * 1000.0
            self.latest_depth = depth
        except Exception as e:
            print(f"[Camera] Error decoding CARLA Depth: {e}")

    def get_rgb_frame(self) -> np.ndarray:
        """Returns the latest RGB frame or generates a synthetic road scene."""
        if self.latest_rgb is not None:
            return self.latest_rgb.copy()
        return self._generate_synthetic_road_scene()

    def get_depth_frame(self) -> np.ndarray:
        """Returns the latest depth frame in meters."""
        if self.latest_depth is not None:
            return self.latest_depth.copy()
        return self._generate_synthetic_depth_map()

    def get_rgb_base64(self, quality: int = 70) -> str:
        """Encodes latest RGB frame to base64 JPEG string for WebSockets/UI."""
        frame = self.get_rgb_frame()
        success, encoded_image = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if success:
            return "data:image/jpeg;base64," + base64.b64encode(encoded_image).decode('utf-8')
        return ""

    def _generate_synthetic_road_scene(self) -> np.ndarray:
        """Generates realistic synthetic Indian road perspective when CARLA is offline."""
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Sky & Horizon
        img[0:int(self.height * 0.45), :] = [180, 200, 220] # Light Indian daytime sky
        
        # Ground / Road side
        img[int(self.height * 0.45):, :] = [80, 95, 75] # Roadside dust/vegetation
        
        # Road trapezoid (Unstructured / Narrow Indian Road)
        road_top_w = int(self.width * 0.2)
        road_bot_w = int(self.width * 0.85)
        top_y = int(self.height * 0.45)
        bot_y = self.height
        
        road_pts = np.array([
            [int(self.width / 2 - road_top_w / 2), top_y],
            [int(self.width / 2 + road_top_w / 2), top_y],
            [int(self.width / 2 + road_bot_w / 2), bot_y],
            [int(self.width / 2 - road_bot_w / 2), bot_y]
        ], np.int32)
        cv2.fillPoly(img, [road_pts], (70, 70, 70)) # Asphalt color
        
        # Unstructured road edges (broken / dirt borders)
        cv2.polylines(img, [road_pts], isClosed=False, color=(120, 130, 110), thickness=4)
        
        # Subtle dashed center line (often faded on Indian roads)
        dash_len = 15
        for y in range(top_y + 10, bot_y, 35):
            t = (y - top_y) / (bot_y - top_y)
            w = int(2 + t * 6)
            cv2.line(img, (int(self.width / 2), y), (int(self.width / 2), min(y + dash_len, bot_y)), (200, 200, 190), w)
            
        return img

    def _generate_synthetic_depth_map(self) -> np.ndarray:
        """Generates distance depth map corresponding to synthetic road scene."""
        depth = np.ones((self.height, self.width), dtype=np.float32) * 50.0
        top_y = int(self.height * 0.45)
        for y in range(top_y, self.height):
            # Distance decreases linearly as y moves from horizon down to bumper
            d = 50.0 * (1.0 - (y - top_y) / (self.height - top_y)) + 2.0
            depth[y, :] = max(2.0, d)
        return depth
