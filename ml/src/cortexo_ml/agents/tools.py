from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

TOOL_NAMES = [
    "list_files",
    "read_file",
    "search_text",
    "search_symbols",
    "retrieve_context",
    "graph_neighbors",
    "write_patch",
    "apply_patch",
    "run_tests",
    "run_linter",
    "run_formatter",
    "compile_project",
    "get_git_diff",
    "revert_workspace",
]

COMMAND_TYPE_BY_TOOL = {
    "run_tests": "TEST",
    "compile_project": "COMPILE",
    "run_linter": "LINT",
    "run_formatter": "FORMAT",
}


@dataclass
class ToolSpec:
    name: str
    description: str
    arguments: dict = field(default_factory=dict)


TOOL_SPECS: dict[str, ToolSpec] = {
    "list_files": ToolSpec("list_files", "List files in the workspace (optionally filtered by extension).", {"ext": "optional string"}),
    "read_file": ToolSpec("read_file", "Read a file from the workspace by path.", {"path": "string (required)"}),
    "search_text": ToolSpec("search_text", "Regex/plain-text search across workspace files.", {"query": "string (required)", "path": "optional path" }),
    "search_symbols": ToolSpec("search_symbols", "Search indexed symbols by name.", {"symbol": "string (required)"}),
    "retrieve_context": ToolSpec("retrieve_context", "Run retrieval against the repository index for a query.", {"query": "string (required)", "maxTokens": "optional int"}),
    "graph_neighbors": ToolSpec("graph_neighbors", "Return graph neighbors of a file or symbol node.", {"node": "string (required)", "depth": "optional int"}),
    "write_patch": ToolSpec("write_patch", "Stage a unified diff patch (does not apply).", {"patch": "unified diff (required)"}),
    "apply_patch": ToolSpec("apply_patch", "Apply a staged or inline unified diff to the workspace.", {"patch": "unified diff (required)"}),
    "run_tests": ToolSpec("run_tests", "Run the project test suite via the sandbox runner.", {"target": "optional test target"}),
    "run_linter": ToolSpec("run_linter", "Run the configured linter in the sandbox.", {}),
    "run_formatter": ToolSpec("run_formatter", "Run the configured formatter (check-only) in the sandbox.", {}),
    "compile_project": ToolSpec("compile_project", "Compile the project in the sandbox.", {}),
    "get_git_diff": ToolSpec("get_git_diff", "Return the current workspace diff.", {}),
    "revert_workspace": ToolSpec("revert_workspace", "Revert workspace to snapshot baseline.", {}),
}


class ToolError(RuntimeError):
    pass


ROOT_TRAP_RE = re.compile(r"(^|/)(\.\.|~)(/|$)")
SECRET_EXTS = {".pem", ".key", ".pub", ".env"}


class ToolExecutor:
    """Maps allow-listed tool requests to predefined commands. No arbitrary shell."""

    def __init__(self, workspace: str | Path, logger=None, sandbox=None):
        self.workspace = Path(workspace)
        self.logger = logger
        self.sandbox = sandbox
        self.pending_patch: str | None = None
        self.log: list[dict] = []

    def execute(self, tool: str, arguments: dict) -> dict:
        if tool not in TOOL_SPECS:
            raise ToolError(f"unknown tool: {tool}")
        handler = getattr(self, f"_do_{tool}", None)
        if handler is None:
            raise ToolError(f"tool not implemented: {tool}")
        result = handler(arguments)
        self.log.append({"tool": tool, "arguments": arguments, "result": _summarize(result)})
        if self.logger:
            self.logger({"tool": tool, "arguments": arguments, "ok": not isinstance(result, dict) or result.get("ok", True)})
        return result

    def _resolve(self, arguments: dict) -> Path:
        path = str(arguments.get("path") or arguments.get("file") or "")
        if ROOT_TRAP_RE.search(path):
            raise ToolError(f"path outside workspace: {path}")
        resolved = (self.workspace / path).resolve()
        if not str(resolved).startswith(str(self.workspace.resolve())):
            raise ToolError(f"path outside workspace: {path}")
        return resolved

    def _do_list_files(self, args: dict) -> dict:
        ext = args.get("ext")
        files = []
        for p in sorted(self.workspace.rglob("*")):
            if p.is_file() and (not ext or p.suffix == ext):
                files.append(str(p.relative_to(self.workspace)))
        return {"ok": True, "files": files[:500], "count": len(files)}

    def _do_read_file(self, args: dict) -> dict:
        path = self._resolve(args)
        if path.suffix in SECRET_EXTS:
            raise ToolError("refusing to read secret file")
        return {"ok": True, "path": str(path.relative_to(self.workspace)), "content": path.read_text(errors="replace")}

    def _do_search_text(self, args: dict) -> dict:
        query = args.get("query", "")
        path = args.get("path")
        root = self._resolve({"path": path}) if path else self.workspace
        hits = []
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.suffix in SECRET_EXTS:
                continue
            try:
                text = p.read_text(errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if re.search(query, line, re.IGNORECASE):
                    hits.append({"path": str(p.relative_to(self.workspace)), "line": lineno, "text": line.strip()[:200]})
        return {"ok": True, "hits": hits[:200], "count": len(hits)}

    def _do_search_symbols(self, args: dict) -> dict:
        raise ToolError("search_symbols requires a repository index; wire use 'retrieve_context'")

    def _do_retrieve_context(self, args: dict) -> dict:
        raise ToolError("retrieve_context requires a RepositoryIndex; see RepairAgent(var) index wiring")

    def _do_graph_neighbors(self, args: dict) -> dict:
        raise ToolError("graph_neighbors requires a repository graph")

    def _do_write_patch(self, args: dict) -> dict:
        self.pending_patch = args.get("patch")
        return {"ok": True, "staged": bool(self.pending_patch)}

    def _do_apply_patch(self, args: dict) -> dict:
        patch = args.get("patch") or self.pending_patch
        if not patch:
            raise ToolError("no patch provided")
        try:
            import subprocess

            subprocess.run(
                ["patch", "-p1", "--forward", "-d", str(self.workspace)],
                input=patch,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ToolError(f"patch apply failed: {exc}") from exc
        self.pending_patch = None
        return {"ok": True, "applied": True}

    def _sandbox_run(self, command_type: str, args: dict) -> dict:
        if self.sandbox is None:
            return {"ok": True, "skipped": True, "message": "no sandbox configured (offline mode)"}
        request = {
            "workspaceId": str(self.workspace.name),
            "commandType": command_type,
            "language": args.get("language", "python"),
            "timeoutSeconds": int(args.get("timeoutSeconds", 60)),
        }
        return self.sandbox.run(request)

    def _do_run_tests(self, args: dict) -> dict:
        return self._sandbox_run("TEST", args)

    def _do_compile_project(self, args: dict) -> dict:
        return self._sandbox_run("COMPILE", args)

    def _do_run_linter(self, args: dict) -> dict:
        return self._sandbox_run("LINT", args)

    def _do_run_formatter(self, args: dict) -> dict:
        return self._sandbox_run("FORMAT", args)

    def _do_get_git_diff(self, args: dict) -> dict:
        try:
            import subprocess

            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            return {"ok": True, "diff": result.stdout or "(no changes)"}
        except (OSError, subprocess.SubprocessError) as exc:
            return {"ok": False, "diff": "", "error": str(exc)}

    def _do_revert_workspace(self, args: dict) -> dict:
        try:
            import subprocess

            subprocess.run(
                ["git", "checkout", "--", "."],
                cwd=str(self.workspace),
                capture_output=True,
                check=False,
                timeout=60,
            )
            return {"ok": True, "reverted": True}
        except (OSError, subprocess.SubprocessError) as exc:
            return {"ok": False, "error": str(exc)}


def _summarize(result: dict) -> dict:
    keys = ("ok", "count", "staged", "applied", "skipped", "testSummary")
    return {k: result[k] for k in keys if k in result} or {"keys": list(result)}