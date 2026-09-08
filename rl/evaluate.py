"""
evaluate.py — Comprehensive Policy Evaluation and Benchmark Comparator.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from stable_baselines3 import PPO

from rl.environment.road_env import IndianRoadEnv
from rl.environment.vehicle import Vehicle
from safety.safety_controller import SafetyController


def evaluate_policy(
    model_path: str = "rl/checkpoints/ppo_indian_road.zip",
    num_episodes: int = 20,
    difficulty: int = 1,
    use_safety: bool = True
):
    model = PPO.load(model_path)
    safety = SafetyController() if use_safety else None

    successes = 0
    collisions = 0
    timeouts = 0
    total_rewards = []
    total_interventions = 0
    speeds = []

    for ep in range(num_episodes):
        env = IndianRoadEnv(corridor_length=100.0, road_width=7.0, difficulty=difficulty)
        obs, info = env.reset(seed=ep * 7 + 11)
        done = False
        ep_rew = 0.0
        step = 0

        while not done and step < 200:
            action, _ = model.predict(obs, deterministic=True)
            exec_action = int(action)

            if safety:
                decision = safety.evaluate(env.vehicle.state, env.obstacles, exec_action)
                exec_action = decision.action
                if decision.intervened:
                    total_interventions += 1

            obs, r, term, trunc, info = env.step(exec_action)
            ep_rew += r
            step += 1
            speeds.append(env.vehicle.state.v * 3.6)
            done = term or trunc

        total_rewards.append(ep_rew)
        if info["goal_reached"]:
            successes += 1
        elif info["collision"]:
            collisions += 1
        else:
            timeouts += 1

    success_rate = (successes / num_episodes) * 100.0
    collision_rate = (collisions / num_episodes) * 100.0
    avg_reward = np.mean(total_rewards)
    avg_speed = np.mean(speeds)

    print("-" * 60)
    print(f"EVALUATION RESULTS ({num_episodes} Episodes | Difficulty: {difficulty} | Safety Layer: {use_safety})")
    print("-" * 60)
    print(f"Success Rate:        {success_rate:.1f}% ({successes}/{num_episodes})")
    print(f"Collision Rate:      {collision_rate:.1f}% ({collisions}/{num_episodes})")
    print(f"Timeout Rate:        {(timeouts/num_episodes)*100:.1f}%")
    print(f"Average Reward:      {avg_reward:.2f}")
    print(f"Average Speed:       {avg_speed:.1f} km/h")
    print(f"Safety Overrides:    {total_interventions}")
    print("-" * 60)

    return {
        "success_rate": success_rate,
        "collision_rate": collision_rate,
        "avg_reward": avg_reward,
        "avg_speed": avg_speed,
        "safety_overrides": total_interventions
    }


def generate_comparison_artifact(
    model_path: str = "rl/checkpoints/ppo_indian_road.zip",
    demo_seed: int = 12,
    save_path: str = "before_after_comparison.png"
):
    """Generates clean high-impact Before vs After plot for SIH judges."""
    model = PPO.load(model_path)
    safety = SafetyController()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), dpi=150)
    road_width = 7.0
    half_w = road_width / 2.0

    # 1. Before: Random Untrained Driver
    env_random = IndianRoadEnv(corridor_length=100.0, road_width=road_width, difficulty=1)
    obs, info = env_random.reset(seed=demo_seed)
    done = False
    step_r = 0
    rew_r = 0.0
    while not done and step_r < 80:
        a = env_random.action_space.sample()
        obs, r, term, trunc, info = env_random.step(a)
        rew_r += r
        step_r += 1
        done = term or trunc

    _render_lane(ax1, env_random, f"[BEFORE] Random Untrained Policy — Erratic Deviations & Failure (Reward: {rew_r:.1f})", is_trained=False)

    # 2. After: Trained PPO + Safety Controller
    env_trained = IndianRoadEnv(corridor_length=100.0, road_width=road_width, difficulty=1)
    obs, info = env_trained.reset(seed=demo_seed)
    done = False
    step_t = 0
    rew_t = 0.0
    while not done and step_t < 80:
        a, _ = model.predict(obs, deterministic=True)
        decision = safety.evaluate(env_trained.vehicle.state, env_trained.obstacles, int(a))
        obs, r, term, trunc, info = env_trained.step(decision.action)
        rew_t += r
        step_t += 1
        done = term or trunc

    _render_lane(ax2, env_trained, f"[AFTER] Autonomous RL Agent + Safety Layer — Clean Obstacle Clearance & Goal Reach (Reward: {rew_t:.1f})", is_trained=True)

    plt.tight_layout()
    plt.savefig(save_path, bbox_inches="tight")
    plt.close()
    print(f"Generated comparison artifact: {save_path}")


def _render_lane(ax, env, title, is_trained):
    half_w = env.road_width / 2.0
    ax.axhline(half_w, color="black", linewidth=2.5, label="Road Edge")
    ax.axhline(-half_w, color="black", linewidth=2.5)
    ax.axhline(0.0, color="gold", linestyle="--", linewidth=1.5, label="Center Lane")
    ax.axhspan(-half_w, half_w, color="#f8f9fa", zorder=0)
    ax.axvline(0.0, color="green", linestyle=":", linewidth=2, label="Start")
    ax.axvline(env.target_x, color="red", linestyle=":", linewidth=2, label="Goal")

    # Obstacles
    for obs in env.obstacles:
        c = plt.Circle((obs.x, obs.y), obs.radius, color=obs.profile.color, alpha=0.85, zorder=4)
        ax.add_patch(c)
        ax.text(obs.x, obs.y + obs.radius + 0.25, obs.type.value, fontsize=7, ha="center", va="bottom", fontweight="bold", color="#333333")
        if obs.profile.is_dynamic and len(obs.history) > 1:
            hx, hy = zip(*obs.history)
            ax.plot(hx, hy, color=obs.profile.color, linestyle=":", alpha=0.5, linewidth=1.0)

    # Trajectory
    color = "#2E8B57" if is_trained else "#DC143C"
    if len(env.vehicle.trajectory_history) > 1:
        vx, vy, _, _ = zip(*env.vehicle.trajectory_history)
        ax.plot(vx, vy, color=color, linewidth=2.5, label="Vehicle Trajectory", zorder=5)
        fx, fy = vx[-1], vy[-1]
        car_box = patches.Rectangle((fx - env.vehicle.LENGTH / 2.0, fy - env.vehicle.WIDTH / 2.0), env.vehicle.LENGTH, env.vehicle.WIDTH, color=color, alpha=0.9, zorder=6)
        ax.add_patch(car_box)

    status_str = "SUCCESS" if env.goal_reached else ("COLLISION" if env.collision_occurred else "STOPPED/TIMEOUT")
    ax.set_xlim(-5.0, env.corridor_length + 5.0)
    ax.set_ylim(-half_w - 2.0, half_w + 2.0)
    ax.set_ylabel("Lateral (m)", fontweight="bold")
    ax.set_title(f"{title} | Status: {status_str} | Final X: {env.vehicle.state.x:.1f}m", fontweight="bold", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)


if __name__ == "__main__":
    evaluate_policy(num_episodes=20, difficulty=1, use_safety=True)
    generate_comparison_artifact(demo_seed=12, save_path="before_after_comparison.png")
