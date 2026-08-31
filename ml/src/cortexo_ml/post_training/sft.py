from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

INSTRUCTION_TEMPLATE = (
    "{system}\n\n{context}\n\n### Instruction\n{instruction}\n\n### Response\n{response}"
)


def format_instruction_record(record: dict) -> str:
    return INSTRUCTION_TEMPLATE.format(
        system=record.get("system", ""),
        context=record.get("context", ""),
        instruction=record.get("instruction", ""),
        response=record.get("response", ""),
    ).strip()


DEFINITIVE_RECORD_FIELDS = {"system", "instruction", "context", "response", "metadata"}


def validate_instruction_record(record: dict) -> tuple[bool, str]:
    for key in ("instruction", "response"):
        if not record.get(key):
            return False, f"missing {key}"
    if record.get("metadata") is not None and not isinstance(record["metadata"], dict):
        return False, "metadata must be object"
    if record.get("metadata") and record["metadata"].get("task_type") is None:
        return False, "metadata.task_type recommended"
    return True, "ok"


def build_peft_config(method: str = "lora", r: int = 8, alpha: int = 16, dropout: float = 0.05):
    """Build a PEFT LoraConfig/IA3Config without forcing heavy imports at module load."""
    try:
        from peft import LoraConfig, IA3Config, TaskType
    except ImportError as exc:  # pragma: no cover - optional heavy dep
        raise RuntimeError("peft is required for this path: pip install peft") from exc

    if method in {"lora", "qlora"}:
        return LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=r,
            lora_alpha=alpha,
            lora_dropout=dropout,
            bias="none",
        )
    if method == "ia3":
        return IA3Config(task_type=TaskType.CAUSAL_LM, r=r, target_modules=None, feedforward_modules=None)
    raise ValueError(f"unknown PEFT method: {method}")


def apply_quantization_load(base_model_id: str, quantized: bool, peft_config, device_map="auto"):
    """Load a base model quantized (bitsandbytes 4-bit) for QLoRA, else regular."""
    import torch
    from transformers import AutoModelForCausalLM

    kwargs: dict[str, Any] = {"device_map": device_map}
    if quantized:
        kwargs["load_in_4bit"] = True
        kwargs["quantization_config"] = _bitsandbytes_config()
    model = AutoModelForCausalLM.from_pretrained(base_model_id, **kwargs)
    try:
        from peft import get_peft_model

        return get_peft_model(model, peft_config)
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("peft required") from exc


def _bitsandbytes_config(_=None):
    try:
        from transformers import BitsAndBytesConfig
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("transformers required") from exc
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype="float16",
    )


@dataclass
class SFTResult:
    method: str
    trainable_params: int
    total_params: int
    adapter_mb: float
    peak_vram_mb: float
    training_seconds: float
    val_loss: float | None = None
    checkpoint_dir: str | None = None


def count_trainable(model) -> tuple[int, int]:
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    return int(trainable), int(total)


def estimate_qlora_memory_mb(base_params_mb: float, r: int = 16, layers: int = 0) -> float:
    return base_params_mb * 0.55 + 200  # rough 4-bit + adapter + one forward batch overhead


def train_sft(
    train_records: list[dict],
    base_model_id: str,
    method: str = "lora",
    r: int = 8,
    output_dir: str = "artifacts/models",
    max_steps: int = 500,
    learning_rate: float = 2e-4,
    batch_size: int = 4,
    seed: int = 42,
) -> SFTResult:
    """Run a small SFT/LoRA/QLoRA/IA3 experiment end-to-end.

    Requires torch + transformers + peft. Kept out of the import benchmark of the
    package so lightweight CI can still import the modules.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, DataCollatorForLanguageModeling
    from transformers import TrainingArguments, Trainer

    quantized = method == "qlora"
    peft_config = build_peft_config(method="lora" if quantized else method, r=r if method != "ia3" else 8)
    model = apply_quantization_load(base_model_id, quantized, peft_config)
    tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def _tokenize(record: dict):
        text = format_instruction_record(record)
        return tokenizer(text, truncation=True, max_length=2048, padding="max_length")

    encoded = [_tokenize(r) for r in train_records]
    dataset = _simple_dataset(encoded, tokenizer)

    out = Path(output_dir) / f"{method}-r{r}"
    out.mkdir(parents=True, exist_ok=True)

    args = TrainingArguments(
        output_dir=str(out),
        max_steps=max_steps,
        per_device_train_batch_size=batch_size,
        learning_rate=learning_rate,
        seed=seed,
        save_strategy="steps",
        save_steps=max(1, max_steps // 5),
        fp16=torch.cuda.is_available(),
        report_to=[],
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )

    start = time.time()
    trainer.train()
    elapsed = time.time() - start
    model.save_pretrained(str(out))
    tokenizer.save_pretrained(str(out))

    trainable, total = count_trainable(model)
    adapter_fp = list(out.glob("adapter_model.safetensors"))
    adapter_mb = adapter_fp[0].stat().st_size / 1e6 if adapter_fp else 0.0
    peak = _peak_vram_mb()
    return SFTResult(
        method=method,
        trainable_params=trainable,
        total_params=total,
        adapter_mb=adapter_mb,
        peak_vram_mb=peak,
        training_seconds=elapsed,
        checkpoint_dir=str(out),
    )


def _simple_dataset(entries, tokenizer):
    import torch
    from torch.utils.data import Dataset

    class _DS(Dataset):
        def __len__(self):
            return len(entries)

        def __getitem__(self, idx):
            e = entries[idx]
            return {
                "input_ids": torch.as_tensor(e["input_ids"]),
                "attention_mask": torch.as_tensor(e.get("attention_mask", e["input_ids"].clone().fill_(1))),
                "labels": torch.as_tensor(e["input_ids"]),
            }

    return _DS()


def _peak_vram_mb() -> float:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / (1024 * 1024)
    except ImportError:
        pass
    return 0.0


def comparison_row(result: SFTResult) -> dict:
    return {
        "method": result.method,
        "trainable_params": result.trainable_params,
        "total_params": result.total_params,
        "adapter_mb": round(result.adapter_mb, 2),
        "peak_vram_mb": round(result.peak_vram_mb, 2),
        "training_seconds": round(result.training_seconds, 1),
    }