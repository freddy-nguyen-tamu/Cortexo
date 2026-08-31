from __future__ import annotations

import itertools

from cortexo_ml.repository.dependency_graph import RepositoryGraph, symbol_node_id


def node_adjacency_matrix(graph: RepositoryGraph) -> tuple[list[str], list[list[float]]]:
    node_ids = [n.id for n in graph.nodes]
    index = {nid: i for i, nid in enumerate(node_ids)}
    size = len(node_ids)
    matrix = [[0.0] * size for _ in range(size)]
    for edge in graph.edges:
        if edge.source in index and edge.target in index:
            matrix[index[edge.source]][index[edge.target]] = 1.0
    return node_ids, matrix


def co_occurrence_paths(graph: RepositoryGraph, target_path: str, k: int = 8) -> list[str]:
    """Files that appear with target_path in the same edges (importers/imported)."""
    hits = []
    for edge in graph.edges:
        if target_path in (edge.source, edge.target):
            other = edge.target if edge.source == target_path else edge.source
            if ":" not in other and not other.startswith("table:"):
                hits.append(other)
    return list(dict.fromkeys(hits))[:k]


def symbol_mentions_from_imports(graph: RepositoryGraph, import_name: str) -> list[str]:
    """Resolve an import statement to candidate symbol node IDs."""
    candidates = []
    segment = import_name.replace("/", "-").replace(".", "-")
    for node in graph.nodes:
        if node.type in {"CLASS", "INTERFACE", "FUNCTION", "METHOD"}:
            if import_name.endswith(node.name) or node.name in import_name:
                candidates.append(node.id)
    _ = segment
    return candidates


def transitive_dependents(graph: RepositoryGraph, seed: str, depth: int = 2) -> set[str]:
    dependents: set[str] = set()
    frontier = {seed}
    for _ in range(depth):
        next_frontier: set[str] = set()
        for node in frontier:
            for edge in graph.edges:
                if edge.type == "IMPORTS" and edge.target == node:
                    if edge.source not in dependents:
                        dependents.add(edge.source)
                        next_frontier.add(edge.source)
        frontier = next_frontier
    return dependents


def effect_cone(graph: RepositoryGraph, seed_files: list[str], depth: int = 2) -> set[str]:
    """Approximate blast radius: tests + importers + callers of seed files."""
    affected: set[str] = set()
    frontier = set(seed_files)
    for _ in range(depth):
        next_frontier: set[str] = set()
        for node_id in frontier:
            for edge in graph.edges:
                if edge.target == node_id or (
                    edge.type in {"TESTS", "CALLS", "IMPORTS"} and edge.source == node_id
                ):
                    other = edge.source if edge.target == node_id else edge.target
                    if other not in affected and ":" in other:
                        affected.add(other)
                        node = next((n for n in graph.nodes if n.id == other), None)
                        if node and node.file:
                            next_frontier.add(node.file)
        frontier = next_frontier
    affected.update(seed_files)
    return affected