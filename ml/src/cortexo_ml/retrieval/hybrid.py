from __future__ import annotations

from cortexo_ml.retrieval.base import ChunkResult


def reciprocal_rank_fusion(
    lists: list[list[ChunkResult]],
    k: int = 60,
) -> list[ChunkResult]:
    """Reciprocal Rank Fusion over multiple ranked lists.

    score = sum over lists of 1/(k + rank).
    """
    scores: dict[str, dict] = {}
    for ranked in lists:
        for rank, chunk in enumerate(ranked, start=1):
            slot = scores.setdefault(chunk.chunk_id, {"chunk": chunk, "score": 0.0, "min_rank": rank})
            slot["score"] += 1.0 / (k + rank)
            slot["min_rank"] = min(slot["min_rank"], rank)

    fused = sorted(
        (v["chunk"] for v in scores.values()),
        key=lambda c: -scores[c.chunk_id]["score"],
    )
    results = []
    for rank, chunk in enumerate(fused, start=1):
        slot = scores[chunk.chunk_id]
        results.append(
            ChunkResult(
                chunk_id=chunk.chunk_id,
                path=chunk.path,
                score=float(slot["score"]),
                text=chunk.text,
                symbol=chunk.symbol,
                stage="RRF",
                rank=rank,
                reason=f"rrf(min_rank={slot['min_rank']})",
                tokens=chunk.tokens,
            )
        )
    return results


def fusion_trace(list_names: list[str], lists: list[list[ChunkResult]], k: int = 60) -> dict:
    stage_trace = []
    for name, ranked in zip(list_names, lists):
        stage_trace.append(
            {
                "stage": name,
                "candidates": [
                    {"chunkId": c.chunk_id, "path": c.path, "rank": c.rank, "score": round(c.score, 4)}
                    for c in ranked
                ],
            }
        )
    fused = reciprocal_rank_fusion(lists, k=k)
    stage_trace.append(
        {
            "stage": "RRF",
            "candidates": [
                {"chunkId": c.chunk_id, "path": c.path, "rank": c.rank, "score": round(c.score, 4)}
                for c in fused
            ],
        }
    )
    return {"stages": stage_trace}