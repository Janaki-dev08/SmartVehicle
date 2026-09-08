"""
Multi-Frame Object Tracking Module.
Maintains persistent track IDs, computes velocity vectors, and smoothes 3D trajectories.
"""

import numpy as np
import time
from typing import List, Dict, Any, Tuple
from config import config


class TrackedObject:
    """Represents an active track across time steps."""

    def __init__(self, track_id: int, detection: Dict[str, Any]):
        self.track_id = track_id
        self.class_name = detection["class_name"]
        self.confidence = detection["confidence"]
        self.bounding_box = detection["bounding_box"]
        self.distance = detection["distance"]
        
        rel_pos = detection.get("relative_position", (10.0, 0.0, 0.0))
        self.x = rel_pos[0] # Forward
        self.y = rel_pos[1] # Lateral
        self.z = rel_pos[2] # Vertical
        
        self.vx = 0.0
        self.vy = 0.0
        self.speed = detection.get("velocity", 0.0)
        self.heading = detection.get("direction", 0.0)
        
        self.history: List[Tuple[float, float, float]] = [(self.x, self.y, time.time())]
        self.hits = 1
        self.age = 1
        self.time_since_update = 0

    def update(self, detection: Dict[str, Any], dt: float = 0.05):
        """Updates track with new detection measurement and estimates velocity."""
        self.confidence = 0.7 * self.confidence + 0.3 * detection["confidence"]
        self.bounding_box = detection["bounding_box"]
        self.distance = detection["distance"]
        
        new_rel = detection.get("relative_position", (self.x, self.y, self.z))
        new_x, new_y, new_z = new_rel[0], new_rel[1], new_rel[2]
        
        if dt > 0.001:
            # Velocity estimation with exponential moving average filter
            raw_vx = (new_x - self.x) / dt
            raw_vy = (new_y - self.y) / dt
            self.vx = 0.6 * self.vx + 0.4 * raw_vx
            self.vy = 0.6 * self.vy + 0.4 * raw_vy
            self.speed = float(np.sqrt(self.vx**2 + self.vy**2))
            if self.speed > 0.3:
                self.heading = float(np.arctan2(self.vy, self.vx))
        
        self.x = new_x
        self.y = new_y
        self.z = new_z
        
        self.history.append((self.x, self.y, time.time()))
        if len(self.history) > 30:
            self.history.pop(0)
            
        self.hits += 1
        self.age += 1
        self.time_since_update = 0

    def mark_missed(self):
        """Increments missed update counter."""
        self.age += 1
        self.time_since_update += 1

    def to_dict(self) -> Dict[str, Any]:
        """Returns structured dictionary representation for telemetry/dashboard."""
        return {
            "object_id": self.track_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 2),
            "bounding_box": self.bounding_box,
            "distance": round(self.distance, 2),
            "relative_position": (round(self.x, 2), round(self.y, 2), round(self.z, 2)),
            "velocity": round(self.speed, 2),
            "vx": round(self.vx, 2),
            "vy": round(self.vy, 2),
            "direction": round(float(np.rad2deg(self.heading)), 1),
            "hits": self.hits,
            "age": self.age
        }


class ObjectTracker:
    """
    Multi-Target Tracker using Euclidean association and Kalman-like state updates.
    """

    def __init__(self, max_distance_threshold: float = 4.0):
        self.max_distance_threshold = max_distance_threshold
        self.next_track_id = 1
        self.tracks: List[TrackedObject] = []
        self.last_update_time = time.time()

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Associates detections to tracks and maintains active tracks.
        """
        now = time.time()
        dt = max(0.01, min(0.2, now - self.last_update_time))
        self.last_update_time = now

        unmatched_detections = list(range(len(detections)))
        unmatched_tracks = list(range(len(self.tracks)))
        matched_pairs: List[Tuple[int, int]] = []

        # Cost matrix based on 3D spatial proximity
        if len(self.tracks) > 0 and len(detections) > 0:
            cost_matrix = np.zeros((len(self.tracks), len(detections)))
            for t_idx, track in enumerate(self.tracks):
                for d_idx, det in enumerate(detections):
                    rel = det.get("relative_position", (0.0, 0.0, 0.0))
                    dist = np.sqrt((track.x - rel[0])**2 + (track.y - rel[1])**2)
                    # Class mismatch penalty
                    if track.class_name != det["class_name"]:
                        dist += 5.0
                    cost_matrix[t_idx, d_idx] = dist

            # Greedy Hungarian-like matching
            while True:
                min_val = np.min(cost_matrix)
                if min_val > self.max_distance_threshold:
                    break
                min_idx = np.unravel_index(np.argmin(cost_matrix), cost_matrix.shape)
                t_idx, d_idx = min_idx[0], min_idx[1]
                
                matched_pairs.append((t_idx, d_idx))
                if t_idx in unmatched_tracks:
                    unmatched_tracks.remove(t_idx)
                if d_idx in unmatched_detections:
                    unmatched_detections.remove(d_idx)
                    
                cost_matrix[t_idx, :] = 1e6
                cost_matrix[:, d_idx] = 1e6

        # Update matched tracks
        for t_idx, d_idx in matched_pairs:
            self.tracks[t_idx].update(detections[d_idx], dt)
            detections[d_idx]["object_id"] = self.tracks[t_idx].track_id
            detections[d_idx]["velocity"] = round(self.tracks[t_idx].speed, 2)
            detections[d_idx]["direction"] = round(float(np.rad2deg(self.tracks[t_idx].heading)), 1)

        # Mark unmatched tracks as missed
        for t_idx in unmatched_tracks:
            self.tracks[t_idx].mark_missed()

        # Initialize new tracks for unmatched detections
        for d_idx in unmatched_detections:
            new_track = TrackedObject(self.next_track_id, detections[d_idx])
            detections[d_idx]["object_id"] = self.next_track_id
            self.next_track_id += 1
            self.tracks.append(new_track)

        # Prune dead tracks
        max_age = config.perception.tracker_max_age_frames
        self.tracks = [t for t in self.tracks if t.time_since_update <= max_age]

        # Return structured list of active tracked objects
        return [t.to_dict() for t in self.tracks if t.hits >= 1]
