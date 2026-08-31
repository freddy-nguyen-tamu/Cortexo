from __future__ import annotations

import datetime
import json
import sys
from dataclasses import dataclass, field

from cortexo_ml.serving.model_interface import GenerationConfig


@dataclass
class StdioRequest:
    request_id: str
    model: str
    prompt: str
    config: GenerationConfig

    @classmethod
    def from_json(cls, payload: dict) -> "StdioRequest":
        gen = payload.get("generation") or payload.get("config") or {}
        return cls(
            request_id=payload.get("requestId") or payload.get("request_id") or "unknown",
            model=payload.get("modelVariantId") or payload.get("model") or "default",
            prompt=payload.get("prompt", ""),
            config=GenerationConfig(
                max_new_tokens=int(gen.get("maxNewTokens", gen.get("max_new_tokens", 256))),
                temperature=float(gen.get("temperature", 0.2)),
                top_p=float(gen.get("topP", gen.get("top_p", 0.95))),
                top_k=int(gen.get("topK", gen.get("top_k", 50))),
            ),
        )


def stdio_loop(backends: dict[str, "ModelBackend"], out=None, inp=None) -> None:
    """Minimal line-delimited JSON stdio server.

    Each request: {"requestId", "model", "prompt", "generation": {...}}
    Each response: {"requestId", "status": "ok", "text": ..., "latencyMs": ...}
    """
    out = out or sys.stdout
    inp = inp or sys.stdin
    for line in inp:
        line = line.strip()
        if not line:
            continue
        try:
            request = StdioRequest.from_json(json.loads(line))
        except json.JSONDecodeError as exc:
            out.write(json.dumps({"requestId": "?", "status": "error", "message": f"bad json: {exc}"}) + "\n")
            out.flush()
            continue

        backend = backends.get(request.model)
        if backend is None:
            out.write(json.dumps({"requestId": request.request_id, "status": "error", "message": "unknown model", "available": list(backends)}) + "\n")
            out.flush()
            continue
        result = backend.generate(request.prompt, request.config)
        out.write(json.dumps({
            "requestId": request.request_id,
            "status": "ok",
            "text": result.text,
            "promptTokens": result.prompt_tokens,
            "generatedTokens": result.generated_tokens,
            "latencyMs": round(result.latency_ms, 2),
        }) + "\n")
        out.flush()


def jsonl_inference_server(backends: dict[str, "ModelBackend"], in_path: str, out_path: str) -> None:
    """Batch JSONL inference: one request per line in, one response per line out."""
    from pathlib import Path

    with open(in_path) as fh_in, open(out_path, "w") as fh_out:
        for line in fh_in:
            fh_out.write(handle_one_line(backends, line) + "\n")
    print(f"wrote {out_path}")


def handle_one_line(backends: dict[str, "ModelBackend"], line: str) -> str:
    request = StdioRequest.from_json(json.loads(line))
    backend = backends[request.model]
    result = backend.generate(request.prompt, request.config)
    return json.dumps({
        "requestId": request.request_id,
        "model": request.model,
        "status": "ok",
        "text": result.text,
        "latencyMs": round(result.latency_ms, 2),
        "metadata": result.metadata,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    })


def build_vllm_command(
    model_path: str,
    port: int = 8001,
    dtype: str = "auto",
    max_model_len: int = 4096,
    gpu_memory_utilization: float = 0.9,
    quantization: str | None = None,
    extra: list[str] | None = None,
) -> str:
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_path,
        "--port", str(port),
        "--dtype", dtype,
        "--max-model-len", str(max_model_len),
        "--gpu-memory-utilization", str(gpu_memory_utilization),
        "--served-model-name", model_path.replace("/", "-"),
    ]
    if quantization:
        cmd += ["--quantization", quantization]
    if extra:
        cmd += extra
    return " ".join(cmd)


def speculative_decode_command(draft: str, target: str, gpu_memory_utilization: float = 0.75) -> str:
    return (
        f"python -m vllm.entrypoints.openai.api_server --model {target} "
        f"--speculative-model {draft} --num-speculative-tokens 5 "
        f"--gpu-memory-utilization {gpu_memory_utilization}"
    )