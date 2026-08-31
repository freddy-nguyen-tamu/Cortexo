# Cortexo research database environment
# =====================================
# Uses docker-compose.research.yml at the repository root. Everything in this
# environment is for offline research and PolyDB-SWE fixtures. The public
# Cortexo deployment only depends on MongoDB + optional PostgreSQL (and Redis).

## Quick start

```bash
docker compose -f docker-compose.research.yml up -d mysql cassandra

# Enterprise databases behind compose profiles (pull latest official image
# guidance first; images and commands change often):
docker compose -f docker-compose.research.yml --profile sqlserver up -d
docker compose -f docker-compose.research.yml --profile oracle up -d
docker compose -f docker-compose.research.yml --profile db2 up -d
```

Seeds in `fixtures/sql/<dialect>/schema.sql` under `benchmarks/`.

## Testing entry points (blueprint section 75)

| Layer | Fixture |
|---|---|
| DB adapter | PostgreSQL fixture `infra/postgres/eval_schema.sql` |
| DB adapter | MySQL fixture `benchmarks/fixtures/sql/mysql/schema.sql` |
| DB adapter | SQL Server fixture `benchmarks/fixtures/sql/sqlserver/schema.sql` |
| DB adapter | Oracle fixture `benchmarks/fixtures/sql/oracle/schema.sql` |
| DB adapter | Db2 fixture `benchmarks/fixtures/sql/db2/schema.sql` |

## Notes

- Run `docker compose logs` to inspect slow-query logs for MySQL.
- Never point PolyDB-SWE evaluation writes at a real production schema.
- SQL Server/Oracle/Db2 are behind compose profiles on purpose: their official
  container images require acceptance of license terms and larger resource
  budgets.

## Databricks Free Edition

Databricks is a separate offline analytics workspace for corpus /
experiment profiling (`notebooks/databricks/*.py`). Cortexo's public site does
not depend on any Databricks endpoint.