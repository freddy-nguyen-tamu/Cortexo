# Databricks notebook: 03_experiment_analytics.py
# Quality vs latency / quality vs parameters / quality vs memory. Reads
# normalized task metrics from PostgreSQL via JDBC, exports compact tables.

# Databricks notebook source
# MAGIC %md
# MAGIC # Experiment analytics

from pyspark.sql import SparkSession

spark.jdbc = SparkSession.getActiveSession()

URL = "jdbc:postgresql://cortexo-eval.internal:5432/cortexo_eval"
PROPS = {"user": "cortexo", "password": "cortexo", "driver": "org.postgresql.Driver"}

runs = spark.read.jdbc(URL, "benchmark_runs", properties=PROPS)
tasks = spark.read.jdbc(URL, "task_runs", properties=PROPS)
hw = spark.read.jdbc(URL, "hardware_reports", properties=PROPS)

joined = runs.join(tasks, "run_id").join(hw, ["run_id", "model_variant_id"])
joined.createOrReplaceTempView("b")

# Quality vs latency: per (model_variant_id, task_type) summary.
summary = spark.sql("""
  SELECT model_variant_id,
         task_type,
         avg(CASE WHEN passed THEN 1.0 ELSE 0.0 END)        AS quality,
         percentile_approx(latency_ms, 0.5)                 AS p50_latency_ms,
         avg(params)                                        AS params,
         avg(memory_mb)                                     AS memory_mb
  FROM b
  GROUP BY model_variant_id, task_type
  ORDER BY quality DESC
""")

out_dir = "/dbfs/cortexo/exports"
summary.coalesce(1).write.mode("overwrite").option("header", "true").csv(
    f"{out_dir}/quality_vs_latency.csv"
)
summary.coalesce(1).write.mode("overwrite").parquet(f"{out_dir}/quality_vs_latency.parquet")
summary.show(truncate=False)

# Adapter comparison table (LoRA vs QLoRA vs DPO vs INT4) for the model registry.
adapters = spark.sql("""
  SELECT model_variant_id, passed, run_id
  FROM b
  WHERE model_variant_id IN ('qwen05b-base','qwen05b-dapt-codev1',
                             'qwen05b-lora-r16-swev1','qwen05b-qlora-r16-swev1')
""")
adapters.show(20, truncate=False)