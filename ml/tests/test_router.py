from cortexo_ml.routing.router import Router
from cortexo_ml.routing.features import TaskFeatures
from cortexo_ml.routing.rules import CandidateModel


def test_router_decide_fast_path():
    router = Router()
    features = TaskFeatures(
        prompt="implement merge_dicts",
        task_type="code_generation",
        repo_size="small",
        retrieval_confidence=0.0,
        estimated_context_tokens=120,
        tools_required=False,
        available_ram_mb=4096,
        available_vram_mb=0,
        latency_target_ms=8000,
        quality_target=0.7,
    )
    candidates = [
        CandidateModel(model_id="scratch9m", quality=0.5, ram_mb=512, vram_mb=0),
        CandidateModel(model_id="scratch70m", quality=0.8, ram_mb=2048, vram_mb=0),
    ]
    decision = router.decide(features, candidates)
    assert decision["selectedModel"]
    assert decision["taskFeatures"]["taskType"] == "code_generation"
    assert len(decision["candidates"]) == 2
    assert "ruleBasedPick" in decision