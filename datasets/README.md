# Cortexo incremental data pipeline (local, CPU-only)

Run these steps in order. Every step writes to `datasets/interim/<step>/` and
the final step writes to `datasets/processed/code-v1/`.

```bash
cd ml
python -m cortexo_ml.data.collect   --source datasets/raw/cortexo-demo-code-v1 --output ../datasets/interim/collect
python -m cortexo_ml.data.clean     --input  ../datasets/interim/collect --output ../datasets/interim/clean
python -m cortexo_ml.data.deduplicate --input ../datasets/interim/clean --output ../datasets/interim/dedup
python -m cortexo_ml.tokenization.tokenize_corpus --corpus ../datasets/raw/cortexo-demo-code-v1 \
    --output ../datasets/interim/tokenized --vocab 20000
python -m cortexo_ml.data.split --input ../datasets/interim/dedup --output ../datasets/processed/code-v1
```

## Pipeline stages (mirrors the blueprint)

1. `collect` – enumerate files, apply license gate, skip binaries/generated/vendor.
2. `clean` – encoding normalization, CRLF/BOM normalization, whitespace rules.
3. `deduplicate` – exact hash dedup, then MinHash near-duplicate dedup.
4. `synthesize` – (optional) generate buggy pairs for the repair corpus.
5. `tokenize` – ByteLevel BPE over the cleaned corpus (train first if tokenizer is missing).
6. `split` – content-addressed train/validation/test split via recorded hashes.
7. `pack` – length-bounded sequence packing with document boundaries and loss masks.

## Versioning

The processed directory is content-addressed: `dataset_card.json` stores
`datasetSha256` over every included document hash so a rerun produces the same
identifier unless inputs change.

## Rules that are enforced by code

- Never include `benchmarks/` (solutions, hidden tests, target patches) in a
  training corpus. Excluded by path; see `datasets/manifests/exclusions.json`.
- No file may enter training without `permissionToTrain` being resolved in
  `datasets/manifests/sources.jsonl`.
- Run `secrets.scan_directory` before every indexing/training pass.