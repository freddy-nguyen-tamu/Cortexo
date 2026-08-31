from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class CalibrationResult:
    brier_score: float = 0.0
    ece: float = 0.0
    reliability: list[dict] = field(default_factory=list)
    selective_accuracy: list[dict] = field(default_factory=list)

    def to_record(self) -> dict:
        return {
            "brierScore": round(self.brier_score, 4),
            "ece": round(self.ece, 4),
            "reliability": self.reliability,
            "selectiveAccuracy": self.selective_accuracy,
        }


def brier_score(predicted: list[float], actual: list[float]) -> float:
    if not predicted:
        return 0.0
    return sum((p - a) ** 2 for p, a in zip(predicted, actual)) / len(predicted)


def expected_calibration_error(predicted: list[float], actual: list[float], bins: int = 10) -> tuple[float, list[dict]]:
    rows = sorted(zip(predicted, actual))
    reliability = []
    total = len(rows)
    for b in range(bins):
        lo = b / bins
        hi = (b + 1) / bins
        in_bin = [(p, a) for p, a in rows if lo <= p < hi or (b == bins - 1 and p == 1.0)]
        if not in_bin:
            reliability.append({"binStart": lo, "binEnd": hi, "count": 0, "confidence": round((lo + hi) / 2, 3), "accuracy": 0.0})
            continue
        confidence = sum(p for p, _ in in_bin) / len(in_bin)
        accuracy = sum(a for _, a in in_bin) / len(in_bin)
        weight = len(in_bin) / total
        reliability.append({
            "binStart": lo,
            "binEnd": hi,
            "count": len(in_bin),
            "confidence": round(confidence, 4),
            "accuracy": round(accuracy, 4),
            "gap": round(abs(confidence - accuracy), 4),
        })
    ece = sum(r["gap"] * (r["count"] / total) for r in reliability if r["count"])
    return ece, reliability


def selective_accuracy_curve(predicted: list[float], actual: list[float]) -> list[dict]:
    pairs = sorted(zip(predicted, actual), reverse=True)
    curve = []
    n = len(pairs)
    for threshold_index in range(0, n, max(1, n // 20)):
        kept = pairs[:threshold_index + 1]
        accuracy = sum(a for _, a in kept) / max(1, len(kept))
        coverage = len(kept) / max(1, n)
        curve.append({"threshold": threshold_index, "coverage": round(coverage, 3), "selectiveAccuracy": round(accuracy, 3)})
    return curve


def calibrate(predicted: list[float], actual: list[float], bins: int = 10) -> CalibrationResult:
    ece, reliability = expected_calibration_error(predicted, actual, bins)
    return CalibrationResult(
        brier_score=brier_score(predicted, actual),
        ece=ece,
        reliability=reliability,
        selective_accuracy=selective_accuracy_curve(predicted, actual),
    )


def abstain_selection(
    predicted: list[float],
    actual: list[float],
    threshold: float,
) -> dict:
    retained = [(p, a) for p, a in zip(predicted, actual) if p >= threshold]
    if not retained:
        return {"abstained": len(predicted), "retained": 0, "accuracyOnRetained": None, "coverage": 0.0}
    accuracy = sum(a for _, a in retained) / len(retained)
    return {
        "abstained": len(predicted) - len(retained),
        "retained": len(retained),
        "accuracyOnRetained": round(accuracy, 4),
        "coverage": round(len(retained) / max(1, len(predicted)), 4),
    }