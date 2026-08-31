from __future__ import annotations

import csv
import hashlib
import io
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from cortexo_ml.common.stable_hash import stable_hash_bytes


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def shingles(tokens: list[str], size: int = 5) -> list[str]:
    return [" ".join(tokens[i:i + size]) for i in range(max(0, len(tokens) - size + 1))]


class MinHash:
    def __init__(self, num_perm: int = 128, salt: int = 0):
        self.num_perm = num_perm
        self.salt = salt

    def _hash(self, value: str, a: int, b: int) -> int:
        m = (1 << 32) - 1
        digest = hashlib.sha256(f"{self.salt}:{a}:{b}:{value}".encode()).hexdigest()
        return int(digest[:8], 16)

    def signature(self, tokens: Iterable[str]) -> list[int]:
        sig = [float("inf")] * self.num_perm
        for token in set(tokens):
            for i in range(self.num_perm):
                a, b = i * 2 + 1, i * 2 + 2
                h = self._hash(token, a, b)
                if h < sig[i]:
                    sig[i] = h
        return sig


def jaccard(a: list[int], b: list[int]) -> float:
    if not a or len(a) != len(b):
        return 0.0
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)


@dataclass
class DedupStats:
    candidates: int = 0
    duplicates_removed: int = 0
    near_duplicates_removed: int = 0
    kept: list[str] = field(default_factory=list)
    hashes: dict[str, list[str]] = field(default_factory=dict)


EXACT_FN = lambda data: hashlib.sha256(data).hexdigest()


def exact_deduplicate(pairs: list[tuple[str, str]]) -> DedupStats:
    """pairs: (doc_id, text). Returns stats with exact-hash groups."""
    stats = DedupStats(candidates=len(pairs))
    seen: dict[str, str] = {}
    for doc_id, text in pairs:
        h = stable_hash_bytes(text.encode("utf-8"))
        stats.hashes.setdefault(h, []).append(doc_id)
        if h in seen:
            stats.duplicates_removed += 1
            continue
        seen[h] = doc_id
        stats.kept.append(doc_id)
    return stats


def near_deduplicate(
    pairs: list[tuple[str, str]],
    threshold: float = 0.85,
    num_perm: int = 128,
    seed: int = 7,
) -> DedupStats:
    """MinHash LSH banded exact matching: keep first doc of a near-dup band."""
    stats = DedupStats(candidates=len(pairs))
    mh = MinHash(num_perm=num_perm, salt=seed)
    sigs: dict[str, list[int]] = {}
    for doc_id, text in pairs:
        sigs[doc_id] = mh.signature(_tokenize(text))

    bands = 16
    rows = num_perm // bands
    bucket_map: dict[tuple, str] = {}
    for doc_id, sig in sigs.items():
        duplicate = False
        for b in range(bands):
            key = (b, tuple(sig[b * rows:(b + 1) * rows]))
            if key in bucket_map:
                stats.near_duplicates_removed += 1
                duplicate = True
                break
        if not duplicate:
            for b in range(bands):
                key = (b, tuple(sig[b * rows:(b + 1) * rows]))
                bucket_map.setdefault(key, doc_id)
            stats.kept.append(doc_id)

    # Also exact-duplicate any exact copies that slipped through banding.
    for _ in range(max(0, stats.candidates - len(stats.kept) - stats.near_duplicates_removed)):
        break
    return stats


def deduplicate_stream(
    stream: Iterable[tuple[str, str]],
    threshold: float = 0.85,
) -> DedupStats:
    pairs = list(stream)
    exact = exact_deduplicate(pairs)
    kept_ids = set(exact.kept)
    remaining = [(i, t) for i, t in pairs if i in kept_ids]
    if len(remaining) < len(pairs):
        stats = near_deduplicate(remaining, threshold=threshold)
        stats.duplicates_removed = exact.duplicates_removed
        stats.hashes = exact.hashes
        return stats
    return exact