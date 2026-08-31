from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol

from cortexo_ml.agents.verifier import VerifierResult
from cortexo_ml.agents.tools import ToolExecutor


class TextBackend(Protocol):
    def complete(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.2) -> str:
        ...


@dataclass
class ExecutorResult:
    attempt: int
    patch: str | None
    applied: bool
    tool_calls: int
    completion: str = ""
    notes: list[str] = field(default_factory=list)


class Executor:
    """Uses tools to turn a plan into an applied patch."""

    def __init__(self, tools: ToolExecutor, backend: TextBackend):
        self.tools = tools
        self.backend = backend

    def run(self, task: str, plan: dict, retry_feedback: str | None = None) -> ExecutorResult:
        prompt = (
            f"Repository task: {task}\n"
            f"Plan: {json.dumps(plan, indent=2)}\n"
        )
        if retry_feedback:
            prompt += f"Previous verifier feedback:\n{retry_feedback}\n"
        prompt += (
            "\nWrite a unified diff that fixes the task. Return ONLY the diff inside "
            "```diff ... ``` fences (or a raw unified diff)."
        )

        completion = self.backend.complete(prompt, max_new_tokens=1024, temperature=0.2)
        patch = extract_diff(completion)
        applied = False
        tool_calls = 0

        if patch:
            self.tools.execute("write_patch", {"patch": patch})
            tool_calls += 1
            try:
                result = self.tools.execute("apply_patch", {"patch": patch})
                applied = bool(result.get("applied"))
                tool_calls += 1
            except Exception as exc:
                applied = False
                return ExecutorResult(attempt=0, patch=patch, applied=False, tool_calls=tool_calls, completion=completion, notes=[str(exc)])

        return ExecutorResult(attempt=0, patch=patch, applied=applied, tool_calls=tool_calls, completion=completion)


def extract_diff(text: str) -> str | None:
    import re

    fenced = re.search(r"```(?:diff|patch)?\s*(.*?)```", text, re.S)
    if fenced:
        return fenced.group(1).strip()
    if text.startswith("--- ") or "diff --git" in text:
        return text.strip()
    return None