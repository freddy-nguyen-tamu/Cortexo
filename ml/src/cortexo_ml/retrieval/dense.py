from __future__ import annotations

import hashlib
import math

from cortexo_ml.retrieval.base import ChunkResult, Retriever, simple_tokenize


def _hash_embed(text: str, dim: int = 256) -> list[float]:
    vec = [0.0] * dim
    for token in simple_tokenize(text):
        digest = hashlib.md5(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if (digest[0] & 1) else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class DenseRetriever(Retriever):
    """Dense semantic retriever.

    Uses sentence-transformers when installed; otherwise falls back to a
    deterministic hashing bag-of-tokens projector so the pipeline stays runnable
    on dependency-light CI and CPU-only machines (documented as a weak baseline).
    """

    index_id = "dense"

    def __init__(self, model_name: str | None = None, dim: int = 256):
        self.model_name = model_name
        self.dim = dim
        self._chunks: list[ChunkResult] = []
        self._model = None
        self._vectors: list[list[float]] = []

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name or "BAAI/bge-small-en-v1.5")
        except ImportError:
            self._model = None

    def _embed(self, text: str) -> list[float]:
        self._load_model()
        if self._model is not None:
            return self._model.encode([text], normalize_embeddings=True)[0].tolist()
        return _hash_embed(text, self.dim)

    def add_chunks(self, chunks: list[ChunkResult]) -> None:
        self._chunks.extend(chunks)
        for chunk in chunks:
            self._vectors.append(self._embed(chunk.text))

    def search(self, query: str, k: int = 20) -> list[ChunkResult]:
        q = self._embed(query)
        scored = [
            (sum(a * b for a, b in zip(q, vec)), i)
            for i, vec in enumerate(self._vectors)
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for rank, (score, i) in enumerate(scored[:k], start=1):
            chunk = self._chunks[i]
            results.append(
                ChunkResult(
                    chunk_id=chunk.chunk_id,
                    path=chunk.path,
                    score=float(score),
                    text=chunk.text,
                    symbol=chunk.symbol,
                    stage="dense",
                    rank=rank,
                    reason="dense",
                    tokens=len(simple_tokenize(chunk.text)),
                )
            )
        return results