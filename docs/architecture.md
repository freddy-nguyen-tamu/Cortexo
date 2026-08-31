# Cortexo architecture

```
                 +---------------------------+
                 |   Vue 3 + Vite (web)      |
                 |  visualizers + router     |
                 +------------+--------------+
                              | HTTP (VITE_API_BASE_URL)
                              v
                 +---------------------------+
                 |   Spring Boot (API)       |
                 |  auth, rate limit,        |
                 |  registries, experiments, |
                 |  benchmarks, agents,      |
                 |  inference orchestrator   |
                 +-----+------------+--------+
                       |            |  ML_GATEWAY_URL
                       v            v
            +----------+-----+   +---------------------------+
            |  MongoDB (req)  |   |   Python ML service       |
            |  repositories/  |   |  tokenizer, scratch model |
            |  models/runs    |   |  ingest, retrieval,       |
            +----------+-----+   |  agents, router, evaluate  |
                       |          +----+--------+-------------+
                       v               |        |
            +----------+-----+         |        +---> sandbox (docker, no net)
            | PostgreSQL     |         |
            | evaluation SQL |         +---> artifacts/ (checkpoints, traces)
            +----------------+
```

## Core contracts

### Java <-> Python

Spring calls the Python gateway over HTTP. The `GenerateResponse` shape is:

```json
{
  "requestId": "...",
  "modelVariantId": "...",
  "output": "...",
  "structuredOutput": {},
  "usage": {"latencyMs": 0, "promptTokens": 0, "generatedTokens": 0},
  "trace": {"retrievalIds": [], "toolCalls": [], "warnings": []}
}
```

### Serving abstraction (blueprint section 43, verbatim)

`GenerationConfig(max_new_tokens, temperature, top_p, top_k)` and
`GenerationResult(text, prompt_tokens, generated_tokens, latency_ms, metadata)`
backed by a `ModelBackend.load/generate` protocol. Implementations in
`ml/src/cortexo_ml/serving/backends.py`: Echo, Scratch (from checkpoint),
Hugging Face, ONNX, Quantized, RAG, Agent, Router.

### Evaluation task object (blueprint section 48)

Every model receives the same `EvaluationTask`: `task_id`, `task_type`,
`repository_snapshot_id`, `prompt`, `expected_behavior`, `allowed_tools`,
`test_command`, `compile_command`, `gold_files`, `gold_patch`,
`ground_truth_findings`, `timeout_seconds`.

## Data plane

- **MongoDB** (primary): users, repositories, repository_snapshots/files/
  symbols/chunks/graph_nodes/graph_edges, models, tokenizers, datasets,
  training_runs, experiments, agent_runs, retrieval_runs, router_decisions.
- **PostgreSQL** (normalized analytics): benchmark_runs, task_runs,
  hardware_reports.
- **Redis** (optional): rate limiting + cache control.
- **Cassandra / MySQL / SQL Server / Oracle / Db2**: research/benchmark
  environments only (`docker-compose.research.yml` behind profiles).
- **Artifacts**: `artifacts/` locally, per-run experiment tracker layout
  (`config.json`, `environment.json`, `source.json`, `metrics.jsonl`,
  `summary.json`, `stdout.log`).

## Processing chain (repository knowledge)

1. Register repository -> snapshot id
2. Files enumerated; binaries + secrets excluded
3. Language detection -> tokenizer -> chunks
4. Tree-sitter AST -> symbols
5. Import/call/inheritance graph (nodes + typed edges)
6. BM25 index + dense embeddings
7. Metadata persisted; snapshot marked READY
8. Retrieval: BM25 -> dense -> Reciprocal Rank Fusion -> rerank -> AST
   normalization -> graph expansion -> dedupe -> token-budget context packing

## Execution chain (agents)

Plan (structured PatchPlan) -> tool calls (predefined commands only) ->
patch/diff -> compile + test (sandboxed) -> reflection -> repair loop
(max 3 attempts), with Review/Security/Test/Debug specialists.

## Observability

Structured JSON logs (timestamp, requestId, userId, taskId, experimentId,
modelVariantId, repositorySnapshotId, durationMs, status). Error taxonomy
includes SANDBOX_TIMEOUT, SANDBOX_POLICY, COMPILE_FAIL, TEST_FAIL,
INVALID_STRUCTURED_OUTPUT, RETRIEVAL_EMPTY/WRONG, ROUTER_NO_FEASIBLE_MODEL.

## Licensing

See `docs/licensing.md`. Every model/dataset license is resolved before use.