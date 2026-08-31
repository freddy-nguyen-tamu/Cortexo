from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ChunkResult:
    chunk_id: str
    path: str
    score: float
    text: str
    symbol: str | None = None
    stage: str | None = None
    rank: int | None = None
    reason: str = ""
    tokens: int = 0
    included: bool = True
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalContext:
    query: str
    strategy: str
    maxTokens: int
    usedTokens: int
    chunks: list[ChunkResult]
    trace: list[dict] = field(default_factory=list)

    def to_record(self) -> dict:
        return {
            "query": self.query,
            "strategy": self.strategy,
            "maxTokens": self.maxTokens,
            "usedTokens": self.usedTokens,
            "chunks": [
                {
                    "chunkId": c.chunk_id,
                    "path": c.path,
                    "rank": c.rank,
                    "score": round(c.score, 4),
                    "stage": c.stage,
                    "reason": c.reason,
                    "tokens": c.tokens,
                    "included": c.included,
                }
                for c in self.chunks
            ],
            "trace": self.trace,
        }


class Retriever(ABC):
    index_id: str = "base"

    @abstractmethod
    def search(self, query: str, k: int = 20) -> list[ChunkResult]:
        ...


def simple_tokenize(text: str) -> list[str]:
    import re

    return [t for t in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(t) > 1]


def approx_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))