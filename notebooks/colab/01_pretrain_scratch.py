# Colab notebook 01 - Resume-safe scratch pretraining (free Colab).
# Colab free: resources not guaranteed, GPU types vary, ~12h max runtime.
# Therefore: checkpoint frequently + resume + never depend on a specific GPU.

# %% [markdown]
# # Cortexo scratch pretraining (Colab Free)
# Same Trainer as Kaggle but tuned for Colab: smaller micro-batch, saves every
# 250 steps, resumes from Drive, and prints a live training-curve JSONL.

# %% [code]
import os, sys

# !pip install -q --upgrade pip
# !git clone -q https://github.com/your-org/Cortexo.git /content/Cortexo
sys.path.insert(0, "/content/Cortexo/ml/src")

import torch
from torch.utils.data import DataLoader

from cortexo_ml.scratch_model.config import TransformerConfig
from cortexo_ml.scratch_model.model import ScratchCodeLM
from cortexo_ml.training.dataset import build_datasets
from cortexo_ml.training.trainer import Trainer
from cortexo_ml.training import checkpoints
from cortexo_ml.training.checkpoints import seed_everything

seed_everything(42)

# %% [code]
# Mount Drive so checkpoints survive session restarts.
from google.colab import drive
drive.mount("/content/drive")

ARTIFACTS = "/content/drive/MyDrive/cortexo/artifacts/scratch33m-code-v1"
CHECKPOINTS = f"{ARTIFACTS}/checkpoints"
os.makedirs(CHECKPOINTS, exist_ok=True)

# %% [code]
# GPU-agnostic sizing: T4 = 16 GB, smaller GPUs use micro-batch 1.
gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else 0.0
print("gpu:", gpu_name, round(vram_gb, 1), "GB")

micro_batch = 2 if vram_gb >= 15 else 1
grad_accum = max(1, 32 // micro_batch)

cfg = TransformerConfig(
    vocab_size=17000, hidden_size=768, intermediate_size=2048,
    num_hidden_layers=12, num_attention_heads=12,
    max_position_embeddings=1024, dropout=0.0,
)
model = ScratchCodeLM(cfg)
print("params:", sum(p.numel() for p in model.parameters()))

# %% [code]
TOKEN_PATH = "/content/drive/MyDrive/cortexo/data/code-v1/tokenized/train.bin"
train_ds, eval_ds = build_datasets(TOKEN_PATH, seq_len=cfg.max_position_embeddings)
train_dl = DataLoader(train_ds, batch_size=1, shuffle=False)
eval_dl = DataLoader(eval_ds, batch_size=1, shuffle=False)

trainer = Trainer(
    model=model,
    train_dataloader=train_dl,
    eval_dataloader=eval_dl,
    train_config={
        "learning_rate": 2.5e-4, "min_learning_rate": 2.5e-5,
        "warmup_steps": 500, "max_steps": 8000,           # ~<12h budget
        "weight_decay": 0.1, "grad_clip": 1.0, "precision": "fp16",
        "micro_batch_size": micro_batch,
        "gradient_accumulation_steps": grad_accum,
    },
    model_config=cfg,
    telemetry_path=f"{ARTIFACTS}/metrics.jsonl",
    checkpoint_dir=CHECKPOINTS,
    tokenizer_id="code-bpe-16k",
)

# %% [code]
# Resume from Drive if the session died mid-run.
ckpt = checkpoints.resume_from_checkpoint(
    f"{CHECKPOINTS}/latest.pt", trainer.model, trainer.optimizer
) if os.path.exists(f"{CHECKPOINTS}/latest.pt") else None
start_step = (ckpt["step"] + 1) if ckpt else 0
print("start_step:", start_step)

# Frequent saves every 250 steps: worst-case loss after a recycle is 250 steps.
trainer.run(max_steps=8000, eval_every=200, save_every=250, start_step=start_step)

# %% [markdown]
# After each save, also write `metrics.jsonl` to the Cortexo repo copy under
# `artifacts/evaluations/<run-id>/metrics.jsonl` so the TrainingCurveVisualizer
# can render it offline.