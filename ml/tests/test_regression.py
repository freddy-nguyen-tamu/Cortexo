import json
from pathlib import Path

import pytest

from cortexo_ml.data.collect import collect_directory, path_should_skip
from cortexo_ml.evaluation.regression import (
    DEFAULT_SUITE,
    HARNESS_ERROR,
    CommandCheckResult,
    DeterministicCaseResult,
    RegressionBaselineError,
    baseline_sha256,
    build_report,
    history_summaries,
    is_case_matched,
    load_baseline,
    load_canonical_task_map,
    load_latest_report,
    public_regression_report,
    public_regression_summary,
    regression_report_dir,
    run_deterministic_cases,
    save_report,
    score_cases,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINES_ROOT = REPO_ROOT / "benchmarks" / "baselines"


def _good(overrides: dict | None = None) -> DeterministicCaseResult:
    return DeterministicCaseResult(
        case_id="g",
        category="executable-grading",
        task_id="micro-codegen/merge_dicts",
        expected_status="PASS",
        actual_status="PASS",
        expected_passed=True,
        actual_passed=True,
        matched=True,
        **(overrides or {}),
    )


def _report(**overrides) -> dict:
    defaults = dict(
        suite="deterministic-v1",
        baseline_sha="baseline-sha",
        git={"shortCommit": "a" * 7, "branch": "main", "dirty": False},
        environment={"platform": "linux", "python": "3.11"},
        checks=[],
        cases=[_good()],
        required_score=1.0,
        requested={"software": False, "deterministic": True},
    )
    defaults.update(overrides)
    return build_report(**defaults)


# ------------------------------------------------ committed baseline

def test_baseline_loads():
    baseline = load_baseline(REPO_ROOT)
    assert isinstance(baseline["cases"], list)
    assert len(baseline["cases"]) == 11


def test_baseline_suite_version():
    assert DEFAULT_SUITE == "deterministic-v1"
    assert load_baseline(REPO_ROOT)["suiteVersion"] == "deterministic-v1"


def test_baseline_required_score():
    assert load_baseline(REPO_ROOT)["requiredScore"] == 1.0


def test_baseline_case_ids_unique():
    baseline = load_baseline(REPO_ROOT)
    ids = [case["id"] for case in baseline["cases"]]
    assert len(ids) == len(set(ids))


def test_baseline_has_known_good_and_known_bad():
    baseline = load_baseline(REPO_ROOT)
    assert any(case["expectedPassed"] for case in baseline["cases"])
    assert any(not case["expectedPassed"] for case in baseline["cases"])


@pytest.mark.parametrize("forbidden", ["command", "argv", "hiddenTest", "hidden_test",
                                        "testCommand", "compileCommand"])
def test_baseline_forbids_commandish_keys(forbidden):
    baseline = load_baseline(REPO_ROOT)
    for case in baseline["cases"]:
        assert forbidden not in case


def test_baseline_candidates_stay_inside_baseline_root():
    baseline = load_baseline(REPO_ROOT)
    for case in baseline["cases"]:
        candidate = (BASELINES_ROOT / case["candidate"]).resolve()
        assert BASELINES_ROOT == candidate or BASELINES_ROOT in candidate.parents


def test_baseline_every_candidate_exists():
    baseline = load_baseline(REPO_ROOT)
    for case in baseline["cases"]:
        assert (BASELINES_ROOT / case["candidate"]).is_file()


def test_baseline_every_task_id_in_canonical_map():
    task_map = load_canonical_task_map(REPO_ROOT)
    baseline = load_baseline(REPO_ROOT)
    assert "micro-codegen/merge_dicts" in task_map
    for case in baseline["cases"]:
        assert case["taskId"] in task_map


# ------------------------------------------------------ scoring math

def test_score_cases_hundred_percent_for_expected_failures():
    results = [
        DeterministicCaseResult("a", "exe", "t", "PASS", "PASS", True, True, True),
        DeterministicCaseResult("b", "clf", "t", "TEST_FAIL", "TEST_FAIL", False, False, True),
        DeterministicCaseResult("c", "clf", "t", "TEST_FAIL", "TEST_FAIL", False, False, True),
    ]
    s = score_cases(results)
    assert (s["passed"], s["total"]) == (3, 3)
    assert s["percent"] == 100.0
    assert ("TEST_FAIL" in s["byCategory"]["clf"]) or s["byCategory"]["clf"]["passed"] == 2
    assert s["byCategory"]["clf"] == {"passed": 2, "total": 2}


def test_score_drops_when_expected_test_fail_becomes_compile_fail():
    results = [
        DeterministicCaseResult("bad", "clf", "t", "TEST_FAIL", "COMPILE_FAIL", False, False,
                                is_case_matched("TEST_FAIL", "COMPILE_FAIL", False, False)),
        DeterministicCaseResult("good", "exe", "t", "PASS", "PASS", True, True, True),
    ]
    assert results[0].matched is False
    assert results[1].matched is True
    s = score_cases(results)
    assert s["percent"] == 50.0


def test_matched_semantics():
    assert is_case_matched("TEST_FAIL", "TEST_FAIL", False, False) is True
    assert is_case_matched("TEST_FAIL", "COMPILE_FAIL", False, False) is False
    assert is_case_matched("PASS", "PASS", True, True) is True
    assert is_case_matched("PASS", "TEST_FAIL", True, False) is False


# ---------------------------------------------------- public sanitization

def test_public_report_strips_stdout_stderr_and_command():
    check = CommandCheckResult("python-compile", "python", True, 42, 0,
                               ["python", "-m", "compileall"], "sekrit_stdout", "sekrit_stderr")
    report = _report(checks=[check], requested={"software": True, "deterministic": False})
    public = public_regression_report(report)
    public_json = json.dumps(public)
    assert "sekrit_stdout" not in public_json
    assert "sekrit_stderr" not in public_json
    assert "command" not in public["checks"][0]
    assert public["checks"][0]["check_id"] == "python-compile"
    assert public["checks"][0]["passed"] is True


def test_public_report_omits_candidate_source_and_gold():
    report = _report(cases=[_good()])
    public = public_regression_report(report)
    public_json = json.dumps(public)
    assert "candidate_source" not in public_json
    assert "content" not in public["cases"][0]
    assert "gold_patch" not in public_json
    assert "expected_behavior" not in public_json
    assert public["cases"][0]["expected_status"] == "PASS"


def test_public_summary_shape():
    s = public_regression_summary(_report())
    assert s["suiteVersion"] == "deterministic-v1"
    assert s["git"]["shortCommit"] == "a" * 7
    assert "summary" in s


# ---------------------------------------------------- report persistence

def test_load_latest_report_missing_returns_none(tmp_path):
    assert load_latest_report(tmp_path) is None


def test_save_report_writes_timestamped_and_latest(tmp_path):
    save_report(tmp_path, _report())
    report_dir = regression_report_dir(tmp_path)
    files = sorted(report_dir.glob("*.json"))
    assert len(files) == 2
    names = [f.name for f in files]
    assert "latest.json" in names
    loaded = load_latest_report(tmp_path)
    assert loaded["suiteVersion"] == "deterministic-v1"
    assert loaded["baselineSha256"] == "baseline-sha"
    assert "delta" not in loaded


def test_save_report_computes_delta_same_suite(tmp_path):
    first = _report(git={"shortCommit": "a" * 7, "branch": "main", "dirty": False})
    save_report(tmp_path, first)
    second = _report(git={"shortCommit": "b" * 7, "branch": "main", "dirty": False})
    save_report(tmp_path, second)
    loaded = load_latest_report(tmp_path)
    assert loaded["delta"] is not None
    assert loaded["delta"]["scoreDelta"] == 0.0
    assert loaded["delta"]["changedCases"] == []


def test_history_summaries_skip_latest_and_preserve_historical(tmp_path):
    save_report(tmp_path, _report(git={"shortCommit": "a" * 7, "dirty": False}))
    assert len(history_summaries(tmp_path)) == 1
    save_report(tmp_path, _report(git={"shortCommit": "b" * 7, "dirty": False}))
    report_dir = regression_report_dir(tmp_path)
    assert len(list(report_dir.glob("*.json"))) == 3  # 2 timestamped + latest.json
    assert len(history_summaries(tmp_path)) == 2


def test_history_limit_clamped(tmp_path):
    for i in range(4):
        save_report(tmp_path, _report(git={"shortCommit": f"{i:07}"}))
    assert len(history_summaries(tmp_path, limit=2)) == 2
    assert len(history_summaries(tmp_path, limit=10000)) == 4
    assert len(history_summaries(tmp_path, limit=0)) == 1
    assert len(history_summaries(tmp_path, limit=-5)) == 1


# ------------------------------------------------- training-data integrity

def test_collector_skips_baselines():
    assert path_should_skip("benchmarks/baselines/deterministic-v1.json")[0]
    assert path_should_skip("benchmarks/baselines/fixtures/correct/merge_dicts.py") == (True, "evaluation-baseline")
    assert path_should_skip("benchmarks/baselines/fixtures/incorrect/merge_dicts.py")[0]
    assert path_should_skip("benchmarks/hidden_tests/micro_codegen/test_a.py")[0]


def test_collection_integration_never_copies_correct_candidate(tmp_path):
    demo = tmp_path / "repo"
    candidate = demo / "benchmarks" / "baselines" / "fixtures" / "correct"
    candidate.mkdir(parents=True)
    (demo / "benchmarks" / "tasks").mkdir(parents=True)
    (candidate / "merge_dicts.py").write_text("SECRET_CANDIDATE_ANSWER", encoding="utf-8")
    (demo / "benchmarks" / "tasks" / "a.json").write_text("[]", encoding="utf-8")

    entry = {"sourceId": "s", "source_type": "repository", "license": "Apache-2.0"}
    report = collect_directory("s", demo, entry, tmp_path / "out")
    collected = "".join(f.content for f in report.collected)
    assert "SECRET_CANDIDATE_ANSWER" not in collected


# -------------------------------------------------- case-loop integration

def _content_lookup() -> dict:
    baseline = load_baseline(REPO_ROOT)
    lookup: dict[str, dict] = {}
    for case in baseline["cases"]:
        text = (BASELINES_ROOT / case["candidate"]).read_text(encoding="utf-8").strip()
        bucket = lookup.setdefault(case["taskId"], {})
        bucket[text] = (case["expectedStatus"], case["expectedPassed"])
    return lookup


class _Result:
    def __init__(self, record: dict):
        self.record = record

    def to_record(self) -> dict:
        return dict(self.record)


class _ContentGrader:
    def __init__(self, lookup: dict):
        self.lookup = lookup
        self.seen_tasks: list[dict] = []
        self.seen_outputs: list[str] = []

    def grade(self, task, output) -> _Result:
        self.seen_tasks.append(task)
        self.seen_outputs.append(output)
        status, passed = self.lookup[task["task_id"]].get(output.strip(), ("PASS", True))
        return _Result({"status": status, "passed": passed, "durationMs": 1,
                        "candidateSha256": "deadbeef", "changedFiles": ["solution.py"],
                        "changedLines": 2})


def test_run_deterministic_cases_matches_fixture_tables():
    grader = _ContentGrader(_content_lookup())
    results = run_deterministic_cases(REPO_ROOT, grader=grader)
    assert len(results) == 11
    assert all(r.matched for r in results)
    bad = next(r for r in results if r.case_id == "merge-dicts-bad")
    assert bad.expected_status == "TEST_FAIL"
    assert bad.actual_status == "TEST_FAIL"
    assert bad.matched is True
    syntax = next(r for r in results if r.case_id == "merge-dicts-syntax-error")
    assert syntax.expected_status == "COMPILE_FAIL"
    assert syntax.matched is True
    assert isinstance(score_cases(results)["percent"], float)


def test_run_deterministic_cases_uses_full_canonical_task():
    grader = _ContentGrader(_content_lookup())
    run_deterministic_cases(REPO_ROOT, grader=grader)
    assert len(grader.seen_tasks) == 11
    merge = next(t for t in grader.seen_tasks if t["task_id"] == "micro-codegen/merge_dicts")
    assert "expected_behavior" in merge  # trusted grader receives canonical evaluator info
    assert "test_command" in merge
    assert len(grader.seen_outputs) == 11


class _RaisingGrader(_ContentGrader):
    def grade(self, task, output) -> _Result:
        if output.strip().startswith("def merge_dicts"):
            raise RuntimeError("boom")
        return super().grade(task, output)


def test_harness_error_isolated_and_keeps_going():
    grader = _RaisingGrader(_content_lookup())
    results = run_deterministic_cases(REPO_ROOT, grader=grader)
    assert len(results) == 11
    broken = 0
    matched = 0
    for r in results:
        if "merge-dicts" in r.case_id:
            assert r.actual_status == HARNESS_ERROR
            assert r.matched is False
            assert "RuntimeError" in r.message
            broken += 1
        else:
            assert r.matched is True
            matched += 1
    assert broken == 3
    assert matched == 8


# --------------------------------------------------------- gate modes

def test_grader_only_mode_gate_ignores_software():
    report = _report(checks=[], cases=[_good()], requested={"software": False, "deterministic": True})
    summary = report["summary"]
    assert summary["software"]["total"] == 0
    assert summary["passedGate"] is True
    assert summary["requiredDeterministicScore"] == 1.0
    assert summary["overall"]["total"] == 1


def test_software_only_mode_ignores_deterministic():
    report = _report(checks=[CommandCheckResult("python-tests", "python", True, 1, 0, [], "", "")],
                     cases=[], requested={"software": True, "deterministic": False})
    summary = report["summary"]
    assert summary["deterministic"]["total"] == 0
    assert summary["passedGate"] is True
    assert summary["overall"]["total"] == 1


def test_gate_fails_on_deterministic_mismatch():
    bad = DeterministicCaseResult("bad", "clf", "t", "TEST_FAIL", "COMPILE_FAIL", False, False,
                                  is_case_matched("TEST_FAIL", "COMPILE_FAIL", False, False))
    report = _report(cases=[bad], requested={"software": True, "deterministic": True})
    assert report["summary"]["passedGate"] is False


# --------------------------------------------------- baseline validation

def _write_baseline(root: Path, payload: dict):
    (root / "benchmarks" / "baselines").mkdir(parents=True, exist_ok=True)
    (root / "benchmarks" / "baselines" / "deterministic-v1.json").write_text(
        json.dumps(payload), encoding="utf-8")


def test_baseline_rejects_path_escape(tmp_path):
    _write_baseline(tmp_path, {
        "suiteVersion": "deterministic-v1",
        "requiredScore": 1.0,
        "cases": [{
            "id": "a", "category": "exe", "taskId": "micro-codegen/merge_dicts",
            "candidate": "fixtures/../../outside.py",
            "expectedStatus": "PASS", "expectedPassed": True,
        }],
    })
    with pytest.raises(RegressionBaselineError, match="escapes"):
        load_baseline(tmp_path)


@pytest.mark.parametrize("forbidden_key", ["command", "argv", "hiddenTest", "hidden_test",
                                            "testCommand", "compileCommand"])
def test_baseline_rejects_forbidden_case_field(tmp_path, forbidden_key):
    _write_baseline(tmp_path, {
        "suiteVersion": "deterministic-v1",
        "requiredScore": 1.0,
        "cases": [{
            "id": "a", "category": "exe", "taskId": "micro-codegen/merge_dicts",
            "candidate": "missing.py", "expectedStatus": "PASS", "expectedPassed": True,
            forbidden_key: "ignore-me",
        }],
    })
    with pytest.raises(RegressionBaselineError, match="forbids"):
        load_baseline(tmp_path)


def test_baseline_rejects_suite_version_mismatch(tmp_path):
    _write_baseline(tmp_path, {
        "suiteVersion": "other-v2", "requiredScore": 1.0,
        "cases": [{
            "id": "a", "category": "exe", "taskId": "micro-codegen/merge_dicts",
            "candidate": "x.py", "expectedStatus": "PASS", "expectedPassed": True,
        }],
    })
    with pytest.raises(RegressionBaselineError, match="suiteVersion"):
        load_baseline(tmp_path)


def test_baseline_sha256_is_stable_and_detects_changes(tmp_path):
    payload = {"suiteVersion": "deterministic-v1", "requiredScore": 1.0, "cases": []}
    _write_baseline(tmp_path, payload)
    first = baseline_sha256(tmp_path)
    assert first == baseline_sha256(tmp_path)
    assert len(first) == 64
    payload["requiredScore"] = 0.9
    _write_baseline(tmp_path, payload)
    assert baseline_sha256(tmp_path) != first