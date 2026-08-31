import random
import time

import torch
from pathlib import Path


def save_checkpoint(
    path: Path,
    model,
    optimizer,
    step: int,
    config,
    dataset_position: int,
    tokenizer_id: str | None = None,
):
    """Checkpoint structure mirrors the blueprint contract:

    model state_dict, optimizer state_dict, step, config, RNG states,
    dataset_position.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = torch.get_rng_state()
    rng_cuda = torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None

    checkpoint = {
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict() if optimizer is not None else None,
        "step": step,
        "config": config,
        "rng": rng,
        "rng_cuda": rng_cuda,
        "dataset_position": dataset_position,
        "tokenizer_id": tokenizer_id,
        "saved_at_unix": time.time(),
    }
    torch.save(checkpoint, path)
    return path


def load_checkpoint(path: Path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"checkpoint not found: {path}")
    return torch.load(path, map_location="cpu", weights_only=False)


def resume_from_checkpoint(
    path: Path,
    model,
    optimizer,
):
    checkpoint = load_checkpoint(path)
    model.load_state_dict(checkpoint["model"])
    if optimizer is not None and checkpoint.get("optimizer") is not None:
        optimizer.load_state_dict(checkpoint["optimizer"])
    torch.set_rng_state(checkpoint["rng"])
    if checkpoint.get("rng_cuda") and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(checkpoint["rng_cuda"])
    return checkpoint


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)