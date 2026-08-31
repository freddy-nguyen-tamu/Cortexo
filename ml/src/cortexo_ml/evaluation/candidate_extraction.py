"""Normalize untrusted model text into a sandbox-able candidate WITHOUT executing it.

A candidate is one of:

- kind="full_file": the complete contents of the single allowed target file.
- kind="unified_diff": a unified diff that modifies existing allowed files.

Nothing here imports, compiles, or executes candidate modules on the host.
The final compile/test run belongs to the Docker sandbox.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from dataclasses import dataclass

MAX_CANDIDATE_BYTES = 256 * 1024  # 256 KiB hard size cap

# The candidate protocol supports in-place modifications only; creating or
# deleting files is rejected before staging.
_CREATE_OR_DELETE_MODE = re.compile(r"^\s*(new file mode|deleted file mode)\s", re.MULTILINE)

_FENCE_RE = re.compile(r"```([A-Za-z0-9_+-]*)[ \t]*\n?(.*?)```", re.DOTALL)

_DIFF_GIT_HEADER = re.compile(r"^\s*diff --git\s+a/(.+?)\s+b/(.+?)\s*$", re.MULTILINE)
_DIFF_SIMPLE_HEADER = re.compile(r"^\s*(?:---|\+\+\+)\s+(?:a/)?(\S+)\s*$", re.MULTILINE)

_BLOCKED_PREFIXES = (
    "tests",
    "benches_hidden",
    "hidden_tests",
    "benchmarks/hidden_tests",
    ".cortexo",
    ".git",
)


class CandidateExtractionError(ValueError):
    """Raised when model output cannot be turned into a safe candidate."""


@dataclass(frozen=True)
class Candidate:
    kind: str  # "full_file" or "unified_diff"
    content: str
    sha256: str
    byte_count: int


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fences_in(output: str) -> list[tuple[str | None, str]]:
    return [(m.group(1) or None, m.group(2)) for m in _FENCE_RE.finditer(output)]


def _is_unified_diff(text: str) -> bool:
    return bool(_DIFF_GIT_HEADER.search(text)) or bool(_DIFF_SIMPLE_HEADER.search(text))


def _extract_diff(text: str) -> str:
    """Return only the diff portion of the model output.

    Lines that look like explicit diff/hunk headers stay; trailing prose that
    cannot be part of a patch ends the candidate.
    """
    lines = text.splitlines()

    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("diff --git") or re.match(r"^---\s+(a/)?\S+", stripped):
            start = i
            break

    def _diff_line(line: str) -> bool:
        if line.startswith(("+++", "---", "@@", "\\")):
            return True
        if line.startswith((" ", "+", "-")):
            return True
        if re.match(r"^\s*diff --git\s+a/", line):
            return True
        if re.match(r"^\s*(new file mode|deleted file mode|index |similarity |rename |GIT binary)", line):
            return True
        return False

    body: list[str] = []
    for line in lines[start:]:
        if body and not _diff_line(line):
            break
        if body or _diff_line(line):
            body.append(line)
    return "\n".join(body).strip("\n")


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def _reject_unsafe_path(path: str) -> None:
    if not path:
        raise CandidateExtractionError("diff references an empty path")
    if path.startswith("/"):
        raise CandidateExtractionError(f"absolute path rejected: {path}")
    if re.match(r"^[A-Za-z]:", path):
        raise CandidateExtractionError(f"absolute path rejected: {path}")
    parts = [p for p in path.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise CandidateExtractionError(f"parent traversal rejected: {path}")
    if ".git" in parts or ".cortexo" in parts:
        raise CandidateExtractionError(f"protected path rejected: {path}")
    if path.startswith(_BLOCKED_PREFIXES):
        raise CandidateExtractionError(f"protected path rejected: {path}")


def _header_paths(diff_text: str) -> list[str]:
    """Extract every file path referenced by diff headers (both a/ and b/ sides)."""
    paths: list[str] = []
    seen: set[str] = set()
    for m in _DIFF_GIT_HEADER.finditer(diff_text):
        for side in (m.group(1), m.group(2)):
            p = _normalize_path(side)
            if p not in seen:
                seen.add(p)
                paths.append(p)
    if paths:
        return paths
    for m in _DIFF_SIMPLE_HEADER.finditer(diff_text):
        p = _normalize_path(m.group(1))
        if p not in seen:
            seen.add(p)
            paths.append(p)
    return paths


def changed_paths_from_diff(diff_text: str) -> list[str]:
    """Return the unique file paths a unified diff touches (validated)."""
    if _CREATE_OR_DELETE_MODE.search(diff_text):
        raise CandidateExtractionError("file creation/deletion is not supported by the candidate protocol")
    paths = _header_paths(diff_text)
    for p in paths:
        _reject_unsafe_path(p)
    return paths


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def validate_diff_targets(diff_text: str, allowed_targets: set[str]) -> list[str]:
    """Validate every changed path against the registry allow-list.

    A changed path is allowed when it exactly matches an allowed target or its
    basename does AND that basename uniquely corresponds to an allowed target
    (one-target tasks may be patched with a repository-prefixed path).

    Returns the list of changed files. Raises CandidateExtractionError for any
    unsafe or unlisted path so a bad diff can never reach git apply.
    """
    if _CREATE_OR_DELETE_MODE.search(diff_text):
        raise CandidateExtractionError("file creation/deletion is not supported by the candidate protocol")

    allowed_basenames = {_basename(t) for t in allowed_targets}
    changed: list[str] = []
    seen: set[str] = set()

    for p in _header_paths(diff_text):
        _reject_unsafe_path(p)
        if p in allowed_targets:
            pass
        elif _basename(p) in allowed_basenames and len(allowed_basenames) == 1:
            pass
        else:
            raise CandidateExtractionError(f"diff targets unlisted or unsafe path: {p}")
        if p not in seen:
            seen.add(p)
            changed.append(p)

    if not changed:
        raise CandidateExtractionError("diff does not reference any changed files")
    return changed


def normalize_diff_target(diff_text: str, target: str) -> str:
    """Rewrite a one-file diff so its headers point at the single allowed
    target. Used only when the diff changes exactly one file and the grader
    registry allows exactly one candidate target."""
    title = _normalize_path(target)
    lines = []
    for line in diff_text.splitlines():
        if re.match(r"^---\s+a/", line):
            line = re.sub(r"^---\s+a/\S+", f"--- a/{title}", line)
        elif re.match(r"^\+\+\+\s+b/", line):
            line = re.sub(r"^\+\+\+\s+b/\S+", f"+++ b/{title}", line)
        elif re.match(r"^diff --git\s+a/\S+\s+b/\S+", line):
            line = re.sub(r"^diff --git\s+a/\S+\s+b/\S+", f"diff --git a/{title} b/{title}", line)
        lines.append(line)
    return "\n".join(lines)


def extract_candidate(output: str, language: str = "python") -> Candidate:
    """Extract the normalized candidate from raw model output."""
    if not output or not output.strip():
        raise CandidateExtractionError("candidate output is empty")

    raw = output.strip()

    # Unified diffs take precedence so a model that answers with a patch is
    # graded as a patch even when the diff is wrapped in narrative.
    if _is_unified_diff(raw):
        content = _extract_diff(raw)
        if not content:
            raise CandidateExtractionError("candidate diff is empty")
        if len(content.encode("utf-8")) > MAX_CANDIDATE_BYTES:
            raise CandidateExtractionError("candidate diff exceeds the size limit")
        return Candidate(
            kind="unified_diff",
            content=content,
            sha256=_sha256(content),
            byte_count=len(content.encode("utf-8")),
        )

    # Fenced candidates: prefer a python/py fence for Python tasks, otherwise
    # the first non-empty fence.
    fences = _fences_in(raw)
    picked: str | None = None
    if fences:
        favored = [code for tag, code in fences if (tag or "").lower() in {"python", "py"}]
        if favored:
            picked = favored[0]
        elif len(fences) == 1:
            picked = fences[0][1]
        else:
            for _, code in fences:
                if code.strip():
                    picked = code
                    break
        if picked is None:
            raise CandidateExtractionError("no non-empty code fence found")
        content = picked.strip()
    else:
        content = raw

    if not content:
        raise CandidateExtractionError("candidate source is empty")

    if len(content.encode("utf-8")) > MAX_CANDIDATE_BYTES:
        raise CandidateExtractionError("candidate source exceeds the size limit")

    return Candidate(
        kind="full_file",
        content=content,
        sha256=_sha256(content),
        byte_count=len(content.encode("utf-8")),
    )


def count_changed_lines(before: str, after: str) -> int:
    """Count +/- content lines between two file versions (excludes headers)."""
    count = 0
    for line in difflib.unified_diff(
        (before or "").splitlines(),
        (after or "").splitlines(),
        lineterm="",
    ):
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+") or line.startswith("-"):
            count += 1
    return count


def count_changed_lines_in_diff(diff_text: str) -> int:
    """Count +/- content lines inside a unified diff (excludes headers)."""
    count = 0
    for line in diff_text.splitlines():
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+") or line.startswith("-"):
            count += 1
    return count