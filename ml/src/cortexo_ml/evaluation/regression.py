"""Deterministic engineering-regression harness.

This is an additive layer on top of the executable grader. It answers:

    "Did Cortexo's actual engineering capabilities regress after this change,
     and how far has the project progressed?"

It runs FIXED candidate fixtures (known-good and known-bad) through the SAME
grader on every run and compares the actual classification against the
committed, authored expectations. No stochastic model generation is involved
and model-quality benchmark results are intentionally never mixed in here.

Integrity rules:
- The baseline manifest is authored/committed; it is never rewritten from
  actual results.
- A regression is a mismatch between expected and actual (status AND passed
  flag), not merely a model returning FAIL.
- Known-good baseline candidates are evaluator answers and are excluded from
  training corpora (see cortexo_ml.data.collect.path_should_skip).
- Public/API reports omit candidate source, hidden-test source, gold patches
  and raw command logs.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cortexo_ml.evaluation.grader import ExecutableGrader

DEFAULT_SUITE = "deterministic-v1"
BASELINES_DIR = "benchmarks/baselines"
HARNESS_ERROR = "HARNESS_ERROR"

_REQUIRED_CASE_KEYS = {"id", "category", "taskId", "candidate", "expectedStatus", "expectedPassed"}
_FORBIDDEN_CASE_KEYS = ("command", "argv", "hiddenTest", "hidden_test", "testCommand", "compileCommand")

MAX_LOG_CHARS = 64 * 1024


class RegressionBaselineError(ValueError):
    """Raised when a baseline manifest or task map is invalid."""


@dataclass
class DeterministicCaseResult:
    case_id: str
    category: str
    task_id: str
    expected_status: str
    actual_status: str
    expected_passed: bool
    actual_passed: bool
    matched: bool
    duration_ms: int = 0
    candidate_sha256: str | None = None
    changed_files: list[str] | None = None
    changed_lines: int = 0
    message: str = ""

    def __post_init__(self) -> None:
        if self.changed_files is None:
            self.changed_files = []

    def to_record(self) -> dict:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "task_id": self.task_id,
            "expected_status": self.expected_status,
            "actual_status": self.actual_status,
            "expected_passed": bool(self.expected_passed),
            "actual_passed": bool(self.actual_passed),
            "matched": bool(self.matched),
            "duration_ms": int(self.duration_ms),
            "candidate_sha256": self.candidate_sha256,
            "changed_files": list(self.changed_files or []),
            "changed_lines": int(self.changed_lines),
            "message": self.message or "",
        }


@dataclass
class CommandCheckResult:
    check_id: str
    category: str
    passed: bool
    duration_ms: int = 0
    return_code: int | None = None
    command: list[str] | None = None
    stdout: str = ""
    stderr: str = ""

    def __post_init__(self) -> None:
        if self.command is None:
            self.command = []

    def to_record(self) -> dict:
        return {
            "check_id": self.check_id,
            "category": self.category,
            "passed": bool(self.passed),
            "duration_ms": int(self.duration_ms),
            "return_code": self.return_code,
            "command": list(self.command or []),
            "stdout": (self.stdout or "")[:MAX_LOG_CHARS],
            "stderr": (self.stderr or "")[:MAX_LOG_CHARS],
        }


# ------------------------------------------------------------------ time

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso() -> str:
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def compact_timestamp(now: datetime | None = None) -> str:
    return (now or utc_now()).strftime("%Y%m%dT%H%M%SZ")


# ------------------------------------------------------------- metadata

def _git_unsafe(argv: list[str], repo_root: Path) -> str:
    try:
        proc = subprocess.run(["git", *argv], cwd=str(repo_root),
                              capture_output=True, text=True, timeout=10)
        return proc.stdout.strip() if proc.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def git_metadata(repo_root: str | Path) -> dict:
    root = Path(repo_root).resolve()
    commit = _git_unsafe(["rev-parse", "HEAD"], root)
    short = _git_unsafe(["rev-parse", "--short", "HEAD"], root)
    branch = _git_unsafe(["rev-parse", "--abbrev-ref", "HEAD"], root)
    porcelain = _git_unsafe(["status", "--porcelain"], root)
    return {
        "commit": commit,
        "shortCommit": short,
        "branch": branch,
        "dirty": bool(porcelain),
    }


def _version_first_line(argv: list[str]) -> str:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        text = "\n".join((proc.stdout or proc.stderr).splitlines())
        return text.strip() or "not-found"
    except (OSError, subprocess.TimeoutExpired):
        return "not-found"


def environment_metadata(repo_root: str | Path) -> dict:
    java_home = os.environ.get("JAVA_HOME") or "/usr/lib/jvm/java-21-openjdk-amd64"
    return {
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "java": _version_first_line([str(Path(java_home) / "bin" / "java"), "-version"]),
        "maven": _version_first_line(["mvn", "-version"]),
        "node": _version_first_line(["node", "--version"]),
        "npm": _version_first_line(["npm", "--version"]),
        "docker": _version_first_line(["docker", "--version"]),
        "sandboxImage": os.environ.get("CORTEXO_SANDBOX_IMAGE", "cortexo-sandbox:latest"),
    }


def baseline_sha256(repo_root: str | Path, suite: str = DEFAULT_SUITE) -> str:
    path = Path(repo_root).resolve() / BASELINES_DIR / f"{suite}.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -------------------------------------------------------------- baseline

def load_baseline(repo_root: str | Path, suite: str = DEFAULT_SUITE) -> dict:
    root = Path(repo_root).resolve()
    baselines_root = root / BASELINES_DIR
    path = baselines_root / f"{suite}.json"
    if not path.is_file():
        raise RegressionBaselineError(f"baseline suite not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RegressionBaselineError("baseline must be a JSON object")
    if data.get("suiteVersion") != suite:
        raise RegressionBaselineError(
            f"suiteVersion mismatch: expected {suite}, got {data.get('suiteVersion')}")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise RegressionBaselineError("baseline cases must be a non-empty list")

    seen_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise RegressionBaselineError("every baseline case must be an object")
        missing = _REQUIRED_CASE_KEYS - set(case)
        if missing:
            raise RegressionBaselineError(f"case missing keys {sorted(missing)}: {case.get('id')!r}")
        for forbidden in _FORBIDDEN_CASE_KEYS:
            if forbidden in case:
                raise RegressionBaselineError(
                    f"case {case['id']!r} forbids key {forbidden!r}")
        if case["id"] in seen_ids:
            raise RegressionBaselineError(f"duplicate case id: {case['id']}")
        seen_ids.add(case["id"])
        if not isinstance(case["expectedPassed"], bool):
            raise RegressionBaselineError(f"case {case['id']!r} expectedPassed must be boolean")
        candidate = case["candidate"]
        candidate_path = _baseline_join(baselines_root, candidate)
        if not candidate_path.is_file():
            raise RegressionBaselineError(f"case {case['id']!r} candidate not found: {candidate}")
    if not any(c.get("expectedPassed") for c in cases):
        raise RegressionBaselineError("baseline must contain at least one known-good case")
    if not any(not c.get("expectedPassed") for c in cases):
        raise RegressionBaselineError("baseline must contain at least one known-bad case")
    return data


def _baseline_join(baselines_root: Path, rel: str) -> Path:
    candidate_path = (baselines_root / rel).resolve()
    if baselines_root != candidate_path and baselines_root not in candidate_path.parents:
        raise RegressionBaselineError(f"candidate escapes baseline root: {rel}")
    return candidate_path


def load_canonical_task_map(repo_root: str | Path) -> dict[str, dict]:
    root = Path(repo_root).resolve()
    tasks_root = root / "benchmarks" / "tasks"
    if not tasks_root.is_dir():
        raise RegressionBaselineError(f"task root not found: {tasks_root}")
    task_map: dict[str, dict] = {}
    for path in sorted(tasks_root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RegressionBaselineError(f"task file invalid: {path}: {exc}")
        if not isinstance(data, list):
            raise RegressionBaselineError(f"task file must contain a list: {path.name}")
        for item in data:
            if not isinstance(item, dict) or not item.get("task_id"):
                raise RegressionBaselineError(f"task missing task_id in {path.name}")
            if item["task_id"] in task_map:
                raise RegressionBaselineError(f"duplicate task_id: {item['task_id']}")
            task_map[item["task_id"]] = item
    return task_map


# ------------------------------------------------------------- scoring

def is_case_matched(expected_status: str, actual_status: str,
                    expected_passed: bool, actual_passed: bool) -> bool:
    return bool(expected_status == actual_status
                and bool(expected_passed) == bool(actual_passed))


def score_cases(results: list[DeterministicCaseResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.matched)
    failed = total - passed
    score = (passed / total) if total else 0.0
    by_category: dict[str, dict] = {}
    for r in results:
        bucket = by_category.setdefault(r.category, {"passed": 0, "total": 0})
        bucket["total"] += 1
        if r.matched:
            bucket["passed"] += 1
    return {
        "passed": passed,
        "failed": failed,
        "total": total,
        "score": score,
        "percent": round(score * 100, 2),
        "byCategory": by_category,
    }


def score_command_checks(results: list[CommandCheckResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    score = (passed / total) if total else 0.0
    return {
        "passed": passed,
        "failed": failed,
        "total": total,
        "score": score,
        "percent": round(score * 100, 2),
    }


# -------------------------------------------------------- case execution

def _read_candidate(repo_root: str | Path, rel: str) -> str:
    baselines_root = Path(repo_root).resolve() / BASELINES_DIR
    return _baseline_join(baselines_root, rel).read_text(encoding="utf-8")


def run_deterministic_cases(repo_root: str | Path, suite: str = DEFAULT_SUITE,
                            grader: Any | None = None) -> list[DeterministicCaseResult]:
    """Run every baseline case through the executable grader.

    `grader` may be injected (tests / custom harness); it must expose
    `grade(task, output) -> GraderResult`.
    """
    baseline = load_baseline(repo_root, suite)
    task_map = load_canonical_task_map(repo_root)
    executor = grader if grader is not None else ExecutableGrader(repo_root=repo_root)

    results: list[DeterministicCaseResult] = []
    for case in baseline["cases"]:
        try:
            candidate_text = _read_candidate(repo_root, case["candidate"])
            task = task_map[case["taskId"]]
            record = executor.grade(task, candidate_text).to_record()
            actual_status = str(record.get("status") or "UNKNOWN")
            actual_passed = bool(record.get("passed"))
            matched = is_case_matched(case["expectedStatus"], actual_status,
                                      case["expectedPassed"], actual_passed)
            results.append(DeterministicCaseResult(
                case_id=case["id"],
                category=case["category"],
                task_id=case["taskId"],
                expected_status=case["expectedStatus"],
                actual_status=actual_status,
                expected_passed=case["expectedPassed"],
                actual_passed=actual_passed,
                matched=matched,
                duration_ms=int(record.get("durationMs") or 0),
                candidate_sha256=record.get("candidateSha256"),
                changed_files=list(record.get("changedFiles") or []),
                changed_lines=int(record.get("changedLines") or 0),
            ))
        except Exception as exc:  # noqa: BLE001 - harness must continue
            results.append(DeterministicCaseResult(
                case_id=case["id"],
                category=case["category"],
                task_id=case["taskId"],
                expected_status=case["expectedStatus"],
                actual_status=HARNESS_ERROR,
                expected_passed=case["expectedPassed"],
                actual_passed=False,
                matched=False,
                message=f"{type(exc).__name__}: {exc}",
            ))
    return results


# -------------------------------------------------------------- reports

def _gate(software: dict, deterministic: dict, requested: dict, required_score: float) -> bool:
    parts: list[bool] = []
    if requested.get("software"):
        parts.append(software["failed"] == 0)
    if requested.get("deterministic"):
        parts.append(deterministic["score"] >= float(required_score))
    return bool(parts) and all(parts)


def build_report(*, suite: str, baseline_sha: str, git: dict, environment: dict,
                 checks: list[CommandCheckResult], cases: list[DeterministicCaseResult],
                 required_score: float, requested: dict, delta: dict | None = None,
                 generated_at: str | None = None) -> dict:
    generated = generated_at or utc_iso()
    software = score_command_checks(checks)
    deterministic = score_cases(cases)

    overall_passed = 0
    overall_total = 0
    if requested.get("software"):
        overall_passed += software["passed"]
        overall_total += software["total"]
    if requested.get("deterministic"):
        overall_passed += deterministic["passed"]
        overall_total += deterministic["total"]
    overall_score = (overall_passed / overall_total) if overall_total else 0.0
    overall = {
        "passed": overall_passed,
        "failed": overall_total - overall_passed,
        "total": overall_total,
        "score": overall_score,
        "percent": round(overall_score * 100, 2),
    }

    summary: dict = {
        "software": software,
        "deterministic": deterministic,
        "overall": overall,
        "requiredDeterministicScore": float(required_score),
        "passedGate": _gate(software, deterministic, requested, required_score),
    }

    report: dict = {
        "schemaVersion": 1,
        "suiteVersion": suite,
        "generatedAt": generated,
        "git": {
            "commit": git.get("commit", ""),
            "shortCommit": git.get("shortCommit", ""),
            "branch": git.get("branch", ""),
            "dirty": bool(git.get("dirty")),
        },
        "environment": environment,
        "baselineSha256": baseline_sha,
        "requested": {
            "software": bool(requested.get("software")),
            "deterministic": bool(requested.get("deterministic")),
        },
        "summary": summary,
        "checks": [c.to_record() for c in checks],
        "cases": [c.to_record() for c in cases],
    }
    if delta is not None:
        report["delta"] = delta
    return report


def regression_report_dir(repo_root: str | Path) -> Path:
    return Path(repo_root).resolve() / "artifacts" / "evaluations" / "regression"


def load_latest_report(repo_root: str | Path) -> dict | None:
    path = regression_report_dir(repo_root) / "latest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _compute_delta(previous: dict, current: dict) -> dict:
    prev_score = float(((previous.get("summary") or {}).get("overall") or {}).get("score", 0.0))
    curr_score = float(((current.get("summary") or {}).get("overall") or {}).get("score", 0.0))
    previous_cases = {c["case_id"]: c for c in previous.get("cases", []) if isinstance(c, dict)}
    changed_cases: list[dict] = []
    for case in current.get("cases", []):
        if not isinstance(case, dict):
            continue
        prev = previous_cases.get(case.get("case_id"))
        if prev is None:
            continue
        prev_matched = bool(prev.get("matched"))
        curr_matched = bool(case.get("matched"))
        if prev_matched != curr_matched:
            changed_cases.append({
                "caseId": case.get("case_id"),
                "previousMatched": prev_matched,
                "currentMatched": curr_matched,
            })
    return {
        "previousOverallScore": prev_score,
        "currentOverallScore": curr_score,
        "scoreDelta": round(curr_score - prev_score, 4),
        "changedCases": changed_cases,
    }


def save_report(repo_root: str | Path, report: dict) -> Path:
    report_dir = regression_report_dir(repo_root)
    report_dir.mkdir(parents=True, exist_ok=True)
    previous = load_latest_report(repo_root)
    if previous and previous.get("suiteVersion") == report.get("suiteVersion"):
        report["delta"] = _compute_delta(previous, report)
    else:
        report.pop("delta", None)
    timestamp = compact_timestamp()
    short = (report.get("git") or {}).get("shortCommit") or "nosha"
    path = report_dir / f"{timestamp}-{short}.json"
    encoded = json.dumps(report, indent=2, sort_keys=True)
    path.write_text(encoded, encoding="utf-8")
    (report_dir / "latest.json").write_text(encoded, encoding="utf-8")
    return path


def history_summaries(repo_root: str | Path, limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    report_dir = regression_report_dir(repo_root)
    if not report_dir.is_dir():
        return []
    reports: list[tuple[str, dict]] = []
    for path in sorted(report_dir.glob("*.json")):
        if path.name == "latest.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict):
            reports.append((path.name, data))
    reports.sort(key=lambda pair: pair[0])
    return [public_regression_summary(report) for _, report in reports[-limit:]]


# --------------------------------------------------------- public views

def _public_git(git: dict) -> dict:
    return {
        "shortCommit": git.get("shortCommit") or None,
        "branch": git.get("branch") or None,
        "dirty": bool(git.get("dirty")),
    }


def public_regression_summary(report: dict) -> dict:
    return {
        "suiteVersion": report.get("suiteVersion"),
        "generatedAt": report.get("generatedAt"),
        "git": _public_git(report.get("git") or {}),
        "summary": report.get("summary", {}),
        "delta": report.get("delta"),
    }


def public_regression_report(report: dict | None) -> dict | None:
    """Browser/API-safe projection. Raw candidate source, hidden-test source,
    gold patches, environment secrets and full command stdout/stderr are all
    omitted."""
    if report is None:
        return None
    public: dict = {
        "suiteVersion": report.get("suiteVersion"),
        "generatedAt": report.get("generatedAt"),
        "git": _public_git(report.get("git") or {}),
        "summary": report.get("summary", {}),
        "baselineSha256": report.get("baselineSha256"),
        "cases": _public_cases(report.get("cases") or []),
        "checks": _public_checks(report.get("checks") or []),
    }
    if report.get("delta") is not None:
        public["delta"] = report["delta"]
    return public


def _public_cases(cases: list[dict]) -> list[dict]:
    public = []
    for case in cases:
        public.append({
            "case_id": case.get("case_id"),
            "category": case.get("category"),
            "task_id": case.get("task_id"),
            "expected_status": case.get("expected_status"),
            "actual_status": case.get("actual_status"),
            "expected_passed": case.get("expected_passed"),
            "actual_passed": case.get("actual_passed"),
            "matched": bool(case.get("matched")),
            "duration_ms": case.get("duration_ms"),
            "candidate_sha256": case.get("candidate_sha256"),
            "changed_files": list(case.get("changed_files") or []),
            "changed_lines": case.get("changed_lines"),
            "message": case.get("message") or "",
        })
    return public


def _public_checks(checks: list[dict]) -> list[dict]:
    public = []
    for check in checks:
        public.append({
            "check_id": check.get("check_id"),
            "category": check.get("category"),
            "passed": bool(check.get("passed")),
            "duration_ms": check.get("duration_ms"),
            "return_code": check.get("return_code"),
        })
    return public