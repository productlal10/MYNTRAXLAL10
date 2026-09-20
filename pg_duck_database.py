"""
pg_duck_database.py
Unified Dual-Database Storage & Analytics Layer:
  - PostgreSQL -> Transactional CRUD, product catalog, crawl checkpoints, scraper logs, snapshots
  - DuckDB     -> Vectorized analytics, multi-dimensional GROUP BY, price intelligence, KPIs
"""

import psycopg2
import psycopg2.extras
import json
import os
import threading
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, Any, Optional, Set, List
from dotenv import load_dotenv

from config import (
    PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DBNAME,
    DUCKDB_PATH
)
from duckdb_analytics import analytics_db


def normalize_fashion_category(raw_cat: str, title: str = "", product_url: str = "", sub_cat: str = "") -> str:
    raw = (raw_cat or "").strip()
    u = (product_url or "").lower()
    t = (title or "").lower()
    s = (sub_cat or "").lower()

    if raw in ("Clothing", "", "Apparel") or not raw:
        if "/shirts/" in u or "-shirt" in u or "shirt" in t or s == "topwear":
            return "Shirts"
        elif "/jeans/" in u or "/denims/" in u or "jean" in t or "denim" in t or s == "bottomwear":
            return "Jeans"
        elif "western" in u or "/dresses/" in u or "/tops/" in u or "/jumpsuit" in u or "/skirts/" in u or "/co-ords/" in u or "dress" in t or "skirt" in t or "top" in t:
            return "Western Wear"
        return "Shirts"

    if raw.lower() in ("shirts", "shirt", "casual shirts", "formal shirts"):
        return "Shirts"
    if raw.lower() in ("jeans", "jean", "denims", "denim"):
        return "Jeans"
    if raw.lower() in ("western wear", "western-wear", "women-western-wear", "dresses", "dress"):
        return "Western Wear"
    return raw


class Database:
    """Thread-safe Dual-Database Manager: PostgreSQL (CRUD) + DuckDB (Analytics)."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DUCKDB_PATH
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self.pg_dsn = {
            "host": PG_HOST,
            "port": PG_PORT,
            "user": PG_USER,
            "password": PG_PASSWORD,
            "dbname": PG_DBNAME,
        }
        self.duckdb = analytics_db

    def _get_connection(self) -> psycopg2.extensions.connection:
        """Returns thread-local PostgreSQL connection with automatic reconnection."""
        if not hasattr(self._local, "conn") or self._local.conn is None or self._local.conn.closed != 0:
            self._local.conn = psycopg2.connect(**self.pg_dsn)
            self._local.conn.autocommit = True
        return self._local.conn

    def init_db(self):
        """Initializes database schema and verified connectivity."""
        pass  # Schema is managed via pg_schema.py and DuckDB builder

    def save_product(self, product_data: Dict[str, Any]) -> bool:
        """Saves or updates a product and its sizes in PostgreSQL."""
        conn = self._get_connection()
        p_info = product_data.get("product_info", {})
        pricing = product_data.get("pricing", {})
        inv_sizes = product_data.get("inventory_and_sizes", {})
        specs = product_data.get("specifications", {})
        ratings = product_data.get("ratings_and_reviews") or product_data.get("ratings") or {}

        product_id = p_info.get("product_id")
        if not product_id:
            return False

        full_json = json.dumps(product_data, ensure_ascii=False)
        now = datetime.utcnow()

        fit_val = inv_sizes.get("fit") or specs.get("fit") or ""
        fabric_val = specs.get("fabric") or ""
        pattern_val = specs.get("pattern") or ""
        color_val = p_info.get("primary_color") or specs.get("color") or specs.get("primary_color") or product_data.get("primary_color") or "Multicolor"
        hex_val = p_info.get("color_hex") or specs.get("color_hex") or product_data.get("color_hex") or "#0f172a"

        def _to_str(val, default=""):
            if isinstance(val, dict):
                return str(val.get("typeName") or val.get("name") or val.get("value") or default)
            return str(val) if val is not None else default

        try:
            clean_cat = normalize_fashion_category(
                _to_str(p_info.get("category")),
                _to_str(p_info.get("title")),
                _to_str(p_info.get("product_url")),
                _to_str(p_info.get("sub_category"))
            )

            cur = conn.cursor()
            cur.execute("""
                INSERT INTO products (
                    product_id, sku, brand, is_myntra_label, brand_type, title, category, sub_category, gender,
                    product_url, mrp, selling_price, discount_percentage, is_in_stock,
                    fit, fabric, pattern, primary_color, color_hex, average_rating, total_ratings_count, total_reviews_count,
                    full_data_json, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(product_id) DO UPDATE SET
                    sku=EXCLUDED.sku,
                    brand=EXCLUDED.brand,
                    is_myntra_label=EXCLUDED.is_myntra_label,
                    brand_type=EXCLUDED.brand_type,
                    title=EXCLUDED.title,
                    category=EXCLUDED.category,
                    sub_category=EXCLUDED.sub_category,
                    gender=EXCLUDED.gender,
                    product_url=EXCLUDED.product_url,
                    mrp=EXCLUDED.mrp,
                    selling_price=EXCLUDED.selling_price,
                    discount_percentage=EXCLUDED.discount_percentage,
                    is_in_stock=EXCLUDED.is_in_stock,
                    fit=EXCLUDED.fit,
                    fabric=EXCLUDED.fabric,
                    pattern=EXCLUDED.pattern,
                    primary_color=EXCLUDED.primary_color,
                    color_hex=EXCLUDED.color_hex,
                    average_rating=EXCLUDED.average_rating,
                    total_ratings_count=EXCLUDED.total_ratings_count,
                    total_reviews_count=EXCLUDED.total_reviews_count,
                    full_data_json=EXCLUDED.full_data_json,
                    updated_at=EXCLUDED.updated_at;
            """, (
                product_id,
                _to_str(p_info.get("sku")),
                _to_str(p_info.get("brand")),
                1 if p_info.get("is_myntra_label") else 0,
                _to_str(p_info.get("brand_type")),
                _to_str(p_info.get("title")),
                clean_cat,
                _to_str(p_info.get("sub_category")),
                _to_str(p_info.get("gender")),
                _to_str(p_info.get("product_url")),
                float(pricing.get("mrp", 0.0) or 0.0),
                float(pricing.get("selling_price", 0.0) or 0.0),
                int(pricing.get("discount_percentage", 0) or 0),
                1 if inv_sizes.get("is_in_stock", True) else 0,
                fit_val,
                fabric_val,
                pattern_val,
                color_val,
                hex_val,
                float(ratings.get("average_rating", 0.0) or 0.0),
                int(ratings.get("total_ratings_count", 0) or 0),
                int(ratings.get("total_reviews_count", 0) or 0),
                full_json,
                now
            ))

            # Sizes
            cur.execute("DELETE FROM product_sizes WHERE product_id = %s;", (product_id,))
            sizes = inv_sizes.get("sizes_available", [])
            if sizes:
                size_rows = [
                    (
                        product_id,
                        _to_str(s.get("size")),
                        int(s.get("sku_id") or 0) if str(s.get("sku_id", "")).isdigit() else 0,
                        1 if s.get("available", False) else 0,
                        int(s.get("inventory_count", 0) or 0)
                    )
                    for s in sizes
                ]
                psycopg2.extras.execute_batch(
                    cur,
                    "INSERT INTO product_sizes (product_id, size, sku_id, available, inventory_count) VALUES (%s, %s, %s, %s, %s)",
                    size_rows
                )

            return True
        except Exception as e:
            print(f"[PostgreSQL Error] Failed to save product {product_id}: {e}")
            return False

    def is_product_scraped(self, product_id: int) -> bool:
        """Checks if a product exists in PostgreSQL."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM products WHERE product_id = %s LIMIT 1;", (product_id,))
        return cur.fetchone() is not None

    def get_scraped_product_ids(self) -> Set[int]:
        """Returns set of all product IDs in PostgreSQL."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT product_id FROM products;")
        return {r[0] for r in cur.fetchall()}

    def save_crawl_state(self, category: str, brand: str, page: int, items_scraped: int, status: str = "IN_PROGRESS"):
        """Saves current checkpoint in PostgreSQL."""
        conn = self._get_connection()
        cur = conn.cursor()
        now = datetime.utcnow()
        cur.execute("""
            INSERT INTO crawl_state (category, brand, page, items_scraped, status, last_scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT(category, brand) DO UPDATE SET
                page=EXCLUDED.page,
                items_scraped=EXCLUDED.items_scraped,
                status=EXCLUDED.status,
                last_scraped_at=EXCLUDED.last_scraped_at;
        """, (category, brand, page, items_scraped, status, now))

    def get_crawl_state(self, category: str, brand: str) -> Optional[Dict[str, Any]]:
        """Retrieves checkpoint state from PostgreSQL."""
        conn = self._get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT category, brand, page, items_scraped, status, last_scraped_at FROM crawl_state WHERE category = %s AND brand = %s;",
            (category, brand)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    # ─────────────────────────────────────────────────────────────
    # Analytics Endpoints (Delegated to DuckDB for Maximum Speed)
    # ─────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Global catalog KPIs powered by DuckDB columnar engine."""
        return self.duckdb.get_stats()

    def get_price_intelligence(self, category: Optional[str] = None, brand: Optional[str] = None) -> Dict[str, Any]:
        """Price intelligence, histogram buckets, and percentiles."""
        return self.duckdb.get_price_intelligence(category=category, brand=brand)

    def get_category_intelligence(self) -> Dict[str, Any]:
        """Category & sub-category multi-dimensional intelligence."""
        return self.duckdb.get_category_intelligence()

    def get_fabric_intelligence(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Fabric share, pricing, and ratings."""
        return self.duckdb.get_fabric_intelligence(category=category)

    def get_size_inventory_analytics(self, category: Optional[str] = None, brand: Optional[str] = None) -> Dict[str, Any]:
        """Size curves and warehouse units distribution."""
        return self.duckdb.get_size_intelligence(category=category, brand=brand)

    def get_scraper_runs(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Scraper execution history from PostgreSQL."""
        conn = self._get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM scraper_runs ORDER BY started_at DESC LIMIT %s", (limit,))
        return [dict(r) for r in cur.fetchall()]

    def get_scraper_errors(self, run_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Scraper error logs from PostgreSQL."""
        conn = self._get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if run_id:
            cur.execute("SELECT * FROM scraper_errors WHERE run_id = %s ORDER BY created_at DESC LIMIT %s", (run_id, limit))
        else:
            cur.execute("SELECT * FROM scraper_errors ORDER BY created_at DESC LIMIT %s", (limit,))
        return [dict(r) for r in cur.fetchall()]
