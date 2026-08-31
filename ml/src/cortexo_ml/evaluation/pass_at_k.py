from __future__ import annotations

import math
from typing import Sequence


def compute_pass_at_k(
    n: int,
    c: int,
    k: int,
) -> float:
    """Standard pass@k estimator where n samples generated, c pass.

    pass@k = 1 - C(n - c, k) / C(n, k)  (0 when n < k).
    """
    if k > n:
        return 0.0
    if n - c < k:
        return 1.0
    return 1.0 - _comb(n - c, k) / _comb(n, k)


def pass_at_k_batch(
    examples: Sequence[Sequence[bool]],
    k: int,
) -> tuple[float, list[float]]:
    """examples: list of (list of booleans per task). Returns single pass@k average."""
    values = []
    for sample_results in examples:
        c = int(sum(1 for r in sample_results if r))
        n = max(1, len(sample_results))
        if n < k:
            values.append(0.0)
        else:
            values.append(compute_pass_at_k(n, c, k))
    if not values:
        return 0.0, []
    return sum(values) / len(values), values


def _comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return 0.0
    return math.comb(n, k)


def estimate_samples_for_pass_at_k(
    target: float,
    true_pass_rate: float,
    k: int,
    tolerance: int = 20,
    max_samples: int = 200,
) -> int:
    """Find n samples so expected pass@k reaches ~target for a given p."""
    best = max_samples
    for n in range(k, max_samples + 1):
        p_base = (1 - true_pass_rate) ** n
        estimate = 1 - p_base * sum(
            _comb(n, i) * ((true_pass_rate / max(1e-9, 1 - true_pass_rate)) ** i)
            for i in range(k)
        )
        if abs(estimate - target) < tolerance / 100:
            best = n
            break
    return best