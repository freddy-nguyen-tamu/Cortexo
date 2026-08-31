from __future__ import annotations

from dataclasses import dataclass, field

PREFERENCE_RECORD_FIELDS = {"prompt", "chosen", "rejected", "metadata"}


def validate_preference_record(record: dict) -> tuple[bool, str]:
    for key in ("prompt", "chosen", "rejected"):
        if not record.get(key):
            return False, f"missing {key}"
    if not record.get("metadata"):
        return False, "metadata required"
    return True, "ok"


# Ranking rules from the blueprint (highest priority first).
RANKING_RULES = [
    ("all_tests_pass", lambda r: bool(r.get("chosen_tests_pass", False)) and not bool(r.get("rejected_tests_pass", True))),
    ("compiles", lambda r: r.get("chosen_compiles") and not r.get("rejected_compiles")),
    ("no_new_failures", lambda r: r.get("chosen_new_failures", 0) < r.get("rejected_new_failures", 0)),
    ("fewer_security_findings", lambda r: r.get("chosen_security_findings", 0) < r.get("rejected_security_findings", 0)),
    ("smaller_patch", lambda r: r.get("chosen_patch_size", 9999) < r.get("rejected_patch_size", 9999)),
    ("fewer_unnecessary_edits", lambda r: r.get("chosen_unnecessary_edits", 0) < r.get("rejected_unnecessary_edits", 0)),
]


@dataclass
class BuildPreferencesResult:
    pairs: list[dict] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)


def build_preferences_from_results(
    results: list[dict],
    prompt: str | None = None,
    use_verifier_labels: bool = False,
) -> BuildPreferencesResult:
    """Turn model outputs annotated with verifier labels into (chosen, rejected) pairs.

    Each result should carry metadata:
      tests_pass, compiles, new_failures, security_findings, patch_size,
      unnecessary_edits.
    use_verifier_labels=True means the labels already encode pass/fail and we can
    prefer any passing output over a failing one directly.
    """
    builder = BuildPreferencesResult()
    passing = [r for r in results if r.get("tests_pass")]
    failing = [r for r in results if not r.get("tests_pass")]

    if use_verifier_labels and passing and failing:
        for p in passing:
            for f in failing[:1]:
                builder.pairs.append({
                    "prompt": prompt or p.get("prompt", ""),
                    "chosen": p.get("output", ""),
                    "rejected": f.get("output", ""),
                    "metadata": {
                        "chosen_tests_pass": True,
                        "rejected_tests_pass": False,
                        "task_type": "repair",
                    },
                })
        return builder

    for i in range(len(results) - 1):
        for j in range(i + 1, len(results)):
            a, b = results[i], results[j]
            decision = _prefer(a, b)
            if decision is None:
                continue
            chosen, rejected = (a, b) if decision else (b, a)
            builder.pairs.append({
                "prompt": prompt or chosen.get("prompt", ""),
                "chosen": chosen.get("output", ""),
                "rejected": rejected.get("output", ""),
                "metadata": {
                    "chosen_tests_pass": bool(chosen.get("tests_pass")),
                    "rejected_tests_pass": bool(rejected.get("tests_pass")),
                    "task_type": "repair",
                },
            })
    return builder


def _prefer(a: dict, b: dict) -> bool | None:
    """Return True if a is preferred over b, False if b, None if tie."""
    for _, rule in RANKING_RULES:
        a_better = rule(a)
        b_better = rule(b)
        if a_better != b_better:
            return a_better
    return None


def reward_from_verifier(metadata: dict) -> float:
    score = 0.0
    if metadata.get("hidden_tests_pass"):
        score += 1.00
    if metadata.get("compiles"):
        score += 0.20
    if metadata.get("patch_minimal"):
        score += 0.10
    if metadata.get("new_regression"):
        score -= 0.20
    if metadata.get("linter_security_regression"):
        score -= 0.30
    if metadata.get("timeout"):
        score -= 1.00
    if metadata.get("sandbox_violation"):
        score -= 1.00
    return score


def train_dpo(
    pairs: list[dict],
    base_model_id: str,
    method: str = "dpo",
    output_dir: str = "artifacts/models",
    max_steps: int = 300,
    learning_rate: float = 5e-5,
    beta: float = 0.1,
    seed: int = 42,
) -> dict:
    """DPO (or ORPO) fine-tune on verifier-derived preference pairs."""
    from trl import DPOTrainer, ORPOTrainer, DPOConfig

    from transformers import AutoModelForCausalLM, AutoTokenizer

    tmp_dir = Path(output_dir) / (method + "-tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def _fmt(x, field_name):
        return f"### Prompt\n{x['prompt']}\n\n### {field_name}\n{x[field_name.lower()]}"

    formatted = []
    for p in pairs:
        formatted.append({
            "prompt": _fmt(p, "Prompt"),
            "chosen": p["chosen"],
            "rejected": p["rejected"],
        })

    config = DPOConfig(
        output_dir=str(tmp_dir),
        max_steps=max_steps,
        per_device_train_batch_size=2,
        learning_rate=learning_rate,
        beta=beta,
        seed=seed,
        report_to=[],
    )
    model = AutoModelForCausalLM.from_pretrained(base_model_id)
    model_ref = AutoModelForCausalLM.from_pretrained(base_model_id)

    trainer_cls = ORPOTrainer if method == "orpo" else DPOTrainer
    trainer = trainer_cls(
        model=model,
        ref_model=None if method == "orpo" else model_ref,
        args=config,
        train_dataset=formatted,
        tokenizer=tokenizer,
    )
    trainer.train()

    out = Path(output_dir) / f"{method}-{seed}"
    out.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(out))
    tokenizer.save_pretrained(str(out))
    return {"method": method, "output_dir": str(out), "pairs": len(pairs), "seed": seed}