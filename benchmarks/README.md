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
|-- suites/grader_registry.json   evaluator-only executable-grading specs
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

## Executable grading path

`benchmarks/suites/grader_registry.json` maps a canonical `task_id` to an
evaluator-only grading spec. It is read straight from the repository, never
from model output, and it is never sent to a model:

```json
{
  "kind": "standalone_python",
  "candidateTargets": ["solution.py"],
  "test_command": ["pytest", "-q"],
  "compile_command": ["python3", "-m", "compileall", "-q", "."],
  "hiddenTests": ["hidden_tests/micro_codegen/test_merge_dicts.py"]
}
```

Grading flow (`ml/src/cortexo_ml/evaluation/`):

1. **candidate_extraction.py** — the untrusted model output is normalized into
   a `full_file` or `unified_diff` candidate without executing it. Diffs are
   allow-listed per task: absolute paths, `..` traversal, file
   creation/deletion, and any touch of `tests/`, `hidden_tests/`,
   `benches_hidden/` or VCS dirs are rejected before `git apply`.
2. **grader.py** — builds an ephemeral workspace, stages the fixture, applies
   the candidate, stages hidden tests (only AFTER generation), then runs the
   fixed sandbox COMPILE and TEST stages. Candidate code is never imported on
   the host.
3. **runner.py / API** — `POST /v1/evaluations/run` composes prompt -> trusted
   grader. The grader status (`PASS`, `COMPILE_FAIL`, `TEST_FAIL`,
   `SANDBOX_TIMEOUT`, `SANDBOX_POLICY`, `CANDIDATE_INVALID`, ...) is recorded.

Grading is gated by `CORTEXO_GRADER_ENABLED` and defaults to **off**
(`503` from the API when disabled). Hidden tests, gold patches and the
registry are never visible to the model, and candidate module code is only
ever executed inside the Docker sandbox.

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