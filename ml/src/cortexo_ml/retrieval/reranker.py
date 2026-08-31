from __future__ import annotations

from cortexo_ml.retrieval.base import ChunkResult, simple_tokenize


class Reranker:
    """Rerank RRf candidates.

    When a cross-encoder is installed (`cross_encoder` package) it is used as
    the semantic signal; otherwise a lightweight overlap + structural bonus
    heuristic is used so the pipeline is dependency-free.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        except ImportError:
            self._model = None

    def rerank(self, query: str, chunks: list[ChunkResult], top_n: int = 12) -> list[ChunkResult]:
        if not chunks:
            return []
        self._load()
        if self._model is not None:
            pairs = [(query, c.text[:4000]) for c in chunks]
            scores = self._model.predict(pairs).tolist()
        else:
            q_terms = set(simple_tokenize(query))
            scores = []
            for c in chunks:
                overlap = len(q_terms & set(simple_tokenize(c.text)))
                structural = 0.0
                if c.symbol:
                    structural += 0.3
                if c.path.endswith((".py", ".java", ".js", ".ts", ".go", ".rs")):
                    structural += 0.1
                if "test" in c.path.lower():
                    structural += 0.05
                scores.append(overlap + structural)

        ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)[:top_n]
        results = []
        for rank, (chunk, score) in enumerate(ranked, start=1):
            results.append(
                ChunkResult(
                    chunk_id=chunk.chunk_id,
                    path=chunk.path,
                    score=float(score),
                    text=chunk.text,
                    symbol=chunk.symbol,
                    stage="rerank",
                    rank=rank,
                    reason="reranked",
                    tokens=chunk.tokens,
                )
            )
        return results