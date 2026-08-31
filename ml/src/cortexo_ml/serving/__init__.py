"""Model serving: backends, weights, quantization, stdio/jsonl/vLLM serving."""

from cortexo_ml.serving.model_interface import ModelBackend, GenerationConfig, GenerationResult
from cortexo_ml.serving.backends import EchoBackend, ScratchBackend, HFBackend, ONNXBackend, QuantizedBackend, RAGBackend, RouterBackend
from cortexo_ml.serving.weights import load_scratch_checkpoint, torch_safe_load_dict
from cortexo_ml.serving.quantization import quantize_with_torch, QuantizationReport, QUANTIZATION_LEVELS
from cortexo_ml.serving.stdio_server import stdio_loop, jsonl_inference_server, build_vllm_command

__all__ = [
    "ModelBackend",
    "GenerationConfig",
    "GenerationResult",
    "EchoBackend",
    "ScratchBackend",
    "HFBackend",
    "ONNXBackend",
    "QuantizedBackend",
    "RAGBackend",
    "RouterBackend",
    "load_scratch_checkpoint",
    "torch_safe_load_dict",
    "quantize_with_torch",
    "QuantizationReport",
    "QUANTIZATION_LEVELS",
    "stdio_loop",
    "jsonl_inference_server",
    "build_vllm_command",
]