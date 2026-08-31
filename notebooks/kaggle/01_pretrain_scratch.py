# Kaggle notebook 01 - Pretrain a scratch code Transformer (resumable).
# GPU autodetect only - P100 retired 2026-09-15; do not hard-code an accelerator.
# Sizes micro-batch/grad-accum from VRAM, saves checkpoints frequently, and
# can resume from the latest checkpoint after a quota recycle.

# %% [markdown]
# # Cortexo scratch pretraining (Kaggle)
# 1. clone repo -> 2. mount the code-v1 corpus dataset -> 3. run train()

# %% [code]
import os
import sys

# !git clone -q https://github.com/your-org/Cortexo.git /kaggle/working/Cortexo
sys.path.insert(0, "/kaggle/working/Cortexo/ml/src")

import torch
from torch.utils.data import DataLoader

from cortexo_ml.scratch_model.config import TransformerConfig
from cortexo_ml.scratch_model.model import ScratchCodeLM
from cortexo_ml.training.dataset import build_datasets
from cortexo_ml.training.trainer import Trainer
from cortexo_ml.training import checkpoints

ARTIFACTS = "/kaggle/working/artifacts/scratch33m-code-v1"
os.makedirs(f"{ARTIFACTS}/checkpoints", exist_ok=True)

# %% [code]
n_gpu = torch.cuda.device_count()
for i in range(n_gpu):
    props = torch.cuda.get_device_properties(i)
    print(i, torch.cuda.get_device_name(i), round(props.total_memory / 1e9, 1), "GB")
vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9

# Use config.example.yml values; machine-specific flattens to a single run config.
cfg = TransformerConfig.from_dict({
    "vocab_size": 17000,
    "hidden_size": 768,
    "intermediate_size": 2048,
    "num_hidden_layers": 12,
    "num_attention_heads": 12,
    "max_position_embeddings": 1024,
    "dropout": 0.0,
})
cfg.vocab_size = 17000  # after you train the tokenizer, load tokenizer.vocab_size

model = ScratchCodeLM(cfg)
n_params = sum(p.numel() for p in model.parameters())
print("params:", n_params)

# %% [code]
# Mount your processed tokenized corpus as a Kaggle Dataset input.
TOKEN_PATH = "/kaggle/input/cortexo-corpus/code-v1/tokenized/train.bin"
train_ds, eval_ds = build_datasets(TOKEN_PATH, seq_len=cfg.max_position_embeddings)

train_dl = DataLoader(train_ds, batch_size=1, shuffle=False)
eval_dl = DataLoader(eval_ds, batch_size=1, shuffle=False)

# %% [code]
# Auto-size from VRAM (single-GPU and T4x2 multi-GPU both work).
if vram_gb >= 15:
    micro_batch = 2
else:
    micro_batch = 1
grad_accum = max(1, 32 // (micro_batch * max(n_gpu, 1)))
print(f"micro_batch={micro_batch} grad_accum={grad_accum} gpus={n_gpu}")

train_config = {
    "learning_rate": 2.5e-4,
    "min_learning_rate": 2.5e-5,
    "warmup_steps": 1000,
    "max_steps": 20000,
    "weight_decay": 0.1,
    "grad_clip": 1.0,
    "precision": "fp16",
    "micro_batch_size": micro_batch,
    "gradient_accumulation_steps": grad_accum,
    "save_every": 500,
    "eval_every": 250,
}

trainer = Trainer(
    model=model,
    train_dataloader=train_dl,
    eval_dataloader=eval_dl,
    train_config=train_config,
    model_config=cfg,
    telemetry_path=f"{ARTIFACTS}/metrics.jsonl",
    checkpoint_dir=f"{ARTIFACTS}/checkpoints",
    tokenizer_id="code-bpe-16k",
)

# %% [code]
# Resume from the latest Kaggle-output checkpoint if present.
ckpt = checkpoints.resume_from_checkpoint(
    f"{ARTIFACTS}/checkpoints/latest.pt", trainer.model, trainer.optimizer
) if os.path.exists(f"{ARTIFACTS}/checkpoints/latest.pt") else None
start_step = ckpt["step"] + 1 if ckpt else 0
if ckpt:
    print("resumed at step", start_step)

# Full run. Quota-safe: every save_every steps a checkpoint is written and
# the telemetry file can be replayed into the TrainingCurveVisualizer.
trainer.run(
    max_steps=train_config["max_steps"],
    eval_every=train_config["eval_every"],
    save_every=train_config["save_every"],
    start_step=start_step,
)

checkpoints.save_checkpoint(
    f"{ARTIFACTS}/checkpoints/final.pt", trainer.model, trainer.optimizer,
    trainer.global_step, trainer.tc, trainer.dataset_position, trainer.tokenizer_id,
)

# %% [markdown]
# ## Post-run
# - Upload `artifacts/scratch33m-code-v1/*` (config.json, metrics.jsonl,
#   checkpoints) -> Kaggle Dataset.
# - Register the model in Cortexo (MongoDB `models`) with artifact Sha256 and
#   the `training_curve_series` payload so the TrainingCurveVisualizer ingests.