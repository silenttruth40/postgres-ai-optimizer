from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.models import ParsedPlan
from optimizer.bottleneck_detector import Bottleneck
from optimizer.index_advisor import advise_indexes
from optimizer.join_optimizer import join_recommendations
from optimizer.query_rewriter import rewrite_candidates


@dataclass
class Candidate:
    candidate_id: str
    type: str
    table: str | None = None
    columns: list[str] = field(default_factory=list)
    sql: str | None = None
    rewritten_sql: str | None = None
    session_sql: str | None = None
    reason: str = ""
    confidence: float = 0.5
    sources: list[str] = field(default_factory=list)
    estimated: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "type": self.type,
            "table": self.table,
            "columns": self.columns,
            "sql": self.sql,
            "rewritten_sql": self.rewritten_sql,
            "session_sql": self.session_sql,
            "reason": self.reason,
            "confidence": round(self.confidence, 4),
            "sources": self.sources,
            "estimated": self.estimated,
        }


def generate_candidates(
    sql: str,
    plan: ParsedPlan,
    bottlenecks: list[Bottleneck],
    existing: list[tuple[str, tuple[str, ...]]] | None = None,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    idx = 1

    for rec in advise_indexes(sql, plan, bottlenecks, existing):
        kind = (
            "CREATE_COMPOSITE_INDEX"
            if len(rec.columns) > 1
            else "CREATE_INDEX"
        )

        candidates.append(
            Candidate(
                candidate_id=f"C{idx:03d}",
                type=kind,
                table=rec.table,
                columns=rec.columns,
                sql=rec.ddl,
                reason=rec.reason,
                confidence=rec.confidence,
                sources=["Heuristic"],
                estimated=True,
            )
        )
        idx += 1

    for rec in join_recommendations(plan, bottlenecks):
        candidates.append(
            Candidate(
                candidate_id=f"C{idx:03d}",
                type=rec["type"],
                session_sql=rec.get("session_sql"),
                reason=rec["reason"],
                confidence=rec["confidence"],
                sources=["Heuristic"],
                estimated=True,
            )
        )
        idx += 1

    for rec in rewrite_candidates(sql, bottlenecks):
        candidates.append(
            Candidate(
                candidate_id=f"C{idx:03d}",
                type=rec["type"],
                rewritten_sql=rec.get("rewritten_sql"),
                reason=rec["reason"],
                confidence=rec["confidence"],
                sources=[rec.get("source", "Heuristic")],
                estimated=True,
            )
        )
        idx += 1

    if any(
        b.type == "CARDINALITY_MISESTIMATION"
        for b in bottlenecks
    ):
        table = next(
            (b.relation for b in bottlenecks if b.relation),
            "orders",
        )

        candidates.append(
            Candidate(
                candidate_id=f"C{idx:03d}",
                type="UPDATE_STATISTICS",
                table=table,
                sql=f"ANALYZE {table}",
                reason="Refresh planner statistics after large estimation error",
                confidence=0.45,
                sources=["Heuristic"],
                estimated=True,
            )
        )
        idx += 1

    large_tables = {
        b.relation
        for b in bottlenecks
        if b.relation
        and b.type in {"MISSING_INDEX", "EXPENSIVE_JOIN"}
    }

    if "orders" in large_tables or "transactions" in large_tables:
        table = (
            "orders"
            if "orders" in large_tables
            else "transactions"
        )

        candidates.append(
            Candidate(
                candidate_id=f"C{idx:03d}",
                type="PARTITION",
                table=table,
                reason=(
                    f"Estimated: range partitioning {table} by "
                    "created_at may help time-window queries"
                ),
                confidence=0.35,
                sources=["Heuristic"],
                estimated=True,
                extra={"not_auto_applied": True},
            )
        )
        idx += 1

    candidates.append(
        Candidate(
            candidate_id=f"C{idx:03d}",
            type="NO_CHANGE",
            reason=(
                "Keep the current query and database configuration "
                "if no tested optimization improves performance."
            ),
            confidence=1.0,
            sources=["Safety fallback"],
            estimated=False,
            extra={
                "safe_fallback": True,
                "accept_if_no_improvement": True,
            },
        )
    )

    return candidates