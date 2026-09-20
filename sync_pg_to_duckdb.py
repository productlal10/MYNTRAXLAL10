"""
sync_pg_to_duckdb.py
Refreshes the DuckDB analytics database from PostgreSQL using DuckDB's native postgres extension.
Fast, vectorized, and handles full refresh or scheduled sync.

Usage:
    python3 sync_pg_to_duckdb.py
"""

import duckdb
import os
import time
from dotenv import load_dotenv

load_dotenv()

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "alan1234")
PG_DBNAME = os.getenv("PG_DBNAME", "myntra")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/myntra_analytics.duckdb")


def refresh_duckdb_from_pg():
    print("\n" + "="*60)
    print("  PostgreSQL → DuckDB Analytics Synchronizer")
    print("="*60)
    print(f"  Source PostgreSQL : {PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DBNAME}")
    print(f"  Target DuckDB     : {DUCKDB_PATH}")
    print("="*60 + "\n")

    t0 = time.time()
    
    # Connect to DuckDB
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("PRAGMA threads=8;")
    con.execute("PRAGMA memory_limit='4GB';")
    con.execute("INSTALL postgres; LOAD postgres;")

    pg_conn_str = f"host={PG_HOST} port={PG_PORT} user={PG_USER} password={PG_PASSWORD} dbname={PG_DBNAME}"
    print(f"Connecting to PostgreSQL via native extension…")
    
    con.execute(f"ATTACH '{pg_conn_str}' AS pg (TYPE POSTGRES, READ_ONLY);")

    print("Refreshing analytics_products…")
    t_step = time.time()
    con.execute("DROP TABLE IF EXISTS analytics_products;")
    con.execute("""
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
    """)
    n_prod = con.execute("SELECT COUNT(*) FROM analytics_products").fetchone()[0]
    print(f"  ✓ analytics_products: {n_prod:,} rows in {time.time() - t_step:.2f}s")

    print("Refreshing analytics_sizes…")
    t_step = time.time()
    con.execute("DROP TABLE IF EXISTS analytics_sizes;")
    con.execute("""
        CREATE TABLE analytics_sizes AS
        SELECT 
            product_id,
            size,
            sku_id,
            CAST(available AS INTEGER) AS available,
            CAST(inventory_count AS INTEGER) AS inventory_count
        FROM pg.product_sizes;
    """)
    n_sizes = con.execute("SELECT COUNT(*) FROM analytics_sizes").fetchone()[0]
    print(f"  ✓ analytics_sizes: {n_sizes:,} rows in {time.time() - t_step:.2f}s")

    print("Refreshing analytics_sales…")
    t_step = time.time()
    con.execute("DROP TABLE IF EXISTS analytics_sales;")
    con.execute("""
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
    """)
    n_sales = con.execute("SELECT COUNT(*) FROM analytics_sales").fetchone()[0]
    print(f"  ✓ analytics_sales: {n_sales:,} rows in {time.time() - t_step:.2f}s")

    print("Refreshing analytics_snapshots…")
    t_step = time.time()
    con.execute("DROP TABLE IF EXISTS analytics_snapshots;")
    con.execute("""
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
    """)
    n_snaps = con.execute("SELECT COUNT(*) FROM analytics_snapshots").fetchone()[0]
    print(f"  ✓ analytics_snapshots: {n_snaps:,} rows in {time.time() - t_step:.2f}s")

    print("Refreshing brands…")
    t_step = time.time()
    con.execute("DROP TABLE IF EXISTS brands;")
    con.execute("""
        CREATE TABLE brands AS
        SELECT * FROM pg.brands;
    """)
    n_brands = con.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    print(f"  ✓ brands: {n_brands:,} rows in {time.time() - t_step:.2f}s")

    print("Re-creating analytical views…")
    con.execute("DROP VIEW IF EXISTS v_category_summary;")
    con.execute("""
        CREATE VIEW v_category_summary AS
        SELECT 
            category,
            COUNT(*) AS total_skus,
            AVG(selling_price) AS avg_price,
            AVG(discount_percentage) AS avg_discount,
            AVG(average_rating) AS avg_rating,
            SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) AS in_stock_count,
            COUNT(DISTINCT brand) AS brand_count
        FROM analytics_products
        GROUP BY category;
    """)

    con.execute("DROP VIEW IF EXISTS v_brand_summary;")
    con.execute("""
        CREATE VIEW v_brand_summary AS
        SELECT 
            brand,
            COUNT(*) AS total_skus,
            AVG(selling_price) AS avg_price,
            AVG(discount_percentage) AS avg_discount,
            AVG(average_rating) AS avg_rating,
            SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) AS in_stock_count,
            COUNT(DISTINCT category) AS category_count
        FROM analytics_products
        GROUP BY brand;
    """)

    con.execute("DETACH pg;")
    total_elapsed = time.time() - t0

    print("\n" + "="*60)
    print(f"  ✅ PostgreSQL → DuckDB Refresh Complete in {total_elapsed:.2f}s!")
    print(f"     Products  : {n_prod:,}")
    print(f"     Sizes     : {n_sizes:,}")
    print(f"     Sales     : {n_sales:,}")
    print(f"     Snapshots : {n_snaps:,}")
    print(f"     Brands    : {n_brands:,}")
    print("="*60 + "\n")

    con.close()


if __name__ == "__main__":
    refresh_duckdb_from_pg()
