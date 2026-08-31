from __future__ import annotations

from dataclasses import dataclass, field

from cortexo_ml.routing.features import TaskFeatures


@dataclass
class CandidateModel:
    model_id: str
    quality: float = 0.5
    historical_success: float = 0.5
    latency_ms: float = 1000.0
    ram_mb: int = 2048
    vram_mb: int = 0
    context_length: int = 4096
    supports_tools: bool = False
    loaded: bool = True
    precision: str = "fp16"
    family: str = "scratch"
    technique: str = "base"
    quantization: str | None = None


def rule_select(features: TaskFeatures, candidates: list[CandidateModel]) -> str:
    """V1 rule-based router per the blueprint's example mappings."""
    if features.task_type == "sql" and features.repo_size in {"small", "medium"}:
        matches = [c for c in candidates if c.family == "qwen" and c.technique == "lora"]
        if matches:
            return _cheapest(matches).model_id
    if features.task_type == "interactive" or features.tools_required:
        matches = [c for c in candidates if c.supports_tools]
        if matches:
            return _cheapest(matches).model_id
    if features.retrieval_confidence > 0.8 and features.repo_size == "small":
        cheap = [c for c in candidates if c.vram_mb == 0]
        if cheap:
            return _cheapest(cheap).model_id
    if features.task_type in {"security", "review", "sql"}:
        sorted_candidates = sorted(candidates, key=lambda c: -c.quality)
        chosen = None
        for c in sorted_candidates:
            if c.vram_mb <= features.available_vram_mb and c.ram_mb <= features.available_ram_mb:
                chosen = c
                break
        return chosen.model_id if chosen else _cheapest(candidates).model_id
    if features.available_vram_mb == 0:
        cpu_safe = [c for c in candidates if c.vram_mb == 0]
        return _cheapest(cpu_safe or candidates).model_id
    return _heaviest_that_fits(features, candidates)


def _cheapest(candidates: list[CandidateModel]) -> CandidateModel:
    return min(candidates, key=lambda c: c.latency_ms)


def _heaviest_that_fits(features: TaskFeatures, candidates: list[CandidateModel]) -> CandidateModel:
    feasible = [
        c for c in candidates
        if c.context_length >= features.estimated_context_tokens
        and c.ram_mb <= features.available_ram_mb
        and c.vram_mb <= features.available_vram_mb
        and c.loaded
    ]
    if not feasible:
        feasible = [c for c in candidates if c.loaded]
    return max(feasible, key=lambda c: c.quality)


RULES_DOC = [
    "exact symbol lookup -> BM25 + small model",
    "architecture question -> graph + stronger model",
    "failing test -> repair agent",
    "CPU only -> quantized model",
    "low confidence -> cascade upward",
    "high quality budget -> ensemble",
]