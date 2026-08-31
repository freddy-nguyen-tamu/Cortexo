# Databricks notebook: 05_scaling_analysis.py
# Scratch model size vs validation loss vs pass@k vs latency. Feeds the
# ScalingVisualizer in the Vue app.

# Databricks notebook source
# MAGIC %md
# MAGIC # Scaling analysis

import json, os

TRAINING_CURVES = "/dbfs/cortexo/artifacts/training"  # one metrics.jsonl per run

def load_metrics(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows

runs = {
    "scratch9m-code-v1": load_metrics(os.path.join(TRAINING_CURVES, "scratch9m/metrics.jsonl")),
    "scratch33m-code-v1": load_metrics(os.path.join(TRAINING_CURVES, "scratch33m/metrics.jsonl")),
    "scratch70m-code-v1": load_metrics(os.path.join(TRAINING_CURVES, "scratch70m/metrics.jsonl")),
}

params = {"scratch9m-code-v1": 9_000_000, "scratch33m-code-v1": 33_000_000, "scratch70m-code-v1": 70_000_000}

rows = []
for model_id, metrics in runs.items():
    val = [m["validation_loss"] for m in metrics if m.get("validation_loss")]
    final_val = val[-1] if val else None
    steps = max((m.get("step", 0) for m in metrics), default=0)
    rows.append({
        "modelVariantId": model_id,
        "parameters": params[model_id],
        "finalValidationLoss": final_val,
        "steps": steps,
        "passAt1": None,   # filled after micro-codegen evaluation
        "p50LatencyMs": None,
    })

summary = {"scaling": rows}
with open("/dbfs/cortexo/exports/scaling_summary.json", "w") as fh:
    json.dump(summary, fh, indent=2)

# Compact parquet export -> visualized in Databricks + imported into MongoDB
# as "trainingRuns" documents for the TrainingCurveVisualizer.
from pyspark.sql import Row
spark.createDataFrame([Row(**r) for r in rows]).coalesce(1).write.mode("overwrite").parquet(
    "/dbfs/cortexo/exports/scaling.parquet"
)
print(json.dumps(summary, indent=2))