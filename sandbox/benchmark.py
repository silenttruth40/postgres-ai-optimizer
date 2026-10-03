from __future__ import annotations

from typing import Any

from backend.config import get_settings
from backend.database import get_connection
from ingestion.explain import collect_plan, is_safe_select
from sandbox.manager import apply_candidate, revert, validate_candidate


def _metrics(parsed) -> dict[str, Any]:
    m = parsed.metrics
    return {
        "execution_time_ms": m.execution_time_ms,
        "planning_time_ms": m.planning_time_ms,
        "rows": m.rows,
        "shared_hit_blocks": m.shared_hit_blocks,
        "shared_read_blocks": m.shared_read_blocks,
        "source": "Measured",
    }


def run_query_metrics(sql: str, sandbox: bool = False):
    if not is_safe_select(sql):
        raise ValueError("Only SELECT statements can be benchmarked")
    timeout = get_settings().benchmark_timeout_seconds
    with get_connection(sandbox=sandbox) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET statement_timeout = '{int(timeout)}s'")
        return collect_plan(conn, sql)


def benchmark_candidate(sql: str, candidate: dict[str, Any]) -> dict[str, Any]:
    kind = candidate.get("type")
    baseline_plan = run_query_metrics(sql, sandbox=False)
    baseline = _metrics(baseline_plan)

    if kind in {None, "NO_CHANGE"}:
        return {
            "baseline": baseline,
            "optimized": baseline,
            "improvement_percent": 0.0,
            "validation_status": "NO_CHANGE",
            "applied_to": "none",
        }
    if kind == "PARTITION":
        return {
            "baseline": baseline,
            "optimized": None,
            "improvement_percent": None,
            "validation_status": "NOT_APPLIED_ESTIMATED",
            "applied_to": "none",
            "error": "Partitioning is not auto-applied; labeled Estimated only.",
        }

    try:
        validate_candidate(candidate)
    except ValueError as exc:
        return {
            "baseline": baseline,
            "optimized": None,
            "improvement_percent": None,
            "validation_status": "REJECTED",
            "applied_to": "none",
            "error": str(exc),
        }

    bench_sql = candidate.get("rewritten_sql") if kind == "REWRITE_QUERY" else sql
    undo = None
    try:
        with get_connection(sandbox=True) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SET statement_timeout = '{int(get_settings().benchmark_timeout_seconds)}s'")
            undo = apply_candidate(conn, candidate)
            optimized_plan = collect_plan(conn, bench_sql)
            optimized = _metrics(optimized_plan)
            revert(conn, undo)
    except Exception as exc:
        try:
            if undo:
                with get_connection(sandbox=True) as conn:
                    revert(conn, undo)
        except Exception:
            pass
        return {
            "baseline": baseline,
            "optimized": None,
            "improvement_percent": None,
            "validation_status": "SANDBOX_FAILED",
            "applied_to": "sandbox",
            "error": str(exc),
        }

    base_t = baseline["execution_time_ms"]
    opt_t = optimized["execution_time_ms"]
    improvement = ((base_t - opt_t) / base_t * 100) if base_t else 0.0
    if improvement > 5:
        status = "VALIDATED"
    elif improvement < -5:
        status = "REGRESSED"
    else:
        status = "NEUTRAL"
    return {
        "baseline": baseline,
        "optimized": optimized,
        "improvement_percent": round(improvement, 2),
        "validation_status": status,
        "applied_to": "sandbox",
    }
