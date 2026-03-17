"""
load_data.py – RoseAmor ETL Pipeline
=====================================
Reads raw CSVs, applies data cleaning, and loads three layers into PostgreSQL:
    raw       → data/*.csv  (untouched source)
    staging   → stg_orders, stg_customers, stg_products  (typed + flagged)
    consumption → dim_customers, dim_products, fact_orders, v_orders_full

Connection config (env vars with defaults):
    PG_HOST     = localhost
    PG_PORT     = 5432
    PG_DBNAME   = test
    PG_USER     = dev
    PG_PASSWORD = test

Usage:
        python etl/load_data.py
"""

import csv
import os
import sys
import psycopg2
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"


def get_conn() -> psycopg2.extensions.connection:
        return psycopg2.connect(
                host=os.environ.get("PG_HOST",     "localhost"),
                port=int(os.environ.get("PG_PORT", "5432")),
                dbname=os.environ.get("PG_DBNAME", "test"),
                user=os.environ.get("PG_USER",     "dev"),
                password=os.environ.get("PG_PASSWORD", "test"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def safe_float(value: str):
    """Return float or None for blank/invalid strings."""
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None


def safe_int(value: str):
    """Return int or None for blank/invalid strings."""
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return None


def normalize_date(value: str) -> str | None:
    """Strip timestamp component, validate and keep only YYYY-MM-DD."""
    if not value or not value.strip():
        return None
    date_part = value.strip().split(" ")[0]
    try:
        datetime.strptime(date_part, "%Y-%m-%d")
    except ValueError:
        return None
    return date_part


# ─────────────────────────────────────────────────────────────────────────────
# STAGING
# ─────────────────────────────────────────────────────────────────────────────

def load_staging(cur):
    print("→ Loading staging layer …")

    for stmt in [
        "DROP TABLE IF EXISTS stg_orders   CASCADE",
        "DROP TABLE IF EXISTS stg_customers CASCADE",
        "DROP TABLE IF EXISTS stg_products  CASCADE",
        """CREATE TABLE stg_orders (
            order_id        TEXT,
            customer_id     TEXT,
            sku             TEXT,
            quantity        INTEGER,
            unit_price      DOUBLE PRECISION,
            order_date      DATE,
            channel         TEXT,
            _is_duplicate   SMALLINT DEFAULT 0,
            _negative_qty   SMALLINT DEFAULT 0,
            _null_price     SMALLINT DEFAULT 0,
            _invalid_date   SMALLINT DEFAULT 0
        )""",
        """CREATE TABLE stg_customers (
            customer_id TEXT,
            name        TEXT,
            country     TEXT,
            segment     TEXT,
            created_at  DATE
        )""",
        """CREATE TABLE stg_products (
            sku      TEXT,
            category TEXT,
            cost     DOUBLE PRECISION,
            active   SMALLINT
        )""",
    ]:
        cur.execute(stmt)

    # ---------- orders ----------
    seen_order_ids: set = set()
    order_rows = []
    with open(DATA / "orders.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            oid      = row["order_id"].strip()
            qty      = safe_int(row["quantity"])
            price    = safe_float(row["unit_price"])
            date     = normalize_date(row["order_date"])
            channel  = row["channel"].strip().lower()

            is_dup   = 1 if oid in seen_order_ids else 0
            neg_qty  = 1 if (qty is not None and qty < 0) else 0
            null_prc = 1 if price is None else 0
            bad_date = 1 if date is None else 0

            seen_order_ids.add(oid)
            order_rows.append((
                oid, row["customer_id"].strip(), row["sku"].strip(),
                qty, price, date, channel,
                is_dup, neg_qty, null_prc, bad_date
            ))

    cur.executemany(
        "INSERT INTO stg_orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        order_rows
    )
    print(f"   stg_orders   : {len(order_rows):>6} rows loaded")

    # ---------- customers ----------
    customer_rows = []
    with open(DATA / "customers.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            customer_rows.append((
                row["customer_id"].strip(),
                row["name"].strip(),
                row["country"].strip() or "Unknown",
                row["segment"].strip() or "Unknown",
                normalize_date(row["created_at"]),
            ))

    cur.executemany(
        "INSERT INTO stg_customers VALUES (%s,%s,%s,%s,%s)",
        customer_rows
    )
    print(f"   stg_customers: {len(customer_rows):>6} rows loaded")

    # ---------- products ----------
    product_rows = []
    with open(DATA / "products.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            product_rows.append((
                row["sku"].strip(),
                row["category"].strip() or "Unknown",
                safe_float(row["cost"]),
                1 if row["active"].strip().lower() == "true" else 0,
            ))

    cur.executemany(
        "INSERT INTO stg_products VALUES (%s,%s,%s,%s)",
        product_rows
    )
    print(f"   stg_products : {len(product_rows):>6} rows loaded")


# ─────────────────────────────────────────────────────────────────────────────
# CONSUMPTION  (star schema)
# ─────────────────────────────────────────────────────────────────────────────

def load_consumption(cur):
    print("→ Building consumption layer …")

    for stmt in [
        "DROP TABLE IF EXISTS dim_customers CASCADE",
        "CREATE TABLE dim_customers AS SELECT customer_id, name, country, segment, created_at FROM stg_customers",
        "ALTER TABLE dim_customers ADD PRIMARY KEY (customer_id)",
        "DROP TABLE IF EXISTS dim_products CASCADE",
        "CREATE TABLE dim_products AS SELECT sku, category, cost, active FROM stg_products",
        "ALTER TABLE dim_products ADD PRIMARY KEY (sku)",
        "DROP TABLE IF EXISTS fact_orders CASCADE",
        """CREATE TABLE fact_orders AS
        SELECT
            o.order_id,
            o.customer_id,
            o.sku,
            o.quantity,
            o.unit_price,
            o.order_date,
            TO_CHAR(o.order_date, 'YYYY')    AS year,
            TO_CHAR(o.order_date, 'MM')      AS month,
            TO_CHAR(o.order_date, 'YYYY-MM') AS year_month,
            o.channel,
            ROUND((o.quantity * o.unit_price)::numeric,                          2) AS revenue,
            ROUND((o.quantity * (o.unit_price - COALESCE(p.cost, 0)))::numeric,  2) AS gross_profit,
            ROUND((CASE WHEN o.unit_price > 0
                        THEN (o.unit_price - COALESCE(p.cost, 0)) / o.unit_price * 100
                        ELSE NULL
                   END)::numeric, 2) AS margin_pct
        FROM stg_orders o
        LEFT JOIN dim_products p ON o.sku = p.sku
        WHERE o._is_duplicate = 0
          AND o._negative_qty = 0
                    AND o._null_price   = 0
                    AND o._invalid_date = 0""",
        "ALTER TABLE fact_orders ADD PRIMARY KEY (order_id)",
        "CREATE INDEX idx_fact_orders_customer ON fact_orders (customer_id)",
        "CREATE INDEX idx_fact_orders_sku      ON fact_orders (sku)",
        "CREATE INDEX idx_fact_orders_date     ON fact_orders (order_date)",
        "CREATE INDEX idx_fact_orders_channel  ON fact_orders (channel)",
        "DROP VIEW IF EXISTS v_orders_full",
        """CREATE VIEW v_orders_full AS
        SELECT
            f.order_id,
            f.order_date,
            f.year,
            f.month,
            f.year_month,
            f.channel,
            f.quantity,
            f.unit_price,
            f.revenue,
            f.gross_profit,
            f.margin_pct,
            c.customer_id,
            c.name        AS customer_name,
            c.country,
            c.segment,
            p.sku,
            p.category,
            p.cost        AS product_cost,
            p.active      AS product_active
        FROM fact_orders   f
        JOIN dim_customers c ON f.customer_id = c.customer_id
        JOIN dim_products  p ON f.sku         = p.sku""",
    ]:
        cur.execute(stmt)

    cur.execute("SELECT COUNT(*) FROM fact_orders")
    n_fact = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM dim_customers")
    n_cust = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM dim_products")
    n_prod = cur.fetchone()[0]
    print(f"   dim_customers: {n_cust:>6} rows")
    print(f"   dim_products : {n_prod:>6} rows")
    print(f"   fact_orders  : {n_fact:>6} rows (clean)")


# ─────────────────────────────────────────────────────────────────────────────
# QA SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_qa(cur):
    print("\n── QA Summary ──────────────────────────────────────────────────")
    def q(sql):
        cur.execute(sql)
        return cur.fetchone()[0]
    dups   = q("SELECT COUNT(*) FROM stg_orders WHERE _is_duplicate=1")
    negs   = q("SELECT COUNT(*) FROM stg_orders WHERE _negative_qty=1")
    nulls  = q("SELECT COUNT(*) FROM stg_orders WHERE _null_price=1")
    bad_dt = q("SELECT COUNT(*) FROM stg_orders WHERE _invalid_date=1")
    total  = q("SELECT COUNT(*) FROM stg_orders")
    clean  = q("SELECT COUNT(*) FROM fact_orders")
    rev    = q("SELECT ROUND(SUM(revenue),2) FROM fact_orders")
    margin = q("SELECT ROUND(SUM(gross_profit),2) FROM fact_orders")
    print(f"   Raw orders          : {total}")
    print(f"   Removed – duplicates: {dups}")
    print(f"   Removed – neg qty   : {negs}")
    print(f"   Removed – null price: {nulls}")
    print(f"   Removed – bad date  : {bad_dt}")
    print(f"   Clean fact_orders   : {clean}")
    print(f"   Total revenue       : ${rev:,.2f}")
    print(f"   Total gross profit  : ${margin:,.2f}")
    unk_c = q("SELECT COUNT(*) FROM dim_customers WHERE country='Unknown'")
    unk_s = q("SELECT COUNT(*) FROM dim_customers WHERE segment='Unknown'")
    unk_p = q("SELECT COUNT(*) FROM dim_products  WHERE category='Unknown'")
    print(f"   Customers – unknown country : {unk_c}")
    print(f"   Customers – unknown segment : {unk_s}")
    print(f"   Products  – unknown category: {unk_p}")
    print("────────────────────────────────────────────────────────────────")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run():
    conn = get_conn()
    conn.autocommit = False
    cur = conn.cursor()
    dsn = conn.get_dsn_parameters()
    print(f"Database: {dsn.get('dbname')}  host: {dsn.get('host')}:{dsn.get('port')}")

    try:
        load_staging(cur)
        conn.commit()

        load_consumption(cur)
        conn.commit()

        print_qa(cur)
        print("\n✓ ETL complete → PostgreSQL tables created/updated")
    except Exception as exc:
        conn.rollback()
        print(f"\n✗ ETL failed: {exc}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
