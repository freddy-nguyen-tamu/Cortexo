from __future__ import annotations

import re
from dataclasses import dataclass, field

SEPARATOR = "."
SANITIZE_RE = re.compile(r"[^A-Za-z0-9_./-]")

NODE_TYPES = {
    "MODULE", "FILE", "CLASS", "INTERFACE", "FUNCTION", "METHOD",
    "CONSTRUCTOR", "FIELD", "TEST", "ENDPOINT", "DATABASE_TABLE_REFERENCE", "CONFIG_KEY",
}
EDGE_TYPES = {
    "CONTAINS", "IMPORTS", "CALLS", "INHERITS", "IMPLEMENTS", "REFERENCES",
    "TESTS", "DEFINES_ENDPOINT", "READS_TABLE", "WRITES_TABLE", "CONFIGURES", "DEPENDS_ON",
}


@dataclass
class GraphNode:
    id: str
    type: str
    name: str
    file: str | None = None
    line: int | None = None


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    line: int | None = None


@dataclass
class RepositoryGraph:
    repository: str
    snapshot_id: str
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> None:
        if all(n.id != node.id for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: GraphEdge) -> None:
        if all((e.source, e.target, e.type) != (edge.source, edge.target, edge.type) for e in self.edges):
            self.edges.append(edge)

    def to_record(self) -> dict:
        return {
            "repository": self.repository,
            "snapshotId": self.snapshot_id,
            "nodes": [n.__dict__ for n in self.nodes],
            "edges": [e.__dict__ for e in self.edges],
        }


def file_node_id(path: str) -> str:
    return sanitize(path)


def sanitize(value: str) -> str:
    value = SANITIZE_RE.sub("-", value)
    return value.strip("-")


def symbol_node_id(path: str, symbol: str) -> str:
    return sanitize(f"{path}:{symbol}")


CALL_RE = re.compile(r"\b(\w+)\s*\(")


def build_graph(
    repository: str,
    snapshot_id: str,
    parsed_files: list,
    config_keys: list[str] | None = None,
) -> RepositoryGraph:
    graph = RepositoryGraph(repository=repository, snapshot_id=snapshot_id)
    graph.add_node(GraphNode(id=sanitize(repository), type="MODULE", name=repository))

    symbol_by_name: dict[str, dict] = {}
    file_nodes: dict[str, str] = {}

    for pf in parsed_files:
        fid = file_node_id(pf.path)
        file_nodes[pf.path] = fid
        graph.add_node(GraphNode(id=fid, type="FILE", name=pf.path))
        graph.add_edge(GraphEdge(sanitize(repository), fid, "CONTAINS"))

        for sym in pf.symbols:
            sid = symbol_node_id(pf.path, sym.name)
            graph.add_node(
                GraphNode(id=sid, type=sym.kind.upper(), name=sym.name, file=pf.path, line=sym.line)
            )
            graph.add_edge(GraphEdge(fid, sid, "CONTAINS", line=sym.line))
            symbol_by_name.setdefault(sym.name, []).append({"id": sid, "file": pf.path, "kind": sym.kind})

        for imp in pf.imports:
            target_fid = file_node_id(imp.replace(".", "/"))
            graph.add_edge(GraphEdge(fid, target_fid, "IMPORTS"))

        for ep in pf.endpoints:
            eid = symbol_node_id(pf.path, f"endpoint:{ep}")
            graph.add_node(GraphNode(id=eid, type="ENDPOINT", name=ep, file=pf.path))
            graph.add_edge(GraphEdge(fid, eid, "DEFINES_ENDPOINT"))

        for table in pf.table_references:
            tid = sanitize(f"table:{table}")
            graph.add_node(GraphNode(id=tid, type="DATABASE_TABLE_REFERENCE", name=table))
            graph.add_edge(GraphEdge(fid, tid, "READS_TABLE"))

        if pf.has_test:
            for sym in pf.symbols:
                if sym.kind not in {"function", "method"}:
                    continue
                for target, refs in symbol_by_name.items():
                    _ = refs
                    if target == sym.name:
                        continue
                    tid = symbol_node_id(pf.path, f"test:{sym.name}")
                    graph.add_node(GraphNode(id=tid, type="TEST", name=sym.name, file=pf.path))
                    graph.add_edge(GraphEdge(tid, symbol_node_id(pf.path, target), "TESTS"))

    return graph


def neighbors(graph: RepositoryGraph, node_id: str) -> list[GraphEdge]:
    return [e for e in graph.edges if e.source == node_id or e.target == node_id]


def expand_neighbors(
    graph: RepositoryGraph,
    seed: list[str],
    depth: int = 1,
    edge_types: set[str] | None = None,
) -> tuple[list[str], list[GraphEdge]]:
    """Return up to `depth` rounds of neighbor expansion from seed node ids."""
    seen = set(seed)
    frontier = list(seen)
    collected_edges: list[GraphEdge] = []
    for _ in range(depth):
        next_frontier: list[str] = []
        for node in frontier:
            for edge in neighbors(graph, node):
                if edge_types and edge.type not in edge_types:
                    continue
                collected_edges.append(edge)
                other = edge.target if edge.source == node else edge.source
                if other not in seen:
                    seen.add(other)
                    next_frontier.append(other)
        frontier = next_frontier
    return list(seen), collected_edges