from __future__ import annotations

from datetime import datetime, timezone

from backend.database import get_connection
from ingestion.catalog import DemoQuery
from ingestion.explain import collect_plan, is_safe_select


def collect(query: DemoQuery, sandbox: bool = False) -> dict:
    if not query.sql or not is_safe_select(query.sql):
        raise ValueError("Empty or unsupported SQL")
    with get_connection(sandbox=sandbox) as conn:
        parsed = collect_plan(conn, query.sql)
    return {
        "query_id": query.query_id,
        "sql": query.sql,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "plan": parsed,
        "metrics": parsed.metrics.__dict__,
    }
