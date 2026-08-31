from cortexo_ml.evaluation.pass_at_k import compute_pass_at_k, pass_at_k_batch
from cortexo_ml.evaluation.runner import run_evaluation
from cortexo_ml.serving.backends import EchoBackend
from cortexo_ml.serving.model_interface import GenerationConfig

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
        prompt_fn=lambda p, b=backend: b.generate(p, GenerationConfig(temperature=0.2)).text,
        seed=42,
    )
    assert record["taskId"] == "micro-codegen/merge_dicts"
    assert record["output"]
    assert record["metrics"]["parameterCount"] >= 0
    assert record["runId"].startswith("run-")
    assert record["repositorySnapshotId"] is None