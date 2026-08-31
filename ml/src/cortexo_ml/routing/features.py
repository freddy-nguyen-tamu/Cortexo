from __future__ import annotations

from dataclasses import dataclass, field

TASK_TYPE_KEYWORDS = {
    "repair": ["repair", "fix", "bug", "failing", "fails", "broken", "exception", "error"],
    "security": ["security", "injection", "traversal", "xss", "ssrf", "vulnerability", "cwe"],
    "review": ["review", "findings", "code review", "pull request"],
    "sql": ["sql", "query", "schema", "join", "transaction", "index", "migration", "stored procedure"],
    "repo_qa": ["where is", "what calls", "what test", "which module", "does this"]
    + ["defined", "invoked", "covered", "depends", "imports"],
    "infill": ["fill", "complete the function", "complete this", "implement body"],
    "explain": ["explain", "why", "what does", "how does"],
}


def infer_task_type(prompt: str) -> str:
    lower = prompt.lower()
    for task_type, keywords in TASK_TYPE_KEYWORDS.items():
        if any(k in lower for k in keywords):
            return task_type
    return "general"


def estimate_repo_size(chunks: int, files: int) -> str:
    if files <= 30 and chunks <= 300:
        return "small"
    if files <= 150 and chunks <= 2000:
        return "medium"
    return "large"


def retrieval_confidence(query: str, retrieval_trace: list[dict] | None) -> float:
    if not retrieval_trace:
        return 0.0
    top = 0.0
    for stage in retrieval_trace:
        candidates = stage.get("candidates")
        if isinstance(candidates, list) and candidates:
            top = max(top, float(candidates[0].get("score", 0.0)))
    if not retrieval_trace:
        return 0.0
    stages = [s for s in retrieval_trace if s.get("stage") == "context compression"]
    if stages and stages[0].get("usedTokens") == 0:
        return 0.0
    # Normalized confidence proxy from top RRF/rerank scores.
    return min(1.0, top / 5.0)


@dataclass
class TaskFeatures:
    prompt: str
    task_type: str
    repo_size: str
    retrieval_confidence: float
    estimated_context_tokens: int
    tools_required: bool
    available_ram_mb: int
    available_vram_mb: int
    latency_target_ms: int
    quality_target: float
    historical_scores: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        return {
            "prompt": self.prompt[:200],
            "taskType": self.task_type,
            "repoSize": self.repo_size,
            "retrievalConfidence": round(self.retrieval_confidence, 3),
            "contextTokens": self.estimated_context_tokens,
            "toolsRequired": self.tools_required,
            "availableRamMb": self.available_ram_mb,
            "availableVramMb": self.available_vram_mb,
            "latencyTargetMs": self.latency_target_ms,
            "qualityTarget": self.quality_target,
        }


def extract_features(
    prompt: str,
    repo_stats: dict | None = None,
    retrieval_trace: list[dict] | None = None,
    tool_requirement: bool = False,
    available_ram_mb: int = 4096,
    available_vram_mb: int = 0,
    latency_target_ms: int = 8000,
    quality_target: float = 0.7,
    historical_scores: dict | None = None,
) -> TaskFeatures:
    repo_stats = repo_stats or {}
    return TaskFeatures(
        prompt=prompt,
        task_type=infer_task_type(prompt),
        repo_size=estimate_repo_size(repo_stats.get("chunkCount", 0), repo_stats.get("fileCount", 0)),
        retrieval_confidence=retrieval_confidence(prompt, retrieval_trace),
        estimated_context_tokens=int(repo_stats.get("chunkCount", 0) * 150),
        tools_required=tool_requirement or infer_task_type(prompt) == "repair",
        available_ram_mb=available_ram_mb,
        available_vram_mb=available_vram_mb,
        latency_target_ms=latency_target_ms,
        quality_target=quality_target,
        historical_scores=historical_scores or {},
    )