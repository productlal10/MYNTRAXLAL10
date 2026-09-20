"""
benchmark_migration.py
Benchmark representative PostgreSQL CRUD queries against DuckDB analytics queries.
"""

import os
import time

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


def time_query(func, runs=3):
    durations = []
    result = None
    for _ in range(runs):
        start = time.perf_counter()
        result = func()
        durations.append((time.perf_counter() - start) * 1000)
    return sum(durations) / len(durations), result


def run_benchmarks():
    print("\n" + "=" * 88)
    print("  PERFORMANCE BENCHMARK: PostgreSQL vs DuckDB")
    print("=" * 88)

    pg = psycopg2.connect(**PG_DSN)
    duck = duckdb.connect(DUCKDB_PATH, read_only=True) if os.path.exists(DUCKDB_PATH) else None
    if duck is None:
        raise FileNotFoundError(f"DuckDB analytics database not found at {DUCKDB_PATH}")

    results = []

    workloads = [
        (
            "Global KPIs",
            "SELECT COUNT(*), AVG(selling_price), AVG(discount_percentage), SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) FROM products",
            "SELECT COUNT(*), AVG(selling_price), AVG(discount_percentage), SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) FROM analytics_products",
        ),
        (
            "Price Intelligence",
            """
            SELECT
                CASE
                    WHEN selling_price < 1000 THEN 'Under 1k'
                    WHEN selling_price < 2500 THEN '1k-2.5k'
                    ELSE '2.5k+'
                END AS bucket,
                COUNT(*),
                AVG(selling_price)
            FROM products
            WHERE category = 'Shirts'
            GROUP BY bucket
            """,
            """
            SELECT
                CASE
                    WHEN selling_price < 1000 THEN 'Under 1k'
                    WHEN selling_price < 2500 THEN '1k-2.5k'
                    ELSE '2.5k+'
                END AS bucket,
                COUNT(*),
                AVG(selling_price),
                MEDIAN(selling_price)
            FROM analytics_products
            WHERE category = 'Shirts'
            GROUP BY bucket
            """,
        ),
        (
            "Category Aggregations",
            "SELECT category, sub_category, COUNT(*), AVG(selling_price), AVG(average_rating) FROM products GROUP BY category, sub_category",
            "SELECT category, sub_category, COUNT(*), AVG(selling_price), AVG(average_rating) FROM analytics_products GROUP BY category, sub_category",
        ),
        (
            "Fabric Intelligence",
            "SELECT fabric, COUNT(*), AVG(selling_price) FROM products WHERE fabric IS NOT NULL AND fabric != '' GROUP BY fabric ORDER BY COUNT(*) DESC LIMIT 25",
            "SELECT fabric, COUNT(*), AVG(selling_price) FROM analytics_products WHERE fabric IS NOT NULL AND fabric != '' GROUP BY fabric ORDER BY COUNT(*) DESC LIMIT 25",
        ),
    ]

    for name, pg_sql, duck_sql in workloads:
        pg_time, _ = time_query(
            lambda sql=pg_sql: [cur := pg.cursor(), cur.execute(sql), cur.fetchall()][2]
        )
        duck_time, _ = time_query(lambda sql=duck_sql: duck.execute(sql).fetchall())
        speedup = (pg_time / duck_time) if duck_time else 0.0
        results.append((name, pg_time, duck_time, speedup))

    point_lookup_id = 70172
    point_lookup_sql = f"SELECT * FROM products WHERE product_id = {point_lookup_id}"
    pg_lookup_time, _ = time_query(
        lambda: [cur := pg.cursor(), cur.execute(point_lookup_sql), cur.fetchone()][2]
    )
    results.append(("Point Lookup / CRUD", pg_lookup_time, 0.0, 0.0))

    print(f"\n{'Query Workload':<30} | {'PostgreSQL':<15} | {'DuckDB':<15} | {'Relative Speed':<20}")
    print("-" * 88)
    for name, pg_time, duck_time, speedup in results:
        if duck_time > 0:
            speed_display = f"{speedup:.1f}x DuckDB"
            duck_display = f"{duck_time:>10.2f} ms"
        else:
            speed_display = "PG only"
            duck_display = f"{'N/A':>10}"
        print(f"{name:<30} | {pg_time:>10.2f} ms | {duck_display:<15} | {speed_display:<20}")

    print("=" * 88 + "\n")
    pg.close()
    duck.close()


if __name__ == "__main__":
    run_benchmarks()
