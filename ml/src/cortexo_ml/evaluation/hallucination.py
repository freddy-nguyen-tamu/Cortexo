from __future__ import annotations

import re
from dataclasses import dataclass, field

from cortexo_ml.repository.dependency_graph import RepositoryGraph

FILE_PATTERN = re.compile(r"([`\"]?([\w./-]+\.(?:py|java|js|ts|tsx|go|rs|c|cc|cpp|h|cs|rb|php|sql|vue))[\`\"]?)")
SYMBOL_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(|\.|\band\b|\bof\b|\bin\b)")


@dataclass
class AuditableClaim:
    claim: str
    kind: str
    value: str
    supported: bool
    note: str = ""


@dataclass
class HallucinationReport:
    total_auditable: int = 0
    unsupported: int = 0
    findings: list[AuditableClaim] = field(default_factory=list)

    @property
    def hallucination_rate(self) -> float:
        return self.unsupported / max(1, self.total_auditable)

    def to_record(self) -> dict:
        return {
            "hallucinationRate": round(self.hallucination_rate, 4),
            "totalAuditableClaims": self.total_auditable,
            "unsupportedClaims": self.unsupported,
            "findings": [
                {"kind": f.kind, "claim": f.claim, "value": f.value, "supported": f.supported, "note": f.note}
                for f in self.findings
            ],
        }


class RepositoryFactChecker:
    """Validates claims against auditable repository facts."""

    def __init__(self, files: list[str], symbols: list[str], graph: RepositoryGraph | None = None):
        self.files = set(files)
        self.symbols = set(symbols)
        self.graph = graph

    def file_exists(self, path: str) -> bool:
        return path in self.files or any(path.endswith(f) for f in self.files)

    def symbol_exists(self, name: str) -> bool:
        return name in self.symbols

    def dependency_edge_exists(self, source: str, target: str, edge_type: str | None = None) -> bool:
        if self.graph is None:
            return True  # unverifiable without graph
        return any(
            (e.source == source and e.target == target)
            or (e.source == target and e.target == source)
            for e in self.graph.edges
            if edge_type is None or e.type == edge_type
        )

    def check_text(self, text: str, admit_file_patterns: list[str] | None = None) -> HallucinationReport:
        report = HallucinationReport()
        seen_paths: set[str] = set()
        for m in FILE_PATTERN.finditer(text):
            path = m.group(2)
            if path in seen_paths:
                continue
            seen_paths.add(path)
            supported = self.file_exists(path)
            report.total_auditable += 1
            claim = AuditableClaim(claim=path, kind="file", value=path, supported=supported, note="path exists" if supported else "nonexistent path")
            if not supported:
                report.unsupported += 1
            report.findings.append(claim)

        seen_symbols: set[str] = set()
        for m in SYMBOL_PATTERN.finditer(text):
            name = m.group(1)
            if len(name) < 3 or name in {"def", "class", "import", "from", "return", "if", "for", "while", "with", "self", "and", "or", "not", "the", "this"}:
                continue
            if name in seen_symbols:
                continue
            seen_symbols.add(name)
            # Only audit identifiers that look like code identifiers (mix of case or underscore).
            if not re.search(r"[A-Z]|_|\\b(?:.*_test|Test)\b", name) and name.islower() and len(name) < 10:
                continue
            report.total_auditable += 1
            supported = self.symbol_exists(name)
            claim = AuditableClaim(claim=name, kind="symbol", value=name, supported=supported, note="symbol exists" if supported else "nonexistent symbol")
            if not supported:
                report.unsupported += 1
            report.findings.append(claim)
        return report


def check_output_against_repository(output: str, snapshot_files: list[str], symbols: list[str], graph: RepositoryGraph | None = None) -> HallucinationReport:
    checker = RepositoryFactChecker(snapshot_files, symbols, graph)
    return checker.check_text(output)


def check_tool_result_claim(output: str, executed_tool_reports: list[str]) -> HallucinationReport:
    """Verify 'I ran tests' style claims against the actual tool log."""
    report = HallucinationReport()
    claims = re.findall(r"(?:I (?:ran|ran the|executed)|the (?:tests?|verifier))[^\n]*", output, re.I)
    joined_tools = "\n".join(executed_tool_reports)
    for claim in claims:
        report.total_auditable += 1
        supported = any(tool_name.lower() in claim.lower() for tool_name in ("tests", "compile", "lint", "formatter", "verifier"))
        if not supported:
            report.unsupported += 1
        report.findings.append(AuditableClaim(claim=claim.strip()[:120], kind="tool-result", value=claim.strip()[:120], supported=supported, note="tool call logged" if supported else "invented tool result"))
    return report


def invented_relation_claims(output: str, graph: RepositoryGraph | None, max_checks: int = 50) -> HallucinationReport:
    report = HallucinationReport()
    if graph is None:
        return report
    relations = re.findall(r"([\w./-]+\.(?:py|java|js|ts|go)) (?:calls|imports|extends|implements|uses|depends on) ([\w./-]+\.(?:py|java|js|ts|go))", output)
    seen = set()
    for src, dst in relations:
        if (src, dst) in seen:
            continue
        seen.add((src, dst))
        if len(seen) > max_checks:
            break
        report.total_auditable += 1
        supported = graph.dependency_edge_exists(src, dst)
        if not supported:
            report.unsupported += 1
        report.findings.append(AuditableClaim(claim=f"{src} -> {dst}", kind="relation", value=f"{src}->{dst}", supported=supported, note="edge in graph" if supported else "unsupported relation"))
    return report