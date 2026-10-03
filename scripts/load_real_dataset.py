"""
Real-world dataset loader and high-volume realistic benchmark generator for PostgreSQL AI Optimizer.
Fulfills Problem Statement 4 requirement for real datasets across 4-5 tables with high row volume.

Usage:
    python scripts/load_real_dataset.py --mode realistic --rows 100000
    python scripts/load_real_dataset.py --mode olist --csv-dir ./data/olist/
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings
from backend.database import get_connection

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "demo" / "schema.sql"


def apply_schema(conn) -> None:
    print("Applying base schema (demo/schema.sql)...")
    sql = SCHEMA_PATH.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)


def generate_realistic_dataset(conn, target_orders: int = 100_000) -> dict[str, int]:
    """
    Generates a realistic enterprise-scale relational dataset with Power-Law (Zipfian)
    distributions and real-world skew across 5 tables:
      - customers
      - products
      - orders
      - order_items
      - transactions
    """
    num_customers = max(target_orders // 5, 5_000)
    num_products = max(target_orders // 20, 1_000)
    num_orders = target_orders
    num_items = int(target_orders * 2.2)
    num_txns = int(target_orders * 1.1)

    print(f"Generating realistic dataset: {num_customers:,} customers, {num_products:,} products, "
          f"{num_orders:,} orders, {num_items:,} items, {num_txns:,} transactions...")

    t0 = time.time()
    with conn.cursor() as cur:
        # 1. Clean existing tables if needed
        cur.execute("TRUNCATE TABLE transactions, order_items, orders, customers, products RESTART IDENTITY CASCADE;")

        # 2. Customers with realistic email domains and phone patterns
        print("  - Inserting customers...")
        cur.execute(
            """
            INSERT INTO customers (customer_id, name, email, phone, address, created_at)
            SELECT
                gs,
                'Customer ' || gs,
                'user' || gs || '@' || (ARRAY['gmail.com', 'enterprise.corp', 'yahoo.com', 'outlook.com', 'company.org'])[1 + mod(gs, 5)],
                '+1-555-' || lpad(mod(gs, 10000)::text, 4, '0'),
                (100 + mod(gs, 9000)) || ' Market Boulevard, Suite ' || mod(gs, 50),
                NOW() - (mod(gs, 1200) || ' days')::interval
            FROM generate_series(1, %s) gs;
            """,
            (num_customers,),
        )

        # 3. Products with realistic categories and price distribution
        print("  - Inserting products...")
        cur.execute(
            """
            INSERT INTO products (product_id, sku, name, category, price)
            SELECT
                gs,
                'SKU-' || upper(substring(md5(gs::text) from 1 for 8)),
                'Product ' || gs,
                (ARRAY['electronics', 'cloud_services', 'hardware', 'office_supplies', 'apparel'])[1 + mod(gs, 5)],
                ROUND((15.0 + mod(gs, 1200)::numeric * 1.35), 2)
            FROM generate_series(1, %s) gs;
            """,
            (num_products,),
        )

        # 4. Orders with realistic Pareto/Power-Law distribution (80/20 customer activity)
        print("  - Inserting orders with realistic customer skew...")
        cur.execute(
            """
            INSERT INTO orders (order_id, customer_id, amount, status, created_at)
            SELECT
                gs,
                CASE
                    WHEN mod(gs, 5) != 0 THEN 1 + mod(abs(gs::bigint * 1103515245 + 12345)::bigint, GREATEST(%s / 5, 1))
                    ELSE 1 + mod(abs(gs::bigint * 1103515245 + 12345)::bigint, %s)
                END,
                ROUND((20.0 + mod(abs(gs::bigint * 7919), 2500)::numeric), 2),
                (ARRAY['paid', 'open', 'shipped', 'cancelled', 'refunded'])[1 + mod(gs, 5)],
                NOW() - (mod(gs, 730) || ' days')::interval - (mod(gs, 86400) || ' seconds')::interval
            FROM generate_series(1, %s) gs;
            """,
            (num_customers, num_customers, num_orders),
        )

        # 5. Order items linking orders to products
        print("  - Inserting order items...")
        cur.execute(
            """
            INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price)
            SELECT
                gs,
                1 + mod(abs(gs::bigint * 2654435761)::bigint, %s),
                1 + mod(abs(gs::bigint * 2246822519)::bigint, %s),
                1 + mod(gs, 6),
                ROUND((10.0 + mod(gs, 350)::numeric), 2)
            FROM generate_series(1, %s) gs;
            """,
            (num_orders, num_products, num_items),
        )

        # 6. Transactions
        print("  - Inserting transactions...")
        cur.execute(
            """
            INSERT INTO transactions (transaction_id, customer_id, amount, method, created_at)
            SELECT
                gs,
                1 + mod(abs(gs::bigint * 1664525 + 1013904223)::bigint, %s),
                ROUND((15.0 + mod(gs, 2400)::numeric), 2),
                (ARRAY['credit_card', 'wire_transfer', 'ach', 'corporate_wallet'])[1 + mod(gs, 4)],
                NOW() - (mod(gs, 700) || ' days')::interval
            FROM generate_series(1, %s) gs;
            """,
            (num_customers, num_txns),
        )

        # 7. Update PostgreSQL Planner Statistics
        print("  - Running ANALYZE to refresh catalog statistics for PostgreSQL optimizer...")
        cur.execute("ANALYZE customers, products, orders, order_items, transactions;")

    elapsed = time.time() - t0
    print(f"Data generation completed in {elapsed:.2f}s!")
    return {
        "customers": num_customers,
        "products": num_products,
        "orders": num_orders,
        "order_items": num_items,
        "transactions": num_txns,
    }


def load_from_csv(conn, csv_dir: str) -> None:
    """Load real CSV files (e.g. from Olist Kaggle or custom exports)."""
    p = Path(csv_dir)
    if not p.exists():
        print(f"Error: Directory {csv_dir} does not exist.")
        return

    tables = ["customers", "products", "orders", "order_items", "transactions"]
    with conn.cursor() as cur:
        for t in tables:
            csv_file = p / f"{t}.csv"
            if csv_file.exists():
                print(f"Loading {csv_file} into {t}...")
                with open(csv_file, "r", encoding="utf-8") as f:
                    with cur.copy(f"COPY {t} FROM STDIN WITH (FORMAT csv, HEADER true)") as copy:
                        while data := f.read(8192):
                            copy.write(data)
                print(f"  - Loaded {t} successfully.")
        cur.execute("ANALYZE;")


def main():
    parser = argparse.ArgumentParser(description="Load real or high-volume dataset into PostgreSQL Optimizer DBs.")
    parser.add_argument("--mode", choices=["realistic", "csv"], default="realistic",
                        help="Data generation mode ('realistic' for high-volume skewed dataset, 'csv' for real CSVs)")
    parser.add_argument("--rows", type=int, default=100_000, help="Target number of orders (e.g. 100000, 250000, 500000)")
    parser.add_argument("--csv-dir", type=str, default="./data/real_data", help="Directory containing CSV files for 'csv' mode")
    parser.add_argument("--target", choices=["main", "sandbox", "both"], default="both", help="Target database")

    args = parser.parse_args()

    targets = []
    if args.target in ["main", "both"]:
        targets.append(False)  # sandbox=False
    if args.target in ["sandbox", "both"]:
        targets.append(True)   # sandbox=True

    for is_sandbox in targets:
        db_name = "SANDBOX" if is_sandbox else "PRODUCTION (DEMO)"
        print(f"\n==========================================")
        print(f"Targeting {db_name} Database")
        print(f"==========================================")
        try:
            with get_connection(sandbox=is_sandbox) as conn:
                apply_schema(conn)
                if args.mode == "realistic":
                    stats = generate_realistic_dataset(conn, target_orders=args.rows)
                    print(f"Final table counts for {db_name}: {stats}")
                elif args.mode == "csv":
                    load_from_csv(conn, args.csv_dir)
        except Exception as exc:
            print(f"Failed to connect or seed {db_name}: {exc}")
            print("Ensure PostgreSQL is running (e.g. docker compose up -d postgres sandbox-postgres).")


if __name__ == "__main__":
    main()
