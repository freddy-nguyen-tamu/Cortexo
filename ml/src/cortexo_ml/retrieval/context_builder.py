from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from cortexo_ml.repository.dependency_graph import RepositoryGraph, neighbors, expand_neighbors
from cortexo_ml.retrieval.base import ChunkResult, RetrievalContext, approx_tokens
from cortexo_ml.retrieval.bm25 import BM25Retriever
from cortexo_ml.retrieval.dense import DenseRetriever
from cortexo_ml.retrieval.hybrid import reciprocal_rank_fusion
from cortexo_ml.retrieval.reranker import Reranker


@dataclass
class IndexedChunk:
    chunk_id: str
    path: str
    text: str
    symbol: str | None = None
    tokens: int = 0

    def as_result(self, stage: str | None = None, reason: str = "", score: float = 0.0, rank: int | None = None) -> ChunkResult:
        return ChunkResult(
            chunk_id=self.chunk_id,
            path=self.path,
            score=score,
            text=self.text,
            symbol=self.symbol,
            stage=stage,
            rank=rank,
            reason=reason,
            tokens=self.tokens,
        )


class RepositoryIndex:
    """In-memory snapshot retrieval index with BM25 + dense + hybrid + graph."""

    def __init__(self, repository: str, snapshot_id: str):
        self.repository = repository
        self.snapshot_id = snapshot_id
        self.chunks: list[IndexedChunk] = []
        self.graph: RepositoryGraph | None = None
        self.bm25 = BM25Retriever()
        self.dense = DenseRetriever()

    @classmethod
    def from_ingest(cls, result) -> "RepositoryIndex":
        index = cls(result.repository, result.snapshot_id)
        chunk_results: list[ChunkResult] = []
        for f in result.files:
            symbols = f.symbols or []
            line_to_symbol = {s["line"]: s["name"] for s in symbols}
            for c in f.chunks:
                start_line = c["start"] + 1
                symbol = line_to_symbol.get(start_line)
                if symbol is None:
                    for line in range(start_line, c["end"] + 2):
                        if line in line_to_symbol:
                            symbol = line_to_symbol[line]
                            break
                ic = IndexedChunk(
                    chunk_id=c["id"],
                    path=f.path,
                    text=c["text"],
                    symbol=symbol,
                    tokens=approx_tokens(c["text"]),
                )
                index.chunks.append(ic)
                chunk_results.append(
                    ic.as_result(reason="indexed", stage="index", score=1.0)
                )
        graph = getattr(result, "graph", None)
        if graph is not None:
            index.graph = RepositoryGraph(repository=result.repository, snapshot_id=result.snapshot_id)
            index.graph.nodes = graph.nodes
            index.graph.edges = graph.edges
        index.bm25.add_chunks(chunk_results)
        index.dense.add_chunks(chunk_results)
        return index

    def search(
        self,
        query: str,
        strategy: str = "GRAPH_HYBRID",
        top_k: int = 12,
        max_tokens: int = 8192,
    ) -> RetrievalContext:
        trace: list[dict] = []

        bm25_results = self.bm25.search(query, k=30)
        dense_results = self.dense.search(query, k=30)
        trace.append({"stage": "BM25", "candidates": len(bm25_results)})
        trace.append({"stage": "dense", "candidates": len(dense_results)})

        fused = reciprocal_rank_fusion([bm25_results, dense_results], k=60)
        trace.append({"stage": "RRF", "candidates": len(fused)})

        reranked = Reranker().rerank(query, fused, top_n=30)
        trace.append({"stage": "rerank", "candidates": len(reranked)})

        ast_normalized = self._ast_normalize(reranked)
        trace.append({"stage": "AST normalization", "candidates": len(ast_normalized)})

        graph_expanded = self._graph_expand(ast_normalized, query)
        trace.append({"stage": "graph expansion", "candidates": len(graph_expanded)})

        deduped = self._dedupe(graph_expanded)
        trace.append({"stage": "deduplication", "candidates": len(deduped)})

        packed = self._token_budget_pack(query, deduped, max_tokens=max_tokens)
        trace.append({"stage": "context compression", "candidates": len(packed), "usedTokens": sum(p.tokens for p in packed)})

        return RetrievalContext(
            query=query,
            strategy=strategy,
            maxTokens=max_tokens,
            usedTokens=sum(c.tokens for c in packed),
            chunks=[c for c in packed if c.included],
            trace=trace,
        )

    def _chunk_by_id(self, chunk_id: str) -> IndexedChunk | None:
        for ic in self.chunks:
            if ic.chunk_id == chunk_id:
                return ic
        return None

    def _ast_normalize(self, chunks: list[ChunkResult]) -> list[ChunkResult]:
        normalized: list[ChunkResult] = []
        for c in chunks:
            ic = self._chunk_by_id(c.chunk_id)
            if ic is None:
                continue
            if ic.symbol and "function" in str(c.reason).lower():
                c.reason += "+ast"
            normalized.append(c)
        # Prefer full-line boundaries: expand chunk to nearest full function block text stored.
        return normalized

    def _graph_expand(self, chunks: list[ChunkResult], query: str) -> list[ChunkResult]:
        if self.graph is None:
            return chunks
        seed_ids = []
        for c in chunks:
            ic = self._chunk_by_id(c.chunk_id)
            if ic is None:
                continue
            node_id = ic.path.replace("/", "-")
            seed_ids.append(node_id)
            if ic.symbol:
                seed_ids.append(f"{ic.path}:{ic.symbol}")

        seen_files = {self._chunk_by_id(c.chunk_id).path for c in chunks if self._chunk_by_id(c.chunk_id)}
        added: list[ChunkResult] = []
        for node_id in seed_ids:
            expanded, edges = expand_neighbors(self.graph, [node_id], depth=1, edge_types={"IMPORTS", "CONTAINS", "CALLS"})
            for other in expanded:
                if other == node_id:
                    continue
                for edge in edges:
                    if edge.source == other:
                        candidate_id = edge.target
                    else:
                        candidate_id = edge.source
                    if ":" in candidate_id or candidate_id.startswith("table:"):
                        continue
                    path = candidate_id
                    for ic in self.chunks:
                        if ic.path == path and ic.path not in seen_files:
                            seen_files.add(ic.path)
                            added.append(ic.as_result(stage="graph", reason="graph-expansion"))
        return chunks + added

    def _dedupe(self, chunks: list[ChunkResult]) -> list[ChunkResult]:
        seen: set[str] = set()
        out: list[ChunkResult] = []
        for c in chunks:
            key = hashlib.sha256(c.text.encode("utf-8")).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out

    def _token_budget_pack(self, query: str, chunks: list[ChunkResult], max_tokens: int) -> list[ChunkResult]:
        out: list[ChunkResult] = []
        used = 0
        query_tokens = approx_tokens(query)
        budget = max_tokens - query_tokens
        for rank, c in enumerate(chunks, start=1):
            c.rank = rank
            c.tokens = approx_tokens(c.text)
            if used + c.tokens > budget:
                c.included = False
                c.reason += "+excluded-budget"
            else:
                c.included = True
                c.reason += "+included"
                used += c.tokens
            out.append(c)
        return out

    def configure_graph(self, graph: RepositoryGraph) -> None:
        self.graph = graph