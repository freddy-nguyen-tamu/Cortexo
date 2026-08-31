from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from cortexo_ml.common.git import environment_snapshot
from cortexo_ml.evaluation.resource_metrics import ResourceMetrics, LatencySample, compute_resource_report

# Keys that are safe to hand to a model. Everything else (expected_behavior,
# gold_patch, gold_files, ground_truth_findings, hidden tests, test_command,
# compile_command, grader registry info) is evaluator-only and never sent.
MODEL_VISIBLE_TASK_KEYS = {
    "task_id",
    "task_type",
    "repository_snapshot_id",
    "prompt",
    "allowed_tools",
    "language",
    "timeout_seconds",
    "requiresTools",
    "dialect",
}


def model_visible_task(task: dict) -> dict:
    return {k: task[k] for k in MODEL_VISIBLE_TASK_KEYS if k in task}


@dataclass
class RunOutcome:
    run_id: str
    task_id: str
    model_variant_id: str
    repository_snapshot_id: str | None
    seed: int
    generation: dict = field(default_factory=dict)
    retrieval: dict = field(default_factory=dict)
    agent: dict = field(default_factory=dict)
    hardware: dict = field(default_factory=dict)
    output: str = ""
    patch: str | None = None
    tests: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    status: str = "COMPLETED"
    trace_ids: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_record(self) -> dict:
        return {
            "runId": self.run_id,
            "taskId": self.task_id,
            "modelVariantId": self.model_variant_id,
            "repositorySnapshotId": self.repository_snapshot_id,
            "seed": self.seed,
            "status": self.status,
            "generation": self.generation,
            "retrieval": self.retrieval,
            "agent": self.agent,
            "hardware": self.hardware,
            "output": self.output,
            "patch": self.patch,
            "tests": self.tests,
            "metrics": self.metrics,
            "traceIds": self.trace_ids,
            "createdAt": self.created_at,
        }


def _normalize_generation(raw_generation):
    """Accept a GenerationResult (preferred) or a plain string fallback.

    Returns (output, prompt_tokens, generated_tokens, backend_metadata).
    """
    if hasattr(raw_generation, "text"):
        return (
            raw_generation.text,
            getattr(raw_generation, "prompt_tokens", None),
            getattr(raw_generation, "generated_tokens", None),
            getattr(raw_generation, "metadata", {}) or {},
        )
    return str(raw_generation), None, None, {}


def run_evaluation(
    task: dict,
    model_variant_id: str,
    prompt_fn,
    repository_snapshot_id: str | None = None,
    retrieval_fn=None,
    agent_fn=None,
    grader_fn=None,
    seed: int = 42,
    hardware_snapshot: dict | None = None,
) -> dict:
    """Execute one model x task evaluation, recording every subsystem.

    task: canonical task object. Only model_visible_task(task) is ever passed
          to prompt_fn / agent_fn; the trusted grader (grader_fn) receives the
          full canonical task AFTER generation.
    prompt_fn: callable(safe_prompt) -> GenerationResult or plain string.
    retrieval_fn: optional callable(query) -> RetrievalContext (or dict).
    agent_fn: optional callable(safe_task) -> RepairAgentResult.
    grader_fn: optional callable(canonical_task, output) -> grader record dict.
    """
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    metrics = ResourceMetrics()
    safe_task = model_visible_task(task)

    generation = {"seed": seed}
    agent: dict = {}
    tests: dict = {}
    patch: str | None = None
    output = ""
    status = "COMPLETED"

    start = time.monotonic()
    if agent_fn is not None:
        agent_record = agent_fn(safe_task).to_record()
        agent = agent_record
        output = agent_record.get("output") or f"agent {agent_record.get('outcome')}"
        patch = agent_record.get("patch")
        metrics.add(LatencySample("agent", agent_record.get("elapsedSeconds", 0) * 1000))
        tests = {"agentOutcome": agent_record.get("outcome")}
    else:
        raw_generation = prompt_fn(safe_task["prompt"])
        elapsed = (time.monotonic() - start) * 1000
        metrics.add(LatencySample("generate", elapsed))
        output, prompt_tokens, generated_tokens, backend_metadata = _normalize_generation(raw_generation)
        generation = {
            "seed": seed,
            "usage": {
                "promptTokens": prompt_tokens,
                "generatedTokens": generated_tokens,
            },
            "backend": backend_metadata,
            "tokenCountSource": "backend" if generated_tokens is not None else "unavailable",
        }

    if grader_fn is not None:
        grader_record = grader_fn(task, output)
        tests = grader_record
        status = grader_record.get("status", "COMPLETED")

    retrieval = {}
    trace_ids: list[str] = []
    if retrieval_fn is not None:
        context = retrieval_fn(safe_task["prompt"])
        if context is not None:
            retrieval = context.to_record() if not isinstance(context, dict) else context
    if task.get("traceIds"):
        trace_ids.extend(task["traceIds"])

    resource_report = compute_resource_report(
        latencies=[s.duration_ms for s in metrics.samples],
        generated_tokens=(generation.get("usage", {}).get("generatedTokens") or 0),
        param_count=int(task.get("modelParams", 0)),
    )
    hardware = hardware_snapshot or environment_snapshot()

    outcome = RunOutcome(
        run_id=run_id,
        task_id=task["task_id"],
        model_variant_id=model_variant_id,
        repository_snapshot_id=repository_snapshot_id,
        seed=seed,
        generation=generation,
        retrieval=retrieval,
        agent=agent,
        hardware=hardware,
        output=output,
        patch=patch,
        tests=tests,
        metrics=resource_report,
        status=status,
        trace_ids=trace_ids,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    return outcome.to_record()