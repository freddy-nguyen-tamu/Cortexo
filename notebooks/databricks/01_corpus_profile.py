# Databricks notebook: 01_corpus_profile.py
# Offline corpus analysis on Databricks Free Edition. Exports compact Parquet /
# CSV / JSON summaries for MongoDB/PostgreSQL visualization. Cortexo's public
# site does NOT depend on these commands.

# Databricks notebook source
# MAGIC %md
# MAGIC # Corpus profile
# MAGIC Files, languages, licenses, file sizes, dedup rates from the code-v1 corpus.

import json
import os
from collections import Counter
from pathlib import Path

ROOT = "/dbfs/cortexo/datasets/processed/code-v1"  # mount your corpus on DBFS

def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]

# Simulated/real manifests. Replace with the real manifest path.
manifests = load_jsonl(os.path.join(ROOT, "manifest.jsonl"))

languages = Counter()
licenses = Counter()
size_buckets = Counter()
total_chars = 0
documents = len(manifests)

for doc in manifests:
    languages[doc.get("language", "unknown")] += 1
    licenses[doc.get("license", "unknown")] += 1
    chars = doc.get("chars", 0)
    total_chars += chars
    bucket = "0-1k" if chars < 1000 else ("1k-10k" if chars < 10000 else "10k+")
    size_buckets[bucket] += 1

profile = {
    "documents": documents,
    "totalChars": total_chars,
    "languages": dict(languages),
    "licenses": dict(licenses),
    "fileSizeBuckets": dict(size_buckets),
    "dedupRate": {"note": "computed during exact/near dedup; see interim/dedup"},
}

out_dir = "/dbfs/cortexo/exports"
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "corpus_profile.json"), "w") as fh:
    json.dump(profile, fh, indent=2)

df = spark.createDataFrame(
    [(k, v) for k, v in profile["languages"].items()], ["language", "count"]
)
df.coalesce(1).write.mode("overwrite").option("header", "true").csv(
    "/dbfs/cortexo/exports/corpus_profile.csv"
)

print(json.dumps(profile, indent=2))
display(spark.read.csv("/dbfs/cortexo/exports/corpus_profile.csv", header=True, inferSchema=True))