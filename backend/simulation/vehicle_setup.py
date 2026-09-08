"""
Vehicle and Sensor Setup Module for CARLA Simulator.
Spawns ego vehicle and attaches RGB, Depth, LiDAR, GNSS, IMU, and Collision sensors.
"""

import time
from typing import Optional, List, Dict, Any
from config import config
from backend.perception.camera import CameraSensor


class VehicleSetup:
    """
    Spawns ego vehicle, configures physical blueprints,
    and manages sensor attachments.
    """

    def __init__(self, carla_manager, camera_sensor: CameraSensor):
        self.cm = carla_manager
        self.camera_sensor = camera_sensor
        self.ego_vehicle = None
        self.sensor_actors: List[Any] = []
        self.collision_history: List[Dict[str, Any]] = []
        self.latest_gnss: Dict[str, float] = {"lat": 28.6139, "lon": 77.2090, "alt": 215.0} # New Delhi default

    def spawn_ego_vehicle(self, spawn_transform=None) -> bool:
        """Spawns autonomous ego vehicle and attaches full sensor suite."""
        if not self.cm.is_connected or self.cm.world is None:
            return False

        try:
            self.destroy_actors()
            world = self.cm.world
            bp_lib = world.get_blueprint_library()

            # 1. Spawn Ego Vehicle
            veh_bp = bp_lib.find(config.vehicle.blueprint_id)
            veh_bp.set_attribute('role_name', 'ego_vehicle')

            if spawn_transform is None:
                spawn_points = self.cm.map.get_spawn_points()
                spawn_transform = spawn_points[0] if spawn_points else self.cm.carla_module.Transform()

            self.ego_vehicle = world.spawn_actor(veh_bp, spawn_transform)
            print(f"[VehicleSetup] Spawned Ego Vehicle #{self.ego_vehicle.id}")

            # 2. Attach RGB Camera
            cam_bp = bp_lib.find('sensor.camera.rgb')
            cam_bp.set_attribute('image_size_x', str(config.sensor.camera_width))
            cam_bp.set_attribute('image_size_y', str(config.sensor.camera_height))
            cam_bp.set_attribute('fov', str(config.sensor.camera_fov))
            cam_transform = self.cm.carla_module.Transform(
                self.cm.carla_module.Location(x=config.sensor.camera_transform[0], y=config.sensor.camera_transform[1], z=config.sensor.camera_transform[2])
            )
            rgb_actor = world.spawn_actor(cam_bp, cam_transform, attach_to=self.ego_vehicle)
            rgb_actor.listen(self.camera_sensor.carla_rgb_callback)
            self.sensor_actors.append(rgb_actor)

            # 3. Attach Depth Camera
            depth_bp = bp_lib.find('sensor.camera.depth')
            depth_bp.set_attribute('image_size_x', str(config.sensor.camera_width))
            depth_bp.set_attribute('image_size_y', str(config.sensor.camera_height))
            depth_bp.set_attribute('fov', str(config.sensor.camera_fov))
            depth_actor = world.spawn_actor(depth_bp, cam_transform, attach_to=self.ego_vehicle)
            depth_actor.listen(self.camera_sensor.carla_depth_callback)
            self.sensor_actors.append(depth_actor)

            # 4. Attach Collision Sensor
            col_bp = bp_lib.find('sensor.other.collision')
            col_actor = world.spawn_actor(col_bp, self.cm.carla_module.Transform(), attach_to=self.ego_vehicle)
            col_actor.listen(self._on_collision)
            self.sensor_actors.append(col_actor)

            # 5. Attach GNSS Sensor
            gnss_bp = bp_lib.find('sensor.other.gnss')
            gnss_actor = world.spawn_actor(gnss_bp, self.cm.carla_module.Transform(), attach_to=self.ego_vehicle)
            gnss_actor.listen(self._on_gnss)
            self.sensor_actors.append(gnss_actor)

            return True

        except Exception as e:
            print(f"[VehicleSetup] Error spawning vehicle & sensors: {e}")
            return False

    def _on_collision(self, event):
        """Callback on collision event."""
        other_actor = event.other_actor.type_id if event.other_actor else "unknown"
        impulse = event.normal_impulse
        intensity = (impulse.x**2 + impulse.y**2 + impulse.z**2)**0.5
        record = {
            "timestamp": time.time(),
            "other_actor": other_actor,
            "intensity": round(intensity, 2)
        }
        self.collision_history.append(record)
        print(f"[COLLISION EVENT] Impact with {other_actor} (Intensity: {intensity:.1f})")

    def _on_gnss(self, event):
        """Callback on GNSS telemetry."""
        self.latest_gnss = {
            "lat": round(event.latitude, 6),
            "lon": round(event.longitude, 6),
            "alt": round(event.altitude, 2)
        }

    def apply_control(self, steer: float, throttle: float, brake: float):
        """Applies driverless vehicle control to CARLA actor."""
        if self.ego_vehicle is not None and self.cm.is_connected:
            try:
                control = self.cm.carla_module.VehicleControl()
                control.steer = float(steer)
                control.throttle = float(throttle)
                control.brake = float(brake)
                control.hand_brake = False
                control.reverse = False
                self.ego_vehicle.apply_control(control)
            except Exception as e:
                print(f"[VehicleSetup] Control apply error: {e}")

    def get_telemetry(self) -> Dict[str, Any]:
        """Retrieves live transform, velocity, acceleration, and heading from CARLA vehicle."""
        if self.ego_vehicle is not None and self.cm.is_connected:
            try:
                tf = self.ego_vehicle.get_transform()
                vel = self.ego_vehicle.get_velocity()
                acc = self.ego_vehicle.get_acceleration()
                
                speed_ms = (vel.x**2 + vel.y**2 + vel.z**2)**0.5
                speed_kmh = speed_ms * 3.6
                acc_ms2 = (acc.x**2 + acc.y**2 + acc.z**2)**0.5

                return {
                    "x": round(tf.location.x, 2),
                    "y": round(tf.location.y, 2),
                    "z": round(tf.location.z, 2),
                    "heading_deg": round(tf.rotation.yaw, 1),
                    "speed_kmh": round(speed_kmh, 1),
                    "speed_ms": round(speed_ms, 2),
                    "accel_ms2": round(acc_ms2, 2),
                    "gnss": self.latest_gnss
                }
            except Exception:
                pass

        return {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "heading_deg": 0.0,
            "speed_kmh": 0.0,
            "speed_ms": 0.0,
            "accel_ms2": 0.0,
            "gnss": self.latest_gnss
        }

    def destroy_actors(self):
        """Destroys all spawned CARLA actors and sensors."""
        for sensor in self.sensor_actors:
            try:
                sensor.stop()
                sensor.destroy()
            except Exception:
                pass
        self.sensor_actors.clear()

        if self.ego_vehicle is not None:
            try:
                self.ego_vehicle.destroy()
            except Exception:
                pass
            self.ego_vehicle = None
