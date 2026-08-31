import os
import subprocess
from pathlib import Path

import pytest

from cortexo_ml.evaluation.candidate_extraction import (
    CandidateExtractionError,
    count_changed_lines,
    count_changed_lines_in_diff,
    extract_candidate,
    validate_diff_targets,
)
from cortexo_ml.evaluation.grader import (
    ExecutableGrader,
    STATUS_CANDIDATE_INVALID,
    STATUS_COMPILE_FAIL,
    STATUS_NOT_APPLICABLE,
    STATUS_NO_TESTS,
    STATUS_PASS,
    STATUS_PATCH_APPLY_FAIL,
    STATUS_POLICY,
    STATUS_TEST_FAIL,
    STATUS_TIMEOUT,
    grader_spec_for_task,
    load_grader_registry,
    parse_pytest_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

GOOD_CODE = (
    "def merge_dicts(left, right):\n"
    "    return {**left, **right}\n"
)


def micro_task(**overrides):
    task = {
        "task_id": "micro-codegen/merge_dicts",
        "task_type": "code_generation",
        "language": "python",
        "prompt": "implement merge_dicts",
        "timeout_seconds": 30,
    }
    task.update(overrides)
    return task


class FakeExecutor:
    def __init__(self):
        self.calls: list[dict] = []
        self.results: dict[str, dict] = {}

    def set(self, command_type: str, **fields):
        base = {"ok": True, "passed": True, "exitCode": 0, "stdout": "",
                "stderr": "", "durationMs": 5, "policy": False, "timedOut": False}
        base.update(fields)
        self.results[command_type] = base

    def execute(self, command_type, language, workspace, timeout_seconds):
        ws = Path(workspace)
        snap = {}
        for p in ws.rglob("*"):
            if p.is_file():
                try:
                    snap[p.relative_to(ws).as_posix()] = p.read_text(encoding="utf-8")
                except OSError:
                    snap[p.relative_to(ws).as_posix()] = "<unreadable>"
        self.calls.append({
            "commandType": command_type,
            "language": language,
            "workspace": str(ws),
            "timeoutSeconds": timeout_seconds,
            "files": snap,
        })
        return dict(self.results.get(command_type, {
            "ok": True, "passed": True, "exitCode": 0, "stdout": "",
            "stderr": "", "durationMs": 5, "policy": False, "timedOut": False,
        }))


def make_grader(executor=None):
    return ExecutableGrader(repo_root=REPO_ROOT, executor=executor)


# ------------------------------------------------------------- extraction

def test_extract_fenced_python_candidate():
    c = extract_candidate("thinking...\n```python\n" + GOOD_CODE + "```\n")
    assert c.kind == "full_file"
    assert "return {**left, **right}" in c.content
    assert len(c.sha256) == 64
    assert c.byte_count == len(c.content.encode("utf-8"))


def test_extract_raw_python_candidate():
    c = extract_candidate(GOOD_CODE)
    assert c.kind == "full_file"
    assert c.content == GOOD_CODE.strip()


def test_extract_unified_diff_candidate():
    diff = "--- a/solution.py\n+++ b/solution.py\n@@ -1 +1 @@\n-foo\n+bar\n"
    c = extract_candidate(diff)
    assert c.kind == "unified_diff"


def test_reject_empty_candidate():
    with pytest.raises(CandidateExtractionError):
        extract_candidate("   \n\n ")


def test_reject_oversized_candidate():
    with pytest.raises(CandidateExtractionError):
        extract_candidate("#" * (256 * 1024 + 1))


def test_reject_absolute_diff_path():
    diff = "--- a/out.py\n+++ /tmp/evil.py\n@@ -1 +1 @@\n-foo\n+bar\n"
    with pytest.raises(CandidateExtractionError):
        validate_diff_targets(diff, {"out.py"})


def test_reject_parent_traversal():
    diff = "--- a/out.py\n+++ b/../evil.py\n@@ -1 +1 @@\n-foo\n+bar\n"
    with pytest.raises(CandidateExtractionError):
        validate_diff_targets(diff, {"out.py"})


def test_reject_hidden_test_modification():
    diff = ("--- a/benches_hidden/test_out.py\n"
            "+++ b/benches_hidden/test_out.py\n"
            "@@ -1 +1 @@\n-assert 1\n+assert 0\n")
    with pytest.raises(CandidateExtractionError):
        validate_diff_targets(diff, {"out.py"})


def test_reject_unlisted_diff_target():
    diff = "--- a/other.py\n+++ b/other.py\n@@ -1 +1 @@\n-x\n+y\n"
    with pytest.raises(CandidateExtractionError):
        validate_diff_targets(diff, {"out.py"})


def test_reject_creation_and_deletion():
    diff = ("new file mode 100644\n--- /dev/null\n+++ b/evil.py\n"
            "@@ -0,0 +1 @@\n+import os\n")
    with pytest.raises(CandidateExtractionError):
        count = validate_diff_targets(diff, {"solution.py"})
        assert count  # pragma: no cover


def test_changed_lines_deterministic():
    assert count_changed_lines("a\nb\nc\n", "a\nx\nc\n") == 2
    assert count_changed_lines("a\nb\n", "a\nb\n") == 0
    diff = "--- a/solution.py\n+++ b/solution.py\n@@ -1,2 +1,2 @@\n def f():\n-    return 1\n+    return 2\n"
    assert count_changed_lines_in_diff(diff) == 2
    assert count_changed_lines_in_diff(diff) == count_changed_lines_in_diff(diff)


def test_sha256_stable_and_sensitive():
    one = extract_candidate(GOOD_CODE)
    two = extract_candidate(GOOD_CODE)
    other = extract_candidate("def g():\n    return 2\n")
    assert one.sha256 == two.sha256
    assert one.sha256 != other.sha256


def test_parse_pytest_summary_variants():
    assert (parse_pytest_summary("3 passed, 1 failed in 0.07s").passed_count,
            parse_pytest_summary("3 passed, 1 failed in 0.07s").failed_count,
            parse_pytest_summary("3 passed, 1 failed in 0.07s").collected_count) == (3, 1, 4)
    s = parse_pytest_summary("1 failed, 2 errors, 4 passed in 1.10s")
    assert (s.passed_count, s.failed_count, s.error_count, s.collected_count) == (4, 1, 2, 7)
    zero = parse_pytest_summary("no tests ran")
    assert (zero.passed_count, zero.failed_count, zero.collected_count) == (0, 0, 0)


def test_grader_registry_lookup():
    registry = load_grader_registry(REPO_ROOT)
    spec = grader_spec_for_task("micro-codegen/merge_dicts", registry)
    assert spec is not None
    assert spec["candidateTargets"] == ["solution.py"]
    assert grader_spec_for_task("unlisted/suite", registry) is None


# ----------------------------------------------------------------- grading

def test_full_file_candidate_passes():
    ex = FakeExecutor()
    ex.set("TEST", passed=True, exitCode=0, stdout="4 passed in 0.05s")
    result = make_grader(ex).grade(micro_task(), GOOD_CODE)
    assert result.status == STATUS_PASS
    assert result.passed is True
    assert result.applicable is True
    assert result.changed_files == ["solution.py"]
    assert result.test_summary.passed_count == 4
    assert result.candidate_kind == "full_file"
    assert result.patch_applied is True
    calls = [c["commandType"] for c in ex.calls]
    assert calls == ["COMPILE", "TEST"]


def test_workspace_deleted_after_grade():
    ex = FakeExecutor()
    ex.set("TEST", passed=True, exitCode=0, stdout="4 passed in 0.05s")
    make_grader(ex).grade(micro_task(), GOOD_CODE)
    assert ex.calls, "executor was never invoked"
    for call in ex.calls:
        assert not Path(call["workspace"]).exists()


def test_compile_failure_stops_before_tests():
    ex = FakeExecutor()
    ex.set("COMPILE", passed=False, exitCode=1, stderr="SyntaxError")
    result = make_grader(ex).grade(micro_task(), GOOD_CODE)
    assert result.status == STATUS_COMPILE_FAIL
    assert result.passed is False
    assert [c["commandType"] for c in ex.calls] == ["COMPILE"]


def test_test_failure_reports_summary():
    ex = FakeExecutor()
    ex.set("TEST", passed=False, exitCode=1, stdout="2 passed, 1 failed in 0.06s")
    result = make_grader(ex).grade(micro_task(), GOOD_CODE)
    assert result.status == STATUS_TEST_FAIL
    assert result.passed is False
    assert (result.test_summary.passed_count, result.test_summary.failed_count,
            result.test_summary.collected_count) == (2, 1, 3)


def test_no_tests_run_classified():
    ex = FakeExecutor()
    ex.set("TEST", passed=False, exitCode=5, stdout="no tests ran")
    result = make_grader(ex).grade(micro_task(), GOOD_CODE)
    assert result.status == STATUS_NO_TESTS
    assert result.test_summary.collected_count == 0


def test_sandbox_timeout_classified():
    ex = FakeExecutor()
    ex.set("TEST", timedOut=True, passed=False, exitCode=None, stderr="timeout")
    result = make_grader(ex).grade(micro_task(), GOOD_CODE)
    assert result.status == STATUS_TIMEOUT


def test_sandbox_policy_classified():
    ex = FakeExecutor()
    ex.set("TEST", policy=True, passed=False, exitCode=None, stderr="policy")
    result = make_grader(ex).grade(micro_task(), GOOD_CODE)
    assert result.status == STATUS_POLICY


def test_invalid_candidate_classified():
    result = make_grader(FakeExecutor()).grade(micro_task(), "   \n")
    assert result.status == STATUS_CANDIDATE_INVALID
    assert result.passed is False


def test_unregistered_task_not_applicable():
    result = make_grader(FakeExecutor()).grade(
        micro_task(task_id="other/suite"), GOOD_CODE)
    assert result.status == STATUS_NOT_APPLICABLE
    assert result.applicable is False


def test_bad_diff_classified_patch_apply_fail():
    task = micro_task()
    bad_diff = ("--- a/solution.py\n+++ b/solution.py\n"
                "@@ -1 +1 @@\n-this context does not exist\n+changed\n")
    result = make_grader(FakeExecutor()).grade(task, bad_diff)
    assert result.status == STATUS_PATCH_APPLY_FAIL


def test_candidate_only_writes_allowed_target():
    ex = FakeExecutor()
    ex.set("TEST", passed=True, exitCode=0, stdout="4 passed in 0.05s")
    result = make_grader(ex).grade(micro_task(), GOOD_CODE)
    test_call = next(c for c in ex.calls if c["commandType"] == "TEST")
    files = test_call["files"]
    assert "solution.py" in files
    assert any(p.startswith("benches_hidden/") for p in files), "hidden tests must be staged"
    candidate_files = [
        p for p, content in files.items()
        if not p.startswith("benches_hidden/") and content == GOOD_CODE.strip()
    ]
    assert candidate_files == ["solution.py"]
    assert result.candidate_sha256 and len(result.candidate_sha256) == 64


def test_diff_applies_without_shell():
    grader = make_grader()
    repo = Path(os.environ.get("TMPDIR", "/tmp")) / "cortexo-apply-test"
    if repo.exists():
        subprocess.run(["rm", "-rf", str(repo)], check=True)
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "merge.py").write_text("def merge_dicts(a, b):\n    return dict(a)\n", encoding="utf-8")
    env = dict(os.environ)
    env.setdefault("GIT_AUTHOR_NAME", "cortexo test")
    env.setdefault("GIT_AUTHOR_EMAIL", "test@cortexo.local")
    env.setdefault("GIT_COMMITTER_NAME", "cortexo test")
    env.setdefault("GIT_COMMITTER_EMAIL", "test@cortexo.local")
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, env=env)
    subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True, env=env)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=str(repo), check=True, env=env)
    diff = ("--- a/src/merge.py\n+++ b/src/merge.py\n"
            "@@ -1,2 +1,2 @@\n def merge_dicts(a, b):\n-    return dict(a)\n+    return {**a, **b}\n")
    grader._apply_diff(repo, diff)
    assert "{**a, **b}" in (repo / "src" / "merge.py").read_text(encoding="utf-8")

def test_compile_failure_result_serializes():
    """Regression: started timestamp must never populate test_stage."""
    executor = FakeExecutor()
    executor.set(
        "COMPILE",
        ok=True,
        passed=False,
        exitCode=1,
        stderr="compile failed",
    )

    grader = make_grader(executor)
    result = grader.grade(micro_task(), GOOD_CODE)

    assert result.status == STATUS_COMPILE_FAIL
    assert result.test_stage is None

    record = result.to_record()
    assert record["status"] == STATUS_COMPILE_FAIL
    assert record["testStage"] is None
    assert isinstance(record["durationMs"], int)


def test_patch_apply_failure_result_serializes():
    """Regression: failure results must remain safely serializable."""
    grader = make_grader()

    bad_diff = (
        "--- a/solution.py\n"
        "+++ b/solution.py\n"
        "@@ -1,2 +1,2 @@\n"
        " this line does not exist\n"
        "-old\n"
        "+new\n"
    )

    result = grader.grade(micro_task(), bad_diff)

    assert result.status == STATUS_PATCH_APPLY_FAIL
    assert result.test_stage is not None

    record = result.to_record()
    assert record["status"] == STATUS_PATCH_APPLY_FAIL
    assert isinstance(record["testStage"], dict)
    assert isinstance(record["durationMs"], int)


def test_compile_failure_result_serializes():
    """Regression: started timestamp must never populate test_stage."""
    executor = FakeExecutor()
    executor.set(
        "COMPILE",
        ok=True,
        passed=False,
        exitCode=1,
        stderr="compile failed",
    )

    grader = make_grader(executor)
    result = grader.grade(micro_task(), GOOD_CODE)

    assert result.status == STATUS_COMPILE_FAIL
    assert result.test_stage is None

    record = result.to_record()
    assert record["status"] == STATUS_COMPILE_FAIL
    assert record["testStage"] is None
    assert isinstance(record["durationMs"], int)


def test_patch_apply_failure_result_serializes():
    """Regression: failure results must remain safely serializable."""
    grader = make_grader()

    bad_diff = (
        "--- a/solution.py\n"
        "+++ b/solution.py\n"
        "@@ -1,2 +1,2 @@\n"
        " this line does not exist\n"
        "-old\n"
        "+new\n"
    )

    result = grader.grade(micro_task(), bad_diff)

    assert result.status == STATUS_PATCH_APPLY_FAIL
    assert result.test_stage is not None

    record = result.to_record()
    assert record["status"] == STATUS_PATCH_APPLY_FAIL
    assert isinstance(record["testStage"], dict)
    assert isinstance(record["durationMs"], int)


def test_compile_failure_result_serializes():
    """Regression: started timestamp must never populate test_stage."""
    executor = FakeExecutor()
    executor.set(
        "COMPILE",
        ok=True,
        passed=False,
        exitCode=1,
        stderr="compile failed",
    )

    grader = make_grader(executor)
    result = grader.grade(micro_task(), GOOD_CODE)

    assert result.status == STATUS_COMPILE_FAIL
    assert result.test_stage is None

    record = result.to_record()
    assert record["status"] == STATUS_COMPILE_FAIL
    assert record["testStage"] is None
    assert isinstance(record["durationMs"], int)


def test_patch_apply_failure_result_serializes():
    """Regression: failure results must remain safely serializable."""
    grader = make_grader()

    bad_diff = (
        "--- a/solution.py\n"
        "+++ b/solution.py\n"
        "@@ -1,2 +1,2 @@\n"
        " this line does not exist\n"
        "-old\n"
        "+new\n"
    )

    result = grader.grade(micro_task(), bad_diff)

    assert result.status == STATUS_PATCH_APPLY_FAIL
    assert result.test_stage is not None

    record = result.to_record()
    assert record["status"] == STATUS_PATCH_APPLY_FAIL
    assert isinstance(record["testStage"], dict)
    assert isinstance(record["durationMs"], int)


def test_compile_failure_result_serializes():
    """Regression: started timestamp must never populate test_stage."""
    executor = FakeExecutor()
    executor.set(
        "COMPILE",
        ok=True,
        passed=False,
        exitCode=1,
        stderr="compile failed",
    )

    grader = make_grader(executor)
    result = grader.grade(micro_task(), GOOD_CODE)

    assert result.status == STATUS_COMPILE_FAIL
    assert result.test_stage is None

    record = result.to_record()
    assert record["status"] == STATUS_COMPILE_FAIL
    assert record["testStage"] is None
    assert isinstance(record["durationMs"], int)


def test_patch_apply_failure_result_serializes():
    """Regression: failure results must remain safely serializable."""
    grader = make_grader()

    bad_diff = (
        "--- a/solution.py\n"
        "+++ b/solution.py\n"
        "@@ -1,2 +1,2 @@\n"
        " this line does not exist\n"
        "-old\n"
        "+new\n"
    )

    result = grader.grade(micro_task(), bad_diff)

    assert result.status == STATUS_PATCH_APPLY_FAIL
    assert result.test_stage is not None

    record = result.to_record()
    assert record["status"] == STATUS_PATCH_APPLY_FAIL
    assert isinstance(record["testStage"], dict)
    assert isinstance(record["durationMs"], int)



def test_real_grader_workspace_is_sandbox_traversable():
    """Sandbox UID must be able to traverse the grader's temporary workspace."""
    import stat

    class PermissionRecordingExecutor:
        def __init__(self):
            self.modes = []

        def execute(self, command_type, language, workspace, timeout_seconds):
            mode = stat.S_IMODE(Path(workspace).stat().st_mode)
            self.modes.append(mode)

            if command_type == "COMPILE":
                return {
                    "ok": True,
                    "passed": True,
                    "exitCode": 0,
                    "stdout": "",
                    "stderr": "",
                    "durationMs": 1,
                    "policy": False,
                    "timedOut": False,
                }

            return {
                "ok": True,
                "passed": True,
                "exitCode": 0,
                "stdout": "4 passed in 0.01s",
                "stderr": "",
                "durationMs": 1,
                "policy": False,
                "timedOut": False,
            }

    executor = PermissionRecordingExecutor()
    result = make_grader(executor).grade(micro_task(), GOOD_CODE)

    assert result.status == STATUS_PASS
    assert executor.modes
    assert all(mode == 0o755 for mode in executor.modes)
