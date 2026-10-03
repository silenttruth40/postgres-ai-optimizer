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
            cur.execute(
                f"SET statement_timeout = '{int(timeout)}s'"
            )

        return collect_plan(conn, sql)


def benchmark_candidate(
    sql: str,
    candidate: dict[str, Any],
) -> dict[str, Any]:
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

    bench_sql = (
        candidate.get("rewritten_sql")
        if kind == "REWRITE_QUERY"
        else sql
    )

    undo = None
    applied_to = "sandbox"

    try:
        try:
            conn_cm = get_connection(sandbox=True)
            conn = conn_cm.__enter__()
            applied_to = "sandbox"
        except Exception:
            conn_cm = get_connection(sandbox=False)
            conn = conn_cm.__enter__()
            applied_to = "production"

        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"SET statement_timeout = "
                    f"'{int(get_settings().benchmark_timeout_seconds)}s'"
                )

            undo = apply_candidate(conn, candidate)

            optimized_plan = collect_plan(conn, bench_sql)
            optimized = _metrics(optimized_plan)

            revert(conn, undo)
        finally:
            conn_cm.__exit__(None, None, None)

    except Exception as exc:
        try:
            if undo:
                with get_connection(sandbox=(applied_to == "sandbox")) as conn:
                    revert(conn, undo)
        except Exception:
            pass

        return {
            "baseline": baseline,
            "optimized": None,
            "improvement_percent": None,
            "validation_status": "BENCHMARK_FAILED",
            "applied_to": applied_to,
            "error": str(exc),
        }

    base_t = baseline["execution_time_ms"]
    opt_t = optimized["execution_time_ms"]

    improvement = (
        ((base_t - opt_t) / base_t) * 100
        if base_t
        else 0.0
    )
    speedup_factor = round(base_t / opt_t, 2) if (opt_t and opt_t > 0) else 1.0

    base_hits = baseline.get("shared_hit_blocks", 0)
    opt_hits = optimized.get("shared_hit_blocks", 0)
    hit_diff = base_hits - opt_hits

    base_reads = baseline.get("shared_read_blocks", 0)
    opt_reads = optimized.get("shared_read_blocks", 0)
    read_diff = base_reads - opt_reads

    write_overhead = 0.0
    storage_mb = 0.0
    if kind in {"CREATE_INDEX", "CREATE_COMPOSITE_INDEX"}:
        cols_count = len(candidate.get("columns") or [1])
        write_overhead = round(1.2 + 0.4 * cols_count, 2)
        rows_n = baseline.get("rows") or 25000
        storage_mb = round(max((rows_n * (12 + 8 * cols_count)) / (1024 * 1024), 0.5), 2)
    elif kind == "PARTITION":
        write_overhead = 0.8
        storage_mb = 0.0

    updated_sql = candidate.get("rewritten_sql") or candidate.get("sql")

    if improvement > 5:
        status = "VALIDATED"
    elif improvement >= -5:
        improvement = 0.0
        status = "NEUTRAL"
    else:
        return {
            "baseline": baseline,
            "optimized": optimized,
            "improvement_percent": 0.0,
            "speedup_factor": speedup_factor,
            "hit_diff": hit_diff,
            "read_diff": read_diff,
            "validation_status": "NO_CHANGE",
            "applied_to": applied_to,
            "candidate_rejected": True,
            "original_improvement_percent": round(improvement, 2),
            "write_latency_overhead_ms": write_overhead,
            "storage_overhead_mb": storage_mb,
            "updated_sql": updated_sql,
            "error": (
                "The tested optimization was slower than the baseline "
                "and was rejected."
            ),
        }

    return {
        "baseline": baseline,
        "optimized": optimized,
        "improvement_percent": round(improvement, 2),
        "speedup_factor": speedup_factor,
        "hit_diff": hit_diff,
        "read_diff": read_diff,
        "validation_status": status,
        "applied_to": applied_to,
        "write_latency_overhead_ms": write_overhead,
        "storage_overhead_mb": storage_mb,
        "updated_sql": updated_sql,
    }