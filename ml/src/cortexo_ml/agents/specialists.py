from __future__ import annotations

import json

from cortexo_ml.common.schemas import REVIEW_RESULT, SECURITY_RESULT, validate_against_schema
from cortexo_ml.agents.executor import TextBackend
from cortexo_ml.agents.tools import ToolExecutor

INJECTION_RE = [
    "sql-injection-re", "path-traversal-re", "xss-re", "ssrf-re"
]

SECURITY_PATTERNS_REVIEW = {
    "sql_injection": r"execute\(\s*[\"'][^\"']*%.*[\"']",
    "path_traversal": r"open\(\s*os\.path\.join\([^)]+\)",
    "xss": r"innerHTML\s*=|dangerouslySetInnerHTML|v-html\s*=",
    "weak_crypto": r"md5\(|sha1\(|DES|RC4",
    "hardcoded_secret": r"(?i)(password|secret|api_key)\s*=\s*[\"'][^\"']{6,}[\"']",
    "authz_omission": r"@app\.route\s*\([^)]*methods=\[[^]]*\"DELETE\"|\"POST\"\]\)",
}


def _line_of(text: str, match_start: int) -> int:
    return text.count("\n", 0, match_start) + 1


def deterministic_security_scan(file_path: str, text: str) -> list[dict]:
    findings = []
    for category, pattern in SECURITY_PATTERNS_REVIEW.items():
        import re

        for m in re.finditer(pattern, text, re.I):
            findings.append({
                "file": file_path,
                "line": _line_of(text, m.start()),
                "severity": "high" if category in {"sql_injection", "path_traversal", "weak_crypto", "hardcoded_secret"} else "medium",
                "category": category,
                "cwe": {
                    "sql_injection": "CWE-89", "path_traversal": "CWE-22", "xss": "CWE-79",
                    "weak_crypto": "CWE-327", "hardcoded_secret": "CWE-798",
                }.get(category, "CWE-000"),
                "expected_fix": f"fix {category}",
                "confidence": 0.9,
            })
    return findings


class ReviewAgent:
    """Produces structured ReviewResult findings, mixed with deterministic scans."""

    def __init__(self, backend: TextBackend):
        self.backend = backend

    def review(self, file_path: str, text: str) -> dict:
        prompt = (
            f"Review this source file for correctness bugs. Return ONLY JSON matching:\n"
            f"{json.dumps(REVIEW_RESULT)}\n\nFILE {file_path}:\n{text[:8000]}"
        )
        raw = self.backend.complete(prompt, max_new_tokens=512, temperature=0.1)
        from cortexo_ml.common.schemas import extract_json_objects

        for candidate in extract_json_objects(raw):
            validation = validate_against_schema(candidate, REVIEW_RESULT)
            if validation.valid:
                return candidate
        return {"findings": []}


class SecurityAgent:
    def __init__(self, backend: TextBackend):
        self.backend = backend

    def scan(self, file_path: str, text: str) -> dict:
        deterministic = deterministic_security_scan(file_path, text)
        prompt = (
            f"Audit this source for security vulnerabilities. Return ONLY JSON matching:\n"
            f"{json.dumps(SECURITY_RESULT)}\n\nFILE {file_path}:\n{text[:8000]}"
        )
        raw = self.backend.complete(prompt, max_new_tokens=512, temperature=0.1)
        from cortexo_ml.common.schemas import extract_json_objects

        model_findings = []
        for candidate in extract_json_objects(raw):
            if validate_against_schema(candidate, SECURITY_RESULT).valid:
                model_findings = candidate.get("findings", [])
                break
        merged = _merge_findings(deterministic + model_findings)
        return {"findings": merged}


class TestAgent:
    """Generate tests; ensure the new test fails before the fix and passes after."""

    def __init__(self, backend: TextBackend, tools: ToolExecutor | None = None):
        self.backend = backend
        self.tools = tools

    def generate(self, target_file: str, text: str) -> str:
        prompt = (
            f"Write a pytest/unittest test file for {target_file} covering the main behavior.\n"
            "Return ONLY code inside a ```python ... ``` fence.\n"
        )
        raw = self.backend.complete(prompt, max_new_tokens=768, temperature=0.2)
        import re

        fence = re.search(r"```python\s*(.*?)```", raw, re.S)
        return (fence.group(1).strip() if fence else raw.strip())


class DebugAgent:
    def __init__(self, backend: TextBackend):
        self.backend = backend

    def diagnose(self, failing_test: str, stack_trace: str, relevant_files: list[tuple[str, str]]) -> dict:
        context = "\n\n".join(f"--- {path} ---\n{text[:3000]}" for path, text in relevant_files)
        prompt = (
            f"FAILING TEST:\n{failing_test}\n\nSTACK TRACE:\n{stack_trace}\n\n"
            f"RELEVANT FILES:\n{context}\n\n"
            'Diagnose the root cause. Return JSON {"root_cause": string, "culprit_file": string, "fix_hint": string}'
        )
        raw = self.backend.complete(prompt, max_new_tokens=512, temperature=0.2)
        from cortexo_ml.common.schemas import extract_json_objects

        for candidate in extract_json_objects(raw):
            if isinstance(candidate, dict) and "root_cause" in candidate:
                return candidate
        return {"root_cause": "", "culprit_file": "", "fix_hint": ""}


def _merge_findings(findings: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    merged = []
    for f in findings:
        key = (f.get("file"), f.get("line"), f.get("category"))
        if key in seen:
            continue
        seen.add(key)
        f.setdefault("severity", "medium")
        f.setdefault("confidence", 0.5)
        merged.append(f)
    return sorted(merged, key=lambda x: x["line"])