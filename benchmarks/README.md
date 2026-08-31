# Cortexo Benchmark Suites

All suites follow the canonical evaluation task object from the blueprint:

```json
{
  "task_id": "...",
  "task_type": "bug_fix",
  "repository_snapshot_id": "...",
  "prompt": "...",
  "expected_behavior": "...",
  "allowed_tools": [],
  "test_command": "...",
  "compile_command": "...",
  "gold_files": [],
  "gold_patch": null,
  "ground_truth_findings": [],
  "timeout_seconds": 120
}
```

## Layout

```
benchmarks/
|-- fixtures/            synthetic repos, bug files, vulnerable toys, SQL dialect schemas
|-- tasks/               one JSON file per suite, each containing evaluation tasks
|-- hidden_tests/        hidden tests + graders (micro_codegen, synthetic_bugfix, polydb)
|-- suites/suites.json   suite registry and metric notes
```

## Suites

| Suite | Fixture | Metrics |
|---|---|---|
| micro-codegen | – | pass@1/pass@k, syntax, compile, hidden-test rate |
| synthetic-bugfix | `fixtures/bugs/range_util_buggy.py` | solved, regressions, patch size, attempts, time to repair |
| repo-understanding | `fixtures/repos/python-inventory`, `java-inventory` | file/symbol recall@k, dependency accuracy, citations |
| code-review | bugs + python-inventory | precision, recall, F1, line localization, severity accuracy |
| security-review | `fixtures/vulnerable/shop.py` | precision, recall, FP, CWE accuracy |
| polydb-swe | `fixtures/sql/{postgres,mysql,sqlserver,oracle,db2}` | parse, execute, expected rows, forbidden writes, dialect correctness, hallucinated objects, repair success |
| retrieval | python/java inventory fixtures | file/symbol recall@k, first-hit rank |
| agent-repair | bug fixtures | solved, tool calls, attempts, time to repair |
| context-strategy | python-inventory | quality x strategy x token budget |

## PolyDB-SWE

PolyDB-SWE evaluates whether models understand enterprise database dialects,
schemas, transactions, and repository/database relationships. Equivalent
synthetic schemas exist for PostgreSQL, MySQL, SQL Server, Oracle and Db2
(customer / project / task / invoice / audit_event). Task families:

generate dialect-correct SELECT, repair broken SQL, detect SQL injection,
migrate DDL between dialects, diagnose incorrect JOIN, identify transaction
isolation problems, explain stored procedures, repair JDBC/JPA mappings, choose
a useful index, identify hallucinated tables/columns, explain query-plan
differences, generate migration scripts.

## Integrity rules

- Hidden tests, gold patches and solutions never enter training corpora.
- Every task is scored using the same task object for every model.
- Every run records seed, hashes, generation settings and a run record
  (see blueprint "Model evaluation run record").

## Running locally

```bash
cd ml
python - <<'PY'
import json
from pathlib import Path
tasks = json.loads(Path("../benchmarks/tasks/repair-bugfix.json").read_text())
print(len(tasks), "tasks ready")
PY
```

Full execution flows through Spring `BenchmarkService` -> Python
`evaluation/runner.py` -> metric normalization in PostgreSQL.