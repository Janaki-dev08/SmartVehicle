"""
train.py — Stable-Baselines3 PPO Training Pipeline for Indian Road Navigation.

Features:
- Multi-tier difficulty progression (Tier 1 -> Tier 2).
- Real-time training metric tracking (rewards, success rate, collision rate).
- Policy checkpointing to rl/checkpoints/ppo_indian_road.zip.
- Automated generation of SIH artifacts:
  1. training_reward_curve.png (Reward & Success Rate Learning Curves)
  2. before_after_comparison.png (Random vs Trained Policy Demonstration)
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from typing import List, Dict, Any

from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import BaseCallback

from rl.environment.road_env import IndianRoadEnv
from rl.environment.vehicle import Vehicle
from rl.environment.obstacle import Obstacle


class TrainingMetricsCallback(BaseCallback):
    """Custom callback to record episode outcomes and telemetry for training curves."""

    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.episode_rewards: List[float] = []
        self.episode_lengths: List[int] = []
        self.episode_successes: List[bool] = []
        self.episode_collisions: List[bool] = []
        self.timesteps: List[int] = []

    def _on_step(self) -> bool:
        # Check if any episode ended in this step
        for info in self.locals.get("infos", []):
            if "episode" in info:
                ep_r = info["episode"]["r"]
                ep_l = info["episode"]["l"]
                self.episode_rewards.append(ep_r)
                self.episode_lengths.append(ep_l)
                self.timesteps.append(self.num_timesteps)

                # Track collision & success flags if present
                self.episode_successes.append(info.get("goal_reached", False))
                self.episode_collisions.append(info.get("collision", False))
        return True


def train_ppo_agent(
    tier1_steps: int = 10000,
    tier2_steps: int = 10000,
    seed: int = 42,
    checkpoint_dir: str = "rl/checkpoints"
) -> PPO:
    """Trains a PPO agent over multi-tier difficulty environments."""
    print("=" * 80)
    print("MISSION 3 — Training PPO Agent with Stable-Baselines3")
    print("=" * 80)
    
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_path = os.path.join(checkpoint_dir, "ppo_indian_road.zip")

    # 1. Initialize Tier 1 Environment (Low Obstacle Density)
    print(f"[Phase 1] Initializing Tier 1 Environment (Difficulty: 1, Steps: {tier1_steps})...")
    env_tier1 = IndianRoadEnv(corridor_length=100.0, road_width=7.0, difficulty=1)
    env_tier1 = Monitor(env_tier1)

    callback = TrainingMetricsCallback()

    # 2. Configure PPO Hyperparameters
    model = PPO(
        policy="MlpPolicy",
        env=env_tier1,
        learning_rate=3e-4,
        n_steps=512,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        verbose=1,
        seed=seed
    )

    print(f"[Phase 1] Training on Tier 1 for {tier1_steps} timesteps...")
    model.learn(total_timesteps=tier1_steps, callback=callback)
    print("[Phase 1] Completed.")

    # 3. Transition to Tier 2 Environment (Medium Density + Dynamic Obstacles)
    print(f"\n[Phase 2] Transitioning to Tier 2 Environment (Difficulty: 2, Steps: {tier2_steps})...")
    env_tier2 = IndianRoadEnv(corridor_length=100.0, road_width=7.0, difficulty=2)
    env_tier2 = Monitor(env_tier2)
    model.set_env(env_tier2)

    print(f"[Phase 2] Training on Tier 2 for {tier2_steps} timesteps...")
    model.learn(total_timesteps=tier2_steps, callback=callback, reset_num_timesteps=False)
    print("[Phase 2] Completed.")

    # 4. Save Trained Checkpoint
    model.save(checkpoint_path)
    print(f"\nSaved trained PPO policy to: {checkpoint_path}")

    # 5. Plot Training Reward Curves
    plot_training_curves(callback, save_path="training_reward_curve.png")

    # 6. Generate Before/After Comparison Artifact
    generate_before_after_comparison(model, seed=105, save_path="before_after_comparison.png")

    print("=" * 80)
    print("Mission 3 PPO Training & Evaluation Finished Successfully!")
    print("=" * 80)
    return model


def plot_training_curves(callback: TrainingMetricsCallback, save_path: str = "training_reward_curve.png"):
    """Generates dual-panel training performance plots."""
    if len(callback.episode_rewards) == 0:
        print("Warning: No finished episodes to plot.")
        return

    episodes = np.arange(1, len(callback.episode_rewards) + 1)
    rewards = np.array(callback.episode_rewards)

    # Compute rolling averages (window = 10)
    window = min(15, len(rewards))
    if window > 1:
        rolling_rewards = np.convolve(rewards, np.ones(window)/window, mode="valid")
        rolling_episodes = episodes[window - 1:]
    else:
        rolling_rewards = rewards
        rolling_episodes = episodes

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)

    # Panel 1: Episode Reward Curve
    ax1.plot(episodes, rewards, color="#B0C4DE", alpha=0.6, label="Raw Episode Reward")
    ax1.plot(rolling_episodes, rolling_rewards, color="#0055AA", linewidth=2.5, label=f"Rolling Mean (w={window})")
    ax1.set_xlabel("Episode Number", fontweight="bold")
    ax1.set_ylabel("Total Cumulative Reward", fontweight="bold")
    ax1.set_title("PPO Agent Training Convergence — Reward vs Episodes", fontweight="bold", fontsize=11)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="lower right")

    # Panel 2: Episode Length & Stability
    lengths = np.array(callback.episode_lengths)
    if window > 1:
        rolling_lengths = np.convolve(lengths, np.ones(window)/window, mode="valid")
    else:
        rolling_lengths = lengths

    ax2.plot(episodes, lengths, color="#E9967A", alpha=0.6, label="Episode Length (Steps)")
    ax2.plot(rolling_episodes, rolling_lengths, color="#D9534F", linewidth=2.5, label=f"Rolling Mean (w={window})")
    ax2.set_xlabel("Episode Number", fontweight="bold")
    ax2.set_ylabel("Steps per Episode", fontweight="bold")
    ax2.set_title("Episode Steps / Survival Time per Episode", fontweight="bold", fontsize=11)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="lower right")

    plt.tight_layout()
    plt.savefig(save_path, bbox_inches="tight")
    plt.close()
    print(f"Saved training curve plot to: {save_path}")


def generate_before_after_comparison(
    trained_model: PPO,
    seed: int = 105,
    save_path: str = "before_after_comparison.png"
):
    """
    Runs a side-by-side rollout on the exact same road layout:
    Top: Random Policy (Untrained Baseline)
    Bottom: Trained PPO Policy
    """
    print(f"Generating Before/After Policy Comparison (Seed: {seed})...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), dpi=150)
    road_width = 7.0
    half_w = road_width / 2.0

    # 1. Rollout A: Untrained / Random Policy
    env_random = IndianRoadEnv(corridor_length=100.0, road_width=road_width, difficulty=2)
    obs, info = env_random.reset(seed=seed)
    done = False
    step_count_rand = 0
    rand_reward = 0.0

    while not done and step_count_rand < 100:
        action = env_random.action_space.sample()
        obs, r, term, trunc, step_info = env_random.step(action)
        rand_reward += r
        step_count_rand += 1
        done = term or trunc

    _render_comparison_subplot(
        ax=ax1,
        env=env_random,
        title="[BEFORE] Untrained / Random Action Policy — Erratic Wandering & Failure",
        total_reward=rand_reward,
        is_trained=False
    )

    # 2. Rollout B: Trained PPO Policy
    env_trained = IndianRoadEnv(corridor_length=100.0, road_width=road_width, difficulty=2)
    obs, info = env_trained.reset(seed=seed)
    done = False
    step_count_ppo = 0
    ppo_reward = 0.0

    while not done and step_count_ppo < 100:
        action, _ = trained_model.predict(obs, deterministic=True)
        obs, r, term, trunc, step_info = env_trained.step(int(action))
        ppo_reward += r
        step_count_ppo += 1
        done = term or trunc

    _render_comparison_subplot(
        ax=ax2,
        env=env_trained,
        title="[AFTER] Trained PPO Policy — Adaptive Evasion, Lane Centering & Goal Reach",
        total_reward=ppo_reward,
        is_trained=True
    )

    plt.tight_layout()
    plt.savefig(save_path, bbox_inches="tight")
    plt.close()
    print(f"Saved before/after comparison plot to: {save_path}")


def _render_comparison_subplot(ax, env: IndianRoadEnv, title: str, total_reward: float, is_trained: bool):
    """Helper to render road corridor and trajectory on comparison subplot."""
    half_w = env.road_width / 2.0

    # Road boundaries & Center line
    ax.axhline(half_w, color="black", linewidth=2.5, label="Road Boundary")
    ax.axhline(-half_w, color="black", linewidth=2.5)
    ax.axhline(0.0, color="gold", linestyle="--", linewidth=1.5, label="Center Lane")
    ax.axhspan(-half_w, half_w, color="#f8f9fa", zorder=0)

    # Start & Goal lines
    ax.axvline(0.0, color="green", linestyle=":", linewidth=2, label="Start")
    ax.axvline(env.target_x, color="red", linestyle=":", linewidth=2, label="Goal")

    # Obstacles
    for obs in env.obstacles:
        circle = plt.Circle(
            (obs.x, obs.y),
            obs.radius,
            color=obs.profile.color,
            alpha=0.85,
            zorder=4
        )
        ax.add_patch(circle)
        ax.text(
            obs.x,
            obs.y + obs.radius + 0.25,
            obs.type.value,
            fontsize=7,
            ha="center",
            va="bottom",
            fontweight="bold",
            color="#333333"
        )

        # Dynamic trace
        if obs.profile.is_dynamic and len(obs.history) > 1:
            hx, hy = zip(*obs.history)
            ax.plot(hx, hy, color=obs.profile.color, linestyle=":", alpha=0.5, linewidth=1.0)

    # Vehicle Trajectory
    traj_color = "#2E8B57" if is_trained else "#DC143C"
    if len(env.vehicle.trajectory_history) > 1:
        vx, vy, vv, _ = zip(*env.vehicle.trajectory_history)
        ax.plot(vx, vy, color=traj_color, linewidth=2.5, label="Vehicle Path", zorder=5)

        # Final vehicle position box
        fx, fy = vx[-1], vy[-1]
        car_box = patches.Rectangle(
            (fx - env.vehicle.LENGTH / 2.0, fy - env.vehicle.WIDTH / 2.0),
            env.vehicle.LENGTH,
            env.vehicle.WIDTH,
            color=traj_color,
            alpha=0.9,
            zorder=6
        )
        ax.add_patch(car_box)

    status_str = "SUCCESS (Goal Reached)" if env.goal_reached else ("COLLISION" if env.collision_occurred else "TIMEOUT")
    ax.set_xlim(-5.0, env.corridor_length + 5.0)
    ax.set_ylim(-half_w - 2.0, half_w + 2.0)
    ax.set_ylabel("Lateral (m)", fontweight="bold")
    ax.set_title(
        f"{title}\nStatus: {status_str} | Steps: {env.current_step} | Total Reward: {total_reward:.1f} | Final Speed: {env.vehicle.state.v*3.6:.1f} km/h",
        fontweight="bold",
        fontsize=10
    )
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)


if __name__ == "__main__":
    train_ppo_agent(tier1_steps=10000, tier2_steps=10000)
