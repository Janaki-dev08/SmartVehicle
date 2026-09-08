"""
tests/test_rl.py — Verification Tests for PPO Policy Inference.
"""

import os
import pytest
import numpy as np
from stable_baselines3 import PPO
from rl.environment.road_env import IndianRoadEnv


def test_ppo_inference_rollout():
    checkpoint_path = "rl/checkpoints/ppo_indian_road.zip"
    if not os.path.exists(checkpoint_path):
        pytest.skip("Model checkpoint not yet trained.")

    model = PPO.load(checkpoint_path)
    env = IndianRoadEnv(corridor_length=100.0, road_width=7.0, difficulty=1)
    obs, info = env.reset(seed=42)

    for _ in range(20):
        action, _ = model.predict(obs, deterministic=True)
        assert 0 <= int(action) <= 7
        obs, reward, term, trunc, info = env.step(int(action))
        if term or trunc:
            break
