# Databricks notebook: 04_failure_taxonomy.py
# Failure taxonomy: failure kind x model x task type (+ retrieval/tool failure).
# Drives the "failures by model and task type" dashboard.

# Databricks notebook source
# MAGIC %md
# MAGIC # Failure taxonomy

from collections import Counter
import json, os

# 1) From PostgreSQL normalized runs (preferred).
from pyspark.sql import SparkSession
spark = SparkSession.getActiveSession()
PROPS = {"user": "cortexo", "password": "cortexo", "driver": "org.postgresql.Driver"}
tasks = spark.read.jdbc(
    "jdbc:postgresql://cortexo-eval.internal:5432/cortexo_eval",
    "task_runs", properties=PROPS,
)
fail = tasks.filter(tasks.passed.isNull() | (tasks.passed == False))  # noqa: E712
fail.createOrReplaceTempView("f")

taxonomy = spark.sql("""
  SELECT model_variant_id,
         task_type,
         metrics->>'failure_kind' AS failure_kind,
         count(*) AS n
  FROM f
  GROUP BY model_variant_id, task_type, metrics->>'failure_kind'
  ORDER BY n DESC
""")
taxonomy.coalesce(1).write.mode("overwrite").option("header", "true").csv(
    "/dbfs/cortexo/exports/failure_taxonomy.csv"
)

# 2) From retrieval_runs / agent_runs telemetry counts.
#    retrieval empty / retrieval wrong / tool error / sandbox timeout / policy.
data = {
    "failures": [
        r["metrics"] for r in tasks.select("metrics").collect() if r["metrics"]
    ],
}
counts = Counter()
for m in data["failures"]:
    kind = m.get("failure_kind")
    if kind:
        counts[kind] += 1
with open("/dbfs/cortexo/exports/failure_summary.json", "w") as fh:
    json.dump(dict(counts), fh, indent=2)

taxonomy.show(40, truncate=False)