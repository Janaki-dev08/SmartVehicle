"""
tests/test_api.py — Verification Tests for FastAPI Endpoints & OSRM Routing.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model_ready" in data


def test_route_osrm_endpoint():
    # Source & Destination in Andhra Pradesh (Guntur to Vijayawada)
    payload = {
        "source_lat": 16.3067,
        "source_lon": 80.4365,
        "dest_lat": 16.5062,
        "dest_lon": 80.6480
    }
    response = client.post("/api/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["waypoints"]) >= 2
    assert data["distance_m"] > 0
    assert "geometry" in data


def test_simulation_lifecycle():
    # 1. Start simulation
    start_payload = {
        "difficulty": 1,
        "corridor_length": 100.0,
        "road_width": 7.0,
        "seed": 42
    }
    start_resp = client.post("/api/simulation/start", json=start_payload)
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    session_id = start_data["session_id"]
    assert session_id is not None
    assert len(start_data["obstacles"]) > 0
    assert start_data["vehicle"]["x"] >= 0.0

    # 2. Step simulation across multiple ticks
    for _ in range(10):
        step_payload = {
            "session_id": session_id
        }
        step_resp = client.post("/api/simulation/step", json=step_payload)
        assert step_resp.status_code == 200
        step_data = step_resp.json()
        assert step_data["step"] > 0
        assert "vehicle" in step_data
        assert "safety" in step_data
        assert "action_executed_name" in step_data
        assert len(step_data["obstacles"]) > 0
        if step_data["done"]:
            break

    # 3. Check metrics endpoint
    metrics_resp = client.get("/api/metrics")
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    assert metrics_data["total_sessions"] > 0
    assert metrics_data["total_steps"] > 0
