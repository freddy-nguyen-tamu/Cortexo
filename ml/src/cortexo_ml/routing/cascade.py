from __future__ import annotations

from cortexo_ml.routing.rules import CandidateModel
from cortexo_ml.agents.verifier import VerifierResult


def cascade(
    ordered_models: list[CandidateModel],
    call: callable,
    validate: callable,
    max_escalations: int = 5,
) -> dict:
    """Start small; escalate on invalid/failed validation.

    call: (model_id) -> output
    validate: (model_id, output) -> (bool validated, result)
    """
    history = []
    for idx, model in enumerate(ordered_models[:max_escalations]):
        output = call(model.model_id)
        validated, result = validate(model.model_id, output)
        history.append({"modelId": model.model_id, "validated": validated, "output": output})
        if validated:
            return {"escalations": idx, "modelId": model.model_id, "output": output, "result": result, "history": history}
    return {"escalations": len(ordered_models), "modelId": None, "output": None, "result": None, "history": history}


def best_of_n(
    n: int,
    samples: callable,
    verifier_result: callable,
    prefer_minimal: bool = True,
) -> dict:
    """Generate n patches; select the passing minimal patch (test-time compute)."""
    candidates = []
    for i in range(n):
        patch = samples(i)
        result = verifier_result(patch)
        if result.passed:
            candidates.append((patch, result))
        else:
            candidates.append((patch, result))

    passing = [c for c in candidates if c[1].passed]
    if not passing:
        return {"passed": False, "candidates": [{"patch": p, "passed": r.passed} for p, r in candidates]}
    if prefer_minimal:
        selected = min(passing, key=lambda c: _patch_size(c[0]))
    else:
        selected = passing[0]
    return {"passed": True, "selected": selected[0], "candidates": [{"patch": p, "passed": r.passed} for p, r in candidates]}


def _patch_size(patch: str | None) -> int:
    if not patch:
        return 10 ** 9
    lines = patch.splitlines()
    return sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))