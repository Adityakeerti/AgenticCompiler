"""
dataset_loader.py
─────────────────
Loads the CPY error-correction CSV dataset and provides
convenient access for the RL environment and evaluation.
"""

import csv
import os
import random


# ── Action label ↔ integer mapping ────────────────────────────
ACTION_LABELS = [
    "INSERT_SEMICOLON",      # 0
    "DELETE_CHAR_AT_INDEX",   # 1
    "INSERT_QUOTE",          # 2
    "INSERT_CHAR",           # 3
    "INSERT_RPAREN",         # 4
    "INSERT_RBRACE",         # 5
    "PREPEND_LET",           # 6
    "REMOVE_LET_OR_RENAME",  # 7
    "MAKE_ARRAY",            # 8
]

ACTION_TO_ID = {label: idx for idx, label in enumerate(ACTION_LABELS)}
ID_TO_ACTION = {idx: label for idx, label in enumerate(ACTION_LABELS)}
NUM_ACTIONS = len(ACTION_LABELS)


class DatasetEntry:
    """One row from the CSV dataset."""

    def __init__(self, row: dict):
        self.id = int(row["id"])
        self.original_code = row["original_code"]
        self.error_type = row["error_type"]
        self.error_message = row["error_message"]
        self.error_line = int(row["error_line"])
        self.target_action = row["target_action"]
        self.target_action_id = ACTION_TO_ID.get(self.target_action, -1)
        self.fixed_code = row["fixed_code"]
        # complexity column added in v2 of the dataset (infer if missing)
        if "complexity" in row and row["complexity"]:
            self.complexity = row["complexity"]
        else:
            self.complexity = self._infer_complexity()

    def _infer_complexity(self) -> str:
        n = len([l for l in self.original_code.split('\n') if l.strip()])
        if n <= 3:
            return 'short'
        elif n <= 8:
            return 'medium'
        else:
            return 'long'

    def __repr__(self):
        return (
            f"DatasetEntry(id={self.id}, "
            f"error_type={self.error_type!r}, "
            f"action={self.target_action!r}, "
            f"complexity={self.complexity!r})"
        )


def load_dataset(csv_path: str | None = None) -> list[DatasetEntry]:
    """
    Load the full dataset from CSV.  Falls back to
    ``../cpy_error_dataset.csv`` relative to this file.
    """
    if csv_path is None:
        csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "cpy_error_dataset.csv",
        )

    entries: list[DatasetEntry] = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = DatasetEntry(row)
            if entry.target_action_id >= 0:
                entries.append(entry)

    return entries


def train_test_split(
    entries: list[DatasetEntry],
    test_ratio: float = 0.2,
    seed: int = 42,
) -> tuple[list[DatasetEntry], list[DatasetEntry]]:
    """Deterministic train / test split."""
    rng = random.Random(seed)
    shuffled = list(entries)
    rng.shuffle(shuffled)
    split = int(len(shuffled) * (1 - test_ratio))
    return shuffled[:split], shuffled[split:]


def filter_by_complexity(
    entries: list[DatasetEntry],
    complexities: list[str],
) -> list[DatasetEntry]:
    """Filter dataset by complexity level(s). Used for curriculum learning."""
    allowed = set(complexities)
    return [e for e in entries if e.complexity in allowed]


# ── Quick sanity check ────────────────────────────────────────
if __name__ == "__main__":
    data = load_dataset()
    print(f"Loaded {len(data)} entries")

    # Distribution
    from collections import Counter
    type_counts = Counter(e.error_type for e in data)
    action_counts = Counter(e.target_action for e in data)

    print("\nError-type distribution:")
    for k, v in type_counts.most_common():
        print(f"  {k}: {v}")

    print("\nAction distribution:")
    for k, v in action_counts.most_common():
        print(f"  {k}: {v}")

    print(f"\nSample entry: {data[0]}")
    print(f"  original_code (first 80 chars): {data[0].original_code[:80]!r}")
