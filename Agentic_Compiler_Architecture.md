# Agentic Compiler Architecture: Deep Dive

This document provides a comprehensive technical overview of the RL-based Agentic Compiler for the CPY language. It details the end-to-end pipeline from synthetic dataset generation and state encoding to Reinforcement Learning (RL) training using Proximal Policy Optimization (PPO) and the final inference loop.

---

## 1. System Overview
The Agentic Compiler is an autonomous code-repair system that wraps a standard deterministic compiler (Java CPY Compiler). Instead of just reporting errors to the user, the system intercepts the errors, encodes the context into a numerical state vector, feeds it to a trained neural network, and applies the predicted fix back to the source code.

**The Inference Loop:**
1. **Compile:** The Java compiler attempts to compile the `.cpy` file.
2. **Detect:** If it fails, the Python wrapper extracts the `error_type`, `error_message`, and `error_line`.
3. **Encode:** The context is converted into a 25-dimensional float vector.
4. **Predict:** The PPO agent performs a forward pass and outputs a discrete action ID (0-8).
5. **Apply:** A deterministic heuristic applies the fix to the source code string.
6. **Loop:** Repeat up to `MAX_ITERATIONS` (5) until compilation succeeds.

---

## 2. The Synthetic Dataset Pipeline (`generate_dataset.py`)
Training an RL agent by continuously calling a Java subprocess is computationally bottlenecked. To solve this, we use a **Synthetic Oracle Dataset** for rapid, off-line simulated environment training.

### Mutation Operators
The generator first creates perfectly valid AST-compliant CPY code (templates of varying complexities). It then applies specific inverse-mutations to inject faults:
- **Lexical:** Injecting illegal characters (e.g., `$`) or removing closing quotes.
- **Syntactic:** Stripping specific tokens like `;`, `)`, or `}`.
- **Semantic:** Stripping `let` to force "used before declaration", duplicating `let`, or treating a scalar as an array.

### Dataset Balancing
The dataset contains exactly 10,000 rows. In Machine Learning, highly imbalanced classes lead to mode collapse. The dataset forces a perfect 1:1:1 distribution across Lexical, Syntactic, and Semantic errors, and evenly distributes short, medium, and long code lengths to ensure the model generalizes across code complexity.

---

## 3. RL Environment Formulation (`compiler_env.py`)
We map the code-repair problem to a Markov Decision Process (MDP) using the standard **Gymnasium** API. 

*Note: During training, instead of running the slow Java compiler, the environment uses the synthetic dataset as an "Oracle" to instantly verify if the agent's action matches the intended target action.*

### Observation Space (State)
`Box(-1.0, 2.0, (25,), float32)`
A continuous 25-dimensional vector representing the code and error context.

### Action Space
`Discrete(9)`
A discrete integer representing which of the 9 specific repair heuristics to apply.

### Reward Function
- **+10** for choosing the correct fix action.
- **-1** for choosing an incorrect action.
- Episode terminates immediately after 1 step (this is formulated as a Contextual Bandit problem during training, as the dataset acts as a single-step oracle).

---

## 4. Feature Encoding (`feature_encoder.py`)
Neural networks cannot read raw text natively. The `feature_encoder.py` bridges the gap between text/code and numerical representations without using heavy Transformers (LLMs), ensuring the agent stays lightning-fast.

The 25-dimensional vector is divided into four conceptual blocks:
1. **Error Type One-Hot (Dims 0-2):** Is it Lexical, Syntactic, or Semantic?
2. **Message Bag-of-Words (Dims 3-14):** A binary flag array checking for the presence of highly correlated keywords in the error message (e.g., `";"`, `"unterminated"`, `"already"`). *Crucially, we use Regex to strip compiler-specific punctuation like `(got 'a')` to prevent dataset distribution shifts.*
3. **Spatial Awareness (Dim 15):** The normalized error line `(error_line / total_lines)`. Does the error happen at the start, middle, or EOF?
4. **Code Structural Features (Dims 16-24):** Checks the target code string for the presence of language keywords (`let`, `if`, `while`), symbols (`[`, `"`), and normalized length. 

---

## 5. The Reinforcement Learning Agent (`train.py`)
We use **Proximal Policy Optimization (PPO)** from the `Stable-Baselines3` library. 

### Why PPO?
PPO is an actor-critic method that is currently the industry standard for RL (used heavily by OpenAI). It strikes the perfect balance between sample efficiency, stability, and tuning simplicity. It excels in environments with discrete action spaces and dense rewards.

### Neural Network Architecture
The agent uses a standard Multi-Layer Perceptron (MLP) Policy:
- **Input:** 25 neurons (Observation Space)
- **Hidden Layer 1:** 128 neurons (ReLU activation)
- **Hidden Layer 2:** 128 neurons (ReLU activation)
- **Output (Actor):** 9 neurons (Softmax probabilities for Action Space)
- **Output (Critic):** 1 neuron (Value estimation of the state)
- **Total Parameters:** ~40,970 (Extremely lightweight, running inference in <1ms on CPU).

---

## 6. Deterministic Fix Application (`fix_applier.py`)
Once the Neural Network outputs a classification (e.g., Action `0`), it maps to a specific string manipulation function (e.g., `_insert_semicolon()`).

**Algorithmic Upwards Scanning:** 
Compilers frequently report errors one token *after* the actual mistake (e.g., reporting a missing semicolon on line 5 because it encountered `let` when it was expecting `;` after line 4). The `fix_applier` contains deterministic algorithms to scan *upwards* from the compiler's reported line to find the true source of the syntax error.

---

## 7. Future Scope

The current system (Tier 1) is a strong, fully functional RL-based compiler agent. The following upgrades represent natural research progressions — each one is an independent, publishable experiment in AIML.

---

### Tier 2 — Algorithm Comparison: DQN vs PPO

**Files created:** `train_dqn.py`, `compare_algorithms.py`

PPO is an **on-policy** algorithm — it collects a batch of experience, updates once, and throws the data away. This is wasteful.

**DQN (Deep Q-Network)** is **off-policy**: it stores every experience in a large **Replay Buffer** and randomly samples from it for every gradient update. This means the agent learns from each data point many times, making it 3–5x more sample-efficient for discrete classification tasks like ours.

**Key DQN components:**
- **Replay Buffer** (`buffer_size=100,000`): stores `(state, action, reward, next_state)` tuples. Breaks temporal correlation between consecutive steps, which stabilizes learning.
- **Target Network**: a frozen copy of the Q-network updated every 1,000 steps. Prevents the "moving target" problem where both the predicted Q-values and the target Q-values change simultaneously (a major source of training instability in standard DQN).
- **Epsilon-Greedy Exploration**: starts fully random (`eps=1.0`), decays to `0.05` over time. Ensures the agent explores enough early on.

**Expected result:** DQN should significantly outperform PPO on the `INSERT_RBRACE` action, because its replay buffer will oversample rare difficult examples automatically, balancing the learned Q-values.

**To run (after current demo):**
```bash
python train_dqn.py
python compare_algorithms.py
```

---

### Tier 3 — Real Multi-Step MDP with Live Compiler

**File created:** `compiler_env_live.py`

This is the most academically significant upgrade. Currently, the agent trains entirely on a **synthetic oracle CSV** — it never sees the actual Java compiler's error messages during training. This is called **dataset distribution shift**: the agent learned from simplified error strings but encounters richer, more complex strings at inference time.

`compiler_env_live.py` replaces the oracle with the **real Java CPY compiler subprocess** at every training step. This changes the problem from a simple contextual bandit (single-step classification) into a **true sequential MDP**:

**Episode flow (up to 5 steps):**
1. Pick a broken CPY snippet
2. Compile with real Java → get actual error string
3. Encode to 25-dim vector → agent predicts action
4. Apply fix → recompile
5. Give reward based on success/progress → repeat

**Reward shaping:**
| Event | Reward |
|-------|--------|
| Code compiles successfully | `+10.0 - (steps * 0.5)` |
| Error type changed (forward progress) | `+1.0` |
| No progress (same error) | `-0.5` |
| Exhausted all 5 steps | `-5.0` |

The `+1.0` for error type changes is called a **potential-based reward shaping** — it guides the agent without altering the optimal policy (proven safe by the reward shaping invariance theorem).

**To run (after current demo):**
```bash
python train.py --live --timesteps 200000
```

> Note: live training is ~50x slower than oracle training because each step spawns a Java subprocess. For a demo, run with `--timesteps 50000` first.

---

### Tier 4 — Curriculum Learning + TensorBoard

**Curriculum Learning** is a well-established technique in AIML: start with easy examples, gradually introduce harder ones. This prevents the agent from getting stuck on hard examples before it has learned the basics.

**Stages in our system:**
| Stage | Data | Timesteps |
|-------|------|-----------|
| 1 | Short snippets only (1–3 lines) | 33% of total |
| 2 | Short + Medium (1–8 lines) | 33% of total |
| 3 | All complexities | 33% of total |

This is implemented in `train.py` via the `--curriculum` flag. Run it as:
```bash
python train.py --curriculum --timesteps 1000000
```

**TensorBoard** is the industry-standard training dashboard. It records metrics like:
- `rollout/ep_rew_mean` — average reward per episode (rising = agent improving)
- `train/entropy_loss` — how exploratory the agent is (should start high, decay)
- `train/value_loss` — how accurately the critic estimates future rewards
- `eval/mean_reward` — performance on held-out evaluation set

Launch the dashboard:
```bash
.\launch_tensorboard.bat
# Then open: http://localhost:6006
```

