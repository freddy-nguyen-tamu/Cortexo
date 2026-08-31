from __future__ import annotations

import math

from cortexo_ml.scratch_model.config import TransformerConfig


def architecture_json(
    model_id: str,
    cfg: TransformerConfig,
    parameter_counts: dict | None = None,
) -> dict:
    counts = parameter_counts or {}
    layer_repr = []
    for layer in range(cfg.n_layers):
        layer_repr.append({
            "index": layer,
            "attention": {
                "type": "MHA" if cfg.n_kv_heads is None or cfg.n_kv_heads == cfg.n_heads else "GQA",
                "heads": cfg.n_heads,
                "kvHeads": cfg.n_kv_heads or cfg.n_heads,
                "headDim": cfg.d_model // max(1, cfg.n_heads),
            },
            "ffn": {
                "type": "SwiGLU",
                "hidden": cfg.d_ff,
                "experts": cfg.moe_num_experts or None,
                "topK": cfg.moe_top_k if cfg.moe_num_experts else None,
            },
        })
    return {
        "modelId": model_id,
        "embedding": {"vocab": cfg.vocab_size, "dimension": cfg.d_model},
        "layers": layer_repr,
        "norm": "RMSNorm",
        "position": "RoPE",
        "ropeTheta": cfg.rope_theta,
        "contextLength": cfg.max_seq_len,
        "parameters": counts,
        "tieEmbeddings": cfg.tie_embeddings,
        "useBias": cfg.use_bias,
    }


def training_curve_series(records: list[dict]) -> dict:
    """records: telemetry lines with step/loss/validation_loss/perplexity/learning_rate/grad_norm/..."""
    x = [r.get("step") for r in records]
    series = {
        "x": x,
        "train_loss": [r.get("loss") for r in records],
        "validation_loss": [r.get("validation_loss") for r in records if r.get("validation_loss") is not None],
        "validation_steps": [r.get("step") for r in records if r.get("validation_loss") is not None],
        "perplexity": [r.get("perplexity") for r in records if r.get("perplexity") is not None],
        "learning_rate": [r.get("learning_rate") for r in records],
        "grad_norm": [r.get("grad_norm") for r in records],
        "tokens_per_second": [r.get("tokens_per_second") for r in records],
        "peak_vram_mb": [r.get("peak_vram_mb") for r in records],
    }
    return series


def scaling_series(models: list[dict]) -> dict:
    params = [m.get("parameterCount", 0) for m in models]
    return {
        "parameters": params,
        "validationLoss": [m.get("validationLoss") for m in models],
        "passAt1": [m.get("passAt1") for m in models],
        "repairRate": [m.get("repairRate") for m in models],
        "latencyMs": [m.get("latencyMs") for m in models],
        "ramMb": [m.get("ramMb") for m in models],
        "vramMb": [m.get("vramMb") for m in models],
    }


def weight_histogram(values: list[float], bins: int = 40, label: str = "weight") -> dict:
    lo, hi = min(values), max(values)
    width = (hi - lo) / max(1, bins)
    hist = [0] * bins
    edges = []
    for i in range(bins):
        edges.append(lo + i * width)
        for v in values:
            if lo + i * width <= v < lo + (i + 1) * width:
                hist[i] += 1
    if values:
        hist[-1] = 0
        for v in values:
            if v == hi:
                hist[-1] += 1
    return {"label": label, "edges": edges, "counts": hist, "mean": sum(values) / len(values) if values else 0.0, "std": _std(values)}


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def quantization_table(rows: list[dict]) -> dict:
    return {"rows": rows}


def attention_metrics(attn_matrix) -> dict:
    """attn_matrix: numpy/Torch-like [n_pos, n_pos]."""
    try:
        import numpy as np
    except ImportError:
        return {"available": False}
    matrix = np.asarray(attn_matrix, dtype=np.float64)
    if matrix.ndim != 2:
        return {"available": False}
    n = matrix.shape[0]
    entropy_series = []
    avg_distance = []
    for i in range(n):
        row = matrix[i]
        row = row[row > 0]
        if row.size:
            entropy_series.append(-float((row * np.log(row + 1e-12)).sum()))
        else:
            entropy_series.append(0.0)
        distances = np.arange(n, dtype=np.float64)
        avg_distance.append(float((matrix[i] * distances).sum()))
    top = np.argsort(matrix[-1])[::-1][:5]
    return {
        "available": True,
        "size": n,
        "entropy": entropy_series,
        "averageAttentionDistance": avg_distance,
        "topAttendedTokens": [int(i) for i in top],
    }


def retrieval_trace_payload(context_record: dict) -> list[dict]:
    out = []
    for stage in context_record.get("trace", []):
        for cand in stage.get("candidates", []):
            out.append({
                "path": cand.get("path"),
                "chunkId": cand.get("chunkId"),
                "stage": stage.get("stage"),
                "rank": cand.get("rank"),
                "score": cand.get("score"),
                "included": cand.get("included", True),
            })
    return out


def graph_cytoscape(graph_record: dict) -> dict:
    elements = []
    for node in graph_record.get("nodes", []):
        elements.append({"data": {"id": node["id"], "label": node["name"], "type": node["type"]}})
    for edge in graph_record.get("edges", []):
        elements.append({"data": {"source": edge["source"], "target": edge["target"], "type": edge.get("type", "")}})
    return {"elements": elements}


def agent_timeline(trace_record: dict) -> list[dict]:
    events = []
    for i, event in enumerate(trace_record.get("events", [])):
        events.append({"index": i, "type": event.get("type"), "time": i, "summary": _event_summary(event)})
    return events


def _event_summary(event: dict) -> str:
    etype = event.get("type")
    data = event.get("data") or {}
    if etype == "PLAN":
        return str(data.get("summary") or data.get("prompt") or "plan")[:120]
    if etype in {"TOOL_REQUEST", "TOOL_RESULT"}:
        return f"attempt={data.get('attempt')}"
    if etype == "PATCH":
        return f"attempt={data.get('attempt')}"
    if etype in {"COMPILE", "TEST"}:
        return f"{data.get('summary')}"
    if etype == "REFLECT":
        return f"kind={data.get('failure_kind')}"
    if etype == "FINISH":
        return f"outcome={data.get('outcome')}"
    return str(data)[:120]


def router_table(decision: dict) -> dict:
    return {
        "candidates": decision.get("candidates", []),
        "selectedModel": decision.get("selectedModel"),
        "ruleBasedPick": decision.get("ruleBasedPick"),
        "fallback": decision.get("fallback"),
    }


def calibration_reliability(result: dict) -> dict:
    return {
        "reliability": result.get("reliability", []),
        "brierScore": result.get("brierScore"),
        "ece": result.get("ece"),
    }


def dataset_lineage(record: dict) -> list[dict]:
    stages = ["source", "license gate", "filtering", "dedup", "synthetic augmentation", "split", "tokenization", "dataset version"]
    out = []
    for i, stage in enumerate(stages):
        out.append({"index": i, "stage": stage, "source": record.get("datasetId", "?"), "parent": None if i == 0 else stages[i - 1]})
    return out


def database_architecture(adapters: list[dict]) -> list[dict]:
    return [
        {
            "id": a.get("id"),
            "enabled": a.get("enabled"),
            "role": a.get("role"),
            "health": a.get("health"),
            "lastLatencyMs": a.get("lastLatencyMs"),
            "recordCount": a.get("recordCount"),
            "mode": a.get("mode"),
        }
        for a in adapters
    ]


def tokenizer_comparison(listing: list[dict]) -> dict:
    return {"tokenizers": listing}