"""
compiler_wrapper.py
───────────────────
Wraps the Java-based CPY compiler so Python can invoke it,
capture its output, and determine success / failure.

Used during **inference** (the compile→fix→recompile loop).
During **training** we use the dataset as the oracle instead
of calling the real compiler, for speed.
"""

import os
import re
import subprocess
import tempfile


# Path to the Compiler directory (sibling of agentic_pipeline/)
_COMPILER_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Compiler")
)
_OUT_DIR = os.path.join(_COMPILER_DIR, "out")


class CompileResult:
    """Holds the outcome of a single compilation attempt."""

    def __init__(self, success: bool, error_message: str = "",
                 error_line: int = -1, error_type: str = "", raw_output: str = ""):
        self.success = success
        self.error_message = error_message
        self.error_line = error_line
        self.error_type = error_type
        self.raw_output = raw_output

    def __repr__(self):
        if self.success:
            return "CompileResult(success=True)"
        return (
            f"CompileResult(success=False, "
            f"error_type={self.error_type!r}, "
            f"line={self.error_line}, "
            f"msg={self.error_message!r})"
        )


def compile_code(source_code: str) -> CompileResult:
    """
    Write *source_code* to a temp ``.cpy`` file, invoke the
    Java compiler, parse the output, and return a ``CompileResult``.
    """
    # Write source to a temporary file
    tmp_dir = os.path.join(_COMPILER_DIR, "_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_file = os.path.join(tmp_dir, "agent_test.cpy")

    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(source_code)

    try:
        result = subprocess.run(
            ["java", "-cp", _OUT_DIR, "Main", "compile", tmp_file],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=_COMPILER_DIR,
        )

        raw = (result.stdout + "\n" + result.stderr).strip()

        if result.returncode == 0:
            # Clean up the .cpyc file
            cpyc_file = tmp_file.replace(".cpy", ".cpyc")
            if os.path.exists(cpyc_file):
                os.remove(cpyc_file)
            return CompileResult(success=True, raw_output=raw)

        # Parse the error output
        error_msg, error_line, error_type = _parse_error(raw)
        return CompileResult(
            success=False,
            error_message=error_msg,
            error_line=error_line,
            error_type=error_type,
            raw_output=raw,
        )

    except subprocess.TimeoutExpired:
        return CompileResult(
            success=False,
            error_message="Compilation timed out",
            error_type="Timeout",
        )
    except FileNotFoundError:
        return CompileResult(
            success=False,
            error_message="Java not found. Make sure 'java' is on your PATH.",
            error_type="System",
        )
    finally:
        # Clean up temp file
        if os.path.exists(tmp_file):
            os.remove(tmp_file)


def _parse_error(raw_output: str) -> tuple[str, int, str]:
    """
    Extract (error_message, error_line, error_type) from CPY compiler output.
    Returns best-effort values.
    """
    error_msg = raw_output.strip()
    error_line = 1
    error_type = "Unknown"

    # Try to extract line number from patterns like "at line 5" or "(line 3)"
    line_match = re.search(r"(?:at |at\s+)?line\s+(\d+)", raw_output, re.IGNORECASE)
    if line_match:
        error_line = int(line_match.group(1))

    # Determine error type from keywords
    lower = raw_output.lower()
    if any(kw in lower for kw in ["unexpected character", "unterminated", "char literal"]):
        error_type = "Lexical"
    elif any(kw in lower for kw in ["expected", "unexpected token"]):
        error_type = "Syntactic"
    elif any(kw in lower for kw in ["before declaration", "already declared", "not an array"]):
        error_type = "Semantic"
    elif "runtime error" in lower:
        error_type = "Runtime"

    return error_msg, error_line, error_type


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing compiler wrapper...\n")

    # This should SUCCEED
    res = compile_code('let x = 10;\nprint(x);')
    print(f"Valid code   → {res}")

    # This should FAIL (missing semicolon)
    res = compile_code('let x = 10\nprint(x);')
    print(f"Missing ';'  → {res}")

    # This should FAIL (undeclared variable)
    res = compile_code('x = 5;\nprint(x);')
    print(f"Undeclared x → {res}")
