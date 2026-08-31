import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from cortexo_ml.common.license_gate import verify_license_for_training
from cortexo_ml.common.secrets import scan_file

EXCLUDED_NAMES = {
    ".env", ".env.", "node_modules", "vendor", "build", "dist", "target",
    "__pycache__", ".git", ".idea", ".gradle", ".cache", "venv", ".venv",
}
EXCLUDED_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".jar", ".class", ".so", ".dll", ".dylib", ".exe", ".bin", ".woff",
    ".woff2", ".ttf", ".eot", ".ipynb_checkpoints",
}


@dataclass
class CollectedFile:
    source_id: str
    path: str
    content: str
    sha256: str
    bytes: int
    language: str | None = None


@dataclass
class CollectReport:
    source_id: str
    collected: list[CollectedFile] = field(default_factory=list)
    skipped_binary: int = 0
    skipped_excluded: int = 0
    skipped_license: int = 0
    skipped_secrets: list[str] = field(default_factory=list)


LANGUAGE_BY_EXT = {
    ".py": "python", ".pyi": "python", ".java": "java", ".js": "javascript",
    ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescriptreact",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php", ".c": "c",
    ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".cs": "csharp", ".scala": "scala",
    ".kt": "kotlin", ".sql": "sql", ".vue": "vue", ".svelte": "svelte",
    ".html": "html", ".css": "css", ".scss": "scss", ".sh": "shell", ".bash": "shell",
}


def path_should_skip(path: str) -> tuple[bool, str]:
    parts = Path(path).parts
    for component in parts:
        if component in EXCLUDED_NAMES:
            return True, "excluded-name"
    if re.search(r"(^|/)\.env(\.|$)", path):
        return True, "env-file"
    if Path(path).suffix.lower() in EXCLUDED_SUFFIXES:
        return True, "binary-like-suffix"
    if re.search(r"(requirements.*\.lock|package-lock\.json|yarn\.lock|Pipfile\.lock|poetry\.lock)$", path):
        return True, "lockfile"
    return False, ""


def collect_directory(
    source_id: str,
    root: str | Path,
    manifest_entry: dict,
    out_dir: str | Path,
    secret_threshold: int = 1,
) -> CollectReport:
    ok, reason = verify_license_for_training(manifest_entry)
    report = CollectReport(source_id=source_id)
    if not ok:
        report.skipped_license = 1
        return report

    root = Path(root)
    out = Path(out_dir) / source_id
    out.mkdir(parents=True, exist_ok=True)

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        skip, why = path_should_skip(rel)
        if skip:
            if why == "binary-like-suffix":
                report.skipped_binary += 1
            else:
                report.skipped_excluded += 1
            continue

        data = path.read_bytes()
        if b"\x00" in data[:8192]:
            report.skipped_binary += 1
            continue

        text = data.decode("utf-8", errors="replace")
        findings = scan_file(path)
        if len(findings) >= secret_threshold:
            report.skipped_secrets.append(rel)
            report.skipped_excluded += 1
            continue

        rel_path = out / rel
        rel_path.parent.mkdir(parents=True, exist_ok=True)
        rel_path.write_bytes(data)

        report.collected.append(
            CollectedFile(
                source_id=source_id,
                path=rel,
                content=text,
                sha256=hashlib.sha256(data).hexdigest(),
                bytes=len(data),
                language=LANGUAGE_BY_EXT.get(path.suffix.lower()),
            )
        )
    return report


def read_manifest(path: str | Path) -> list[dict]:
    entries = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        entries.append(json.loads(line))
    return entries


def gate_entry(entry: dict) -> tuple[bool, str]:
    ok, reason = verify_license_for_training(entry)
    if not ok:
        return False, reason
    if entry.get("source_type") not in {"dataset", "repository"}:
        return False, "unsupported source_type"
    return True, "ok"