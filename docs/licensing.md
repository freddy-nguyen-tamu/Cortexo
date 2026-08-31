# Cortexo licensing policy

Cortexo never states "all GitHub code is free for model training." Every model
and every dataset used for training must have its license resolved and
recorded before ingestion.

## Dataset checklist (per dataset)

- [ ] source (URL, origin)
- [ ] license
- [ ] training permitted?
- [ ] redistribution permitted?
- [ ] derived-dataset publication permitted?
- [ ] applies to all files/splits?
- [ ] trainer of last resort (no hands-wave)

## Per public repo (for repository pretraining / ingestion)

- [ ] license
- [ ] exact commit SHA (recorded in the dataset manifest)
- [ ] training-use decision + who made it + date
- [ ] license headers in all files (or a license inventory)

## Per model

- [ ] exact model ID (e.g. `Qwen/Qwen2.5-Coder-0.5B`)
- [ ] exact checkpoint/commit hash
- [ ] license (e.g. Apache-2.0 for Qwen2.5-Coder)
- [ ] redistribution of weights permitted for the intended artifact path?
- [ ] derivative-model rules

## Dependency inventory

- [ ] license inventory for all Python/Java/JS dependencies used in the product
      (pyproject.toml + pip/poetry lock + Maven/Cargo audit)
- [ ] note any GPL-only dependency that would affect distribution

## Maintained manifests

- `datasets/manifests/sources.jsonl` – every registered source, per-source
  license + permission flags.
- `datasets/manifests/exclusions.json` – benchmark solutions, hidden tests and
  target patches are always excluded from training corpora (path rules).
- `datasets/processed/code-v1/dataset_card.json` – per-final-dataset card.

## Reference decisions

| Source / model | License | Training use |
|---|---|---|
| `cortexo-demo-code-v1` (own synthetic files) | Apache-2.0 | Yes (allowed, self-authored) |
| HumanEval | MIT (check snapshot terms) | Evaluation only; keep solutions out of training corpus |
| MBPP | CC-BY-4.0 (check snapshot) | Evaluation only unless current terms permit training |
| CodeSearchNet | Multiple permissive per language | Verify each sub-corpus |
| Qwen2.5-Coder-0.5B / 1.5B | Apache-2.0 | Yes with attribution + same model-card diligence |
| BAAI/bge-small-en-v1.5 | MIT | Yes, attribution |
| StarCoder2 | BigCode OpenRAIL-M (per checkpoint) | Check each specific checkpoint card before use |

## Redistribution

Deploying a fine-tuned model requires checking the base model's redistribution
terms and any dataset-derived license obligations, not just the training-use
permission.

## Final principle

If the source's terms are unclear, do not include it. Finance-quality licensing
discipline is part of the research project, not an afterthought.