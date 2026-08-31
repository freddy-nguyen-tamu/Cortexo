from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from cortexo_ml.observability.structured_log import LogEvent, emit
from cortexo_ml.observability.experiment_tracker import ExperimentTracker, Span


@dataclass
class InferenceObservation:
    request_id: str
    model_variant_id: str
    latency_ms: float
    prompt_tokens: int | None = None
    generated_tokens: int | None = None
    status: str = "ok"
    task_id: str | None = None
    user_id: str | None = None
    repository_snapshot_id: str | None = None
    trace: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        return {
            "requestId": self.request_id,
            "modelVariantId": self.model_variant_id,
            "taskId": self.task_id,
            "userId": self.user_id,
            "repositorySnapshotId": self.repository_snapshot_id,
            "latencyMs": round(self.latency_ms, 2),
            "promptTokens": self.prompt_tokens,
            "generatedTokens": self.generated_tokens,
            "status": self.status,
            "trace": self.trace,
        }


class InferenceObserver:
    """Wraps any backend generate() with spans + structured logging."""

    def __init__(self, tracker: ExperimentTracker | None = None, log_name: str = "cortexo.ml.inference"):
        self.tracker = tracker
        self.log_name = log_name
        self.observations: list[InferenceObservation] = []

    def generate(self, backend, prompt: str, config, notice: dict | None = None):
        notice = notice or {}
        request_id = f"inf-{uuid.uuid4().hex[:12]}"
        start = time.monotonic()
        span: Span | None = None
        if self.tracker:
            span = self.tracker.begin("inference", requestId=request_id, model=notice.get("modelVariantId"))
        try:
            result = backend.generate(prompt, config)
            status = "ok"
            message = ""
        except Exception as exc:
            status = "error"
            message = str(exc)
            raise
        finally:
            elapsed = (time.monotonic() - start) * 1000
            if span is not None:
                span.finish(status=status, latencyMs=round(elapsed, 2))

        observation = InferenceObservation(
            request_id=request_id,
            model_variant_id=notice.get("modelVariantId") or (backend.metadata() or {}).get("model_id", "unknown"),
            latency_ms=elapsed,
            prompt_tokens=result.prompt_tokens,
            generated_tokens=result.generated_tokens,
            status=status,
            task_id=notice.get("taskId"),
            user_id=notice.get("userId"),
            repository_snapshot_id=notice.get("repositorySnapshotId"),
        )
        emit(
            LogEvent(
                requestId=request_id,
                modelVariantId=observation.model_variant_id,
                taskId=observation.task_id,
                userId=observation.user_id,
                repositorySnapshotId=observation.repository_snapshot_id,
                durationMs=elapsed,
                status=status,
                extra={"promptTokens": observation.prompt_tokens, "generatedTokens": observation.generated_tokens},
            ),
            name=self.log_name,
        )
        self.observations.append(observation)
        return result, observation