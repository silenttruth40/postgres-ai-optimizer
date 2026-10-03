from __future__ import annotations

from typing import Any

import psycopg

from backend.database import get_connection
from privacy.hashing import is_safe_identifier

ALLOWED_TABLES = {"customers", "orders", "products", "transactions", "order_items"}
ALLOWED_COLUMNS = {
    "customer_id",
    "name",
    "email",
    "phone",
    "address",
    "created_at",
    "order_id",
    "amount",
    "status",
    "product_id",
    "sku",
    "category",
    "price",
    "order_item_id",
    "quantity",
    "unit_price",
    "transaction_id",
    "method",
}


def list_indexes(conn: psycopg.Connection) -> list[tuple[str, tuple[str, ...]]]:
    sql = """
    SELECT
        t.relname AS table_name,
        i.relname AS index_name,
        array_agg(a.attname ORDER BY k.ordinality) AS columns
    FROM pg_class t
    JOIN pg_index x ON t.oid = x.indrelid
    JOIN pg_class i ON i.oid = x.indexrelid
    JOIN LATERAL unnest(x.indkey) WITH ORDINALITY AS k(attnum, ordinality) ON true
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public' AND t.relkind = 'r' AND NOT x.indisprimary
    GROUP BY t.relname, i.relname
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    out = []
    for row in rows:
        cols = row["columns"] if isinstance(row, dict) else row[2]
        table = row["table_name"] if isinstance(row, dict) else row[0]
        out.append((table, tuple(cols)))
    return out


def validate_candidate(candidate: dict[str, Any]) -> None:
    kind = candidate.get("type")
    if kind in {"CREATE_INDEX", "CREATE_COMPOSITE_INDEX"}:
        table = candidate.get("table") or ""
        columns = candidate.get("columns") or []
        if table not in ALLOWED_TABLES or not is_safe_identifier(table):
            raise ValueError(f"Refusing index on unknown table {table}")
        if not columns or not all(c in ALLOWED_COLUMNS and is_safe_identifier(c) for c in columns):
            raise ValueError("Refusing index with invalid columns")
    if kind == "UPDATE_STATISTICS":
        table = candidate.get("table") or ""
        if table not in ALLOWED_TABLES:
            raise ValueError("Refusing ANALYZE on unknown table")
    if kind == "REWRITE_QUERY":
        sql = (candidate.get("rewritten_sql") or "").strip().lower()
        if not sql.startswith("select"):
            raise ValueError("Rewrite must be a SELECT")
    if kind == "PARTITION":
        raise ValueError("Partitioning is not auto-applied")


def apply_candidate(conn: psycopg.Connection, candidate: dict[str, Any]) -> str | None:
    kind = candidate.get("type")
    if kind == "NO_CHANGE":
        return None
    if kind == "PARTITION":
        raise ValueError("Partitioning is estimated only and not applied")
    validate_candidate(candidate)
    undo = None
    with conn.cursor() as cur:
        if kind in {"CREATE_INDEX", "CREATE_COMPOSITE_INDEX"}:
            ddl = candidate.get("sql")
            if not ddl or not ddl.lower().startswith("create index"):
                raise ValueError("Invalid index DDL")
            cur.execute(ddl)
            name = ddl.split()[5] if "IF NOT EXISTS" in ddl.upper() else ddl.split()[2]
            # CREATE INDEX IF NOT EXISTS idx ON ...
            parts = ddl.split()
            if "EXISTS" in parts:
                name = parts[parts.index("EXISTS") + 1]
            else:
                name = parts[2]
            undo = f"DROP INDEX IF EXISTS {name}"
        elif kind == "UPDATE_STATISTICS":
            cur.execute(f"ANALYZE {candidate['table']}")
        elif kind == "JOIN_STRATEGY":
            session_sql = candidate.get("session_sql") or "SET enable_nestloop = off"
            cur.execute(session_sql.replace("SET LOCAL", "SET"))
            undo = "SET enable_nestloop = on"
        elif kind == "REWRITE_QUERY":
            return None
    return undo


def revert(conn: psycopg.Connection, undo_sql: str | None) -> None:
    if not undo_sql:
        return
    with conn.cursor() as cur:
        cur.execute(undo_sql)
