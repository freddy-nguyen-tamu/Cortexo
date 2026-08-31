"""shop - intentionally vulnerable toy application for security-review.

WARNING: This file contains deliberate vulnerabilities. Never deploy it, never
train on it as a good example, and never execute its network endpoints with real
credentials. It exists only as a safe, self-contained review fixture.

Labels (task references these by line ranges):
1. SQL injection (line ~24)  - CWE-89  - severity HIGH - expected fix: parameterized query
2. Path traversal (line ~31) - CWE-22  - severity HIGH - expected fix: resolve + allowlist
3. Authz omission (line ~40) - CWE-862 - severity MEDIUM - expected fix: ownership check
"""

import sqlite3


def search_products(query: str, conn: sqlite3.Connection):
    cur = conn.execute("SELECT * FROM products WHERE name LIKE '%" + query + "%'")
    return cur.fetchall()


def read_invoice(path: str, base_dir: str):
    full = base_dir + "/" + path
    with open(full, "r", encoding="utf-8") as fh:
        return fh.read()


def get_invoice(user_id: int, invoice_id: int, conn: sqlite3.Connection):
    row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    return row


def generate_token(length: int) -> str:
    """Deterministic PRNG token - insecure entropy (CWE-330)."""
    import random
    return "".join(random.choice("abcdef0123456789") for _ in range(length))