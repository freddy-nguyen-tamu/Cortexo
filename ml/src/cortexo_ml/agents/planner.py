from __future__ import annotations

from dataclasses import dataclass, field

from cortexo_ml.common.schemas import PATCH_PLAN, validate_against_schema


@dataclass
class AgentTrace:
    run_id: str
    repo: str
    task: str
    events: list[dict] = field(default_factory=list)

    def add(self, event_type: str, **payload) -> None:
        self.events.append({"type": event_type, "data": payload})

    def to_record(self) -> dict:
        return {"runId": self.run_id, "repo": self.repo, "task": self.task, "events": self.events}


def make_plan_prompt(repo: str, task: str) -> str:
    return (
        f"You are a software engineering agent working in repository '{repo}'.\n"
        f"TASK: {task}\n\n"
        "Produce a bounded JSON PatchPlan matching this schema:\n"
        '{"summary": string, "steps": string[], "files": string[], "risk": string}\n'
    )


def parse_plan(text: str) -> dict:
    from cortexo_ml.common.schemas import extract_json_objects

    for candidate in extract_json_objects(text):
        validation = validate_against_schema(candidate, PATCH_PLAN)
        if validation.valid:
            return candidate
    # Fallback: mark attempts as one or fail.
    return {"summary": text.strip()[:200], "steps": [], "files": [], "risk": "unknown"}


def validate_plan(plan: dict) -> tuple[bool, list[str]]:
    validation = validate_against_schema(plan, PATCH_PLAN)
    return validation.valid, validation.errors