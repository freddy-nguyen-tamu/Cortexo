import hashlib
import io
import os
import zlib
from pathlib import Path


def stable_hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def stable_hash_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def stable_hash_dict(obj: object) -> str:
    encoded = _canonical_bytes(obj)
    return hashlib.sha256(encoded).hexdigest()


def _canonical_bytes(obj: object) -> bytes:
    if obj is None:
        return b"null"
    if isinstance(obj, bool):
        return b"true" if obj else b"false"
    if isinstance(obj, int):
        return str(obj).encode()
    if isinstance(obj, float):
        return repr(obj).encode()
    if isinstance(obj, str):
        return obj.encode("utf-8")
    if isinstance(obj, (list, tuple)):
        parts = [b"["]
        for i, item in enumerate(obj):
            if i:
                parts.append(b",")
            parts.append(_canonical_bytes(item))
        parts.append(b"]")
        return b"".join(parts)
    if isinstance(obj, dict):
        parts = [b"{"]
        for i, key in enumerate(sorted(obj, key=lambda k: str(k))):
            if i:
                parts.append(b",")
            parts.append(_canonical_bytes(key))
            parts.append(b":")
            parts.append(_canonical_bytes(obj[key]))
        parts.append(b"}")
        return b"".join(parts)
    if isinstance(obj, (bytes, bytearray)):
        return b"base64:" + __import__("base64").b64encode(bytes(obj))
    return _canonical_bytes(repr(obj))


def short_hash(payload: object, length: int = 12) -> str:
    return stable_hash_dict(payload)[:length]


def gzip_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def crc32(path: str | Path) -> int:
    value = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            value = zlib.crc32(chunk, value)
    return value


def memmap_token_hash(token_path: str | Path) -> str:
    import numpy as np

    arr = np.lib.format.open_memmap(str(token_path), mode="r", dtype=np.uint16)
    hasher = hashlib.sha256()
    block = arr.view(np.uint8)
    step = 1 << 20
    for start in range(0, block.size, step):
        hasher.update(np.ascontiguousarray(block[start:start + step]))
    return hasher.hexdigest()