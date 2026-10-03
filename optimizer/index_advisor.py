from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.models import ParsedPlan
from optimizer.bottleneck_detector import Bottleneck
from privacy.hashing import is_safe_identifier

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass
class IndexCandidate:
    table: str
    columns: list[str]
    reason: str
    confidence: float
    from_scan: bool = False

    @property
    def name(self) -> str:
        cols = "_".join(self.columns)[:40]
        return f"idx_{self.table}_{cols}"[:63]

    @property
    def ddl(self) -> str:
        cols = ", ".join(self.columns)
        return f"CREATE INDEX IF NOT EXISTS {self.name} ON {self.table} ({cols})"


def advise_indexes(
    sql: str,
    plan: ParsedPlan,
    bottlenecks: list[Bottleneck],
    existing: list[tuple[str, tuple[str, ...]]] | None = None,
) -> list[IndexCandidate]:
    existing = existing or []
    existing_set = {(table, cols) for table, cols in existing}
    hints = _sql_index_hints(sql)
    seq_tables = {
        b.relation
        for b in bottlenecks
        if b.type == "MISSING_INDEX" and b.relation
    }
    for node in plan.root.flatten():
        if node.node_type == "Seq Scan" and node.relation:
            seq_tables.add(node.relation)

    out: list[IndexCandidate] = []
    for hint in hints:
        if hint.table not in seq_tables and not hint.from_scan:
            # still useful if SQL clearly filters/joins these columns
            hint.confidence *= 0.85
        key = (hint.table, tuple(hint.columns))
        if key in existing_set or any(key == (c.table, tuple(c.columns)) for c in out):
            continue
        if not is_safe_identifier(hint.table) or not all(is_safe_identifier(c) for c in hint.columns):
            continue
        out.append(hint)

    if not out:
        fallback_candidates = []

        for table in seq_tables:
            if table == "orders":
                fallback_candidates.append(
                    IndexCandidate(
                        table="orders",
                        columns=["created_at", "customer_id"],
                        reason="Sequential scan with time filter and customer join",
                        confidence=0.82,
                        from_scan=True,
                    )
                )
            elif table == "transactions":
                fallback_candidates.append(
                    IndexCandidate(
                        table="transactions",
                        columns=["created_at", "customer_id"],
                        reason="Sequential scan on timestamp-filtered transactions",
                        confidence=0.8,
                        from_scan=True,
                    )
                )
            elif table == "customers":
                fallback_candidates.append(
                    IndexCandidate(
                        table="customers",
                        columns=["email"],
                        reason="Equality lookup on customers.email",
                        confidence=0.78,
                        from_scan=True,
                    )
                )
            elif table == "order_items":
                fallback_candidates.append(
                    IndexCandidate(
                        table="order_items",
                        columns=["order_id", "product_id"],
                        reason="Join keys used without supporting indexes",
                        confidence=0.74,
                        from_scan=True,
                    )
                )
            elif table == "products":
                fallback_candidates.append(
                    IndexCandidate(
                        table="products",
                        columns=["category"],
                        reason="Filter on products.category during join",
                        confidence=0.7,
                        from_scan=True,
                    )
                )

        for candidate in fallback_candidates:
            key = (candidate.table, tuple(candidate.columns))

            if key in existing_set:
                continue

            if any(
                key == (c.table, tuple(c.columns))
                for c in out
            ):
                continue

            if not is_safe_identifier(candidate.table):
                continue

            if not all(is_safe_identifier(c) for c in candidate.columns):
                continue

            out.append(candidate)
    return out

def _sql_index_hints(sql: str) -> list[IndexCandidate]:
    text = re.sub(r"\s+", " ", sql.strip())
    lowered = text.lower()
    candidates: list[IndexCandidate] = []

    def add(table: str, columns: list[str], reason: str, confidence: float) -> None:
        if table and columns:
            candidates.append(IndexCandidate(table, columns, reason, confidence))

    if "from customers" in lowered and "email" in lowered:
        add("customers", ["email"], "Equality/filter on customers.email", 0.86)
    if "join orders" in lowered or "from orders" in lowered:
        cols = []
        if "o.created_at" in lowered or "orders.created_at" in lowered or "created_at" in lowered:
            cols.append("created_at")
        if "customer_id" in lowered:
            cols.append("customer_id")
        if "status" in lowered and "from orders" in lowered:
            cols = ["status", "created_at"] if "created_at" in lowered else ["status"]
        if cols:
            add("orders", cols, "Filtering/joining orders on " + ", ".join(cols), 0.88)
    if "from transactions" in lowered:
        cols = ["created_at"]
        if "customer_id" in lowered:
            cols.append("customer_id")
        add("transactions", cols, "Range filter on transactions.created_at", 0.84)
    if "join order_items" in lowered or "from order_items" in lowered:
        add("order_items", ["order_id", "product_id"], "Join keys on order_items", 0.8)
    if "join products" in lowered and "category" in lowered:
        add("products", ["category"], "Filter on products.category", 0.72)
    return candidates
