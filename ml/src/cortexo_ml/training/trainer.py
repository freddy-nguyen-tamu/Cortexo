import time

import psutil
import torch
from torch import nn
from torch.utils.data import DataLoader

from cortexo_ml.training.schedules import cosine_lr
from cortexo_ml.training.telemetry import TelemetryWriter
from cortexo_ml.training import checkpoints


class Trainer:
    """Custom training loop: AdamW, warmup + cosine decay, mixed precision,
    gradient accumulation, gradient clipping, checkpointing and JSONL telemetry.
    """

    def __init__(
        self,
        model: nn.Module,
        train_dataloader,
        eval_dataloader,
        train_config: dict,
        model_config,
        telemetry_path,
        checkpoint_dir,
        device=None,
        tokenizer_id=None,
    ):
        self.model = model
        self.train_dl = train_dataloader
        self.eval_dl = eval_dataloader
        self.tc = train_config
        self.mc = model_config
        self.telemetry = TelemetryWriter(telemetry_path)
        self.checkpoint_dir = checkpoint_dir
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer_id = tokenizer_id

        self.model.to(self.device)

        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.tc["learning_rate"],
            weight_decay=self.tc.get("weight_decay", 0.1),
            betas=(0.9, 0.95),
        )

        precision = self.tc.get("precision", "fp16")
        self.scaler = torch.amp.GradScaler(enabled=precision == "fp16")
        self.precision = precision

        self.global_step = 0
        self.dataset_position = 0

    def build_lr(self, step):
        return cosine_lr(
            step,
            self.tc.get("warmup_steps", 1000),
            self.tc.get("max_steps", 20000),
            self.tc.get("learning_rate", 0.00025),
            self.tc.get("min_learning_rate", self.tc.get("learning_rate", 0.00025) / 10),
        )

    def peak_ram_mb(self):
        return psutil.Process().memory_info().rss / (1024 * 1024)

    def peak_vram_mb(self):
        if not torch.cuda.is_available():
            return 0.0
        return torch.cuda.max_memory_allocated() / (1024 * 1024)

    def train_step(self, batch):
        input_ids = batch["input_ids"].to(self.device)
        labels = batch["labels"].to(self.device)

        micro_batch_size = self.tc.get("micro_batch_size", 2)
        accumulation = self.tc.get("gradient_accumulation_steps", 1)
        clip = self.tc.get("grad_clip", 1.0)

        total_loss = 0.0

        for start in range(0, input_ids.size(0), micro_batch_size):
            chunk_ids = input_ids[start:start + micro_batch_size]
            chunk_labels = labels[start:start + micro_batch_size]

            autocast = {
                "fp16": torch.float16,
                "bf16": torch.bfloat16,
            }.get(self.precision, torch.float32)

            with torch.amp.autocast(self.device.type, dtype=autocast, enabled=self.precision != "fp32"):
                outputs = self.model(chunk_ids, labels=chunk_labels)
                loss = outputs["loss"] / accumulation

            self.scaler.scale(loss).backward()
            total_loss += loss.item()

        if self.precision == "fp32":
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), clip)
            self.optimizer.step()
        else:
            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), clip)
            self.scaler.step(self.optimizer)
            self.scaler.update()

        self.optimizer.zero_grad(set_to_none=True)
        return total_loss

    def evaluate(self):
        self.model.eval()
        losses = []
        with torch.no_grad():
            for batch in self.eval_dl:
                input_ids = batch["input_ids"].to(self.device)
                labels = batch["labels"].to(self.device)
                with torch.amp.autocast(
                    self.device.type,
                    dtype=torch.float16,
                    enabled=self.precision != "fp32",
                ):
                    outputs = self.model(input_ids, labels=labels)
                if outputs["loss"] is not None:
                    losses.append(outputs["loss"].item())
        self.model.train()
        if not losses:
            return None
        return sum(losses) / len(losses)

    def run(self, max_steps, eval_every=250, save_every=500, start_step=0):
        run_start = time.time()
        first_batch = True

        for epoch in range(1_000_000):
            for batch in self.train_dl:
                if self.global_step < start_step:
                    self.global_step += 1
                    continue

                if first_batch:
                    self.optimizer.zero_grad()
                    first_batch = False

                step_start = time.time()
                tokens = batch["input_ids"].numel()
                loss = self.train_step(batch)
                self.global_step += 1
                self.dataset_position += tokens

                lr = self.build_lr(self.global_step)
                for group in self.optimizer.param_groups:
                    group["lr"] = lr

                val_loss = None
                perplexity = None
                if eval_every and self.global_step % eval_every == 0:
                    val_loss = self.evaluate()
                    if val_loss is not None:
                        perplexity = 2.0 ** val_loss

                self.telemetry.write({
                    "step": self.global_step,
                    "loss": loss,
                    "validation_loss": val_loss,
                    "perplexity": perplexity,
                    "learning_rate": lr,
                    "grad_norm": None,
                    "tokens_per_second": tokens / max(1e-9, time.time() - step_start),
                    "samples_per_second": 1.0 / max(1e-9, time.time() - step_start),
                    "peak_ram_mb": round(self.peak_ram_mb(), 1),
                    "peak_vram_mb": round(self.peak_vram_mb(), 0),
                    "elapsed_seconds": round(time.time() - run_start, 2),
                })

                if save_every and self.global_step % save_every == 0:
                    path = f"{self.checkpoint_dir}/step-{self.global_step}.pt"
                    checkpoints.save_checkpoint(
                        path,
                        self.model,
                        self.optimizer,
                        self.global_step,
                        self.tc,
                        self.dataset_position,
                        self.tokenizer_id,
                    )

                if self.global_step >= max_steps:
                    return self.global_step

            if self.global_step >= max_steps:
                return self.global_step

        return self.global_step

    def grad_norm(self):
        total = 0.0
        for p in self.model.parameters():
            if p.grad is not None:
                total += p.grad.detach().float().pow(2).sum().item()
        return total ** 0.5