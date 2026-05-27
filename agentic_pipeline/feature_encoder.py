"""
feature_encoder.py
──────────────────
Converts a (code, error_type, error_message, error_line) tuple
into a fixed-size numeric feature vector that Stable-Baselines3
can consume as the observation.

Feature vector layout  (25 dimensions):
  [0-2]   error_type one-hot   (Lexical / Syntactic / Semantic)
  [3-14]  error_message keyword flags
  [15]    normalised error_line
  [16-24] code structural features
"""

import numpy as np

OBSERVATION_SIZE = 25

# ── Error-message keywords to detect ──────────────────────────
_MSG_KEYWORDS = [
    ";",             # 0  → semicolon related
    ")",             # 1  → closing paren
    "}",             # 2  → closing brace
    "]",             # 3  → closing bracket
    "declaration",   # 4  → variable declaration context
    "already",       # 5  → duplicate declaration
    "before",        # 6  → used before declaration
    "character",     # 7  → unexpected character (lexical)
    "unterminated",  # 8  → unterminated string/char
    "string",        # 9  → string related
    "array",         # 10 → array related
    "expression",    # 11 → expression context
]


def encode(
    original_code: str,
    error_type: str,
    error_message: str,
    error_line: int,
) -> np.ndarray:
    """Return a float32 vector of shape ``(OBSERVATION_SIZE,)``."""

    vec = np.zeros(OBSERVATION_SIZE, dtype=np.float32)

    # ── 1. Error-type one-hot (dims 0-2) ──────────────────────
    if error_type == "Lexical":
        vec[0] = 1.0
    elif error_type == "Syntactic":
        vec[1] = 1.0
    elif error_type == "Semantic":
        vec[2] = 1.0

    # Remove the "(got ...)" suffix from the error message so its punctuation
    # doesn't confuse the keyword detectors (e.g. thinking a closing parenthesis
    # is missing because the compiler said "(got 'a')")
    import re
    msg_cleaned = re.sub(r"\(got[^\)]+\)", "", error_message)
    msg_lower = msg_cleaned.lower()
    for i, kw in enumerate(_MSG_KEYWORDS):
        if kw.lower() in msg_lower:
            vec[3 + i] = 1.0

    # ── 3. Normalised error line (dim 15) ─────────────────────
    lines = original_code.split("\n")
    num_lines = max(len(lines), 1)
    vec[15] = error_line / num_lines  # ratio 0..1+

    # ── 4. Code structural features (dims 16-24) ─────────────
    code_lower = original_code.lower()
    vec[16] = min(num_lines / 15.0, 1.0)         # normalised length
    vec[17] = 1.0 if "let " in code_lower else 0.0
    vec[18] = 1.0 if "if " in code_lower or "if(" in code_lower else 0.0
    vec[19] = 1.0 if "while " in code_lower or "while(" in code_lower else 0.0
    vec[20] = 1.0 if "for " in code_lower or "for(" in code_lower else 0.0
    vec[21] = 1.0 if "print" in code_lower else 0.0
    vec[22] = 1.0 if "[" in original_code else 0.0
    vec[23] = 1.0 if '"' in original_code else 0.0
    vec[24] = min(original_code.count(";") / 10.0, 1.0)  # normalised semicolons

    return vec


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    sample_vec = encode(
        original_code="let x = 10\nprint(x);",
        error_type="Syntactic",
        error_message="Expected ';' after expression",
        error_line=1,
    )
    print(f"Feature vector (shape {sample_vec.shape}):")
    print(sample_vec)
