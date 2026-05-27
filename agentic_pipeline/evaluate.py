"""
evaluate.py
───────────
Evaluate a trained PPO model on the test split and produce
a detailed accuracy report with per-action breakdowns and
a confusion matrix saved as a PNG.

Usage:
    python evaluate.py
    python evaluate.py --model trained_model/cpy_agent.zip
"""

import argparse
import os
import sys
from collections import Counter, defaultdict

import numpy as np

from stable_baselines3 import PPO

from dataset_loader import (
    load_dataset, train_test_split,
    ACTION_LABELS, ID_TO_ACTION, NUM_ACTIONS,
)
from feature_encoder import encode


def evaluate(model_path: str):
    """Load model, run on test set, print report."""

    print("=" * 60)
    print("  CPY Agentic Compiler -- Evaluation Report")
    print("=" * 60)

    # ── Load ──────────────────────────────────────────────────
    print(f"\nLoading model from: {model_path}")
    model = PPO.load(model_path)

    print("Loading dataset...")
    all_data = load_dataset()
    _, test_data = train_test_split(all_data)
    print(f"  Test set size: {len(test_data)}")

    # ── Predict ───────────────────────────────────────────────
    correct = 0
    total = len(test_data)
    confusion = np.zeros((NUM_ACTIONS, NUM_ACTIONS), dtype=int)
    per_type_correct = defaultdict(int)
    per_type_total = defaultdict(int)
    per_action_correct = defaultdict(int)
    per_action_total = defaultdict(int)

    for entry in test_data:
        obs = encode(
            entry.original_code,
            entry.error_type,
            entry.error_message,
            entry.error_line,
        )

        pred_action, _ = model.predict(obs, deterministic=True)
        pred_action = int(pred_action)
        true_action = entry.target_action_id

        confusion[true_action][pred_action] += 1

        if pred_action == true_action:
            correct += 1
            per_type_correct[entry.error_type] += 1
            per_action_correct[entry.target_action] += 1

        per_type_total[entry.error_type] += 1
        per_action_total[entry.target_action] += 1

    # ── Overall accuracy ──────────────────────────────────────
    acc = correct / total * 100
    print(f"\n{'-' * 40}")
    print(f"  Overall Accuracy: {acc:.1f}% ({correct}/{total})")
    print(f"{'-' * 40}")

    # ── Per error-type accuracy ───────────────────────────────
    print(f"\n  Per Error-Type Accuracy:")
    for etype in ["Lexical", "Syntactic", "Semantic"]:
        c = per_type_correct[etype]
        t = per_type_total[etype]
        a = c / t * 100 if t > 0 else 0
        bar = "#" * int(a / 5) + "." * (20 - int(a / 5))
        print(f"    {etype:12s}  {bar}  {a:5.1f}%  ({c}/{t})")

    # ── Per action accuracy ───────────────────────────────────
    print(f"\n  Per Action Accuracy:")
    for action in ACTION_LABELS:
        c = per_action_correct[action]
        t = per_action_total[action]
        a = c / t * 100 if t > 0 else 0
        bar = "#" * int(a / 5) + "." * (20 - int(a / 5))
        print(f"    {action:25s}  {bar}  {a:5.1f}%  ({c}/{t})")

    # ── Confusion matrix (text) ───────────────────────────────
    print(f"\n  Confusion Matrix (rows=true, cols=predicted):")
    header = "  " + " " * 12
    for i in range(NUM_ACTIONS):
        header += f" {i:>4}"
    print(header)
    for i in range(NUM_ACTIONS):
        row = f"  {i:>2} {ACTION_LABELS[i][:8]:>8s}"
        for j in range(NUM_ACTIONS):
            row += f" {confusion[i][j]:>4}"
        print(row)

    # ── Save confusion matrix as image ────────────────────────
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(confusion, cmap="Blues")

        short_labels = [l[:12] for l in ACTION_LABELS]
        ax.set_xticks(range(NUM_ACTIONS))
        ax.set_yticks(range(NUM_ACTIONS))
        ax.set_xticklabels(short_labels, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(short_labels, fontsize=8)
        ax.set_xlabel("Predicted Action")
        ax.set_ylabel("True Action")
        ax.set_title(f"CPY Agent Confusion Matrix - Accuracy: {acc:.1f}%")

        # Add text annotations
        for i in range(NUM_ACTIONS):
            for j in range(NUM_ACTIONS):
                val = confusion[i][j]
                if val > 0:
                    color = "white" if val > confusion.max() * 0.5 else "black"
                    ax.text(j, i, str(val), ha="center", va="center",
                            color=color, fontsize=7)

        fig.colorbar(im)
        plt.tight_layout()

        out_path = os.path.join(os.path.dirname(model_path), "confusion_matrix.png")
        plt.savefig(out_path, dpi=150)
        plt.close()
        print(f"\n  Confusion matrix saved to: {out_path}")

    except ImportError:
        print("\n  (matplotlib not installed — skipping confusion matrix image)")

    print(f"\n{'=' * 60}")
    print(f"  Evaluation complete!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the trained CPY agent")
    parser.add_argument("--model", type=str, default="trained_model/cpy_agent.zip",
                        help="Path to the trained model .zip file")
    args = parser.parse_args()

    evaluate(args.model)
