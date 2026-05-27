"""
compare_algorithms.py
---------------------
Load the trained PPO and DQN models and produce a side-by-side
accuracy comparison on the same test holdout set.

Generates:
  - Console table with per-action accuracy for each algorithm
  - trained_model/algorithm_comparison.png  (bar chart)

Usage:
    python compare_algorithms.py
    python compare_algorithms.py --ppo trained_model/cpy_agent.zip --dqn trained_model/cpy_agent_dqn.zip
"""

import argparse
import os
from collections import defaultdict

import numpy as np

from stable_baselines3 import PPO, DQN
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from dataset_loader import load_dataset, train_test_split, ACTION_LABELS, ID_TO_ACTION
from feature_encoder import encode
from compiler_env import CPYCompilerEnv


def evaluate_model(model, test_data, norm_stats_path=None):
    """Run model on test set, return per-action accuracy dict."""
    per_action_correct = defaultdict(int)
    per_action_total = defaultdict(int)
    per_type_correct = defaultdict(int)
    per_type_total = defaultdict(int)
    correct_total = 0

    # Load normalization stats if available (for PPO)
    vec_norm = None
    if norm_stats_path and os.path.exists(norm_stats_path):
        dummy_vec = DummyVecEnv([lambda: CPYCompilerEnv(dataset=test_data)])
        vec_norm = VecNormalize.load(norm_stats_path, dummy_vec)
        vec_norm.training = False
        vec_norm.norm_reward = False

    for entry in test_data:
        obs = encode(
            entry.original_code,
            entry.error_type,
            entry.error_message,
            entry.error_line,
        )

        if vec_norm is not None:
            obs_input = vec_norm.normalize_obs(obs)
        else:
            obs_input = obs

        pred_action, _ = model.predict(obs_input, deterministic=True)
        pred_action = int(pred_action)
        true_action = entry.target_action_id
        is_correct = pred_action == true_action

        if is_correct:
            correct_total += 1
            per_action_correct[entry.target_action] += 1
            per_type_correct[entry.error_type] += 1

        per_action_total[entry.target_action] += 1
        per_type_total[entry.error_type] += 1

    if vec_norm:
        vec_norm.close()

    return {
        "overall": correct_total / len(test_data) * 100,
        "per_action_correct": dict(per_action_correct),
        "per_action_total": dict(per_action_total),
        "per_type_correct": dict(per_type_correct),
        "per_type_total": dict(per_type_total),
    }


def print_comparison_table(ppo_results, dqn_results, test_size):
    """Print a formatted comparison table to the console."""
    print("\n" + "=" * 72)
    print(f"  ALGORITHM COMPARISON  (Test set: {test_size:,} samples)")
    print("=" * 72)
    print(f"  {'Metric':<28}  {'PPO':>10}  {'DQN':>10}  {'Winner':>10}")
    print("-" * 72)

    # Overall
    ppo_oa = ppo_results["overall"]
    dqn_oa = dqn_results["overall"]
    winner = "PPO" if ppo_oa > dqn_oa else ("DQN" if dqn_oa > ppo_oa else "TIE")
    print(f"  {'Overall Accuracy':<28}  {ppo_oa:>9.1f}%  {dqn_oa:>9.1f}%  {winner:>10}")
    print("-" * 72)

    # Per error type
    for etype in ["Lexical", "Syntactic", "Semantic"]:
        pc = ppo_results["per_type_correct"].get(etype, 0)
        pt = ppo_results["per_type_total"].get(etype, 1)
        dc = dqn_results["per_type_correct"].get(etype, 0)
        dt = dqn_results["per_type_total"].get(etype, 1)
        pa = pc / pt * 100
        da = dc / dt * 100
        winner = "PPO" if pa > da else ("DQN" if da > pa else "TIE")
        print(f"  {etype + ' errors':<28}  {pa:>9.1f}%  {da:>9.1f}%  {winner:>10}")

    print("-" * 72)
    print(f"  {'Per-Action Breakdown':<28}")
    print("-" * 72)

    for action in ACTION_LABELS:
        pc = ppo_results["per_action_correct"].get(action, 0)
        pt = ppo_results["per_action_total"].get(action, 0)
        dc = dqn_results["per_action_correct"].get(action, 0)
        dt = dqn_results["per_action_total"].get(action, 0)
        if pt == 0 and dt == 0:
            continue
        pa = pc / pt * 100 if pt > 0 else 0
        da = dc / dt * 100 if dt > 0 else 0
        winner = "PPO" if pa > da else ("DQN" if da > pa else "TIE")
        print(f"  {action:<28}  {pa:>9.1f}%  {da:>9.1f}%  {winner:>10}")

    print("=" * 72)


def save_comparison_chart(ppo_results, dqn_results, output_path):
    """Save a grouped bar chart comparing per-action accuracy."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        actions = [a for a in ACTION_LABELS
                   if ppo_results["per_action_total"].get(a, 0) > 0
                   or dqn_results["per_action_total"].get(a, 0) > 0]

        ppo_accs = []
        dqn_accs = []
        for a in actions:
            pc = ppo_results["per_action_correct"].get(a, 0)
            pt = ppo_results["per_action_total"].get(a, 1)
            dc = dqn_results["per_action_correct"].get(a, 0)
            dt = dqn_results["per_action_total"].get(a, 1)
            ppo_accs.append(pc / pt * 100 if pt > 0 else 0)
            dqn_accs.append(dc / dt * 100 if dt > 0 else 0)

        x = np.arange(len(actions))
        width = 0.35

        fig, ax = plt.subplots(figsize=(14, 6))
        bars1 = ax.bar(x - width / 2, ppo_accs, width, label=f"PPO ({ppo_results['overall']:.1f}% overall)", color="#4C72B0", alpha=0.85)
        bars2 = ax.bar(x + width / 2, dqn_accs, width, label=f"DQN ({dqn_results['overall']:.1f}% overall)", color="#DD8452", alpha=0.85)

        ax.set_xlabel("Fix Action")
        ax.set_ylabel("Accuracy (%)")
        ax.set_title("PPO vs DQN Per-Action Accuracy Comparison")
        ax.set_xticks(x)
        ax.set_xticklabels([a.replace("_", "\n") for a in actions], fontsize=8)
        ax.set_ylim(0, 110)
        ax.legend()
        ax.axhline(y=100, color='gray', linestyle='--', alpha=0.4)

        for bar in bars1:
            ax.annotate(f'{bar.get_height():.0f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=7)
        for bar in bars2:
            ax.annotate(f'{bar.get_height():.0f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=7)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        print(f"\n[OK] Comparison chart saved to: {output_path}")

    except ImportError:
        print("\n(matplotlib not installed -- skipping chart)")


def main(ppo_path, dqn_path, norm_stats_path):
    print("=" * 60)
    print("  CPY Agent -- Algorithm Comparison: PPO vs DQN")
    print("=" * 60)

    print("\nLoading dataset...")
    all_data = load_dataset()
    _, test_data = train_test_split(all_data)
    print(f"  Test set size: {len(test_data):,}")

    # -- Load PPO --------------------------------------------------------
    if not os.path.exists(ppo_path):
        print(f"[ERR] PPO model not found: {ppo_path}")
        print("  Run 'python train.py' first.")
        return
    print(f"\nLoading PPO model: {ppo_path}")
    ppo_model = PPO.load(ppo_path)
    print("Evaluating PPO...")
    ppo_results = evaluate_model(ppo_model, test_data, norm_stats_path)

    # -- Load DQN --------------------------------------------------------
    if not os.path.exists(dqn_path):
        print(f"[ERR] DQN model not found: {dqn_path}")
        print("  Run 'python train_dqn.py' first.")
        return
    print(f"\nLoading DQN model: {dqn_path}")
    dqn_model = DQN.load(dqn_path)
    print("Evaluating DQN...")
    dqn_results = evaluate_model(dqn_model, test_data)

    # -- Compare ---------------------------------------------------------
    print_comparison_table(ppo_results, dqn_results, len(test_data))

    chart_path = os.path.join(os.path.dirname(ppo_path), "algorithm_comparison.png")
    save_comparison_chart(ppo_results, dqn_results, chart_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare PPO and DQN agents")
    parser.add_argument("--ppo", type=str, default="trained_model/cpy_agent.zip")
    parser.add_argument("--dqn", type=str, default="trained_model/cpy_agent_dqn.zip")
    parser.add_argument("--norm-stats", type=str, default="trained_model/vec_normalize.pkl",
                        help="VecNormalize stats file from PPO training")
    args = parser.parse_args()

    main(args.ppo, args.dqn, args.norm_stats)
