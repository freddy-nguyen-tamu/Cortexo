from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


@dataclass
class SchemaValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)


def _walk_required(schema: dict, data: object, path: str, errors: list[str]) -> None:
    if not isinstance(schema, dict):
        return
    schema_type = schema.get("type")
    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{path}.{key}: required field missing")
        props = schema.get("properties", {})
        for key, value in (data.items() if isinstance(data, dict) else []):
            if key in props:
                _walk_required(props[key], value, f"{path}.{key}", errors)
    elif isinstance(data, list) and schema_type == "array":
        item_schema = schema.get("items", {})
        for i, item in enumerate(data):
            _walk_required(item_schema, item, f"{path}[{i}]", errors)


def validate_against_schema(data: object, schema: dict) -> SchemaValidation:
    errors: list[str] = []
    if schema.get("type") == "object" and not isinstance(data, dict):
        return SchemaValidation(False, ["root must be an object"])
    _walk_required(schema, data, "$", errors)
    return SchemaValidation(valid=not errors, errors=errors)


PATCH_PLAN = {
    "type": "object",
    "required": ["summary", "steps", "files"],
    "properties": {
        "summary": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}},
        "files": {"type": "array", "items": {"type": "string"}},
        "risk": {"type": "string"},
    },
}

PATCH_RESULT = {
    "type": "object",
    "required": ["patch", "files_changed"],
    "properties": {
        "patch": {"type": "string"},
        "files_changed": {"type": "array", "items": {"type": "string"}},
        "tests_to_run": {"type": "array", "items": {"type": "string"}},
    },
}

REVIEW_RESULT = {
    "type": "object",
    "required": ["findings"],
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["file", "line", "severity", "category", "message", "confidence"],
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "severity": {"type": "string"},
                    "category": {"type": "string"},
                    "message": {"type": "string"},
                    "confidence": {"type": "number"},
                },
            },
        }
    },
}

SECURITY_RESULT = {
    "type": "object",
    "required": ["findings"],
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["file", "line", "severity", "category", "cwe", "expected_fix"],
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "severity": {"type": "string"},
                    "category": {"type": "string"},
                    "cwe": {"type": "string"},
                    "expected_fix": {"type": "string"},
                },
            },
        }
    },
}

REPOSITORY_ANSWER = {
    "type": "object",
    "required": ["answer", "citations"],
    "properties": {
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
        "confident": {"type": "boolean"},
    },
}

TOOL_CALL = {
    "type": "object",
    "required": ["tool", "arguments"],
    "properties": {
        "tool": {"type": "string"},
        "arguments": {"type": "object"},
        "thought": {"type": "string"},
    },
}

ROUTER_DECISION = {
    "type": "object",
    "required": ["selected_model", "scores"],
    "properties": {
        "selected_model": {"type": "string"},
        "scores": {"type": "object"},
        "fallback": {"type": "string"},
    },
}

SCHEMAS = {
    "PatchPlan": PATCH_PLAN,
    "PatchResult": PATCH_RESULT,
    "ReviewResult": REVIEW_RESULT,
    "SecurityResult": SECURITY_RESULT,
    "RepositoryAnswer": REPOSITORY_ANSWER,
    "ToolCall": TOOL_CALL,
    "RouterDecision": ROUTER_DECISION,
}


def extract_json_objects(text: str) -> list[object]:
    """Parse fenced/codeblock or embedded JSON objects from a generation."""
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        return [json.loads(block) for block in fenced if _try(json.loads, block)]

    decoder = json.JSONDecoder()
    results = []
    idx = 0
    while idx < len(text):
        try:
            obj, nxt = decoder.raw_decode(text, idx)
            results.append(obj)
            idx = nxt
        except json.JSONDecodeError:
            idx += 1
    return results


def parse_structured(text: str, schema_name: str) -> tuple[object | None, SchemaValidation, int]:
    """Return (parsed, validation, retries_used)."""
    schema = SCHEMAS.get(schema_name)
    if schema is None:
        return None, SchemaValidation(False, [f"unknown schema {schema_name}"]), 0

    attempts = 0
    for candidate in extract_json_objects(text):
        attempts += 1
        validation = validate_against_schema(candidate, schema)
        if validation.valid:
            return candidate, validation, attempts - 1
    return None, SchemaValidation(False, ["no valid JSON object matched schema"]), max(0, attempts - 1)


def _try(fn, *args):
    try:
        fn(*args)
        return True
    except Exception:
        return False


@dataclass
class StructuredOutputStats:
    raw_generations: int = 0
    valid_first_try: int = 0
    valid_after_retry: int = 0
    invalid_permanently: int = 0
    retries: list[int] = field(default_factory=list)

    @property
    def first_try_schema_success(self) -> float:
        return self.valid_first_try / max(1, self.raw_generations)

    @property
    def eventual_schema_success(self) -> float:
        return (self.valid_first_try + self.valid_after_retry) / max(1, self.raw_generations)

    @property
    def mean_retry_count(self) -> float:
        return sum(self.retries) / max(1, len(self.retries))


def record_structured_outcome(stats: StructuredOutputStats, validation: SchemaValidation, retries: int) -> None:
    stats.raw_generations += 1
    stats.retries.append(retries)
    if validation.valid:
        if retries == 0:
            stats.valid_first_try += 1
        else:
            stats.valid_after_retry += 1
    else:
        stats.invalid_permanently += 1