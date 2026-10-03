from __future__ import annotations

from pathlib import Path

from backend.config import get_settings
from backend.database import get_connection

SCALES = {
    "tiny": {"customers": 400, "products": 80, "orders": 1600, "items": 3200, "txns": 2000},
    "small": {"customers": 5000, "products": 1000, "orders": 25000, "items": 50000, "txns": 30000},
    "medium": {"customers": 20000, "products": 4000, "orders": 80000, "items": 160000, "txns": 100000},
    "large": {"customers": 50000, "products": 10000, "orders": 200000, "items": 400000, "txns": 300000},
}

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "demo" / "schema.sql"


def _count(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
        row = cur.fetchone()
    return int(row["n"] if isinstance(row, dict) else row[0])


def _apply_schema(conn) -> None:
    sql = SCHEMA_PATH.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)


def seed_if_needed(sandbox: bool = False) -> dict[str, int]:
    settings = get_settings()
    scale = SCALES.get(settings.demo_scale.lower(), SCALES["small"])
    with get_connection(sandbox=sandbox) as conn:
        _apply_schema(conn)
        try:
            n = _count(conn, "customers")
        except Exception:
            _apply_schema(conn)
            n = 0
        if n > 0:
            return {"customers": n, "seeded": 0, "sandbox": int(sandbox)}
        c, p, o, items, t = (
            scale["customers"],
            scale["products"],
            scale["orders"],
            scale["items"],
            scale["txns"],
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO customers (customer_id, name, email, phone, address, created_at)
                SELECT gs,
                       'Customer ' || gs,
                       'user' || gs || '@example.com',
                       '555-01' || lpad((gs % 10000)::text, 4, '0'),
                       gs || ' Demo Street',
                       NOW() - ((gs % 800) || ' days')::interval
                FROM generate_series(1, %s) gs
                """,
                (c,),
            )
            cur.execute(
                """
                INSERT INTO products (product_id, sku, name, category, price)
                SELECT gs,
                       'SKU-' || gs,
                       'Product ' || gs,
                       (ARRAY['electronics','home','grocery','fashion','sports'])[1 + (gs % 5)],
                       (5 + (gs % 490))::numeric
                FROM generate_series(1, %s) gs
                """,
                (p,),
            )
            cur.execute(
                """
                INSERT INTO orders (order_id, customer_id, amount, status, created_at)
                SELECT gs,
                       1 + ((gs * 1103515245 + 12345) % %s),
                       (10 + (gs % 990))::numeric,
                       (ARRAY['open','paid','shipped','cancelled'])[1 + (gs % 4)],
                       NOW() - ((gs % 400) || ' days')::interval
                FROM generate_series(1, %s) gs
                """,
                (c, o),
            )
            cur.execute(
                """
                INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price)
                SELECT gs,
                       1 + ((gs * 2654435761) % %s),
                       1 + ((gs * 2246822519) % %s),
                       1 + (gs % 5),
                       (5 + (gs % 200))::numeric
                FROM generate_series(1, %s) gs
                """,
                (o, p, items),
            )
            cur.execute(
                """
                INSERT INTO transactions (transaction_id, customer_id, amount, method, created_at)
                SELECT gs,
                       1 + ((gs * 1664525 + 1013904223) % %s),
                       (5 + (gs % 800))::numeric,
                       (ARRAY['card','ach','wallet','cash'])[1 + (gs % 4)],
                       NOW() - ((gs % 360) || ' days')::interval
                FROM generate_series(1, %s) gs
                """,
                (c, t),
            )
            cur.execute("ANALYZE")
        return {
            "customers": c,
            "products": p,
            "orders": o,
            "order_items": items,
            "transactions": t,
            "seeded": 1,
            "sandbox": int(sandbox),
        }


def init_both() -> dict:
    main = seed_if_needed(sandbox=False)
    sandbox = seed_if_needed(sandbox=True)
    return {"main": main, "sandbox": sandbox}


if __name__ == "__main__":
    print(init_both())
