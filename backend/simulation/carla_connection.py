"""
CARLA Simulator Connection Manager.
Manages network connection, world loading, synchronous mode, and graceful disconnection states.
"""

import time
from typing import Optional, Dict, Any
from config import config


class CarlaConnectionManager:
    """
    Manages lifecycle of CARLA Python API client connection.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host or config.carla.host
        self.port = port or config.carla.port
        self.timeout = config.carla.timeout
        self.client = None
        self.world = None
        self.map = None
        self.is_connected = False
        self.connection_status = "CARLA DISCONNECTED"
        self.last_error = ""
        self.carla_module = None
        self._check_carla_package()

    def _check_carla_package(self):
        """Checks if carla python package is installed."""
        try:
            import carla
            self.carla_module = carla
        except ImportError:
            self.carla_module = None
            self.last_error = "CARLA Python library not installed in current environment."

    def connect(self) -> bool:
        """
        Attempts connection to the CARLA server.
        Does not crash if CARLA is offline.
        """
        if self.carla_module is None:
            self.is_connected = False
            self.connection_status = "CARLA DISCONNECTED"
            self.last_error = "CARLA Python API package ('carla') is not installed."
            return False

        try:
            self.connection_status = "CONNECTING..."
            self.client = self.carla_module.Client(self.host, self.port)
            self.client.set_timeout(self.timeout)
            
            # Retrieve world
            self.world = self.client.get_world()
            self.map = self.world.get_map()
            
            # Configure Synchronous Mode if specified
            if config.carla.sync_mode:
                settings = self.world.get_settings()
                settings.synchronous_mode = True
                settings.fixed_delta_seconds = config.carla.fixed_delta_seconds
                self.world.apply_settings(settings)

            self.is_connected = True
            self.connection_status = "CARLA CONNECTED"
            self.last_error = ""
            print(f"[CARLA] Successfully connected to {self.host}:{self.port} (Map: {self.map.name})")
            return True

        except Exception as e:
            self.client = None
            self.world = None
            self.map = None
            self.is_connected = False
            self.connection_status = "CARLA DISCONNECTED"
            self.last_error = str(e)
            print(f"[CARLA] Connection failed: {e}")
            return False

    def disconnect(self):
        """Cleanly releases synchronous mode and client references."""
        if self.is_connected and self.world is not None:
            try:
                settings = self.world.get_settings()
                settings.synchronous_mode = False
                settings.fixed_delta_seconds = None
                self.world.apply_settings(settings)
            except Exception:
                pass
        
        self.is_connected = False
        self.connection_status = "CARLA DISCONNECTED"
        self.client = None
        self.world = None
        self.map = None

    def tick(self):
        """Ticks the simulation in synchronous mode."""
        if self.is_connected and self.world is not None and config.carla.sync_mode:
            try:
                self.world.tick()
            except Exception as e:
                print(f"[CARLA] World tick error: {e}")
                self.disconnect()

    def get_status(self) -> Dict[str, Any]:
        """Returns connection telemetry for the dashboard."""
        return {
            "connected": self.is_connected,
            "status": self.connection_status,
            "host": self.host,
            "port": self.port,
            "map": self.map.name if self.map else "Town03 (Simulated)",
            "sync_mode": config.carla.sync_mode,
            "last_error": self.last_error,
            "instructions": "Ensure CARLA server (CarlaUE4.exe -carla-server) is running on port 2000." if not self.is_connected else "Connected."
        }
