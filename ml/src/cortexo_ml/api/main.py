import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from cortexo_ml.serving.model_interface import GenerationConfig
from cortexo_ml.serving.backends import EchoBackend

app = FastAPI(title="Cortexo ML Gateway", version="0.1.0")

ARTIFACTS_ROOT = Path(os.environ.get("CORTEXO_ARTIFACTS", "artifacts"))
BACKENDS: dict[str, Any] = {}
_indexes: dict[str, Any] = {}


def _get_backend(model_id: str) -> Any:
    if model_id in BACKENDS:
        return BACKENDS[model_id]
    backend = EchoBackend(model_id=model_id)
    BACKENDS[model_id] = backend
    return backend


class GenerateRequest(BaseModel):
    requestId: str
    modelVariantId: str
    repositorySnapshotId: str | None = None
    taskId: str | None = None
    prompt: str
    seed: int = 42
    generation: dict[str, Any] = Field(default_factory=dict)


class TokenizeRequest(BaseModel):
    text: str
    tokenizerId: str = "code-bpe-16k"


class IngestRequest(BaseModel):
    repository: str
    path: str
    snapshotId: str | None = None


class AgentRunRequest(BaseModel):
    runId: str | None = None
    repositorySnapshotId: str | None = None
    task: str
    maxAttempts: int = 3
    language: str = "python"


class EvaluationRequest(BaseModel):
    task: dict[str, Any]
    modelVariantId: str
    repositorySnapshotId: str | None = None
    seed: int = 42


@app.get("/health")
def health():
    return {"status": "ok", "service": "cortexo-ml", "version": "0.1.0"}


@app.get("/v1/models/available")
def available_models():
    models = []
    for model_id, backend in BACKENDS.items():
        meta = backend.metadata()
        models.append({"modelId": model_id, **meta})
    if not any(m["modelId"] == "echo-demo" for m in models):
        models.append({"modelId": "echo-demo", "backend": "echo", "placeholder": True})
    return {"status": "ok", "data": {"models": models}}


@app.post("/v1/inference/generate")
def generate(req: GenerateRequest):
    start = time.perf_counter()

    backend = _get_backend(req.modelVariantId)

    config = GenerationConfig(
        max_new_tokens=int(req.generation.get("maxNewTokens", 256)),
        temperature=float(req.generation.get("temperature", 0.2)),
        top_p=float(req.generation.get("topP", req.generation.get("top_p", 0.95))),
        top_k=int(req.generation.get("topK", req.generation.get("top_k", 50))),
    )

    retrieval_ids = []
    tool_calls = []
    warnings = []
    prompt = req.prompt

    index = None
    if req.repositorySnapshotId and req.repositorySnapshotId in _indexes:
        index = _indexes[req.repositorySnapshotId]
        try:
            context = index.search(req.prompt, max_tokens=4096)
            retrieval_ids.append(context.to_record())
            prompt = _sandwich_context(context, req.prompt)
        except Exception as exc:
            warnings.append(f"retrieval failed: {exc}")

    result = backend.generate(prompt, config)

    return {
        "requestId": req.requestId,
        "modelVariantId": req.modelVariantId,
        "output": result.text,
        "structuredOutput": {},
        "usage": {
            "latencyMs": round((time.perf_counter() - start) * 1000, 2),
            "promptTokens": result.prompt_tokens,
            "generatedTokens": result.generated_tokens,
        },
        "trace": {
            "retrievalIds": retrieval_ids,
            "toolCalls": tool_calls,
            "warnings": warnings + list(result.metadata.get("backend", "") and []),
        },
    }


@app.post("/v1/tokenize")
def tokenize(req: TokenizeRequest):
    tokenizer_path = ARTIFACTS_ROOT / "tokenizers" / req.tokenizerId / "tokenizer.json"
    if not tokenizer_path.exists():
        raise HTTPException(status_code=404, detail=f"tokenizer not found: {req.tokenizerId}")
    from cortexo_ml.tokenization.tokenizer import load_tokenizer

    tokenizer = load_tokenizer(tokenizer_path)
    ids = tokenizer.encode(req.text)
    return {
        "status": "ok",
        "data": {
            "tokenizerId": req.tokenizerId,
            "tokens": list(ids.tokens[:500]),
            "ids": list(ids.ids[:500]),
            "offsets": list(ids.offsets[:500]),
            "count": len(ids.ids),
        },
    }


@app.post("/v1/repositories/ingest")
def ingest_repo(req: IngestRequest):
    root = Path(req.path)
    if not root.is_dir():
        raise HTTPException(status_code=404, detail=f"path not found: {req.path}")
    from cortexo_ml.repository.ingest import ingest_repository

    result = ingest_repository(req.repository, root, snapshot_id=req.snapshotId)
    from cortexo_ml.retrieval.context_builder import RepositoryIndex

    _indexes[result.snapshot_id] = RepositoryIndex.from_ingest(result)
    return {"status": "ok", "data": result.to_record()}


@app.post("/v1/agents/runs")
def agent_run(req: AgentRunRequest):
    from cortexo_ml.agents.repair_agent import RepairAgent, RepairAgentConfig
    from cortexo_ml.agents.tools import ToolExecutor
    from cortexo_ml.agents.verifier import Verifier

    backend = _PromptBackend()

    workspace = None
    if req.repositorySnapshotId and req.repositorySnapshotId in _indexes:
        index = _indexes[req.repositorySnapshotId]
        if getattr(index, "_workspace", None):
            workspace = index._workspace

    tools = ToolExecutor(workspace=workspace or Path(os.environ.get("SANDBOX_WORKSPACE", "/tmp/cortexo-workspace")))
    verifier = Verifier(tools)
    agent = RepairAgent(backend, tools, verifier, RepairAgentConfig(max_attempts=req.maxAttempts, language=req.language))
    result = agent.run(repo="repository", task=req.task, run_id=req.runId)
    return {"status": "ok", "data": result.to_record()}


@app.post("/v1/evaluations/run")
def evaluation_run(req: EvaluationRequest):
    from cortexo_ml.evaluation.runner import run_evaluation

    def _prompt_fn(prompt: str) -> str:
        return _get_backend(req.modelVariantId).generate(prompt, GenerationConfig(temperature=0.2)).text

    def _retrieval_fn(query: str):
        index = _indexes.get(req.repositorySnapshotId or "")
        if index:
            return index.search(query, max_tokens=4096)
        return None

    record = run_evaluation(
        task=req.task,
        model_variant_id=req.modelVariantId,
        prompt_fn=_prompt_fn,
        repository_snapshot_id=req.repositorySnapshotId,
        retrieval_fn=_retrieval_fn,
        seed=req.seed,
    )
    return {"status": "ok", "data": record}


class _PromptBackend:
    """Deterministic offline agent backend that can answer simple repair prompts."""

    def complete(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.2) -> str:
        text = prompt[-4000:]
        if "uniform diff" in prompt.lower() or "diff" in prompt.lower():
            return _probe_diff(text)
        return _probe_plan(text)


def _probe_plan(text: str) -> str:
    return '{"summary": "deterministic plan", "steps": ["read failing test", "locate function", "apply patch", "run tests"], "files": [], "risk": "low"}'


def _probe_diff(text: str) -> str:
    import re

    for pattern in [r"for i in range\((\d+)\)", r"range\((\d+)\)", r"range\((\d+),\s*(\d+)\)"]:
        m = re.search(pattern, text)
        if m:
            a = m.group(1)
            b = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            end = b or a
            return f"--- a/source\n+++ b/source\n@@ -1,3 +1,3 @@\n- for i in range({a}:{b or ''})\n+ for i in range(1, {end} + 1)\n"
    return (
        "--- a/source\n+++ b/source\n@@ -0,0 +1 @@\n+patch\n"
    )


def _sandwich_context(context, prompt: str) -> str:
    blocks = []
    for c in context.chunks[:8]:
        blocks.append(f"### {c.path}\n{c.text[:3000]}")
    return "\n\n".join(blocks) + "\n\nTASK:\n" + prompt