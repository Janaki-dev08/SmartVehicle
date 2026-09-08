"""
Central Configuration Module for Autonomous Vehicle Simulation
Adaptive Path Planning and Collision Avoidance on Unstructured Indian Roads
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class CarlaConfig:
    """CARLA Simulator Connection and Map Settings."""
    host: str = os.getenv("CARLA_HOST", "localhost")
    port: int = int(os.getenv("CARLA_PORT", "2000"))
    timeout: float = float(os.getenv("CARLA_TIMEOUT", "10.0"))
    map_name: str = os.getenv("CARLA_MAP", "Town03")
    sync_mode: bool = os.getenv("CARLA_SYNC_MODE", "true").lower() == "true"
    fixed_delta_seconds: float = float(os.getenv("CARLA_DELTA_SECONDS", "0.05"))  # 20 Hz
    render_spectator: bool = os.getenv("CARLA_RENDER_SPECTATOR", "true").lower() == "true"


@dataclass
class VehicleConfig:
    """Ego Vehicle Kinematics and Dimensions."""
    blueprint_id: str = os.getenv("VEHICLE_BLUEPRINT", "vehicle.tesla.model3")
    length: float = 4.7      # meters
    width: float = 2.0       # meters
    height: float = 1.45     # meters
    wheelbase: float = 2.875 # meters
    max_steer_angle: float = 0.7  # ~40 degrees in radians
    max_speed_kmh: float = float(os.getenv("MAX_SPEED", "40.0")) # km/h on Indian urban roads
    target_speed_kmh: float = 30.0
    max_acceleration: float = float(os.getenv("MAX_ACCELERATION", "3.0"))  # m/s^2
    max_braking: float = float(os.getenv("MAX_BRAKING", "6.0"))            # m/s^2
    emergency_braking: float = 8.5                                         # m/s^2


@dataclass
class SensorConfig:
    """On-board Sensor Specifications."""
    camera_width: int = int(os.getenv("CAMERA_WIDTH", "800"))
    camera_height: int = int(os.getenv("CAMERA_HEIGHT", "600"))
    camera_fov: float = float(os.getenv("CAMERA_FOV", "90.0"))
    camera_fps: int = 20
    camera_transform: Tuple[float, float, float] = (1.6, 0.0, 1.7) # x, y, z relative to vehicle
    depth_camera_enabled: bool = True
    lidar_enabled: bool = True
    lidar_channels: int = 32
    lidar_range: float = 50.0 # meters
    collision_sensor_enabled: bool = True
    gnss_enabled: bool = True


@dataclass
class PerceptionConfig:
    """YOLO Object Detection & Multi-Frame Tracking Settings."""
    yolo_model_path: str = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
    confidence_threshold: float = float(os.getenv("YOLO_CONFIDENCE", "0.45"))
    nms_iou_threshold: float = 0.45
    device: str = os.getenv("PERCEPTION_DEVICE", "cpu")  # 'cuda' or 'cpu'
    
    # Custom class mapping for Indian Road Context
    coco_indian_road_mapping: Dict[int, str] = field(default_factory=lambda: {
        0: "pedestrian",       # person
        1: "bicycle",          # bicycle
        2: "car",              # car
        3: "motorcycle",       # motorcycle / scooter
        5: "bus",              # bus
        7: "truck",            # truck
        15: "animal",          # cat
        16: "animal",          # dog
        17: "animal",          # horse
        18: "animal",          # sheep
        19: "animal",          # cow / cattle
    })
    
    tracker_max_age_frames: int = 15
    tracker_min_hits: int = 3
    distance_estimation_method: str = "depth_geometry_hybrid" # 'carla_depth', 'pinhole', 'hybrid'


@dataclass
class PlanningConfig:
    """Adaptive A* Grid & Path Planning Parameters."""
    grid_resolution: float = 0.5   # meters per grid cell
    grid_width: int = 100          # 50 meters total width (-25m to +25m lateral)
    grid_length: int = 160         # 80 meters forward horizon
    replan_interval: float = float(os.getenv("REPLAN_INTERVAL", "0.1")) # 10 Hz replan check
    lookahead_distance_min: float = 4.0   # meters
    lookahead_distance_max: float = 15.0  # meters
    
    # Cost weights
    weight_distance: float = 1.0
    weight_obstacle_proximity: float = 5.0
    weight_collision_risk: float = 10.0
    weight_smoothness: float = 2.5
    weight_road_boundary: float = 4.0
    
    obstacle_safety_margin: float = float(os.getenv("OBSTACLE_CLEARANCE", "1.8")) # meters safety radius
    spline_smoothing_factor: float = 0.5


@dataclass
class CollisionConfig:
    """Collision Risk Estimation & TTC Thresholds."""
    ttc_warning_threshold: float = float(os.getenv("TTC_WARNING_THRESHOLD", "4.0"))    # seconds
    ttc_high_threshold: float = float(os.getenv("TTC_HIGH_THRESHOLD", "2.5"))          # seconds
    ttc_critical_threshold: float = float(os.getenv("TTC_CRITICAL_THRESHOLD", "1.5"))  # seconds
    
    lateral_safety_clearance: float = 1.5  # meters
    longitudinal_safety_clearance: float = 3.0  # meters
    prediction_horizon: float = 3.0 # seconds into future for obstacle trajectory


@dataclass
class GoogleMapsConfig:
    """Google Maps High-Level Navigation."""
    api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    enabled: bool = os.getenv("ENABLE_GOOGLE_MAPS", "false").lower() == "true"
    default_origin: str = "Connaught Place, New Delhi, India"
    default_destination: str = "India Gate, New Delhi, India"


@dataclass
class SystemConfig:
    """Top-Level Application Configuration."""
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    logs_dir: Path = BASE_DIR / "data" / "logs"
    scenarios_dir: Path = BASE_DIR / "data" / "scenarios"
    docs_dir: Path = BASE_DIR / "docs"
    
    carla: CarlaConfig = field(default_factory=CarlaConfig)
    vehicle: VehicleConfig = field(default_factory=VehicleConfig)
    sensor: SensorConfig = field(default_factory=SensorConfig)
    perception: PerceptionConfig = field(default_factory=PerceptionConfig)
    planning: PlanningConfig = field(default_factory=PlanningConfig)
    collision: CollisionConfig = field(default_factory=CollisionConfig)
    maps: GoogleMapsConfig = field(default_factory=GoogleMapsConfig)
    
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    telemetry_frequency_hz: int = 20 # 20 Hz WebSocket broadcast


# Global singleton instance
config = SystemConfig()
