from __future__ import annotations

def reward(improvement_percent: float, index_columns: int = 0, rewrite: bool = False) -> float:
    index_cost_penalty = 0.15 * index_columns
    complexity_penalty = 0.05 if rewrite else 0.0
    return float(improvement_percent) / 100.0 - index_cost_penalty - complexity_penalty
