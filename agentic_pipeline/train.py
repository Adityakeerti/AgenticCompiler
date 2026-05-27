"""
train.py  (v2 -- GPU + VecNormalize + Deeper MLP + Curriculum)
--------------------------------------------------------------
Upgrades over v1:
  - device='cuda' (RTX 4050 6GB)
  - VecNormalize wrapper (running mean/std normalization of observations)
  - 3-layer MLP [256, 256, 128]  (up from [128, 128])
  - 8 parallel DummyVecEnv environments
  - 1,000,000 default timesteps (up from 100k)
  - batch_size=512, n_steps=1024
  - EvalCallback -> auto-saves best model checkpoint
  - TensorBoard logging   (run: tensorboard --logdir ./tb_logs)
  - --curriculum flag for staged complexity training
  - --live flag to use real Java compiler (see compiler_env_live.py)

Usage:
    python train.py                          # 1M steps, GPU, oracle dataset
    python train.py --timesteps 500000
    python train.py --curriculum             # start easy, unlock harder gradually
    python train.py --live                   # use real Java compiler (slow but real)
"""

import argparse
import os
import sys
import time

import torch
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import EvalCallback, BaseCallback

from dataset_loader import load_dataset, train_test_split, filter_by_complexity
from compiler_env import CPYCompilerEnv


# ── Custom progress callback ─────────────────────────────────────────────────
class ProgressCallback(BaseCallback):
    """Print a rolling accuracy line every *print_freq* steps."""

    def __init__(self, print_freq: int = 10000, verbose: int = 0):
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


# ── Curriculum training ──────────────────────────────────────────────────────
def run_curriculum(model, train_data, eval_env, vec_norm, save_dir: str,
                   total_timesteps: int, progress_cb):
    """
    Curriculum learning: train on easy samples first, unlock harder ones
    once the agent achieves 95% accuracy on the current stage.

    Stages:
      1. short only          (1/3 of steps)
      2. short + medium      (1/3 of steps)
      3. all complexities    (1/3 of steps)
    """
    stages = [
        (['short'],                   "Stage 1/3: short only"),
        (['short', 'medium'],         "Stage 2/3: short + medium"),
        (['short', 'medium', 'long'], "Stage 3/3: all complexities"),
    ]
    steps_per_stage = total_timesteps // len(stages)

    for complexities, label in stages:
        stage_data = filter_by_complexity(train_data, complexities)
        print(f"\n[CURRICULUM] {label}  ({len(stage_data):,} samples)")

        # Re-create training envs with the filtered dataset
        def make_stage_env():
            return CPYCompilerEnv(dataset=stage_data)

        stage_vec = DummyVecEnv([make_stage_env] * 8)
        stage_vec = VecNormalize(stage_vec, norm_obs=True, norm_reward=False,
                                 clip_obs=10.0, gamma=0.99)

        # Transfer normalization stats from previous stage if possible
        if vec_norm is not None:
            stage_vec.obs_rms = vec_norm.obs_rms
            stage_vec.ret_rms = vec_norm.ret_rms

        model.set_env(stage_vec)
        model.learn(total_timesteps=steps_per_stage, callback=progress_cb,
                    reset_num_timesteps=False, progress_bar=False)

        vec_norm = stage_vec  # carry stats forward

    return vec_norm


# ── Main training function ───────────────────────────────────────────────────
def train(timesteps: int, learning_rate: float, save_dir: str,
          curriculum: bool, live: bool):

    print("=" * 60)
    print("  CPY Agentic Compiler -- RL Training v2")
    print("=" * 60)

    # ── GPU check ────────────────────────────────────────────────
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        print(f"\n[GPU] Using: {gpu_name}")
    else:
        print("\n[GPU] CUDA not available, using CPU")

    # ── Load data ─────────────────────────────────────────────────
    print("\n[1/4] Loading dataset...")
    all_data = load_dataset()
    train_data, test_data = train_test_split(all_data)
    print(f"  Total: {len(all_data):,} | Train: {len(train_data):,} | Test: {len(test_data):,}")

    # ── Create environments ───────────────────────────────────────
    print("\n[2/4] Creating environments...")

    if live:
        from compiler_env_live import CPYCompilerEnvLive
        print("  [LIVE] Using real Java compiler for training (slow but real-world accurate)")
        def make_train_env():
            return CPYCompilerEnvLive(dataset=train_data)
        def make_eval_env():
            return CPYCompilerEnvLive(dataset=test_data)
    else:
        def make_train_env():
            return CPYCompilerEnv(dataset=train_data)
        def make_eval_env():
            return CPYCompilerEnv(dataset=test_data)

    # 8 parallel envs (DummyVecEnv is fast for our lightweight oracle env)
    n_envs = 8
    train_vec = DummyVecEnv([make_train_env] * n_envs)

    # VecNormalize: running mean/std normalization of observations
    train_vec = VecNormalize(train_vec, norm_obs=True, norm_reward=False,
                             clip_obs=10.0, gamma=0.99)

    raw_eval_env = make_eval_env()

    print(f"  Training envs: {n_envs} parallel (DummyVecEnv + VecNormalize)")
    print(f"  Observation space: {raw_eval_env.observation_space}")
    print(f"  Action space: {raw_eval_env.action_space} ({raw_eval_env.action_space.n} fix actions)")
    print(f"  Device: {device}")

    # ── Build PPO agent ───────────────────────────────────────────
    print("\n[3/4] Building PPO agent...")

    os.makedirs("tb_logs", exist_ok=True)

    model = PPO(
        policy="MlpPolicy",
        env=train_vec,
        learning_rate=learning_rate,
        n_steps=1024,
        batch_size=512,
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.05,
        clip_range=0.2,
        verbose=0,
        device=device,
        tensorboard_log="./tb_logs",
        policy_kwargs=dict(
            net_arch=[256, 256, 128],   # 3 layers: deeper than v1 [128, 128]
        ),
    )

    total_params = sum(p.numel() for p in model.policy.parameters())
    print(f"  Policy network: [256, 256, 128] (3 hidden layers)")
    print(f"  Total parameters: {total_params:,}")
    print(f"  Learning rate: {learning_rate}")
    print(f"  Batch size: 512  |  n_steps: 1024  |  Parallel envs: {n_envs}")
    print(f"  Training steps: {timesteps:,}")

    # ── Train ─────────────────────────────────────────────────────
    print(f"\n[4/4] Training for {timesteps:,} steps...")
    print("-" * 60)

    progress_cb = ProgressCallback(print_freq=10000)

    # EvalCallback: auto-saves the best model seen during training
    os.makedirs(save_dir, exist_ok=True)
    eval_vec = DummyVecEnv([make_eval_env])
    # Sync normalization stats with training env before evaluation
    eval_vec = VecNormalize(eval_vec, norm_obs=True, norm_reward=False,
                            clip_obs=10.0, gamma=0.99, training=False)

    eval_cb = EvalCallback(
        eval_vec,
        best_model_save_path=os.path.join(save_dir, "best"),
        log_path=os.path.join(save_dir, "eval_logs"),
        eval_freq=max(50_000 // n_envs, 1),
        n_eval_episodes=500,
        deterministic=True,
        verbose=1,
    )

    if curriculum:
        print("  [CURRICULUM MODE] Training in 3 complexity stages")
        final_vec_norm = run_curriculum(
            model, train_data, raw_eval_env, train_vec, save_dir,
            timesteps, progress_cb
        )
        train_vec = final_vec_norm
    else:
        model.learn(
            total_timesteps=timesteps,
            callback=[progress_cb, eval_cb],
            progress_bar=False,
        )

    print("-" * 60)

    # ── Save model + normalization stats ─────────────────────────
    model_path = os.path.join(save_dir, "cpy_agent")
    model.save(model_path)
    print(f"\n[OK] Model saved to: {model_path}.zip")

    norm_path = os.path.join(save_dir, "vec_normalize.pkl")
    train_vec.save(norm_path)
    print(f"[OK] Normalization stats saved to: {norm_path}")

    # ── Quick evaluation ──────────────────────────────────────────
    print("\nRunning quick evaluation on test set...")
    correct = 0
    total = min(len(test_data), 3000)
    raw_eval_env2 = make_eval_env()
    for i in range(total):
        obs, _ = raw_eval_env2.reset()
        # Apply normalization manually for standalone evaluation
        obs_norm = train_vec.normalize_obs(obs)
        action, _ = model.predict(obs_norm, deterministic=True)
        _, _, _, _, info = raw_eval_env2.step(int(action))
        if info["was_correct"]:
            correct += 1

    acc = correct / total * 100
    print(f"  Test accuracy: {acc:.1f}% ({correct}/{total})")

    raw_eval_env.close()
    raw_eval_env2.close()
    train_vec.close()

    print(f"\n{'=' * 60}")
    print(f"  Training complete!")
    print(f"  TensorBoard: tensorboard --logdir ./tb_logs")
    print(f"{'=' * 60}")

    return model_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the CPY RL agent (v2)")
    parser.add_argument("--timesteps", type=int, default=1_000_000,
                        help="Total training timesteps (default: 1,000,000)")
    parser.add_argument("--lr", type=float, default=3e-4,
                        help="Learning rate (default: 0.0003)")
    parser.add_argument("--save-dir", type=str, default="trained_model",
                        help="Directory to save model + normalization stats")
    parser.add_argument("--curriculum", action="store_true",
                        help="Enable curriculum learning (short -> medium -> long)")
    parser.add_argument("--live", action="store_true",
                        help="Use real Java compiler for training (slow, accurate)")
    args = parser.parse_args()

    train(args.timesteps, args.lr, args.save_dir, args.curriculum, args.live)
