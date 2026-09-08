"""
road_env.py — Gymnasium Environment for Indian Road Simulation.

Simulates a structured-yet-unstructured road corridor with dynamic and static
Indian road obstacles (jaywalkers, motorcycles, autos, potholes).

Compatible with Gymnasium API (reset, step, render) and Stable-Baselines3.
"""

from __future__ import annotations
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Optional, Dict, Any, Tuple, List
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

from .vehicle import Vehicle, VehicleState
from .obstacle import Obstacle, ObstacleType, RiskLevel
from .reward import RewardCalculator, RewardWeights


class IndianRoadEnv(gym.Env):
    """
    Custom Gymnasium Environment for Local Autonomous Navigation on Indian Roads.
    
    Observation Space (Box, shape=(24,)):
      [0:6]   Ego Vehicle State:
              - norm_x (x / corridor_length)
              - norm_y (y / (road_width / 2))
              - norm_v (v / max_speed)
              - norm_theta (theta / max_heading)
              - dist_to_left_edge_norm
              - dist_to_right_edge_norm
      [6:22]  K=4 Nearest Obstacles (4 features each = 16 values):
              - rel_dx / 50.0
              - rel_dy / (road_width / 2)
              - rel_vx / max_speed
              - obstacle_radius_norm
      [22:24] Target Waypoint:
              - target_rel_dx / 50.0
              - target_rel_dy / (road_width / 2)
              
    Action Space (Discrete(8)):
      0: CRUISE
      1: STEER_LEFT
      2: STEER_RIGHT
      3: ACCELERATE
      4: BRAKE
      5: SWERVE_LEFT
      6: SWERVE_RIGHT
      7: EMERGENCY_STOP
    """

    metadata = {"render_modes": ["human", "rgb_array", "text"], "render_fps": 10}

    def __init__(
        self,
        corridor_length: float = 120.0,
        road_width: float = 7.0,
        num_lanes: int = 2,
        dt: float = 0.1,
        max_steps: int = 200,
        difficulty: int = 1,
        render_mode: Optional[str] = None
    ):
        super().__init__()
        self.corridor_length = corridor_length
        self.road_width = road_width
        self.num_lanes = num_lanes
        self.dt = dt
        self.max_steps = max_steps
        self.difficulty = difficulty
        self.render_mode = render_mode

        # Physics & Models
        self.vehicle = Vehicle()
        self.obstacles: List[Obstacle] = []
        self.target_x = corridor_length - 5.0
        self.target_y = 0.0
        self.reward_calculator = RewardCalculator()
        self.last_reward_breakdown: Dict[str, float] = {}

        # RL Spaces
        self.action_space = spaces.Discrete(8)
        self.num_obs_obstacles = 4
        self.obs_dim = 6 + (self.num_obs_obstacles * 4) + 2
        
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.obs_dim,),
            dtype=np.float32
        )

        # Simulation bookkeeping
        self.current_step = 0
        self.last_x = 0.0
        self.collision_occurred = False
        self.collision_obstacle_type = None
        self.goal_reached = False
        self.off_road = False
        self.episode_rewards: List[float] = []

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Resets the environment for a new episode."""
        super().reset(seed=seed)
        
        # Parse options
        if options and "difficulty" in options:
            self.difficulty = options["difficulty"]

        self.current_step = 0
        self.collision_occurred = False
        self.collision_obstacle_type = None
        self.goal_reached = False
        self.off_road = False
        self.episode_rewards = []
        self.last_reward_breakdown = {}

        # Reset Ego Vehicle at corridor start
        init_v = 5.0 + self.np_random.uniform(-1.0, 1.0)
        init_y = self.np_random.uniform(-0.5, 0.5)
        self.vehicle.reset(x=0.0, y=init_y, v=init_v, theta=0.0)
        self.last_x = 0.0

        # Spawn obstacles based on difficulty
        self._spawn_obstacles()

        obs = self._get_observation()
        info = self._get_info()
        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """Executes one simulation step."""
        self.current_step += 1
        
        # Snapshot previous state for reward shaping
        prev_state = VehicleState(
            x=self.vehicle.state.x,
            y=self.vehicle.state.y,
            v=self.vehicle.state.v,
            theta=self.vehicle.state.theta,
            steer=self.vehicle.state.steer,
            accel=self.vehicle.state.accel
        )
        
        # 1. Update vehicle state
        self.vehicle.apply_action(action, dt=self.dt)
        curr_x = self.vehicle.state.x
        curr_y = self.vehicle.state.y

        # 2. Update dynamic obstacles
        for obs in self.obstacles:
            obs.step(dt=self.dt)

        # 3. Collision checking
        self._check_collisions()

        # 4. Check boundaries and goal
        half_w = self.road_width / 2.0
        if abs(curr_y) > half_w + 1.2:
            self.off_road = True

        if curr_x >= self.target_x:
            self.goal_reached = True

        # 5. Compute Reward via RewardCalculator
        reward, self.last_reward_breakdown = self.reward_calculator.compute(
            prev_state=prev_state,
            curr_state=self.vehicle.state,
            action=action,
            obstacles=self.obstacles,
            road_width=self.road_width,
            collision=self.collision_occurred,
            off_road=self.off_road,
            goal_reached=self.goal_reached
        )
        self.episode_rewards.append(reward)

        # 6. Termination & Truncation flags
        terminated = bool(self.collision_occurred or self.goal_reached or self.off_road)
        truncated = bool(self.current_step >= self.max_steps)

        obs = self._get_observation()
        info = self._get_info()

        if self.render_mode == "human":
            self.render()

        return obs, reward, terminated, truncated, info

    def _spawn_obstacles(self) -> None:
        """Procedurally populates the road corridor with obstacles based on difficulty."""
        self.obstacles = []
        obs_id = 0
        
        # Obstacle counts scale with difficulty
        if self.difficulty == 1:
            num_static = self.np_random.integers(2, 4)
            num_dynamic = self.np_random.integers(1, 3)
        elif self.difficulty == 2:
            num_static = self.np_random.integers(3, 5)
            num_dynamic = self.np_random.integers(3, 5)
        else: # High difficulty / chaos
            num_static = self.np_random.integers(4, 7)
            num_dynamic = self.np_random.integers(4, 7)

        # Spawn static obstacles (potholes, parked vehicles, debris)
        static_types = [ObstacleType.POTHOLE, ObstacleType.PARKED_VEHICLE, ObstacleType.DEBRIS]
        used_x = []
        
        for _ in range(num_static):
            stype = static_types[int(self.np_random.integers(0, len(static_types)))]
            # Place in forward path (between x=20 and x=target_x - 10)
            x_pos = float(self.np_random.uniform(20.0, self.target_x - 10.0))
            # Ensure minimum separation
            if any(abs(x_pos - ux) < 8.0 for ux in used_x):
                continue
            used_x.append(x_pos)
            
            if stype == ObstacleType.PARKED_VEHICLE:
                # Parked vehicles are usually near the road shoulder (left or right edge)
                side = float(self.np_random.choice([-1.0, 1.0]))
                y_pos = side * (self.road_width / 2.0 - 1.0)
            else:
                y_pos = float(self.np_random.uniform(-self.road_width / 2.5, self.road_width / 2.5))

            self.obstacles.append(
                Obstacle(
                    obstacle_id=obs_id,
                    obstacle_type=stype,
                    x=x_pos,
                    y=y_pos,
                    vx=0.0,
                    vy=0.0,
                    road_width=self.road_width
                )
            )
            obs_id += 1

        # Spawn dynamic obstacles (pedestrians, autorickshaws, motorcycles, wrong-way)
        dynamic_types = [
            ObstacleType.PEDESTRIAN,
            ObstacleType.AUTORICKSHAW,
            ObstacleType.MOTORCYCLE,
            ObstacleType.WRONG_WAY,
            ObstacleType.STRAY_ANIMAL
        ]
        
        for _ in range(num_dynamic):
            dtype = dynamic_types[int(self.np_random.integers(0, len(dynamic_types)))]
            x_pos = float(self.np_random.uniform(25.0, self.target_x - 15.0))
            
            if dtype == ObstacleType.PEDESTRIAN:
                # Crosses road laterally from side to side
                start_side = self.np_random.choice([-1.0, 1.0])
                y_pos = start_side * (self.road_width / 2.0 + 0.5)
                vy = -start_side * self.np_random.uniform(0.8, 1.4)
                vx = 0.0
            elif dtype == ObstacleType.AUTORICKSHAW:
                y_pos = self.np_random.uniform(-1.5, 1.5)
                vx = self.np_random.uniform(3.0, 5.0)
                vy = self.np_random.uniform(-0.3, 0.3)
            elif dtype == ObstacleType.MOTORCYCLE:
                y_pos = self.np_random.uniform(-2.0, 2.0)
                vx = self.np_random.uniform(6.0, 8.5)
                vy = self.np_random.uniform(-0.5, 0.5)
            elif dtype == ObstacleType.WRONG_WAY:
                # Coming towards vehicle on vehicle's lane
                y_pos = self.np_random.uniform(-1.5, 1.5)
                vx = -self.np_random.uniform(3.5, 6.0)
                vy = 0.0
            else: # STRAY_ANIMAL
                y_pos = self.np_random.uniform(-2.0, 2.0)
                vx = self.np_random.uniform(-0.5, 0.5)
                vy = self.np_random.uniform(-0.4, 0.4)

            self.obstacles.append(
                Obstacle(
                    obstacle_id=obs_id,
                    obstacle_type=dtype,
                    x=x_pos,
                    y=y_pos,
                    vx=vx,
                    vy=vy,
                    road_width=self.road_width
                )
            )
            obs_id += 1

    def _check_collisions(self) -> None:
        """Checks intersection between vehicle bounding radius/box and all obstacles."""
        ego_x = self.vehicle.state.x
        ego_y = self.vehicle.state.y
        ego_radius = self.vehicle.LENGTH / 2.0

        for obs in self.obstacles:
            dist = obs.distance_to(ego_x, ego_y)
            # Collision if distance < combined radius
            if dist < (ego_radius * 0.7 + obs.radius):
                self.collision_occurred = True
                self.collision_obstacle_type = obs.type.value
                break

    def _compute_reward(
        self,
        action: int,
        prev_x: float,
        prev_y: float,
        curr_x: float,
        curr_y: float
    ) -> float:
        """
        Step reward calculation.
        - Forward progress bonus
        - Collision penalty (-100)
        - Goal reached bonus (+50)
        - Off-road penalty (-50)
        - Smoothness & center line encouragement
        """
        if self.collision_occurred:
            return -100.0

        if self.off_road:
            return -50.0

        if self.goal_reached:
            return 50.0

        # 1. Forward progress reward (normalized)
        dx = curr_x - prev_x
        r_progress = 2.0 * dx

        # 2. Road keeping reward (stay close to lane/center)
        half_w = self.road_width / 2.0
        r_lane = - 0.5 * (abs(curr_y) / half_w)

        # 3. Heading alignment reward
        r_heading = - 0.3 * abs(self.vehicle.state.theta)

        # 4. Proximity penalty to nearest obstacles
        r_proximity = 0.0
        for obs in self.obstacles:
            dist = obs.distance_to(curr_x, curr_y)
            if dist < 4.0:
                r_proximity -= (4.0 - dist) * 0.5

        # 5. Excessive steering penalty (smooth driving)
        r_smooth = - 0.05 * (abs(self.vehicle.state.steer))

        step_reward = r_progress + r_lane + r_heading + r_proximity + r_smooth
        return float(step_reward)

    def _get_observation(self) -> np.ndarray:
        """Constructs fixed 24-dimensional normalized observation vector."""
        state = self.vehicle.state
        half_w = self.road_width / 2.0

        # 1. Ego State (6 features)
        norm_x = np.clip(state.x / self.corridor_length, 0.0, 1.0)
        norm_y = np.clip(state.y / half_w, -2.0, 2.0)
        norm_v = np.clip(state.v / self.vehicle.MAX_SPEED, 0.0, 1.0)
        norm_theta = np.clip(state.theta / self.vehicle.MAX_HEADING, -1.0, 1.0)
        dist_left = np.clip((half_w - state.y) / half_w, -1.0, 2.0)
        dist_right = np.clip((state.y - (-half_w)) / half_w, -1.0, 2.0)

        ego_features = [norm_x, norm_y, norm_v, norm_theta, dist_left, dist_right]

        # 2. Closest K Obstacles (16 features)
        # Sort obstacles by distance to vehicle
        sorted_obs = sorted(
            self.obstacles,
            key=lambda o: (o.x - state.x)**2 + (o.y - state.y)**2
        )

        obs_features = []
        for i in range(self.num_obs_obstacles):
            if i < len(sorted_obs):
                ob = sorted_obs[i]
                rel_dx = np.clip((ob.x - state.x) / 50.0, -1.0, 1.0)
                rel_dy = np.clip((ob.y - state.y) / half_w, -2.0, 2.0)
                rel_vx = np.clip((ob.vx - state.v) / self.vehicle.MAX_SPEED, -1.0, 1.0)
                radius_norm = np.clip(ob.radius / 3.0, 0.1, 1.0)
                obs_features.extend([rel_dx, rel_dy, rel_vx, radius_norm])
            else:
                # Padding for absent obstacles (far away in front)
                obs_features.extend([1.0, 0.0, 0.0, 0.0])

        # 3. Target Waypoint Vector (2 features)
        target_dx = np.clip((self.target_x - state.x) / 50.0, -1.0, 1.0)
        target_dy = np.clip((self.target_y - state.y) / half_w, -1.0, 1.0)
        target_features = [target_dx, target_dy]

        full_obs = np.array(ego_features + obs_features + target_features, dtype=np.float32)
        return full_obs

    def _get_info(self) -> Dict[str, Any]:
        """Provides metadata dictionary for logging and visualization."""
        return {
            "step": self.current_step,
            "vehicle": self.vehicle.to_dict(),
            "collision": self.collision_occurred,
            "collision_type": self.collision_obstacle_type,
            "goal_reached": self.goal_reached,
            "off_road": self.off_road,
            "total_reward": round(float(sum(self.episode_rewards)), 2),
            "num_obstacles": len(self.obstacles),
            "reward_breakdown": self.last_reward_breakdown
        }

    def render(self) -> None:
        """Simple text rendering in terminal."""
        v = self.vehicle.state
        print(
            f"Step {self.current_step:03d} | x={v.x:6.2f}m | y={v.y:+5.2f}m | "
            f"v={v.v:5.2f}m/s ({v.v*3.6:5.1f}km/h) | theta={np.degrees(v.theta):+5.1f}° | "
            f"Obstacles: {len(self.obstacles)}"
        )

    def plot_rollout(self, save_path: str = "rollout_trajectory.png") -> str:
        """
        Generates a clear matplotlib diagram of the vehicle rollout trajectory,
        road corridor boundaries, and obstacle positions.
        """
        fig, ax = plt.subplots(figsize=(14, 4), dpi=150)
        
        half_w = self.road_width / 2.0
        
        # 1. Draw road boundaries and center line
        ax.axhline(half_w, color="black", linestyle="-", linewidth=2.5, label="Road Boundary")
        ax.axhline(-half_w, color="black", linestyle="-", linewidth=2.5)
        ax.axhline(0.0, color="gold", linestyle="--", linewidth=1.5, label="Center Lane")

        # Fill road surface
        ax.axhspan(-half_w, half_w, color="#f5f5f5", zorder=0)

        # 2. Draw Start & Goal lines
        ax.axvline(0.0, color="green", linestyle=":", linewidth=2, label="Start Line")
        ax.axvline(self.target_x, color="red", linestyle=":", linewidth=2, label="Goal Target")

        # 3. Draw Obstacles (static and dynamic paths)
        for obs in self.obstacles:
            # Current/Final Position
            circle = plt.Circle(
                (obs.x, obs.y),
                obs.radius,
                color=obs.profile.color,
                alpha=0.8,
                zorder=4,
                label=f"Obs: {obs.type.value}" if obs.id == 0 else ""
            )
            ax.add_patch(circle)
            
            # Label obstacle type
            ax.text(
                obs.x,
                obs.y + obs.radius + 0.3,
                obs.type.value,
                fontsize=7,
                ha="center",
                va="bottom",
                color="#333333",
                fontweight="bold"
            )

            # Draw trajectory path if dynamic
            if obs.profile.is_dynamic and len(obs.history) > 1:
                hist_x, hist_y = zip(*obs.history)
                ax.plot(hist_x, hist_y, color=obs.profile.color, linestyle=":", alpha=0.6, linewidth=1.2)

        # 4. Draw Vehicle Trajectory History
        if len(self.vehicle.trajectory_history) > 1:
            vx_hist, vy_hist, vv_hist, _ = zip(*self.vehicle.trajectory_history)
            ax.plot(vx_hist, vy_hist, color="#0066CC", linewidth=2.2, label="Vehicle Trajectory", zorder=5)
            
            # Draw final vehicle position marker
            final_x, final_y = vx_hist[-1], vy_hist[-1]
            car_box = patches.Rectangle(
                (final_x - self.vehicle.LENGTH / 2.0, final_y - self.vehicle.WIDTH / 2.0),
                self.vehicle.LENGTH,
                self.vehicle.WIDTH,
                color="#0066CC",
                alpha=0.9,
                zorder=6
            )
            ax.add_patch(car_box)

        # Formatting
        ax.set_xlim(-5.0, self.corridor_length + 5.0)
        ax.set_ylim(-half_w - 2.0, half_w + 2.0)
        ax.set_xlabel("Longitudinal Distance (meters)", fontsize=10, fontweight="bold")
        ax.set_ylabel("Lateral Position (meters)", fontsize=10, fontweight="bold")
        
        status_str = "SUCCESS (Goal Reached)" if self.goal_reached else ("COLLISION" if self.collision_occurred else "TIMEOUT")
        ax.set_title(
            f"Indian Road Simulation — Rollout Trajectory [{status_str}]\n"
            f"Steps: {self.current_step} | Total Reward: {sum(self.episode_rewards):.1f} | Final Speed: {self.vehicle.state.v*3.6:.1f} km/h",
            fontsize=11,
            fontweight="bold"
        )
        
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
        plt.tight_layout()

        # Save to specified path
        plt.savefig(save_path, bbox_inches="tight")
        plt.close()
        return save_path


def run_random_rollout():
    """Executes a sample rollout with random actions to verify the simulation core."""
    print("=" * 80)
    print("MISSION 1 — Running Pure-Python Simulation Core Rollout Test")
    print("=" * 80)
    
    env = IndianRoadEnv(corridor_length=100.0, road_width=7.0, difficulty=1)
    obs, info = env.reset(seed=42)
    
    print(f"Environment Initialized.")
    print(f"Observation Space: {env.observation_space.shape} | Action Space: {env.action_space.n}")
    print(f"Number of Obstacles Spawned: {len(env.obstacles)}")
    print("-" * 80)
    print(f"{'Step':<5} | {'Action Name':<16} | {'x (m)':<7} | {'y (m)':<7} | {'Speed (km/h)':<12} | {'Reward':<8} | {'Status'}")
    print("-" * 80)

    done = False
    step_count = 0
    total_reward = 0.0

    while not done and step_count < 60:
        # Sample random action
        action = env.action_space.sample()
        action_name = env.vehicle.ACTION_NAMES[action]
        
        obs, reward, terminated, truncated, step_info = env.step(action)
        total_reward += reward
        step_count += 1
        done = terminated or truncated

        status = "RUNNING"
        if step_info["collision"]:
            status = f"COLLISION ({step_info['collision_type']})"
        elif step_info["goal_reached"]:
            status = "GOAL REACHED"
        elif step_info["off_road"]:
            status = "OFF-ROAD"

        v_state = step_info["vehicle"]
        print(
            f"{step_count:<5} | {action_name:<16} | {v_state['x']:<7.2f} | {v_state['y']:<+7.2f} | "
            f"{v_state['speed_kmh']:<12.1f} | {reward:<+8.2f} | {status}"
        )

    print("-" * 80)
    print(f"Rollout Completed in {step_count} steps. Total Episode Reward: {total_reward:.2f}")
    
    # Save trajectory plot
    plot_file = "rollout_trajectory.png"
    env.plot_rollout(plot_file)
    print(f"Saved rollout visualization to: {plot_file}")
    print("=" * 80)


if __name__ == "__main__":
    run_random_rollout()
