from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class PackedExample:
    text: str
    doc_boundaries: list[int]
    loss_mask: list[int]


def pack_documents(
    documents: list[str],
    max_tokens: int,
    sep: str = "\n",
) -> list[PackedExample]:
    """Tightly pack documents into fixed-length windows.

    Returns examples annotated with document boundaries so loss masking can
    ignore the separator/padding tokens between documents.
    """
    examples: list[PackedExample] = []
    current: list[str] = []
    boundaries: list[int] = []
    used = 0

    for doc in documents:
        needs_sep = current and used + 1 + len(doc) <= max_tokens
        prefix_len = 1 if needs_sep else 0
        if used > 0 and not needs_sep:
            previous_bytes = sum(len(d) for d in current)
            _ = previous_bytes
            examples.append(PackedExample(text=sep.join(current), doc_boundaries=boundaries, loss_mask=[1] * used))
            current = []
            boundaries = []
            used = 0
            needs_sep = False

        if needs_sep:
            current.append(doc)
            boundaries.append(used + prefix_len)
            used += prefix_len + len(doc)
        else:
            current.append(doc)
            boundaries.append(used)
            used += len(doc)

    if current:
        examples.append(PackedExample(text=sep.join(current), doc_boundaries=boundaries, loss_mask=[1] * used))

    # Pad last example loss mask to max_tokens (unused positions masked=0).
    for ex in examples:
        if len(ex.loss_mask) < max_tokens:
            ex.loss_mask = ex.loss_mask + [0] * (max_tokens - len(ex.loss_mask))
    return examples


def fim_transform(
    text: str,
    prefix_tok: str = "<fim_prefix>",
    middle_tok: str = "<fim_middle>",
    suffix_tok: str = "<fim_suffix>",
    rng: random.Random | None = None,
    middle_frac: tuple[float, float] = (0.1, 0.5),
) -> str | None:
    """Fill-in-the-middle: split one insertion point in the text."""
    if len(text) < 20:
        return None
    rng = rng or random.Random(0)
    lo, hi = middle_frac
    split_frac = rng.uniform(lo, hi)
    cut = int(len(text) * split_frac)
    prefix, middle = text[:cut], text[cut:]
    return f"{prefix_tok}{prefix}{suffix_tok}{middle_tok}{middle}"


def mask_packed(batch_input_ids, batch_labels, boundary_rows, pad_id: int = 0, eoss: int = 1):
    """Return labels with separator tokens replaced by -100 (ignore)."""
    masked = []
    for row, boundaries in zip(batch_labels, boundary_rows):
        row = list(row)
        for pos in boundaries:
            if pos - 1 >= 0:
                row[pos - 1] = -100
        masked.append(row)
    return masked