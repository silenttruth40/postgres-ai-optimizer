from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionNode:
    node_type: str
    actual_time: float = 0.0
    actual_startup_time: float = 0.0
    actual_rows: int = 0
    actual_loops: int = 1
    plan_rows: int = 0
    plan_width: int = 0
    startup_cost: float = 0.0
    total_cost: float = 0.0
    relation: str | None = None
    alias: str | None = None
    index_name: str | None = None
    filter: str | None = None
    join_type: str | None = None
    join_filter: str | None = None
    hash_cond: str | None = None
    merge_cond: str | None = None
    index_cond: str | None = None
    rec_check: str | None = None
    shared_hit_blocks: int = 0
    shared_read_blocks: int = 0
    temp_read_blocks: int = 0
    temp_written_blocks: int = 0
    output: list[str] = field(default_factory=list)
    depth: int = 0
    children: list["ExecutionNode"] = field(default_factory=list)

    @property
    def exclusive_time(self) -> float:
        child_time = sum(child.actual_time for child in self.children)
        return max(self.actual_time - child_time, 0.0)

    @property
    def estimation_error(self) -> float:
        if self.plan_rows <= 0:
            return float(self.actual_rows)
        return abs(self.actual_rows - self.plan_rows) / max(self.plan_rows, 1)

    def flatten(self) -> list["ExecutionNode"]:
        nodes = [self]
        for child in self.children:
            nodes.extend(child.flatten())
        return nodes

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_type": self.node_type,
            "actual_time": self.actual_time,
            "actual_rows": self.actual_rows,
            "plan_rows": self.plan_rows,
            "total_cost": self.total_cost,
            "exclusive_time": self.exclusive_time,
            "estimation_error": self.estimation_error,
            "relation": self.relation,
            "alias": self.alias,
            "index_name": self.index_name,
            "filter": self.filter,
            "join_type": self.join_type,
            "shared_hit_blocks": self.shared_hit_blocks,
            "shared_read_blocks": self.shared_read_blocks,
            "depth": self.depth,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class PlanMetrics:
    execution_time_ms: float
    planning_time_ms: float
    rows: int
    shared_hit_blocks: int
    shared_read_blocks: int
    node_count: int
    seq_scans: int
    nested_loops: int
    sorts: int
    joins: int


@dataclass
class ParsedPlan:
    root: ExecutionNode
    metrics: PlanMetrics
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root.to_dict(),
            "metrics": self.metrics.__dict__,
        }
