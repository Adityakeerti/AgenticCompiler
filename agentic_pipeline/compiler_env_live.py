"""
compiler_env_live.py  (Tier 3)
------------------------------
A multi-step Gymnasium environment that calls the REAL CPY Java compiler
at every step. This is the most academically significant upgrade:

  - Training happens in the real-world error distribution (no oracle shortcuts)
  - The agent learns to plan across 5 steps (true sequential MDP)
  - Reward shaping guides the agent: each unique error type change = forward progress

Key difference from compiler_env.py:
  - compiler_env.py  = single-step oracle (fast, uses CSV ground truth)
  - compiler_env_live.py = multi-step MDP (slow, uses real Java subprocess)

Episode flow:
  1. Pick a broken CPY snippet from dataset
  2. Compile it with real Java compiler -> get actual error
  3. Encode error -> 25-dim observation
  4. Agent picks action
  5. Apply fix to code
  6. Recompile -> check success / progress
  7. Repeat up to MAX_STEPS

Reward:
  +10.0  code compiles successfully
  +1.0   error type changed (made forward progress)
  -0.5   per step taken (penalizes unnecessary steps)
  -5.0   exhausted all steps without success
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random
import sys
import os

# Add the pipeline directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataset_loader import load_dataset, DatasetEntry, NUM_ACTIONS, ID_TO_ACTION
from feature_encoder import encode, OBSERVATION_SIZE
from fix_applier import apply_fix
from compiler_wrapper import compile_code


class CPYCompilerEnvLive(gym.Env):
    """
    Multi-step Gymnasium environment using the real CPY Java compiler.

    Each episode:
      1. reset() picks a broken snippet, compiles it for real.
      2. Agent observes the 25-dim vector from the REAL compiler error.
      3. Agent picks an action.
      4. Fix is applied, code recompiles.
      5. Reward given based on success/progress.
      6. Repeat up to MAX_STEPS.
    """

    MAX_STEPS = 5
    metadata = {"render_modes": ["human"]}

    def __init__(self, dataset: list | None = None, render_mode=None):
        super().__init__()

        self.dataset = dataset if dataset is not None else load_dataset()
        self.render_mode = render_mode

        self.observation_space = spaces.Box(
            low=-1.0, high=2.0,
            shape=(OBSERVATION_SIZE,),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(NUM_ACTIONS)

        # Episode state
        self._current_code: str | None = None
        self._steps: int = 0
        self._prev_error_type: str | None = None
        self._obs: np.ndarray | None = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self._steps = 0
        self._prev_error_type = None

        # Pick a random broken snippet from dataset
        entry = random.choice(self.dataset)
        self._current_code = entry.original_code

        # Compile with REAL Java compiler to get actual error
        result = compile_code(self._current_code)

        if result.success:
            # Rarely, our "broken" code might compile (e.g. if Java is lenient)
            # Return zero observation and mark as already done
            self._obs = np.zeros(OBSERVATION_SIZE, dtype=np.float32)
            self._prev_error_type = None
        else:
            self._prev_error_type = result.error_type
            self._obs = encode(
                self._current_code,
                result.error_type,
                result.error_message,
                result.error_line,
            )

        return self._obs.copy(), {}

    def step(self, action: int):
        assert self._current_code is not None, "Call reset() first"

        action_label = ID_TO_ACTION.get(action, "UNKNOWN")

        # First get the current error state
        result = compile_code(self._current_code)

        if result.success:
            # Already compiled (from reset edge case)
            reward = 10.0
            terminated = True
            info = {"success": True, "steps": self._steps, "action": action_label}
            return np.zeros(OBSERVATION_SIZE, dtype=np.float32), reward, terminated, False, info

        # Apply the predicted fix
        error_line = result.error_line
        self._current_code = apply_fix(
            self._current_code,
            error_line,
            action_label,
            result.error_message,
        )

        self._steps += 1

        # Recompile after applying fix
        new_result = compile_code(self._current_code)

        if new_result.success:
            # SUCCESS: code now compiles!
            reward = 10.0 - (self._steps * 0.5)  # Bonus for fewer steps
            reward = max(reward, 5.0)             # Minimum success reward
            terminated = True
            obs = np.zeros(OBSERVATION_SIZE, dtype=np.float32)
            info = {"success": True, "steps": self._steps, "action": action_label}

        elif self._steps >= self.MAX_STEPS:
            # FAILURE: exhausted all steps
            reward = -5.0
            terminated = True
            obs = np.zeros(OBSERVATION_SIZE, dtype=np.float32)
            info = {"success": False, "steps": self._steps, "action": action_label}

        else:
            # PARTIAL: still errors, keep going
            # Give +1 reward if the error TYPE changed (forward progress)
            if new_result.error_type != self._prev_error_type and self._prev_error_type is not None:
                reward = 1.0  # Progress: different kind of error now
            else:
                reward = -0.5  # No progress: same error

            terminated = False
            self._prev_error_type = new_result.error_type
            obs = encode(
                self._current_code,
                new_result.error_type,
                new_result.error_message,
                new_result.error_line,
            )
            info = {
                "success": False,
                "steps": self._steps,
                "action": action_label,
                "new_error": new_result.error_message,
            }

        self._obs = obs

        if self.render_mode == "human":
            status = "OK" if info["success"] else "..."
            print(f"  [{status}] action={action_label}, steps={self._steps}, reward={reward:+.1f}")

        return obs.copy(), reward, terminated, False, info


# ── Quick smoke test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing CPYCompilerEnvLive...")
    print("(This will call the real Java CPY compiler)\n")

    env = CPYCompilerEnvLive(render_mode="human")

    for ep in range(3):
        print(f"\nEpisode {ep + 1}:")
        obs, _ = env.reset()
        done = False
        total_reward = 0.0

        while not done:
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            total_reward += reward

        status = "SUCCESS" if info["success"] else "FAILED"
        print(f"  Result: {status} | Steps: {info['steps']} | Total reward: {total_reward:+.1f}")

    env.close()
    print("\nLive environment is working!")
