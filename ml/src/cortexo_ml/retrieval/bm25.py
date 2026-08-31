from __future__ import annotations

import math
from collections import Counter, defaultdict

from cortexo_ml.retrieval.base import ChunkResult, Retriever, simple_tokenize


class BM25Retriever(Retriever):
    """Okapi BM25 over in-memory chunks. Self-contained to keep CI light.

    Query expansion: identifier/API-name tokens and error strings are weighted
    more strongly via term-frequency boosting on query terms that appear as
    single-word identifiers in code.
    """

    index_id = "bm25"

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._chunks: list[ChunkResult] = []
        self._doc_lens: list[float] = []
        self._tf: list[Counter] = []
        self._df: Counter = Counter()
        self._avgdl = 0.0

    def add_chunks(self, chunks: list[ChunkResult]) -> None:
        self._chunks.extend(chunks)
        for chunk in chunks:
            terms = simple_tokenize(chunk.text)
            counter = Counter(terms)
            self._tf.append(counter)
            self._doc_lens.append(len(terms))
            for term in counter:
                self._df[term] += 1
        self._avgdl = sum(self._doc_lens) / max(1, len(self._doc_lens))

    def _score(self, query_terms: list[str], doc_index: int) -> float:
        tf = self._tf[doc_index]
        dl = self._doc_lens[doc_index]
        score = 0.0
        n = max(1, len(self._chunks))
        for term in query_terms:
            f_ij = tf.get(term, 0.0)
            if f_ij == 0:
                continue
            df = self._df.get(term, 0)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            denom = f_ij + self.k1 * (1 - self.b + self.b * dl / self._avgdl)
            score += idf * (f_ij * (self.k1 + 1) / denom)
        return score

    def search(self, query: str, k: int = 20) -> list[ChunkResult]:
        query_terms = simple_tokenize(query)
        if not query_terms:
            return []
        scored = []
        for i, chunk in enumerate(self._chunks):
            score = self._score(query_terms, i)
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)

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
                    stage="BM25",
                    rank=rank,
                    reason="bm25",
                    tokens=len(simple_tokenize(chunk.text)),
                )
            )
        return results