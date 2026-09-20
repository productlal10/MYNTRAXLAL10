#!/usr/bin/env python3
"""Restore the PostgreSQL catalog from the local SQLite backup database."""

from __future__ import annotations

import csv
import io
import os
import sqlite3
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = ROOT / "data" / "myntra_catalog.db"

TABLES = [
    {
        "name": "products",
        "columns": [
            "product_id", "sku", "brand", "title", "category", "sub_category", "gender",
            "product_url", "mrp", "selling_price", "discount_percentage", "is_in_stock",
            "is_myntra_label", "brand_type", "fit", "fabric", "pattern", "primary_color",
            "color_hex", "average_rating", "total_ratings_count", "total_reviews_count",
            "full_data_json", "created_at", "updated_at",
        ],
    },
    {
        "name": "product_sizes",
        "columns": ["id", "product_id", "size", "sku_id", "available", "inventory_count"],
    },
    {
        "name": "brands",
        "columns": [
            "brand_name", "shirts_count", "denims_count", "western_count", "total_count",
            "is_myntra_label", "brand_type", "crawled_status", "updated_at",
        ],
    },
    {
        "name": "crawl_state",
        "columns": ["category", "brand", "page", "items_scraped", "status", "last_scraped_at"],
    },
    {
        "name": "daily_inventory_snapshots",
        "columns": [
            "snapshot_date", "product_id", "brand", "category", "selling_price", "mrp",
            "discount_percentage", "is_in_stock", "total_stock",
        ],
    },
    {
        "name": "daily_sales_analytics",
        "columns": [
            "analytics_date", "product_id", "brand", "category", "units_sold",
            "revenue_generated", "stock_added", "price_delta", "ros", "stock_status",
        ],
    },
    {
        "name": "scraper_runs",
        "columns": [
            "run_id", "run_type", "status", "started_at", "completed_at", "total_items",
            "successful_items", "failed_items", "rate_items_per_sec", "duration_seconds", "log_summary",
        ],
    },
    {
        "name": "scraper_errors",
        "columns": ["id", "run_id", "product_id", "error_type", "error_message", "created_at"],
    },
]


def load_pg_dsn() -> dict:
    load_dotenv()
    return {
        "host": os.getenv("PG_HOST", "127.0.0.1"),
        "port": int(os.getenv("PG_PORT", 5432)),
        "user": os.getenv("PG_USER", "postgres"),
        "password": os.getenv("PG_PASSWORD", "alan1234"),
        "dbname": os.getenv("PG_DBNAME", "myntra"),
    }


def open_sqlite(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"SQLite backup not found: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def copy_table(sqlite_conn: sqlite3.Connection, pg_conn, table_name: str, columns: list[str], batch_size: int = 10000) -> None:
    sqlite_cur = sqlite_conn.cursor()
    pg_cur = pg_conn.cursor()

    sqlite_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_rows = int(sqlite_cur.fetchone()[0] or 0)
    print(f"\n[{table_name}] {total_rows:,} rows")
    if total_rows == 0:
        return

    col_sql = ", ".join(columns)
    sqlite_cur.execute(f"SELECT {col_sql} FROM {table_name}")

    copied = 0
    started = time.time()

    while True:
        rows = sqlite_cur.fetchmany(batch_size)
        if not rows:
            break

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        for row in rows:
            writer.writerow(["\\N" if value is None else value for value in row])
        buffer.seek(0)

        pg_cur.copy_expert(
            f"COPY {table_name} ({col_sql}) FROM STDIN WITH (FORMAT CSV, NULL '\\N')",
            buffer,
        )
        pg_conn.commit()

        copied += len(rows)
        elapsed = max(time.time() - started, 0.001)
        rate = copied / elapsed
        print(f"  copied {copied:,}/{total_rows:,} rows ({rate:,.0f} rows/sec)", flush=True)


def reset_pg(pg_conn) -> None:
    with pg_conn.cursor() as cur:
        cur.execute("""
            TRUNCATE TABLE
                product_sizes,
                daily_inventory_snapshots,
                daily_sales_analytics,
                scraper_errors,
                scraper_runs,
                crawl_state,
                brands,
                products
            RESTART IDENTITY;
        """)
    pg_conn.commit()


def get_pg_table_count(pg_conn, table_name: str) -> int:
    with pg_conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return int(cur.fetchone()[0] or 0)


def print_pg_counts(pg_conn) -> None:
    with pg_conn.cursor() as cur:
        for table in ("products", "product_sizes", "daily_inventory_snapshots", "daily_sales_analytics", "brands"):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"{table}: {int(cur.fetchone()[0] or 0):,}")


def main() -> int:
    sqlite_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SQLITE_PATH
    print(f"SQLite source: {sqlite_path}")

    sqlite_conn = open_sqlite(sqlite_path)
    pg_conn = psycopg2.connect(**load_pg_dsn())
    pg_conn.autocommit = False

    with pg_conn.cursor() as cur:
        cur.execute("SET synchronous_commit TO OFF;")
    pg_conn.commit()

    try:
        existing_products = get_pg_table_count(pg_conn, "products")
        if existing_products > 0:
            print(
                f"Refusing to restore because PostgreSQL already has {existing_products:,} products. "
                "This safe mode only restores into an empty catalog."
            )
            return 2

        print("PostgreSQL catalog is empty. Starting safe restore without destructive reset...")
        for table in TABLES:
            copy_table(sqlite_conn, pg_conn, table["name"], table["columns"])
        print("\nRestore complete. Final PostgreSQL counts:")
        print_pg_counts(pg_conn)
    finally:
        sqlite_conn.close()
        pg_conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
