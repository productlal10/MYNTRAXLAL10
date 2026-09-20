"""
validate_migration.py
Validate consistency between PostgreSQL transactional tables and DuckDB analytics tables.
"""

import os

import duckdb
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/myntra_analytics.duckdb")
PG_DSN = {
    "host": os.getenv("PG_HOST", "127.0.0.1"),
    "port": int(os.getenv("PG_PORT", 5432)),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD", "alan1234"),
    "dbname": os.getenv("PG_DBNAME", "myntra"),
}


def validate_all():
    print("\n" + "=" * 80)
    print("  DATA VALIDATION SUITE: PostgreSQL ↔ DuckDB")
    print("=" * 80)

    if not os.path.exists(DUCKDB_PATH):
        raise FileNotFoundError(f"DuckDB analytics database not found at {DUCKDB_PATH}")

    pg = psycopg2.connect(**PG_DSN)
    dk = duckdb.connect(DUCKDB_PATH, read_only=True)
    pg_cur = pg.cursor()

    all_passed = True

    print("\n[TEST 1] Row Count Comparisons:")
    print(f"  {'Table Name':<30} | {'PostgreSQL':<12} | {'DuckDB':<12} | {'Status':<10}")
    print("  " + "-" * 74)

    tables_map = [
        ("products", "analytics_products"),
        ("product_sizes", "analytics_sizes"),
        ("daily_sales_analytics", "analytics_sales"),
        ("daily_inventory_snapshots", "analytics_snapshots"),
    ]

    for pg_tbl, dk_tbl in tables_map:
        pg_cur.execute(f"SELECT COUNT(*) FROM {pg_tbl}")
        n_pg = pg_cur.fetchone()[0]
        n_dk = dk.execute(f"SELECT COUNT(*) FROM {dk_tbl}").fetchone()[0]
        passed = n_pg == n_dk
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        print(f"  {pg_tbl:<30} | {n_pg:>10,} | {n_dk:>10,} | {status}")

    print("\n[TEST 2] Aggregate Metric Consistency:")
    print(f"  {'Metric Description':<35} | {'PostgreSQL':<15} | {'DuckDB':<15} | {'Status'}")
    print("  " + "-" * 84)

    metric_queries = [
        (
            "Total Selling Price",
            "SELECT ROUND(COALESCE(SUM(selling_price), 0), 2) FROM products",
            "SELECT ROUND(COALESCE(SUM(selling_price), 0), 2) FROM analytics_products",
            "currency",
        ),
        (
            "Distinct Brands in Catalog",
            "SELECT COUNT(DISTINCT brand) FROM products",
            "SELECT COUNT(DISTINCT brand) FROM analytics_products",
            "count",
        ),
        (
            "In-Stock Warehouse Units",
            "SELECT COALESCE(SUM(inventory_count), 0) FROM product_sizes WHERE available = 1",
            "SELECT COALESCE(SUM(inventory_count), 0) FROM analytics_sizes WHERE available = 1",
            "count",
        ),
    ]

    for label, pg_sql, dk_sql, metric_type in metric_queries:
        pg_cur.execute(pg_sql)
        pg_value = pg_cur.fetchone()[0]
        dk_value = dk.execute(dk_sql).fetchone()[0]
        passed = abs(float(pg_value or 0) - float(dk_value or 0)) < 1.0
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        if metric_type == "currency":
            pg_display = f"₹{float(pg_value or 0):,.2f}"
            dk_display = f"₹{float(dk_value or 0):,.2f}"
        else:
            pg_display = f"{int(pg_value or 0):,}"
            dk_display = f"{int(dk_value or 0):,}"
        print(f"  {label:<35} | {pg_display:>15} | {dk_display:>15} | {status}")

    print("\n[TEST 3] Sample Product Spot-Check:")
    pg_cur.execute(
        """
        SELECT product_id, title, brand, selling_price, mrp
        FROM products
        ORDER BY updated_at DESC NULLS LAST, product_id DESC
        LIMIT 5
        """
    )
    samples = pg_cur.fetchall()

    for product_id, title, brand, price, mrp in samples:
        duck_row = dk.execute(
            """
            SELECT title, brand, selling_price, mrp
            FROM analytics_products
            WHERE product_id = ?
            """,
            [product_id],
        ).fetchone()
        passed = bool(
            duck_row
            and duck_row[0] == title
            and duck_row[1] == brand
            and float(duck_row[2] or 0) == float(price or 0)
            and float(duck_row[3] or 0) == float(mrp or 0)
        )
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        print(f"  Product ID {product_id:<10} | Brand: {str(brand)[:15]:<15} | {status}")

    print("\n" + "=" * 80)
    if all_passed:
        print("  ALL POSTGRESQL ↔ DUCKDB VALIDATION CHECKS PASSED.")
    else:
        print("  Some PostgreSQL ↔ DuckDB validation checks failed.")
    print("=" * 80 + "\n")

    pg.close()
    dk.close()
    return all_passed


if __name__ == "__main__":
    validate_all()
