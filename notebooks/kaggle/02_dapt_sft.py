# Kaggle notebook 02 - DAPT + SFT + LoRA / QLoRA on Qwen2.5-Coder-0.5B.
# Uses the ml post_training package (transformers + PEFT when installed).

# %% [markdown]
# # Cortexo DAPT / SFT / LoRA / QLoRA (Kaggle)
# Recipe: continued pretraining on code-v1 -> SFT repair instructions ->
# optionally QLoRA 4-bit if VRAM is tight.

# %% [code]
import os, sys, json
sys.path.insert(0, "/kaggle/working/Cortexo/ml/src")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTTrainer  # optional; we implement a Trainer wrapper below

from cortexo_ml.post_training.sft import format_instruction_record, count_trainable
from cortexo_ml.training.checkpoints import seed_everything
from cortexo_ml.observability.experiment_tracker import ExperimentTracker

seed_everything(42)
MODEL_ID = "Qwen/Qwen2.5-Coder-0.5B"
tracker = ExperimentTracker(run_id="qwen05b-dapt-codev1", root="/kaggle/working/artifacts")

# %% [code]
# Tokenizer + base model. Qwen2.5-Coder-0.5B is Apache-2.0.
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
print("trainable before:", count_trainable(model))

# %% [code]
# QLoRA-ready: reload in 4-bit if VRAM < 16 GB.
if torch.cuda.get_device_properties(0).total_memory / 1e9 < 15:
    del model
    torch.cuda.empty_cache()
    from cortexo_ml.post_training.sft import apply_quantization_load, build_peft_config
    model = apply_quantization_load(
        MODEL_ID, quantized=True, peft_config=build_peft_config("lora", r=16)
    )
    print("loaded in 4-bit (QLoRA)")

# %% [code]
# Example instruction records from the synthetic repair corpus / PolyDB-SWE
# fixtures. format_instruction_record applies the canonical chat template.
records = [
    {
        "instruction": "Fix the off-by-one in chunk so trailing elements are kept.",
        "bad_code": "def chunk(items, size):\n    out = []\n    for i in range(0, len(items), size):\n        out.append(items[i:i + size])\n    return out[:size]",
        "tests": "assert chunk([1,2,3,4,5],2) == [[1,2],[3,4],[5]]",
        "target_patch": "return out",
    },
]
prompt = format_instruction_record(records[0])
print(prompt[:400])

# TODO(user): load the tokenized SFT dataset (JSONL of instruction records).
# Write a Trainer loop like notebook 01 but with model.save_pretrained()
# checkpoints + adapter saving, then here:
#   from peft import LoraConfig, get_peft_model
#   peft_config = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj","k_proj","v_proj","o_proj"])
#   model = get_peft_model(model, peft_config)

# %% [markdown]
# Registry handoff: after training, save adapter + base + metrics into the
# tracker's run dir and register `qwen05b-dapt-codev1` and
# `qwen05b-lora-r16-swev1` in MongoDB `models` with parentModelId lineage.