from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from cortexo_ml.common.stable_hash import stable_hash_bytes
from cortexo_ml.repository.dependency_graph import build_graph, RepositoryGraph
from cortexo_ml.repository.symbols import parse_file

CHUNK_TARGET_CHARS = 1500
CHUNK_OVERLAP_CHARS = 150

EXCLUDED_DIRS = {
    "node_modules", "vendor", "build", "dist", "target", "__pycache__",
    ".git", ".idea", ".gradle", ".venv", "venv", ".cache", "repos",
}
EXCLUDED_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".tar",
    ".jar", ".class", ".so", ".dll", ".exe", ".woff", ".woff2", ".ico",
}


@dataclass
class IngestedFile:
    path: str
    content: str
    sha256: str
    size: int
    language: str | None
    symbols: list[dict] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    chunks: list[dict] = field(default_factory=list)


@dataclass
class IngestResult:
    snapshot_id: str
    repository: str
    files: list[IngestedFile] = field(default_factory=list)
    graph: RepositoryGraph | None = None
    stats: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        return {
            "snapshotId": self.snapshot_id,
            "repository": self.repository,
            "files": [
                {
                    "path": f.path,
                    "hash": f.sha256,
                    "size": f.size,
                    "language": f.language,
                    "symbolCount": len(f.symbols),
                    "chunkCount": len(f.chunks),
                }
                for f in self.files
            ],
            "stats": self.stats,
        }


def iter_repo_files(root: str | Path):
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root)).replace(os.sep, "/")
        if any(seg in EXCLUDED_DIRS for seg in rel.split("/")):
            continue
        if Path(rel).suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        if rel.startswith(".env") or rel.endswith((".pem", ".key")):
            continue
        yield path, rel


def _chunk_text(content: str, target: int = CHUNK_TARGET_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[dict]:
    chunks: list[dict] = []
    if len(content) <= target:
        return [{"start": 0, "end": len(content)}]
    start = 0
    idx = 0
    while start < len(content):
        end = min(start + target, len(content))
        cutoff = end
        nearest = content.rfind("\n", start, end)
        if nearest > start + target // 2:
            cutoff = nearest
        chunks.append({"start": start, "end": cutoff})
        start = max(start + 1, cutoff - overlap)
        idx += 1
        if idx > 10_000:
            break
    if not chunks:
        chunks.append({"start": 0, "end": len(content)})
    return chunks


def ingest_repository(
    repository: str,
    repo_root: str | Path,
    snapshot_id: str | None = None,
    max_files: int = 0,
) -> IngestResult:
    repo_root = Path(repo_root)
    if snapshot_id is None:
        snapshot_id = hashlib.sha256(f"{repository}".encode()).hexdigest()[:16]

    result = IngestResult(snapshot_id=snapshot_id, repository=repository)
    total_chars = 0

    for path, rel in iter_repo_files(repo_root):
        raw = path.read_bytes()
        content = raw.decode("utf-8", errors="replace")
        total_chars += len(content)

        pf = parse_file(rel, content)
        symbols = [{"name": s.name, "kind": s.kind, "line": s.line, "endLine": s.end_line} for s in pf.symbols]
        chunks = []
        for chunk in _chunk_text(content):
            chunk_text = content[chunk["start"]:chunk["end"]]
            chunk_hash = stable_hash_bytes(chunk_text.encode("utf-8"))
            chunks.append({
                "id": hashlib.sha256(f"{rel}:{chunk['start']}:{chunk_text}".encode()).hexdigest()[:16],
                "start": chunk["start"],
                "end": chunk["end"],
                "text": chunk_text,
                "hash": chunk_hash,
            })

        result.files.append(
            IngestedFile(
                path=rel,
                content=content,
                sha256=hashlib.sha256(raw).hexdigest(),
                size=len(raw),
                language=pf.language,
                symbols=symbols,
                imports=pf.imports,
                chunks=chunks,
            )
        )
        if max_files and len(result.files) >= max_files:
            break

    graph = build_graph(repository, snapshot_id, [parse_file(f.path, f.content) for f in result.files])
    result.graph = graph

    total_symbols = sum(len(f.symbols) for f in result.files)
    total_chunks = sum(len(f.chunks) for f in result.files)
    result.stats = {
        "fileCount": len(result.files),
        "totalChars": total_chars,
        "symbolCount": total_symbols,
        "chunkCount": total_chunks,
        "edgeCount": len(graph.edges),
        "nodeCount": len(graph.nodes),
    }
    return result


def write_ingestion_artifacts(
    result: IngestResult,
    out_dir: str | Path,
) -> dict[str, str]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = result.to_record()
    manifest["graph"] = result.graph.to_record() if result.graph else None
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    chunks_dir = out_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    for f in result.files:
        for c in f.chunks:
            (chunks_dir / f"{c['id']}.txt").write_text(c["text"], encoding="utf-8")

    (out_dir / "graph.json").write_text(json.dumps((result.graph.to_record() if result.graph else {}), indent=2))
    return {"manifest": str(out_dir / "manifest.json"), "graph": str(out_dir / "graph.json")}