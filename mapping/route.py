"""
route.py — OSRM Global Route Client & Coordinate Projection Utilities.

Connects to the Open Source Routing Machine (OSRM) to fetch real road geometries
between GPS waypoints. Provides local corridor <-> GPS coordinate transformations.
"""

from __future__ import annotations
import requests
import numpy as np
from typing import List, Tuple, Dict, Any, Optional


class RouteManager:
    """Manages global route queries and coordinate projections."""

    OSRM_ENDPOINT = "http://router.project-osrm.org/route/v1/driving"

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    def get_route(
        self,
        source_lat: float,
        source_lon: float,
        dest_lat: float,
        dest_lon: float
    ) -> Dict[str, Any]:
        """
        Fetches driving route between source and destination via OSRM.
        Falls back to densified geodesic interpolation if OSRM is offline.
        """
        url = f"{self.OSRM_ENDPOINT}/{source_lon},{source_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson&steps=true"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok" and len(data.get("routes", [])) > 0:
                    primary_route = data["routes"][0]
                    coords = primary_route["geometry"]["coordinates"] # List of [lon, lat]
                    
                    # Convert to list of [lat, lon]
                    waypoints = [[lat, lon] for lon, lat in coords]
                    
                    return {
                        "status": "success",
                        "source": [source_lat, source_lon],
                        "destination": [dest_lat, dest_lon],
                        "distance_m": primary_route["distance"],
                        "duration_s": primary_route["duration"],
                        "waypoints": waypoints,
                        "geometry": primary_route["geometry"],
                        "source_type": "OSRM"
                    }
        except Exception as e:
            print(f"[RouteManager] OSRM query failed ({e}), using fallback route generator.")

        # Fallback densified route generator (for offline hackathons / rate limits)
        return self._generate_fallback_route(source_lat, source_lon, dest_lat, dest_lon)

    def _generate_fallback_route(
        self,
        src_lat: float,
        src_lon: float,
        dst_lat: float,
        dst_lon: float,
        num_points: int = 50
    ) -> Dict[str, Any]:
        """Generates realistic curved road waypoints between two GPS points."""
        lats = np.linspace(src_lat, dst_lat, num_points)
        lons = np.linspace(src_lon, dst_lon, num_points)
        
        # Add slight natural road curvature
        curve_factor = 0.0008 * np.sin(np.linspace(0, np.pi, num_points))
        lats = lats + curve_factor
        
        waypoints = [[float(lat), float(lon)] for lat, lon in zip(lats, lons)]
        coords_geojson = [[float(lon), float(lat)] for lat, lon in zip(lats, lons)]

        # Approximate distance in meters using Haversine
        dist_m = self.haversine_distance(src_lat, src_lon, dst_lat, dst_lon)
        duration_s = dist_m / 10.0 # ~36 km/h avg speed

        return {
            "status": "success",
            "source": [src_lat, src_lon],
            "destination": [dst_lat, dst_lon],
            "distance_m": round(dist_m, 2),
            "duration_s": round(duration_s, 2),
            "waypoints": waypoints,
            "geometry": {
                "type": "LineString",
                "coordinates": coords_geojson
            },
            "source_type": "FALLBACK_INTERPOLATED"
        }

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance between two GPS coordinates in meters."""
        R = 6371000.0 # Earth radius in meters
        phi1 = np.radians(lat1)
        phi2 = np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)

        a = np.sin(dphi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0)**2
        c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
        return float(R * c)


def local_to_gps(
    x: float,
    y: float,
    waypoints: List[List[float]],
    corridor_length: float = 100.0
) -> Tuple[float, float, float]:
    """
    Maps local simulation corridor coordinates (x: longitudinal, y: lateral)
    onto the global GPS waypoint path.
    
    Returns:
      (latitude, longitude, heading_degrees)
    """
    if not waypoints or len(waypoints) < 2:
        return 0.0, 0.0, 0.0

    num_pts = len(waypoints)
    # Normalized progress fraction [0, 1]
    progress = np.clip(x / max(1.0, corridor_length), 0.0, 1.0)
    index_float = progress * (num_pts - 1)
    idx0 = int(np.floor(index_float))
    idx1 = min(idx0 + 1, num_pts - 1)
    frac = index_float - idx0

    p0 = waypoints[idx0]
    p1 = waypoints[idx1]

    # Centerline position
    lat_center = p0[0] + frac * (p1[0] - p0[0])
    lon_center = p0[1] + frac * (p1[1] - p0[1])

    # Tangent vector & heading angle
    d_lat = p1[0] - p0[0]
    d_lon = p1[1] - p0[1]
    heading_rad = np.arctan2(d_lon, d_lat)
    heading_deg = (np.degrees(heading_rad) + 360.0) % 360.0

    # Perpendicular normal vector for lateral offset y (1 deg lat ~ 111,139 meters)
    meters_per_deg_lat = 111139.0
    meters_per_deg_lon = 111139.0 * np.cos(np.radians(lat_center))

    normal_lat = -np.sin(heading_rad)
    normal_lon = np.cos(heading_rad)

    lat_final = lat_center + (y * normal_lat) / meters_per_deg_lat
    lon_final = lon_center + (y * normal_lon) / max(1.0, meters_per_deg_lon)

    return float(lat_final), float(lon_final), float(heading_deg)
