from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoQuery:
    query_id: str
    title: str
    description: str
    problem_class: str
    sql: str


DEMO_QUERIES: dict[str, DemoQuery] = {
    "Q001": DemoQuery(
        query_id="Q001",
        title="Orders by customer and date",
        description="Filtered order lookup without a supporting composite index.",
        problem_class="MISSING_INDEX",
        sql="""
SELECT *
FROM orders
WHERE customer_id = 42
  AND created_at >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY created_at DESC;
""".strip(),
    ),
    "Q002": DemoQuery(
        query_id="Q002",
        title="Customer lookup by email",
        description="Equality filter on a potentially unindexed customer email column; also demonstrates privacy anonymization.",
        problem_class="SEQ_SCAN",
        sql="""
SELECT customer_id, name, email
FROM customers
WHERE email = 'user42@example.com';
""".strip(),
    ),
    "Q003": DemoQuery(
        query_id="Q003",
        title="Customers with many orders",
        description="Correlated subquery that can produce repeated work across customer rows.",
        problem_class="REWRITE",
        sql="""
SELECT c.customer_id, c.name
FROM customers c
WHERE (
    SELECT COUNT(*)
    FROM orders o
    WHERE o.customer_id = c.customer_id
) > 10;
""".strip(),
    ),
    "Q004": DemoQuery(
        query_id="Q004",
        title="Open orders sorted by amount",
        description="SELECT * with a status filter followed by a potentially expensive multi-column sort.",
        problem_class="SELECT_STAR_SORT",
        sql="""
SELECT *
FROM orders
WHERE status = 'open'
ORDER BY created_at DESC, amount DESC;
""".strip(),
    ),
    "Q005": DemoQuery(
        query_id="Q005",
        title="Customers with large orders",
        description="Correlated EXISTS subquery that can be analyzed for rewrite and join optimization.",
        problem_class="REWRITE",
        sql="""
SSELECT c.customer_id, c.name
FROM customers c
WHERE EXISTS (
    SELECT 1
    FROM orders o
    WHERE o.customer_id = c.customer_id
      AND o.amount > 500
);
""".strip(),
    ),
    "Q006": DemoQuery(
        query_id="Q006",
        title="Recent electronics line items",
        description="Multi-table join with date and category filters that can benefit from supporting indexes.",
        problem_class="JOIN",
        sql="""
SELECT o.order_id, p.name, oi.quantity, oi.unit_price
FROM orders o
JOIN order_items oi
    ON oi.order_id = o.order_id
JOIN products p
    ON p.product_id = oi.product_id
WHERE o.created_at >= CURRENT_DATE - INTERVAL '7 days'
  AND p.category = 'electronics';
}


def get_demo_query(
    query_id: str,
    sql: str | None = None,
) -> DemoQuery:
    if sql:
        base = DEMO_QUERIES.get(query_id)
        return DemoQuery(
            query_id=query_id,
            title=base.title if base else "Ad-hoc query",
            description=base.description if base else "User-supplied SELECT",
            problem_class=base.problem_class if base else "ADHOC",
            sql=sql.strip(),
        )

    if query_id not in DEMO_QUERIES:
        known = ", ".join(DEMO_QUERIES)
        raise KeyError(
            f"Unknown query_id {query_id}. Known: {known}"
        )

    return DEMO_QUERIES[query_id]