from __future__ import annotations

from typing import Any

from backend.models import ExecutionNode, ParsedPlan, PlanMetrics

SUPPORTED_NODES = {
    "Seq Scan",
    "Index Scan",
    "Index Only Scan",
    "Bitmap Heap Scan",
    "Bitmap Index Scan",
    "Nested Loop",
    "Hash Join",
    "Merge Join",
    "Sort",
    "Aggregate",
    "HashAggregate",
    "Gather",
    "Gather Merge",
    "Limit",
    "Materialize",
    "Hash",
    "Result",
    "Unique",
    "WindowAgg",
    "Subquery Scan",
    "CTE Scan",
}


def parse_explain_json(payload: Any) -> ParsedPlan:
    if isinstance(payload, list):
        if not payload:
            raise ValueError("Empty EXPLAIN result")
        payload = payload[0]
    if not isinstance(payload, dict) or "Plan" not in payload:
        raise ValueError("Invalid EXPLAIN JSON: missing Plan")
    root = _parse_node(payload["Plan"], depth=0)
    nodes = root.flatten()
    metrics = PlanMetrics(
        execution_time_ms=float(payload.get("Execution Time") or root.actual_time),
        planning_time_ms=float(payload.get("Planning Time") or 0.0),
        rows=int(root.actual_rows),
        shared_hit_blocks=sum(n.shared_hit_blocks for n in nodes),
        shared_read_blocks=sum(n.shared_read_blocks for n in nodes),
        node_count=len(nodes),
        seq_scans=sum(1 for n in nodes if n.node_type == "Seq Scan"),
        nested_loops=sum(1 for n in nodes if "Nested Loop" in n.node_type),
        sorts=sum(1 for n in nodes if n.node_type == "Sort"),
        joins=sum(1 for n in nodes if "Join" in n.node_type or "Nested Loop" in n.node_type),
    )
    return ParsedPlan(root=root, metrics=metrics, raw=payload)


def _parse_node(raw: dict[str, Any], depth: int) -> ExecutionNode:
    buffers = raw.get("Shared Hit Blocks") is not None
    node = ExecutionNode(
        node_type=str(raw.get("Node Type") or "Unknown"),
        actual_time=float(raw.get("Actual Total Time") or 0.0),
        actual_startup_time=float(raw.get("Actual Startup Time") or 0.0),
        actual_rows=int(raw.get("Actual Rows") or 0),
        actual_loops=int(raw.get("Actual Loops") or 1),
        plan_rows=int(raw.get("Plan Rows") or 0),
        plan_width=int(raw.get("Plan Width") or 0),
        startup_cost=float(raw.get("Startup Cost") or 0.0),
        total_cost=float(raw.get("Total Cost") or 0.0),
        relation=raw.get("Relation Name"),
        alias=raw.get("Alias"),
        index_name=raw.get("Index Name"),
        filter=raw.get("Filter") or raw.get("Rows Removed by Filter") and str(raw.get("Filter")),
        join_type=raw.get("Join Type"),
        join_filter=raw.get("Join Filter"),
        hash_cond=raw.get("Hash Cond"),
        merge_cond=raw.get("Merge Cond"),
        index_cond=raw.get("Index Cond"),
        rec_check=raw.get("Recheck Cond"),
        shared_hit_blocks=int(raw.get("Shared Hit Blocks") or 0) if buffers or "Shared Hit Blocks" in raw else 0,
        shared_read_blocks=int(raw.get("Shared Read Blocks") or 0),
        temp_read_blocks=int(raw.get("Temp Read Blocks") or 0),
        temp_written_blocks=int(raw.get("Temp Written Blocks") or 0),
        output=list(raw.get("Output") or []),
        depth=depth,
        children=[_parse_node(child, depth + 1) for child in raw.get("Plans") or []],
    )
    if raw.get("Filter") is not None:
        node.filter = str(raw.get("Filter"))
    return node
