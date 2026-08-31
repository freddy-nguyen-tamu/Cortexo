"""Post-training: SFT / LoRA / QLoRA / IA3 and DPO / ORPO preference optimization."""

from cortexo_ml.post_training.sft import build_peft_config, train_sft, format_instruction_record, comparison_row
from cortexo_ml.post_training.dpo import build_preferences_from_results, train_dpo, reward_from_verifier

__all__ = [
    "build_peft_config",
    "train_sft",
    "format_instruction_record",
    "comparison_row",
    "build_preferences_from_results",
    "train_dpo",
    "reward_from_verifier",
]