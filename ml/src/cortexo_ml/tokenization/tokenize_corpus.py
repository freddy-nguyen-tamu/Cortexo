import argparse
import json
from pathlib import Path

import numpy as np
import orjson
from tokenizers import Tokenizer

from cortexo_ml.tokenization.tokenizer import load_tokenizer


def tokenize_corpus(
    tokenizer: Tokenizer,
    corpus_dirs: list[str],
    output_npy: str,
    max_chars: int = 0,
    eos_id: int | None = None,
) -> dict:
    eos_id = eos_id if eos_id is not None else tokenizer.token_to_id("<eos>")

    tokens: list[int] = []
    doc_count = 0
    total_chars = 0

    for corpus_dir in corpus_dirs:
        for path in sorted(Path(corpus_dir).rglob("*")):
            if not path.is_file():
                continue
            if max_chars and total_chars >= max_chars:
                break
            try:
                text = path.read_text(errors="replace")
            except OSError:
                continue
            if not text.strip():
                continue
            ids = tokenizer.encode(text).ids
            tokens.extend(ids)
            if eos_id is not None:
                tokens.append(eos_id)
            doc_count += 1
            total_chars += len(text)

    arr = np.asarray(tokens, dtype=np.uint16)
    out = Path(output_npy)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(out, arr)

    return {
        "tokens": int(arr.size),
        "documents": doc_count,
        "chars": total_chars,
        "output": str(out),
    }


def main():
    parser = argparse.ArgumentParser(description="Tokenize a corpus to a uint16 .npy shard")
    parser.add_argument("--tokenizer", required=True, help="tokenizer.json path")
    parser.add_argument("--corpus", nargs="+", required=True)
    parser.add_argument("--output", required=True, help="output .npy path")
    parser.add_argument("--max-chars", type=int, default=0)
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args()

    tokenizer = load_tokenizer(args.tokenizer)
    report = tokenize_corpus(
        tokenizer,
        args.corpus,
        args.output,
        max_chars=args.max_chars,
    )

    if args.manifest:
        Path(args.manifest).write_bytes(
            orjson.dumps(report, option=orjson.OPT_INDENT_2)
        )
    print(json.dumps(report))


if __name__ == "__main__":
    main()