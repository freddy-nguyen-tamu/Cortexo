# Kaggle notebook 03 - DPO on repair preferences derived from tests.
# Tests create automatic preference labels (research question #12).

# %% [markdown]
# # Cortexo DPO (Kaggle)
# Given a repair problem, generation A and generation B, pick the winner using
# deterministic verifier rules (all tests pass > compiles > fewer new failures >
# fewer security findings > smaller patch), then create a preference pair.

# %% [code]
import os, sys, json
sys.path.insert(0, "/kaggle/working/Cortexo/ml/src")

from cortexo_ml.post_training.dpo import (
    build_preferences_from_results,
    validate_preference_record,
    train_dpo,
)

# %% [code]
# Each dict mirrors the evaluation/results record from the Runner:
#   {result_index, passed_tests, total_tests, compiled, new_failures,
#    security_findings, patch_size, unnecessary_edits, metadata}
results = [
    {"passed_tests": 3, "total_tests": 3, "compiled": True, "new_failures": 0,
     "security_findings": 0, "patch_size": 4, "unnecessary_edits": 0},
    {"passed_tests": 0, "total_tests": 3, "compiled": True, "new_failures": 2,
     "security_findings": 1, "patch_size": 60, "unnecessary_edits": 5},
]

prefs = build_preferences_from_results([results])
print("preference pairs built:", len(prefs))
for pair in prefs[:1]:
    print(json.dumps(pair, indent=2)[:400])

# TODO(user): point at JSONL of generated repairs from a scratch Qwen run and
# train via train_dpo(model, tokenizer, dataset, ...) writing the adapter to
# artifacts/qwen05b-lora-r16-swev1 into the experiment tracker.

# %% [markdown]
# Registry handoff: register `qwen05b-lora-r16-swev1` with
# parentModelId = qwen05b-dapt-codev1 and DPO metrics in the run record.