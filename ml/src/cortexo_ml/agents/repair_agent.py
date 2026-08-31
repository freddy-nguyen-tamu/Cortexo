from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from cortexo_ml.agents.executor import Executor, TextBackend
from cortexo_ml.agents.planner import AgentTrace, make_plan_prompt, parse_plan
from cortexo_ml.agents.reflector import reflect
from cortexo_ml.agents.verifier import Verifier, VerifierResult
from cortexo_ml.agents.tools import ToolExecutor


@dataclass
class RepairAgentConfig:
    max_attempts: int = 3
    max_tool_calls: int = 30
    timeout_seconds: float = 300.0
    token_budget: int = 60_000
    language: str = "python"
    test_command: str | None = None


@dataclass
class RepairAgentResult:
    run_id: str
    repo: str
    task: str
    outcome: str
    attempts: int
    tool_calls: int
    elapsed_seconds: float
    final_patch: str | None = None
    verifier_logs: list[str] = field(default_factory=list)
    trace: AgentTrace | None = None

    def to_record(self) -> dict:
        return {
            "runId": self.run_id,
            "repo": self.repo,
            "task": self.task,
            "outcome": self.outcome,
            "attempts": self.attempts,
            "toolCalls": self.tool_calls,
            "elapsedSeconds": round(self.elapsed_seconds, 2),
            "patch": self.final_patch,
            "trace": self.trace.to_record() if self.trace else None,
        }


class RepairAgent:
    """Loop: planner -> executor -> verifier -> success OR reflection -> executor.

    Stops on success, max attempts, token budget, or wall-clock timeout.
    """

    def __init__(self, backend: TextBackend, tools: ToolExecutor, verifier: Verifier, config: RepairAgentConfig | None = None):
        self.backend = backend
        self.tools = tools
        self.verifier = verifier
        self.executor = Executor(tools, backend)
        self.config = config or RepairAgentConfig()

    def run(self, repo: str, task: str, run_id: str | None = None) -> RepairAgentResult:
        run_id = run_id or f"agent-{uuid.uuid4().hex[:8]}"
        trace = AgentTrace(run_id=run_id, repo=repo, task=task)
        trace.add("PLAN", prompt=task)
        start = time.monotonic()

        plan_prompt = make_plan_prompt(repo, task)
        plan_text = self.backend.complete(plan_prompt, max_new_tokens=512, temperature=0.2)
        plan = parse_plan(plan_text)
        trace.add("PLAN", plan=plan)

        feedback: str | None = None
        attempts = 0
        tool_calls_used = 0

        while attempts < self.config.max_attempts:
            if time.monotonic() - start > self.config.timeout_seconds:
                trace.add("FINISH", outcome="timeout")
                return self._result(run_id, repo, task, "timeout", attempts, tool_calls_used, start, None, trace)

            attempts += 1
            trace.add("TOOL_REQUEST", attempt=attempts)
            exec_result = self.executor.run(task, plan, retry_feedback=feedback)
            tool_calls_used += exec_result.tool_calls
            trace.add("TOOL_RESULT", attempt=attempts, applied=exec_result.applied, toolCalls=exec_result.tool_calls)

            if time.monotonic() - start > self.config.timeout_seconds:
                trace.add("FINISH", outcome="timeout")
                return self._result(run_id, repo, task, "timeout", attempts, tool_calls_used, start, exec_result.patch, trace)

            if exec_result.applied:
                trace.add("PATCH", attempt=attempts, patch=exec_result.patch)

            compile_result = self.verifier.compile(self.config.language)
            trace.add("COMPILE", attempt=attempts, passed=compile_result.passed, summary=compile_result.summary)
            test_result = self.verifier.test(self.config.language)
            trace.add("TEST", attempt=attempts, passed=test_result.passed, summary=test_result.summary)

            verifier_log = f"{compile_result.summary}\n{test_result.summary}"
            if compile_result.passed and test_result.passed:
                trace.add("FINISH", outcome="success", attempts=attempts)
                return self._result(run_id, repo, task, "success", attempts, tool_calls_used, start, exec_result.patch, trace, [verifier_log])

            if tool_calls_used > self.config.max_tool_calls:
                trace.add("FINISH", outcome="tool-budget-exhausted")
                return self._result(run_id, repo, task, "tool-budget-exhausted", attempts, tool_calls_used, start, exec_result.patch, trace, [verifier_log])

            failure = test_result if not test_result.passed else compile_result
            trace.add("REFLECT", attempt=attempts, failure_kind=failure.failure_kind)
            feedback = reflect(failure, prior_attempts=attempts - 1)
            if attempts < self.config.max_attempts:
                trace.add("RETRY", attempt=attempts, reason=failure.failure_kind)

        trace.add("FINISH", outcome="exhausted", attempts=attempts)
        return self._result(run_id, repo, task, "exhausted", attempts, tool_calls_used, start, None, trace)

    def _result(self, run_id, repo, task, outcome, attempts, tool_calls, start, patch, trace, logs=None) -> RepairAgentResult:
        return RepairAgentResult(
            run_id=run_id,
            repo=repo,
            task=task,
            outcome=outcome,
            attempts=attempts,
            tool_calls=tool_calls,
            elapsed_seconds=time.monotonic() - start,
            final_patch=patch,
            verifier_logs=logs or [],
            trace=trace,
        )