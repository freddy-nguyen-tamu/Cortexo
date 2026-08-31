from __future__ import annotations

import contextlib
import datetime
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from cortexo_ml.common.git import environment_snapshot, git_sha_short


@dataclass
class Span:
    name: str
    started_at: float
    ended_at: float | None = None
    metadata: dict = field(default_factory=dict)
    status: str = "running"

    def finish(self, status: str = "ok", **metadata) -> None:
        self.ended_at = time.monotonic()
        self.status = status
        self.metadata.update(metadata)

    @property
    def duration_ms(self) -> float:
        end = self.ended_at if self.ended_at is not None else time.monotonic()
        return (end - self.started_at) * 1000

    def to_dict(self) -> dict:
        return {
            "spanId": _id(self.name),
            "name": self.name,
            "startedAt": self.started_at,
            "endedAt": self.ended_at,
            "durationMs": round(self.duration_ms, 3),
            "status": self.status,
            "metadata": self.metadata,
        }


_span_counter = 0


def _id(name: str) -> str:
    global _span_counter
    _span_counter += 1
    return f"{_span_counter:04d}-{uuid.uuid4().hex[:8]}"


class ExperimentTracker:
    """Local JSONL+JSON run tracking; optionally mirrored to MongoDB."""

    def __init__(self, run_id: str | None = None, root: str | Path = "artifacts/evaluations"):
        self.run_id = run_id or f"run-{uuid.uuid4().hex[:10]}"
        self.root = Path(root) / self.run_id
        self.root.mkdir(parents=True, exist_ok=True)
        self.spans: list[Span] = []
        self._active: dict[str, Span] = {}
        self.start_wall = time.monotonic()
        self._sinks: list = []
        self._metrics_path = self.root / "metrics.jsonl"
        self._metrics_path.touch()

    def add_sink(self, sink) -> None:
        self._sinks.append(sink)

    def begin(self, name: str, **metadata) -> Span:
        span = Span(name=name, started_at=time.monotonic(), metadata=metadata)
        self.spans.append(span)
        self._active[name] = span
        self.emit_span(span)
        return span

    def end(self, name: str, status: str = "ok", **metadata) -> Span:
        span = self._active.pop(name)
        span.finish(status, **metadata)
        self.emit_span(span)
        return span

    def context_manager(self, name: str, **metadata):
        @contextlib.contextmanager
        def _cm():
            span = self.begin(name, **metadata)
            try:
                yield span
            except Exception:
                self.end(name, "error")
                raise
            else:
                self.end(name, "ok")

        return _cm()

    def log(self, event: dict) -> None:
        record = {"ts": datetime.datetime.utcnow().isoformat() + "Z", "runId": self.run_id, **event}
        with self._metrics_path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")

    def emit_span(self, span: Span) -> None:
        for sink in self._sinks:
            sink.on_span(span.to_dict(), run_id=self.run_id)

    def write_artifacts(
        self,
        config: dict,
        source: dict,
        summary: dict,
        stdout_log: str = "",
    ) -> None:
        (self.root / "config.json").write_text(json.dumps(config, indent=2))
        (self.root / "environment.json").write_text(json.dumps(environment_snapshot(), indent=2))
        source["gitSha"] = source.get("gitSha") or git_sha_short()
        (self.root / "source.json").write_text(json.dumps(source, indent=2))
        (self.root / "summary.json").write_text(json.dumps(summary, indent=2))
        (self.root / "stdout.log").write_text(stdout_log)
        artifacts = {
            "artifacts": [
                str(p.relative_to(self.root))
                for p in sorted(self.root.iterdir()) if p.is_file()
            ]
        }
        (self.root / "artifacts.json").write_text(json.dumps(artifacts, indent=2))

    def summary_from_spans(self) -> dict:
        return {
            "runId": self.run_id,
            "elapsedSeconds": round((time.monotonic() - self.start_wall), 2),
            "spans": [s.to_dict() for s in self.spans],
        }


class JSONLWriter:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch()

    def on_span(self, span: dict, run_id: str) -> None:
        with self.path.open("a") as fh:
            fh.write(json.dumps({"runId": run_id, "span": span}) + "\n")

    def write(self, record: dict) -> None:
        with self.path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")


class MongoSink:
    """Optional MongoDB span sink. Never required at runtime."""

    def __init__(self, mongo_uri: str | None, database: str = "cortexo", collection: str = "telemetry"):
        self.mongo_uri = mongo_uri
        self.database = database
        self.collection = collection
        self._disabled = mongo_uri is None

    def on_span(self, span: dict, run_id: str) -> None:
        if self._disabled:
            return
        try:
            from pymongo import MongoClient

            client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
            client[self.database][self.collection].insert_one({"runId": run_id, "span": span})
            client.close()
        except Exception:
            pass  # telemetry must never crash the experiment