from __future__ import annotations

from cortexo_ml.repository.dependency_graph import RepositoryGraph

try:
    import networkx as nx
except ImportError:  # pragma: no cover - optional heavy dependency
    nx = None


def _nx() -> "networkx_type":
    if nx is None:  # pragma: no cover
        raise RuntimeError("networkx required: pip install networkx")
    return nx


def to_networkx(graph: RepositoryGraph):
    G = _nx().DiGraph()
    for node in graph.nodes:
        G.add_node(node.id, type=node.type, name=node.name, file=node.file, line=node.line)
    for edge in graph.edges:
        G.add_edge(edge.source, edge.target, type=edge.type)
    return G


def pagerank(graph: RepositoryGraph, alpha: float = 0.85, max_iter: int = 200) -> dict[str, float]:
    G = to_networkx(graph)
    return dict(_nx().pagerank(G, alpha=alpha, max_iter=max_iter))


def betweenness(graph: RepositoryGraph, k: int = 32) -> dict[str, float]:
    G = to_networkx(graph).to_undirected()
    return dict(_nx().betweenness_centrality(G, k=k))


def shortest_path(graph: RepositoryGraph, source: str, target: str) -> list[str]:
    G = to_networkx(graph)
    try:
        return _nx().shortest_path(G.to_undirected(), source, target)
    except (_nx().NetworkXNoPath, _nx().NodeNotFound):
        return []


def subgraph(graph: RepositoryGraph, seeds: list[str], depth: int = 1) -> RepositoryGraph:
    from cortexo_ml.repository.dependency_graph import GraphNode, GraphEdge, neighbors

    reachable = set(seeds)
    frontier = list(seeds)
    for _ in range(depth):
        nxt = []
        for node_id in frontier:
            for edge in neighbors(graph, node_id):
                other = edge.target if edge.source == node_id else edge.source
                if other not in reachable:
                    reachable.add(other)
                    nxt.append(other)
        frontier = nxt

    nodes = [n for n in graph.nodes if n.id in reachable]
    edges = [e for e in graph.edges if e.source in reachable or e.target in reachable]
    sub = RepositoryGraph(repository=graph.repository, snapshot_id=graph.snapshot_id)
    sub.nodes = nodes
    sub.edges = edges
    return sub


def node_frequencies(graph: RepositoryGraph) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in graph.nodes:
        counts[node.type] = counts.get(node.type, 0) + 1
    return counts


def edge_frequencies(graph: RepositoryGraph) -> dict[str, int]:
    counts: dict[str, int] = {}
    for edge in graph.edges:
        counts[edge.type] = counts.get(edge.type, 0) + 1
    return counts