import argparse
import collections
import json
import re
from pathlib import Path

from tokenizers import Tokenizer

from cortexo_ml.tokenization.tokenizer import build_bpe_tokenizer, save_tokenizer, load_tokenizer

IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\([^)]*\))?")
INDENT_RE = re.compile(r"^[ \t]+|[ \t]+$")
FUNC_RE = re.compile(r"\b(?:def|function|func|fn|public\s+\w+\s+\w+|private\s+\w+\s+\w+)\s+\w+\s*\(")

_LANGUAGE_HINTS = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".tsx": "typescriptreact",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
}


def _language(path: str) -> str:
    return _LANGUAGE_HINTS.get(Path(path).suffix, "other")


def _extract_identifiers(text: str) -> list[str]:
    return IDENTIFIER_RE.findall(text)


def tokenizer_metrics(tokenizer: Tokenizer, sample_files: list[tuple[str, str]]):
    """Compute tokenization comparison metrics on a small labeled sample.

    sample_files: list of (path, content) pairs.
    Returns tokens/char, tokens/line, tokens/function, identifier
    fragmentation, indentation fragmentation, compression by language.
    """
    total_chars = 0
    total_lines = 0
    total_functions = 0
    total_tokens = 0
    fragmented_identifiers = 0
    total_identifiers = 0
    indent_fragmented = 0
    indent_runs = 0
    compression: dict[str, list[float]] = collections.defaultdict(list)

    for path, content in sample_files:
        lang = _language(path)
        ids = tokenizer.encode(content)
        tokens = ids.tokens
        n = len(tokens)
        total_tokens += n
        total_chars += len(content)
        total_lines += content.count("\n") + 1
        total_functions += len(list(FUNC_RE.finditer(content)))

        compression[lang].append(len(content) / max(1, n))

        for ident in _extract_identifiers(content):
            total_identifiers += 1
            encoded = tokenizer.encode(ident).tokens
            if len(encoded) > 1:
                fragmented_identifiers += 1

        indent_runs_in_content = 0
        for line in content.splitlines():
            m = INDENT_RE.match(line)
            if m and m.group(0):
                indent_runs_in_content += 1
        indent_runs += indent_runs_in_content

    return {
        "total_tokens": total_tokens,
        "tokens_per_char": total_tokens / max(1, total_chars),
        "tokens_per_line": total_tokens / max(1, total_lines),
        "tokens_per_function": total_tokens / max(1, total_functions),
        "identifier_fragmentation": fragmented_identifiers / max(1, total_identifiers),
        "indentation_fragmentation_estimate": indent_runs / max(1, total_tokens),
        "compression_by_language": {k: sum(v) / len(v) for k, v in compression.items()},
    }


def main():
    parser = argparse.ArgumentParser(description="Train a Cortexo byte-level BPE tokenizer")
    parser.add_argument("--corpus", nargs="+", required=True, help="corpus files to train on")
    parser.add_argument("--vocab-size", type=int, default=16384)
    parser.add_argument("--min-frequency", type=int, default=2)
    parser.add_argument("--output", default="artifacts/tokenizers/code-bpe-16k/tokenizer.json")
    parser.add_argument("--metrics-output", default="artifacts/tokenizers/code-bpe-16k/metrics.json")
    parser.add_argument("--sample-dir", default=None, help="optional directory for metric estimation")
    parser.add_argument("--resume", default=None, help="existing tokenizer.json to measure instead of training")
    args = parser.parse_args()

    if args.resume:
        tokenizer = load_tokenizer(args.resume)
    else:
        tokenizer = build_bpe_tokenizer(
            args.corpus,
            vocab_size=args.vocab_size,
            min_frequency=args.min_frequency,
        )
        save_tokenizer(tokenizer, args.output)

    metrics = {}
    if args.sample_dir:
        samples = []
        for path in list(Path(args.sample_dir).glob("**/*"))[:100]:
            if path.is_file() and path.suffix in _LANGUAGE_HINTS:
                samples.append((str(path), path.read_text(errors="replace")))
        metrics = tokenizer_metrics(tokenizer, samples)

    report = {
        "vocab_size": tokenizer.get_vocab_size(),
        "special_tokens": len(tokenizer.token_to_id) - tokenizer.get_vocab_size()
        if hasattr(tokenizer, "token_to_id") else None,
        "metrics": metrics,
    }
    if args.metrics_output:
        out = Path(args.metrics_output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()