# Agentic Pipeline — RL-Based CPY Error Correction

A **100% free, fully local** reinforcement learning pipeline that teaches an agent to automatically fix errors in CPY programs.

> **No paid APIs. No cloud services. Everything runs on your machine.**

---

## Architecture

```
┌──────────────┐    Error    ┌─────────────────┐    Fix    ┌─────────────┐
│ CPY Compiler │ ──────────▸ │  Agent Pipeline  │ ───────▸ │ Source Code │
│ (Java)       │             │  (Python + RL)   │          │ (.cpy file) │
└──────────────┘             └────────┬────────┘          └──────┬──────┘
       ▲                              │                          │
       │                     ┌────────▼────────┐                 │
       │                     │  RL Policy Model │                 │
       │                     │  (PPO / PyTorch) │                 │
       │                     └─────────────────┘                 │
       └─────────────────── Recompile ◀──────────────────────────┘
```

## Quick Start

### 1. Install dependencies
```bash
cd agentic_pipeline
pip install -r requirements.txt
```

### 2. Train the agent
```bash
python train.py
```
This trains a PPO agent for 100,000 steps (~2-5 minutes on CPU).
The trained model is saved to `trained_model/cpy_agent.zip`.

### 3. Evaluate accuracy
```bash
python evaluate.py
```
Prints per-error-type and per-action accuracy, plus a confusion matrix.

### 4. Run the Agentic Compiler
```bash
# Fix a .cpy file
python run_agent.py --file ../Compiler/broken_example.cpy

# Fix inline code
python run_agent.py --code "let x = 10\nprint(x)"

# Interactive mode
python run_agent.py --interactive
```

---

## File Structure

| File | Purpose |
|------|---------|
| `dataset_loader.py` | Loads the 10k-row CSV dataset |
| `feature_encoder.py` | Encodes error context → 25-dim feature vector |
| `fix_applier.py` | Applies fix actions (INSERT_SEMICOLON, etc.) to code |
| `compiler_wrapper.py` | Wraps the Java CPY compiler via subprocess |
| `compiler_env.py` | Gymnasium RL environment |
| `train.py` | PPO training script |
| `evaluate.py` | Evaluation with accuracy report + confusion matrix |
| `run_agent.py` | End-to-end agentic compiler demo |

## How It Works

1. **State**: The agent sees a 25-dimensional feature vector encoding the error type, error message keywords, and code structure.
2. **Action**: The agent picks one of 9 fix actions (e.g., `INSERT_SEMICOLON`, `PREPEND_LET`).
3. **Reward**: +1 for correct fix, −1 for wrong fix.
4. **Training**: Uses the dataset as an oracle (fast, no compiler calls needed).
5. **Inference**: Actually runs the Java compiler in a loop until the code compiles.

## Technologies (All Free & Open-Source)

- **PyTorch** — ML backend
- **Stable-Baselines3** — PPO implementation
- **Gymnasium** — RL environment framework
- **NumPy / Pandas** — Data handling
- **Matplotlib** — Visualisation
