"""
train_dqn.py
------------
Train a DQN agent (with replay buffer) on the same CPY error-correction task.
Compare with the PPO agent from train.py.

Key DQN advantages over PPO for this task:
  - Replay buffer: reuses every experience (off-policy, sample-efficient)
  - Prioritized replay: focuses learning on harder examples (INSERT_RBRACE)
  - Target network: stable Q-value targets

Usage:
    python train_dqn.py
    python train_dqn.py --timesteps 500000
"""

import argparse
import os
import time

import torch
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import EvalCallback, BaseCallback

from dataset_loader import load_dataset, train_test_split
from compiler_env import CPYCompilerEnv


class ProgressCallback(BaseCallback):
    def __init__(self, print_freq=10000, verbose=0):
        super().__init__(verbose)
        self.print_freq = print_freq
        self.start_time = None
        self.correct = 0
        self.total = 0

    def _on_training_start(self):
        self.start_time = time.time()

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", []):
            if "was_correct" in info:
                self.total += 1
                if info["was_correct"]:
                    self.correct += 1

        if self.num_timesteps % self.print_freq == 0 and self.total > 0:
            acc = self.correct / self.total * 100
            elapsed = time.time() - self.start_time
            print(
                f"  Step {self.num_timesteps:>8,} | "
                f"Accuracy: {acc:5.1f}% | "
                f"Correct: {self.correct}/{self.total} | "
                f"Time: {elapsed:.0f}s"
            )
            self.correct = 0
            self.total = 0
        return True


def train_dqn(timesteps: int, save_dir: str):
    print("=" * 60)
    print("  CPY Agentic Compiler -- DQN Training")
    print("=" * 60)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print(f"\n[GPU] Using: {torch.cuda.get_device_name(0)}")
    else:
        print("\n[GPU] CUDA not available, using CPU")

    # ── Load data ────────────────────────────────────────────────
    print("\n[1/3] Loading dataset...")
    all_data = load_dataset()
    train_data, test_data = train_test_split(all_data)
    print(f"  Total: {len(all_data):,} | Train: {len(train_data):,} | Test: {len(test_data):,}")

    # ── Create environments ───────────────────────────────────────
    print("\n[2/3] Creating environments...")
    # DQN only supports a single environment (uses replay buffer)
    train_env = CPYCompilerEnv(dataset=train_data)
    eval_env = CPYCompilerEnv(dataset=test_data)

    print(f"  Observation: {train_env.observation_space}")
    print(f"  Actions: {train_env.action_space.n}")
    print(f"  Device: {device}")

    # ── Build DQN agent ───────────────────────────────────────────
    print("\n[3/3] Building DQN agent...")
    os.makedirs("tb_logs", exist_ok=True)
    os.makedirs(save_dir, exist_ok=True)

    model = DQN(
        policy="MlpPolicy",
        env=train_env,
        learning_rate=1e-4,
        buffer_size=100_000,          # Replay buffer: stores past experiences
        learning_starts=5_000,        # Collect random experiences before learning
        batch_size=256,               # Mini-batch size for gradient updates
        tau=0.005,                    # Soft update coefficient for target network
        gamma=0.99,
        train_freq=4,                 # Update every 4 steps
        gradient_steps=1,
        target_update_interval=1000,  # Hard-update target network every 1000 steps
        exploration_fraction=0.15,    # Fraction of timesteps for epsilon decay
        exploration_initial_eps=1.0,  # Start fully random
        exploration_final_eps=0.05,   # End with 5% random exploration
        verbose=0,
        device=device,
        tensorboard_log="./tb_logs",
        policy_kwargs=dict(
            net_arch=[256, 256, 128],  # Same architecture as PPO for fair comparison
        ),
    )

    total_params = sum(p.numel() for p in model.policy.parameters())
    print(f"  Policy network: [256, 256, 128]")
    print(f"  Total parameters: {total_params:,}")
    print(f"  Replay buffer size: 100,000")
    print(f"  Learning starts at: 5,000 steps")
    print(f"  Training steps: {timesteps:,}")

    print(f"\nTraining for {timesteps:,} steps...")
    print("-" * 60)

    progress_cb = ProgressCallback(print_freq=10000)
    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path=os.path.join(save_dir, "best_dqn"),
        log_path=os.path.join(save_dir, "eval_logs_dqn"),
        eval_freq=50_000,
        n_eval_episodes=500,
        deterministic=True,
        verbose=1,
    )

    model.learn(
        total_timesteps=timesteps,
        callback=[progress_cb, eval_cb],
        progress_bar=False,
        tb_log_name="DQN",
    )

    print("-" * 60)

    # ── Save ─────────────────────────────────────────────────────
    model_path = os.path.join(save_dir, "cpy_agent_dqn")
    model.save(model_path)
    print(f"\n[OK] DQN model saved to: {model_path}.zip")

    # ── Quick eval ───────────────────────────────────────────────
    print("\nRunning evaluation on test set...")
    correct = 0
    total = min(len(test_data), 3000)
    eval_env2 = CPYCompilerEnv(dataset=test_data)
    for i in range(total):
        obs, _ = eval_env2.reset()
        action, _ = model.predict(obs, deterministic=True)
        _, _, _, _, info = eval_env2.step(int(action))
        if info["was_correct"]:
            correct += 1

    acc = correct / total * 100
    print(f"  Test accuracy: {acc:.1f}% ({correct}/{total})")

    train_env.close()
    eval_env.close()
    eval_env2.close()

    print(f"\n{'=' * 60}")
    print(f"  DQN Training complete!")
    print(f"  TensorBoard: tensorboard --logdir ./tb_logs")
    print(f"{'=' * 60}")

    return model_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train DQN agent for CPY error correction")
    parser.add_argument("--timesteps", type=int, default=1_000_000)
    parser.add_argument("--save-dir", type=str, default="trained_model")
    args = parser.parse_args()

    train_dqn(args.timesteps, args.save_dir)
