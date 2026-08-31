from __future__ import annotations

import statistics
from dataclasses import dataclass, field


@dataclass
class LatencySample:
    event: str
    duration_ms: float
    metadata: dict = field(default_factory=dict)


def percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile / 100.0
    lower = int(index)
    frac = index - lower
    if lower + 1 < len(ordered):
        return ordered[lower] * (1 - frac) + ordered[lower + 1] * frac
    return ordered[lower]


class ResourceMetrics:
    def __init__(self) -> None:
        self.samples: list[LatencySample] = []

    def add(self, sample: LatencySample) -> None:
        self.samples.append(sample)

    def latency_timeseries(self, event: str) -> list[float]:
        return [s.duration_ms for s in self.samples if s.event == event or event == "*"]

    def p50(self, event: str = "*") -> float:
        return percentile(self.latency_timeseries(event), 50)

    def p95(self, event: str = "*") -> float:
        return percentile(self.latency_timeseries(event), 95)


def ttft_first_token(latencies: list[float], output_tokens: int) -> float:
    if not latencies:
        return 0.0
    return latencies[0]


def tokens_per_second(generated_tokens: int, total_seconds: float) -> float:
    return generated_tokens / max(1e-9, total_seconds)


def compute_resource_report(
    latencies: list[float],
    generated_tokens: int,
    param_count: int = 0,
    active_params: int | None = None,
    ram_mb: float = 0.0,
    vram_mb: float = 0.0,
    cpu_percent: float = 0.0,
    gpu_percent: float = 0.0,
    disk_mb: float = 0.0,
    model_postfix: str = "",
) -> dict:
    total = sum(latencies) / 1000
    out = {
        "p50LatencyMs": round(percentile(latencies, 50), 2),
        "p95LatencyMs": round(percentile(latencies, 95), 2),
        "ttftMs": round(ttft_first_token(latencies, generated_tokens), 2),
        "tokensPerSec": round(tokens_per_second(generated_tokens, total), 2),
        "ramMb": ram_mb,
        "vramMb": vram_mb,
        "cpuPercent": cpu_percent,
        "gpuPercent": gpu_percent,
        "diskMb": round(disk_mb, 2),
        "parameterCount": param_count,
        "activeParameters": active_params if active_params is not None else param_count,
    }
    if model_postfix:
        out["model"] = model_postfix
    return out


def summarize(fn) -> dict:
    """Decorator-friendly helper to build a human summary from a report dict."""
    return {k: v for k, v in fn.items() if isinstance(v, (int, float, str))}