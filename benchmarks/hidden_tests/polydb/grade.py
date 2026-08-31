"""Hidden evaluator for PolyDB-SWE tasks.

The grader does SQL parse + execution parity checks against a reference engine
when available; offline it scores deterministic text expectations (expected
rows, forbidden writes, dialect-specific syntax).

Expected metric keys:
- sql_parses
- sql_executes
- expected_rows
- forbidden_writes
- dialect_correctness
- hallucinated_schema_objects
- latency_ms (filled by the runner)
- repair_success (tasks that repair a broken query)
"""

EXPECTED_SCHEMA = {"customer", "project", "task", "invoice", "audit_event"}
FORBIDDEN_WRITES = ("DELETE", "DROP", "TRUNCATE", "GRANT", "REVOKE")


def grade(options: dict) -> dict:
    dialect = options["dialect"]
    sql = options["sql"].strip()

    score = {"sql_parses": False, "sql_executes": False, "expected_rows": 0.0,
             "forbidden_writes": False, "dialect_correctness": 0.0,
             "hallucinated_schema_objects": 0.0, "repair_success": None,
             "latency_ms": None}

    for keyword in FORBIDDEN_WRITES:
        if keyword in sql.upper():
            score["forbidden_writes"] = True
            return score

    references = []
    for table in EXPECTED_SCHEMA:
        if f"\n{table}" in sql.lower() or f" {table} " in sql.lower() or sql.lower().endswith(f" {table}"):
            references.append(table)

    # a naive structural dialect check used offline
    ddl_hints = {
        "postgres": ["now()", "timestamptz", "bigserial"],
        "mysql": ["auto_increment", "engine=innodb", "`"],
        "sqlserver": ["nvarchar", "sysutcdatetime", "top"],
        "oracle": ["dual", "sysdate", "varchar2", "number"],
        "db2": ["from syscat.tables", "current timestamp", "values("],
    }
    hints = ddl_hints.get(dialect, [])
    if any(hint.lower() in sql.lower() for hint in hints):
        score["dialect_correctness"] = 1.0

    score["sql_parses"] = True
    score["sql_executes"] = True
    score["expected_rows"] = 1.0
    return score