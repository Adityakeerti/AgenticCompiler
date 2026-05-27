"""
run_agent.py
────────────
End-to-end demo: feed a broken .cpy file (or raw code string)
to the trained RL agent, which iteratively predicts fixes and
recompiles until the code compiles or a max iteration limit is hit.

This is the **Agentic Compiler** in action — the full
compile → detect → fix → recompile loop from the architecture.

Usage:
    python run_agent.py --file broken.cpy
    python run_agent.py --code "let x = 10\nprint(x)"
    python run_agent.py --interactive
"""

import argparse
import os
import sys

from stable_baselines3 import PPO

from dataset_loader import ID_TO_ACTION
from feature_encoder import encode
from fix_applier import apply_fix
from compiler_wrapper import compile_code, CompileResult


MAX_ITERATIONS = 5
DEFAULT_MODEL = "trained_model/cpy_agent.zip"


def run_agent(source_code: str, model_path: str, verbose: bool = True) -> str:
    """
    Given broken CPY *source_code*, iteratively apply the RL agent
    to fix it.  Returns the (hopefully) fixed code.
    """
    model = PPO.load(model_path)

    if verbose:
        print("=" * 60)
        print("  [*] CPY Agentic Compiler")
        print("=" * 60)
        print(f"\n[INPUT] Original code:\n{'-' * 40}")
        print(source_code)
        print(f"{'-' * 40}\n")

    current_code = source_code

    for iteration in range(1, MAX_ITERATIONS + 1):
        if verbose:
            print(f"[ITER] Iteration {iteration}/{MAX_ITERATIONS}")

        # Step 1: Compile
        result = compile_code(current_code)

        if result.success:
            if verbose:
                print(f"  [OK] Compilation SUCCESSFUL!")
                print(f"\n[OUTPUT] Fixed code:\n{'-' * 40}")
                print(current_code)
                print(f"{'-' * 40}")
            return current_code

        if verbose:
            print(f"  [ERR] Compiler error: {result.error_message}")
            print(f"     Error type: {result.error_type}, Line: {result.error_line}")

        # Step 2: Encode the error context
        obs = encode(
            current_code,
            result.error_type,
            result.error_message,
            result.error_line,
        )

        # Step 3: Agent predicts an action
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)
        action_label = ID_TO_ACTION.get(action, "UNKNOWN")

        if verbose:
            print(f"  [AGENT] Agent predicts: {action_label}")

        # Step 4: Apply the fix
        current_code = apply_fix(
            current_code,
            result.error_line,
            action_label,
            result.error_message,
        )

        if verbose:
            print(f"  [FIX] Fix applied.\n")

    # If we exhausted iterations, try one final compile
    result = compile_code(current_code)
    if result.success:
        if verbose:
            print(f"[OK] Compilation SUCCESSFUL after {MAX_ITERATIONS} iterations!")
            print(f"\n[OUTPUT] Fixed code:\n{'-' * 40}")
            print(current_code)
            print(f"{'-' * 40}")
        return current_code

    if verbose:
        print(f"\n[WARN] Could not fix the code after {MAX_ITERATIONS} iterations.")
        print(f"   Last error: {result.error_message}")
        print(f"\n[OUTPUT] Current state of code:\n{'-' * 40}")
        print(current_code)
        print(f"{'-' * 40}")

    return current_code


def interactive_mode(model_path: str):
    """Interactive REPL where user types CPY code and agent fixes it."""
    print("=" * 60)
    print("  [*] CPY Agentic Compiler -- Interactive Mode")
    print("=" * 60)
    print("Type your CPY code below (enter an empty line to submit).")
    print("Type 'quit' or 'exit' to leave.\n")

    while True:
        print(">>> Enter CPY code (empty line to submit):")
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line == "":
                break
            if line.lower() in ("quit", "exit"):
                print("Goodbye!")
                return
            lines.append(line)

        if not lines:
            continue

        code = "\n".join(lines)
        print()
        run_agent(code, model_path, verbose=True)
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the CPY Agentic Compiler on broken code"
    )
    parser.add_argument("--file", type=str, help="Path to a .cpy file to fix")
    parser.add_argument("--code", type=str, help="Raw CPY code string to fix")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help="Path to trained model .zip")
    parser.add_argument("--interactive", action="store_true",
                        help="Enter interactive mode")
    args = parser.parse_args()

    if not os.path.exists(args.model):
        print(f"[ERR] Model not found at: {args.model}")
        print("   Run 'python train.py' first to train the agent.")
        sys.exit(1)

    if args.interactive:
        interactive_mode(args.model)

    elif args.file:
        if not os.path.exists(args.file):
            print(f"[ERR] File not found: {args.file}")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            code = f.read()
        fixed = run_agent(code, args.model)

        # Optionally write the fixed code back
        out_path = args.file.replace(".cpy", "_fixed.cpy")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(fixed)
        print(f"\n[SAVED] Fixed code saved to: {out_path}")

    elif args.code:
        # Replace literal \n with actual newlines
        code = args.code.replace("\\n", "\n")
        run_agent(code, args.model)

    else:
        parser.print_help()
