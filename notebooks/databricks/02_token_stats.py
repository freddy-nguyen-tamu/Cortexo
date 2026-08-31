# Databricks notebook: 02_token_stats.py
# Token frequency, compression ratio, identifier fragmentation, tokenizer
# comparisons. Reads the tokenize_corpus metrics output
# (ml/src/cortexo_ml/tokenization/train_tokenizer.py --metrics-output).

# Databricks notebook source
# MAGIC %md
# MAGIC # Token statistics

import json
import os

METRICS = "/dbfs/cortexo/artifacts/tokenizers/code-bpe-16k/metrics.json"

def load(path):
    with open(path) as fh:
        return json.load(fh)

metrics = load(METRICS)

compression = metrics.get("compression_by_language", {})
top = sorted(metrics.get("top_tokens", {}).items(), key=lambda kv: -kv[1])[:50]

stat = {
    "vocabSize": metrics.get("vocab_size"),
    "corpusChars": metrics.get("corpus_chars"),
    "totalTokenCount": metrics.get("total_token_count"),
    "tokensPerChar": metrics.get("tokens_per_char"),
    "tokensPerLine": metrics.get("tokens_per_line"),
    "identifierFragmentation": metrics.get("identifier_fragmentation_ratio"),
    "compressionByLanguage": compression,
    "topTokens": top,
}

out_dir = "/dbfs/cortexo/exports"
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "token_stats.json"), "w") as fh:
    json.dump(stat, fh, indent=2, default=str)

# Parquet export of token frequencies for later scatter analysis.
from pyspark.sql import Row
rows = [Row(token=t, freq=c) for t, c in top]
spark.createDataFrame(rows).coalesce(1).write.mode("overwrite").parquet(
    "/dbfs/cortexo/exports/token_freq.parquet"
)

print(json.dumps(stat, indent=2, default=str))