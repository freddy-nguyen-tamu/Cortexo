from __future__ import annotations

import difflib
import random
import re
import uuid
from dataclasses import dataclass, field
from typing import Callable

IDENTIFIER_RE = re.compile(r"\b([a-z][a-z0-9_]*)\b")

NUMERIC_RE = re.compile(r"\b(\d+)\b")


@dataclass
class MutationOperator:
    name: str
    description: str
    apply: Callable[[str, dict], str]


def change_constant(text: str, rng) -> str:
    matches = list(NUMERIC_RE.finditer(text))
    if not matches:
        return text
    idx = rng.randrange(0, len(matches))
    m = matches[idx]
    value = int(m.group(1))
    new_value = value + rng.choice([1, -1, 2, -2])
    if new_value == value:
        new_value += 1
    return text[:m.start()] + str(new_value) + text[m.end():]


def reverse_comparison(text: str, rng) -> str:
    patterns = {
        "==": "!=", "!=": "==", "<": ">=", ">": "<=", "<=": ">", ">=": "<",
    }
    found = [op for op in patterns if op in text]
    if not found:
        return text
    op = rng.choice(found)
    replacement = patterns[op]
    return text.replace(op, replacement, 1)


def remove_null_check(text: str, rng) -> str:
    patterns = [
        re.compile(r'\s*if\s+\w+\s+is\s+not\s+None:\s*\n(.*?)\n\s*', re.S),
        re.compile(r'\s*if\s+not\s+\w+:\s*\n(.*?)\n\s*raise', re.S),
    ]
    for pattern in patterns:
        if pattern.search(text):
            return re.sub(pattern, lambda m: "\n" * m.group(0).count("\n") + "    pass\n", text, count=1)
    return text


def off_by_one(text: str, rng) -> str:
    matches = [
        re.search(r"\brange\((\d+)\)", text),
        re.search(r"\brange\(\d+,\s*(\d+)\)", text),
        re.search(r"\b\[\s*:\s*(\d+)\s*\]", text),
    ]
    for m in matches:
        if m:
            value = int(m.group(1))
            return text[:m.start(1)] + str(value + 1) + text[m.end(1):]
    return change_constant(text, rng)


def wrong_type_conversion(text: str, rng) -> str:
    mapping = {"int(": "float(", "float(": "int(", "str(": "int("}
    for src, dst in mapping.items():
        if src in text:
            return text.replace(src, dst, 1)
    return text


def broken_import(text: str, rng) -> str:
    m = re.search(r"^import (\w+)", text, re.M)
    if m:
        return text[:m.start(1)] + "_missing_" + m.group(1) + text[m.end(1):]
    return text


def dead_code(text: str, rng) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"\s*return\b", line):
            indent = re.match(r"(\s*)", line).group(1)
            lines.insert(i, indent + "if True:\n" + indent + "    pass  # unreachable")
            break
    return "\n".join(lines)


def wrong_operand(text: str, rng) -> str:
    ops = ["+", "-", "*", "/", "%", " and ", " or "]
    found = [op for op in ops if op in text]
    if not found:
        return text
    op = rng.choice(found)
    replacement = rng.choice([o for o in ops if o != op])
    return text.replace(op, replacement, 1)


OPERATORS: list[MutationOperator] = [
    MutationOperator("off-by-one", "index/range boundary shifted by one", off_by_one),
    MutationOperator("comparison-reversal", "comparison operator negated", reverse_comparison),
    MutationOperator("null-check-removal", "null/None guard removed", remove_null_check),
    MutationOperator("wrong-operand", "arithmetic/logical operand changed", wrong_operand),
    MutationOperator("changed-constant", "numeric constant shifted", change_constant),
    MutationOperator("wrong-type-conversion", "type conversion swapped", wrong_type_conversion),
    MutationOperator("dead-code", "unreachable code inserted", dead_code),
    MutationOperator("broken-import", "import target renamed", broken_import),
]

SPECIAL_FIXTURES = {
    "sql-injection": {
        "category": "injection",
        "fragment": 'cursor.execute("SELECT * FROM users WHERE name = %s" % user_input)',
        "target_fix": 'cursor.execute("SELECT * FROM users WHERE name = %s", (user_input,))',
    },
    "path-traversal": {
        "category": "path traversal",
        "fragment": 'open(os.path.join(ROOT, user_path), "r")',
        "target_fix": "path = os.path.realpath(os.path.join(ROOT, user_path)); assert path.startswith(ROOT); open(path, 'r')",
    },
    "authz-omission": {
        "category": "authz omission",
        "fragment": "def delete_record(request, record_id): record = get_record(record_id)",
        "target_fix": "def delete_record(request, record_id): assert request.user.is_admin; record = get_record(record_id)",
    },
    "incorrect-join": {
        "category": "incorrect JOIN",
        "fragment": "FROM invoice i JOIN customer c ON i.invoice_id = c.invoice_id",
        "target_fix": "FROM invoice i JOIN customer c ON i.customer_id = c.customer_id",
    },
    "resource-leak": {
        "category": "resource leak",
        "fragment": "handle = open(filename, 'r')\n    data = handle.read()",
        "target_fix": "with open(filename, 'r') as handle:\n        data = handle.read()",
    },
    "removed-await": {
        "category": "removed await",
        "fragment": "result = fetch_user()",
        "target_fix": "result = await fetch_user()",
    },
    "missing-transaction-boundary": {
        "category": "missing transaction boundary",
        "fragment": "db.execute('INSERT INTO ledger (...) VALUES (...)')",
        "target_fix": "with db.transaction():\n        db.execute('INSERT INTO ledger (...) VALUES (...)')",
    },
    "wrong-exception": {
        "category": "wrong exception",
        "fragment": "raise ValueError('invalid input')",
        "target_fix": "raise TypeError('invalid input')",
    },
    "wrong-variable": {
        "category": "wrong variable",
        "fragment": "return total_price",
        "target_fix": "return total_cost",
    },
}


@dataclass
class MutationResult:
    task_id: str
    operator: str
    original_code: str
    mutated_code: str
    tests: str
    target_patch: str
    verifier: dict
    metadata: dict = field(default_factory=dict)


def make_unittest(name: str, expected: object) -> str:
    return (
        "import unittest\n\n"
        f"class {name.title().replace('_', '')}Test(unittest.TestCase):\n"
        f"    def test_{name}(self):\n"
        f"        self.assertEqual({name}(), {expected!r})\n\n"
        "if __name__ == '__main__':\n    unittest.main()\n"
    )


SEED_PROGRAMS = {
    "sum_range": "def sum_range(n):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n",
    "factorial": "def factorial(n):\n    result = 1\n    for i in range(1, n + 1):\n        result *= i\n    return result\n",
    "is_even": "def is_even(n):\n    return n % 2 == 0\n",
    "count_vowels": "def count_vowels(text):\n    count = 0\n    for ch in text:\n        if ch in 'aeiou':\n            count += 1\n    return count\n",
}

SEED_EXPECTED = {
    "sum_range": 45,
    "factorial": 120,
    "is_even": False,
    "count_vowels": 5,
}


def synthesize_task(
    program_name: str | None = None,
    operator_name: str | None = None,
    seed: int = 42,
) -> MutationResult:
    rng = random.Random(seed)
    program_name = program_name or rng.choice(list(SEED_PROGRAMS))
    original = SEED_PROGRAMS[program_name]
    expected = SEED_EXPECTED[program_name]

    operator = None
    if operator_name:
        for op in OPERATORS:
            if op.name == operator_name:
                operator = op
                break
    if operator is None:
        operator = rng.choice(OPERATORS)

    mutated = operator.apply(original, rng)
    if mutated == original:
        mutated = change_constant(original, rng)

    tests = make_unittest(program_name, expected)
    patch = "".join(
        difflib.unified_diff(
            mutated.splitlines(keepends=True),
            original.splitlines(keepends=True),
            fromfile="a/bad.py",
            tofile="b/good.py",
        )
    )
    return MutationResult(
        task_id=f"synthetic-{program_name}-{operator.name}-{uuid.uuid4().hex[:6]}",
        operator=operator.name,
        original_code=original,
        mutated_code=mutated,
        tests=tests,
        target_patch=patch,
        verifier={"before_pass": False, "after_pass": True},
        metadata={"verification": "deterministic unit-test verifier"},
    )


def synthesize_batch(count: int, seed: int = 42, operators: list[str] | None = None) -> list[MutationResult]:
    results = []
    for i in range(count):
        op = None
        if operators:
            op = operators[i % len(operators)]
        pname = list(SEED_PROGRAMS)[i % len(SEED_PROGRAMS)]
        results.append(synthesize_task(program_name=pname, operator_name=op, seed=seed + i))
    return results


def to_record(result: MutationResult) -> dict:
    return {
        "instruction": "Repair the bug.",
        "bad_code": result.mutated_code,
        "tests": result.tests,
        "target_patch": result.target_patch,
        "verifier": result.verifier,
        "metadata": {
            "task_id": result.task_id,
            "operator": result.operator,
            "expected_behavior": result.verifier,
        },
    }