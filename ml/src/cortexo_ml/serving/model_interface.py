from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class GenerationConfig:
    max_new_tokens: int = 256
    temperature: float = 0.2
    top_p: float = 0.95
    top_k: int = 50

@dataclass
class GenerationResult:
    text: str
    prompt_tokens: int | None
    generated_tokens: int | None
    latency_ms: float
    metadata: dict[str, Any]

class ModelBackend(ABC):
    @abstractmethod
    def load(self) -> None:
        ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        config: GenerationConfig,
    ) -> GenerationResult:
        ...

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        ...