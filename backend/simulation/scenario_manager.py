"""
Scenario Manager for Indian Road Autonomous Driving Challenges.
Manages 10 reproducible benchmark scenarios with realistic traffic actors,
motion profiles, and trigger conditions.
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import config


class Scenario:
    """Represents an autonomous vehicle test scenario."""

    def __init__(
        self,
        scenario_id: str,
        name: str,
        category: str,
        difficulty: str,
        description: str,
        road_width: float,
        actors: List[Dict[str, Any]],
        start_position: Dict[str, float],
        destination: Dict[str, float]
    ):
        self.id = scenario_id
        self.name = name
        self.category = category
        self.difficulty = difficulty
        self.description = description
        self.road_width = road_width
        self.actors = actors # List of actor specifications
        self.start_position = start_position
        self.destination = destination

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "difficulty": self.difficulty,
            "description": self.description,
            "road_width": self.road_width,
            "actor_count": len(self.actors),
            "actors": self.actors,
            "start_position": self.start_position,
            "destination": self.destination
        }


class ScenarioManager:
    """
    Loads, configures, and dynamically updates scenario actors and trajectories.
    """

    def __init__(self, scenarios_dir: Optional[Path] = None):
        self.scenarios_dir = scenarios_dir or config.scenarios_dir
        self.scenarios: Dict[str, Scenario] = {}
        self.current_scenario: Optional[Scenario] = None
        self.active_actors: List[Dict[str, Any]] = []
        self.scenario_start_time: float = 0.0
        
        # Load predefined scenarios
        self._load_all_scenarios()

    def _load_all_scenarios(self):
        """Initializes all 10 Indian road scenarios."""
        # Scenario definitions
        scenarios_def = [
            {
                "id": "scenario_01",
                "name": "Unmarked Narrow Road",
                "category": "Rural / Semi-Urban",
                "difficulty": "Easy",
                "description": "Narrow two-way rural Indian road without lane markings. Requires centered path keeping and road boundary adherence.",
                "road_width": 6.5,
                "start_position": {"x": 0.0, "y": 0.0, "heading": 0.0},
                "destination": {"x": 120.0, "y": 0.0},
                "actors": [
                    {"id": 1, "type": "debris", "rel_x": 45.0, "rel_y": 1.2, "rel_z": 0.0, "speed": 0.0, "heading": 0.0, "behavior": "static"},
                    {"id": 2, "type": "bicycle", "rel_x": 75.0, "rel_y": 2.2, "rel_z": 0.0, "speed": 3.0, "heading": 0.0, "behavior": "forward_slow"}
                ]
            },
            {
                "id": "scenario_02",
                "name": "Sudden Motorcycle Cut-In",
                "category": "Urban Commute",
                "difficulty": "Medium",
                "description": "A two-wheeler abruptly cuts across the ego vehicle's path from the left shoulder, testing fast TTC detection and rapid lateral replanning.",
                "road_width": 8.0,
                "start_position": {"x": 0.0, "y": 0.0, "heading": 0.0},
                "destination": {"x": 130.0, "y": 0.0},
                "actors": [
                    {"id": 1, "type": "motorcycle", "rel_x": 24.0, "rel_y": -3.2, "rel_z": 0.0, "speed": 6.5, "heading": 35.0, "behavior": "cut_in", "target_y": 1.0, "trigger_dist": 28.0}
                ]
            },
            {
                "id": "scenario_03",
                "name": "Jaywalking Pedestrian Crossing",
                "category": "Urban Pedestrian",
                "difficulty": "Hard",
                "description": "Pedestrian jaywalks unpredictably across the road between stopped traffic without a pedestrian crossing. Tests emergency braking and pedestrian safety buffers.",
                "road_width": 9.0,
                "start_position": {"x": 0.0, "y": 0.0, "heading": 0.0},
                "destination": {"x": 110.0, "y": 0.0},
                "actors": [
                    {"id": 1, "type": "pedestrian", "rel_x": 22.0, "rel_y": 4.0, "rel_z": 0.0, "speed": 1.4, "heading": -90.0, "behavior": "cross_road", "target_y": -4.0, "trigger_dist": 26.0}
                ]
            },
            {
                "id": "scenario_04",
                "name": "Parked Vehicle Road Blockage",
                "category": "Urban Congestion",
                "difficulty": "Medium",
                "description": "A stationary delivery car blocks 60% of the primary lane. The autonomous vehicle must detect the blockage, verify clearance, and execute an adaptive overtake maneuver.",
                "road_width": 8.5,
                "start_position": {"x": 0.0, "y": 0.0, "heading": 0.0},
                "destination": {"x": 140.0, "y": 0.0},
                "actors": [
                    {"id": 1, "type": "car", "rel_x": 30.0, "rel_y": 0.2, "rel_z": 0.0, "speed": 0.0, "heading": 0.0, "behavior": "static"}
                ]
            },
            {
                "id": "scenario_05",
                "name": "Auto-Rickshaw Lateral Weaving",
                "category": "Indian Mixed Traffic",
                "difficulty": "Hard",
                "description": "An auto-rickshaw ahead changes lateral position erratically across lanes, forcing dynamic real-time prediction and smooth trajectory adaptation.",
                "road_width": 9.0,
                "start_position": {"x": 0.0, "y": 0.0, "heading": 0.0},
                "destination": {"x": 150.0, "y": 0.0},
                "actors": [
                    {"id": 1, "type": "auto_rickshaw", "rel_x": 20.0, "rel_y": 0.0, "rel_z": 0.0, "speed": 5.0, "heading": 0.0, "behavior": "weave", "weave_amplitude": 1.8, "weave_freq": 0.8}
                ]
            },
            {
                "id": "scenario_06",
                "name": "Chaotic Mixed Traffic Stream",
                "category": "Dense Urban",
                "difficulty": "Expert",
                "description": "Simultaneous presence of multiple vehicles: 2 motorcycles, an auto-rickshaw, a truck, and a cyclist moving at heterogeneous speeds.",
                "road_width": 11.0,
                "start_position": {"x": 0.0, "y": 0.0, "heading": 0.0},
                "destination": {"x": 160.0, "y": 0.0},
                "actors": [
                    {"id": 1, "type": "auto_rickshaw", "rel_x": 18.0, "rel_y": -1.5, "rel_z": 0.0, "speed": 4.5, "heading": 0.0, "behavior": "forward"},
                    {"id": 2, "type": "motorcycle", "rel_x": 12.0, "rel_y": 2.2, "rel_z": 0.0, "speed": 7.0, "heading": -5.0, "behavior": "overtake"},
                    {"id": 3, "type": "truck", "rel_x": 45.0, "rel_y": 1.5, "rel_z": 0.0, "speed": 3.5, "heading": 0.0, "behavior": "forward_slow"},
                    {"id": 4, "type": "motorcycle", "rel_x": 32.0, "rel_y": -2.8, "rel_z": 0.0, "speed": 6.0, "heading": 0.0, "behavior": "forward"}
                ]
            },
            {
                "id": "scenario_07",
                "name": "Stray Animal on Highway",
                "category": "Suburban / Rural",
                "difficulty": "Hard",
                "description": "A stray cow/animal slowly enters and stops directly in the center of the lane. Autonomous system must identify animal classification, halt safely, and replan around when clear.",
                "road_width": 8.0,
                "start_position": {"x": 0.0, "y": 0.0, "heading": 0.0},
                "destination": {"x": 120.0, "y": 0.0},
                "actors": [
                    {"id": 1, "type": "animal", "rel_x": 28.0, "rel_y": 3.0, "rel_z": 0.0, "speed": 0.8, "heading": -80.0, "behavior": "wander_and_stop", "target_y": 0.2, "trigger_dist": 35.0}
                ]
            },
            {
                "id": "scenario_08",
                "name": "Oncoming Vehicle on Single-Lane Road",
                "category": "Rural / Mountain Road",
                "difficulty": "Hard",
                "description": "Oncoming car traveling in opposite direction on narrow un-divided road. Requires speed reduction, yielding to left shoulder, and passing safely.",
                "road_width": 6.0,
                "start_position": {"x": 0.0, "y": 0.0, "heading": 0.0},
                "destination": {"x": 130.0, "y": 0.0},
                "actors": [
                    {"id": 1, "type": "car", "rel_x": 65.0, "rel_y": -0.4, "rel_z": 0.0, "speed": 6.0, "heading": 180.0, "behavior": "oncoming"}
                ]
            },
            {
                "id": "scenario_09",
                "name": "Road Debris and Pothole Obstacle",
                "category": "Unstructured Road Surface",
                "difficulty": "Medium",
                "description": "Roadside construction debris and deep pothole obstruction in the primary driving corridor, necessitating smooth local path diversion.",
                "road_width": 8.0,
                "start_position": {"x": 0.0, "y": 0.0, "heading": 0.0},
                "destination": {"x": 120.0, "y": 0.0},
                "actors": [
                    {"id": 1, "type": "debris", "rel_x": 25.0, "rel_y": 0.1, "rel_z": 0.0, "speed": 0.0, "heading": 0.0, "behavior": "static"},
                    {"id": 2, "type": "debris", "rel_x": 55.0, "rel_y": -1.2, "rel_z": 0.0, "speed": 0.0, "heading": 0.0, "behavior": "static"}
                ]
            },
            {
                "id": "scenario_10",
                "name": "Unstructured Indian Crossroad Intersection",
                "category": "Intersection Complex",
                "difficulty": "Expert",
                "description": "High-complexity unstructured intersection without traffic signals. Pedestrians, auto-rickshaws, and motorcycles cross from multiple conflicting angles.",
                "road_width": 14.0,
                "start_position": {"x": 0.0, "y": 0.0, "heading": 0.0},
                "destination": {"x": 140.0, "y": 0.0},
                "actors": [
                    {"id": 1, "type": "auto_rickshaw", "rel_x": 35.0, "rel_y": 6.0, "rel_z": 0.0, "speed": 3.8, "heading": -90.0, "behavior": "cross_road", "target_y": -6.0},
                    {"id": 2, "type": "pedestrian", "rel_x": 30.0, "rel_y": -5.0, "rel_z": 0.0, "speed": 1.2, "heading": 85.0, "behavior": "cross_road", "target_y": 5.0},
                    {"id": 3, "type": "motorcycle", "rel_x": 50.0, "rel_y": 0.5, "rel_z": 0.0, "speed": 5.0, "heading": 0.0, "behavior": "forward"}
                ]
            }
        ]

        # Save to JSON directory and instantiate Scenario objects
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
        for s_data in scenarios_def:
            scenario_obj = Scenario(
                scenario_id=s_data["id"],
                name=s_data["name"],
                category=s_data["category"],
                difficulty=s_data["difficulty"],
                description=s_data["description"],
                road_width=s_data["road_width"],
                actors=s_data["actors"],
                start_position=s_data["start_position"],
                destination=s_data["destination"]
            )
            self.scenarios[scenario_obj.id] = scenario_obj
            
            # Save JSON copy
            json_file = self.scenarios_dir / f"{s_data['id']}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(s_data, f, indent=2)

        # Set default active scenario
        self.load_scenario("scenario_02")

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """Returns list of all available scenarios."""
        return [s.to_dict() for s in self.scenarios.values()]

    def load_scenario(self, scenario_id: str) -> Optional[Scenario]:
        """Loads and resets active scenario state."""
        if scenario_id in self.scenarios:
            self.current_scenario = self.scenarios[scenario_id]
            self.active_actors = [dict(a) for a in self.current_scenario.actors]
            self.scenario_start_time = time.time()
            print(f"[ScenarioManager] Loaded: {self.current_scenario.name} ({self.current_scenario.difficulty})")
            return self.current_scenario
        return None

    def update_actors(self, ego_x: float, ego_speed: float, dt: float = 0.05) -> List[Dict[str, Any]]:
        """
        Updates dynamic actor positions based on realistic motion profiles and ego trigger distances.
        """
        if not self.current_scenario:
            return []

        elapsed = time.time() - self.scenario_start_time

        for actor in self.active_actors:
            behavior = actor.get("behavior", "static")
            speed = actor.get("speed", 0.0)
            rel_x = actor.get("rel_x", 20.0)
            rel_y = actor.get("rel_y", 0.0)

            # Check trigger distance if configured
            trigger = actor.get("trigger_dist", 999.0)
            is_triggered = rel_x <= trigger

            if behavior == "cut_in" and is_triggered:
                # Motorcycle moves forward and laterally cuts across lane
                actor["rel_x"] -= (ego_speed - speed) * dt
                target_y = actor.get("target_y", 0.8)
                if abs(actor["rel_y"] - target_y) > 0.05:
                    step_y = 2.2 * dt if target_y > actor["rel_y"] else -2.2 * dt
                    actor["rel_y"] += step_y
                    actor["heading"] = 30.0
                else:
                    actor["heading"] = 0.0

            elif behavior == "cross_road" and is_triggered:
                # Pedestrian / crossing actor crosses laterally
                actor["rel_x"] -= (ego_speed) * dt
                target_y = actor.get("target_y", -4.0)
                if abs(actor["rel_y"] - target_y) > 0.1:
                    step_y = speed * dt if target_y > actor["rel_y"] else -speed * dt
                    actor["rel_y"] += step_y
                else:
                    actor["speed"] = 0.0

            elif behavior == "weave":
                # Auto-rickshaw sinusoidal weaving
                actor["rel_x"] -= (ego_speed - speed) * dt
                amp = actor.get("weave_amplitude", 1.5)
                freq = actor.get("weave_freq", 0.6)
                actor["rel_y"] = amp * np.sin(freq * elapsed * 2 * np.pi)
                actor["heading"] = float(np.rad2deg(np.arctan2(amp * freq * np.cos(freq * elapsed * 2 * np.pi), speed)))

            elif behavior == "wander_and_stop" and is_triggered:
                # Stray cattle walks to lane center and stops
                actor["rel_x"] -= ego_speed * dt
                target_y = actor.get("target_y", 0.2)
                if abs(actor["rel_y"] - target_y) > 0.1:
                    actor["rel_y"] -= speed * dt
                else:
                    actor["speed"] = 0.0

            elif behavior == "oncoming":
                # Vehicle approaching in opposite direction
                actor["rel_x"] -= (ego_speed + speed) * dt

            elif behavior in ["forward", "forward_slow"]:
                # Normal forward flow
                actor["rel_x"] -= (ego_speed - speed) * dt

            elif behavior == "static":
                # Static stationary obstacle
                actor["rel_x"] -= ego_speed * dt

        # Filter out actors that have passed far behind vehicle
        self.active_actors = [a for a in self.active_actors if a.get("rel_x", 0.0) > -15.0]

        return self.active_actors
