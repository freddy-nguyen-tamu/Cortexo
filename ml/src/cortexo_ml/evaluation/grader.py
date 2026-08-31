"""Executable hidden-test grader.

Runs a model-generated candidate through a trusted, restricted sandbox:

    generation complete
      -> ephemeral workspace
      -> stage fixture/source
      -> apply candidate (allow-list only)
      -> stage hidden tests (AFTER generation)
      -> sandbox COMPILE
      -> sandbox TEST
      -> classify PASS / COMPILE_FAIL / TEST_FAIL / SANDBOX_TIMEOUT / ...
      -> delete workspace

The grader is evaluator-only. Hidden tests, gold files and the registry are
never sent to the model, and candidate module code is never imported on the
host.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from cortexo_ml.evaluation.candidate_extraction import (
    CandidateExtractionError,
    count_changed_lines,
    count_changed_lines_in_diff,
    extract_candidate,
    normalize_diff_target,
    validate_diff_targets,
)

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(os.environ.get("CORTEXO_REPO_ROOT", DEFAULT_REPO_ROOT)).resolve()
BENCHMARKS_ROOT = REPO_ROOT / "benchmarks"

MAX_STAGE_OUTPUT_CHARS = 64 * 1024  # per-field log cap in serialized records

STATUS_PASS = "PASS"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
STATUS_CANDIDATE_INVALID = "CANDIDATE_INVALID"
STATUS_PATCH_APPLY_FAIL = "PATCH_APPLY_FAIL"
STATUS_COMPILE_FAIL = "COMPILE_FAIL"
STATUS_TEST_FAIL = "TEST_FAIL"
STATUS_NO_TESTS = "NO_TESTS"
STATUS_TIMEOUT = "SANDBOX_TIMEOUT"
STATUS_POLICY = "SANDBOX_POLICY"
STATUS_WORKSPACE_ERROR = "WORKSPACE_ERROR"
STATUS_INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class ExecutionStageResult:
    attempted: bool = False
    passed: bool = False
    exit_code: int | None = None
    timed_out: bool = False
    policy_violation: bool = False
    duration_ms: int = 0
    stdout: str = ""
    stderr: str = ""

    def to_record(self) -> dict:
        return {
            "attempted": self.attempted,
            "passed": self.passed,
            "exitCode": self.exit_code,
            "timedOut": self.timed_out,
            "policyViolation": self.policy_violation,
            "durationMs": self.duration_ms,
            "stdout": self.stdout[:MAX_STAGE_OUTPUT_CHARS],
            "stderr": self.stderr[:MAX_STAGE_OUTPUT_CHARS],
        }


@dataclass
class TestSummary:
    passed_count: int = 0
    failed_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    collected_count: int = 0

    def to_record(self) -> dict:
        return {
            "passedCount": self.passed_count,
            "failedCount": self.failed_count,
            "errorCount": self.error_count,
            "skippedCount": self.skipped_count,
            "collectedCount": self.collected_count,
        }


@dataclass
class GraderResult:
    applicable: bool
    passed: bool
    status: str
    candidate_kind: str | None = None
    candidate_sha256: str | None = None
    candidate_bytes: int = 0
    changed_files: list[str] = field(default_factory=list)
    changed_lines: int = 0
    compile: ExecutionStageResult | None = None
    test_stage: ExecutionStageResult | None = None
    test_summary: TestSummary = field(default_factory=TestSummary)
    patch_applied: bool = False
    duration_ms: int = 0

    def to_record(self) -> dict:
        return {
            "applicable": self.applicable,
            "passed": self.passed,
            "status": self.status,
            "candidateKind": self.candidate_kind,
            "candidateSha256": self.candidate_sha256,
            "candidateBytes": self.candidate_bytes,
            "changedFiles": list(self.changed_files),
            "changedLines": self.changed_lines,
            "compile": self.compile.to_record() if self.compile else None,
            "testStage": self.test_stage.to_record() if self.test_stage else None,
            "testSummary": self.test_summary.to_record(),
            "patchApplied": self.patch_applied,
            "durationMs": self.duration_ms,
        }


_RESULT_PASSED_RE = re.compile(r"(\d+)\s+passed")
_RESULT_FAILED_RE = re.compile(r"(\d+)\s+failed")
_RESULT_ERRORS_RE = re.compile(r"(\d+)\s+errors")
_RESULT_SKIPPED_RE = re.compile(r"(\d+)\s+skipped")
_NO_TESTS_RE = re.compile(r"no tests ran", re.IGNORECASE)


def parse_pytest_summary(text: str) -> TestSummary:
    """Parse pytest's final summary line(s) from stdout/stderr.

    Handles: "4 passed", "3 passed, 1 failed", "1 failed, 2 errors, 4 passed",
    "2 skipped, 1 warning". A run with no collected tests yields collected 0.
    """
    def _first(pattern: re.Pattern) -> int:
        m = pattern.search(text)
        return int(m.group(1)) if m else 0

    passed = _first(_RESULT_PASSED_RE)
    failed = _first(_RESULT_FAILED_RE)
    errors = _first(_RESULT_ERRORS_RE)
    skipped = _first(_RESULT_SKIPPED_RE)

    known = passed + failed + errors + skipped
    if _NO_TESTS_RE.search(text):
        return TestSummary(passed_count=0, failed_count=0, error_count=0,
                           skipped_count=0, collected_count=0)
    return TestSummary(
        passed_count=passed,
        failed_count=failed,
        error_count=errors,
        skipped_count=skipped,
        collected_count=known,
    )


class SandboxExecutor:
    """Default grader executor: the trusted sandbox runner via subprocess.

    The model never controls any argv element; only commandType + language
    (plus the bounded timeout) reach the policy layer.
    """

    def __init__(self, repo_root: Path | None = None, image: str | None = None):
        self.repo_root = Path(repo_root or REPO_ROOT).resolve()
        self.image = image or os.environ.get("CORTEXO_SANDBOX_IMAGE", "cortexo-sandbox:latest")
        self.runner_script = self.repo_root / "sandbox" / "runner.py"

    def execute(self, command_type: str, language: str, workspace: Path, timeout_seconds: int) -> dict:
        if not self.runner_script.exists():
            raise OSError(f"sandbox runner not found: {self.runner_script}")
        request = {
            "workspaceId": f"grader-{abs(hash(str(workspace))) & 0x7fffffff}",
            "commandType": command_type,
            "language": language,
            "timeoutSeconds": int(timeout_seconds),
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, prefix="cortexo-grader-req-") as fh:
            json.dump(request, fh)
            request_file = fh.name
        try:
            argv = [
                sys.executable,
                str(self.runner_script),
                "--request-file", request_file,
                "--workspace", str(workspace),
                "--keep-workspace",
            ]
            env = dict(os.environ)
            env["CORTEXO_SANDBOX_IMAGE"] = self.image
            proc = subprocess.run(
                argv,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=int(timeout_seconds) + 60,
                env=env,
            )
            if proc.returncode not in (0, 1):
                return {"ok": False, "policy": False, "error": "RUNNER_FAILED",
                        "exitCode": proc.returncode, "stdout": proc.stdout[:MAX_STAGE_OUTPUT_CHARS],
                        "stderr": proc.stderr[:MAX_STAGE_OUTPUT_CHARS], "passed": False}
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                return {"ok": False, "policy": False, "error": "RUNNER_BAD_OUTPUT",
                        "exitCode": None, "stdout": proc.stdout[:MAX_STAGE_OUTPUT_CHARS],
                        "stderr": proc.stderr[:MAX_STAGE_OUTPUT_CHARS], "passed": False}
        except subprocess.TimeoutExpired:
            return {"ok": False, "policy": False, "error": "RUNNER_TIMEOUT",
                    "exitCode": None, "stdout": "", "stderr": "sandbox runner timeout", "passed": False,
                    "timedOut": True}
        finally:
            try:
                os.unlink(request_file)
            except OSError:
                pass


def load_grader_registry(repo_root: Path | None = None) -> dict:
    root = Path(repo_root or REPO_ROOT)
    path = root / "benchmarks" / "suites" / "grader_registry.json"
    if not path.exists():
        raise FileNotFoundError(f"grader registry not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def grader_spec_for_task(task_id: str, registry: dict | None = None, repo_root: Path | None = None) -> dict | None:
    data = registry if registry is not None else load_grader_registry(repo_root)
    return data.get(task_id)


class ExecutableGrader:
    """Runs one candidate through sandbox compile + hidden tests."""

    def __init__(self, repo_root: Path | None = None, executor: SandboxExecutor | None = None,
                 registry: dict | None = None):
        self.repo_root = Path(repo_root or REPO_ROOT).resolve()
        self.benchmarks_root = self.repo_root / "benchmarks"
        if not self.benchmarks_root.is_dir():
            raise FileNotFoundError(f"benchmarks root not found: {self.benchmarks_root}")
        self.registry = registry if registry is not None else load_grader_registry(self.repo_root)
        self.executor = executor or SandboxExecutor(repo_root=self.repo_root)

    # ------------------------------------------------------------------ API

    def grade(self, task: dict, output: str) -> GraderResult:
        started = time.monotonic()
        task_id = task.get("task_id", "")
        spec = grader_spec_for_task(task_id, self.registry)
        if spec is None:
            return GraderResult(applicable=False, passed=False, status=STATUS_NOT_APPLICABLE,
                                duration_ms=int((time.monotonic() - started) * 1000))

        try:
            candidate = extract_candidate(output, language=task.get("language", "python"))
        except CandidateExtractionError as exc:
            return GraderResult(applicable=True, passed=False, status=STATUS_CANDIDATE_INVALID,
                                changed_lines=0, duration_ms=int((time.monotonic() - started) * 1000),
                                candidate_kind=None, candidate_sha256=None,
                                test_stage=self._policy_stage_from_error(str(exc)))

        workspace = tempfile.mkdtemp(prefix="cortexo-grader-")
        try:
            return self._grade_in_workspace(task, spec, candidate, Path(workspace), started)
        except OSError as exc:
            return GraderResult(applicable=True, passed=False, status=STATUS_WORKSPACE_ERROR,
                                candidate_kind=candidate.kind, candidate_sha256=candidate.sha256,
                                candidate_bytes=candidate.byte_count,
                                duration_ms=int((time.monotonic() - started) * 1000),
                                test_stage=self._policy_stage_from_error(str(exc)))
        except Exception as exc:  # noqa: BLE001 - grader must degrade, never crash the API
            return GraderResult(applicable=True, passed=False, status=STATUS_INTERNAL_ERROR,
                                candidate_kind=candidate.kind, candidate_sha256=candidate.sha256,
                                candidate_bytes=candidate.byte_count,
                                duration_ms=int((time.monotonic() - started) * 1000),
                                test_stage=self._policy_stage_from_error(str(exc)))
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    # ------------------------------------------------------------ internals

    @staticmethod
    def _policy_stage_from_error(message: str) -> ExecutionStageResult:
        return ExecutionStageResult(attempted=True, passed=False, stderr=message[:MAX_STAGE_OUTPUT_CHARS])

    def _grade_in_workspace(self, task: dict, spec: dict, candidate, workspace: Path, started: float) -> GraderResult:
        language = task.get("language", "python")
        timeout_seconds = int(task.get("timeout_seconds", 60))
        targets = list(spec.get("candidateTargets", []))
        allow = set(targets)

        self._fixture_stage(spec, workspace)

        patch_applied = False
        changed_files: list[str] = []
        changed_lines = 0
        if candidate.kind == "unified_diff":
            try:
                changed = validate_diff_targets(candidate.content, allow)
                if len(changed) == 1 and allow == {targets[0]}:
                    name = changed[0]
                    if name != targets[0] and _basename(name) == _basename(targets[0]):
                        candidate_content = normalize_diff_target(candidate.content, targets[0])
                    else:
                        candidate_content = candidate.content
                else:
                    candidate_content = candidate.content
                self._apply_diff(workspace, candidate_content)
            except CandidateExtractionError as exc:
                return self._result(
                    False,
                    STATUS_CANDIDATE_INVALID,
                    candidate,
                    changed_files,
                    0,
                    None,
                    started=started,
                    patch_applied=False,
                    message=str(exc),
                )
            except PatchApplyFailure as exc:
                return self._result(
                    False,
                    STATUS_PATCH_APPLY_FAIL,
                    candidate,
                    list(changed),
                    0,
                    None,
                    started=started,
                    patch_applied=False,
                    message=str(exc),
                )
            changed_files = list(changed)
            changed_lines = count_changed_lines_in_diff(candidate.content)
            patch_applied = True
        else:
            if len(targets) != 1:
                return self._result(
                    False,
                    STATUS_CANDIDATE_INVALID,
                    candidate,
                    [],
                    0,
                    None,
                    started=started,
                    message="full-file candidate requires exactly one candidate target",
                )
            target = targets[0]
            original = (workspace / target).read_text(encoding="utf-8") if (workspace / target).exists() else ""
            (workspace / target).write_text(candidate.content, encoding="utf-8")
            changed_files = [target]
            changed_lines = count_changed_lines(original, candidate.content)
            patch_applied = True

        self._stage_hidden_tests(spec, workspace)

        compile_stage = self._run_stage("COMPILE", language, workspace, timeout_seconds)
        if compile_stage.timed_out:
            return self._result(
                False,
                STATUS_TIMEOUT,
                candidate,
                changed_files,
                changed_lines,
                compile_stage,
                started=started,
                patch_applied=patch_applied,
            )
        if compile_stage.policy_violation:
            return self._result(
                False,
                STATUS_POLICY,
                candidate,
                changed_files,
                changed_lines,
                compile_stage,
                started=started,
                patch_applied=patch_applied,
            )
        if not compile_stage.passed:
            return self._result(
                False,
                STATUS_COMPILE_FAIL,
                candidate,
                changed_files,
                changed_lines,
                compile_stage,
                started=started,
                patch_applied=patch_applied,
            )

        test_stage = self._run_stage("TEST", language, workspace, timeout_seconds)
        if test_stage.timed_out:
            return self._result(
                False,
                STATUS_TIMEOUT,
                candidate,
                changed_files,
                changed_lines,
                compile_stage,
                test_stage=test_stage,
                started=started,
                patch_applied=patch_applied,
            )
        if test_stage.policy_violation:
            return self._result(
                False,
                STATUS_POLICY,
                candidate,
                changed_files,
                changed_lines,
                compile_stage,
                test_stage=test_stage,
                started=started,
                patch_applied=patch_applied,
            )

        summary = parse_pytest_summary(test_stage.stdout + "\n" + test_stage.stderr)
        if summary.collected_count == 0:
            return self._result(
                False,
                STATUS_NO_TESTS,
                candidate,
                changed_files,
                changed_lines,
                compile_stage,
                test_stage=test_stage,
                started=started,
                patch_applied=patch_applied,
                summary=summary,
            )
        if test_stage.passed:
            status = STATUS_PASS
            passed = True
        else:
            status = STATUS_TEST_FAIL
            passed = False
        return self._result(
            passed,
            status,
            candidate,
            changed_files,
            changed_lines,
            compile_stage,
            test_stage=test_stage,
            started=started,
            patch_applied=patch_applied,
            summary=summary,
        )

    def _result(
        self,
        passed,
        status,
        candidate,
        changed_files,
        changed_lines,
        compile_stage,
        *,
        test_stage=None,
        started=None,
        patch_applied=False,
        summary=None,
        message: str | None = None,
    ):
        duration = int((time.monotonic() - started) * 1000) if started is not None else 0
        if message and test_stage is None:
            test_stage = self._policy_stage_from_error(message)
        return GraderResult(
            applicable=True,
            passed=bool(passed),
            status=status,
            candidate_kind=candidate.kind,
            candidate_sha256=candidate.sha256,
            candidate_bytes=candidate.byte_count,
            changed_files=changed_files,
            changed_lines=changed_lines,
            compile=compile_stage,
            test_stage=test_stage,
            test_summary=summary or TestSummary(),
            patch_applied=patch_applied,
            duration_ms=duration,
        )

    def _fixture_stage(self, spec: dict, workspace: Path) -> None:
        kind = spec.get("kind")
        if kind == "standalone_python":
            return
        if kind == "single_file_fixture":
            source = self.benchmarks_root / spec["fixtureSource"]
            target = Path(spec["candidateTargets"][0])
            if not source.exists():
                raise OSError(f"fixture source not found: {source}")
            (workspace / target.parent).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, workspace / target)
            return
        if kind == "repository_fixture":
            source = self.benchmarks_root / spec["fixtureSource"]
            if not source.is_dir():
                raise OSError(f"fixture repository not found: {source}")
            shutil.copytree(source, workspace, dirs_exist_ok=True)
            return
        raise OSError(f"unknown fixture kind: {kind}")

    def _stage_hidden_tests(self, spec: dict, workspace: Path) -> None:
        hidden = spec.get("hiddenTests") or []
        hidden_dir = workspace / "benches_hidden"
        hidden_dir.mkdir(parents=True, exist_ok=True)
        for rel in hidden:
            src = self.benchmarks_root / rel
            if not src.exists():
                raise OSError(f"hidden test not found: {src}")
            shutil.copyfile(src, hidden_dir / src.name)

    def _apply_diff(self, workspace: Path, diff_text: str) -> None:
        check = subprocess.run(
            ["git", "apply", "--check", "--whitespace=nowarn"],
            input=diff_text,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check.returncode != 0:
            raise PatchApplyFailure(check.stderr)
        applied = subprocess.run(
            ["git", "apply", "--whitespace=nowarn"],
            input=diff_text,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if applied.returncode != 0:
            raise PatchApplyFailure(applied.stderr)

    def _run_stage(self, command_type: str, language: str, workspace: Path, timeout_seconds: int) -> ExecutionStageResult:
        try:
            out = self.executor.execute(command_type, language, workspace, timeout_seconds)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return ExecutionStageResult(attempted=True, passed=False, timed_out=True,
                                        stderr=str(exc)[:MAX_STAGE_OUTPUT_CHARS])
        policy = bool(out.get("policy")) or (bool(out.get("error")) and out.get("error") == "SANDBOX_POLICY")
        return ExecutionStageResult(
            attempted=True,
            passed=bool(out.get("passed")),
            exit_code=out.get("exitCode"),
            timed_out=bool(out.get("timedOut")),
            policy_violation=policy,
            duration_ms=int(out.get("durationMs", 0) or 0),
            stdout=str(out.get("stdout") or "")[:MAX_STAGE_OUTPUT_CHARS],
            stderr=str(out.get("stderr") or "")[:MAX_STAGE_OUTPUT_CHARS],
        )


class PatchApplyFailure(Exception):
    pass


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]