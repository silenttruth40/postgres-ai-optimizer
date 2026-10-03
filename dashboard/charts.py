from __future__ import annotations


def metric_rows(metrics: dict) -> list[dict[str, str]]:
    return [
        {
            "Metric": "Execution time",
            "Value": f"{metrics.get('execution_time_ms', 0):.2f} ms",
        },
        {
            "Metric": "Planning time",
            "Value": f"{metrics.get('planning_time_ms', 0):.2f} ms",
        },
        {
            "Metric": "Rows",
            "Value": str(metrics.get("rows", 0)),
        },
        {
            "Metric": "Shared buffer hits",
            "Value": str(metrics.get("shared_hit_blocks", 0)),
        },
        {
            "Metric": "Shared buffer reads",
            "Value": str(metrics.get("shared_read_blocks", 0)),
        },
    ]


def benchmark_rows(
    baseline: dict | None,
    optimized: dict | None,
    improvement: float | None,
    status: str,
) -> list[dict[str, str]]:
    return [
        {
            "Metric": "Baseline execution time",
            "Value": (
                f"{(baseline or {}).get('execution_time_ms', 0):.2f} ms"
            ),
        },
        {
            "Metric": "Optimized execution time",
            "Value": (
                f"{(optimized or {}).get('execution_time_ms', 0):.2f} ms"
                if optimized
                else "n/a"
            ),
        },
        {
            "Metric": "Improvement",
            "Value": (
                "n/a"
                if improvement is None
                else f"{improvement:.2f}%"
            ),
        },
        {
            "Metric": "Validation status",
            "Value": status or "UNKNOWN",
        },
    ]