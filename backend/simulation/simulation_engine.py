"""
Master Autonomous Driving Simulation Engine.
Orchestrates the complete continuous feedback loop:
PERCEIVE -> TRACK -> PREDICT -> MAP -> PLAN (A*) -> ASSESS RISK (TTC) -> REPLAN -> CONTROL -> ACTUATE
"""

import time
import asyncio
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from config import config

from backend.simulation.carla_connection import CarlaConnectionManager
from backend.simulation.vehicle_setup import VehicleSetup
from backend.simulation.scenario_manager import ScenarioManager
from backend.perception.camera import CameraSensor
from backend.perception.object_detection import ObjectDetector
from backend.perception.object_tracking import ObjectTracker
from backend.perception.obstacle_detection import OccupancyGridBuilder, ObstaclePredictor
from backend.planning.path_planner import PathPlanner
from backend.planning.replanning import ReplanningEngine
from backend.collision.risk_estimation import RiskEstimator, RiskLevel
from backend.collision.collision_avoidance import CollisionAvoidanceSupervisor
from backend.control.vehicle_controller import VehicleController
from backend.metrics.metrics_collector import MetricsCollector


class SimulationEngine:
    """
    Core Autonomous Driving Loop Orchestrator.
    """

    def __init__(self):
        # 1. Simulator & Setup
        self.carla_conn = CarlaConnectionManager()
        self.camera_sensor = CameraSensor(
            width=config.sensor.camera_width,
            height=config.sensor.camera_height,
            fov=config.sensor.camera_fov
        )
        self.vehicle_setup = VehicleSetup(self.carla_conn, self.camera_sensor)
        self.scenario_manager = ScenarioManager()

        # 2. Perception & Tracking
        self.detector = ObjectDetector()
        self.tracker = ObjectTracker()
        self.predictor = ObstaclePredictor(horizon_seconds=config.collision.prediction_horizon)
        self.grid_builder = OccupancyGridBuilder(
            resolution=config.planning.grid_resolution,
            width_meters=config.planning.grid_width * config.planning.grid_resolution,
            length_meters=config.planning.grid_length * config.planning.grid_resolution
        )

        # 3. Planning & Replanning
        self.planner = PathPlanner()
        self.replanner = ReplanningEngine(check_interval=config.planning.replan_interval)

        # 4. Risk & Safety
        self.risk_estimator = RiskEstimator()
        self.safety_supervisor = CollisionAvoidanceSupervisor()

        # 5. Vehicle Control
        self.controller = VehicleController()

        # 6. Metrics & Logging
        self.metrics = MetricsCollector()

        # Kinematic State (for Standalone Engine & CARLA Synchronizer)
        self.ego_x = 0.0
        self.ego_y = 0.0
        self.ego_z = 0.0
        self.ego_heading = 0.0 # radians
        self.ego_speed_kmh = 0.0
        self.ego_accel_ms2 = 0.0
        
        # Simulation lifecycle flags
        self.is_running = False
        self.simulation_step_count = 0
        self.destination_x = 120.0
        self.destination_y = 0.0
        self.latest_telemetry: Dict[str, Any] = {}
        self.simulation_speed_multiplier = 1.0

        # Driver mode: NONE | META | CARLA
        self.active_driver: str = "META"

        # Try connecting to CARLA on startup
        self.try_carla_connect()
        
        # Initialize default scenario
        self.load_scenario("scenario_02")

    def try_carla_connect(self) -> bool:
        """Attempts CARLA connection."""
        success = self.carla_conn.connect()
        if success:
            self.vehicle_setup.spawn_ego_vehicle()
        return success

    def load_scenario(self, scenario_id: str) -> bool:
        """Loads and initializes a scenario."""
        scenario = self.scenario_manager.load_scenario(scenario_id)
        if scenario:
            self.destination_x = scenario.destination.get("x", 120.0)
            self.destination_y = scenario.destination.get("y", 0.0)
            self.reset_simulation()
            return True
        return False

    def set_driver(self, driver_type: str) -> bool:
        """Sets the active driver mode: NONE | META | CARLA."""
        valid = {"NONE", "META", "CARLA"}
        if driver_type.upper() not in valid:
            return False
        self.active_driver = driver_type.upper()
        print(f"[SimulationEngine] Driver set to: {self.active_driver}")
        return True

    def start_simulation(self):
        """Starts the autonomous simulation loop."""
        self.is_running = True
        print("[SimulationEngine] Autonomous driving loop started.")

    def stop_simulation(self):
        """Pauses the simulation loop."""
        self.is_running = False
        print("[SimulationEngine] Autonomous driving loop paused.")

    def reset_simulation(self):
        """Resets vehicle, planner, controller, and scenario actors to initial state."""
        self.is_running = False
        self.ego_x = 0.0
        self.ego_y = 0.0
        self.ego_z = 0.0
        self.ego_heading = 0.0
        self.ego_speed_kmh = 0.0
        self.ego_accel_ms2 = 0.0
        self.simulation_step_count = 0

        self.controller.reset()
        self.tracker = ObjectTracker()
        self.metrics.reset()

        if self.scenario_manager.current_scenario:
            self.scenario_manager.load_scenario(self.scenario_manager.current_scenario.id)

        # Initial baseline planning
        init_costmap = self.grid_builder.build_grid([])
        self.planner.plan_local_trajectory((0, 0, 0), init_costmap)
        
        print("[SimulationEngine] Simulation reset.")

    def step(self, dt: float = 0.05) -> Dict[str, Any]:
        """
        Executes one full autonomous driving iteration at 20 Hz.
        """
        t_cycle_start = time.perf_counter()
        self.simulation_step_count += 1

        # 1. Update Scenario Actors
        active_scenario_actors = self.scenario_manager.update_actors(
            ego_x=self.ego_x,
            ego_speed=self.ego_speed_kmh / 3.6,
            dt=dt
        )

        # 2. CARLA Hardware Tick / Sensor Sync
        if self.carla_conn.is_connected:
            self.carla_conn.tick()
            carla_telem = self.vehicle_setup.get_telemetry()
            self.ego_speed_kmh = carla_telem["speed_kmh"]
            self.ego_accel_ms2 = carla_telem["accel_ms2"]

        # 3. Perception: YOLO Object Detection
        rgb_frame = self.camera_sensor.get_rgb_frame()
        depth_map = self.camera_sensor.get_depth_frame()
        raw_detections = self.detector.detect(
            rgb_frame=rgb_frame,
            depth_map=depth_map,
            ground_truth_actors=active_scenario_actors
        )

        # 4. Multi-Frame Object Tracking
        tracked_objects = self.tracker.update(raw_detections)

        # 5. Motion Prediction
        predicted_objects = self.predictor.predict_trajectories(tracked_objects)

        # 6. Occupancy Grid Construction
        road_width = self.scenario_manager.current_scenario.road_width if self.scenario_manager.current_scenario else 8.0
        costmap = self.grid_builder.build_grid(
            obstacles=predicted_objects,
            road_half_width=road_width / 2.0,
            safety_margin_m=config.planning.obstacle_safety_margin
        )

        # 7. Collision Risk Assessment (TTC)
        risk_report = self.risk_estimator.calculate_risk(
            ego_speed=self.ego_speed_kmh / 3.6,
            tracked_obstacles=predicted_objects
        )

        # 8. Supervisory Collision Avoidance Action
        action_name, target_speed_kmh, brake_override = self.safety_supervisor.evaluate_action(
            risk_report=risk_report,
            current_speed_kmh=self.ego_speed_kmh
        )

        # 9. Dynamic Replanning Audit
        replan_needed, replan_reason = self.replanner.check_replan_needed(
            current_local_path=self.planner.current_local_path,
            tracked_obstacles=predicted_objects,
            safety_clearance=config.planning.obstacle_safety_margin
        )

        # 10. Adaptive A* Planning Execution
        plan_latency_ms = 0.0
        replan_occurred = False
        if replan_needed or len(self.planner.current_local_path) < 3:
            prev_len = len(self.planner.current_local_path)
            local_path, global_path, success, plan_latency_ms = self.planner.plan_local_trajectory(
                vehicle_pos=(self.ego_x, self.ego_y, self.ego_heading),
                costmap=costmap,
                lookahead_distance=min(40.0, max(15.0, self.destination_x - self.ego_x))
            )
            replan_occurred = True
            self.replanner.record_replan_event(replan_reason, plan_latency_ms, prev_len, len(local_path))

        # 11. Vehicle Control (Pure Pursuit + Longitudinal PID)
        lookahead_point = self.planner.get_lookahead_target(current_speed=self.ego_speed_kmh / 3.6)
        
        control_cmd = self.controller.control_step(
            current_speed_kmh=self.ego_speed_kmh,
            target_speed_kmh=target_speed_kmh if self.is_running else 0.0,
            target_local_point=lookahead_point,
            emergency_brake_demand=brake_override if self.is_running else 1.0,
            dt=dt
        )

        # 12. Actuate Vehicle (CARLA or Kinematic Update)
        if self.is_running:
            if self.carla_conn.is_connected:
                self.vehicle_setup.apply_control(
                    steer=control_cmd["steer"],
                    throttle=control_cmd["throttle"],
                    brake=control_cmd["brake"]
                )
            else:
                # High-Fidelity Standalone Kinematic Vehicle Model
                curr_ms = self.ego_speed_kmh / 3.6
                
                # Longitudinal acceleration
                if control_cmd["brake"] > 0.1:
                    accel = -config.vehicle.emergency_braking * control_cmd["brake"]
                else:
                    accel = config.vehicle.max_acceleration * control_cmd["throttle"]
                
                new_speed_ms = max(0.0, min(config.vehicle.max_speed_kmh / 3.6, curr_ms + accel * dt))
                self.ego_speed_kmh = round(new_speed_ms * 3.6, 1)
                self.ego_accel_ms2 = round(accel, 2)

                # Lateral kinematics: Bicycle Model
                steer_rad = control_cmd["steer"] * config.vehicle.max_steer_angle
                yaw_rate = (new_speed_ms / config.vehicle.wheelbase) * np.tan(steer_rad)
                self.ego_heading += yaw_rate * dt
                
                # Displacement
                dx = new_speed_ms * np.cos(self.ego_heading) * dt
                dy = new_speed_ms * np.sin(self.ego_heading) * dt
                self.ego_x += dx
                self.ego_y += dy
                self.metrics.total_distance_m += float(np.sqrt(dx**2 + dy**2))

        # Check Destination Reach
        dist_to_dest = np.sqrt((self.destination_x - self.ego_x)**2 + (self.destination_y - self.ego_y)**2)
        if dist_to_dest < 3.0:
            self.metrics.is_completed = True
            action_name = "DESTINATION_REACHED"
            self.is_running = False

        # 13. Logging & Metrics
        self.metrics.log_step(
            vehicle_state={"x": self.ego_x, "y": self.ego_y, "speed_kmh": self.ego_speed_kmh},
            control_cmd=control_cmd,
            risk_report=risk_report,
            detections=tracked_objects,
            path_length=len(self.planner.current_local_path),
            planning_latency_ms=plan_latency_ms,
            replan_occurred=replan_occurred,
            replan_reason=replan_reason
        )

        # 14. Synthesize Full Telemetry Payload
        telemetry = {
            "timestamp": round(time.time(), 3),
            "step": self.simulation_step_count,
            "running": self.is_running,
            "mode": "AUTONOMOUS",
            "driver": self.active_driver,
            "human_control": "DISABLED",
            "vehicle": {
                "speed_kmh": round(self.ego_speed_kmh, 1),
                "speed_ms": round(self.ego_speed_kmh / 3.6, 2),
                "position": {"x": round(self.ego_x, 2), "y": round(self.ego_y, 2), "z": round(self.ego_z, 2)},
                "heading_deg": round(float(np.rad2deg(self.ego_heading)), 1),
                "heading_rad": round(self.ego_heading, 3),
                "acceleration_ms2": round(self.ego_accel_ms2, 2),
                "steering_angle": control_cmd["steer"],
                "throttle": control_cmd["throttle"],
                "brake": control_cmd["brake"],
                "destination_distance_m": round(dist_to_dest, 1)
            },
            "carla": self.carla_conn.get_status(),
            "scenario": self.scenario_manager.current_scenario.to_dict() if self.scenario_manager.current_scenario else None,
            "risk": risk_report,
            "action": action_name,
            "planner": {
                "algorithm": "Adaptive A*",
                "total_replans": self.replanner.replan_count,
                "latest_planning_time_ms": round(plan_latency_ms, 2),
                "local_path": self.planner.current_local_path,
                "global_path": self.planner.current_global_path,
                "lookahead_target": lookahead_point
            },
            "perception": {
                "detected_objects_count": len(tracked_objects),
                "objects": predicted_objects
            },
            "metrics": self.metrics.get_summary_metrics(),
            "benchmark": self.metrics.get_benchmark_comparison(),
            "latest_replans": self.replanner.replan_history[-5:],
            "road_width": road_width
        }

        self.latest_telemetry = telemetry
        return telemetry
