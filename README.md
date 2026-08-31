# Cortexo

## What it is

Cortexo is an end-to-end LLM research and autonomous software-engineering
platform. It implements configurable decoder-only code transformers, a custom
code tokenizer, registry-driven model/dataset lineage, repository analysis and
retrieval, sandboxed software-engineering agents, a common executable benchmark
harness, and a Vue/Spring Boot/MongoDB application that visualizes the entire
model lifecycle.

## Why it exists

Most portfolio projects wrap someone else's model. Cortexo instead treats the
model as the artifact: the same repository-level task is replayed against
scratch-trained, domain-pretrained, fine-tuned, PEFT, aligned, distilled,
quantized, retrieval-enhanced, graph-enhanced, agentic, routed and ensemble
variants — with controlled evaluation at every step.

## Research thesis

Controlled evaluation beats feature count. Every claimed result must come from
a reproducible run with a recorded seed, exact artifact hashes, generation
settings and environment. The platform is organized around that principle
(sections 1, 124, 125 of the build blueprint).

## What makes it different

- Not an API wrapper: custom scratch Transformer + custom tokenizer.
- Repository-level context is auditable: lexical (BM25), dense, AST,
  dependency-graph, reranked and compressed for a token budget, with a
  per-stage retrieval trace.
- Hallucination is measured, not assumed: path existence, symbol existence,
  dependency-edge, executed-test and executed-tool validators feeding a
  hallucination_rate.
- Generated code runs only in a disposable sandbox (no network, no root,
  bounded resources, policy-restricted command types).

## LLM lifecycle covered

Tokenizer training -> corpus pipeline (collect/clean/dedup/synthesize/split/
pack) -> scratch pretraining -> DAPT -> SFT/LoRA/QLoRA/IA3 -> DPO ->
distillation -> pruning -> quantization -> retrieval -> agents -> routing ->
benchmark evaluation -> calibration -> observability -> registry.

## Model variants

| Variant | Path |
|---|---|
| `scratch9m-code-v1` / `scratch33m-code-v1` / `scratch70m-code-v1` | scratch pretraining (`ml/scratch_model`, `ml/training`) |
| `qwen05b-base` | Apache-2.0 baseline Qwen2.5-Coder-0.5B |
| `qwen05b-dapt-codev1` | domain-adaptive continued pretraining |
| `qwen05b-lora-r16-swev1` / `qwen05b-qlora-r16-swev1` | LoRA / QLoRA repair adapters |
| DPO / distillation / INT8 / INT4 variants | post-training + serving backends |

## Architecture diagram

```
Vue 3 (visualizers)  ->  Spring Boot API  ->  Python ML gateway
                        MongoDB (registries/snapshots)
                        PostgreSQL (normalized eval metrics)
                        Redis (optional cache/rate limiting)
                        research DBs behind compose profiles
```

See `docs/architecture.md`.

## Scratch Transformer

`ml/scratch_model/` contains the full implementation: `config.py`,
`layers.py` (RMSNorm), `rope.py`, `attention.py`, `model.py`
(decoder-only, FIM-aware), `generate.py`, `parameter_count.py`, `moe.py`.

Training loop: AdamW + gradient accumulation + mixed precision (FP16/BF16)
+ gradient clipping + linear warmup to `max_lr`, cosine decay to `min_lr`,
frequent checkpoints with RNG/optimizer state for resume, JSONL telemetry.

## Training data

- Corpus source manifest + per-source license gate: `datasets/manifests/`.
- Benchmark solutions, hidden tests and target patches are excluded from
  training corpora by path rules.
- Every final dataset has a dataset card (`datasets/processed/code-v1/`).
- Synthetic repair corpus with 17 mutation operators validated by verifier
  (before/after pass) in `ml/data/synthesize.py`.

## Fine-tuning and alignment

`ml/post_training/`: SFT (with LoRA/IA3 config, 4-bit QLoRA load), DPO
(preference labels from deterministic verifier rules: all tests pass >
compiles > fewer new failures > fewer security findings > smaller patch >
fewer unnecessary edits), distillation, pruning and quantization helpers.

## Retrieval and repository graph

Repository ingestion produces chunks + AST symbols + a typed dependency graph
(REPOSITORY/MODULE/FILE/CLASS/FUNCTION/METHOD, edges CONTAINS/IMPORTS/CALLS/
INHERITS/README_TABLE/…). Retrieval pipeline: BM25 -> dense -> Reciprocal Rank
Fusion -> rerank -> AST normalization -> graph expansion -> dedupe ->
token-budget packing, with every stage recorded for the RetrievalTraceVisualizer.

## Agents

Planner -> executor -> verifier -> reflector -> repair loop, plus Review,
Security, Test and Debug specialists. Tools are predefined; generated code is
sandboxed (`sandbox/`).

## Evaluation methodology

Canonical task object (same for every model) across suites: `micro-codegen`,
`synthetic-bugfix`, `repo-understanding`, `code-review`, `security-review`,
`polydb-swe` (PostgreSQL/MySQL/SQL Server/Oracle/Db2), `retrieval`,
`agent-repair`, `context-strategy`. Metrics: pass@k, repair success,
regressions, review precision/recall, retrieval recall@k, hallucination rate,
calibration (Brier, ECE), latency/throughput/memory.

## Deterministic regression

The grader's own verdicts are guarded by a committed good/bad baseline
(`benchmarks/baselines/deterministic-v1.json`) re-run through the same
executable grader. A regression is any mismatch between expected and actual
status — including a failure mode that changed (`TEST_FAIL` → `COMPILE_FAIL`)
but including a bad fixture that now passes. `make regression` runs the
software checks plus the 11 baseline cases (`make regression-fast`,
`make regression-grader`, `make regression-show`), writes git-ignored reports
to `artifacts/evaluations/regression/` with history deltas, and exposes
read-only endpoints + the Benchmarks progress panel. Baseline fixtures and
hidden tests are excluded from training corpora. See `docs/regression.md`.

## Visualizers

Architecture, tokenizer, training curves, scaling, attention, weight stats,
retrieval trace, repository graph, agent trace, router, calibration,
quantization, dataset lineage, database architecture, Model Arena.

## Polyglot data architecture

MongoDB required primary; PostgreSQL normalized eval analytics; Redis
cache/control; Cassandra telemetry; MySQL/SQL Server/Oracle/Db2 as safe local
benchmark fixtures; Databricks for offline analytics; Snowflake intentionally
disabled (trial-only). See `docs/snowflake-optional.md`.

## Free deployment architecture

Cloudflare Pages + Render + MongoDB Atlas Free (+ optional Neon/Redis). Heavy
training runs on Kaggle/Colab/local GPU and results are uploaded to the
registry. The public site also works in offline "Replay Experiment" mode with
clearly-labeled placeholder data.

## Reproducibility

Every experiment records gitSha, datasetSha256, tokenizerSha256,
parentModelSha256, seed, environment, generation settings, latency and tool
calls in an experiment folder (`artifacts/evaluations/<run-id>/`).

## Security

Generated code is executed only inside the sandbox: non-root, `--network none`,
`--read-only`, bounded memory/CPU/PID, wall-clock timeout, process-tree kill,
tmpfs, workspace deleted afterward. Secrets scanner gates indexing, and
auth/rate-limiting (Redis or in-memory token bucket) gate the public API.

## Results

No benchmark numbers are reported yet. The Results section will contain only
real, reproducible measurements once training and evaluation runs complete.
Existing demo records are explicitly labeled
`DEMO PLACEHOLDER - NOT A REAL BENCHMARK RESULT`.

## Research questions

1. How does scratch-model quality scale with parameter count?
2. Does FIM pretraining improve code infilling?
3. How much does DAPT improve a small coding model?
4. When does LoRA match full SFT?
5. How much memory does QLoRA save?
6. Does DPO improve executable repair success?
7. How much quality survives distillation?
8. What quality is lost at INT8/INT4?
9. Does AST-aware retrieval beat dense retrieval?
10. Does graph expansion help repository-level tasks?
11. Does reflection improve repair or mostly add latency?
12. Can tests create useful automatic preference labels?
13. Can confidence predict repair failure?
14. Can a dynamic router preserve quality with lower average compute?
15. Which SQL dialect causes the most hallucinations?
16. Does a small MoE specialize experts by task type?
17. Can hard-negative mining improve code retrieval?
18. Does continued learning cause measurable forgetting?

## Limitations

- Scratch models are small (9M/33M/70M) and matched against permissively
  licensed, small-to-medium corpora.
- Free hosting platforms sleep; heavy inference is not presented as permanent.
- All reported metrics require a registered run with seed + hashes; placeholder
  data is labeled and will be deleted before any real report.

## Roadmap

Complete the model registry + first real scratch pretraining run (Kaggle),
then DAPT/LoRA/QLoRA/DPO and quantization comparisons, then a common
benchmark dashboard and Model Arena, then PolyDB-SWE + routing + continuous
learning experiments, matching blueprint sections 98-100.

## License

Project source: MIT (see `LICENSE`). All training data and model weights carry
their own resolved licenses (`docs/licensing.md`); no dataset enters training
without a recorded license decision.

## Quick start

```bash
docker compose -f docker-compose.core.yml up -d           # MongoDB, Postgres, Redis
cd ml && python -m venv .venv && source .venv/bin/activate
pip install -e . && pip install -r requirements.txt
uvicorn cortexo_ml.api.main:app --reload --port 8000

cd apps/api-spring && ./mvnw spring-boot:run             # API :8080
cd apps/web-vue && npm install && npm run dev            # UI :5173
```

Health checks: `http://localhost:8080/api/health`, `http://localhost:8000/health`.

See `docs/deployment.md`, `notebooks/README.md`, `benchmarks/README.md`,
`sandbox/README.md`, `docs/regression.md`.