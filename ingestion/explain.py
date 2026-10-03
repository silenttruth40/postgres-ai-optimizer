from typing import Any

try:
    import psycopg
except Exception:
    psycopg = None

from ingestion.query_parser import parse_explain_json


def is_safe_select(sql: str) -> bool:
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    forbidden = (
        "insert ",
        "update ",
        "delete ",
        "drop ",
        "alter ",
        "create ",
        "truncate ",
        "grant ",
        "revoke ",
        "copy ",
        "vacuum ",
        "call ",
        "do ",
    )
    if any(token in lowered for token in forbidden):
        return False
    return lowered.startswith("select") or lowered.startswith("with")


def explain_analyze(conn: Any, sql: str) -> dict[str, Any]:
    if not is_safe_select(sql):

        raise ValueError("Only read-only SELECT/CTE statements can be explained")
    with conn.cursor() as cur:
        cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}")
        row = cur.fetchone()
    if not row:
        raise ValueError("EXPLAIN returned no rows")
    payload = next(iter(row.values())) if isinstance(row, dict) else row[0]
    return payload


def collect_plan(conn: Any, sql: str):
    payload = explain_analyze(conn, sql)
    return parse_explain_json(payload)

