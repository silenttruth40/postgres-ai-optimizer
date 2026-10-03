from __future__ import annotations

from typing import Any

from backend.models import ExecutionNode, ParsedPlan
from gnn.graph_builder import build_graph
from gnn.model import PlanGNN

_MODEL: PlanGNN | None = None


def generate_gnn_explanation(
    bottleneck_node: ExecutionNode,
    bottleneck_class: str,
    importance_pct: float,
    total_time: float,
) -> str:
    """Generate clear natural language explanation of the bottleneck from GNN analysis."""
    node_type = bottleneck_node.node_type
    rel = f" on table '{bottleneck_node.relation}'" if bottleneck_node.relation else ""
    time_share = (bottleneck_node.exclusive_time / max(total_time, 1e-6)) * 100

    if bottleneck_class == "SEQ_SCAN_UNINDEXED" or node_type == "Seq Scan":
        filter_clause = f" with filter condition: {bottleneck_node.filter}" if bottleneck_node.filter else ""
        return (
            f"GNN Execution Tree Analytics identified an unindexed sequential scan{rel} as the dominant bottleneck "
            f"(GNN Attention Saliency: {importance_pct:.1f}%). The engine scanned {bottleneck_node.actual_rows:,} raw rows "
            f"consuming {bottleneck_node.exclusive_time:.2f} ms ({time_share:.1f}% of total query time){filter_clause}. "
            f"Recommendation: Creating a supporting composite B-Tree index will convert this O(N) full table scan "
            f"into an O(log N) index seek, bypassing row filtering overhead."
        )
    elif bottleneck_class == "EXPENSIVE_JOIN" or "Join" in node_type or "Nested Loop" in node_type:
        join_type = bottleneck_node.join_type or node_type
        return (
            f"GNN Execution Tree Analytics flagged a high-cost join operator ({join_type}){rel} "
            f"(GNN Attention Saliency: {importance_pct:.1f}%). The operator processed {bottleneck_node.actual_rows:,} rows "
            f"over {bottleneck_node.actual_loops} loops, consuming {bottleneck_node.exclusive_time:.2f} ms. "
            f"Recommendation: Restructure join ordering or add foreign-key indexing on joined columns to eliminate repeated loops."
        )
    elif bottleneck_class == "SORT_MEMORY_SPILL" or node_type == "Sort":
        return (
            f"GNN Execution Tree Analytics detected an expensive sort operator "
            f"(GNN Attention Saliency: {importance_pct:.1f}%). Sorting {bottleneck_node.actual_rows:,} rows "
            f"took {bottleneck_node.exclusive_time:.2f} ms. "
            f"Recommendation: Pre-order with a composite index or narrow the SELECT column list to fit inside work_mem."
        )
    else:
        return (
            f"GNN Execution Tree Analytics localized performance degradation to {node_type}{rel} "
            f"(GNN Attention Saliency: {importance_pct:.1f}%), accounting for {bottleneck_node.exclusive_time:.2f} ms."
        )


def analyze_plan_graph(plan: ParsedPlan) -> dict[str, Any]:
    graph, features, nodes = build_graph(plan)
    model = _get_model(features.shape[1])
    edges = list(graph.edges())
    result = model.infer(features, edges)
    idx = result["bottleneck_index"]
    bottleneck_node = nodes[idx]

    importance_list = result["node_importance"]
    importance_pct = float(importance_list[idx] * 100) if idx < len(importance_list) else 50.0
    total_time = plan.metrics.execution_time_ms

    explanation = generate_gnn_explanation(
        bottleneck_node=bottleneck_node,
        bottleneck_class=result["bottleneck_class"],
        importance_pct=importance_pct,
        total_time=total_time,
    )

    result["bottleneck_node"] = {
        "node_type": bottleneck_node.node_type,
        "relation": bottleneck_node.relation,
        "actual_time": bottleneck_node.actual_time,
        "exclusive_time": bottleneck_node.exclusive_time,
        "actual_rows": bottleneck_node.actual_rows,
        "plan_rows": bottleneck_node.plan_rows,
        "filter": bottleneck_node.filter,
    }
    result["explanation"] = explanation
    result["attention_percent"] = round(importance_pct, 1)

    result["nodes"] = [
        {
            "id": i,
            "node_type": n.node_type,
            "relation": n.relation,
            "actual_time": round(n.actual_time, 2),
            "exclusive_time": round(n.exclusive_time, 2),
            "actual_rows": n.actual_rows,
            "plan_rows": n.plan_rows,
            "importance": round(result["node_importance"][i] * 100, 1),
            "is_bottleneck": (i == idx),
        }
        for i, n in enumerate(nodes)
    ]
    result["edges"] = [{"source": s, "target": t} for s, t in edges]
    return result


def _get_model(in_dim: int) -> PlanGNN:
    global _MODEL
    if _MODEL is None or _MODEL.in_dim != in_dim:
        _MODEL = PlanGNN(in_dim)
    return _MODEL
