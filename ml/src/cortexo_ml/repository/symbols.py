from __future__ import annotations

import re
from dataclasses import dataclass, field

from cortexo_ml.repository.ast_parser import parse_source, fallback_scan, node_text

IMPORT_PATTERNS = [
    (re.compile(r"^\s*(?:import|from)\s+([\w.]+)", re.M), "py_import"),
    (re.compile(r"\(?import\s+(?:['\"])?([\w./]+)|from\s+(['\"])([\w./]+)(['\"])", re.M), "js_import"),
    (re.compile(r"^\s*import\s+(\w+)|^\s*package\s+([\w.]+)", re.M), "go_package"),
    (re.compile(r"^\s*use\s+([\w:]+)", re.M), "rs_use"),
    (re.compile(r"^\s*import\s+[\w.*]+\s+([\w.]+);", re.M), "java_import"),
]


@dataclass
class Symbol:
    name: str
    kind: str
    line: int
    end_line: int | None = None
    signature: str | None = None
    qualified: str | None = None


@dataclass
class ParsedFile:
    path: str
    language: str | None
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    has_test: bool = False
    endpoints: list[str] = field(default_factory=list)
    table_references: list[str] = field(default_factory=list)


NODE_KIND_TO_SYMBOL = {
    "function_definition": "function",
    "class_definition": "class",
    "method_definition": "method",
    "constructor_definition": "constructor",
    "attribute": "field",
}


def _extract_tree_symbols(text: str, path: str, ext: str) -> tuple[list[Symbol], list[str]]:
    parsed = parse_source(text, ext)
    if parsed is None:
        return [], []
    tree = parsed["tree"]
    symbols: list[Symbol] = []
    imports: list[str] = []
    for node in tree.root_node.children:
        _collect_symbols(node, text, path, "", symbols)
    return symbols, imports


def _collect_symbols(node, text: str, path: str, scope: str, out: list[Symbol]) -> None:
    kind = NODE_KIND_TO_SYMBOL.get(node.type)
    if kind:
        name_node = _name_of(node)
        if name_node is not None:
            name = node_text(name_node, text)
            qualified = f"{path}:{scope}{name}" if scope else f"{path}:{name}"
            line = node.start_point[0] + 1
            out.append(Symbol(name=name, kind=kind, line=line, end_line=node.end_point[0] + 1, qualified=qualified))
            scope = f"{scope}{name}."
    for child in node.children:
        _collect_symbols(child, text, path, scope, out)


def _name_of(node):
    for child in node.children:
        if child.type == "name" or child.type == "identifier":
            return child
    return None


def parse_file(path: str, content: str) -> ParsedFile:
    ext = "." + (path.rsplit(".", 1)[-1] if "." in path else "")
    parsed = parse_source(content, ext)
    symbols: list[Symbol] = []

    if parsed is not None:
        tree = parsed["tree"]
        _collect_symbols(tree.root_node, content, path, "", symbols)
    else:
        for hit in fallback_scan(content, ext):
            symbols.append(Symbol(name=hit["name"], kind=hit["kind"], line=hit["line"], signature=hit["signature"]))

    imports = _extract_imports(content, ext)
    has_test = _looks_like_test(path, symbols)
    endpoints = _extract_endpoints(content)
    table_refs = _extract_table_references(content)

    return ParsedFile(
        path=path,
        language=ext or None,
        symbols=symbols,
        imports=imports,
        has_test=has_test,
        endpoints=endpoints,
        table_references=table_refs,
    )


def _extract_imports(content: str, ext: str) -> list[str]:
    results: list[str] = []
    for pattern, kind in IMPORT_PATTERNS:
        if kind == "py_import" and ext in ("py", "pyi"):
            for m in pattern.finditer(content):
                results.append(m.group(1))
        elif kind == "js_import" and ext in ("js", "jsx", "ts", "tsx", "mjs", "cjs"):
            for m in pattern.finditer(content):
                results.append(m.group(3) or m.group(2) or "")
        elif kind == "go_package" and ext == "go":
            for m in pattern.finditer(content):
                results.append(m.group(1) or m.group(2))
        elif kind == "rs_use" and ext == "rs":
            for m in pattern.finditer(content):
                results.append(m.group(1))
        elif kind == "java_import" and ext == "java":
            for m in pattern.finditer(content):
                results.append(m.group(1))
    return [r.strip() for r in results if r and r.strip()]


def _looks_like_test(path: str, symbols: list[Symbol]) -> bool:
    lower = path.lower()
    if "test" in lower or "spec" in lower:
        return True
    return any("test" in (s.name or "").lower() for s in symbols[:20])


def _extract_endpoints(content: str) -> list[str]:
    endpoints = []
    for pattern in [
        re.compile(r"@(?:Get|Post|Put|Delete|Patch|RequestMapping|get|post|put|delete|patch)Mapping\(['\"]([^'\"]+)['\"]\)"),
        re.compile(r"(?:route|router)\.(?:get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]"),
    ]:
        endpoints.extend(pattern.findall(content))
    return endpoints


def _extract_table_references(content: str) -> list[str]:
    refs = []
    for m in re.finditer(
        r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE|INSERT INTO)\s+([A-Za-z_][A-Za-z0-9_]*)",
        content,
        re.I,
    ):
        refs.append(m.group(1))
    return list(dict.fromkeys(refs))