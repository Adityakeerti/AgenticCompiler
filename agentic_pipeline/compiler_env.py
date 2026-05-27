"""
compiler_env.py
───────────────
A Gymnasium environment that frames CPY error correction as an
RL problem.

  State   →  25-dim feature vector (error context + code features)
  Action  →  one of 9 discrete fix operations
  Reward  →  +1 correct action, −1 wrong action, −0.1 per step

During **training** the dataset itself acts as the oracle
(we compare the predicted action to the ground-truth target_action).
This is orders of magnitude faster than calling the real compiler
on every step, and produces identical learning signal for our data.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random

from dataset_loader import load_dataset, DatasetEntry, NUM_ACTIONS, ID_TO_ACTION
from feature_encoder import encode, OBSERVATION_SIZE


class CPYCompilerEnv(gym.Env):
    """
    Custom Gymnasium environment for CPY error correction.

    Each episode:
      1. ``reset()`` picks a random buggy snippet from the dataset.
      2. The agent observes the 25-dim feature vector.
      3. The agent chooses an action (integer 0-8).
      4. ``step()`` compares to the ground-truth action.
         • Correct  → reward = +1, episode done.
         • Wrong    → reward = −1, episode done.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, dataset: list[DatasetEntry] | None = None, render_mode=None):
        super().__init__()

        self.dataset = dataset if dataset is not None else load_dataset()
        self.render_mode = render_mode

        # Gym spaces
        self.observation_space = spaces.Box(
            low=-1.0, high=2.0,
            shape=(OBSERVATION_SIZE,),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(NUM_ACTIONS)

        # Current episode state
        self._current_entry: DatasetEntry | None = None
        self._obs: np.ndarray | None = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        # Pick a random entry
        self._current_entry = random.choice(self.dataset)

        # Encode observation
        self._obs = encode(
            self._current_entry.original_code,
            self._current_entry.error_type,
            self._current_entry.error_message,
            self._current_entry.error_line,
        )

        return self._obs.copy(), {}

    def step(self, action: int):
        assert self._current_entry is not None, "Call reset() first"

        correct_action = self._current_entry.target_action_id

        if action == correct_action:
            reward = 1.0
        else:
            reward = -1.0

        # Episode always ends after one step (single-shot prediction)
        terminated = True
        truncated = False

        info = {
            "correct_action": correct_action,
            "correct_label": ID_TO_ACTION[correct_action],
            "predicted_label": ID_TO_ACTION.get(action, "UNKNOWN"),
            "was_correct": action == correct_action,
            "entry_id": self._current_entry.id,
        }

        if self.render_mode == "human":
            self._render_step(action, info)

        return self._obs.copy(), reward, terminated, truncated, info

    def _render_step(self, action: int, info: dict):
        status = "CORRECT" if info["was_correct"] else "WRONG"
        print(f"  [{status}] predicted={info['predicted_label']}, "
              f"expected={info['correct_label']}, "
              f"id={info['entry_id']}")


# ── Quick smoke test ──────────────────────────────────────────
if __name__ == "__main__":
    env = CPYCompilerEnv(render_mode="human")

    print("Running 5 random episodes...\n")
    for ep in range(5):
        obs, _ = env.reset()
        action = env.action_space.sample()
        obs, reward, term, trunc, info = env.step(action)
        print(f"  reward={reward:+.0f}\n")

    env.close()
    print("Environment is working!")
