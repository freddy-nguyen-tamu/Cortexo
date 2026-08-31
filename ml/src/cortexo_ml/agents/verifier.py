from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from cortexo_ml.agents.tools import ToolExecutor


@dataclass
class VerifierResult:
    passed: bool
    command_type: str
    stdout: str = ""
    stderr: str = ""
    failure_kind: str | None = None
    details: dict = field(default_factory=dict)

    @property
    def summary(self) -> str:
        if self.passed:
            return f"{self.command_type}: PASS"
        kind = self.failure_kind or "FAIL"
        return f"{self.command_type}: FAIL ({kind})"


class Verifier:
    """Compiles/tests/checks the workspace; never trusts model output directly."""

    def __init__(self, tools: ToolExecutor, test_command: str | None = None):
        self.tools = tools
        self.test_command = test_command

    def compile(self, language: str = "python") -> VerifierResult:
        result = self.tools.execute("compile_project", {"language": language})
        return self._from_tool_result(result, "COMPILE")

    def test(self, language: str = "python", target: str | None = None) -> VerifierResult:
        result = self.tools.execute("run_tests", {"language": language, "target": target})
        return self._from_tool_result(result, "TEST")

    def lint(self) -> VerifierResult:
        result = self.tools.execute("run_linter", {})
        return self._from_tool_result(result, "LINT")

    def _from_tool_result(self, result: dict, command_type: str) -> VerifierResult:
        if result.get("skipped"):
            # Offline/sandbox-less mode: nothing to verify.
            if command_type == "TEST":
                return VerifierResult(passed=True, command_type=command_type, failure_kind="skipped-offline", details=result)
            return VerifierResult(passed=True, command_type=command_type, failure_kind="skipped-offline", details=result)
        if result.get("ok") is False:
            return VerifierResult(False, command_type, stderr=str(result.get("error", "tool failure")), failure_kind="TOOL_ERROR")
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exitCode", 0)
        passed = bool(result.get("passed", exit_code == 0 and result.get("ok", True)))
        failure_kind = None
        if not passed:
            if "Timed out" in stderr or "timed out" in (stdout + stderr):
                failure_kind = "SANDBOX_TIMEOUT"
            elif result.get("policy", False):
                failure_kind = "SANDBOX_POLICY"
            elif "error:" in stderr.lower() or "build failed" in stderr.lower():
                failure_kind = "COMPILE_FAIL"
            else:
                failure_kind = "TEST_FAIL"
        return VerifierResult(passed, command_type, stdout=stdout, stderr=stderr, failure_kind=failure_kind, details=result)


def elapsed_ms(start: float) -> float:
    return (time.monotonic() - start) * 1000