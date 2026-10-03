from __future__ import annotations

from backend.models import ParsedPlan
from optimizer.bottleneck_detector import Bottleneck


def join_recommendations(plan: ParsedPlan, bottlenecks: list[Bottleneck]) -> list[dict]:
    recs = []
    nested = [b for b in bottlenecks if b.type == "NESTED_LOOP"]
    if nested:
        recs.append(
            {
                "type": "JOIN_STRATEGY",
                "reason": "Expensive nested loop; prefer a hash join when both sides are large",
                "session_sql": "SET enable_nestloop = off",
                "confidence": 0.6,
            }
        )
    expensive_joins = [b for b in bottlenecks if b.type == "EXPENSIVE_JOIN"]
    if expensive_joins and not recs:
        recs.append(
            {
                "type": "JOIN_STRATEGY",
                "reason": "Large join intermediate results; supporting indexes on join keys should reduce join cost",
                "session_sql": None,
                "confidence": 0.55,
            }
        )
    return recs
