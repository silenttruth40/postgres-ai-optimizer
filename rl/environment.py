from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ACTIONS = [
    "NO_CHANGE",
    "CREATE_INDEX",
    "CREATE_COMPOSITE_INDEX",
    "REWRITE_QUERY",
    "UPDATE_STATISTICS",
    "JOIN_STRATEGY",
    "PARTITION",
]


@dataclass
class OptimizerState:
    query_complexity: float
    execution_time: float
    joins: float
    seq_scans: float
    indexes: float
    estimated_rows: float
    actual_rows: float
    buffer_reads: float
    buffer_hits: float
    sort_cost: float

    def vector(self) -> np.ndarray:
        return np.array(
            [
                self.query_complexity,
                np.log1p(self.execution_time),
                self.joins,
                self.seq_scans,
                self.indexes,
                np.log1p(self.estimated_rows),
                np.log1p(self.actual_rows),
                np.log1p(self.buffer_reads),
                np.log1p(self.buffer_hits),
                np.log1p(self.sort_cost),
            ],
            dtype=float,
        )


def state_from_plan(plan, sql: str, index_count: int = 0) -> OptimizerState:
    m = plan.metrics
    return OptimizerState(
        query_complexity=float(sql.lower().count("join") + sql.lower().count("group") + 1),
        execution_time=m.execution_time_ms,
        joins=float(m.joins),
        seq_scans=float(m.seq_scans),
        indexes=float(index_count),
        estimated_rows=float(plan.root.plan_rows),
        actual_rows=float(m.rows),
        buffer_reads=float(m.shared_read_blocks),
        buffer_hits=float(m.shared_hit_blocks),
        sort_cost=float(m.sorts),
    )
