#!/usr/bin/env python3
"""Standard CLI entrypoint for the deterministic regression harness.

Modes:
    full      software checks + deterministic grader suite
    grader    deterministic suite only
    software  build/test checks only

The runner continues past individual failures so one invocation shows the
whole health picture. Exit code is 0 only when the requested gate passes.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ML_SRC = ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from cortexo_ml.evaluation.regression import (  # noqa: E402
    DEFAULT_SUITE,
    CommandCheckResult,
    baseline_sha256,
    build_report,
    environment_metadata,
    git_metadata,
    load_baseline,
    run_deterministic_cases,
    save_report,
)

JAVA_HOME_FALLBACK = "/usr/lib/jvm/java-21-openjdk-amd64"


def _python() -> list[str]:
    venv = ROOT / "ml" / ".venv" / "bin" / "python"
    if venv.exists():
        return [str(venv)]
    return [sys.executable]


def _run_check(check_id: str, category: str, argv: list[str],
               cwd: Path | None = None, timeout: int = 900,
               env: dict | None = None) -> CommandCheckResult:
    start = time.monotonic()
    stdout = ""
    stderr = ""
    return_code: int | None = None
    passed = False
    try:
        proc = subprocess.run(argv, cwd=str(cwd) if cwd else None,
                              capture_output=True, text=True, timeout=timeout,
                              env=env)
        return_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
        passed = return_code == 0
    except subprocess.TimeoutExpired:
        stderr = f"TIMEOUT after {timeout}s"
    except OSError as exc:
        stderr = f"command not found: {exc}"
    duration_ms = int((time.monotonic() - start) * 1000)
    return CommandCheckResult(
        check_id=check_id,
        category=category,
        passed=passed,
        duration_ms=duration_ms,
        return_code=return_code,
        command=argv,
        stdout=stdout,
        stderr=stderr,
    )


def _scan_forbidden_gold_patch_assignment() -> CommandCheckResult:
    """Deterministic source scan for the forbidden old pattern
    `patch = task.get("gold_patch")` which leaked the gold patch into the run
    patch field. No subprocess / shell involved."""
    forbidden = 'patch = task.get("gold_patch")'
    hits: list[str] = []
    scan_roots = [ROOT / "ml" / "src" / "cortexo_ml"]
    start = time.monotonic()
    for root in scan_roots:
        for path in sorted(root.rglob("*.py")):
            try:
                if forbidden in path.read_text(encoding="utf-8"):
                    hits.append(str(path.relative_to(ROOT)))
            except OSError:
                continue
    passed = not hits
    return CommandCheckResult(
        check_id="gold-patch-assignment",
        category="evaluator-integrity",
        passed=passed,
        duration_ms=int((time.monotonic() - start) * 1000),
        return_code=0 if passed else 1,
        command=[],
        stdout="",
        stderr=("forbidden gold_patch assignment found in: " + ", ".join(hits)) if hits else "",
    )


def software_checks() -> list[CommandCheckResult]:
    py = _python()
    checks: list[CommandCheckResult] = [
        _run_check("python-compile", "python", [*py, "-m", "compileall", "-q", "ml/src/cortexo_ml"], cwd=ROOT),
        _run_check("python-tests", "python", [*py, "-m", "pytest", "-q", "ml/tests", "-ra"], cwd=ROOT, timeout=1800),
        _run_check("sandbox-build", "sandbox", ["docker", "build", "-t", "cortexo-sandbox:latest", "sandbox"], cwd=ROOT, timeout=1800),
        _run_check("vue-typecheck", "vue", ["npm", "run", "typecheck"], cwd=ROOT / "apps" / "web-vue"),
        _run_check("vue-build", "vue", ["npm", "run", "build"], cwd=ROOT / "apps" / "web-vue"),
    ]
    java_env = dict(os.environ)
    java_home = os.environ.get("JAVA_HOME") or JAVA_HOME_FALLBACK
    java_env["JAVA_HOME"] = java_home
    checks.append(_run_check("spring-tests", "java", ["mvn", "-q", "test"],
                             cwd=ROOT / "apps" / "api-spring", timeout=1800, env=java_env))
    checks.append(_scan_forbidden_gold_patch_assignment())
    return checks


def _print_summary(report: dict) -> None:
    summary = report["summary"]
    s = summary["software"]
    d = summary["deterministic"]
    o = summary["overall"]
    git = report.get("git") or {}
    delta = report.get("delta")
    width = 76
    print("=" * width)
    print("CORTEXO REGRESSION REPORT")
    print("=" * width)
    print(f"Suite:                    {report.get('suiteVersion')}")
    print(f"Generated:                {report.get('generatedAt')}")
    print(f"Commit:                   {git.get('shortCommit') or 'n/a'}")
    print(f"Branch:                   {git.get('branch') or 'n/a'}")
    print(f"Dirty working tree:       {git.get('dirty')}")
    print("-")
    print(f"Software checks:          {s['passed']} / {s['total']}")
    print(f"Deterministic cases:      {d['passed']} / {d['total']}")
    print(f"Deterministic score:      {d['percent']:.2f}%")
    print(f"Overall checks:           {o['passed']} / {o['total']}")
    print(f"Overall score:            {o['percent']:.2f}%")
    print(f"Gate passed:              {summary['passedGate']}")
    print()
    print("SOFTWARE")
    for check in report.get("checks", []):
        label = "PASS" if check.get("passed") else "FAIL"
        print(f"  [{label}] {check.get('check_id')}")
    print()
    print("DETERMINISTIC CASES")
    for case in report.get("cases", []):
        label = "PASS" if case.get("matched") else "FAIL"
        print(f"  [{label}] {str(case.get('case_id')):<26} "
              f"expected={case.get('expected_status')} actual={case.get('actual_status')}")
    print()
    print("DELTA VS PREVIOUS")
    if delta is not None:
        print(f"  Score delta: {delta.get('scoreDelta'):+.4f} "
              f"(previous {delta.get('previousOverallScore'):.4f} -> "
              f"current {delta.get('currentOverallScore'):.4f})")
        for changed in delta.get("changedCases", []):
            print(f"  changed: {changed.get('caseId')} "
                  f"previous={changed.get('previousMatched')} current={changed.get('currentMatched')}")
    else:
        print("  none (first report or different suite)")
    print()
    print(f"STATUS: {'PASS' if summary.get('passedGate') else 'FAIL'}")
    print("=" * width)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cortexo deterministic regression harness")
    parser.add_argument("--mode", choices=["full", "grader", "software"], default="full")
    parser.add_argument("--suite", default=DEFAULT_SUITE)
    parser.add_argument("--json", action="store_true", help="print the full report as JSON after the summary")
    parser.add_argument("--no-history", action="store_true", help="do not write report artifacts")
    args = parser.parse_args(argv)

    requested = {
        "software": args.mode in ("full", "software"),
        "deterministic": args.mode in ("full", "grader"),
    }

    baseline = load_baseline(ROOT, suite=args.suite)
    required_score = float(baseline["requiredScore"])

    checks: list[CommandCheckResult] = []
    if requested["software"]:
        checks = software_checks()

    cases = []
    if requested["deterministic"]:
        cases = run_deterministic_cases(ROOT, suite=args.suite)

    report = build_report(
        suite=args.suite,
        baseline_sha=baseline_sha256(ROOT, suite=args.suite),
        git=git_metadata(ROOT),
        environment=environment_metadata(ROOT),
        checks=checks,
        cases=cases,
        required_score=required_score,
        requested=requested,
    )

    if not args.no_history:
        save_report(ROOT, report)

    _print_summary(report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))

    return 0 if report["summary"]["passedGate"] else 1


if __name__ == "__main__":
    sys.exit(main())