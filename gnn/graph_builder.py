from __future__ import annotations

from typing import Any

import networkx as nx
import numpy as np

from backend.models import ExecutionNode, ParsedPlan

NODE_TYPES = [
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
    "Other",
]


def node_type_index(name: str) -> int:
    return NODE_TYPES.index(name) if name in NODE_TYPES else len(NODE_TYPES) - 1


def build_graph(plan: ParsedPlan) -> tuple[nx.DiGraph, np.ndarray, list[ExecutionNode]]:
    graph = nx.DiGraph()
    nodes = plan.root.flatten()
    for idx, node in enumerate(nodes):
        graph.add_node(idx, node_type=node.node_type, exclusive_time=node.exclusive_time)
    id_map = {id(node): i for i, node in enumerate(nodes)}
    for parent in nodes:
        for child in parent.children:
            graph.add_edge(id_map[id(child)], id_map[id(parent)])
    features = np.vstack([node_features(n, plan.metrics.execution_time_ms) for n in nodes])
    return graph, features, nodes


def node_features(node: ExecutionNode, total_time: float) -> np.ndarray:
    one_hot = np.zeros(len(NODE_TYPES), dtype=float)
    one_hot[node_type_index(node.node_type)] = 1.0
    total = max(total_time, 1e-6)
    numeric = np.array(
        [
            node.total_cost,
            node.actual_time,
            node.exclusive_time,
            node.actual_rows,
            node.plan_rows,
            node.shared_hit_blocks,
            node.shared_read_blocks,
            node.depth,
            node.estimation_error,
            node.exclusive_time / total,
        ],
        dtype=float,
    )
    numeric = np.log1p(np.abs(numeric))
    return np.concatenate([one_hot, numeric])
