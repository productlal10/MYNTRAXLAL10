"""
build_duckdb.py
Builds the DuckDB analytics database from PostgreSQL using DuckDB's native
PostgreSQL extension for fast, vectorized refreshes.

The build is atomic by default:
- a temporary database is created first
- the current analytics database stays live during the rebuild
- the new database is swapped into place only after a successful build

Usage:
    python3 build_duckdb.py
    python3 build_duckdb.py --no-swap
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", "data/myntra_analytics.duckdb"))
PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "alan1234")
PG_DBNAME = os.getenv("PG_DBNAME", "myntra")
DUCKDB_THREADS = int(os.getenv("DUCKDB_THREADS", "8"))
DUCKDB_MEMORY_LIMIT = os.getenv("DUCKDB_MEMORY_LIMIT", "4GB")


def _pg_attach_dsn() -> str:
    dsn = (
        f"host={PG_HOST} "
        f"port={PG_PORT} "
        f"user={PG_USER} "
        f"password={PG_PASSWORD} "
        f"dbname={PG_DBNAME}"
    )
    return dsn.replace("'", "''")


def _remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def _cleanup_duckdb_artifacts(base_path: Path) -> None:
    _remove_if_exists(base_path)
    _remove_if_exists(Path(f"{base_path}.wal"))


def _swap_duckdb_database(build_path: Path, target_path: Path) -> None:
    build_wal = Path(f"{build_path}.wal")
    target_wal = Path(f"{target_path}.wal")

    if target_wal.exists():
        target_wal.unlink()

    os.replace(build_path, target_path)

    if build_wal.exists():
        os.replace(build_wal, target_wal)


def _build_tables_and_views(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(f"ATTACH '{_pg_attach_dsn()}' AS pg (TYPE POSTGRES, READ_ONLY);")

    print("Refreshing analytics_products...")
    t_step = time.time()
    con.execute("DROP TABLE IF EXISTS analytics_products;")
    con.execute(
        """
        CREATE TABLE analytics_products AS
        SELECT
            product_id,
            sku,
            brand,
            title,
            category,
            sub_category,
            gender,
            CAST(mrp AS DOUBLE) AS mrp,
            CAST(selling_price AS DOUBLE) AS selling_price,
            CAST(discount_percentage AS INTEGER) AS discount_percentage,
            CAST(is_in_stock AS INTEGER) AS is_in_stock,
            CAST(is_myntra_label AS INTEGER) AS is_myntra_label,
            brand_type,
            fit,
            fabric,
            pattern,
            primary_color,
            color_hex,
            CAST(average_rating AS DOUBLE) AS average_rating,
            CAST(total_ratings_count AS INTEGER) AS total_ratings_count,
            CAST(total_reviews_count AS INTEGER) AS total_reviews_count
        FROM pg.products;
        """
    )
    n_products = con.execute("SELECT COUNT(*) FROM analytics_products").fetchone()[0]
    print(f"  ok analytics_products: {n_products:,} rows in {time.time() - t_step:.2f}s")

    print("Refreshing analytics_sizes...")
    t_step = time.time()
    con.execute("DROP TABLE IF EXISTS analytics_sizes;")
    con.execute(
        """
        CREATE TABLE analytics_sizes AS
        SELECT
            product_id,
            size,
            CAST(available AS INTEGER) AS available,
            CAST(inventory_count AS INTEGER) AS inventory_count
        FROM pg.product_sizes;
        """
    )
    n_sizes = con.execute("SELECT COUNT(*) FROM analytics_sizes").fetchone()[0]
    print(f"  ok analytics_sizes: {n_sizes:,} rows in {time.time() - t_step:.2f}s")

    print("Refreshing analytics_sales...")
    t_step = time.time()
    con.execute("DROP TABLE IF EXISTS analytics_sales;")
    con.execute(
        """
        CREATE TABLE analytics_sales AS
        SELECT
            analytics_date,
            product_id,
            brand,
            category,
            CAST(units_sold AS INTEGER) AS units_sold,
            CAST(revenue_generated AS DOUBLE) AS revenue_generated,
            CAST(stock_added AS INTEGER) AS stock_added,
            CAST(price_delta AS DOUBLE) AS price_delta,
            CAST(ros AS DOUBLE) AS ros,
            stock_status
        FROM pg.daily_sales_analytics;
        """
    )
    n_sales = con.execute("SELECT COUNT(*) FROM analytics_sales").fetchone()[0]
    print(f"  ok analytics_sales: {n_sales:,} rows in {time.time() - t_step:.2f}s")

    print("Refreshing analytics_snapshots...")
    t_step = time.time()
    con.execute("DROP TABLE IF EXISTS analytics_snapshots;")
    con.execute(
        """
        CREATE TABLE analytics_snapshots AS
        SELECT
            snapshot_date,
            product_id,
            brand,
            category,
            CAST(selling_price AS DOUBLE) AS selling_price,
            CAST(mrp AS DOUBLE) AS mrp,
            CAST(discount_percentage AS INTEGER) AS discount_percentage,
            CAST(is_in_stock AS INTEGER) AS is_in_stock,
            CAST(total_stock AS INTEGER) AS total_stock
        FROM pg.daily_inventory_snapshots;
        """
    )
    n_snapshots = con.execute("SELECT COUNT(*) FROM analytics_snapshots").fetchone()[0]
    print(f"  ok analytics_snapshots: {n_snapshots:,} rows in {time.time() - t_step:.2f}s")

    print("Refreshing brands...")
    t_step = time.time()
    con.execute("DROP TABLE IF EXISTS brands;")
    con.execute(
        """
        CREATE TABLE brands AS
        SELECT *
        FROM pg.brands;
        """
    )
    n_brands = con.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    print(f"  ok brands: {n_brands:,} rows in {time.time() - t_step:.2f}s")

    print("Rebuilding analytical views...")
    con.execute("DROP VIEW IF EXISTS v_brand_summary;")
    con.execute(
        """
        CREATE VIEW v_brand_summary AS
        SELECT
            brand,
            COUNT(*) AS total_products,
            AVG(selling_price) AS avg_price,
            AVG(discount_percentage) AS avg_discount,
            AVG(average_rating) AS avg_rating,
            SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) AS in_stock_count,
            SUM(total_ratings_count) AS total_ratings,
            COUNT(DISTINCT category) AS category_count
        FROM analytics_products
        GROUP BY brand;
        """
    )

    con.execute("DROP VIEW IF EXISTS v_category_summary;")
    con.execute(
        """
        CREATE VIEW v_category_summary AS
        SELECT
            category,
            sub_category,
            gender,
            COUNT(*) AS total_products,
            AVG(selling_price) AS avg_price,
            MIN(selling_price) AS min_price,
            MAX(selling_price) AS max_price,
            AVG(discount_percentage) AS avg_discount,
            AVG(average_rating) AS avg_rating,
            SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) AS in_stock_count,
            COUNT(DISTINCT brand) AS brand_count
        FROM analytics_products
        GROUP BY category, sub_category, gender;
        """
    )

    con.execute("DROP VIEW IF EXISTS v_price_distribution;")
    con.execute(
        """
        CREATE VIEW v_price_distribution AS
        SELECT
            category,
            CASE
                WHEN selling_price < 500 THEN 'Under ₹500'
                WHEN selling_price < 1000 THEN '₹500-1K'
                WHEN selling_price < 2000 THEN '₹1K-2K'
                WHEN selling_price < 3000 THEN '₹2K-3K'
                WHEN selling_price < 5000 THEN '₹3K-5K'
                WHEN selling_price < 10000 THEN '₹5K-10K'
                ELSE 'Above ₹10K'
            END AS price_bucket,
            COUNT(*) AS product_count,
            AVG(selling_price) AS avg_price
        FROM analytics_products
        GROUP BY category, price_bucket;
        """
    )

    con.execute("DROP VIEW IF EXISTS v_fabric_summary;")
    con.execute(
        """
        CREATE VIEW v_fabric_summary AS
        SELECT
            fabric,
            category,
            COUNT(*) AS total_products,
            AVG(selling_price) AS avg_price,
            AVG(average_rating) AS avg_rating,
            AVG(discount_percentage) AS avg_discount
        FROM analytics_products
        WHERE fabric IS NOT NULL AND fabric != ''
        GROUP BY fabric, category
        ORDER BY total_products DESC;
        """
    )

    con.execute("DROP VIEW IF EXISTS v_size_summary;")
    con.execute(
        """
        CREATE VIEW v_size_summary AS
        SELECT
            s.size,
            COUNT(DISTINCT s.product_id) AS product_count,
            SUM(s.inventory_count) AS total_inventory,
            AVG(p.selling_price) AS avg_price,
            AVG(p.average_rating) AS avg_rating
        FROM analytics_sizes s
        JOIN analytics_products p ON p.product_id = s.product_id
        WHERE s.available = 1
        GROUP BY s.size
        ORDER BY product_count DESC;
        """
    )

    con.execute("DETACH pg;")


def rebuild_duckdb(target_path: Path, swap: bool = True) -> Path:
    print("\n" + "=" * 60)
    print("  Building DuckDB Analytics Database")
    print("=" * 60)
    print(f"  Source : PG {PG_HOST}/{PG_DBNAME}")
    print(f"  Target : {target_path}")
    print(f"  Mode   : {'atomic swap' if swap else 'direct write'}")
    print("=" * 60 + "\n")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    build_path = Path(f"{target_path}.build") if swap else target_path
    _cleanup_duckdb_artifacts(build_path)

    t0 = time.time()
    con = duckdb.connect(str(build_path))
    try:
        con.execute(f"PRAGMA threads={DUCKDB_THREADS};")
        con.execute(f"PRAGMA memory_limit='{DUCKDB_MEMORY_LIMIT}';")
        con.execute("INSTALL postgres; LOAD postgres;")
        _build_tables_and_views(con)
        con.execute("CHECKPOINT;")
    finally:
        con.close()

    if swap:
        _swap_duckdb_database(build_path, target_path)

    elapsed = time.time() - t0
    print("\n" + "=" * 60)
    print(f"  DuckDB build complete in {elapsed:.1f}s")
    print(f"  Active file: {target_path}")
    print("=" * 60 + "\n")
    return target_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the DuckDB analytics database.")
    parser.add_argument(
        "--output",
        default=str(DUCKDB_PATH),
        help="Target DuckDB database path.",
    )
    parser.add_argument(
        "--no-swap",
        action="store_true",
        help="Write directly to the target path instead of atomic swap mode.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    rebuild_duckdb(Path(args.output), swap=not args.no_swap)
