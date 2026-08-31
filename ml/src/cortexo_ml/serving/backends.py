from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from cortexo_ml.serving.model_interface import ModelBackend, GenerationConfig, GenerationResult


@dataclass
class BackendMetadata:
    model_id: str
    family: str
    technique: str
    precision: str
    quantization: str | None
    context_length: int
    loaded: bool = False
    extra: dict = field(default_factory=dict)


def _latency_ms(start: float) -> float:
    return (time.monotonic() - start) * 1000


class EchoBackend(ModelBackend):
    """Used by Spring->Python boot demo: echoes a deterministic placeholder."""

    def __init__(self, model_id: str = "echo-demo"):
        self.model_id = model_id

    def load(self) -> None:
        return None

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        start = time.monotonic()
        text = f"[ECHO BACKEND model={self.model_id}] {prompt[:200]}\n"
        return GenerationResult(
            text=text,
            prompt_tokens=len(prompt.split()),
            generated_tokens=len(text.split()),
            latency_ms=_latency_ms(start),
            metadata={"backend": "echo"},
        )

    def metadata(self) -> dict[str, Any]:
        return {"model_id": self.model_id, "backend": "echo"}


class ScratchBackend(ModelBackend):
    """Serves a cortexo_ml scratch transformer from a checkpoint (weights_only=True)."""

    def __init__(self, model_id: str, checkpoint: str, device: str | None = None):
        self.model_id = model_id
        self.checkpoint = checkpoint
        self.device = device
        self.model = None
        self.tokenizer = None

    def load(self) -> None:
        import torch

        from cortexo_ml.serving.weights import load_scratch_checkpoint
        state = load_scratch_checkpoint(self.checkpoint)
        self.model = state["model"].to(self.device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model.eval()
        tokenizer_path = state.get("tokenizer_path")
        if tokenizer_path:
            from cortexo_ml.tokenization.tokenizer import load_tokenizer
            self.tokenizer = load_tokenizer(tokenizer_path)

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        import torch

        if self.model is None:
            self.load()
        from cortexo_ml.scratch_model.generate import generate
        start = time.monotonic()
        ids = self.tokenizer.encode(prompt).ids if self.tokenizer else []
        if self.tokenizer is None:
            ids = [t for t in prompt.encode("utf-8")][:512]
        generated = generate(
            self.model,
            torch.as_tensor([ids], dtype=torch.long, device=self.model.device),
            max_new_tokens=config.max_new_tokens,
            temperature=config.temperature,
            top_k=config.top_k,
            top_p=config.top_p,
            eos_id=self.tokenizer.token_to_id("<eos>") if self.tokenizer else None,
        )
        text = self.tokenizer.decode(generated[0].tolist()) if self.tokenizer else str(generated[0].tolist())
        return GenerationResult(
            text=text,
            prompt_tokens=len(ids),
            generated_tokens=int(generated.shape[1]),
            latency_ms=_latency_ms(start),
            metadata={"backend": "scratch", "device": str(self.model.device), "checkpoint": self.checkpoint},
        )

    def metadata(self) -> dict[str, Any]:
        return {"model_id": self.model_id, "backend": "scratch", "checkpoint": self.checkpoint}


class HFBackend(ModelBackend):
    def __init__(self, model_id: str, pretrained: str, trust_remote_code: bool = False):
        self.model_id = model_id
        self.pretrained = pretrained
        self.trust_remote_code = trust_remote_code
        self.model = None
        self.tokenizer = None

    def load(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(self.pretrained, trust_remote_code=self.trust_remote_code)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(self.pretrained, trust_remote_code=self.trust_remote_code)

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        if self.model is None:
            self.load()
        start = time.monotonic()
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=config.max_new_tokens,
                do_sample=config.temperature > 0,
                temperature=config.temperature or None,
                top_p=config.top_p,
                top_k=config.top_k,
            )
        text = self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return GenerationResult(
            text=text,
            prompt_tokens=int(inputs["input_ids"].shape[1]),
            generated_tokens=int(outputs.shape[1] - inputs["input_ids"].shape[1]),
            latency_ms=_latency_ms(start),
            metadata={"backend": "hf", "model": self.pretrained},
        )

    def metadata(self) -> dict[str, Any]:
        return {"model_id": self.model_id, "backend": "hf", "pretrained": self.pretrained}


class ONNXBackend(HFBackend):
    """ONNX Runtime wrapper; falls back to HF if onnxruntime missing."""

    def __init__(self, model_id: str, onnx_path: str, pretrained: str | None = None):
        super().__init__(model_id, pretrained or model_id)
        self.onnx_path = onnx_path

    def load(self) -> None:
        from transformers import AutoTokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.pretrained)
        try:
            import onnxruntime as ort
            import numpy as np

            self.session = ort.InferenceSession(self.onnx_path)
            self.ort = ort
        except ImportError:
            self.session = None
            super().load()

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        if getattr(self, "session", None) is None:
            return super().generate(prompt, config)
        start = time.monotonic()
        tokens = self.tokenizer([prompt], return_tensors="np")
        feed = {self.session.get_inputs()[0].name: tokens["input_ids"]}
        logits = self.session.run(None, feed)[0]
        idx = int(logits[0, -1, :].argmax())
        text = self.tokenizer.decode([idx], skip_special_tokens=True)
        return GenerationResult(text=text, prompt_tokens=int(tokens["input_ids"].shape[1]), generated_tokens=1, latency_ms=_latency_ms(start), metadata={"backend": "onnx"})


class QuantizedBackend(HFBackend):
    """Wraps an INT8/INT4 quantized checkpoint the same way as HF."""

    def __init__(self, model_id: str, quantized_path: str, precision: str = "int8"):
        super().__init__(model_id, quantized_path)
        self.precision = precision

    def metadata(self) -> dict[str, Any]:
        return {"model_id": self.model_id, "backend": "quantized", "precision": self.precision, "path": self.pretrained}


# ---- System technique wrappers ----

class RAGBackend(ModelBackend):
    def __init__(self, base: ModelBackend, retriever):
        self.base = base
        self.retriever = retriever

    def load(self) -> None:
        self.base.load()

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        context = self.retriever.search(prompt, k=5)
        rag_prompt = "Relevant repository context:\n" + "\n".join(f"--- {c.path} ---\n{c.text[:1500]}" for c in context.chunks) + "\n\nQuery:\n" + prompt
        result = self.base.generate(rag_prompt, config)
        result.metadata["rag"] = {"chunks": [c.chunk_id for c in context.chunks]}
        return result

    def metadata(self) -> dict[str, Any]:
        return {"backend": "RAG", "base": self.base.metadata()}


class AgentBackend(ModelBackend):
    def __init__(self, base: ModelBackend, agent_factory):
        self.base = base
        self.agent_factory = agent_factory

    def load(self) -> None:
        self.base.load()

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        agent = self.agent_factory(self.base)
        record = agent.run(repo="unknown", task=prompt)
        result = GenerationResult(
            text=str(record.to_record()),
            prompt_tokens=None,
            generated_tokens=None,
            latency_ms=record.elapsed_seconds * 1000,
            metadata={"backend": "agent", "agentRunId": record.run_id},
        )
        return result

    def metadata(self) -> dict[str, Any]:
        return {"backend": "agent-wrapper", "base": self.base.metadata()}


class RouterBackend(ModelBackend):
    def __init__(self, candidates: dict[str, ModelBackend], router):
        self.candidates = candidates
        self.router = router

    def load(self) -> None:
        for backend in self.candidates.values():
            backend.load()

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        from cortexo_ml.routing.features import extract_features
        from cortexo_ml.routing.rules import CandidateModel

        cand_models = [
            CandidateModel(model_id=mid, quality=0.5, latency_ms=1000, ram_mb=2048, vram_mb=0, context_length=4096)
            for mid in self.candidates
        ]
        features = extract_features(prompt)
        decision = self.router.decide(features, cand_models)
        backend = self.candidates[decision["selectedModel"]]
        result = backend.generate(prompt, config)
        result.metadata["router"] = decision
        return result

    def metadata(self) -> dict[str, Any]:
        return {"backend": "router", "candidates": list(self.candidates)}