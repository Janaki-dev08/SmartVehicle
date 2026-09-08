"""
Unit Tests for Scenario Manager & Indian Road Scenarios.
"""

import pytest
from backend.simulation.scenario_manager import ScenarioManager


def test_scenario_loader():
    """Verify all 10 Indian road scenarios are present and structurally valid."""
    sm = ScenarioManager()
    scenarios = sm.list_scenarios()

    assert len(scenarios) >= 10

    expected_ids = [
        "scenario_01", "scenario_02", "scenario_03", "scenario_04", "scenario_05",
        "scenario_06", "scenario_07", "scenario_08", "scenario_09", "scenario_10"
    ]

    scenario_id_set = {s["id"] for s in scenarios}
    for exp_id in expected_ids:
        assert exp_id in scenario_id_set, f"Missing scenario {exp_id}"

    # Verify attributes of each scenario
    for s in scenarios:
        assert "name" in s and len(s["name"]) > 0
        assert "road_width" in s and s["road_width"] > 0
        assert "actors" in s
        assert "start_position" in s
        assert "destination" in s


def test_scenario_activation():
    """Test switching scenarios loads actors properly."""
    sm = ScenarioManager()
    scenario = sm.load_scenario("scenario_07") # Stray Animal

    assert scenario is not None
    assert scenario.id == "scenario_07"
    assert any(a["type"] == "animal" for a in scenario.actors)
