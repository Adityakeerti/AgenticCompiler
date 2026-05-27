import csv
import random
import os

# Configuration
OUTPUT_FILE = "cpy_error_dataset.csv"

# Expanded to 30,000 rows (10k per error type)
TARGETS = {
    'Lexical': 10000,
    'Syntactic': 10000,
    'Semantic': 10000
}

VAR_NAMES = ['x', 'y', 'count', 'total', 'score', 'player', 'index', 'value',
             'result', 'sum', 'i', 'j', 'data', 'arr', 'name', 'flag', 'limit',
             'n', 'k', 'temp', 'max', 'min', 'found', 'target', 'size']
VALUES_NUM = ['0', '1', '2', '5', '10', '42', '100', '99', '3', '7', '15', '20']
BAD_CHARS = ['$', '@', '#', '&', '`', '~', '^', '?']

def get_vars(n=3):
    return random.sample(VAR_NAMES, n)

def build_template(complexity):
    """Generates perfectly valid CPY snippets."""
    v1, v2, v3 = get_vars(3)
    val1, val2 = random.choice(VALUES_NUM), random.choice(VALUES_NUM)

    if complexity == 'short':
        templates = [
            f"let {v1} = {val1};\nprint({v1});",
            f"let {v1} = {val1};\nlet {v2} = {v1} + {val2};\nprint({v2});",
            f"let {v1} = [{val1}, {val2}, 0];\nprint({v1}[1]);",
            f"let {v1} = {val1};\nlet {v2} = {v1} * 2;\nprint({v2});",
            f"let {v1} = {val1};\nif ({v1} > 0) {{\n    print({v1});\n}}",
        ]
        return random.choice(templates)

    elif complexity == 'medium':
        templates = [
            f"let {v1} = 0;\nwhile ({v1} < {val1}) {{\n    print({v1});\n    {v1} = {v1} + 1;\n}}",
            f"let {v1} = {val1};\nif ({v1} > 5) {{\n    let {v2} = {v1} * 2;\n    print({v2});\n}} else {{\n    print({v1});\n}}",
            f"for (let {v1} = 0; {v1} < 10; {v1} = {v1} + 1) {{\n    let {v2} = {v1} * {val1};\n    print({v2});\n}}",
            f"let {v1} = 0;\nwhile ({v1} < {val1}) {{\n    if ({v1} > 3) {{\n        print({v1});\n    }}\n    {v1} = {v1} + 1;\n}}",
            f"let {v1} = {val1};\nif ({v1} < 5) {{\n    print(\"low\");\n}} else {{\n    print(\"high\");\n}}",
            f"for (let {v1} = 0; {v1} < {val1}; {v1} = {v1} + 1) {{\n    if ({v1} > 2) {{\n        print({v1});\n    }}\n}}",
            f"let {v2} = {val2};\nlet {v1} = 0;\nwhile ({v1} < {v2}) {{\n    {v1} = {v1} + 1;\n}}\nprint({v1});",
        ]
        return random.choice(templates)

    else:  # long
        templates = [
            f"let {v1} = 0;\nlet {v2} = 10;\nlet sum = 0;\nwhile ({v1} < {v2}) {{\n    if ({v1} > 5) {{\n        sum = sum + {v1};\n    }} else {{\n        sum = sum + {v2};\n    }}\n    {v1} = {v1} + 1;\n}}\nprint(sum);",
            f"let {v1} = [10, 20, 30, 40, 50];\nlet {v2} = 30;\nlet {v3} = 0;\nfor (let i = 0; i < 5; i = i + 1) {{\n    if ({v1}[i] == {v2}) {{\n        {v3} = 1;\n    }}\n}}\nif ({v3} == 1) {{\n    print(\"Found\");\n}} else {{\n    print(\"Not Found\");\n}}",
            f"let arr = [{val1}, {val2}, 0, 5, 9];\nlet max = 0;\nfor (let j = 0; j < 5; j = j + 1) {{\n    if (arr[j] > max) {{\n        max = arr[j];\n    }}\n}}\nlet {v1} = max;\nprint({v1});\nif ({v1} == 0) {{\n    print(\"Zero\");\n}}",
            f"let {v1} = 0;\nfor (let i = 0; i < {val1}; i = i + 1) {{\n    for (let j = 0; j < {val2}; j = j + 1) {{\n        {v1} = {v1} + 1;\n    }}\n}}\nprint({v1});",
            f"let {v1} = {val1};\nlet {v2} = {val2};\nif ({v1} > {v2}) {{\n    print(\"greater\");\n    {v1} = {v1} - 1;\n}} else {{\n    if ({v1} == {v2}) {{\n        print(\"equal\");\n    }} else {{\n        print(\"less\");\n    }}\n}}\nprint({v1});",
            f"let {v1} = 0;\nwhile ({v1} < {val1}) {{\n    for (let k = 0; k < {val2}; k = k + 1) {{\n        print(k);\n    }}\n    {v1} = {v1} + 1;\n}}\nprint({v1});",
        ]
        return random.choice(templates)


def mutate_lexical(fixed_code):
    lines = fixed_code.split('\n')
    line_idx = random.randint(0, len(lines) - 1)

    if random.choice([True, False]):
        bad_char = random.choice(BAD_CHARS)
        old_line = lines[line_idx]
        if ';' in old_line:
            new_line = old_line.replace(';', f"{bad_char};", 1)
        else:
            new_line = old_line + bad_char
        lines[line_idx] = new_line
        err_msg = f"Unexpected character '{bad_char}'"
        action = "DELETE_CHAR_AT_INDEX"
    else:
        lines[line_idx] = 'print("hello);'
        fixed_lines = fixed_code.split('\n')
        fixed_lines[line_idx] = 'print("hello");'
        fixed_code = '\n'.join(fixed_lines)
        err_msg = "Unterminated string"
        action = "INSERT_QUOTE"

    return '\n'.join(lines), err_msg, line_idx + 1, action, fixed_code


def mutate_syntactic(fixed_code):
    lines = fixed_code.split('\n')
    # Weight RBRACE higher to fix the accuracy gap
    mut = random.choices(
        ['MISSING_SEMICOLON', 'MISSING_RBRACE', 'MISSING_RPAREN'],
        weights=[33, 40, 27],
        k=1
    )[0]

    if mut == 'MISSING_SEMICOLON':
        valid_lines = [i for i, l in enumerate(lines) if ';' in l and '{' not in l]
        if not valid_lines:
            valid_lines = [i for i, l in enumerate(lines) if ';' in l]
        if not valid_lines:
            return mutate_syntactic(fixed_code + "\nlet _x = 1;")
        line_idx = random.choice(valid_lines)
        lines[line_idx] = lines[line_idx].replace(';', '', 1)
        if 'let ' in lines[line_idx]:
            err_msg = "Expected ';' after variable declaration"
        elif 'print' in lines[line_idx]:
            err_msg = "Expected ';' after print statement"
        else:
            err_msg = "Expected ';' after assignment"
        return '\n'.join(lines), err_msg, line_idx + 1, "INSERT_SEMICOLON", fixed_code

    elif mut == 'MISSING_RBRACE':
        valid_lines = [i for i, l in enumerate(lines) if '}' in l]
        if not valid_lines:
            return mutate_syntactic(fixed_code)
        line_idx = random.choice(valid_lines)
        lines[line_idx] = lines[line_idx].replace('}', '', 1)
        err_msg = "Expected '}' to close block"
        return '\n'.join(lines), err_msg, line_idx + 1, "INSERT_RBRACE", fixed_code

    elif mut == 'MISSING_RPAREN':
        valid_lines = [i for i, l in enumerate(lines) if ')' in l]
        if not valid_lines:
            return mutate_syntactic(fixed_code)
        line_idx = random.choice(valid_lines)
        lines[line_idx] = lines[line_idx].replace(')', '', 1)
        err_msg = "Expected ')'"
        return '\n'.join(lines), err_msg, line_idx + 1, "INSERT_RPAREN", fixed_code


def mutate_semantic(fixed_code):
    lines = fixed_code.split('\n')
    mut = random.choice(['USED_BEFORE_DECLARATION', 'ALREADY_DECLARED', 'NOT_AN_ARRAY'])

    if mut == 'USED_BEFORE_DECLARATION':
        for i, l in enumerate(lines):
            if 'let ' in l:
                var_name = l.split('let ')[1].split(' ')[0]
                lines[i] = l.replace('let ', '', 1)
                return '\n'.join(lines), f"Variable '{var_name}' used before declaration", i + 1, "PREPEND_LET", fixed_code

    elif mut == 'ALREADY_DECLARED':
        for i, l in enumerate(lines):
            if 'let ' in l:
                var_name = l.split('let ')[1].split(' ')[0]
                lines.insert(i + 1, l)
                fixed_lines = lines.copy()
                fixed_lines[i + 1] = fixed_lines[i + 1].replace('let ', '', 1)
                return '\n'.join(lines), f"Variable '{var_name}' already declared", i + 2, "REMOVE_LET_OR_RENAME", '\n'.join(fixed_lines)

    elif mut == 'NOT_AN_ARRAY':
        for i, l in enumerate(lines):
            if 'let ' in l and '[' not in l:
                var_name = l.split('let ')[1].split(' =')[0]
                lines.insert(i + 1, f"{var_name}[0] = 1;")
                fixed_lines = lines.copy()
                fixed_lines[i] = fixed_lines[i].replace(l.split('=')[1].strip(), "[0, 0];")
                return '\n'.join(lines), f"'{var_name}' is not an array", i + 2, "MAKE_ARRAY", '\n'.join(fixed_lines)

    return mutate_semantic(build_template("medium"))


def get_complexity(code):
    """Infer complexity from line count."""
    n = len([l for l in code.split('\n') if l.strip()])
    if n <= 3:
        return 'short'
    elif n <= 8:
        return 'medium'
    else:
        return 'long'


def generate_row(id_num, error_type, complexity):
    fixed_code = build_template(complexity)
    if error_type == 'Lexical':
        orig, msg, line, action, fixed = mutate_lexical(fixed_code)
    elif error_type == 'Syntactic':
        orig, msg, line, action, fixed = mutate_syntactic(fixed_code)
    else:
        orig, msg, line, action, fixed = mutate_semantic(fixed_code)
    return [id_num, orig, error_type, msg, line, action, fixed, get_complexity(orig)]


def main():
    total = sum(TARGETS.values())
    print(f"Generating balanced {total:,}-row CPY dataset...")

    dataset = []
    current_id = 1

    for err_type, target_count in TARGETS.items():
        short_count = target_count // 3
        med_count = target_count // 3
        long_count = target_count - short_count - med_count
        counts = {'short': short_count, 'medium': med_count, 'long': long_count}

        print(f"  Generating {err_type}: {target_count:,} rows...")
        for complexity, count in counts.items():
            for _ in range(count):
                row = generate_row(current_id, err_type, complexity)
                dataset.append(row)
                current_id += 1

    random.shuffle(dataset)
    for idx, row in enumerate(dataset, start=1):
        row[0] = idx

    with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(['id', 'original_code', 'error_type', 'error_message',
                         'error_line', 'target_action', 'fixed_code', 'complexity'])
        for row in dataset:
            writer.writerow(row)

    print(f"\nDone! Dataset saved to {os.path.abspath(OUTPUT_FILE)}")

    from collections import Counter
    err_counts = Counter(row[2] for row in dataset)
    action_counts = Counter(row[5] for row in dataset)
    complexity_counts = Counter(row[7] for row in dataset)

    print("\nError Type Distribution:")
    for k, v in sorted(err_counts.items()):
        print(f"  {k}: {v:,}")

    print("\nAction Distribution (RBRACE should be higher now):")
    for k, v in sorted(action_counts.items()):
        print(f"  {k}: {v:,}")

    print("\nComplexity Distribution:")
    for k, v in sorted(complexity_counts.items()):
        print(f"  {k}: {v:,}")


if __name__ == "__main__":
    main()
