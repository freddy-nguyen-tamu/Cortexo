#!/usr/bin/env python3
"""Generate clearly-labeled PUBLIC DEMO DATA (blueprint section 107).

Produces demo artifacts under artifacts/demo/ so the Vue visualizers and the
offline replay mode have something safe to render before real runs exist.

Every demo record is labeled:
    DEMO PLACEHOLDER - NOT A REAL BENCHMARK RESULT

Delete artifacts/demo/ before reporting real numbers anywhere.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml" / "src"))

from cortexo_ml.visualization.charts import (
    architecture_json,
    training_curve_series,
    scaling_series,
    retrieval_trace_payload,
    graph_cytoscape,
    agent_timeline,
    router_table,
    calibration_reliability,
    dataset_lineage,
    database_architecture,
    tokenizer_comparison,
)
from cortexo_ml.scratch_model.config import TransformerConfig

DEMO_LABEL = "DEMO PLACEHOLDER - NOT A REAL BENCHMARK RESULT"
OUT = Path(__file__).resolve().parents[1] / "artifacts" / "demo"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    cfg = TransformerConfig()
    cfg.vocab_size = 17000

    payloads = {
        "architecture_scratch33m.json": architecture_json("scratch33m-code-v1", cfg),
        "training_curve_demo.json": training_curve_series(
            [
                {"step": s, "loss": 6.0 - s * 0.2, "validation_loss": 6.0 - s * 0.18}
                for s in range(0, 40)
            ]
        ),
        "scaling_demo.json": scaling_series(
            [
                {"modelId": "scratch9m-code-v1", "params": 8_500_000, "valLoss": 4.1, "passAt1": None},
                {"modelId": "scratch33m-code-v1", "params": 32_000_000, "valLoss": 3.6, "passAt1": None},
                {"modelId": "scratch70m-code-v1", "params": 68_000_000, "valLoss": 3.2, "passAt1": None},
            ]
        ),
        "retrieval_trace_demo.json": retrieval_trace_payload(
            {
                "query": "where is Calculator sum_range defined?",
                "trace": [
                    {"stage": "BM25", "candidates": [
                        {"path": "src/mathutil.py", "chunkId": "c1", "rank": 1, "score": 8.2, "included": True},
                        {"path": "src/app.py", "chunkId": "c2", "rank": 2, "score": 5.1, "included": True},
                    ]},
                    {"stage": "dense", "candidates": [
                        {"path": "src/mathutil.py", "chunkId": "c1", "rank": 1, "score": 0.9, "included": True},
                    ]},
                    {"stage": "graph expansion", "candidates": [
                        {"path": "src/mathutil.py", "chunkId": "c1", "rank": 1, "score": 0.99, "included": True},
                    ]},
                ],
            }
        ),
        "graph_demo.json": graph_cytoscape(
            {
                "nodes": [
                    {"id": "src/mathutil.py", "name": "src/mathutil.py", "type": "FILE"},
                    {"id": "src/mathutil.py:Calculator", "name": "Calculator", "type": "CLASS"},
                    {"id": "src/app.py", "name": "src/app.py", "type": "FILE"},
                ],
                "edges": [
                    {"source": "src/app.py", "target": "src/mathutil.py", "type": "IMPORTS"},
                    {"source": "src/mathutil.py:Calculator", "target": "src/mathutil.py", "type": "CONTAINS"},
                ],
            }
        ),
        "agent_trace_demo.json": agent_timeline(
            {
                "events": [
                    {"type": "PLAN", "data": {"summary": "read test, locate clamp, apply patch", "attempt": 0}},
                    {"type": "TOOL_REQUEST", "data": {"name": "read_file", "attempt": 1, "query": "range_util.py"}},
                    {"type": "TOOL_RESULT", "data": {"name": "read_file", "attempt": 1, "summary": "24 lines"}},
                    {"type": "PATCH", "data": {"attempt": 1, "summary": "swapped comparison branches"}},
                    {"type": "TOOL_REQUEST", "data": {"name": "run_tests", "attempt": 1}},
                    {"type": "TOOL_RESULT", "data": {"name": "run_tests", "attempt": 1, "summary": "8 passed"}},
                    {"type": "REFLECT", "data": {"attempt": 1, "summary": "both bugs fixed; no regression"}},
                ]
            }
        ),
        "router_table_demo.json": router_table(
            {
                "models": [
                    {"id": "scratch-9m", "name": "scratch-9m", "utility": 0.31, "switchedOn": True, "constraints": "ok"},
                    {"id": "qwen-lora-r16", "name": "qwen05b-lora-r16-swev1", "utility": 0.74, "switchedOn": False, "constraints": "slow"},
                    {"id": "qwen-qlora", "name": "qwen05b-qlora-r16-swev1", "utility": 0.68, "switchedOn": False, "constraints": "vram"},
                ],
                "selected": "qwen-lora-r16",
            }
        ),
        "calibration_demo.json": calibration_reliability(
            {
                "rows": [
                    {"bucket": 0.0, "accuracy": 0.0, "confidence": 0.0, "count": 20},
                    {"bucket": 0.2, "accuracy": 0.25, "confidence": 0.2, "count": 18},
                    {"bucket": 0.5, "accuracy": 0.42, "confidence": 0.5, "count": 15},
                    {"bucket": 0.8, "accuracy": 0.7, "confidence": 0.8, "count": 22},
                ]
            }
        ),
        "dataset_lineage_demo.json": dataset_lineage(
            {
                "root": "code-v1",
                "lineage": [
                    {"step": "raw", "label": "cortexo-demo-code-v1"},
                    {"step": "interim/clean", "label": "normalized"},
                    {"step": "interim/dedup", "label": "deduplicated"},
                    {"step": "processed", "label": "code-v1"},
                ],
            }
        ),
        "database_architecture_demo.json": database_architecture(
            [
                {"name": "MongoDB", "role": "primary/store", "status": "required"},
                {"name": "PostgreSQL", "role": "eval analytics", "status": "optional"},
                {"name": "Redis", "role": "cache", "status": "optional"},
                {"name": "Cassandra", "role": "telemetry", "status": "research"},
            ]
        ),
        "tokenizer_comparison_demo.json": tokenizer_comparison(
            [
                {"name": "code-bpe-16k", "tokensPerChar": 0.31, "vocab": 16000},
                {"name": "qwen2.5-coder-tokenizer", "tokensPerChar": 0.24, "vocab": 151936},
            ]
        ),
    }

    for name, payload in payloads.items():
        if isinstance(payload, dict):
            payload["demoLabel"] = DEMO_LABEL
            record = payload
        else:
            record = {"demoLabel": DEMO_LABEL, "data": payload}
        (OUT / name).write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"wrote artifacts/demo/{name}")

    # A single demo evaluation run record to feed replay mode / seeding.
    run = {
        "runId": "demo-run-1",
        "taskId": "synthetic-bugfix/range_util",
        "modelVariantId": "echo-demo",
        "repositorySnapshotId": "fixtures-bugs-range-util",
        "seed": 42,
        "generation": {"temperature": 0.2, "maxNewTokens": 256},
        "retrieval": {"mode": "bm25", "stages": ["BM25", "RRF"]},
        "agent": {"attempts": 1, "toolCalls": 3},
        "hardware": {"gpu": None, "ram_mb": 128},
        "output": "DEMO OUTPUT (echo)", 
        "patch": "DEMO PATCH (echo)",
        "tests": {"passed": None},
        "metrics": {"latencyMs": 2},
        "traceIds": [],
        "createdAt": "2026-01-01T00:00:00Z",
        "demoLabel": DEMO_LABEL,
    }
    (OUT / "evaluation_run_demo.json").write_text(
        json.dumps(run, indent=2), encoding="utf-8"
    )
    print("wrote artifacts/demo/evaluation_run_demo.json")


if __name__ == "__main__":
    main()