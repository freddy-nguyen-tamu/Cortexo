from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

LANGUAGE_PARSER_MAP: dict[tuple[str, ...], str] = {
    (".py", ".pyi"): "python",
    (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"): "javascript",
    (".go",): "go",
    (".rs",): "rust",
    (".java",): "java",
    (".c", ".h"): "c",
    (".cc", ".cpp", ".hpp"): "cpp",
    (".cs",): "csharp",
    (".rb",): "ruby",
    (".php",): "php",
    (".sql",): "sql",
}


def tree_sitter_language(extension: str):
    try:
        from tree_sitter import Language, Parser  # noqa: F401
    except ImportError:
        return None
    ext = extension.lower()
    for suffixes, lang_name in LANGUAGE_PARSER_MAP.items():
        if ext in suffixes:
            try:
                module = _import_tree_sitter_binding(lang_name)
                if module is not None:
                    return Language(module.language())
            except Exception:
                return None
    return None


def _import_tree_sitter_binding(lang_name: str):
    binding_names = {
        "python": "tree_sitter_python",
        "javascript": "tree_sitter_javascript",
        "go": "tree_sitter_go",
        "rust": "tree_sitter_rust",
        "java": "tree_sitter_java",
        "c": "tree_sitter_c",
        "cpp": "tree_sitter_cpp",
        "csharp": "tree_sitter_c_sharp",
        "ruby": "tree_sitter_ruby",
        "php": "tree_sitter_php",
    }
    try:
        import importlib

        return importlib.import_module(binding_names[lang_name])
    except ImportError:
        return None


def parse_source(text: str, extension: str) -> dict[str, Any] | None:
    """Parse source text into a Tree-sitter tree dict (or None when unavailable)."""
    language = tree_sitter_language(extension)
    if language is None:
        return None
    try:
        from tree_sitter import Parser
    except ImportError:
        return None
    parser = Parser(language)
    tree = parser.parse(bytes(text, "utf-8"))
    return {"tree": tree, "language": extension.lower()}


def walk_tree(node):
    yield node
    cursor = node.walk()
    cursor.goto_first_child()
    while True:
        for sub in walk_tree(cursor.node):
            yield sub
        if not cursor.goto_next_sibling():
            break


def node_text(node, text: str) -> str:
    return text[node.start_byte:node.end_byte]


# --- fallback regex browser used when tree-sitter bindings are missing ---

FALLBACK_PATTERNS = {
    "python": [
        ("function", re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?:->\s*[^:]+)?:", re.M)),
        ("class", re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^)]*\))?\s*:", re.M)),
    ],
    "java": [
        ("method", re.compile(r"^\s*(?:public|private|protected|static|final|abstract|synchronized|default|\s)*[\w<>.?\[\]]+\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+\w+)?\s*\{", re.M)),
        ("class", re.compile(r"^\s*(?:public|private|protected|abstract|final|\s)*class\s+(\w+)", re.M)),
        ("interface", re.compile(r"^\s*(?:public|private|protected|\s)*interface\s+(\w+)", re.M)),
    ],
    "javascript": [
        ("function", re.compile(r"^(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>|async\s+function\s+(\w+))", re.M)),
        ("class", re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)", re.M)),
    ],
    "go": [
        ("function", re.compile(r"^func\s+(?:\([^)]*\)\s+)?(?:\w+\.)?([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)),
    ],
    "rust": [
        ("function", re.compile(r"^(?:pub\s+)?fn\s+([a-z_][a-z0-9_]*)\s*\(", re.M)),
    ],
    "sql": [
        ("table_reference", re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)),
    ],
}


FALLBACK_SUFFIX_TO_KEY = {
    ".py": "python",
    ".pyi": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".sql": "sql",
}


def fallback_scan(text: str, extension: str) -> list[dict]:
    ext = extension.lower()
    key = FALLBACK_SUFFIX_TO_KEY.get(ext, ext.lstrip("."))
    patterns = FALLBACK_PATTERNS.get(key)
    if not patterns:
        return []
    scans = []
    for kind, pattern in patterns:
        for m in pattern.finditer(text):
            name = next((g for g in m.groups() if g), None)
            if name is None:
                continue
            line = text.count("\n", 0, m.start()) + 1
            scans.append({"kind": kind, "name": name, "line": line, "signature": m.group(0).strip()})
    return scans