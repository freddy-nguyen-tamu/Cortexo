import json
from pathlib import Path


class TelemetryWriter:
    """Append-only JSONL record for a training run.

    Every line contains: step, loss, validation_loss, perplexity, learning_rate,
    grad_norm, tokens_per_second, samples_per_second, peak_ram_mb, peak_vram_mb,
    elapsed_seconds.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict) -> None:
        with self.path.open("a") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    @staticmethod
    def standard_fields() -> list[str]:
        return [
            "step",
            "loss",
            "validation_loss",
            "perplexity",
            "learning_rate",
            "grad_norm",
            "tokens_per_second",
            "samples_per_second",
            "peak_ram_mb",
            "peak_vram_mb",
            "elapsed_seconds",
        ]