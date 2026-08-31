from __future__ import annotations

from pathlib import Path


def load_scratch_checkpoint(path: str | Path, safe: bool = True) -> dict:
    """Load a cortexo_ml training checkpoint using weights_only-first loading."""
    import torch

    checkpoint_path = Path(path)
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if payload.get("config") is None:
        # Older full-format checkpoint or pickled objects: fall back explicitly.
        payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

    from cortexo_ml.scratch_model.config import TransformerConfig
    from cortexo_ml.scratch_model.model import ScratchCodeLM

    config_data = payload["config"]
    cfg = TransformerConfig.from_dict(config_data)
    model = ScratchCodeLM(cfg)
    model.load_state_dict(payload["model"])

    tokenizer_path = payload.get("tokenizer_id")
    return {
        "model": model,
        "config": cfg,
        "step": payload.get("step"),
        "tokenizer_path": tokenizer_path,
        "checkpoint_path": str(checkpoint_path),
        "saved_at": payload.get("saved_at_unix"),
    }


def torch_safe_load_dict(path: str | Path) -> dict:
    import torch

    return torch.load(path, map_location="cpu", weights_only=True)


def sha256_of_file(path: str | Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()