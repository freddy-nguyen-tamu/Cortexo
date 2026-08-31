from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from cortexo_ml.common.stable_hash import stable_hash_bytes


@dataclass
class SplitResult:
    dataset_id: str
    version: str
    train: list[str]
    validation: list[str]
    test: list[str]
    split_hashes: dict[str, str] = field(default_factory=dict)

    def as_record(self) -> dict:
        return {
            "datasetId": self.dataset_id,
            "version": self.version,
            "splitHashes": self.split_hashes,
            "counts": {
                "train": len(self.train),
                "validation": len(self.validation),
                "test": len(self.test),
            },
        }


def deterministic_split(
    doc_ids: list[str],
    train_frac: float = 0.90,
    val_frac: float = 0.05,
    seed: int = 42,
    test_frac: float | None = None,
) -> tuple[list[str], list[str], list[str]]:
    if test_frac is None:
        test_frac = round(1.0 - train_frac - val_frac, 6)
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(doc_ids)).tolist()
    shuffled = [doc_ids[i] for i in order]

    n_train = int(len(shuffled) * train_frac)
    n_val = int(len(shuffled) * val_frac)
    train = shuffled[:n_train]
    val = shuffled[n_train:n_train + n_val]
    test = shuffled[n_train + n_val:]
    return train, val, test


def split_by_hash(
    doc_ids: list[str],
    train_seed: str = "train",
    val_seed: str = "val",
    test_seed: str = "test",
    splits: tuple[float, float] = (0.90, 0.05),
) -> tuple[list[str], list[str], list[str]]:
    """Content-addressed split: hash of the id+seed classifies the doc.

    Stable across re-runs and ordering changes.
    """
    train_frac, val_frac = splits
    train, val, test = [], [], []
    for doc_id in doc_ids:
        h = int(stable_hash_bytes(doc_id.encode("utf-8"))[:16], 16)
        bucket = h / (16 ** 16)
        if bucket < train_frac:
            train.append(doc_id)
        elif bucket < train_frac + val_frac:
            val.append(doc_id)
        else:
            test.append(doc_id)
    return train, val, test


def split_hashes(split: tuple[list[str], list[str], list[str]]) -> dict[str, str]:
    result = {}
    for name, docs in zip(("train", "validation", "test"), split):
        payload = "\n".join(sorted(docs)).encode("utf-8")
        result[name] = stable_hash_bytes(payload)
    return result


def write_split_manifest(dest: str | Path, result: SplitResult) -> Path:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "train.jsonl").write_text("\n".join(result.train) + "\n")
    (dest / "validation.jsonl").write_text("\n".join(result.validation) + "\n")
    (dest / "test.jsonl").write_text("\n".join(result.test) + "\n")
    (dest / "split.json").write_text(json.dumps(result.as_record(), indent=2))
    return dest / "split.json"


def split_token_shard(token_path: str | Path, train_frac: float = 0.9) -> tuple[str, str, str]:
    import os

    arr = np.lib.format.open_memmap(str(token_path), mode="r", dtype=np.uint16)
    n = len(arr)
    cut_train = int(n * train_frac)
    cut_val = int(n * (train_frac + (1 - train_frac) / 2))
    root = os.path.dirname(str(token_path))
    base = os.path.splitext(os.path.basename(str(token_path)))[0]

    train_path = os.path.join(root, f"{base}.train.npy")
    val_path = os.path.join(root, f"{base}.val.npy")
    test_path = os.path.join(root, f"{base}.test.npy")
    np.save(train_path, np.ascontiguousarray(arr[:cut_train]))
    np.save(val_path, np.ascontiguousarray(arr[cut_train:cut_val]))
    np.save(test_path, np.ascontiguousarray(arr[cut_val:]))
    return train_path, val_path, test_path