"""
tests/test_safety_scenario.py — Verification Scenario for Mission 2: Safety Layer Override.

Demonstrates deterministic collision prevention:
- Obstacle placed directly ahead in ego lane at x=35.0m.
- Scripted agent aggressively commands ACTION_ACCELERATE towards the hazard.
- SafetyController detects safety envelope violation and forces EMERGENCY_STOP.
- Vehicle halts safely before the obstacle with zero collisions.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

from rl.environment.vehicle import Vehicle, VehicleState
from rl.environment.obstacle import Obstacle, ObstacleType
from safety.safety_controller import SafetyController, SafetyDecision


def run_scripted_safety_scenario(save_plot: bool = True) -> dict:
    print("=" * 100)
    print("MISSION 2 — Scripted 'Obstacle Directly Ahead' Safety Override Demonstration")
    print("=" * 100)

    # 1. Initialize Vehicle and Safety Controller
    vehicle = Vehicle(x=0.0, y=0.0, v=10.0, theta=0.0) # Starting at 36 km/h
    safety_controller = SafetyController(
        reaction_time=0.35,
        emergency_decel=6.0,
        min_clearance_gap=3.0,
        ttc_emergency_threshold=1.5
    )

    # 2. Place a stationary obstacle directly in the vehicle's path
    obstacle_x = 35.0
    obstacle_y = 0.0
    hazard = Obstacle(
        obstacle_id=101,
        obstacle_type=ObstacleType.PARKED_VEHICLE,
        x=obstacle_x,
        y=obstacle_y,
        vx=0.0,
        vy=0.0,
        road_width=7.0
    )
    obstacles = [hazard]

    print(f"Scenario Setup:")
    print(f"  - Ego Vehicle Initial State: x={vehicle.state.x:.1f}m, y={vehicle.state.y:.1f}m, speed={vehicle.state.v*3.6:.1f} km/h")
    print(f"  - Target Hazard: {hazard.type.value.upper()} directly ahead at x={hazard.x:.1f}m, y={hazard.y:.1f}m (radius: {hazard.radius:.1f}m)")
    print(f"  - Scripted Policy: Blindly proposes ACTION_ACCELERATE every step.")
    print("-" * 100)
    print(f"{'Step':<5} | {'Ego X':<7} | {'Speed (km/h)':<13} | {'Obs Dist':<9} | {'Proposed':<12} | {'Executed':<15} | {'Override':<9} | {'Reason'}")
    print("-" * 100)

    dt = 0.1
    history = []
    override_count = 0
    collision = False

    for step in range(1, 51):
        # Scripted unsafe action: always accelerate
        proposed_action = Vehicle.ACTION_ACCELERATE

        # Safety controller evaluation
        decision: SafetyDecision = safety_controller.evaluate(
            vehicle_state=vehicle.state,
            obstacles=obstacles,
            proposed_action=proposed_action
        )

        # Apply safe action to vehicle
        vehicle.apply_action(decision.action, dt=dt)
        curr_dist = hazard.distance_to(vehicle.state.x, vehicle.state.y)

        # Collision check
        if curr_dist < (vehicle.LENGTH / 2.0 + hazard.radius):
            collision = True

        if decision.intervened:
            override_count += 1

        history.append({
            "step": step,
            "ego_x": vehicle.state.x,
            "ego_y": vehicle.state.y,
            "ego_v": vehicle.state.v,
            "ego_speed_kmh": vehicle.state.v * 3.6,
            "dist_to_obs": curr_dist,
            "proposed_action": Vehicle.ACTION_NAMES[proposed_action],
            "executed_action": Vehicle.ACTION_NAMES[decision.action],
            "intervened": decision.intervened,
            "reason": decision.reason
        })

        status_str = "YES" if decision.intervened else "NO"
        reason_short = decision.reason[:40] + "..." if len(decision.reason) > 40 else decision.reason
        print(
            f"{step:<5} | {vehicle.state.x:<7.2f} | {vehicle.state.v*3.6:<13.1f} | {curr_dist:<9.2f} | "
            f"{Vehicle.ACTION_NAMES[proposed_action]:<12} | {Vehicle.ACTION_NAMES[decision.action]:<15} | "
            f"{status_str:<9} | {reason_short}"
        )

        # Stop simulation when vehicle comes to a complete halt
        if vehicle.state.v <= 0.01 and step > 10:
            print("-" * 100)
            print(f"Vehicle brought to a complete safe stop at Step {step}.")
            break

    final_dist = hazard.distance_to(vehicle.state.x, vehicle.state.y)
    final_gap = final_dist - (vehicle.LENGTH / 2.0 + hazard.radius)
    print("-" * 100)
    print(f"Results Summary:")
    print(f"  - Total Simulation Steps: {len(history)}")
    print(f"  - Total Safety Layer Overrides: {override_count}")
    print(f"  - Collision Occurred: {collision} (0 collisions)")
    print(f"  - Final Vehicle Position: x={vehicle.state.x:.2f}m (Obstacle at x={hazard.x:.2f}m)")
    print(f"  - Final Stopping Clearance Margin: {final_gap:.2f} meters")
    print("=" * 100)

    if save_plot:
        plot_path = "safety_override_rollout.png"
        generate_safety_plot(history, hazard, vehicle, plot_path)
        print(f"Saved safety override demonstration plot to: {plot_path}")

    return {
        "history": history,
        "override_count": override_count,
        "collision": collision,
        "final_gap": final_gap
    }


def generate_safety_plot(history: list, hazard: Obstacle, vehicle: Vehicle, save_path: str):
    """Plots the trajectory, velocity profile, and safety intervention zone."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), dpi=150, gridspec_kw={"height_ratios": [1.5, 1]})

    # --- Top Subplot: Road Corridor & Obstacle ---
    road_width = 7.0
    half_w = road_width / 2.0
    ax1.axhline(half_w, color="black", linewidth=2.5, label="Road Boundary")
    ax1.axhline(-half_w, color="black", linewidth=2.5)
    ax1.axhline(0.0, color="gold", linestyle="--", linewidth=1.5, label="Center Lane")
    ax1.axhspan(-half_w, half_w, color="#f8f9fa", zorder=0)

    # Obstacle
    obs_circle = plt.Circle((hazard.x, hazard.y), hazard.radius, color="#DC143C", alpha=0.85, zorder=5, label=f"Hazard: {hazard.type.value}")
    ax1.add_patch(obs_circle)
    ax1.text(hazard.x, hazard.y + hazard.radius + 0.3, f"{hazard.type.value}\n(x={hazard.x}m)", fontsize=8, ha="center", va="bottom", fontweight="bold", color="#8B0000")

    # Trajectory points colored by safety status
    steps_x = [h["ego_x"] for h in history]
    steps_y = [h["ego_y"] for h in history]
    
    # Safe segment (Proposed == Executed)
    safe_x = [h["ego_x"] for h in history if not h["intervened"]]
    safe_y = [h["ego_y"] for h in history if not h["intervened"]]
    if safe_x:
        ax1.plot(safe_x, safe_y, "o-", color="#2E8B57", linewidth=2.5, markersize=5, label="Normal Operation (AI Proposes)")

    # Override segment (Safety Intervened)
    override_x = [h["ego_x"] for h in history if h["intervened"]]
    override_y = [h["ego_y"] for h in history if h["intervened"]]
    if override_x:
        ax1.plot(override_x, override_y, "s-", color="#FF4500", linewidth=3.0, markersize=6, label="Safety Override (Forced Brake)")

    # Final vehicle box
    final_x = history[-1]["ego_x"]
    final_y = history[-1]["ego_y"]
    car_box = patches.Rectangle(
        (final_x - vehicle.LENGTH / 2.0, final_y - vehicle.WIDTH / 2.0),
        vehicle.LENGTH,
        vehicle.WIDTH,
        color="#0066CC",
        alpha=0.9,
        zorder=6,
        label=f"Halted Vehicle (x={final_x:.1f}m)"
    )
    ax1.add_patch(car_box)

    ax1.set_xlim(-2.0, 45.0)
    ax1.set_ylim(-half_w - 1.5, half_w + 1.5)
    ax1.set_ylabel("Lateral Position (m)", fontweight="bold")
    ax1.set_title("Mission 2: Deterministic Safety Layer Override Demonstration (Corridor View)", fontweight="bold", fontsize=11)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper left", fontsize=8, framealpha=0.9)

    # --- Bottom Subplot: Speed Profile & Intervention Point ---
    steps = [h["step"] for h in history]
    speeds = [h["ego_speed_kmh"] for h in history]
    interventions = [h["intervened"] for h in history]

    ax2.plot(steps, speeds, color="#0066CC", linewidth=2.5, label="Vehicle Speed (km/h)")
    
    # Highlight intervention steps
    override_steps = [s for s, i in zip(steps, interventions) if i]
    override_speeds = [sp for sp, i in zip(speeds, interventions) if i]
    if override_steps:
        ax2.scatter(override_steps, override_speeds, color="#FF4500", s=60, zorder=5, label="Emergency Brake Interventions")

    ax2.set_xlabel("Time Step (0.1s / step)", fontweight="bold")
    ax2.set_ylabel("Speed (km/h)", fontweight="bold")
    ax2.set_title("Vehicle Velocity Profile Showing Automatic Emergency Deceleration to Full Stop", fontweight="bold", fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="upper right", fontsize=8, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(save_path, bbox_inches="tight")
    plt.close()


def test_safety_override_scenario():
    """Pytest wrapper to verify zero collisions and positive override count."""
    results = run_scripted_safety_scenario(save_plot=False)
    assert not results["collision"], "Collision must not occur when safety layer is active"
    assert results["override_count"] > 0, "Safety layer must intervene when heading towards obstacle"
    assert results["final_gap"] >= 2.0, "Safety layer must maintain physical clearance margin"


if __name__ == "__main__":
    run_scripted_safety_scenario(save_plot=True)
