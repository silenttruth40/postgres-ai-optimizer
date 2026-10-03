from __future__ import annotations

import re


def rewrite_candidates(sql: str) -> list[dict]:
    text = sql.strip()
    recs: list[dict] = []
    if re.search(r"select\s+\*", text, re.I):
        rewritten = re.sub(
            r"select\s+\*",
            "SELECT order_id, customer_id, amount, status, created_at",
            text,
            count=1,
            flags=re.I,
        )
        recs.append(
            {
                "type": "REWRITE_QUERY",
                "reason": "Avoid SELECT * to reduce tuple width during sort/scan",
                "rewritten_sql": rewritten,
                "confidence": 0.55,
            }
        )
    if re.search(r"where exists\s*\(", text, re.I):
        rewritten = """
SELECT DISTINCT c.customer_id, c.name
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
WHERE o.amount > 500
""".strip()
        recs.append(
            {
                "type": "REWRITE_QUERY",
                "reason": "Rewrite correlated EXISTS as an explicit join",
                "rewritten_sql": rewritten,
                "confidence": 0.58,
            }
        )
    return recs
