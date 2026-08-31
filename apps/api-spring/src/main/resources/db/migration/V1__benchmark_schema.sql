CREATE TABLE IF NOT EXISTS benchmark_suite (
  id VARCHAR(128) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  version VARCHAR(64) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS benchmark_task (
  id VARCHAR(128) PRIMARY KEY,
  suite_id VARCHAR(128) NOT NULL REFERENCES benchmark_suite(id),
  task_type VARCHAR(64) NOT NULL,
  repository_snapshot_id VARCHAR(128),
  difficulty VARCHAR(32),
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS benchmark_run (
  id VARCHAR(128) PRIMARY KEY,
  task_id VARCHAR(128) NOT NULL REFERENCES benchmark_task(id),
  model_variant_id VARCHAR(128) NOT NULL,
  experiment_id VARCHAR(128),
  seed INTEGER NOT NULL,
  status VARCHAR(32) NOT NULL,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS metric_value (
  id BIGSERIAL PRIMARY KEY,
  benchmark_run_id VARCHAR(128) NOT NULL REFERENCES benchmark_run(id),
  metric_name VARCHAR(128) NOT NULL,
  metric_value DOUBLE PRECISION NOT NULL,
  unit VARCHAR(64),
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);