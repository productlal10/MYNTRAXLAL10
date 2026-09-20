"""Utility script to reset PostgreSQL catalog data and local export artifacts."""

import os
from pathlib import Path

import duckdb
import psycopg2
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DUCKDB_PATH = DATA_DIR / "myntra_analytics.duckdb"
PG_DSN = {
    "host": os.getenv("PG_HOST", "127.0.0.1"),
    "port": int(os.getenv("PG_PORT", 5432)),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD", "alan1234"),
    "dbname": os.getenv("PG_DBNAME", "myntra"),
}


def reset_database():
    print("=" * 60)
    print("RESETTING MYNTRA POSTGRESQL CATALOG & EXPORT DATA")
    print("=" * 60)

    try:
        conn = psycopg2.connect(**PG_DSN)
        conn.autocommit = False
        cur = conn.cursor()

        print("--> Clearing products table...")
        cur.execute("TRUNCATE TABLE products RESTART IDENTITY CASCADE;")

        print("--> Resetting brand product counters to 0 in brands directory...")
        cur.execute(
            """
            UPDATE brands
            SET shirts_count = 0,
                denims_count = 0,
                western_count = 0,
                total_count = 0,
                crawled_status = 'PENDING',
                updated_at = NOW();
            """
        )

        conn.commit()
        conn.close()
        print("[✓] PostgreSQL catalog tables cleared successfully.")
    except Exception as exc:
        raise RuntimeError(f"Failed to reset PostgreSQL catalog data: {exc}") from exc

    if DUCKDB_PATH.exists():
        try:
            duck = duckdb.connect(str(DUCKDB_PATH))
            for table_name in [
                "analytics_products",
                "analytics_sizes",
                "analytics_sales",
                "analytics_snapshots",
                "brands",
            ]:
                duck.execute(f"DROP TABLE IF EXISTS {table_name};")
            for view_name in [
                "v_brand_summary",
                "v_category_summary",
                "v_price_distribution",
            ]:
                duck.execute(f"DROP VIEW IF EXISTS {view_name};")
            duck.close()
            print("[✓] Cleared DuckDB analytics tables/views")
        except Exception:
            try:
                DUCKDB_PATH.unlink()
                print("[✓] Removed DuckDB analytics database")
            except Exception:
                pass

    # Reset data export files
    csv_prod = DATA_DIR / "myntra_shirts_denims.csv"
    if csv_prod.exists():
        with open(csv_prod, "w", encoding="utf-8") as f:
            f.write(
                "product_id,sku,brand,is_myntra_label,brand_type,title,category,sub_category,gender,selling_price,mrp,discount_percentage,in_stock,total_inventory_units,sizes_available_count,average_rating,total_ratings_count,total_reviews_count,fabric,fit,product_url\n"
            )
        print("[✓] Reset myntra_shirts_denims.csv header")

    csv_size = DATA_DIR / "myntra_size_inventory.csv"
    if csv_size.exists():
        with open(csv_size, "w", encoding="utf-8") as f:
            f.write("product_id,brand,brand_type,title,category,gender,selling_price,size,sku_id,available,inventory_count,product_url\n")
        print("[✓] Reset myntra_size_inventory.csv header")

    jsonl_file = DATA_DIR / "products_shirts_denims.jsonl"
    if jsonl_file.exists():
        with open(jsonl_file, "w", encoding="utf-8") as f:
            pass
        print("[✓] Cleared products_shirts_denims.jsonl")

    sample_json = DATA_DIR / "products_sample.json"
    if sample_json.exists():
        with open(sample_json, "w", encoding="utf-8") as f:
            f.write("[]")
        print("[✓] Reset products_sample.json")

    # Clear logs
    for log_path in LOGS_DIR.glob("*.log"):
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                pass
            print(f"[✓] Truncated log file: {log_path.name}")
        except Exception:
            pass

    print("=" * 60)
    print("ALL CATALOG DATA RESET TO ZERO. READY FOR FRESH CRAWL.")
    print("=" * 60)


if __name__ == "__main__":
    reset_database()
