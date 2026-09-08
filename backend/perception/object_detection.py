"""
YOLO-Compatible Object Detection Pipeline for Autonomous Driving Perception.
Detects pedestrians, cars, motorcycles, auto-rickshaws, buses, trucks, animals, and obstacles.
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from config import config
from backend.perception.distance_estimation import DistanceEstimator


class ObjectDetector:
    """
    Perception engine running YOLO object detection with distance estimation
    and Indian road context class mapping.
    """

    def __init__(self):
        self.conf_threshold = config.perception.confidence_threshold
        self.nms_threshold = config.perception.nms_iou_threshold
        self.distance_estimator = DistanceEstimator(
            camera_width=config.sensor.camera_width,
            camera_height=config.sensor.camera_height,
            camera_fov=config.sensor.camera_fov
        )
        self.yolo_model = None
        self._initialize_yolo()

    def _initialize_yolo(self):
        """Attempts to load Ultralytics YOLO model; handles fallback if weights unavailable."""
        try:
            from ultralytics import YOLO
            model_path = config.perception.yolo_model_path
            self.yolo_model = YOLO(model_path)
            print(f"[ObjectDetector] Successfully loaded YOLO model: {model_path}")
        except Exception as e:
            print(f"[ObjectDetector] YOLO model load note: {e}. Using resilient perception fallback.")
            self.yolo_model = None

    def detect(
        self,
        rgb_frame: np.ndarray,
        depth_map: Optional[np.ndarray] = None,
        ground_truth_actors: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes perception on current camera frame.
        Returns a list of structured detection dictionaries.
        """
        detections: List[Dict[str, Any]] = []

        if rgb_frame is None or rgb_frame.size == 0:
            return detections

        # Path A: Real YOLO Inference
        if self.yolo_model is not None:
            try:
                results = self.yolo_model.predict(
                    source=rgb_frame,
                    conf=self.conf_threshold,
                    iou=self.nms_threshold,
                    device=config.perception.device,
                    verbose=False
                )
                
                if results and len(results) > 0:
                    r = results[0]
                    for box in r.boxes:
                        cls_id = int(box.cls[0].item())
                        confidence = float(box.conf[0].item())
                        coords = box.xyxy[0].tolist() # [x1, y1, x2, y2]
                        bbox = (int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3]))
                        
                        # Map COCO classes to Indian road domain
                        class_name = config.perception.coco_indian_road_mapping.get(cls_id, "obstacle")
                        
                        # Distance & 3D Relative position
                        dist, rel_pos = self.distance_estimator.estimate_distance(bbox, class_name, depth_map)
                        
                        detections.append({
                            "object_id": -1, # Set later by ObjectTracker
                            "class_name": class_name,
                            "confidence": round(confidence, 3),
                            "bounding_box": [bbox[0], bbox[1], bbox[2], bbox[3]],
                            "distance": round(dist, 2),
                            "relative_position": rel_pos,
                            "velocity": 0.0,
                            "direction": 0.0
                        })
            except Exception as e:
                print(f"[ObjectDetector] YOLO inference error: {e}")

        # Path B: CARLA Simulator / Scenario Actors Ground-Truth Projection (High fidelity perception)
        if len(detections) == 0 and ground_truth_actors:
            for idx, actor in enumerate(ground_truth_actors):
                rel_x = actor.get("rel_x", 10.0) # Forward distance
                rel_y = actor.get("rel_y", 0.0)  # Lateral offset
                rel_z = actor.get("rel_z", 0.0)
                class_name = actor.get("type", "car")
                
                # Only process objects in front of camera (positive X) and within FOV
                if rel_x > 0.5 and rel_x < 80.0:
                    dist = float(np.sqrt(rel_x**2 + rel_y**2 + rel_z**2))
                    
                    # Project 3D point to 2D image pixels using pinhole model
                    u = int(self.distance_estimator.cx + (rel_y * self.distance_estimator.fx) / rel_x)
                    v = int(self.distance_estimator.cy - (rel_z * self.distance_estimator.fy) / rel_x)
                    
                    # Estimate bounding box size in pixels
                    real_h = self.distance_estimator.REAL_WORLD_HEIGHTS.get(class_name, 1.5)
                    box_h = int((self.distance_estimator.fy * real_h) / rel_x)
                    box_w = int(box_h * 0.75)
                    
                    x1 = max(0, u - box_w // 2)
                    y1 = max(0, v - box_h // 2)
                    x2 = min(config.sensor.camera_width, u + box_w // 2)
                    y2 = min(config.sensor.camera_height, v + box_h // 2)
                    
                    if (x2 - x1) > 5 and (y2 - y1) > 5:
                        detections.append({
                            "object_id": actor.get("id", idx + 1),
                            "class_name": class_name,
                            "confidence": round(float(actor.get("confidence", 0.92)), 2),
                            "bounding_box": [x1, y1, x2, y2],
                            "distance": round(dist, 2),
                            "relative_position": (round(rel_x, 2), round(rel_y, 2), round(rel_z, 2)),
                            "velocity": round(float(actor.get("speed", 0.0)), 2),
                            "direction": round(float(actor.get("heading", 0.0)), 2)
                        })

        return detections

    def draw_detections(self, image: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """Renders bounding boxes, distance tags, and class badges on image frame."""
        annotated = image.copy()
        
        # Color palette for classes
        colors = {
            "pedestrian": (0, 165, 255),    # Orange
            "motorcycle": (255, 0, 255),    # Magenta
            "auto_rickshaw": (0, 255, 255), # Yellow
            "car": (0, 255, 0),            # Green
            "bus": (255, 255, 0),          # Cyan
            "truck": (255, 128, 0),        # Amber
            "animal": (180, 105, 255),     # Pink
            "debris": (0, 0, 255),         # Red
            "obstacle": (0, 0, 255)
        }

        for det in detections:
            bbox = det["bounding_box"]
            cls_name = det["class_name"]
            dist = det["distance"]
            obj_id = det.get("object_id", "")
            vel = det.get("velocity", 0.0)
            
            color = colors.get(cls_name, (255, 255, 255))
            
            # Draw Bounding Box
            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            # Label banner
            id_str = f"#{obj_id} " if obj_id != -1 else ""
            vel_str = f" | {vel*3.6:.0f}km/h" if vel > 0.2 else ""
            label = f"{id_str}{cls_name.upper()} {dist:.1f}m{vel_str}"
            
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(annotated, (bbox[0], bbox[1] - 18), (bbox[0] + w + 6, bbox[1]), color, -1)
            cv2.putText(annotated, label, (bbox[0] + 3, bbox[1] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        return annotated
