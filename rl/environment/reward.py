"""
reward.py — Multi-Objective Reward Function for Autonomous Navigation.

Implements structured reward shaping designed for Stable-Baselines3 PPO:
1. Progress Reward: Encourages longitudinal movement along the corridor.
2. Lane Keeping Reward: Penalizes excessive lateral deviation from the lane center.
3. Heading Alignment Reward: Penalizes driving diagonal to the road axis.
4. Obstacle Clearance / Repulsive Field: Penalizes encroachment into safety buffers.
5. Action Smoothness & Comfort: Penalizes abrupt jerk in steering and acceleration.
6. Target Speed Tracking: Rewards maintaining optimal cruising speed (e.g. 35-40 km/h).
7. Terminal Outcomes: Heavy penalty for collision / off-road, bonus for goal reached.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, List
from .vehicle import VehicleState, Vehicle
from .obstacle import Obstacle


@dataclass
class RewardWeights:
    """Configurable weights for each component of the reward function."""
    w_progress: float = 2.5       # Weight for forward distance gained
    w_lane: float = 0.8           # Weight for centering within road corridor
    w_heading: float = 0.5        # Weight for road alignment
    w_clearance: float = 1.2      # Weight for distance buffer around obstacles
    w_smoothness: float = 0.15    # Weight for smooth control inputs
    w_speed: float = 0.4          # Weight for maintaining target cruising speed
    
    # Terminal rewards / penalties
    r_collision: float = -120.0
    r_off_road: float = -60.0
    r_goal_reached: float = 80.0
    
    # Safety thresholds
    safe_obstacle_margin: float = 4.5  # meters
    target_speed: float = 10.0         # m/s (~36 km/h)


class RewardCalculator:
    """Calculates multi-objective scalar rewards and provides component telemetry."""

    def __init__(self, weights: RewardWeights = None):
        self.weights = weights or RewardWeights()

    def compute(
        self,
        prev_state: VehicleState,
        curr_state: VehicleState,
        action: int,
        obstacles: List[Obstacle],
        road_width: float,
        collision: bool,
        off_road: bool,
        goal_reached: bool
    ) -> tuple[float, Dict[str, float]]:
        """
        Computes the step reward and returns:
          (total_reward, reward_breakdown_dict)
        """
        # Terminal penalties take immediate precedence
        if collision:
            return self.weights.r_collision, {"collision_penalty": self.weights.r_collision}
            
        if off_road:
            return self.weights.r_off_road, {"off_road_penalty": self.weights.r_off_road}
            
        if goal_reached:
            return self.weights.r_goal_reached, {"goal_reached_bonus": self.weights.r_goal_reached}

        half_w = road_width / 2.0

        # 1. Forward progress (meters gained along x-axis)
        dx = curr_state.x - prev_state.x
        r_progress = self.weights.w_progress * dx

        # 2. Lane keeping (normalized quadratic penalty for lateral deviation)
        norm_y = abs(curr_state.y) / max(1.0, half_w)
        r_lane = - self.weights.w_lane * (norm_y ** 2)

        # 3. Heading alignment (penalize yaw angle away from longitudinal axis)
        norm_theta = abs(curr_state.theta) / Vehicle.MAX_HEADING
        r_heading = - self.weights.w_heading * norm_theta

        # 4. Obstacle clearance repulsive field
        r_clearance = 0.0
        for obs in obstacles:
            dist = obs.distance_to(curr_state.x, curr_state.y)
            critical_dist = obs.radius + (Vehicle.LENGTH / 2.0)
            if dist < self.weights.safe_obstacle_margin:
                # Proximity repulsion grows non-linearly as distance approaches critical boundary
                penetration = (self.weights.safe_obstacle_margin - dist) / max(0.1, self.weights.safe_obstacle_margin - critical_dist)
                r_clearance -= self.weights.w_clearance * float(np.clip(penetration, 0.0, 3.0))

        # 5. Action smoothness (penalize aggressive steering/braking changes)
        steer_diff = abs(curr_state.steer - prev_state.steer)
        accel_diff = abs(curr_state.accel - prev_state.accel)
        r_smooth = - self.weights.w_smoothness * (steer_diff + 0.2 * accel_diff)

        # 6. Target speed tracking (encourage smooth cruising without stalling or speeding)
        speed_error = abs(curr_state.v - self.weights.target_speed) / self.weights.target_speed
        r_speed = self.weights.w_speed * (1.0 - float(np.clip(speed_error, 0.0, 2.0)))

        # Total step reward
        total_reward = r_progress + r_lane + r_heading + r_clearance + r_smooth + r_speed

        breakdown = {
            "progress": round(r_progress, 3),
            "lane": round(r_lane, 3),
            "heading": round(r_heading, 3),
            "clearance": round(r_clearance, 3),
            "smoothness": round(r_smooth, 3),
            "speed": round(r_speed, 3),
            "total": round(total_reward, 3)
        }

        return float(total_reward), breakdown
