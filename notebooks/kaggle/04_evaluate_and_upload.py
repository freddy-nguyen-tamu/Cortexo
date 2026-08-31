# Kaggle notebook 04 - Evaluate scratch + adapted models locally, upload artifacts.

# %% [markdown]
# # Cortexo evaluation + registry handoff (Kaggle)
# Runs micro-codegen, synthetic-bugfix and PolyDB-SWE smoke evaluations with
# the benchmark task objects, then packages artifacts for the model registry.

# %% [code]
import os, sys, json, hashlib
sys.path.insert(0, "/kaggle/working/Cortexo/ml/src")

from cortexo_ml.serving.backends import ScratchBackend, EchoBackend
from cortexo_ml.serving.weights import load_scratch_checkpoint
from cortexo_ml.serving.model_interface import GenerationConfig
from cortexo_ml.evaluation.pass_at_k import compute_pass_at_k
from cortexo_ml.evaluation.resource_metrics import compute_resource_report

# %% [code]
# Placeholder backend: swap for ScratchBackend once a real checkpoint exists.
backend = EchoBackend(model_id="scratch33m-code-v1")
config = GenerationConfig(max_new_tokens=128, temperature=0.2, top_p=0.95, top_k=50)

# Example latency report (pure python; no GPU required).
report = compute_resource_report(
    latencies=[100.0, 260.0, 310.0, 4000.0],
    output_tokens=64,
    hardware={"gpu": None, "memory_mb": 0},
)

tasks = json.load(open("/kaggle/working/Cortexo/benchmarks/tasks/micro-codegen.json"))
runs = []
for task in tasks:
    out = backend.generate(task["prompt"], config)
    runs.append({
        "taskId": task["task_id"],
        "modelVariantId": "scratch33m-code-v1",
        "output": out.text,
        "metrics": {"pass@1-hint": None},  # real grader fills this
    })
print(f"generated {len(runs)} candidate outputs")

# Shipped pure-python pass@k reference (no scipy needed):
print("pass@k example:", compute_pass_at_k(n_samples=10, n_correct=7, k=1))

# %% [code]
# Artifact packaging with hashes for the registry.
def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

manifest = {
    "modelVariantId": "scratch33m-code-v1",
    "parentModelId": None,
    "artifactSha256": None,
    "tokenizerSha256": None,
    "license": "project-defined",
    "metrics": {},
    "tags": ["scratch", "code"],
}
os.makedirs("/kaggle/working/registry", exist_ok=True)
with open("/kaggle/working/registry/model.json", "w") as fh:
    json.dump(manifest, fh, indent=2)
print(json.dumps(manifest, indent=2))

# %% [markdown]
# Upload `registry/model.json` + metrics + cards. Register in MongoDB `models`,
# then the Evaluation/Scaling visualizers in the Vue app show these runs.
# NOTE: never present placeholder runs as real benchmark results.