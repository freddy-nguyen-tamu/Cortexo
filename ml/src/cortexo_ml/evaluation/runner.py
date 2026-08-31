from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from cortexo_ml.common.git import environment_snapshot
from cortexo_ml.evaluation.resource_metrics import ResourceMetrics, LatencySample, compute_resource_report


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
    trace_ids: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_record(self) -> dict:
        return {
            "runId": self.run_id,
            "taskId": self.task_id,
            "modelVariantId": self.model_variant_id,
            "repositorySnapshotId": self.repository_snapshot_id,
            "seed": self.seed,
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


def run_evaluation(
    task: dict,
    model_variant_id: str,
    prompt_fn,
    repository_snapshot_id: str | None = None,
    retrieval_fn=None,
    agent_fn=None,
    seed: int = 42,
    hardware_snapshot: dict | None = None,
) -> dict:
    """Execute one model x task evaluation, recording every subsystem.

    task: canonical task object (taskId, prompt, ...).
    model_variant_id: which model variant ran.
    prompt_fn: callable(prompt) -> str output.
    retrieval_fn: optional callable(query) -> RetrievalContext (or dict).
    agent_fn: optional callable(task) -> RepairAgentResult.
    """
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    metrics = ResourceMetrics()
    generation = {"seed": seed}

    start = time.monotonic()
    if agent_fn is not None:
        agent_record = agent_fn(task).to_record()
        agent = agent_record
        output = agent_record.get("output") or f"agent {agent_record.get('outcome')}"
        patch = agent_record.get("patch")
        metrics.add(LatencySample("agent", agent_record.get("elapsedSeconds", 0) * 1000))
        tests = {"agentOutcome": agent_record.get("outcome")}
    else:
        out = prompt_fn(task["prompt"])
        elapsed = (time.monotonic() - start) * 1000
        metrics.add(LatencySample("generate", elapsed))
        agent = {}
        patch = task.get("gold_patch")
        tests = {}
        output = out

    retrieval = {}
    trace_ids: list[str] = []
    if retrieval_fn is not None:
        context = retrieval_fn(task["prompt"])
        if context is not None:
            retrieval = context.to_record() if not isinstance(context, dict) else context
    if "traceIds" in task and task["traceIds"]:
        trace_ids.extend(task["traceIds"])

    resource_report = compute_resource_report(
        latencies=[s.duration_ms for s in metrics.samples],
        generated_tokens=len(output.split()),
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
        trace_ids=trace_ids,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    return outcome.to_record()