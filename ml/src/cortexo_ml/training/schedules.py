import math

def cosine_lr(
    step,
    warmup_steps,
    max_steps,
    max_lr,
    min_lr,
):
    if step < warmup_steps:
        return max_lr * (step + 1) / max(1, warmup_steps)

    progress = (
        (step - warmup_steps)
        / max(1, max_steps - warmup_steps)
    )
    progress = min(max(progress, 0.0), 1.0)

    coeff = 0.5 * (1.0 + math.cos(math.pi * progress))
    return min_lr + coeff * (max_lr - min_lr)