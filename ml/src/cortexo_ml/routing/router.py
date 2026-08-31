from __future__ import annotations

from dataclasses import dataclass, field

from cortexo_ml.routing.features import TaskFeatures
from cortexo_ml.routing.rules import CandidateModel, rule_select

ROUTER_DECISION_SCHEMA = {
    "selected_model": "",
    "scores": {},
    "fallback": "",
}


@dataclass
class ScoreRow:
    model_id: str
    predicted_quality: float
    predicted_latency_ms: float
    predicted_ram_mb: int
    predicted_vram_mb: int
    feasible: bool
    constraints: list[str] = field(default_factory=list)
    utility: float = 0.0
    selected: bool = False
    fallback: bool = False

    def to_record(self) -> dict:
        return {
            "modelId": self.model_id,
            "predictedQuality": round(self.predicted_quality, 3),
            "predictedLatencyMs": round(self.predicted_latency_ms, 1),
            "predictedRamMb": self.predicted_ram_mb,
            "predictedVramMb": self.predicted_vram_mb,
            "feasible": self.feasible,
            "constraints": self.constraints,
            "utility": round(self.utility, 4),
            "selected": self.selected,
            "fallback": self.fallback,
        }


class Router:
    """Scores every candidate and returns the full table, not just the winner.

    utility = quality_weight * predicted_quality
              - latency_weight * normalized_latency
              - memory_weight * normalized_memory
              - failure_risk_weight * predicted_failure
    """

    def __init__(
        self,
        quality_weight: float = 1.0,
        latency_weight: float = 0.2,
        memory_weight: float = 0.1,
        failure_risk_weight: float = 0.5,
    ):
        self.qw = quality_weight
        self.lw = latency_weight
        self.mw = memory_weight
        self.fw = failure_risk_weight

    def decide(self, features: TaskFeatures, candidates: list[CandidateModel]) -> dict:
        rows: list[ScoreRow] = []
        max_latency = max((c.latency_ms for c in candidates), default=1) or 1
        max_ram = max((c.ram_mb for c in candidates), default=1) or 1
        max_vram = max((c.vram_mb for c in candidates), default=1) or 1

        for c in candidates:
            constraints, feasible = self._constraints(features, c)
            predicted_failure = 1.0 - (0.7 * c.quality + 0.3 * c.historical_success)
            utility = (
                self.qw * c.quality
                - self.lw * (c.latency_ms / max_latency)
                - self.mw * (c.ram_mb / max_ram + c.vram_mb / max_vram) / 2
                - self.fw * predicted_failure
            )
            rows.append(ScoreRow(
                model_id=c.model_id,
                predicted_quality=c.quality,
                predicted_latency_ms=c.latency_ms,
                predicted_ram_mb=c.ram_mb,
                predicted_vram_mb=c.vram_mb,
                feasible=feasible,
                constraints=constraints,
                utility=utility,
            ))

        feasible_rows = [r for r in rows if r.feasible]
        pool = feasible_rows or rows

        selected = max(pool, key=lambda r: r.utility)
        selected.selected = True

        fallback = None
        if selected not in [r for r in rows if True] and feasible_rows:
            fallback = max(feasible_rows, key=lambda r: r.utility)
            fallback.fallback = True

        rule_pick = None
        try:
            rule_pick = rule_select(features, candidates)
        except Exception:
            rule_pick = None

        return {
            "taskFeatures": features.to_record(),
            "candidates": [r.to_record() for r in rows],
            "selectedModel": selected.model_id,
            "selectedUtility": round(selected.utility, 4),
            "ruleBasedPick": rule_pick,
            "fallback": fallback.model_id if fallback else None,
            "weights": {"quality": self.qw, "latency": self.lw, "memory": self.mw, "failureRisk": self.fw},
        }

    def _constraints(self, features: TaskFeatures, c: CandidateModel) -> tuple[list[str], bool]:
        constraints = []
        feasible = True

        def _fails(cond: bool, label: str) -> None:
            nonlocal feasible
            if cond:
                constraints.append(label)
                feasible = False

        _fails(c.ram_mb > features.available_ram_mb, "ram-over-available")
        _fails(c.vram_mb > features.available_vram_mb, "vram-over-available")
        _fails(c.context_length < features.estimated_context_tokens, "context-too-small")
        _fails(features.tools_required and not c.supports_tools, "tools-unsupported")
        _fails(not c.loaded, "not-loaded")
        return constraints, feasible


def full_scoring_table(router: Router, features: TaskFeatures, candidates: list[CandidateModel]) -> list[dict]:
    decision = router.decide(features, candidates)
    return decision["candidates"]