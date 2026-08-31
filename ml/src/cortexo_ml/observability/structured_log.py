from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

BLOCKED_KEYS = {"authorization", "password", "api_key", "apikey", "token", "private_key", "patch", "prompt", "secret"}


def scrubbed(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in BLOCKED_KEYS}


class JSONFormatter(logging.Formatter):
    def format(self, record):
        payload = {"timestamp": _utc_now(), "level": record.levelname, "logger": record.name, "message": record.getMessage()}
        if hasattr(record, "fields") and record.fields:
            payload.update(scrubbed(record.fields))
        return json.dumps(payload)


def structured_logger(name: str = "cortexo.ml") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def _utc_now() -> str:
    import datetime

    return datetime.datetime.utcnow().isoformat() + "Z"


@dataclass
class LogEvent:
    timestamp: str | None = None
    requestId: str | None = None
    userId: str | None = None
    taskId: str | None = None
    experimentId: str | None = None
    modelVariantId: str | None = None
    repositorySnapshotId: str | None = None
    durationMs: float | None = None
    status: str | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp or _utc_now(),
            "requestId": self.requestId,
            "userId": self.userId,
            "taskId": self.taskId,
            "experimentId": self.experimentId,
            "modelVariantId": self.modelVariantId,
            "repositorySnapshotId": self.repositorySnapshotId,
            "durationMs": self.durationMs,
            "status": self.status,
            **self.extra,
        }


def emit(event: LogEvent, log: logging.Logger | None = None, name: str = "cortexo.ml.observability") -> None:
    logger = log or structured_logger(name)
    logger.info("event", extra={"fields": event.to_dict()})