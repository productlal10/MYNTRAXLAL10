"""
duckdb_analytics.py
High-Performance DuckDB Analytics Engine for Myntra E-commerce Dataset.
Provides vectorized GROUP BY, aggregations, percentiles, and multi-dimensional reporting.
"""

import duckdb
import os
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/myntra_analytics.duckdb")


class DuckDBAnalytics:
    """Thread-safe connection and query runner for DuckDB analytics."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(DuckDBAnalytics, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = DUCKDB_PATH):
        if self._initialized:
            return
        self.db_path = db_path
        self._local = threading.local()
        self._initialized = True

    def get_conn(self) -> duckdb.DuckDBPyConnection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            # DuckDB allows concurrent read-only connections or in-process connections
            self._local.conn = duckdb.connect(self.db_path, read_only=False)
            self._local.conn.execute("PRAGMA threads=4;")
            self._local.conn.execute("PRAGMA memory_limit='2GB';")
        return self._local.conn

    def query_df(self, sql: str, params: Optional[list] = None):
        conn = self.get_conn()
        if params:
            return conn.execute(sql, params).fetchdf()
        return conn.execute(sql).fetchdf()

    def query_dicts(self, sql: str, params: Optional[list] = None) -> List[Dict[str, Any]]:
        conn = self.get_conn()
        if params:
            rel = conn.execute(sql, params)
        else:
            rel = conn.execute(sql)
        cols = [desc[0] for desc in rel.description]
        rows = rel.fetchall()
        return [dict(zip(cols, row)) for row in rows]

    def query_one(self, sql: str, params: Optional[list] = None) -> Optional[Dict[str, Any]]:
        rows = self.query_dicts(sql, params)
        return rows[0] if rows else None

    # ─────────────────────────────────────────────────────────────
    # Analytics Methods
    # ─────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Calculates global catalog KPIs instantly using DuckDB vectorized aggregates."""
        conn = self.get_conn()
        res = conn.execute("""
            SELECT 
                COUNT(*) AS total_products,
                COUNT(DISTINCT brand) AS total_brands,
                COALESCE(AVG(selling_price), 0) AS avg_selling_price,
                COALESCE(AVG(mrp), 0) AS avg_mrp,
                COALESCE(AVG(discount_percentage), 0) AS avg_discount,
                COALESCE(AVG(average_rating), 0) AS avg_rating,
                SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) AS in_stock_count,
                SUM(CASE WHEN is_myntra_label = 1 THEN 1 ELSE 0 END) AS myntra_label_count,
                SUM(CASE WHEN is_in_stock = 1 THEN selling_price ELSE 0 END) AS total_inventory_valuation
            FROM analytics_products
        """).fetchone()

        if not res or res[0] == 0:
            return {"total_products": 0, "total_brands": 0}

        total_prod = res[0]
        tot_brands = res[1]
        avg_price = float(res[2])
        avg_mrp = float(res[3])
        avg_disc = float(res[4])
        avg_rating = float(res[5])
        in_stock = int(res[6] or 0)
        m_labels = int(res[7] or 0)
        inv_val = float(res[8] or 0.0)

        # Sizes summary
        sizes_res = conn.execute("""
            SELECT 
                COUNT(*) AS total_sku_sizes,
                COALESCE(SUM(inventory_count), 0) AS total_warehouse_units
            FROM analytics_sizes
        """).fetchone()
        tot_sku_sizes = sizes_res[0] if sizes_res else 0
        tot_warehouse_units = sizes_res[1] if sizes_res else 0

        # Category breakdown
        cat_breakdown = self.query_dicts("""
            SELECT 
                category,
                COUNT(*) AS count,
                COALESCE(AVG(selling_price), 0) AS avg_price,
                COALESCE(AVG(discount_percentage), 0) AS avg_discount
            FROM analytics_products
            GROUP BY category
            ORDER BY count DESC
        """)

        # Gender breakdown
        gender_breakdown = self.query_dicts("""
            SELECT 
                gender,
                COUNT(*) AS count,
                COALESCE(AVG(selling_price), 0) AS avg_price
            FROM analytics_products
            GROUP BY gender
            ORDER BY count DESC
        """)

        return {
            "total_products": total_prod,
            "total_brands": tot_brands,
            "avg_selling_price": round(avg_price, 2),
            "avg_mrp": round(avg_mrp, 2),
            "avg_discount": round(avg_disc, 1),
            "avg_rating": round(avg_rating, 2),
            "in_stock_count": in_stock,
            "in_stock_percentage": round((in_stock / total_prod * 100), 1) if total_prod else 0,
            "myntra_label_count": m_labels,
            "myntra_label_percentage": round((m_labels / total_prod * 100), 1) if total_prod else 0,
            "total_inventory_valuation": round(inv_val, 2),
            "total_sku_sizes": tot_sku_sizes,
            "total_warehouse_units": tot_warehouse_units,
            "category_breakdown": cat_breakdown,
            "gender_breakdown": gender_breakdown
        }

    def get_category_intelligence(self) -> Dict[str, Any]:
        """Calculates multi-dimensional category & sub-category intelligence."""
        categories = self.query_dicts("""
            SELECT 
                category,
                COUNT(*) AS total_skus,
                COALESCE(AVG(selling_price), 0) AS avg_price,
                COALESCE(MIN(selling_price), 0) AS min_price,
                COALESCE(MAX(selling_price), 0) AS max_price,
                COALESCE(AVG(discount_percentage), 0) AS avg_discount,
                COALESCE(AVG(average_rating), 0) AS avg_rating,
                SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) AS in_stock_count,
                COUNT(DISTINCT brand) AS brand_count
            FROM analytics_products
            GROUP BY category
            ORDER BY total_skus DESC
        """)

        subcategories = self.query_dicts("""
            SELECT 
                category,
                sub_category,
                COUNT(*) AS sku_count,
                COALESCE(AVG(selling_price), 0) AS avg_price,
                COALESCE(AVG(discount_percentage), 0) AS avg_discount,
                COALESCE(AVG(average_rating), 0) AS avg_rating
            FROM analytics_products
            GROUP BY category, sub_category
            ORDER BY sku_count DESC
        """)

        return {
            "status": "success",
            "categories": categories,
            "subcategories": subcategories
        }

    def get_price_intelligence(self, category: Optional[str] = None, brand: Optional[str] = None) -> Dict[str, Any]:
        """Vectorized price distribution, percentiles (25th, 50th median, 75th, 90th), and discount tiers."""
        where_clauses = []
        params = []
        if category and category.lower() != "all":
            where_clauses.append("category = ?")
            params.append(category)
        if brand and brand.lower() != "all":
            where_clauses.append("brand = ?")
            params.append(brand)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Price Stats & Percentiles
        stats_sql = f"""
            SELECT 
                COUNT(*) AS total_count,
                COALESCE(AVG(selling_price), 0) AS mean_price,
                COALESCE(MEDIAN(selling_price), 0) AS median_price,
                COALESCE(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY selling_price), 0) AS p25_price,
                COALESCE(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY selling_price), 0) AS p75_price,
                COALESCE(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY selling_price), 0) AS p90_price,
                COALESCE(MIN(selling_price), 0) AS min_price,
                COALESCE(MAX(selling_price), 0) AS max_price,
                COALESCE(AVG(discount_percentage), 0) AS avg_discount
            FROM analytics_products
            {where_sql}
        """
        stats = self.query_one(stats_sql, params)

        # Price Distribution Buckets
        dist_sql = f"""
            SELECT 
                CASE
                    WHEN selling_price < 500   THEN 'Under ₹500'
                    WHEN selling_price < 1000  THEN '₹500 - ₹1,000'
                    WHEN selling_price < 2000  THEN '₹1,000 - ₹2,000'
                    WHEN selling_price < 3000  THEN '₹2,000 - ₹3,000'
                    WHEN selling_price < 5000  THEN '₹3,000 - ₹5,000'
                    WHEN selling_price < 10000 THEN '₹5,000 - ₹10,000'
                    ELSE 'Above ₹10,000'
                END AS price_bucket,
                COUNT(*) AS count,
                COALESCE(AVG(selling_price), 0) AS avg_price,
                COALESCE(AVG(discount_percentage), 0) AS avg_discount
            FROM analytics_products
            {where_sql}
            GROUP BY price_bucket
            ORDER BY count DESC
        """
        distribution = self.query_dicts(dist_sql, params)

        # Discount Tier Breakdown
        disc_sql = f"""
            SELECT 
                CASE
                    WHEN discount_percentage = 0  THEN 'No Discount'
                    WHEN discount_percentage < 20 THEN '1-19% Off'
                    WHEN discount_percentage < 40 THEN '20-39% Off'
                    WHEN discount_percentage < 60 THEN '40-59% Off'
                    WHEN discount_percentage < 80 THEN '60-79% Off'
                    ELSE '80%+ Off'
                END AS discount_tier,
                COUNT(*) AS count,
                COALESCE(AVG(selling_price), 0) AS avg_price
            FROM analytics_products
            {where_sql}
            GROUP BY discount_tier
            ORDER BY count DESC
        """
        discount_tiers = self.query_dicts(disc_sql, params)

        return {
            "status": "success",
            "stats": stats or {},
            "price_distribution": distribution,
            "discount_tiers": discount_tiers
        }

    def get_fabric_intelligence(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Analyzes fabric market share, price positioning, and ratings."""
        where_sql = "WHERE fabric IS NOT NULL AND TRIM(fabric) != ''"
        params = []
        if category and category.lower() != "all":
            where_sql += " AND category = ?"
            params.append(category)

        sql = f"""
            SELECT 
                fabric,
                COUNT(*) AS total_skus,
                COALESCE(AVG(selling_price), 0) AS avg_price,
                COALESCE(AVG(discount_percentage), 0) AS avg_discount,
                COALESCE(AVG(average_rating), 0) AS avg_rating,
                SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) AS in_stock_count
            FROM analytics_products
            {where_sql}
            GROUP BY fabric
            ORDER BY total_skus DESC
            LIMIT 30
        """
        fabrics = self.query_dicts(sql, params)
        return {"status": "success", "fabrics": fabrics}

    def get_size_intelligence(self, category: Optional[str] = None, brand: Optional[str] = None) -> Dict[str, Any]:
        """Size availability curves and warehouse unit distribution."""
        where_clauses = ["s.available = 1"]
        params = []
        if category and category.lower() != "all":
            where_clauses.append("p.category = ?")
            params.append(category)
        if brand and brand.lower() != "all":
            where_clauses.append("p.brand = ?")
            params.append(brand)

        where_sql = "WHERE " + " AND ".join(where_clauses)

        sql = f"""
            SELECT 
                s.size,
                COUNT(DISTINCT s.product_id) AS sku_count,
                COALESCE(SUM(s.inventory_count), 0) AS total_inventory_units,
                COALESCE(AVG(p.selling_price), 0) AS avg_price,
                COALESCE(AVG(p.discount_percentage), 0) AS avg_discount
            FROM analytics_sizes s
            JOIN analytics_products p ON p.product_id = s.product_id
            {where_sql}
            GROUP BY s.size
            ORDER BY sku_count DESC
            LIMIT 25
        """
        sizes = self.query_dicts(sql, params)
        return {"status": "success", "sizes": sizes}


# Global singleton instance
analytics_db = DuckDBAnalytics()
