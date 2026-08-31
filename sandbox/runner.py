#!/usr/bin/env python3
"""Cortexo sandbox execution runner.

Reads a single JSON request on stdin (or --request-file PATH):

    {"workspaceId": "...", "commandType": "TEST",
     "language": "java", "timeoutSeconds": 60}

commandType is restricted to TEST / COMPILE / LINT / FORMAT / STATIC_ANALYSIS.
A free-form "command" field is never accepted.

The runner resolves the predefined command from sandbox/policy.py, launches an
ephemeral container with the sandbox flag set, streams logs back and deletes
the workspace afterwards.

Run from the repository root (so seccomp-profile.json resolves):

    python3 sandbox/runner.py --request-file /tmp/req.json --workspace /tmp/ws --image cortexo-sandbox:latest
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from policy import DEFAULT_MEMORY, DEFAULT_CPUS, DEFAULT_PIDS, PolicyViolation, docker_flags, evaluate_request, MAX_OUTPUT_BYTES  # noqa: E402


def _truncate(data: str, limit: int = MAX_OUTPUT_BYTES) -> str:
    if len(data) <= limit:
        return data
    return data[:limit] + f"\n... [truncated {len(data) - limit} bytes]"


def read_request(path: str | None) -> dict:
    if path:
        req = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        req = json.loads(sys.stdin.read())
    if not isinstance(req, dict):
        raise PolicyViolation("request must be a JSON object")
    return req


def run_request(req: dict, workspace: Path) -> dict:
    decision = evaluate_request(req)

    if not decision.allowed:
        return {
            "ok": False,
            "passed": False,
            "policy": True,
            "exitCode": None,
            "stdout": "",
            "stderr": decision.reason,
            "error": "SANDBOX_POLICY",
        }

    workspace = workspace.expanduser().resolve()
    if not workspace.is_dir():
        return {
            "ok": False,
            "passed": False,
            "exitCode": None,
            "stdout": "",
            "stderr": f"workspace not found: {workspace}",
            "error": "WORKSPACE_MISSING",
        }

    start = time.monotonic()
    cidfile = tempfile.NamedTemporaryFile(delete=False, prefix="cortexo-cid-").name

    flags = docker_flags(
        memory=decision.memory,
        cpus=decision.cpus,
        pids=decision.pids,
        timeout_ms=decision.timeout_seconds * 1000,
    )
    flags += [
        "--cidfile", cidfile,
        "--volume", f"{workspace}:/work",
        "--entrypoint", "/usr/bin/timeout",
        os.environ.get("CORTEXO_SANDBOX_IMAGE", "cortexo-sandbox:latest"),
        "--kill-after=10", str(decision.timeout_seconds),
        *decision.command,
    ]
    command = ["docker", "run", *flags]

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=decision.timeout_seconds + 30)
    except subprocess.TimeoutExpired:
        timed_out = True
        container_id = None
        try:
            container_id = Path(cidfile).read_text(encoding="utf-8").strip()
        except OSError:
            container_id = None
        if container_id:
            subprocess.run(["docker", "kill", container_id], capture_output=True, text=True, timeout=20)
        proc.kill()
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", "Timed out and could not collect output"
        stderr += "\n[runner] wall-clock timeout enforced; process tree killed"

    duration_ms = int((time.monotonic() - start) * 1000)

    try:
        os.unlink(cidfile)
    except OSError:
        pass

    exit_code = proc.returncode if proc.returncode is not None else -1
    passed = (not timed_out) and exit_code == 0

    return {
        "ok": True,
        "passed": passed,
        "policy": False,
        "exitCode": exit_code,
        "stdout": _truncate(stdout),
        "stderr": _truncate(stderr),
        "timedOut": timed_out,
        "durationMs": duration_ms,
        "commandType": req.get("commandType"),
        "memory": decision.memory,
        "cpus": decision.cpus,
        "pids": decision.pids,
        "timeoutSeconds": decision.timeout_seconds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Cortexo sandbox runner")
    parser.add_argument("--request-file", help="path to a JSON request (else reads stdin)")
    parser.add_argument("--workspace", required=True, help="host workspace directory to execute in")
    parser.add_argument("--keep-workspace", action="store_true", help="do not delete the workspace after the run")
    args = parser.parse_args()

    try:
        req = read_request(args.request_file)
        workspace = Path(args.workspace)
    except (json.JSONDecodeError, PolicyViolation, OSError) as exc:
        print(json.dumps({"ok": False, "policy": True, "error": "BAD_REQUEST", "stderr": str(exc)}))
        return 2

    result = run_request(req, workspace)
    if not args.keep_workspace:
        shutil.rmtree(workspace, ignore_errors=True)

    print(json.dumps(result))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())