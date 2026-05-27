"""
fix_applier.py
──────────────
Given a broken CPY code string, an error_line, and a predicted
action label, applies the corresponding repair heuristic and
returns the (hopefully) fixed code.

These heuristics mirror the mutations used in generate_dataset.py
so they can undo the exact injected faults.
"""

import re

BAD_CHARS = set("$@#&`~^?")


def apply_fix(code: str, error_line: int, action: str, error_message: str = "") -> str:
    """
    Apply *action* to *code* at *error_line* (1-based).
    Returns the modified code string.
    """
    lines = code.split("\n")
    idx = max(0, min(error_line - 1, len(lines) - 1))

    if action == "INSERT_SEMICOLON":
        return _insert_semicolon(lines, idx)

    elif action == "DELETE_CHAR_AT_INDEX":
        return _delete_bad_char(lines, idx)

    elif action == "INSERT_QUOTE":
        return _insert_closing_quote(lines, idx)

    elif action == "INSERT_CHAR":
        return _insert_char_literal(lines, idx)

    elif action == "INSERT_RPAREN":
        return _insert_rparen(lines, idx)

    elif action == "INSERT_RBRACE":
        return _insert_rbrace(lines, idx)

    elif action == "PREPEND_LET":
        return _prepend_let(lines, idx, error_message)

    elif action == "REMOVE_LET_OR_RENAME":
        return _remove_let(lines, idx)

    elif action == "MAKE_ARRAY":
        return _make_array(lines, idx, error_message)

    # Unknown action → return code unchanged
    return code


# ── Individual fix heuristics ─────────────────────────────────

def _insert_semicolon(lines: list[str], idx: int) -> str:
    """Add a missing ';' at the end of the target line, or the previous line if it already has one."""
    target_idx = idx
    # Scan upwards if current line is empty or already has semicolon
    while target_idx >= 0:
        line_strip = lines[target_idx].rstrip()
        if line_strip and not line_strip.endswith(";"):
            break
        target_idx -= 1
        
    if target_idx < 0:
        target_idx = idx
        
    line = lines[target_idx].rstrip()
    if not line.endswith(";"):
        line += ";"
    lines[target_idx] = line
    return "\n".join(lines)


def _delete_bad_char(lines: list[str], idx: int) -> str:
    """Remove the first illegal character from the target line."""
    new_line = "".join(ch for ch in lines[idx] if ch not in BAD_CHARS)
    lines[idx] = new_line
    return "\n".join(lines)


def _insert_closing_quote(lines: list[str], idx: int) -> str:
    """
    Fix an unterminated string literal by inserting the
    missing closing double-quote.
    """
    target_idx = idx
    while target_idx >= 0:
        if lines[target_idx].count('"') % 2 == 1:
            break
        target_idx -= 1
        
    if target_idx < 0:
        return "\n".join(lines)
        
    line = lines[target_idx]
    # Find the last quote and insert a closing one before the semicolon or end
    last_q = line.rfind('"')
    # Find where the string content ends (next ; or end of line)
    semi = line.find(";", last_q)
    if semi >= 0:
        # Insert quote just before the semicolon's preceding )
        paren = line.rfind(")", last_q, semi)
        if paren >= 0:
            line = line[:paren] + '"' + line[paren:]
        else:
            line = line[:semi] + '"' + line[semi:]
    else:
        line += '"'
    lines[target_idx] = line
    return "\n".join(lines)


def _insert_char_literal(lines: list[str], idx: int) -> str:
    """Fix an empty char literal '' → 'A'."""
    lines[idx] = lines[idx].replace("''", "'A'")
    return "\n".join(lines)


def _insert_rparen(lines: list[str], idx: int) -> str:
    """
    Insert a missing ')'.  Strategy: find the last token before '{'
    or ';' and insert ')' there.
    """
    line = lines[idx]

    # Common pattern: "print(x;" → "print(x);"
    # or "while (x < 10 {" → "while (x < 10) {"
    brace = line.rfind("{")
    semi = line.rfind(";")
    target = max(brace, semi)

    if target > 0:
        # Insert ')' just before the brace/semicolon
        insert_pos = target
        # Skip any whitespace before the target
        while insert_pos > 0 and line[insert_pos - 1] == " ":
            insert_pos -= 1
        line = line[:insert_pos] + ")" + line[insert_pos:]
    else:
        # Fallback: append ')' before end
        line = line.rstrip() + ")"
    lines[idx] = line
    return "\n".join(lines)


def _insert_rbrace(lines: list[str], idx: int) -> str:
    """Append a closing '}' at the appropriate indentation."""
    # Add '}' as a new line at the end, or after the target line
    lines.append("}")
    return "\n".join(lines)


def _prepend_let(lines: list[str], idx: int, error_message: str = "") -> str:
    """
    Convert an assignment to a declaration by prepending 'let '.
    e.g.  ``x = 5;`` → ``let x = 5;``
    """
    line = lines[idx]
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]

    # Only prepend if not already a declaration
    if not stripped.startswith("let "):
        lines[idx] = indent + "let " + stripped
    return "\n".join(lines)


def _remove_let(lines: list[str], idx: int) -> str:
    """
    Convert a duplicate declaration to an assignment by removing 'let '.
    e.g.  ``let y = 20;`` → ``y = 20;``
    """
    line = lines[idx]
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]

    if stripped.startswith("let "):
        lines[idx] = indent + stripped[4:]
    return "\n".join(lines)


def _make_array(lines: list[str], idx: int, error_message: str = "") -> str:
    """
    Change a scalar variable declaration to an array.
    Looks for the variable name in the error message, then
    finds its declaration and wraps the value in [].
    """
    # Extract variable name from error message like "'x' is not an array"
    match = re.search(r"'(\w+)'", error_message)
    if not match:
        return "\n".join(lines)

    var_name = match.group(1)

    # Find the declaration line for this variable
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(f"let {var_name} =") and "[" not in stripped:
            indent = line[: len(line) - len(stripped)]
            lines[i] = f"{indent}let {var_name} = [0, 0];"
            break

    return "\n".join(lines)


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    # Test INSERT_SEMICOLON
    code = "let x = 10\nprint(x);"
    fixed = apply_fix(code, 1, "INSERT_SEMICOLON")
    print(f"INSERT_SEMICOLON:\n  Before: {code!r}\n  After:  {fixed!r}\n")

    # Test DELETE_CHAR_AT_INDEX
    code = "let x = 10;\nprint(x$);"
    fixed = apply_fix(code, 2, "DELETE_CHAR_AT_INDEX")
    print(f"DELETE_CHAR_AT_INDEX:\n  Before: {code!r}\n  After:  {fixed!r}\n")

    # Test PREPEND_LET
    code = "x = 5;\nprint(x);"
    fixed = apply_fix(code, 1, "PREPEND_LET")
    print(f"PREPEND_LET:\n  Before: {code!r}\n  After:  {fixed!r}\n")
