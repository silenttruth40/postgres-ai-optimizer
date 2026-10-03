from __future__ import annotations

from backend.models import ParsedPlan
from gnn.graph_builder import build_graph
from gnn.model import PlanGNN

_MODEL: PlanGNN | None = None


def analyze_plan_graph(plan: ParsedPlan) -> dict:
    graph, features, nodes = build_graph(plan)
    model = _get_model(features.shape[1])
    edges = list(graph.edges())
    result = model.infer(features, edges)
    idx = result["bottleneck_index"]
    node = nodes[idx]
    result["bottleneck_node"] = {
        "node_type": node.node_type,
        "relation": node.relation,
        "actual_time": node.actual_time,
        "actual_rows": node.actual_rows,
    }
    result["nodes"] = [
        {
            "id": i,
            "node_type": n.node_type,
            "relation": n.relation,
            "actual_time": n.actual_time,
            "actual_rows": n.actual_rows,
            "importance": result["node_importance"][i],
        }
        for i, n in enumerate(nodes)
    ]
    result["edges"] = [{"source": s, "target": t} for s, t in edges]
    return result


def _get_model(in_dim: int) -> PlanGNN:
    global _MODEL
    if _MODEL is None or _MODEL.w1.shape[0] != in_dim:
        _MODEL = PlanGNN(in_dim)
    return _MODEL
