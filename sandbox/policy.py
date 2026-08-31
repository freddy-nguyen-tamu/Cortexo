"""Sandbox policy: validation + resource limits for untrusted code execution.

Policy rules (mirrors blueprint section 68 / 69):

- The model NEVER provides a free-form shell command.
- commandType is restricted to the allow-list below.
- The runner maps each (commandType, language) to one predefined command.
- The sandbox is non-root, has no network, a read-only base FS, bounded
  memory/CPU/PID, a wall-clock timeout, process-tree cleanup, a tmpfs, and the
  workspace is deleted after execution.
- No Docker socket, no host credentials, no arbitrary host mounts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

ALLOWED_COMMAND_TYPES = ("TEST", "COMPILE", "LINT", "FORMAT", "STATIC_ANALYSIS")
ALLOWED_LANGUAGES = ("python", "java", "javascript", "typescript", "shell", "c", "cpp", "go", "rust")

DEFAULT_MEMORY = "1g"
DEFAULT_CPUS = 1
DEFAULT_PIDS = 128
MAX_TIMEOUT_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 60

IMAGE_NAME = "cortexo-sandbox:latest"

# Predefined commands. The names match ToolExecutor commandTypes
# (TEST / COMPILE / LINT / FORMAT / STATIC_ANALYSIS).
COMMANDS: dict[str, dict[str, dict[str, str]]] = {
    "python": {
        "TEST": {"argv": ["python3", "-m", "pytest", "--no-header", "-q"], "file": "pytest"},
        "COMPILE": {"argv": ["python3", "-m", "compileall", "-q", "."], "file": "compileall"},
        "LINT": {"argv": ["python3", "-m", "pyflakes"], "file": "lint"},
        "FORMAT": {"argv": ["python3", "-m", "black", "--check"], "file": "format"},
        "STATIC_ANALYSIS": {"argv": ["python3", "-m", "bandit", "-r", "."], "file": "bandit"},
    },
    "java": {
        "TEST": {"argv": ["mvn", "-q", "test"], "file": "pom"},
        "COMPILE": {"argv": ["mvn", "-q", "compile"], "file": "pom"},
        "LINT": {"argv": ["mvn", "-q", "checkstyle:check"], "file": "pom"},
        "FORMAT": {"argv": ["mvn", "-q", "spotless:check"], "file": "pom"},
        "STATIC_ANALYSIS": {"argv": ["mvn", "-q", "spotbugs:check"], "file": "pom"},
    },
    "javascript": {
        "TEST": {"argv": ["npm", "test"], "file": "package.json"},
        "COMPILE": {"argv": ["npx", "tsc", "--noEmit"], "file": "tsconfig.json"},
        "LINT": {"argv": ["npx", "eslint", "."], "file": "package.json"},
        "FORMAT": {"argv": ["npx", "prettier", "--check", "."], "file": "package.json"},
        "STATIC_ANALYSIS": {"argv": ["npx", "tsc", "--noEmit", "--strict"], "file": "tsconfig.json"},
    },
    "shell": {
        "TEST": {"argv": ["bash", "-n"], "file": None},
        "COMPILE": {"argv": ["bash", "-n"], "file": None},
        "LINT": {"argv": ["shellcheck", "."], "file": None},
        "FORMAT": {"argv": ["shfmt", "-l", "."], "file": None},
        "STATIC_ANALYSIS": {"argv": ["shellcheck", "-e", "SC2317", "."], "file": None},
    },
}

# RegExp for things that must never appear inside a generated patch.
SUSPICIOUS_PATTERNS = [
    re.compile(r"(?i)\b(base64|decrypt|sudo|chmod\s+4?777|pkexec)\b"),
    re.compile(r"(?i)(/etc/(passwd|shadow)|/root/|\.ssh/)"),
    re.compile(r"(?i)(curl|wget)\s+(-o|-O)?\s*\S*(--url\s*)?"),
]

MAX_OUTPUT_BYTES = 2_000_000
VALID_WORKSPACE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
MAX_COMMAND_ARGS = 12


def validate_timeout(timeout_seconds: int) -> int:
    value = int(timeout_seconds or DEFAULT_TIMEOUT_SECONDS)
    if value < 1:
        raise PolicyViolation("timeout_seconds must be >= 1")
    if value > MAX_TIMEOUT_SECONDS:
        raise PolicyViolation(f"timeout_seconds must be <= {MAX_TIMEOUT_SECONDS}")
    return value


def validate_command_type(command_type: str) -> str:
    upper = str(command_type).upper()
    if upper not in ALLOWED_COMMAND_TYPES:
        raise PolicyViolation(
            f"commandType must be one of {ALLOWED_COMMAND_TYPES}, got {command_type!r}"
        )
    return upper


def validate_language(language: str) -> str:
    lower = str(language).lower()
    if lower not in ALLOWED_LANGUAGES:
        raise PolicyViolation(f"language must be one of {ALLOWED_LANGUAGES}, got {language!r}")
    return lower


def validate_workspace_id(workspace_id: str) -> str:
    if not VALID_WORKSPACE_ID.match(workspace_id):
        raise PolicyViolation("workspaceId contains unsafe characters")
    return workspace_id


def resolve_command(command_type: str, language: str) -> list[str]:
    upper = validate_command_type(command_type)
    lower = validate_language(language)
    table = COMMANDS.get(lower)
    if table is None:
        raise PolicyViolation(f"no command map for language {language!r}")
    entry = table.get(upper)
    if entry is None:
        raise PolicyViolation(f"commandType {upper!r} is not supported for language {language!r}")
    return list(entry["argv"])


def check_generated_patch(patch: str) -> list[str]:
    """Return a list of policy findings for a generated patch (no arbitrary exec)."""
    findings = []
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.search(patch or ""):
            findings.append(pattern.pattern)
    return findings


def docker_flags(
    memory: str = DEFAULT_MEMORY,
    cpus: int = DEFAULT_CPUS,
    pids: int = DEFAULT_PIDS,
) -> list[str]:
    flags = [
        "--rm",
        "--network", "none",
        "--memory", memory,
        "--cpus", str(cpus),
        "--pids-limit", str(pids),
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
        "--user", "10001:10001",
        "--workdir", "/work",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "--security-opt", "seccomp=sandbox/seccomp-profile.json",
        "--env", "PYTHONDONTWRITEBYTECODE=1",
        "--env", "HOME=/tmp",
    ]
    return flags


class PolicyViolation(Exception):
    pass


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str | None = None
    command: list[str] = field(default_factory=list)
    memory: str = DEFAULT_MEMORY
    cpus: int = DEFAULT_CPUS
    pids: int = DEFAULT_PIDS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


def evaluate_request(request: dict[str, Any]) -> PolicyDecision:
    """Evaluate an execution request against the policy.

    The request is the canonical sandbox runner request:

        {"workspaceId": "...", "commandType": "TEST",
         "language": "java", "timeoutSeconds": 60}
    """
    try:
        ws = validate_workspace_id(request.get("workspaceId", ""))
        ctype = validate_command_type(request.get("commandType", ""))
        lang = validate_language(request.get("language", ""))
        timeout = validate_timeout(request.get("timeoutSeconds", DEFAULT_TIMEOUT_SECONDS))
        command = resolve_command(ctype, lang)
    except PolicyViolation as exc:
        return PolicyDecision(allowed=False, reason=str(exc))

    extra = request.get("extra")
    if extra:
        return PolicyDecision(allowed=False, reason="extra fields are not allowed in a sandbox request")

    if "command" in request:
        return PolicyDecision(allowed=False, reason="free-form 'command' is never accepted from the model")

    return PolicyDecision(
        allowed=True,
        reason=f"{ctype}/{lang} workspace={ws}",
        command=command,
        timeout_seconds=timeout,
    )