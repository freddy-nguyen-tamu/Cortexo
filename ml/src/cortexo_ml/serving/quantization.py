from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

QUANTIZATION_LEVELS = ["fp32", "fp16", "bf16", "int8", "int4"]


@dataclass
class QuantizationReport:
    model_id: str
    baseline: str
    quantized_path: str | None = None
    disk_mb: float = 0.0
    baseline_disk_mb: float = 0.0
    peak_ram_mb: float = 0.0
    peak_vram_mb: float = 0.0
    latency_ms: float = 0.0
    ttft_ms: float = 0.0
    tokens_per_sec: float = 0.0
    quality_delta: float | None = None
    quantization_error: float | None = None
    metadata: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        return {
            "modelId": self.model_id,
            "baseline": self.baseline,
            "diskMb": round(self.disk_mb, 2),
            "baselineDiskMb": round(self.baseline_disk_mb, 2),
            "peakRamMb": round(self.peak_ram_mb, 1),
            "peakVramMb": round(self.peak_vram_mb, 1),
            "latencyMs": round(self.latency_ms, 2),
            "ttftMs": round(self.ttft_ms, 2),
            "tokensPerSec": round(self.tokens_per_sec, 2),
            "qualityDelta": self.quality_delta,
            "quantizationError": self.quantization_error,
        }


def directory_mb(path: str | Path) -> float:
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file()) / 1e6


def quantize_with_torch(
    model,
    precision: str,
    output_dir: str | Path,
    dtype_map=None,
) -> QuantizationReport:
    """INT8 dynamic quantization for transformer linear layers via torch.quantize."""
    import torch

    dtype_map = dtype_map or {
        "fp32": torch.float32,
        "fp16": torch.float16,
        "bf16": torch.bfloat16,
    }
    if precision in dtype_map:
        model = model.to(dtype_map[precision]).half() if precision == "fp16" else model.to(dtype_map[precision])
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        torch.save({"model": model.state_dict(), "precision": precision}, out / "model.pt")
        report = QuantizationReport(model_id=getattr(model, "config_name", "unset"), baseline="torch")
        report.quantized_path = str(out / "model.pt")
        report.disk_mb = directory_mb(out)
        report.quantization_error = 0.0
        return report

    if precision == "int8":
        try:
            from torch.ao.quantization import quantize_dynamic
        except ImportError:
            from torch.quantization import quantize_dynamic  # legacy

        quantized = quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        torch.save({"model": state_dict_with_dtype(quantized), "precision": "int8"}, out / "model.pt")
        report = QuantizationReport(model_id=str(getattr(model, "config", "")), baseline="fp16")
        report.quantized_path = str(out / "model.pt")
        report.disk_mb = directory_mb(out)
        report.quantization_error = None
        return report

    raise ValueError(f"unsupported local quantization precision: {precision}")


def state_dict_with_dtype(model) -> dict:
    state = {}
    for name, param in model.state_dict().items():
        state[name] = param
    return state


# ---- tiny model parameter helpers used by the Dashboard ----

def estimate_bytes(p: dict) -> int:
    n = p.get("parameterCount", 0)
    precision = str(p.get("precision", "fp16")).lower()
    return n * {"int8": 1, "int4": 0.5, "fp32": 4}.get(precision, 2)


def quantized_size(model_params: int, precision: str) -> float:
    return model_params * {"int8": 1, "int4": 0.5, "fp32": 4, "fp16": 2, "bf16": 2}.get(precision, 2) / 1e6