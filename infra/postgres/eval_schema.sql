-- Cortexo normalized evaluation analytics schema (PostgreSQL).
-- Mirrors the Flyway migration V1__benchmark_schema.sql in apps/api-spring.
-- For local/manual setup only; the app applies the Flyway migration.

CREATE TABLE IF NOT EXISTS benchmark_runs (
    id            BIGSERIAL PRIMARY KEY,
    run_id        TEXT NOT NULL UNIQUE,
    benchmark     TEXT NOT NULL,
    model_variant_id TEXT NOT NULL,
    seed          INTEGER NOT NULL DEFAULT 42,
    status        TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    metrics       JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS task_runs (
    id            BIGSERIAL PRIMARY KEY,
    run_id        TEXT NOT NULL REFERENCES benchmark_runs(run_id),
    task_id       TEXT NOT NULL,
    task_type     TEXT NOT NULL,
    model_variant_id TEXT NOT NULL,
    passed        BOOLEAN,
    latency_ms    INTEGER,
    tokens_in     INTEGER,
    tokens_out    INTEGER,
    output        TEXT,
    metrics       JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (run_id, task_id, model_variant_id)
);

CREATE TABLE IF NOT EXISTS hardware_reports (
    id            BIGSERIAL PRIMARY KEY,
    run_id        TEXT NOT NULL REFERENCES benchmark_runs(run_id),
    model_variant_id TEXT NOT NULL,
    provider      TEXT,
    gpu_name      TEXT,
    memory_mb     INTEGER,
    cpu_cores     INTEGER,
    params        BIGINT,
    UNIQUE (run_id, model_variant_id)
);

CREATE INDEX IF NOT EXISTS idx_task_runs_run ON task_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_task_runs_model ON task_runs(model_variant_id);
CREATE INDEX IF NOT EXISTS idx_benchmark_runs_recent ON benchmark_runs(model_variant_id, started_at DESC);