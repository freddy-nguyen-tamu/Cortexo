from __future__ import annotations

import json

from cortexo_ml.agents.verifier import VerifierResult


def reflect(failure: VerifierResult, test_logs: str = "", prior_attempts: int = 0) -> str:
    """Turn a verifier failure into concrete next-attempt guidance."""
    lines = []
    lines.append("The previous attempt failed.")
    lines.append(f"Verifier: {failure.summary}")
    if failure.failure_kind:
        lines.append(f"Failure kind: {failure.failure_kind}")
    snippet = (failure.stderr or test_logs or failure.stdout or "").strip()
    if snippet:
        lines.append("Log excerpt:")
        lines.append(_truncate(snippet, 1500))
        lines.append("Checklist for next attempt:")
        lines.append("- Re-read the failing test/file before writing the patch.")
        lines.append("- Check indices, off-by-one, null handling, and the exact expected function/return type.")
        lines.append("- Prefer the smallest patch that targets the failure.")
        lines.append("- After patching, run the tests again before finishing.")
    lines.append(f"Attempt history: {prior_attempts + 1} failed attempt(s).")
    return "\n".join(lines)


def _truncate(text: str, limit: int) -> str:
    text = text.replace("\\n", "\n")
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"



def reflection_failed_forever(max_attempts: int) -> str:
    return f"Exhausted {max_attempts} attempts. Summarize what blocked the fix."