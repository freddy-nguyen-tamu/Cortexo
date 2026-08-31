from cortexo_ml.evaluation.pass_at_k import compute_pass_at_k, pass_at_k_batch
from cortexo_ml.evaluation.runner import model_visible_task, run_evaluation
from cortexo_ml.serving.backends import EchoBackend
from cortexo_ml.serving.model_interface import GenerationConfig, GenerationResult

CANONICAL_TASK = {
    "task_id": "micro-codegen/merge_dicts",
    "task_type": "code_generation",
    "repository_snapshot_id": None,
    "prompt": "implement merge_dicts",
    "expected_behavior": "merged dict contains all keys",
    "allowed_tools": [],
    "test_command": None,
    "compile_command": None,
    "gold_files": [],
    "gold_patch": None,
    "ground_truth_findings": [],
    "timeout_seconds": 60,
}


def test_estimate_pass_at_k():
    assert compute_pass_at_k(8, 7, 5) == 1.0
    assert compute_pass_at_k(8, 0, 25) == 0.0
    assert compute_pass_at_k(4, 4, 1) == 1.0
    assert compute_pass_at_k(4, 0, 1) == 0.0
    avg, values = pass_at_k_batch([[True, True], [False, False, False]], k=1)
    assert avg == 0.5
    assert values == [1.0, 0.0]


def test_run_evaluation_echo_backend():
    backend = EchoBackend(model_id="echo-demo")
    record = run_evaluation(
        task=CANONICAL_TASK,
        model_variant_id="echo-demo",
        prompt_fn=lambda p, b=backend: b.generate(p, GenerationConfig(temperature=0.2)),
        seed=42,
    )
    assert record["taskId"] == "micro-codegen/merge_dicts"
    assert record["output"]
    assert record["metrics"]["parameterCount"] >= 0
    assert record["runId"].startswith("run-")
    assert record["repositorySnapshotId"] is None
    assert record["status"] == "COMPLETED"


def test_gold_patch_never_becomes_candidate():
    task = dict(CANONICAL_TASK, gold_patch="SECRET_GOLD_PATCH_SENTINEL")
    records = []

    def prompt_fn(prompt: str) -> str:
        return "def merge_dicts(left, right):\n    return dict(left)\n"

    record = run_evaluation(task=task, model_variant_id="m", prompt_fn=prompt_fn, seed=1)
    assert record["patch"] != "SECRET_GOLD_PATCH_SENTINEL"
    assert record["patch"] is None
    assert "SECRET_GOLD_PATCH_SENTINEL" not in (record["output"] or "")
    records.append(record)


def test_prompt_does_not_contain_evaluator_only_fields():
    task = {
        "task_id": "micro-codegen/merge_dicts",
        "task_type": "code_generation",
        "prompt": "implement the function",
        "expected_behavior": "SECRET_EXPECTED_SENTINEL",
        "gold_patch": "SECRET_GOLD_SENTINEL",
        "ground_truth_findings": [{"secret": "SECRET_FINDING_SENTINEL"}],
        "test_command": "pytest SECRET_TEST_SENTINEL",
        "hidden_test": "SECRET_HIDDEN_SENTINEL",
    }
    captured: list[str] = []

    def prompt_fn(prompt: str) -> str:
        captured.append(prompt)
        return "code"

    run_evaluation(task=task, model_variant_id="m", prompt_fn=prompt_fn, seed=2)
    prompt = captured[0]
    for sentinel in ("SECRET_EXPECTED_SENTINEL", "SECRET_GOLD_SENTINEL",
                     "SECRET_FINDING_SENTINEL", "SECRET_TEST_SENTINEL",
                     "SECRET_HIDDEN_SENTINEL"):
        assert sentinel not in prompt


def test_model_visible_task_omits_gold_fields():
    visible = model_visible_task(CANONICAL_TASK)
    for key in ("expected_behavior", "gold_patch", "gold_files",
                "ground_truth_findings", "test_command", "compile_command"):
        assert key not in visible
    assert "prompt" in visible


def test_backend_token_accounting():
    result = GenerationResult(
        text="def merge_dicts(left, right):\n    return dict(left)\n",
        prompt_tokens=11,
        generated_tokens=7,
        latency_ms=42.0,
        metadata={"backend": "echo"},
    )
    record = run_evaluation(task=CANONICAL_TASK, model_variant_id="m",
                            prompt_fn=lambda p: result, seed=3)
    usage = record["generation"]["usage"]
    assert usage["promptTokens"] == 11
    assert usage["generatedTokens"] == 7
    assert record["generation"]["tokenCountSource"] == "backend"


def test_string_prompt_fn_marks_tokens_unavailable():
    record = run_evaluation(task=CANONICAL_TASK, model_variant_id="m",
                            prompt_fn=lambda p: "raw output", seed=4)
    usage = record["generation"]["usage"]
    assert usage["promptTokens"] is None
    assert usage["generatedTokens"] is None
    assert record["generation"]["tokenCountSource"] == "unavailable"
    assert record["metrics"]["tokensPerSec"] == 0.0


class _FakeAgentResult:
    def __init__(self, task_copy: dict):
        self.received_task = task_copy

    def to_record(self) -> dict:
        return {"outcome": "success", "output": "fake agent output", "patch": None}


def test_agent_receives_safe_task_only():
    task = {
        "task_id": "synthetic-bugfix/range_util",
        "task_type": "bug_fix",
        "prompt": "fix clamp",
        "gold_patch": "SECRET_GOLD_SENTINEL",
        "ground_truth_findings": [{"secret": "SECRET_FINDING_SENTINEL"}],
        "hidden_test": "SECRET_HIDDEN_SENTINEL",
    }
    seen: list[dict] = []

    def agent_fn(t):
        seen.append(t)
        return _FakeAgentResult(t)

    record = run_evaluation(task=task, model_variant_id="m", prompt_fn=lambda p: "x",
                            agent_fn=agent_fn, seed=5)
    assert record["agent"]["outcome"] == "success"
    assert "SECRET_GOLD_SENTINEL" not in seen[0]
    assert "SECRET_FINDING_SENTINEL" not in seen[0]
    assert "SECRET_HIDDEN_SENTINEL" not in seen[0]


def test_grader_fn_result_populates_tests_and_status():
    def grader_fn(canonical_task, output):
        return {"status": "TEST_FAIL", "passed": False, "detail": "x"}

    record = run_evaluation(task=CANONICAL_TASK, model_variant_id="m",
                            prompt_fn=lambda p: "code", grader_fn=grader_fn, seed=6)
    assert record["status"] == "TEST_FAIL"
    assert record["tests"]["passed"] is False