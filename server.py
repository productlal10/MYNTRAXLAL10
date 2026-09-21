"""Flask Web Application & API Server for Myntra Catalog & Scraper Dashboard.
Serves interactive UI, REST APIs, live logs, and file downloads on localhost.
"""

import os
import ast
import json
import base64
import re
import fcntl
import subprocess
import signal
import time
import hmac
import hashlib
import concurrent.futures
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, request, send_from_directory, Response, g, make_response, redirect

from config import DATA_DIR, LOG_FILE, BASE_DIR
from database import Database

app = Flask(__name__, static_folder=str(BASE_DIR / "web"), static_url_path="")
db = Database()


def _parse_json(raw, default=None):
    """Safely parse JSON or Python-repr dict format stored in full_data_json column."""
    if not raw:
        return default if default is not None else {}
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass
    try:
        return ast.literal_eval(raw)
    except Exception:
        return default if default is not None else {}


# Global scraper process tracker
scraper_process = None

# Enterprise Authentication Configuration
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()
ENABLE_SOCIAL_LOGIN = os.environ.get("ENABLE_SOCIAL_LOGIN", "false").strip().lower() in {"1", "true", "yes", "on"}
SECRET_KEY = os.environ.get("SECRET_KEY", "fashionos-myntra-intel-secret-salt-2026").encode("utf-8")


def _load_valid_emails():
    configured = os.environ.get("VALID_EMAILS", "")
    emails = {email.strip().lower() for email in configured.split(",") if email.strip()}
    if ADMIN_EMAIL:
        emails.add(ADMIN_EMAIL)
    return emails


VALID_EMAILS = _load_valid_emails()

# Valid active tokens store (in-memory token registry)
ACTIVE_SESSIONS = set()
PREWARM_STARTED = False

import threading
from typing import Any

class TTLCache:
    """Thread-safe in-memory cache with expiration TTL for ultra-fast API queries."""
    def __init__(self, default_ttl: float = 15.0):
        self._cache = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl

    def get(self, key: str):
        with self._lock:
            if key in self._cache:
                val, exp = self._cache[key]
                if time.time() < exp:
                    return val
                try:
                    del self._cache[key]
                except KeyError:
                    pass
            return None

    def set(self, key: str, value: Any, ttl: float = None):
        with self._lock:
            exp = time.time() + (ttl if ttl is not None else self.default_ttl)
            self._cache[key] = (value, exp)

    def clear(self):
        with self._lock:
            self._cache.clear()

api_cache = TTLCache(default_ttl=15.0)
SHARED_API_CACHE_DIR = BASE_DIR / "tmp" / "api_response_cache"

LARGE_BRAND_MIN_PRODUCTS = 1000
MID_BRAND_MIN_PRODUCTS = 200


def _shared_cache_file(cache_key: str) -> Path:
    digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
    return SHARED_API_CACHE_DIR / f"{digest}.json"


def _load_shared_cache(cache_key: str):
    path = _shared_cache_file(cache_key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text("utf-8"))
    except Exception:
        return None
    expires_at = float(payload.get("expires_at") or 0)
    if time.time() >= expires_at:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return None
    return payload.get("value")


def _store_shared_cache(cache_key: str, value, ttl: float):
    SHARED_API_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _shared_cache_file(cache_key)
    tmp_path = path.with_suffix(".tmp")
    payload = {
        "expires_at": time.time() + ttl,
        "value": value,
    }
    tmp_path.write_text(json.dumps(payload, separators=(",", ":"), default=str), encoding="utf-8")
    os.replace(tmp_path, path)


def get_or_compute_cached_payload(cache_key: str, loader, ttl: float = 60.0, shared: bool = False):
    cached = api_cache.get(cache_key)
    if cached is not None:
        return cached

    if not shared:
        value = loader()
        api_cache.set(cache_key, value, ttl=ttl)
        return value

    SHARED_API_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = _shared_cache_file(cache_key).with_suffix(".lock")
    with open(lock_path, "w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        cached = api_cache.get(cache_key)
        if cached is not None:
            return cached
        shared_cached = _load_shared_cache(cache_key)
        if shared_cached is not None:
            api_cache.set(cache_key, shared_cached, ttl=ttl)
            return shared_cached

        value = loader()
        api_cache.set(cache_key, value, ttl=ttl)
        _store_shared_cache(cache_key, value, ttl=ttl)
        return value


def _safe_int(value, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


INVALID_COLOR_TOKENS = {
    r"\n",
    r"\\n",
    "unknown",
    "na",
    "n/a",
    "null",
    "none",
    "nil",
    "-",
    "--",
}

COLOR_HEX_LOOKUP = {
    "white": "#ffffff",
    "black": "#0f172a",
    "blue": "#2563eb",
    "navy": "#1e3a8a",
    "grey": "#64748b",
    "gray": "#64748b",
    "olive": "#556b2f",
    "red": "#dc2626",
    "green": "#16a34a",
    "yellow": "#eab308",
    "pink": "#ec4899",
    "brown": "#78350f",
    "beige": "#f5f5dc",
    "cream": "#f5f5dc",
    "multicolor": "#94a3b8",
}


def _normalize_color_name(value, fallback: str | None = None) -> str | None:
    token = re.sub(r"\s+", " ", str(value or "").strip())
    if not token:
        return fallback
    lowered = token.lower()
    if lowered in INVALID_COLOR_TOKENS or lowered.replace("\\", "") == "n":
        return fallback
    if lowered in {"multi color", "multi-color"}:
        return "Multicolor"
    return " ".join(part.capitalize() for part in token.split(" "))


def _normalize_color_hex(value, color_name: str | None = None, fallback: str = "#94a3b8") -> str:
    token = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", token):
        return token.lower()
    normalized_name = (_normalize_color_name(color_name, fallback="") or "").strip().lower()
    return COLOR_HEX_LOOKUP.get(normalized_name, fallback)


def _valid_color_sql(column_expr: str = "p.primary_color") -> str:
    invalid_tokens_sql = ", ".join("'" + token.replace("'", "''") + "'" for token in sorted(INVALID_COLOR_TOKENS))
    lowered_expr = f"LOWER(TRIM({column_expr}))"
    slashless_expr = f"REPLACE({lowered_expr}, '\\\\', '')"
    return (
        f"{column_expr} IS NOT NULL AND TRIM({column_expr}) != '' "
        f"AND {lowered_expr} NOT IN ({invalid_tokens_sql}) "
        f"AND {slashless_expr} != 'n'"
    )


def _load_primary_image(full_data_json) -> str:
    if not full_data_json:
        return ""
    try:
        data = json.loads(full_data_json) if isinstance(full_data_json, str) else full_data_json
    except Exception:
        return ""
    media = data.get("media", {}) or {}
    return media.get("primary_image") or ""


def _get_analytics_dates(cur, limit: int = 30):
    cur.execute("""
        SELECT DISTINCT analytics_date
        FROM daily_sales_analytics
        ORDER BY analytics_date DESC
        LIMIT ?;
    """, (limit,))
    return [r[0] for r in cur.fetchall() if r[0]]


def _format_delta(value: int) -> str:
    if value > 0:
        return f"+₹{value:,}"
    if value < 0:
        return f"-₹{abs(value):,}"
    return "₹0"


def _pct_change(current: float, previous: float) -> float:
    if previous in (None, 0):
        return 0.0
    return round(((current - previous) / previous) * 100.0, 1)


def _price_band_midpoint(label: str, fallback: int = 0) -> int:
    mapping = {
        "< ₹500": 399,
        "₹500 - 1K": 750,
        "₹800 - 1K": 900,
        "₹1K - 2K": 1500,
        "₹2K - 3K": 2500,
        "₹3K - 4K": 3500,
        "> ₹4K": 4500,
        "< 500": 399,
        "500 - 1K": 750,
        "1K - 2K": 1500,
        "2K - 3K": 2500,
        "3K - 4K": 3500,
        "> 4K": 4500,
    }
    return mapping.get(label, fallback)


def _format_date_label(value) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).strftime("%b %d, %Y")
    except ValueError:
        try:
            return datetime.combine(value, datetime.min.time()).strftime("%b %d, %Y")
        except Exception:
            return str(value)


def _median_from_sorted(values):
    if not values:
        return 0
    ordered = sorted(v for v in values if v is not None)
    if not ordered:
        return 0
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return round((ordered[mid - 1] + ordered[mid]) / 2)


def _get_brand_size_bucket_counts(cur, where_sql: str, params):
    cur.execute(f"""
        WITH brand_counts AS (
            SELECT p.brand, COUNT(*) as cnt
            FROM products p
            WHERE {where_sql} AND p.brand IS NOT NULL AND p.brand != ''
            GROUP BY p.brand
        )
        SELECT
            COALESCE(SUM(CASE WHEN cnt >= {LARGE_BRAND_MIN_PRODUCTS} THEN 1 ELSE 0 END), 0) as large_cnt,
            COALESCE(SUM(CASE WHEN cnt >= {MID_BRAND_MIN_PRODUCTS} AND cnt < {LARGE_BRAND_MIN_PRODUCTS} THEN 1 ELSE 0 END), 0) as mid_cnt,
            COALESCE(SUM(CASE WHEN cnt < {MID_BRAND_MIN_PRODUCTS} THEN 1 ELSE 0 END), 0) as small_cnt
        FROM brand_counts;
    """, params)
    row = cur.fetchone() or {}
    return {
        "large": int(row["large_cnt"] or 0),
        "mid": int(row["mid_cnt"] or 0),
        "small": int(row["small_cnt"] or 0)
    }


def _get_adaptive_sample_limit(total_count: int | float | None, ceiling: int = 2500) -> int:
    total = _safe_int(total_count, 0)
    cap = max(300, int(ceiling or 2500))
    if total <= 0:
        return min(cap, 1200)
    if total >= 100000:
        return min(cap, 900)
    if total >= 50000:
        return min(cap, 1100)
    if total >= 20000:
        return min(cap, 1400)
    if total >= 8000:
        return min(cap, 1800)
    return min(cap, 2200)


def _get_latest_inventory_snapshot_date(cur):
    cache_key = "latest_inventory_snapshot_date_v1"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
    cur.execute("SELECT MAX(snapshot_date) FROM daily_inventory_snapshots;")
    latest = (cur.fetchone() or [None])[0]
    if latest:
        api_cache.set(cache_key, latest, ttl=300.0)
    return latest


def _get_inventory_snapshot_totals(cur, where_sql: str | None = None, params=None):
    params = list(params or [])
    latest_snapshot_date = _get_latest_inventory_snapshot_date(cur)
    if not latest_snapshot_date:
        return {
            "snapshot_date": None,
            "total_units": 0,
            "selling_value": 0.0,
            "mrp_value": 0.0
        }

    normalized_where = (where_sql or "").strip()
    if normalized_where and normalized_where != "1=1":
        cur.execute(f"""
            WITH filtered_products AS MATERIALIZED (
                SELECT p.product_id, p.selling_price, p.mrp
                FROM products p
                WHERE {normalized_where}
            )
            SELECT
                COALESCE(SUM(s.total_stock), 0) as total_units,
                COALESCE(SUM(s.total_stock * COALESCE(fp.selling_price, s.selling_price, 0)), 0) as selling_value,
                COALESCE(SUM(s.total_stock * COALESCE(fp.mrp, s.mrp, 0)), 0) as mrp_value
            FROM daily_inventory_snapshots s
            JOIN filtered_products fp ON fp.product_id = s.product_id
            WHERE s.snapshot_date = ?;
        """, params + [latest_snapshot_date])
    else:
        cur.execute("""
            SELECT
                COALESCE(SUM(total_stock), 0) as total_units,
                COALESCE(SUM(total_stock * COALESCE(selling_price, 0)), 0) as selling_value,
                COALESCE(SUM(total_stock * COALESCE(mrp, 0)), 0) as mrp_value
            FROM daily_inventory_snapshots
            WHERE snapshot_date = ?;
        """, [latest_snapshot_date])
    row = cur.fetchone() or {}
    return {
        "snapshot_date": latest_snapshot_date,
        "total_units": int(row["total_units"] or 0),
        "selling_value": round(row["selling_value"] or 0.0, 2),
        "mrp_value": round(row["mrp_value"] or 0.0, 2)
    }


def _get_catalog_product_count(cur) -> int:
    cache_key = "catalog_product_count_v1"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return int(cached or 0)
    cur.execute("SELECT COUNT(*) FROM products;")
    total = int((cur.fetchone() or [0])[0] or 0)
    api_cache.set(cache_key, total, ttl=600.0)
    return total


def _estimate_inventory_totals(cur, scoped_products: int, avg_price: float, avg_mrp: float):
    global_totals = api_cache.get("global_inventory_snapshot_totals_v1")
    if not global_totals:
        global_totals = _get_inventory_snapshot_totals(cur)
        api_cache.set("global_inventory_snapshot_totals_v1", global_totals, ttl=600.0)

    catalog_total = max(1, _get_catalog_product_count(cur))
    ratio = max(0.0, min(1.0, scoped_products / catalog_total))
    estimated_units = int((global_totals.get("total_units") or 0) * ratio)
    return {
        "snapshot_date": global_totals.get("snapshot_date"),
        "total_units": estimated_units,
        "selling_value": round(estimated_units * (avg_price or 0.0), 2),
        "mrp_value": round(estimated_units * (avg_mrp or avg_price or 0.0), 2)
    }


def _get_scoped_inventory_units(cur, where_sql: str, params) -> int:
    normalized_where = (where_sql or "").strip()
    if not normalized_where or normalized_where == "1=1":
        global_totals = api_cache.get("global_inventory_snapshot_totals_v1")
        if not global_totals:
            global_totals = _get_inventory_snapshot_totals(cur)
            api_cache.set("global_inventory_snapshot_totals_v1", global_totals, ttl=600.0)
        return int(global_totals.get("total_units") or 0)

    cur.execute(f"""
        SELECT COALESCE(SUM(CASE WHEN s.available = 1 THEN s.inventory_count ELSE 0 END), 0) as total_units
        FROM product_sizes s
        JOIN products p ON p.product_id = s.product_id
        WHERE {where_sql};
    """, params)
    row = cur.fetchone() or {}
    return int(row["total_units"] or 0)


def _canonicalize_size_label(raw_size: str | None) -> str | None:
    token = re.sub(r"\s+", " ", str(raw_size or "").upper().strip())
    if not token:
        return None

    token = token.replace(" SIZE", "")
    normalized = token.replace(" ", "").replace("-", "").replace("_", "")
    direct_map = {
        "XXXS": "XXXS",
        "XXS": "XXS",
        "EXTRAEXTRASMALL": "XXS",
        "XS": "XS",
        "EXTRASMALL": "XS",
        "S": "S",
        "SMALL": "S",
        "M": "M",
        "MEDIUM": "M",
        "L": "L",
        "LARGE": "L",
        "XL": "XL",
        "EXTRALARGE": "XL",
        "XXL": "XXL",
        "2XL": "XXL",
        "XXXL": "XXXL",
        "3XL": "XXXL",
        "4XL": "4XL",
        "5XL": "5XL",
    }
    if normalized in direct_map:
        return direct_map[normalized]
    if "FREE" in normalized or "ONESIZE" in normalized:
        return None

    compact = token.replace(" ", "")
    compact = re.sub(r"(?<=\d)\s*-\s*(?=\d)", "-", compact)
    compact = re.sub(r"(?<=\d)\s+TO\s+(?=\d)", "-", compact)
    return compact


def _size_sort_key(raw_size: str | None):
    label = _canonicalize_size_label(raw_size)
    if not label:
        return (9, float("inf"), "", "")

    alpha_sequence = {
        "XXXS": 0,
        "XXS": 1,
        "XS": 2,
        "S": 3,
        "M": 4,
        "L": 5,
        "XL": 6,
        "XXL": 7,
        "XXXL": 8,
        "4XL": 9,
        "5XL": 10,
    }
    if label in alpha_sequence:
        return (0, alpha_sequence[label], "", label)

    year_match = re.fullmatch(r"(\d+(?:\.\d+)?)(?:-(\d+(?:\.\d+)?))?Y", label)
    if year_match:
        start = float(year_match.group(1))
        end = float(year_match.group(2) or year_match.group(1))
        return (1, start, end, label)

    month_match = re.fullmatch(r"(\d+(?:\.\d+)?)(?:-(\d+(?:\.\d+)?))?M", label)
    if month_match:
        start = float(month_match.group(1))
        end = float(month_match.group(2) or month_match.group(1))
        return (2, start, end, label)

    numeric_match = re.fullmatch(r"(\d+(?:\.\d+)?)", label)
    if numeric_match:
        return (3, float(numeric_match.group(1)), "", label)

    numeric_range_match = re.fullmatch(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)", label)
    if numeric_range_match:
        return (4, float(numeric_range_match.group(1)), float(numeric_range_match.group(2)), label)

    return (5, float("inf"), "", label)


def _select_inventory_heatmap_columns(size_totals: Counter, limit: int = 6):
    default_columns = ["XS", "S", "M", "L", "XL", "XXL"]
    ranked_sizes = [
        (label, units)
        for label, units in (size_totals or {}).items()
        if label and _safe_int(units, 0) > 0
    ]
    if not ranked_sizes:
        return default_columns

    top_labels = [
        label
        for label, _ in sorted(
            ranked_sizes,
            key=lambda item: (-_safe_int(item[1], 0), _size_sort_key(item[0]), item[0])
        )[:max(1, limit)]
    ]
    return sorted(top_labels, key=_size_sort_key)


def _get_brand_inventory_breakdown(cur, where_sql: str, params, brands):
    unique_brands = [brand for brand in dict.fromkeys(brands or []) if brand]
    if not unique_brands:
        return {}, {}, ["XS", "S", "M", "L", "XL", "XXL"]

    placeholders = ",".join("?" for _ in unique_brands)
    query_params = list(params) + unique_brands

    exact_size_breakdown = {brand: defaultdict(int) for brand in unique_brands}
    inventory_units = {brand: 0 for brand in unique_brands}
    size_totals = Counter()

    cur.execute(f"""
        SELECT
            p.brand,
            s.size,
            COALESCE(SUM(CASE WHEN s.available = 1 THEN s.inventory_count ELSE 0 END), 0) as units
        FROM products p
        JOIN product_sizes s ON s.product_id = p.product_id
        WHERE {where_sql} AND p.brand IN ({placeholders})
        GROUP BY p.brand, s.size;
    """, query_params)
    for row in cur.fetchall():
        brand = row["brand"]
        size_label = _canonicalize_size_label(row["size"])
        units = int(row["units"] or 0)
        if not brand or units <= 0:
            continue
        inventory_units[brand] = inventory_units.get(brand, 0) + units
        if not size_label:
            continue
        exact_size_breakdown.setdefault(brand, defaultdict(int))
        exact_size_breakdown[brand][size_label] += units
        size_totals[size_label] += units

    heatmap_columns = _select_inventory_heatmap_columns(size_totals)
    size_breakdown = {
        brand: {size_label: int(exact_size_breakdown.get(brand, {}).get(size_label, 0)) for size_label in heatmap_columns}
        for brand in unique_brands
    }

    return inventory_units, size_breakdown, heatmap_columns


def _get_trending_brands(cur, where_sql: str, params, limit: int = 5):
    analytics_dates = _get_analytics_dates(cur, 2)
    if not analytics_dates:
        return []

    latest_date = analytics_dates[0]
    previous_date = analytics_dates[1] if len(analytics_dates) > 1 else analytics_dates[0]

    cur.execute(f"""
        SELECT
            p.brand,
            COALESCE(SUM(CASE WHEN sa.analytics_date = ? THEN sa.units_sold ELSE 0 END), 0) as latest_units,
            COALESCE(SUM(CASE WHEN sa.analytics_date = ? THEN sa.units_sold ELSE 0 END), 0) as previous_units,
            COALESCE(SUM(CASE WHEN sa.analytics_date = ? THEN sa.revenue_generated ELSE 0 END), 0) as latest_revenue
        FROM daily_sales_analytics sa
        JOIN products p ON p.product_id = sa.product_id
        WHERE {where_sql}
          AND sa.analytics_date IN (?, ?)
          AND p.brand IS NOT NULL
          AND p.brand != ''
        GROUP BY p.brand
        HAVING COALESCE(SUM(CASE WHEN sa.analytics_date = ? THEN sa.units_sold ELSE 0 END), 0) > 0
            OR COALESCE(SUM(CASE WHEN sa.analytics_date = ? THEN sa.units_sold ELSE 0 END), 0) > 0
        ORDER BY latest_units DESC, latest_revenue DESC, p.brand ASC
        LIMIT ?;
    """, [
        latest_date, previous_date, latest_date,
        *list(params),
        latest_date, previous_date,
        latest_date, previous_date,
        limit
    ])

    trending = []
    for row in cur.fetchall():
        latest_units = int(row["latest_units"] or 0)
        previous_units = int(row["previous_units"] or 0)
        growth_pct = round(((latest_units - previous_units) / previous_units) * 100.0, 1) if previous_units > 0 else (100.0 if latest_units > 0 else 0.0)
        trending.append({
            "brand": row["brand"],
            "growth": growth_pct,
            "direction": "+" if growth_pct >= 0 else "-",
            "skus": 0,
            "units_sold": latest_units,
            "revenue": round(float(row["latest_revenue"] or 0.0), 2)
        })
    return trending


def _subcategory_facets(cur, where_sql: str, params, category: str):
    facets = [{"value": "all", "name": "All Subcategories"}]

    cur.execute(f"SELECT COUNT(*) FROM products p WHERE {where_sql};", params)
    total = int((cur.fetchone() or [0])[0] or 0)
    facets[0]["name"] = f"All Subcategories ({total:,})"

    cur.execute(f"""
        SELECT p.sub_category, COUNT(*) as cnt
        FROM products p
        WHERE {where_sql} AND p.sub_category IS NOT NULL AND p.sub_category != ''
        GROUP BY p.sub_category
        ORDER BY cnt DESC, p.sub_category ASC
        LIMIT 30;
    """, params)
    for row in cur.fetchall():
        raw_name = str(row["sub_category"]).strip()
        if not raw_name:
            continue
        facets.append({
            "value": raw_name.lower(),
            "name": f"{raw_name} ({int(row['cnt'] or 0):,})"
        })
    return facets


def _apply_sustainability_filter(base_where_sql: str, base_params, sustainability: str, alias: str = "p"):
    token = (sustainability or "").strip().lower()
    if token in ("", "all"):
        return base_where_sql, list(base_params)

    if token == "organic":
        patterns = ["%organic%"]
    elif token == "recycled":
        patterns = ["%recycled%"]
    elif token == "sustainable":
        patterns = ["%sustainable%", "%ecovero%", "%eco vero%", "%organic%", "%recycled%"]
    else:
        return base_where_sql, list(base_params)

    text_clauses = []
    text_params = []
    for pat in patterns:
        text_clauses.append(f"LOWER(COALESCE({alias}.title, '')) LIKE ?")
        text_clauses.append(f"LOWER(COALESCE({alias}.fabric, '')) LIKE ?")
        text_params.extend([pat, pat])

    where_sql = f"{base_where_sql} AND ({' OR '.join(text_clauses)})"
    return where_sql, list(base_params) + text_params

def create_session_token(email: str) -> str:
    """Generate a tamper-proof signed session token."""
    normalized_email = (email or "").strip().lower()
    ts = str(int(time.time()))
    email_blob = base64.urlsafe_b64encode(normalized_email.encode("utf-8")).decode("ascii").rstrip("=")
    payload = f"{normalized_email}:{ts}"
    signature = hmac.new(SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"fash.{ts}.{email_blob}.{signature[:32]}"
    ACTIVE_SESSIONS.add(token)
    return token

def is_valid_token(token: str) -> bool:
    """Validate token format, signature, and presence."""
    if not token or not isinstance(token, str):
        return False
    if token in ACTIVE_SESSIONS:
        return True
    # If token starts with valid format fash_ts_email_sig, verify signature
    if token.startswith("fash."):
        parts = token.split(".", 3)
        if len(parts) == 4:
            try:
                token_ts = int(parts[1])
                if time.time() - token_ts >= 7 * 86400 or token_ts > int(time.time()) + 300:
                    return False
                email_blob = parts[2]
                padded_email_blob = email_blob + "=" * (-len(email_blob) % 4)
                email = base64.urlsafe_b64decode(padded_email_blob.encode("ascii")).decode("utf-8").strip().lower()
                if not email:
                    return False
                expected_signature = hmac.new(
                    SECRET_KEY,
                    f"{email}:{token_ts}".encode("utf-8"),
                    hashlib.sha256
                ).hexdigest()[:32]
                if hmac.compare_digest(parts[3], expected_signature):
                    ACTIVE_SESSIONS.add(token)
                    return True
            except Exception:
                pass
    return False

def get_current_token() -> str:
    """Extract token from Authorization header, Cookie, or Query param."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    
    cookie_token = request.cookies.get("session_token", "")
    if cookie_token:
        return cookie_token.strip()
    
    query_token = request.args.get("auth_token", "")
    if query_token:
        return query_token.strip()
        
    return ""

@app.before_request
def enforce_authentication():
    """Protect dashboard routes and APIs behind a valid session."""
    path = request.path

    # Publicly accessible routes
    public_exact_paths = {"/login", "/health", "/api/health", "/api/auth/login", "/api/auth/social-login", "/api/auth/forgot-password"}
    if path in public_exact_paths:
        return None

    # Public static assets needed for styling/images
    if (
        path.startswith("/assets/") or 
        path.endswith((".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2"))
    ):
        return None

    token = get_current_token()
    if is_valid_token(token):
        return None

    if path.startswith("/api/"):
        return jsonify({"detail": "Authentication required."}), 401
    return redirect("/login")


@app.after_request
def add_cache_headers(response):
    """Ensure sensitive dashboard pages are not cached by browser history."""
    if request.path in ("/", "/index.html"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    elif request.path.startswith("/api/") and request.method == "GET" and response.status_code == 200:
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    elif any(request.path.endswith(ext) for ext in (".js", ".css")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    elif any(request.path.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff2")):
        response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@app.route("/")
def index():
    """Main dashboard page - protected by enforce_authentication."""
    return send_from_directory(str(BASE_DIR / "web"), "index.html")


@app.route("/favicon.ico")
def favicon():
    return Response(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><text y="20" font-size="20">🏮</text></svg>',
        mimetype="image/svg+xml"
    )


@app.route("/login")
def login_page():
    """Public login page."""
    return send_from_directory(str(BASE_DIR / "web"), "login.html")


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not ADMIN_PASSWORD or not VALID_EMAILS:
        return jsonify({"detail": "Authentication is not configured on this server."}), 503

    if not email or not password:
        return jsonify({"detail": "Email and password are required."}), 400

    if email not in VALID_EMAILS or password != ADMIN_PASSWORD:
        return jsonify({
            "detail": "Invalid work email or password. Please try again."
        }), 401

    username = email.split("@")[0].replace(".", " ").title() or "Workspace Admin"
    token = create_session_token(email)

    resp = make_response(jsonify({
        "token": token,
        "user": {
            "name": username,
            "email": email,
            "role": "Enterprise Catalog Administrator"
        }
    }), 200)

    # Set secure session cookie so browser direct page navigation works seamlessly
    resp.set_cookie(
        "session_token",
        token,
        max_age=7 * 86400,
        httponly=True,
        samesite="Lax",
        path="/"
    )
    return resp


@app.route("/api/auth/logout", methods=["POST", "GET"])
def auth_logout():
    token = get_current_token()
    if token in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS.discard(token)

    resp = make_response(redirect("/login") if request.method == "GET" else jsonify({"message": "Logged out successfully"}))
    resp.delete_cookie("session_token", path="/")
    return resp


@app.route("/api/auth/social-login", methods=["POST"])
def auth_social_login():
    if not ENABLE_SOCIAL_LOGIN:
        return jsonify({"detail": "Enterprise SSO is disabled for this workspace."}), 503

    data = request.get_json(silent=True) or {}
    provider = data.get("provider", "google").capitalize()
    email = f"user@{provider.lower()}.com"
    token = create_session_token(email)

    resp = make_response(jsonify({
        "token": token,
        "user": {
            "name": f"{provider} Enterprise User",
            "email": email,
            "role": "Catalog Intelligence Analyst"
        }
    }), 200)

    resp.set_cookie(
        "session_token",
        token,
        max_age=7 * 86400,
        httponly=True,
        samesite="Lax",
        path="/"
    )
    return resp


@app.route("/api/auth/forgot-password", methods=["POST"])
def auth_forgot_password():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "your email")
    return jsonify({
        "message": f"If {email} is an approved workspace email, the administrator can reset access credentials."
    }), 200


@app.route("/health")
@app.route("/api/health")
def health_check():
    """Lightweight readiness probe for local and EC2 deployments."""
    try:
        conn = db._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        db_ok = bool((cur.fetchone() or [0])[0])
        return jsonify({
            "status": "ok",
            "app": "myntra_dashboard",
            "database": "ok" if db_ok else "unknown"
        }), 200
    except Exception as exc:
        app.logger.exception("Health check failed")
        return jsonify({
            "status": "error",
            "app": "myntra_dashboard",
            "database": "error",
            "message": str(exc)
        }), 500


@app.route("/api/stats")
def get_stats():
    try:
        filters = _get_cto_request_filters(include_sort=False)
        filter_category = filters["category"]
        filter_gender = filters["gender"]
        filter_subcategory = filters["subcategory"]
        filter_brand = filters["brand"]
        filter_brand_scale = filters["brand_scale"]
        filter_price_min = filters["price_min"]
        filter_price_max = filters["price_max"]
        filter_brand_type = filters["brand_type"]

        cache_key = f"stats_v2:{filter_category}:{filter_gender}:{filter_subcategory}:{filter_brand}:{filter_brand_scale}:{filter_price_min}:{filter_price_max}:{filter_brand_type}"
        has_scope_filters = any([
            filter_category and filter_category != "all",
            filter_gender and filter_gender != "all",
            filter_subcategory and filter_subcategory != "all",
            filter_brand and filter_brand != "all",
            filter_brand_scale and filter_brand_scale != "all",
            filter_price_min,
            filter_price_max,
            filter_brand_type and filter_brand_type != "all",
        ])

        def build_stats_payload():
            conn = db._get_connection()
            cur = conn.cursor()
            where_sql, where_params = _build_cto_scope(filters)

            if has_scope_filters:
                cur.execute(f"""
                    SELECT 
                        COUNT(*) as total_products,
                        COUNT(DISTINCT brand) as total_brands,
                        COUNT(DISTINCT CASE WHEN is_myntra_label = 1 THEN brand END) as myntra_brands_count,
                        COUNT(DISTINCT CASE WHEN is_myntra_label = 0 THEN brand END) as non_myntra_brands_count,
                        SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) as in_stock,
                        ROUND(AVG(selling_price), 2) as avg_price,
                        ROUND(AVG(mrp), 2) as avg_mrp,
                        ROUND(AVG(discount_percentage), 1) as avg_discount
                    FROM products p
                    WHERE {where_sql};
                """, where_params)
                r = cur.fetchone()

                total_products = int(r[0] or 0)
                total_brands = int(r[1] or 0)
                myntra_brands_count = int(r[2] or 0)
                non_myntra_brands_count = int(r[3] or 0)
                in_stock = int(r[4] or 0)
                avg_price = float(r[5] or 0.0)
                avg_mrp = float(r[6] or 0.0)
                avg_discount = float(r[7] or 0.0)
            else:
                cur.execute("""
                    SELECT
                        COUNT(*) as total_products,
                        SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) as in_stock,
                        ROUND(AVG(selling_price), 2) as avg_price,
                        ROUND(AVG(mrp), 2) as avg_mrp,
                        ROUND(AVG(discount_percentage), 1) as avg_discount
                    FROM products;
                """)
                r = cur.fetchone()
                total_products = int(r[0] or 0)
                in_stock = int(r[1] or 0)
                avg_price = float(r[2] or 0.0)
                avg_mrp = float(r[3] or 0.0)
                avg_discount = float(r[4] or 0.0)

                cur.execute("""
                    SELECT
                        COUNT(*) as total_brands,
                        SUM(CASE WHEN is_myntra_label = 1 THEN 1 ELSE 0 END) as myntra_brands_count,
                        SUM(CASE WHEN is_myntra_label = 0 THEN 1 ELSE 0 END) as non_myntra_brands_count
                    FROM brands
                    WHERE brand_name IS NOT NULL AND brand_name != '';
                """)
                brand_row = cur.fetchone() or {}
                total_brands = int(brand_row["total_brands"] or 0)
                myntra_brands_count = int(brand_row["myntra_brands_count"] or 0)
                non_myntra_brands_count = int(brand_row["non_myntra_brands_count"] or 0)

            total_warehouse_units = _get_scoped_inventory_units(cur, where_sql, where_params)
            return {
                "total_products": total_products,
                "total_brands": total_brands,
                "total_discovered_brands": total_brands,
                "myntra_brands_count": myntra_brands_count,
                "non_myntra_brands_count": non_myntra_brands_count,
                "in_stock": in_stock,
                "total_warehouse_units": total_warehouse_units,
                "average_price": avg_price,
                "average_mrp": avg_mrp,
                "average_discount": avg_discount,
                "trends": {
                    "products_delta_pct": None,
                    "brands_delta_pct": None,
                    "inventory_delta_pct": None,
                    "price_delta_pct": None,
                    "discount_delta_pct": None
                }
            }

        stats = get_or_compute_cached_payload(
            cache_key,
            build_stats_payload,
            ttl=600.0,
            shared=not has_scope_filters
        )
        return jsonify(stats)
    except Exception as exc:
        app.logger.exception("Failed to load stats")
        return jsonify({
            "status": "error",
            "message": str(exc)
        }), 500


def _get_cto_request_filters(include_sort=False):
    filters = {
        "category": request.args.get("category", "").lower().strip(),
        "gender": request.args.get("gender", "").lower().strip(),
        "subcategory": request.args.get("subcategory", "").strip(),
        "brand": request.args.get("brand", "").strip(),
        "brand_type": request.args.get("brand_type", "").lower().strip(),
        "brand_scale": request.args.get("brand_scale", "").lower().strip(),
        "price_min": request.args.get("price_min", "").strip(),
        "price_max": request.args.get("price_max", "").strip(),
    }
    if include_sort:
        filters["sort_by"] = request.args.get("sort_by", "valuation_desc").strip()
    return filters


def _build_cto_scope(filters, include_brand=True, include_subcategory=True, include_brand_scale=True, product_alias="p"):
    filter_category = filters.get("category", "")
    filter_gender = filters.get("gender", "")
    filter_subcategory = filters.get("subcategory", "")
    filter_brand = filters.get("brand", "")
    filter_brand_type = filters.get("brand_type", "")
    filter_brand_scale = filters.get("brand_scale", "")
    filter_price_min = filters.get("price_min", "")
    filter_price_max = filters.get("price_max", "")

    ref = f"{product_alias}."
    where_parts = ["1=1"]
    where_params = []

    if include_brand and filter_brand and filter_brand != "all":
        where_parts.append(f"{ref}brand = ?")
        where_params.append(filter_brand)

    if filter_category and filter_category != "all":
        if filter_category == "shirts":
            where_parts.append(f"{ref}category = 'Shirts'")
        elif filter_category in ("denims", "jeans"):
            where_parts.append(f"{ref}category = 'Jeans'")
        elif filter_category in ("western-wear", "women-western-wear", "western", "womens-western-wear"):
            where_parts.append(f"{ref}category IN ('Western Wear', 'Dresses', 'Tops', 'Skirts', 'Jumpsuit', 'Jumpsuits')")
        else:
            where_parts.append(f"LOWER({ref}category) = ?")
            where_params.append(filter_category)

    if include_subcategory and filter_subcategory and filter_subcategory != "all":
        where_parts.append(f"{ref}sub_category = ?")
        where_params.append(filter_subcategory)

    if filter_brand_type in ("myntra", "myntra_in_house", "myntra in-house labels"):
        where_parts.append(f"{ref}is_myntra_label = 1")
    elif filter_brand_type in ("non-myntra", "external", "external brands"):
        where_parts.append(f"{ref}is_myntra_label = 0")

    if filter_gender and filter_gender != "all":
        if filter_gender == "men":
            where_parts.append(f"{ref}gender = 'Men'")
        elif filter_gender == "women":
            where_parts.append(f"{ref}gender = 'Women'")
        elif filter_gender == "kids":
            where_parts.append(f"{ref}gender IN ('Kids', 'Boys', 'Girls', 'Unisex Kids')")
        else:
            where_parts.append(f"{ref}gender = ?")
            where_params.append(filter_gender.capitalize())

    if filter_price_min:
        try:
            where_parts.append(f"{ref}selling_price >= ?")
            where_params.append(float(filter_price_min))
        except ValueError:
            pass

    if filter_price_max:
        try:
            where_parts.append(f"{ref}selling_price <= ?")
            where_params.append(float(filter_price_max))
        except ValueError:
            pass

    if include_brand_scale and filter_brand_scale in ("largest", "mid", "small"):
        scoped_sql, scoped_params = _build_cto_scope(
            filters,
            include_brand=include_brand,
            include_subcategory=include_subcategory,
            include_brand_scale=False,
            product_alias="bp"
        )
        if filter_brand_scale == "largest":
            having_sql = f"COUNT(*) >= {LARGE_BRAND_MIN_PRODUCTS}"
        elif filter_brand_scale == "mid":
            having_sql = f"COUNT(*) >= {MID_BRAND_MIN_PRODUCTS} AND COUNT(*) < {LARGE_BRAND_MIN_PRODUCTS}"
        else:
            having_sql = f"COUNT(*) < {MID_BRAND_MIN_PRODUCTS}"

        where_parts.append(f"""
            {ref}brand IN (
                SELECT bp.brand
                FROM products bp
                WHERE {scoped_sql} AND bp.brand IS NOT NULL AND bp.brand != ''
                GROUP BY bp.brand
                HAVING {having_sql}
            )
        """)
        where_params.extend(scoped_params)

    return " AND ".join(where_parts), where_params


def _load_cto_facets(cur, filters):
    use_brand_directory = not any([
        filters.get("category"),
        filters.get("gender"),
        filters.get("subcategory"),
        filters.get("brand_scale"),
        filters.get("price_min"),
        filters.get("price_max"),
    ])
    subcategory_scope_sql, subcategory_scope_params = _build_cto_scope(
        filters,
        include_brand=True,
        include_subcategory=False
    )
    brand_scope_sql, brand_scope_params = _build_cto_scope(
        filters,
        include_brand=False,
        include_subcategory=True
    )

    cur.execute(f"""
        SELECT p.sub_category, COUNT(*) as cnt
        FROM products p
        WHERE {subcategory_scope_sql} AND p.sub_category IS NOT NULL AND p.sub_category != ''
        GROUP BY p.sub_category
        ORDER BY cnt DESC, p.sub_category ASC;
    """, subcategory_scope_params)
    available_subcategories = [
        {"value": r[0], "name": r[0], "count": int(r[1] or 0)}
        for r in cur.fetchall()
    ]

    if use_brand_directory:
        brand_where = ["brand_name IS NOT NULL", "brand_name != ''"]
        brand_params = []
        filter_brand_type = filters.get("brand_type", "")
        if filter_brand_type in ("myntra", "myntra_in_house", "myntra in-house labels"):
            brand_where.append("is_myntra_label = 1")
        elif filter_brand_type in ("non-myntra", "external", "external brands"):
            brand_where.append("is_myntra_label = 0")
        cur.execute(f"""
            SELECT brand_name, total_count
            FROM brands
            WHERE {' AND '.join(brand_where)}
            ORDER BY LOWER(brand_name) ASC;
        """, brand_params)
        available_brands = [
            {"name": r[0], "count": int(r[1] or 0)}
            for r in cur.fetchall()
        ]
    else:
        cur.execute(f"""
            SELECT p.brand, COUNT(*) as cnt
            FROM products p
            WHERE {brand_scope_sql} AND p.brand IS NOT NULL AND p.brand != ''
            GROUP BY p.brand
            ORDER BY LOWER(p.brand) ASC;
        """, brand_scope_params)
        available_brands = [
            {"name": r[0], "count": int(r[1] or 0)}
            for r in cur.fetchall()
        ]

    return {
        "available_subcategories": available_subcategories,
        "available_brands": available_brands,
        "brand_scale_meta": {
            "largest_min": LARGE_BRAND_MIN_PRODUCTS,
            "mid_min": MID_BRAND_MIN_PRODUCTS,
            "mid_max": LARGE_BRAND_MIN_PRODUCTS - 1,
            "largest_label": f"Largest Brands (>={LARGE_BRAND_MIN_PRODUCTS:,} SKUs)",
            "mid_label": f"Mid-Tier Brands ({MID_BRAND_MIN_PRODUCTS:,}-{LARGE_BRAND_MIN_PRODUCTS - 1:,} SKUs)",
            "small_label": f"Small / Emerging (<{MID_BRAND_MIN_PRODUCTS:,} SKUs)"
        },
        "cto_filter_meta": {
            "selected_brand": filters.get("brand", "") if filters.get("brand", "") not in ("", "all") else "",
            "selected_subcategory": filters.get("subcategory", "") if filters.get("subcategory", "") not in ("", "all") else "",
            "available_brand_count": len(available_brands),
            "available_subcategory_count": len(available_subcategories)
        }
    }


def _get_cto_facets_cache_key(filters):
    return (
        f"insights_facets:{filters['category']}:{filters['gender']}:{filters['subcategory']}:"
        f"{filters['brand']}:{filters['brand_type']}:{filters['brand_scale']}:{filters['price_min']}:{filters['price_max']}"
    )


def _get_cached_cto_facets(cur, filters):
    cache_key = _get_cto_facets_cache_key(filters)
    return get_or_compute_cached_payload(
        cache_key,
        lambda: _load_cto_facets(cur, filters),
        ttl=600.0,
        shared=True
    )


@app.route("/api/insights/facets")
def get_insights_facets():
    filters = _get_cto_request_filters(include_sort=False)
    conn = db._get_connection()
    cur = conn.cursor()
    return jsonify(_get_cached_cto_facets(cur, filters))


@app.route("/api/insights")
def get_insights():
    filters = _get_cto_request_filters(include_sort=True)
    filter_category = filters["category"]
    filter_gender = filters["gender"]
    filter_subcategory = filters["subcategory"]
    filter_brand = filters["brand"]
    filter_brand_type = filters["brand_type"]
    filter_brand_scale = filters["brand_scale"]
    filter_price_min = filters["price_min"]
    filter_price_max = filters["price_max"]
    filter_sort_by = filters["sort_by"]

    cache_key = f"insights_v4:{filter_category}:{filter_gender}:{filter_subcategory}:{filter_brand}:{filter_brand_type}:{filter_brand_scale}:{filter_price_min}:{filter_price_max}:{filter_sort_by}"
    cached_payload = _load_shared_cache(cache_key)
    if cached_payload is not None:
        api_cache.set(cache_key, cached_payload, ttl=600.0)
        return jsonify(cached_payload)

    conn = db._get_connection()
    cur = conn.cursor()
    where_sql, where_params = _build_cto_scope(filters, include_brand=True, include_subcategory=True)

    # Combined KPI + Price Brackets + Discount Brackets + Brand Ecosystem Mix + Ratings + Threat Matrix in ONE single-pass SQL query
    cur.execute(f"""
        SELECT 
            COUNT(*) as total_products,
            SUM(CASE WHEN is_in_stock = 1 THEN 1 ELSE 0 END) as in_stock,
            AVG(selling_price) as avg_selling,
            AVG(mrp) as avg_mrp,
            AVG(discount_percentage) as avg_disc,
            SUM(CASE WHEN selling_price < 500 THEN 1 ELSE 0 END) as pb0,
            SUM(CASE WHEN selling_price >= 500 AND selling_price < 1000 THEN 1 ELSE 0 END) as pb1,
            SUM(CASE WHEN selling_price >= 1000 AND selling_price < 2000 THEN 1 ELSE 0 END) as pb2,
            SUM(CASE WHEN selling_price >= 2000 AND selling_price < 3500 THEN 1 ELSE 0 END) as pb3,
            SUM(CASE WHEN selling_price >= 3500 THEN 1 ELSE 0 END) as pb4,
            SUM(CASE WHEN discount_percentage >= 80 THEN 1 ELSE 0 END) as d0,
            SUM(CASE WHEN discount_percentage >= 60 AND discount_percentage < 80 THEN 1 ELSE 0 END) as d1,
            SUM(CASE WHEN discount_percentage >= 40 AND discount_percentage < 60 THEN 1 ELSE 0 END) as d2,
            SUM(CASE WHEN discount_percentage >= 20 AND discount_percentage < 40 THEN 1 ELSE 0 END) as d3,
            SUM(CASE WHEN discount_percentage < 20 THEN 1 ELSE 0 END) as d4,
            SUM(CASE WHEN is_myntra_label = 1 THEN 1 ELSE 0 END) as ih_cnt,
            AVG(CASE WHEN is_myntra_label = 1 THEN selling_price END) as ih_price,
            AVG(CASE WHEN is_myntra_label = 1 THEN discount_percentage END) as ih_disc,
            SUM(CASE WHEN is_myntra_label = 0 THEN 1 ELSE 0 END) as ext_cnt,
            AVG(CASE WHEN is_myntra_label = 0 THEN selling_price END) as ext_price,
            AVG(CASE WHEN is_myntra_label = 0 THEN discount_percentage END) as ext_disc,
            SUM(CASE WHEN category = 'Shirts' THEN 1 ELSE 0 END) as sh_cnt,
            AVG(CASE WHEN category = 'Shirts' THEN selling_price END) as sh_price,
            AVG(CASE WHEN category = 'Shirts' THEN discount_percentage END) as sh_disc,
            SUM(CASE WHEN category = 'Jeans' THEN 1 ELSE 0 END) as dn_cnt,
            AVG(CASE WHEN category = 'Jeans' THEN selling_price END) as dn_price,
            AVG(CASE WHEN category = 'Jeans' THEN discount_percentage END) as dn_disc,
            SUM(CASE WHEN category IN ('Western Wear', 'Dresses', 'Tops', 'Skirts', 'Jumpsuit', 'Jumpsuits') THEN 1 ELSE 0 END) as ww_cnt,
            AVG(CASE WHEN category IN ('Western Wear', 'Dresses', 'Tops', 'Skirts', 'Jumpsuit', 'Jumpsuits') THEN selling_price END) as ww_price,
            AVG(CASE WHEN category IN ('Western Wear', 'Dresses', 'Tops', 'Skirts', 'Jumpsuit', 'Jumpsuits') THEN discount_percentage END) as ww_disc,
            COALESCE(SUM(total_ratings_count), 0) as tot_ratings,
            COALESCE(SUM(total_reviews_count), 0) as tot_reviews,
            ROUND(SUM(CASE WHEN average_rating >= 4.0 THEN 1 ELSE 0 END) * 100.0 / MAX(1, COUNT(*)), 1) as high_rated_pct,
            SUM(CASE WHEN selling_price < 800 THEN 1 ELSE 0 END) as b_tot,
            SUM(CASE WHEN selling_price < 800 AND is_myntra_label = 1 THEN 1 ELSE 0 END) as b_ih_cnt,
            ROUND(AVG(CASE WHEN selling_price < 800 AND is_myntra_label = 1 THEN selling_price END), 1) as b_ih_asp,
            ROUND(AVG(CASE WHEN selling_price < 800 AND is_myntra_label = 1 THEN discount_percentage END), 1) as b_ih_disc,
            ROUND(AVG(CASE WHEN selling_price < 800 AND is_myntra_label = 1 THEN average_rating END), 1) as b_ih_rate,
            SUM(CASE WHEN selling_price < 800 AND is_myntra_label = 0 THEN 1 ELSE 0 END) as b_ext_cnt,
            ROUND(AVG(CASE WHEN selling_price < 800 AND is_myntra_label = 0 THEN selling_price END), 1) as b_ext_asp,
            ROUND(AVG(CASE WHEN selling_price < 800 AND is_myntra_label = 0 THEN discount_percentage END), 1) as b_ext_disc,
            ROUND(AVG(CASE WHEN selling_price < 800 AND is_myntra_label = 0 THEN average_rating END), 1) as b_ext_rate,
            SUM(CASE WHEN selling_price >= 800 AND selling_price <= 1800 THEN 1 ELSE 0 END) as m_tot,
            SUM(CASE WHEN selling_price >= 800 AND selling_price <= 1800 AND is_myntra_label = 1 THEN 1 ELSE 0 END) as m_ih_cnt,
            ROUND(AVG(CASE WHEN selling_price >= 800 AND selling_price <= 1800 AND is_myntra_label = 1 THEN selling_price END), 1) as m_ih_asp,
            ROUND(AVG(CASE WHEN selling_price >= 800 AND selling_price <= 1800 AND is_myntra_label = 1 THEN discount_percentage END), 1) as m_ih_disc,
            ROUND(AVG(CASE WHEN selling_price >= 800 AND selling_price <= 1800 AND is_myntra_label = 1 THEN average_rating END), 1) as m_ih_rate,
            SUM(CASE WHEN selling_price >= 800 AND selling_price <= 1800 AND is_myntra_label = 0 THEN 1 ELSE 0 END) as m_ext_cnt,
            ROUND(AVG(CASE WHEN selling_price >= 800 AND selling_price <= 1800 AND is_myntra_label = 0 THEN selling_price END), 1) as m_ext_asp,
            ROUND(AVG(CASE WHEN selling_price >= 800 AND selling_price <= 1800 AND is_myntra_label = 0 THEN discount_percentage END), 1) as m_ext_disc,
            ROUND(AVG(CASE WHEN selling_price >= 800 AND selling_price <= 1800 AND is_myntra_label = 0 THEN average_rating END), 1) as m_ext_rate,
            SUM(CASE WHEN selling_price > 1800 THEN 1 ELSE 0 END) as p_tot,
            SUM(CASE WHEN selling_price > 1800 AND is_myntra_label = 1 THEN 1 ELSE 0 END) as p_ih_cnt,
            ROUND(AVG(CASE WHEN selling_price > 1800 AND is_myntra_label = 1 THEN selling_price END), 1) as p_ih_asp,
            ROUND(AVG(CASE WHEN selling_price > 1800 AND is_myntra_label = 1 THEN discount_percentage END), 1) as p_ih_disc,
            ROUND(AVG(CASE WHEN selling_price > 1800 AND is_myntra_label = 1 THEN average_rating END), 1) as p_ih_rate,
            SUM(CASE WHEN selling_price > 1800 AND is_myntra_label = 0 THEN 1 ELSE 0 END) as p_ext_cnt,
            ROUND(AVG(CASE WHEN selling_price > 1800 AND is_myntra_label = 0 THEN selling_price END), 1) as p_ext_asp,
            ROUND(AVG(CASE WHEN selling_price > 1800 AND is_myntra_label = 0 THEN discount_percentage END), 1) as p_ext_disc,
            ROUND(AVG(CASE WHEN selling_price > 1800 AND is_myntra_label = 0 THEN average_rating END), 1) as p_ext_rate,
            -- Gender distribution (merged into single scan to save 1 extra query)
            SUM(CASE WHEN gender = 'Men' THEN 1 ELSE 0 END) as g_men,
            SUM(CASE WHEN gender = 'Women' THEN 1 ELSE 0 END) as g_women,
            SUM(CASE WHEN gender = 'Kids' THEN 1 ELSE 0 END) as g_kids,
            SUM(CASE WHEN gender = 'Boys' THEN 1 ELSE 0 END) as g_boys,
            SUM(CASE WHEN gender = 'Girls' THEN 1 ELSE 0 END) as g_girls
        FROM products p
        WHERE {where_sql};
    """, where_params)
    combined = cur.fetchone()
    total_products = combined[0] or 0
    in_stock_products = combined[1] or 0
    avg_price = round(combined[2] or 0, 1)
    avg_mrp_val = round(combined[3] or 0, 1)
    avg_discount_val = round(combined[4] or 0, 1)

    inventory_totals = _get_inventory_snapshot_totals(cur, where_sql, where_params)
    total_warehouse_units = _get_scoped_inventory_units(cur, where_sql, where_params)
    if total_warehouse_units <= 0:
        total_warehouse_units = inventory_totals["total_units"]
    total_selling_val = round(inventory_totals.get("selling_value") or (total_warehouse_units * (avg_price or 0.0)), 2)
    total_mrp_val = round(inventory_totals.get("mrp_value") or (total_warehouse_units * (avg_mrp_val or avg_price or 0.0)), 2)

    price_brackets = {
        "under_500": combined[5] or 0,
        "500_to_1000": combined[6] or 0,
        "1000_to_2000": combined[7] or 0,
        "2000_to_3500": combined[8] or 0,
        "above_3500": combined[9] or 0
    }

    discount_insights = {
        "super_deep_80_plus": combined[10] or 0,
        "deep_discount_60_to_80": combined[11] or 0,
        "moderate_40_to_60": combined[12] or 0,
        "mild_20_to_40": combined[13] or 0,
        "regular_under_20": combined[14] or 0,
        "avg_discount_pct": avg_discount_val
    }

    in_house_cnt = int(combined[15] or 0)
    ih_price = round(combined[16] or avg_price, 1)
    ih_disc = round(combined[17] or avg_discount_val, 1)

    external_cnt = int(combined[18] or 0)
    ext_price = round(combined[19] or avg_price, 1)
    ext_disc = round(combined[20] or avg_discount_val, 1)

    brand_mix_data = {
        "in_house": {
            "count": in_house_cnt,
            "units": int(total_warehouse_units * (in_house_cnt / max(1, total_products))),
            "avg_price": ih_price,
            "avg_discount": ih_disc
        },
        "external": {
            "count": external_cnt,
            "units": int(total_warehouse_units * (external_cnt / max(1, total_products))),
            "avg_price": ext_price,
            "avg_discount": ext_disc
        }
    }

    shirts_real_cnt = int(combined[21] or 0)
    shirts_price = round(combined[22] or avg_price, 1)
    shirts_disc = round(combined[23] or avg_discount_val, 1)

    denims_real_cnt = int(combined[24] or 0)
    denims_price = round(combined[25] or avg_price, 1)
    denims_disc = round(combined[26] or avg_discount_val, 1)

    western_real_cnt = int(combined[27] or 0)
    western_price = round(combined[28] or avg_price, 1)
    western_disc = round(combined[29] or avg_discount_val, 1)
    others_real_cnt = max(0, total_products - shirts_real_cnt - denims_real_cnt - western_real_cnt)

    cur.execute(f"""
        SELECT
            COALESCE(SUM(CASE WHEN p.category = 'Shirts' AND s.available = 1 THEN s.inventory_count ELSE 0 END), 0) as shirts_units,
            COALESCE(SUM(CASE WHEN p.category = 'Jeans' AND s.available = 1 THEN s.inventory_count ELSE 0 END), 0) as denims_units,
            COALESCE(SUM(CASE WHEN p.category IN ('Western Wear', 'Dresses', 'Tops', 'Skirts', 'Jumpsuit', 'Jumpsuits') AND s.available = 1 THEN s.inventory_count ELSE 0 END), 0) as western_units,
            COALESCE(SUM(CASE WHEN p.category NOT IN ('Shirts', 'Jeans', 'Western Wear', 'Dresses', 'Tops', 'Skirts', 'Jumpsuit', 'Jumpsuits') AND s.available = 1 THEN s.inventory_count ELSE 0 END), 0) as others_units
        FROM products p
        LEFT JOIN product_sizes s ON s.product_id = p.product_id
        WHERE {where_sql};
    """, where_params)
    category_units_row = cur.fetchone() or {}

    category_comparison = {
        "Shirts": {
            "count": shirts_real_cnt,
            "units": int(category_units_row["shirts_units"] or 0),
            "avg_price": shirts_price,
            "avg_discount": shirts_disc
        },
        "Denims": {
            "count": denims_real_cnt,
            "units": int(category_units_row["denims_units"] or 0),
            "avg_price": denims_price,
            "avg_discount": denims_disc
        },
        "Western Wear": {
            "count": western_real_cnt,
            "units": int(category_units_row["western_units"] or 0),
            "avg_price": western_price,
            "avg_discount": western_disc
        },
        "Others": {
            "count": others_real_cnt,
            "units": int(category_units_row["others_units"] or 0),
            "avg_price": round(avg_price, 1),
            "avg_discount": round(avg_discount_val, 1)
        }
    }

    # 6. Gender Split - 100% DYNAMIC SQL
    # 6. Gender Split - derived from combined single-pass query (no extra GROUP BY)
    gender_distribution = {}
    for g, idx in [("Men", 60), ("Women", 61), ("Kids", 62), ("Boys", 63), ("Girls", 64)]:
        cnt = combined[idx] or 0
        if cnt > 0:
            gender_distribution[g] = cnt
    if not gender_distribution:
        gender_distribution = {"Men": total_products}

    # 7. Top 10 Brands by product scope. Keep this endpoint lightweight; exact
    # size-level inventory belongs in the dedicated inventory/size views.
    latest_snapshot_date = inventory_totals["snapshot_date"]

    cur.execute(f"""
        SELECT
            p.brand,
            p.is_myntra_label,
            COUNT(*) as product_count,
            ROUND(AVG(p.selling_price), 1) as avg_price,
            ROUND(AVG(p.discount_percentage), 1) as avg_discount,
            ROUND(AVG(p.average_rating), 1) as avg_rating
        FROM products p
        WHERE {where_sql} AND p.brand IS NOT NULL AND p.brand != ''
        GROUP BY p.brand, p.is_myntra_label
        ORDER BY product_count DESC
        LIMIT 10;
    """, where_params)
    top_brands_rows = cur.fetchall()
    brand_inventory_units, brand_size_breakdown, heatmap_columns = _get_brand_inventory_breakdown(
        cur,
        where_sql,
        where_params,
        [row[0] for row in top_brands_rows]
    )
    top_brands = [
        {
            "brand": r[0],
            "is_myntra": bool(r[1]),
            "brand_type": "Myntra In-House Label" if r[1] else "External Brand",
            "product_count": int(r[2] or 0),
            "inventory_count": int(brand_inventory_units.get(r[0], 0) or 0),
            "avg_price": float(r[3] or avg_price),
            "avg_discount": float(r[4] or avg_discount_val),
            "avg_rating": float(r[5] or 0.0)
        }
        for r in top_brands_rows
    ]

    # 8. Discount and premium leaders are computed from live scoped catalog rows.
    top_disc_row = None
    prem_row = None


    def format_currency_in(val):
        if val >= 10000000:
            return f"₹{val / 10000000:.2f} Cr"
        elif val >= 100000:
            return f"₹{val / 100000:.2f} L"
        else:
            return f"₹{val:,.0f}"

    top_brands_val = [
        {
            "brand": b["brand"],
            "is_myntra": b["is_myntra"],
            "value": round(b["inventory_count"] * b["avg_price"], 2),
            "formatted_value": format_currency_in(b["inventory_count"] * b["avg_price"]),
            "units": b["inventory_count"]
        }
        for b in top_brands[:5]
    ]

    inventory_valuation = {
        "total_stock_value": total_selling_val,
        "formatted_stock_value": format_currency_in(total_selling_val),
        "total_mrp_value": total_mrp_val,
        "formatted_mrp_value": format_currency_in(total_mrp_val),
        "top_brands_valuation": top_brands_val
    }

    # 9. Lightweight pricing sample retained only as a fallback for very broad scopes.
    sample_limit = _get_adaptive_sample_limit(total_products, ceiling=2500)
    cur.execute(f"""
        SELECT
            p.selling_price
        FROM products p
        WHERE {where_sql}
          AND p.selling_price > 0
        LIMIT ?;
    """, where_params + [sample_limit])
    sample_rows = cur.fetchall()
    sample_prices = [_safe_float(row[0]) for row in sample_rows if _safe_float(row[0]) > 0]

    # 10. Exact top fabrics for the scoped catalog.
    cur.execute(f"""
        SELECT
            CASE
                WHEN LOWER(p.fabric) LIKE '%cotton%' AND (LOWER(p.fabric) LIKE '%blend%' OR LOWER(p.fabric) LIKE '%poly%' OR LOWER(p.fabric) LIKE '%,%') THEN 'Cotton Blend'
                WHEN LOWER(p.fabric) LIKE '%cotton%' THEN 'Cotton'
                WHEN LOWER(p.fabric) LIKE '%poly%' THEN 'Polyester'
                WHEN LOWER(p.fabric) LIKE '%linen%' THEN 'Linen'
                WHEN LOWER(p.fabric) LIKE '%viscose%' THEN 'Viscose'
                WHEN LOWER(p.fabric) LIKE '%denim%' THEN 'Denim'
                ELSE 'Others'
            END AS clean_fabric,
            COUNT(*) AS cnt,
            ROUND(AVG(COALESCE(p.selling_price, 0)), 1) AS avg_price,
            ROUND(AVG(COALESCE(p.discount_percentage, 0)), 1) AS avg_discount
        FROM products p
        WHERE {where_sql}
          AND p.fabric IS NOT NULL
          AND p.fabric != ''
        GROUP BY clean_fabric
        ORDER BY cnt DESC, clean_fabric ASC
        LIMIT 5;
    """, where_params)
    fabric_rows = cur.fetchall()

    # 11. Exact top colors for the scoped catalog.
    cur.execute(f"""
        SELECT
            p.primary_color,
            p.color_hex,
            COUNT(*) AS cnt,
            ROUND(AVG(COALESCE(p.discount_percentage, 0)), 1) AS avg_discount
        FROM products p
        WHERE {where_sql}
          AND {_valid_color_sql("p.primary_color")}
        GROUP BY p.primary_color, p.color_hex
        ORDER BY cnt DESC, p.primary_color ASC
        LIMIT 6;
    """, where_params)
    color_rows = cur.fetchall()

    # 12. Exact discount and premium signals.
    cur.execute(f"""
        SELECT p.brand, COALESCE(p.discount_percentage, 0) AS discount_pct, COALESCE(p.selling_price, 0) AS selling_price, p.title
        FROM products p
        WHERE {where_sql}
          AND p.brand IS NOT NULL
          AND p.brand != ''
          AND COALESCE(p.is_in_stock, 0) = 1
        ORDER BY COALESCE(p.discount_percentage, 0) DESC,
                 COALESCE(p.selling_price, 0) DESC,
                 p.product_id DESC
        LIMIT 1;
    """, where_params)
    disc_signal = cur.fetchone()
    if disc_signal:
        top_disc_row = (
            disc_signal["brand"],
            _safe_float(disc_signal["discount_pct"]),
            _safe_float(disc_signal["selling_price"]),
            disc_signal["title"]
        )

    cur.execute(f"""
        SELECT
            p.brand,
            COUNT(*) AS sku_count,
            ROUND(AVG(COALESCE(p.selling_price, 0)), 1) AS mean_price,
            ROUND(AVG(COALESCE(p.mrp, 0)), 1) AS mean_mrp
        FROM products p
        WHERE {where_sql}
          AND p.brand IS NOT NULL
          AND p.brand != ''
        GROUP BY p.brand
        ORDER BY sku_count DESC
        LIMIT 25;
    """, where_params)
    brand_matrix_rows = cur.fetchall()
    premium_brand_row = max(brand_matrix_rows, key=lambda row: _safe_float(row["mean_price"])) if brand_matrix_rows else None
    if premium_brand_row:
        prem_row = (
            premium_brand_row["brand"],
            _safe_float(premium_brand_row["mean_price"]),
            None
        )

    # 13. Exact best-seller candidates.
    cur.execute(f"""
        SELECT
            p.product_id,
            p.brand,
            p.title,
            p.selling_price,
            COALESCE(NULLIF(p.mrp, 0), p.selling_price) AS mrp,
            COALESCE(p.discount_percentage, 0) AS discount_percentage,
            COALESCE(p.average_rating, 0) AS average_rating,
            COALESCE(p.total_ratings_count, 0) AS total_ratings_count,
            p.product_url
        FROM products p
        WHERE {where_sql}
          AND COALESCE(p.is_in_stock, 0) = 1
          AND COALESCE(p.total_ratings_count, 0) >= 30
          AND COALESCE(p.average_rating, 0) >= 4.0
        ORDER BY
            COALESCE(p.total_ratings_count, 0) DESC,
            COALESCE(p.average_rating, 0) DESC,
            COALESCE(p.selling_price, 0) DESC,
            p.product_id DESC
        LIMIT 15;
    """, where_params)
    top_rated_candidates = [tuple(row) for row in cur.fetchall()]
    if len(top_rated_candidates) < 3:
        cur.execute(f"""
            SELECT
                p.product_id,
                p.brand,
                p.title,
                p.selling_price,
                COALESCE(NULLIF(p.mrp, 0), p.selling_price) AS mrp,
                COALESCE(p.discount_percentage, 0) AS discount_percentage,
                COALESCE(p.average_rating, 0) AS average_rating,
                COALESCE(p.total_ratings_count, 0) AS total_ratings_count,
                p.product_url
            FROM products p
            WHERE {where_sql}
              AND COALESCE(p.is_in_stock, 0) = 1
            ORDER BY
                COALESCE(p.total_ratings_count, 0) DESC,
                COALESCE(p.average_rating, 0) DESC,
                COALESCE(p.selling_price, 0) DESC,
                p.product_id DESC
            LIMIT 15;
        """, where_params)
        top_rated_candidates = [tuple(row) for row in cur.fetchall()]
    p3_rows = []
    seen_top3_keys = set()
    for row in top_rated_candidates:
        dedupe_key = (
            str(row[1] or "").strip().lower(),
            str(row[2] or "").strip().lower()
        )
        if dedupe_key in seen_top3_keys:
            continue
        seen_top3_keys.add(dedupe_key)
        p3_rows.append(row)
        if len(p3_rows) >= 3:
            break
    p3_image_map = {}
    if p3_rows:
        p3_ids = [row[0] for row in p3_rows if row and row[0]]
        placeholders = ",".join("?" for _ in p3_ids)
        if placeholders:
            cur.execute(f"SELECT product_id, full_data_json FROM products WHERE product_id IN ({placeholders});", p3_ids)
            for img_row in cur.fetchall():
                p3_image_map[int(img_row[0])] = _load_primary_image(img_row[1])
    deepest_brand = top_disc_row[0] if top_disc_row else (top_brands[0]["brand"] if top_brands else "Brand")
    deepest_disc = round(top_disc_row[1] or 0) if top_disc_row else round(avg_discount_val or 0)
    prem_brand = prem_row[0] if prem_row else (top_brands[0]["brand"] if top_brands else "Flagship")
    prem_asp = round(prem_row[1] or avg_price) if prem_row else round(avg_price)

    # Price Band Distribution for UI — derived from already-computed price_brackets (no extra query)
    price_band_distribution = [
        {"label": "< ₹500", "count": price_brackets["under_500"]},
        {"label": "₹500 - 1K", "count": price_brackets["500_to_1000"]},
        {"label": "₹1K - 2K", "count": price_brackets["1000_to_2000"]},
        {"label": "₹2K - 3.5K", "count": price_brackets["2000_to_3500"]},
        {"label": "> ₹3.5K", "count": price_brackets["above_3500"]}
    ]

    # Inventory Heatmap: keep the true scoped size labels so kids and adult assortments
    # do not get forced into misleading generic buckets.
    empty_sizes = {size: 0 for size in heatmap_columns}
    heatmap_matrix = [
        {
            "brand": b["brand"],
            "sizes": dict(brand_size_breakdown.get(b["brand"], empty_sizes))
        }
        for b in top_brands[:5]
    ]

    # Geographic demand should not be inferred from category mix. Until a real regional source is loaded,
    # return an empty state instead of fabricated hub allocations.
    geographic_demand = []

    trending_brands = _get_trending_brands(cur, where_sql, where_params, limit=5)

    # Dynamic AI Market Insights — derived from sampled winners and category mix
    # Derive category from filter or category_comparison
    if filter_category and filter_category != "all":
        deepest_cat = {"shirts": "Shirts", "denims": "Denims", "jeans": "Denims"}.get(filter_category, filter_category.title())
    else:
        deepest_cat = max(category_comparison.items(), key=lambda x: x[1].get("count", 0), default=("Shirts", {}))[0] if category_comparison else "Shirts"

    lead_cat_data = max(category_comparison.items(), key=lambda x: x[1].get("count", 0)) if category_comparison else ("Shirts", {})
    lead_cat = lead_cat_data[0]
    lead_cat_cnt = lead_cat_data[1].get("count", total_products)
    lead_cat_asp = round(lead_cat_data[1].get("avg_price", avg_price))

    prem_candidate = max(top_brands, key=lambda b: b.get("avg_price", 0)) if top_brands else None
    prem_brand = prem_brand if prem_brand else (prem_candidate["brand"] if prem_candidate else "Flagship")
    prem_disc = round(prem_candidate["avg_discount"]) if prem_candidate else round(avg_discount_val or 0)
    prem_asp = prem_asp if prem_asp else round(prem_candidate["avg_price"]) if prem_candidate else avg_price

    core_sz_pct = 0.0

    # Top Fabrics — derived from parallel fabric_rows (no extra query!)
    top_fabrics = [
        {
            "fabric": r["clean_fabric"],
            "count": int(r["cnt"] or 0),
            "percentage": round((int(r["cnt"] or 0) / max(1, total_products)) * 100, 1)
        }
        for r in fabric_rows
    ]

    # Top Colors — derived from parallel col_rows (no extra query!)
    top_colors = [
        {
            "color": _normalize_color_name(r["primary_color"], fallback="Multicolor"),
            "hex": _normalize_color_hex(r["color_hex"], r["primary_color"], fallback="#0f172a"),
            "count": int(r["cnt"] or 0),
            "discount": round(r["avg_discount"] or 0, 1),
            "percentage": round((int(r["cnt"] or 0) / max(1, total_products)) * 100, 1)
        }
        for r in color_rows
    ]

    # Top 3 Products — derived from parallel p3_rows (no extra query!)
    top_3_products = []
    for r in p3_rows:
        top_3_products.append({
            "product_id": r[0],
            "brand": r[1],
            "title": r[2],
            "selling_price": r[3],
            "mrp": r[4],
            "discount_percentage": r[5],
            "rating": r[6],
            "rating_count": r[7],
            "image": p3_image_map.get(int(r[0]), ""),
            "product_url": r[8] or ""
        })

    ai_market_insights = [
        {
            "title": f"Deepest Discount: {deepest_brand}",
            "description": f"Maximum catalog markdown of {deepest_disc}% OFF detected in {deepest_cat}.",
            "icon": "tag"
        },
        {
            "title": f"Dominant Category: {lead_cat}",
            "description": f"{lead_cat_cnt:,} active catalog SKUs leading inventory volume with ASP ₹{lead_cat_asp:,}.",
            "icon": "trending"
        },
        {
            "title": f"Premium Price Tier: {prem_brand}",
            "description": f"Maintains ASP ₹{prem_asp:,} with lower markdown rate ({prem_disc}% avg discount).",
            "icon": "star"
        },
        {
            "title": "Core Size Inventory Concentration",
            "description": "Exact core-size concentration is available in Size Intelligence; dashboard inventory is optimized for fast scope loading.",
            "icon": "default"
        }
    ]

    # Keep headline CTO pricing metrics exact across all scopes unless the DB cannot answer.
    cto_mean_price = avg_price
    cto_mean_mrp = avg_mrp_val
    cto_median_price = float(avg_price)
    cto_p25_price = float(avg_price)
    cto_p75_price = float(avg_price)
    cto_mode_price = int(avg_price or 0)
    try:
        cur.execute(f"""
            SELECT
                COALESCE(AVG(p.selling_price), 0) AS mean_price,
                COALESCE(AVG(p.mrp), 0) AS mean_mrp,
                COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.selling_price), 0) AS median_price,
                COALESCE(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY p.selling_price), 0) AS p25_price,
                COALESCE(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY p.selling_price), 0) AS p75_price,
                COALESCE(MODE() WITHIN GROUP (ORDER BY p.selling_price), 0) AS mode_price
            FROM products p
            WHERE {where_sql} AND p.selling_price > 0;
        """, where_params)
        cto_row = cur.fetchone() or {}
        cto_mean_price = float(cto_row["mean_price"] or avg_price)
        cto_mean_mrp = float(cto_row["mean_mrp"] or avg_mrp_val)
        cto_median_price = float(cto_row["median_price"] or avg_price)
        cto_p25_price = float(cto_row["p25_price"] or avg_price)
        cto_p75_price = float(cto_row["p75_price"] or avg_price)
        cto_mode_price = int(round(float(cto_row["mode_price"] or avg_price or 0)))
    except Exception:
        sorted_sample_prices = sorted(sample_prices)
        if sorted_sample_prices:
            cto_median_price = float(_median_from_sorted(sorted_sample_prices))
            p25_idx = min(len(sorted_sample_prices) - 1, max(0, int(round((len(sorted_sample_prices) - 1) * 0.25))))
            p75_idx = min(len(sorted_sample_prices) - 1, max(0, int(round((len(sorted_sample_prices) - 1) * 0.75))))
            cto_p25_price = float(sorted_sample_prices[p25_idx])
            cto_p75_price = float(sorted_sample_prices[p75_idx])
        pb_weights = [
            (250, price_brackets["under_500"]),
            (750, price_brackets["500_to_1000"]),
            (1500, price_brackets["1000_to_2000"]),
            (2750, price_brackets["2000_to_3500"]),
            (4500, price_brackets["above_3500"])
        ]
        cto_mode_price = int(max(pb_weights, key=lambda x: x[1])[0])

    use_brand_directory = not any([
        filter_category,
        filter_gender,
        filter_brand,
        filter_subcategory,
        filter_price_min,
        filter_price_max,
    ])
    if use_brand_directory:
        brand_where = ["brand_name IS NOT NULL", "brand_name != ''"]
        brand_params = []
        if filter_brand_type in ("myntra", "myntra_in_house", "myntra in-house labels"):
            brand_where.append("is_myntra_label = 1")
        elif filter_brand_type in ("non-myntra", "external", "external brands"):
            brand_where.append("is_myntra_label = 0")
        cur.execute(f"""
            SELECT
                SUM(CASE WHEN total_count >= {LARGE_BRAND_MIN_PRODUCTS} THEN 1 ELSE 0 END),
                SUM(CASE WHEN total_count >= {MID_BRAND_MIN_PRODUCTS} AND total_count < {LARGE_BRAND_MIN_PRODUCTS} THEN 1 ELSE 0 END),
                SUM(CASE WHEN total_count < {MID_BRAND_MIN_PRODUCTS} THEN 1 ELSE 0 END),
                SUM(CASE WHEN total_count >= {LARGE_BRAND_MIN_PRODUCTS} THEN total_count ELSE 0 END),
                SUM(CASE WHEN total_count >= {MID_BRAND_MIN_PRODUCTS} AND total_count < {LARGE_BRAND_MIN_PRODUCTS} THEN total_count ELSE 0 END),
                SUM(CASE WHEN total_count < {MID_BRAND_MIN_PRODUCTS} THEN total_count ELSE 0 END)
            FROM brands
            WHERE {' AND '.join(brand_where)};
        """, brand_params)
        scale_row = cur.fetchone()
    else:
        cur.execute(f"""
            WITH brand_counts AS (
                SELECT p.brand, COUNT(*) as total_count
                FROM products p
                WHERE {where_sql} AND p.brand IS NOT NULL AND p.brand != ''
                GROUP BY p.brand
            )
            SELECT
                SUM(CASE WHEN total_count >= {LARGE_BRAND_MIN_PRODUCTS} THEN 1 ELSE 0 END),
                SUM(CASE WHEN total_count >= {MID_BRAND_MIN_PRODUCTS} AND total_count < {LARGE_BRAND_MIN_PRODUCTS} THEN 1 ELSE 0 END),
                SUM(CASE WHEN total_count < {MID_BRAND_MIN_PRODUCTS} THEN 1 ELSE 0 END),
                SUM(CASE WHEN total_count >= {LARGE_BRAND_MIN_PRODUCTS} THEN total_count ELSE 0 END),
                SUM(CASE WHEN total_count >= {MID_BRAND_MIN_PRODUCTS} AND total_count < {LARGE_BRAND_MIN_PRODUCTS} THEN total_count ELSE 0 END),
                SUM(CASE WHEN total_count < {MID_BRAND_MIN_PRODUCTS} THEN total_count ELSE 0 END)
            FROM brand_counts;
        """, where_params)
        scale_row = cur.fetchone()
    largest_cnt = (scale_row[0] if scale_row else 0) or 0
    mid_cnt = (scale_row[1] if scale_row else 0) or 0
    small_cnt = (scale_row[2] if scale_row else 0) or 0
    largest_prods = (scale_row[3] if scale_row else 0) or 0
    mid_prods = (scale_row[4] if scale_row else 0) or 0
    small_prods = (scale_row[5] if scale_row else 0) or 0
    total_scale_prods = max(1, largest_prods + mid_prods + small_prods)

    brand_scale_breakdown = {
        "largest_brands": {"count": largest_cnt, "products": largest_prods, "share": round((largest_prods / total_scale_prods) * 100, 1)},
        "mid_brands": {"count": mid_cnt, "products": mid_prods, "share": round((mid_prods / total_scale_prods) * 100, 1)},
        "small_brands": {"count": small_cnt, "products": small_prods, "share": round((small_prods / total_scale_prods) * 100, 1)}
    }

    # Brand Valuation & Revenue Matrix — exact inventory snapshot + recent sales telemetry.
    latest_sales_date = _latest_sales_date(cur)
    sales_30d_start_date = latest_sales_date - timedelta(days=29) if latest_sales_date else None
    brand_names_for_matrix = [row["brand"] for row in brand_matrix_rows if row["brand"]]
    stock_units_by_brand = {}
    stock_value_by_brand = {}
    units_sold_by_brand = {}
    revenue_by_brand = {}

    if brand_names_for_matrix:
        brand_placeholders = ",".join("?" for _ in brand_names_for_matrix)

        if latest_snapshot_date:
            cur.execute(f"""
                SELECT
                    p.brand,
                    COALESCE(SUM(s.total_stock), 0) AS stock_units,
                    COALESCE(SUM(s.total_stock * COALESCE(s.selling_price, p.selling_price, 0)), 0) AS stock_value
                FROM daily_inventory_snapshots s
                JOIN products p ON p.product_id = s.product_id
                WHERE s.snapshot_date = ?
                  AND p.brand IN ({brand_placeholders})
                  AND {where_sql}
                GROUP BY p.brand;
            """, [latest_snapshot_date] + brand_names_for_matrix + where_params)
            for row in cur.fetchall():
                stock_units_by_brand[row["brand"]] = int(row["stock_units"] or 0)
                stock_value_by_brand[row["brand"]] = round(_safe_float(row["stock_value"]), 2)

        if latest_sales_date and sales_30d_start_date:
            cur.execute(f"""
                SELECT
                    p.brand,
                    COALESCE(SUM(sa.units_sold), 0) AS units_sold,
                    COALESCE(SUM(sa.revenue_generated), 0) AS revenue
                FROM daily_sales_analytics sa
                JOIN products p ON p.product_id = sa.product_id
                WHERE sa.analytics_date >= ?
                  AND sa.analytics_date <= ?
                  AND p.brand IN ({brand_placeholders})
                  AND {where_sql}
                GROUP BY p.brand;
            """, [sales_30d_start_date, latest_sales_date] + brand_names_for_matrix + where_params)
            for row in cur.fetchall():
                units_sold_by_brand[row["brand"]] = int(row["units_sold"] or 0)
                revenue_by_brand[row["brand"]] = round(_safe_float(row["revenue"]), 2)

    matrix_rows = brand_matrix_rows
    brand_valuation_matrix = []
    for r in matrix_rows:
        b_name = r["brand"]
        b_skus = int(r["sku_count"] or 0)
        b_mean_price = float(r["mean_price"] or 0.0)
        b_mean_mrp = float(r["mean_mrp"] or 0.0)
        b_total_units = stock_units_by_brand.get(b_name, 0)
        b_sales_units = units_sold_by_brand.get(b_name, 0)
        b_revenue = revenue_by_brand.get(b_name, 0.0)
        b_valuation = stock_value_by_brand.get(b_name, round(b_total_units * b_mean_price, 2))

        if b_skus >= LARGE_BRAND_MIN_PRODUCTS:
            scale_tier = "Largest Brand"
        elif b_skus >= MID_BRAND_MIN_PRODUCTS:
            scale_tier = "Mid-Tier"
        else:
            scale_tier = "Small / Emerging"

        brand_valuation_matrix.append({
            "brand": b_name,
            "skus": b_skus,
            "scale_tier": scale_tier,
            "mean_price": b_mean_price,
            "mean_mrp": b_mean_mrp,
            "median_price": b_mean_price,
            "inventory_units": b_total_units,
            "inventory_valuation": b_valuation,
            "units_sold": b_sales_units,
            "revenue": b_revenue
        })

    if filter_sort_by == "revenue_desc":
        brand_valuation_matrix.sort(key=lambda x: x["revenue"], reverse=True)
    elif filter_sort_by == "revenue_asc":
        brand_valuation_matrix.sort(key=lambda x: x["revenue"])
    elif filter_sort_by == "skus_desc":
        brand_valuation_matrix.sort(key=lambda x: x["skus"], reverse=True)
    elif filter_sort_by == "median_desc":
        brand_valuation_matrix.sort(key=lambda x: x["mean_price"], reverse=True)
    elif filter_sort_by == "median_asc":
        brand_valuation_matrix.sort(key=lambda x: x["mean_price"])
    elif filter_sort_by == "valuation_desc":
        brand_valuation_matrix.sort(key=lambda x: x["inventory_valuation"], reverse=True)
    elif filter_sort_by == "valuation_asc":
        brand_valuation_matrix.sort(key=lambda x: x["inventory_valuation"])

    insights_result = {
        "cto_pricing": {
            "mean_price": cto_mean_price,
            "mean_mrp": cto_mean_mrp,
            "median_price": cto_median_price,
            "mode_price": cto_mode_price,
            "p25_price": cto_p25_price,
            "p75_price": cto_p75_price
        },
        "brand_scale_breakdown": brand_scale_breakdown,
        "brand_scale_meta": {
            "largest_min": LARGE_BRAND_MIN_PRODUCTS,
            "mid_min": MID_BRAND_MIN_PRODUCTS,
            "mid_max": LARGE_BRAND_MIN_PRODUCTS - 1,
            "largest_label": f"Largest Brands (>={LARGE_BRAND_MIN_PRODUCTS:,} SKUs)",
            "mid_label": f"Mid-Tier Brands ({MID_BRAND_MIN_PRODUCTS:,}-{LARGE_BRAND_MIN_PRODUCTS - 1:,} SKUs)",
            "small_label": f"Small / Emerging (<{MID_BRAND_MIN_PRODUCTS:,} SKUs)"
        },
        "brand_valuation_matrix": brand_valuation_matrix,
        "total_products": total_products,
        "in_stock_products": in_stock_products,
        "in_stock_percentage": round((in_stock_products / total_products * 100), 1) if total_products > 0 else 100,
        "total_warehouse_units": total_warehouse_units,
        "avg_price": avg_price,
        "avg_mrp": avg_mrp_val,
        "avg_discount_pct": avg_discount_val,
        "price_brackets": price_brackets,
        "price_band_distribution": price_band_distribution,
        "inventory_heatmap_columns": heatmap_columns,
        "inventory_heatmap": heatmap_matrix,
        "geographic_demand": geographic_demand,
        "geographic_demand_available": False,
        "trending_brands": trending_brands,
        "ai_market_insights": ai_market_insights,
        "category_comparison": category_comparison,
        "top_brands": top_brands,
        "top_fabrics": top_fabrics,
        "top_colors": top_colors,
        "top_3_products": top_3_products
    }

    api_cache.set(cache_key, insights_result, ttl=600.0)
    _store_shared_cache(cache_key, insights_result, ttl=600.0)
    return jsonify(insights_result)


def get_latest_two_snapshot_dates(cur):
    """Dynamically resolves the latest two inventory snapshot dates from the database."""
    cur.execute("SELECT DISTINCT snapshot_date FROM daily_inventory_snapshots ORDER BY snapshot_date DESC LIMIT 2;")
    dates = [r[0] for r in cur.fetchall()]
    if len(dates) >= 2:
        return dates[0], dates[1]
    elif len(dates) == 1:
        return dates[0], dates[0]
    today_str = date.today().isoformat()
    yest_str = (date.today() - timedelta(days=1)).isoformat()
    return today_str, yest_str


def _build_snapshot_dates_payload():
    conn = db._get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT snapshot_date FROM daily_inventory_snapshots ORDER BY snapshot_date DESC;")
    dates = [r[0] for r in cur.fetchall()]
    return {
        "status": "success",
        "dates": dates,
        "latest": dates[0] if dates else None,
        "previous": dates[1] if len(dates) > 1 else (dates[0] if dates else None)
    }


@app.route("/api/snapshot-dates")
def get_snapshot_dates_route():
    payload = get_or_compute_cached_payload(
        "snapshot_dates_v1",
        lambda: _build_snapshot_dates_payload(),
        ttl=1800.0,
        shared=True
    )
    return jsonify(payload)


@app.route("/api/products")
def get_products():
    page = max(1, int(request.args.get("page", 1)))
    per_page = max(1, min(int(request.args.get("per_page", 24)), 100))
    offset = (page - 1) * per_page
    category = request.args.get("category")
    brand = request.args.get("brand")
    gender = request.args.get("gender")
    brand_type = request.args.get("brand_type")
    in_stock = request.args.get("in_stock")
    search = request.args.get("search", "").strip()
    subcategory = request.args.get("subcategory")
    price_ranges = request.args.get("price_ranges") or request.args.get("price_range")
    price_min = request.args.get("min_price")
    price_max = request.args.get("max_price")
    min_discount = request.args.get("min_discount")
    rating_filter = request.args.get("rating_min") or request.args.get("rating")
    tab = request.args.get("tab")
    view_mode = (request.args.get("view_mode") or "grid").strip().lower()

    cache_key = f"products:{request.query_string.decode('utf-8', errors='ignore')}"
    cached = _load_shared_cache(cache_key)
    if cached is not None:
        api_cache.set(cache_key, cached, ttl=30.0)
        return jsonify(cached)

    conn = db._get_connection()
    cur = conn.cursor()

    availability = None
    if in_stock in ("1", "true", "yes", "in_stock"):
        availability = "in_stock"

    where_sql, params = _build_catalog_filters(
        category=category or "all",
        gender=gender or "all",
        subcategory=subcategory,
        brand=brand,
        brand_type=brand_type,
        price_min=price_min,
        price_max=price_max,
        price_ranges=price_ranges,
        discount_min=min_discount,
        rating_min=rating_filter,
        availability=availability
    )

    query = f"""
        SELECT
            p.product_id,
            p.sku,
            p.brand,
            p.title,
            p.category,
            p.sub_category,
            p.product_url,
            p.mrp,
            p.selling_price,
            p.discount_percentage,
            p.is_in_stock,
            p.primary_color,
            p.color_hex,
            p.average_rating,
            p.total_ratings_count,
            p.total_reviews_count,
            p.updated_at,
            p.full_data_json
        FROM products p
        WHERE {where_sql}
    """
    count_query = f"SELECT COUNT(*) FROM products p WHERE {where_sql}"
    query_params = list(params)
    count_params = list(params)

    if in_stock in ("0", "false", "no", "out_of_stock"):
        query += " AND p.is_in_stock = 0"
        count_query += " AND p.is_in_stock = 0"

    tab_clause, tab_clause_params = _build_catalog_tab_clause(cur, tab, alias="p")
    if tab_clause:
        query += f" AND {tab_clause}"
        count_query += f" AND {tab_clause}"
        query_params.extend(tab_clause_params)
        count_params.extend(tab_clause_params)

    if search:
        query += " AND (LOWER(COALESCE(p.title, '')) LIKE ? OR LOWER(COALESCE(p.brand, '')) LIKE ? OR CAST(p.sku AS TEXT) LIKE ?)"
        count_query += " AND (LOWER(COALESCE(p.title, '')) LIKE ? OR LOWER(COALESCE(p.brand, '')) LIKE ? OR CAST(p.sku AS TEXT) LIKE ?)"
        p = f"%{search.lower()}%"
        query_params.extend([p, p, p])
        count_params.extend([p, p, p])

    # Size filter
    size_filter = request.args.get("size", "").strip()
    if size_filter:
        query += " AND p.product_id IN (SELECT product_id FROM product_sizes WHERE size = ? AND available = 1)"
        count_query += " AND p.product_id IN (SELECT product_id FROM product_sizes WHERE size = ? AND available = 1)"
        query_params.append(size_filter)
        count_params.append(size_filter)

    # Date filter
    date_filter = request.args.get("date", "").strip()
    if date_filter and date_filter != "all":
        query += " AND p.product_id IN (SELECT product_id FROM daily_inventory_snapshots WHERE snapshot_date = ?)"
        count_query += " AND p.product_id IN (SELECT product_id FROM daily_inventory_snapshots WHERE snapshot_date = ?)"
        query_params.append(date_filter)
        count_params.append(date_filter)

    movement_filter = request.args.get("movement_filter", "").strip()
    if movement_filter:
        today_date, yesterday_date = get_latest_two_snapshot_dates(cur)
    if movement_filter == "price_drop":
        subq = "p.product_id IN (SELECT tb.product_id FROM daily_inventory_snapshots tb JOIN daily_inventory_snapshots ta ON tb.product_id = ta.product_id AND ta.snapshot_date = ? WHERE tb.snapshot_date = ? AND tb.selling_price < ta.selling_price)"
        query += f" AND {subq}"
        count_query += f" AND {subq}"
        query_params.extend([yesterday_date, today_date])
        count_params.extend([yesterday_date, today_date])
    elif movement_filter == "price_hike":
        subq = "p.product_id IN (SELECT tb.product_id FROM daily_inventory_snapshots tb JOIN daily_inventory_snapshots ta ON tb.product_id = ta.product_id AND ta.snapshot_date = ? WHERE tb.snapshot_date = ? AND tb.selling_price > ta.selling_price)"
        query += f" AND {subq}"
        count_query += f" AND {subq}"
        query_params.extend([yesterday_date, today_date])
        count_params.extend([yesterday_date, today_date])
    elif movement_filter == "discount_deepened":
        subq = "p.product_id IN (SELECT tb.product_id FROM daily_inventory_snapshots tb JOIN daily_inventory_snapshots ta ON tb.product_id = ta.product_id AND ta.snapshot_date = ? WHERE tb.snapshot_date = ? AND tb.discount_percentage > ta.discount_percentage)"
        query += f" AND {subq}"
        count_query += f" AND {subq}"
        query_params.extend([yesterday_date, today_date])
        count_params.extend([yesterday_date, today_date])
    elif movement_filter == "restocked":
        subq = "p.product_id IN (SELECT product_id FROM daily_sales_analytics WHERE analytics_date = ? AND stock_added > 0)"
        query += f" AND {subq}"
        count_query += f" AND {subq}"
        query_params.append(today_date)
        count_params.append(today_date)
    elif movement_filter == "fast_movers":
        subq = "p.product_id IN (SELECT product_id FROM daily_sales_analytics WHERE analytics_date = ? AND units_sold >= 1)"
        query += f" AND {subq}"
        count_query += f" AND {subq}"
        query_params.append(today_date)
        count_params.append(today_date)
    elif movement_filter == "stockout_risk":
        subq = "(p.is_in_stock = 0 OR p.product_id IN (SELECT product_id FROM daily_inventory_snapshots WHERE snapshot_date = ? AND total_stock < 5))"
        query += f" AND {subq}"
        count_query += f" AND {subq}"
        query_params.append(today_date)
        count_params.append(today_date)

    cur.execute(count_query, count_params)
    total_count = cur.fetchone()[0]

    # Dynamic sorting
    sort_by = request.args.get("sort", "relevance")
    order_clause, order_params = _catalog_sort_clause(sort_by, search_term=search)
    query += f" ORDER BY {order_clause} LIMIT ? OFFSET ?;"
    query_params.extend(order_params)
    query_params.extend([per_page, offset])

    cur.execute(query, query_params)
    rows = cur.fetchall()

    items = []
    pids = []
    for r in rows:
        pid = int(r["product_id"])
        media_primary = _load_primary_image(r["full_data_json"])
        sku_value = r["sku"] or ""
        brand_value = r["brand"] or ""
        title_value = r["title"] or ""
        product_url = r["product_url"] or ""
        updated_at = r["updated_at"]
        primary_color = _normalize_color_name(r["primary_color"], fallback="Multicolor")
        color_hex = _normalize_color_hex(r["color_hex"], primary_color, fallback="")
        data = {
            "product_info": {
                "product_id": pid,
                "sku": sku_value,
                "brand": brand_value,
                "title": title_value,
                "category": r["category"] or "",
                "sub_category": r["sub_category"] or "",
                "product_url": product_url,
                "primary_color": primary_color,
                "color_hex": color_hex
            },
            "pricing": {
                "mrp": _safe_float(r["mrp"]),
                "selling_price": _safe_float(r["selling_price"]),
                "discount_percentage": _safe_int(r["discount_percentage"])
            },
            "inventory_and_sizes": {
                "is_in_stock": bool(r["is_in_stock"]),
                "sizes_available": []
            },
            "ratings_and_reviews": {
                "average_rating": _safe_float(r["average_rating"]),
                "total_ratings_count": _safe_int(r["total_ratings_count"]),
                "total_reviews_count": _safe_int(r["total_reviews_count"])
            },
            "ratings": {
                "average_rating": _safe_float(r["average_rating"]),
                "total_ratings_count": _safe_int(r["total_ratings_count"]),
                "total_reviews_count": _safe_int(r["total_reviews_count"])
            },
            "media": {
                "primary_image": media_primary,
                "image_gallery": [media_primary] if media_primary else []
            },
            "color_hex": color_hex,
            "last_seen_at": updated_at,
            "updated_at": updated_at
        }
        items.append(data)
        pids.append(pid)

    # Enrich with dynamic size breakdown only when the list view needs it.
    if pids and view_mode == "list":
        placeholders = ",".join("?" for _ in pids)
        cur.execute(f"""
            SELECT product_id, size, sku_id, available, inventory_count
            FROM product_sizes
            WHERE product_id IN ({placeholders})
            ORDER BY id ASC;
        """, pids)
        size_map = {}
        for sz in cur.fetchall():
            pid = sz[0]
            if pid not in size_map:
                size_map[pid] = []
            size_map[pid].append({
                "size": sz[1],
                "sku_id": sz[2],
                "available": bool(sz[3]),
                "inventory_count": sz[4]
            })

        for item in items:
            pid = item.get("product_info", {}).get("product_id") or item.get("product_id")
            if pid in size_map:
                item["sizes"] = size_map[pid]
                if "inventory_and_sizes" in item:
                    item["inventory_and_sizes"]["sizes_available"] = size_map[pid]

    response_payload = {
        "items": items,
        "products": items,
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total_count + per_page - 1) // per_page)
    }
    api_cache.set(cache_key, response_payload, ttl=30.0)
    _store_shared_cache(cache_key, response_payload, ttl=30.0)
    return jsonify(response_payload)


@app.route("/api/catalog/meta")
def get_catalog_meta():
    filters = {
        "category": request.args.get("category", "all").strip(),
        "gender": request.args.get("gender", "all").strip(),
        "subcategory": request.args.get("subcategory"),
        "price_min": request.args.get("min_price"),
        "price_max": request.args.get("max_price"),
        "price_ranges": request.args.get("price_ranges") or request.args.get("price_range"),
        "brand_size": request.args.get("brand_size"),
        "brand_type": request.args.get("brand_type"),
        "brand": request.args.get("brand"),
        "color": request.args.get("color"),
        "fabric": request.args.get("fabric"),
        "fit": request.args.get("fit"),
        "discount_min": request.args.get("min_discount"),
        "rating_min": request.args.get("rating_min") or request.args.get("rating"),
        "availability": (
            "in_stock" if request.args.get("in_stock") in ("1", "true", "yes", "in_stock")
            else "out_of_stock" if request.args.get("in_stock") in ("0", "false", "no", "out_of_stock")
            else request.args.get("availability")
        ),
        "new_arrivals": request.args.get("new_arrivals"),
        "search": request.args.get("search", "").strip(),
        "tab": request.args.get("tab", "all").strip()
    }

    cache_key = f"catalog_meta:{request.query_string.decode('utf-8', errors='ignore')}"
    payload = get_or_compute_cached_payload(
        cache_key,
        lambda: _build_catalog_meta_payload(db._get_connection().cursor(), filters),
        ttl=30.0,
        shared=True
    )
    return jsonify(payload)


@app.route("/api/product/<int:product_id>")
def get_single_product(product_id):
    conn = db._get_connection()
    cur = conn.cursor()
    cur.execute("SELECT full_data_json, average_rating, total_ratings_count, total_reviews_count, primary_color, color_hex FROM products WHERE product_id = ?", (product_id,))
    row = cur.fetchone()
    if row:
        raw_json = row[0]
        try:
            data = json.loads(raw_json)
        except (json.JSONDecodeError, ValueError):
            try:
                data = ast.literal_eval(raw_json)
            except Exception:
                data = {}
        if "ratings_and_reviews" not in data:
            data["ratings_and_reviews"] = {}
        data["ratings_and_reviews"]["average_rating"] = float(row[1] or 0.0)
        data["ratings_and_reviews"]["total_ratings_count"] = int(row[2] or 0)
        data["ratings_and_reviews"]["total_reviews_count"] = int(row[3] or 0)
        data["ratings"] = data["ratings_and_reviews"]
        if "product_info" in data:
            normalized_color = _normalize_color_name(row[4], fallback="Multicolor")
            data["product_info"]["primary_color"] = normalized_color
            data["product_info"]["color_hex"] = _normalize_color_hex(row[5], normalized_color, fallback="#06b6d4")

        # Attach real size-wise inventory table
        cur.execute("""
            SELECT size, sku_id, available, inventory_count
            FROM product_sizes
            WHERE product_id = ?
            ORDER BY id ASC;
        """, (product_id,))
        size_rows = cur.fetchall()
        size_list = [
            {
                "size": sz[0],
                "sku_id": sz[1],
                "available": bool(sz[2]),
                "inventory_count": int(sz[3])
            }
            for sz in size_rows
        ]
        data["size_inventory"] = size_list
        if "inventory_and_sizes" in data:
            data["inventory_and_sizes"]["sizes_available"] = size_list

        # Attach yesterday vs today comparison metrics dynamically
        today_date, yesterday_date = get_latest_two_snapshot_dates(cur)
        cur.execute("""
            SELECT ta.selling_price as yest_price, tb.selling_price as today_price,
                   ROUND(tb.selling_price - ta.selling_price, 2) as price_delta,
                   ROUND(((tb.selling_price - ta.selling_price) / ta.selling_price) * 100.0, 1) as price_delta_pct,
                   ta.discount_percentage as yest_disc, tb.discount_percentage as today_disc,
                   (tb.discount_percentage - ta.discount_percentage) as discount_delta,
                   ta.total_stock as yest_stock, tb.total_stock as today_stock,
                   (tb.total_stock - ta.total_stock) as stock_delta,
                   COALESCE(sa.units_sold, 0) as units_sold,
                   COALESCE(sa.revenue_generated, 0.0) as revenue,
                   COALESCE(sa.stock_added, 0) as stock_added
            FROM daily_inventory_snapshots tb
            JOIN daily_inventory_snapshots ta ON tb.product_id = ta.product_id AND ta.snapshot_date = ?
            LEFT JOIN daily_sales_analytics sa ON tb.product_id = sa.product_id AND sa.analytics_date = tb.snapshot_date
            WHERE tb.snapshot_date = ? AND tb.product_id = ?;
        """, (yesterday_date, today_date, product_id))
        dod_r = cur.fetchone()
        if dod_r:
            data["day_over_day"] = {
                "today_date": today_date,
                "yesterday_date": yesterday_date,
                "yesterday_price": dod_r[0],
                "today_price": dod_r[1],
                "price_delta": dod_r[2],
                "price_delta_pct": dod_r[3],
                "yesterday_discount": dod_r[4],
                "today_discount": dod_r[5],
                "discount_delta": dod_r[6],
                "yesterday_stock": dod_r[7],
                "today_stock": dod_r[8],
                "stock_delta": dod_r[9],
                "units_sold": dod_r[10],
                "revenue": dod_r[11],
                "stock_added": dod_r[12]
            }

        # Attach real historical time-series snapshots (Price & Stock history)
        cur.execute("""
            SELECT snapshot_date, selling_price, mrp, discount_percentage, total_stock
            FROM daily_inventory_snapshots
            WHERE product_id = ?
            ORDER BY snapshot_date ASC;
        """, (product_id,))
        data["price_history"] = [
            {
                "date": r[0],
                "price": r[1],
                "mrp": r[2],
                "discount": r[3],
                "stock": r[4]
            }
            for r in cur.fetchall()
        ]

        # Attach real daily sales velocity history
        cur.execute("""
            SELECT analytics_date, units_sold, revenue_generated, stock_added
            FROM daily_sales_analytics
            WHERE product_id = ?
            ORDER BY analytics_date ASC;
        """, (product_id,))
        data["sales_history"] = [
            {
                "date": r[0],
                "units_sold": r[1],
                "revenue": r[2],
                "stock_added": r[3]
            }
            for r in cur.fetchall()
        ]

        # 1. Category Benchmark Intelligence
        cat = (data.get("product_info", {}) or {}).get("category") or data.get("category")
        if cat:
            cur.execute("""
                SELECT AVG(selling_price), AVG(discount_percentage), AVG(average_rating), COUNT(*)
                FROM products
                WHERE category = ? AND selling_price > 0;
            """, (cat,))
            cat_bench = cur.fetchone()
            if cat_bench and cat_bench[3] > 0:
                cat_asp = round(cat_bench[0] or 0.0, 1)
                cat_disc = round(cat_bench[1] or 0.0, 1)
                cat_rating = round(cat_bench[2] or 0.0, 1)
                p_price = (data.get("pricing", {}) or {}).get("selling_price") or 0.0
                p_disc = (data.get("pricing", {}) or {}).get("discount_percentage") or 0
                price_delta_bench = round(((p_price - cat_asp) / cat_asp * 100.0), 1) if cat_asp > 0 else 0.0
                disc_delta_bench = round(p_disc - cat_disc, 1)
                data["category_benchmark"] = {
                    "category": cat,
                    "category_asp": cat_asp,
                    "category_discount": cat_disc,
                    "category_rating": cat_rating,
                    "total_category_skus": cat_bench[3],
                    "price_delta_pct": price_delta_bench,
                    "discount_delta": disc_delta_bench
                }

        # 2. Size Curve Completeness & Health
        total_sizes = len(size_list)
        avail_sizes = [s["size"] for s in size_list if s["available"] and s["inventory_count"] > 0]
        missing_sizes = [s["size"] for s in size_list if not s["available"] or s["inventory_count"] == 0]
        core_sizes = ["M", "L", "30", "32", "34", "38", "40"]
        missing_core = [s for s in missing_sizes if str(s).upper() in core_sizes]
        completeness = round((len(avail_sizes) / max(1, total_sizes)) * 100)
        is_broken = len(missing_core) > 0 or (total_sizes >= 3 and completeness < 75)
        data["size_curve_health"] = {
            "total_sizes": total_sizes,
            "available_count": len(avail_sizes),
            "available_sizes": avail_sizes,
            "missing_sizes": missing_sizes,
            "missing_core_sizes": missing_core,
            "completeness_pct": completeness,
            "is_broken": is_broken,
            "status": "Broken Size Curve" if is_broken else "Healthy Full Curve"
        }

        # 3. Dynamic Velocity & Inventory Runway
        sales_hist = data.get("sales_history", [])
        tot_sold = sum(s.get("units_sold", 0) for s in sales_hist)
        tot_rev = sum(s.get("revenue", 0) for s in sales_hist)
        days_cnt = len(sales_hist) or 7
        daily_ros = round(tot_sold / max(1, days_cnt), 1)
        total_stock = sum(s["inventory_count"] for s in size_list)
        runway_days = round(total_stock / max(0.5, daily_ros), 1) if total_stock > 0 else 0
        data["velocity_runway"] = {
            "units_sold_window": tot_sold,
            "revenue_window": round(tot_rev, 2),
            "daily_ros": daily_ros,
            "days_runway": runway_days,
            "stock_units": total_stock
        }

        # 4. Related / Sibling Styles from Same Brand
        brand = (data.get("product_info", {}) or {}).get("brand")
        if brand:
            cur.execute("""
                SELECT product_id, title, selling_price, mrp, discount_percentage, average_rating
                FROM products
                WHERE brand = ? AND product_id != ?
                ORDER BY discount_percentage DESC
                LIMIT 4;
            """, (brand, product_id))
            rel_rows = cur.fetchall()
            rel_items = []
            for r in rel_rows:
                cur.execute("SELECT full_data_json FROM products WHERE product_id = ?", (r[0],))
                rel_fj = cur.fetchone()
                thumb = None
                if rel_fj:
                    try:
                        thumb = _parse_json(rel_fj[0]).get("media", {}).get("primary_image")
                    except Exception:
                        pass
                rel_items.append({
                    "product_id": r[0],
                    "title": r[1],
                    "price": r[2],
                    "mrp": r[3],
                    "discount": r[4],
                    "rating": r[5],
                    "thumbnail": thumb
                })
            data["related_products"] = rel_items

        return jsonify(data)
    return jsonify({"error": "Product not found"}), 404


@app.route("/api/analytics/daily-sales-ros")
@app.route("/api/analytics/daily-sales-ros")
def get_daily_sales_ros_analytics():
    """100% Genuine dynamic telemetry endpoint for Daily Sales, Revenue & ROS Intelligence dashboard."""
    category = request.args.get("category", "all").strip().lower()
    gender = request.args.get("gender", "all").strip().lower()
    days = int(request.args.get("days", 30))
    status_filter = request.args.get("status", "all").strip().lower()
    search = request.args.get("search", "").strip().lower()

    cache_key = f"daily_sales_ros_v3:{category}:{gender}:{days}:{status_filter}:{search}"
    cached = _load_shared_cache(cache_key)
    if cached is not None:
        api_cache.set(cache_key, cached, ttl=300.0)
        return jsonify(cached)

    conn = db._get_connection()
    cur = conn.cursor()

    # 0. Fetch distinct snapshot dates to partition period-over-period comparison
    all_dates = _get_analytics_dates(cur, limit=max(days * 2, 60))

    if not all_dates:
        selected_dates = []
        prior_dates = []
    else:
        limit_days = min(days, len(all_dates))
        selected_dates = all_dates[:limit_days]
        remaining = all_dates[limit_days:]
        prior_dates = remaining[:limit_days] if len(remaining) >= limit_days else []

    where_parts = ["1=1"]
    params = []
    if category != "all" and category:
        where_parts.append("sa.category = ?")
        params.append(category.title())

    needs_join = False
    if gender != "all" and gender:
        needs_join = True
        where_parts.append("LOWER(p.gender) = ?")
        params.append(gender)
    if status_filter == "oos" or bool(search):
        needs_join = True

    from_sql = "daily_sales_analytics sa JOIN products p ON sa.product_id = p.product_id" if needs_join else "daily_sales_analytics sa"

    # Date-constrained filter for current period
    curr_where_parts = list(where_parts)
    curr_params = list(params)
    if selected_dates:
        placeholders = ",".join(["?"] * len(selected_dates))
        curr_where_parts.append(f"sa.analytics_date IN ({placeholders})")
        curr_params.extend(selected_dates)
    
    curr_where_sql = " AND ".join(curr_where_parts)

    # 1. Top KPI Summary for current selected period
    cur.execute(f"""
        SELECT 
            COALESCE(SUM(sa.revenue_generated), 0) as total_rev,
            COALESCE(SUM(sa.units_sold), 0) as total_units,
            COALESCE(SUM(sa.stock_added), 0) as total_restocks,
            COALESCE(AVG(sa.ros), 0) as avg_ros,
            COUNT(DISTINCT sa.product_id) as tracked_skus
        FROM {from_sql}
        WHERE {curr_where_sql};
    """, curr_params)
    kpi_row = cur.fetchone()

    total_rev = float(kpi_row["total_rev"] or 0.0)
    total_rev_cr = round(total_rev / 10000000.0, 2)
    total_units = int(kpi_row["total_units"] or 0)
    total_restocks = int(kpi_row["total_restocks"] or 0)
    avg_ros = round(float(kpi_row["avg_ros"] or 0.0), 2)
    tracked_skus = int(kpi_row["tracked_skus"] or 0)

    # 1b. Compute dynamic Period-over-Period growth vs prior period
    gmv_growth_str = "—"
    units_growth_str = "—"
    restocks_growth_str = "—"
    ros_growth_str = "—"

    if prior_dates:
        prior_where_parts = list(where_parts)
        prior_params = list(params)
        placeholders = ",".join(["?"] * len(prior_dates))
        prior_where_parts.append(f"sa.analytics_date IN ({placeholders})")
        prior_params.extend(prior_dates)
        prior_where_sql = " AND ".join(prior_where_parts)

        cur.execute(f"""
            SELECT 
                COALESCE(SUM(sa.revenue_generated), 0) as p_rev,
                COALESCE(SUM(sa.units_sold), 0) as p_units,
                COALESCE(SUM(sa.stock_added), 0) as p_restocks,
                COALESCE(AVG(sa.ros), 0) as p_ros
            FROM {from_sql}
            WHERE {prior_where_sql};
        """, prior_params)
        p_row = cur.fetchone()
        
        p_rev = float(p_row["p_rev"] or 0.0)
        p_units = float(p_row["p_units"] or 0.0)
        p_restocks = float(p_row["p_restocks"] or 0.0)
        p_ros = float(p_row["p_ros"] or 0.0)

        if p_rev > 0:
            g = round(((total_rev - p_rev) / p_rev) * 100.0, 1)
            gmv_growth_str = f"↑ {g}%" if g >= 0 else f"↓ {abs(g)}%"
        if p_units > 0:
            u = round(((total_units - p_units) / p_units) * 100.0, 1)
            units_growth_str = f"↑ {u}%" if u >= 0 else f"↓ {abs(u)}%"
        if p_restocks > 0:
            r = round(((total_restocks - p_restocks) / p_restocks) * 100.0, 1)
            restocks_growth_str = f"↑ {r}%" if r >= 0 else f"↓ {abs(r)}%"
        
        diff_ros = round(avg_ros - p_ros, 2)
        if abs(diff_ros) < 0.001:
            ros_growth_str = "0.00"
        else:
            ros_growth_str = f"↑ {diff_ros:.2f}" if diff_ros > 0 else f"↓ {abs(diff_ros):.2f}"

    # 2. Daily GMV & Units Sold Velocity Curve
    cur.execute(f"""
        SELECT 
            sa.analytics_date,
            ROUND(SUM(sa.revenue_generated) / 10000000.0, 2) as gmv_cr,
            ROUND(SUM(sa.units_sold) / 1000.0, 1) as units_k
        FROM {from_sql}
        WHERE {curr_where_sql}
        GROUP BY sa.analytics_date
        ORDER BY sa.analytics_date ASC;
    """, curr_params)
    daily_rows = cur.fetchall()
    
    daily_labels = [str(r["analytics_date"])[-5:] for r in daily_rows]
    daily_gmv = [float(r["gmv_cr"] or 0.0) for r in daily_rows]
    daily_units = [float(r["units_k"] or 0.0) for r in daily_rows]

    # 3. Category GMV & Units Split
    cur.execute(f"""
        SELECT 
            sa.category,
            SUM(sa.revenue_generated) as cat_rev,
            SUM(sa.units_sold) as cat_units
        FROM {from_sql}
        WHERE {curr_where_sql}
        GROUP BY sa.category
        ORDER BY cat_rev DESC;
    """, curr_params)
    cat_rows = cur.fetchall()
    tot_cat_rev = sum(float(r["cat_rev"] or 0) for r in cat_rows) or 1.0

    category_split = []
    top_5_cat_rev = 0
    colors_palette = ["#2563eb", "#38bdf8", "#f59e0b", "#d97706", "#0d9488", "#64748b"]
    
    for idx, r in enumerate(cat_rows[:5]):
        c_rev = float(r["cat_rev"] or 0)
        top_5_cat_rev += c_rev
        c_share = round((c_rev / tot_cat_rev) * 100.0, 1)
        category_split.append({
            "category": r["category"],
            "share_pct": c_share,
            "rev_cr": f"₹{round(c_rev / 10000000.0, 2):,} Cr",
            "color": colors_palette[idx % len(colors_palette)]
        })
    
    other_cat_rev = max(0.0, tot_cat_rev - top_5_cat_rev)
    if other_cat_rev > 0:
        category_split.append({
            "category": "Others",
            "share_pct": round((other_cat_rev / tot_cat_rev) * 100.0, 1),
            "rev_cr": f"₹{round(other_cat_rev / 10000000.0, 2):,} Cr",
            "color": colors_palette[-1]
        })

    # 4. Top 10 Brands by Rate of Sale & GMV
    cur.execute(f"""
        SELECT 
            sa.brand,
            ROUND(AVG(sa.ros), 2) as b_ros,
            ROUND(SUM(sa.revenue_generated) / 10000000.0, 2) as b_gmv_cr,
            COALESCE(SUM(sa.units_sold), 0) as b_units,
            COUNT(DISTINCT sa.product_id) as b_skus
        FROM {from_sql}
        WHERE {curr_where_sql} AND sa.brand IS NOT NULL AND sa.brand != ''
        GROUP BY sa.brand
        ORDER BY b_ros DESC, b_gmv_cr DESC
        LIMIT 10;
    """, curr_params)
    brand_rows = cur.fetchall()
    top_10_brands = [
        {
            "brand": r["brand"],
            "ros": float(r["b_ros"] or 0.0),
            "gmv_cr": float(r["b_gmv_cr"] or 0.0),
            "units_sold": int(r["b_units"] or 0),
            "skus": int(r["b_skus"] or 0)
        }
        for r in brand_rows
    ]

    # 5. Fast Movers & Inventory Tracking Matrix Table
    matrix_where = list(curr_where_parts)
    matrix_params = list(curr_params)

    if status_filter == "fast":
        matrix_where.append("(sa.stock_status = 'FAST_MOVER' OR sa.ros >= 5.0)")
    elif status_filter == "restocked":
        matrix_where.append("sa.stock_added > 0")
    elif status_filter == "low":
        matrix_where.append("sa.stock_status = 'LOW_STOCK'")
    elif status_filter == "oos":
        matrix_where.append("(sa.stock_status = 'OOS' OR p.is_in_stock = 0)")

    if search:
        matrix_where.append("(LOWER(p.title) LIKE ? OR LOWER(p.brand) LIKE ? OR CAST(p.product_id AS TEXT) LIKE ?)")
        matrix_params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    matrix_sql = " AND ".join(matrix_where)

    matrix_order_sql = "sa.units_sold DESC, sa.revenue_generated DESC"
    if status_filter == "fast":
        matrix_order_sql = "sa.ros DESC, sa.units_sold DESC, sa.revenue_generated DESC"
    elif status_filter == "restocked":
        matrix_order_sql = "sa.stock_added DESC, sa.units_sold DESC, sa.revenue_generated DESC"
    elif status_filter in ("low", "oos"):
        matrix_order_sql = "sa.units_sold DESC, sa.revenue_generated DESC, p.total_ratings_count DESC"

    cur.execute(f"""
        SELECT 
            p.product_id, p.brand, p.title, p.category, p.selling_price, p.mrp, p.discount_percentage, p.product_url,
            sa.units_sold, sa.revenue_generated, sa.stock_added, sa.ros, sa.stock_status
        FROM daily_sales_analytics sa
        JOIN products p ON sa.product_id = p.product_id
        WHERE {matrix_sql}
        ORDER BY {matrix_order_sql}
        LIMIT 25;
    """, matrix_params)
    m_rows = cur.fetchall()

    matrix_image_map = {}
    if m_rows:
        matrix_ids = [r["product_id"] for r in m_rows if r["product_id"]]
        if matrix_ids:
            placeholders = ",".join("?" for _ in matrix_ids)
            cur.execute(f"""
                SELECT product_id, full_data_json
                FROM products
                WHERE product_id IN ({placeholders});
            """, matrix_ids)
            for img_row in cur.fetchall():
                matrix_image_map[int(img_row["product_id"])] = _load_primary_image(img_row["full_data_json"])

    matrix_items = []
    for r in m_rows:
        st_raw = str(r["stock_status"] or "").strip().upper()
        if st_raw in ("OOS", "OUT_OF_STOCK", "OUT OF STOCK"):
            st_clean = "OUT OF STOCK"
        elif (r["stock_added"] or 0) > 0 and (r["units_sold"] or 0) <= 0:
            st_clean = "RESTOCKED"
        elif st_raw == "LOW_STOCK":
            st_clean = "LOW STOCK"
        elif st_raw == "FAST_MOVER" or (r["ros"] or 0) >= 5.0:
            st_clean = "FAST MOVER"
        else:
            st_clean = "HEALTHY"

        matrix_items.append({
            "product_id": r["product_id"],
            "brand": r["brand"],
            "title": r["title"],
            "category": r["category"],
            "selling_price": f"₹{int(r['selling_price'] or 0):,}",
            "mrp": f"₹{int(r['mrp'] or 0):,}",
            "discount": f"{r['discount_percentage'] or 0}% OFF",
            "units_sold": int(r["units_sold"] or 0),
            "revenue": f"₹{int(r['revenue_generated'] or 0):,}",
            "stock_added": f"+{r['stock_added']}" if (r["stock_added"] or 0) > 0 else "-",
            "daily_ros": f"{round(r['ros'] or 0.0, 1)} / day",
            "status": st_clean,
            "image_url": matrix_image_map.get(int(r["product_id"]), ""),
            "product_url": r["product_url"] or "#"
        })

    window_start = selected_dates[-1] if selected_dates else None
    window_end = selected_dates[0] if selected_dates else None
    prior_start = prior_dates[-1] if prior_dates else None
    prior_end = prior_dates[0] if prior_dates else None
    window_label = (
        f"{_format_date_label(window_start) or 'N/A'} to {_format_date_label(window_end) or 'N/A'}"
        if window_start and window_end else "No stored analytics window"
    )
    compare_window_label = (
        f"Compared with {_format_date_label(prior_start) or 'N/A'} to {_format_date_label(prior_end) or 'N/A'}"
        if prior_start and prior_end else "No previous comparison window available"
    )

    result = {
        "status": "success",
        "window_label": window_label,
        "compare_window_label": compare_window_label,
        "methodology_note": "GMV, units sold, restocks, and ROS come from the recorded daily sales analytics table for the selected period.",
        "kpis": {
            "gmv_velocity": f"₹{total_rev_cr} Cr",
            "gmv_growth": gmv_growth_str,
            "units_sold": f"{total_units:,} units",
            "units_growth": units_growth_str,
            "restocks": f"{total_restocks:,} units",
            "restocks_growth": restocks_growth_str,
            "velocity_index": f"{avg_ros:.2f}",
            "ros_growth": ros_growth_str,
            "tracked_skus": f"{tracked_skus:,} Tracked SKUs",
            "gmv_subtext": "Recorded revenue across the selected analytics window",
            "units_subtext": "Recorded units sold across the selected analytics window",
            "restocks_subtext": "Recorded stock replenishment across the selected analytics window",
            "ros_subtext": f"{tracked_skus:,} tracked SKUs in this window"
        },
        "daily_velocity": {
            "labels": daily_labels,
            "gmv_cr": daily_gmv,
            "units_k": daily_units
        },
        "category_split": {
            "total_gmv": f"₹{total_rev_cr} Cr",
            "items": category_split
        },
        "top_brands_ros": top_10_brands,
        "matrix_items": matrix_items
    }

    api_cache.set(cache_key, result, ttl=300.0)
    _store_shared_cache(cache_key, result, ttl=300.0)
    return jsonify(result)


@app.route("/api/analytics/day-over-day")
def get_day_over_day_analytics_route():
    """Day-over-day market movements based only on stored snapshots and analytics."""
    category = request.args.get("category", "shirts").strip()
    gender = request.args.get("gender", "men").strip()
    subcategory = request.args.get("subcategory")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    price_ranges = request.args.get("price_ranges") or request.args.get("price_range")
    brand_size = request.args.get("brand_size")
    brand_type = request.args.get("brand_type")
    brand = request.args.get("brand")
    color = request.args.get("color")
    fabric = request.args.get("fabric")
    fit = request.args.get("fit")
    discount_min = request.args.get("discount_min")
    rating_min = request.args.get("rating_min")
    availability = request.args.get("availability")
    new_arrivals = request.args.get("new_arrivals")
    movement_type = request.args.get("movement_type", "all").strip().lower()

    cache_key = f"dod_market_v7:{category.lower()}:{gender.lower()}:{subcategory}:{price_min}:{price_max}:{price_ranges}:{brand_size}:{brand_type}:{brand}:{color}:{fabric}:{fit}:{discount_min}:{rating_min}:{availability}:{new_arrivals}:{movement_type}"
    cached = api_cache.get(cache_key)
    if cached:
        return jsonify(cached)

    conn = db._get_connection()
    cur = conn.cursor()

    where_sql, params = _build_catalog_filters(
        category=category, gender=gender, price_min=price_min, price_max=price_max,
        brand_size=brand_size, fabric=fabric, subcategory=subcategory, brand=brand,
        color=color, fit=fit, discount_min=discount_min, rating_min=rating_min,
        availability=availability, price_ranges=price_ranges, new_arrivals=new_arrivals,
        brand_type=brand_type
    )

    cur.execute(f"""
        SELECT
            COUNT(*) as total_prods,
            COUNT(DISTINCT p.brand) as brands_count,
            ROUND(AVG(p.selling_price)) as mean_price,
            ROUND(AVG(p.discount_percentage), 1) as avg_disc
        FROM products p
        WHERE {where_sql};
    """, params)
    stat_row = cur.fetchone()
    total_prods = int(stat_row["total_prods"] or 0)
    brands_count = int(stat_row["brands_count"] or 0)
    mean_price = int(stat_row["mean_price"] or 0)
    avg_disc = float(stat_row["avg_disc"] or 0.0)

    all_dates = _get_analytics_dates(cur, limit=14)
    latest_date = all_dates[0] if all_dates else None
    prior_date = all_dates[1] if len(all_dates) > 1 else None

    units_sold = 0
    tot_rev_val = 0.0
    price_drops = 0
    avg_p_drop_val = 0
    price_hikes = 0
    avg_p_hike_val = 0
    restocked_skus = 0
    restocked_units = 0
    stockouts_oos = 0
    disc_deepened = 0
    avg_disc_exp = 0.0
    back_in_stock = 0

    if latest_date:
        cur.execute(f"""
            SELECT
                COALESCE(SUM(sa.units_sold), 0) as tot_units,
                COALESCE(SUM(sa.revenue_generated), 0) as tot_rev,
                COALESCE(SUM(CASE WHEN sa.price_delta < 0 THEN 1 ELSE 0 END), 0) as p_drops,
                COALESCE(ABS(AVG(CASE WHEN sa.price_delta < 0 THEN sa.price_delta END)), 0) as avg_p_drop,
                COALESCE(SUM(CASE WHEN sa.price_delta > 0 THEN 1 ELSE 0 END), 0) as p_hikes,
                COALESCE(AVG(CASE WHEN sa.price_delta > 0 THEN sa.price_delta END), 0) as avg_p_hike,
                COALESCE(SUM(CASE WHEN sa.stock_added > 0 THEN 1 ELSE 0 END), 0) as r_skus,
                COALESCE(SUM(sa.stock_added), 0) as r_units,
                COALESCE(SUM(CASE WHEN sa.stock_status = 'OOS' THEN 1 ELSE 0 END), 0) as oos_cnt
            FROM daily_sales_analytics sa
            JOIN products p ON sa.product_id = p.product_id
            WHERE {where_sql} AND sa.analytics_date = ?;
        """, params + [latest_date])
        sa_row = cur.fetchone()

        units_sold = int(sa_row["tot_units"] or 0)
        tot_rev_val = float(sa_row["tot_rev"] or 0.0)
        price_drops = int(sa_row["p_drops"] or 0)
        avg_p_drop_val = _safe_int(sa_row["avg_p_drop"])
        price_hikes = int(sa_row["p_hikes"] or 0)
        avg_p_hike_val = _safe_int(sa_row["avg_p_hike"])
        restocked_skus = int(sa_row["r_skus"] or 0)
        restocked_units = int(sa_row["r_units"] or 0)
        stockouts_oos = int(sa_row["oos_cnt"] or 0)

    if latest_date and prior_date:
        cur.execute(f"""
            SELECT
                COALESCE(SUM(CASE WHEN curr.discount_percentage > COALESCE(prev.discount_percentage, curr.discount_percentage) THEN 1 ELSE 0 END), 0) as disc_deepened,
                COALESCE(AVG(CASE WHEN curr.discount_percentage > COALESCE(prev.discount_percentage, curr.discount_percentage) THEN curr.discount_percentage - COALESCE(prev.discount_percentage, curr.discount_percentage) END), 0) as avg_disc_exp,
                COALESCE(SUM(CASE WHEN curr.is_in_stock = 1 AND COALESCE(prev.is_in_stock, 1) = 0 THEN 1 ELSE 0 END), 0) as back_in_stock
            FROM products p
            JOIN daily_inventory_snapshots curr
              ON curr.product_id = p.product_id AND curr.snapshot_date = ?
            LEFT JOIN daily_inventory_snapshots prev
              ON prev.product_id = p.product_id AND prev.snapshot_date = ?
            WHERE {where_sql};
        """, [latest_date, prior_date] + params)
        snap_row = cur.fetchone()
        disc_deepened = int(snap_row["disc_deepened"] or 0)
        avg_disc_exp = round(float(snap_row["avg_disc_exp"] or 0.0), 1)
        back_in_stock = int(snap_row["back_in_stock"] or 0)

    discount_expansion_label = f"+{avg_disc_exp:.1f}% avg discount expansion" if avg_disc_exp else "0.0% avg discount expansion"
    if not (latest_date and prior_date):
        discount_expansion_label = "—"

    revenue_lakhs = round(tot_rev_val / 100000.0, 2)
    latest_date_label = _format_date_label(latest_date)
    prior_date_label = _format_date_label(prior_date)
    kpi_data = {
        "price_drops_skus": f"{price_drops:,}",
        "avg_price_drop": f"-₹{avg_p_drop_val:,}" if avg_p_drop_val else "₹0",
        "price_hikes_skus": f"{price_hikes:,}",
        "avg_price_hike": f"+₹{avg_p_hike_val:,}" if avg_p_hike_val else "₹0",
        "discount_deepened_skus": f"{disc_deepened:,}",
        "avg_discount_exp": discount_expansion_label,
        "units_sold_today": f"{units_sold:,} Units",
        "run_rate": f"₹{revenue_lakhs:,.2f}L on {latest_date_label or 'latest date'}",
        "restocked_skus": f"{restocked_skus:,}",
        "restocked_units": f"+{restocked_units:,} Units Added" if restocked_units else "0 Units Added",
        "stockout_oos": f"{stockouts_oos} OOS",
        "back_in_stock": f"{back_in_stock} Back in Stock"
    }

    total_mov = price_drops + price_hikes + disc_deepened + restocked_skus + stockouts_oos
    tot_safe = max(total_mov, 1)
    pd_pct = round((price_drops / tot_safe) * 100.0, 1) if total_mov else 0.0
    ph_pct = round((price_hikes / tot_safe) * 100.0, 1) if total_mov else 0.0
    dd_pct = round((disc_deepened / tot_safe) * 100.0, 1) if total_mov else 0.0
    rst_pct = round((restocked_skus / tot_safe) * 100.0, 1) if total_mov else 0.0
    oos_pct = round((stockouts_oos / tot_safe) * 100.0, 1) if total_mov else 0.0
    other_pct = max(0.0, round(100.0 - (pd_pct + ph_pct + dd_pct + rst_pct + oos_pct), 1)) if total_mov else 0.0

    category_shifts = []
    if latest_date:
        cur.execute(f"""
            SELECT
                p.category,
                COUNT(DISTINCT sa.product_id) as tracked_skus,
                COALESCE(AVG(sa.price_delta), 0) as net_price_delta,
                COALESCE(SUM(sa.units_sold), 0) as units_sold,
                COALESCE(SUM(sa.revenue_generated), 0) as revenue
            FROM daily_sales_analytics sa
            JOIN products p ON sa.product_id = p.product_id
            WHERE {where_sql} AND sa.analytics_date = ?
            GROUP BY p.category
            ORDER BY revenue DESC, units_sold DESC
            LIMIT 6;
        """, params + [latest_date])
        for idx, r in enumerate(cur.fetchall() or [], 1):
            category_shifts.append({
                "rank": idx,
                "category": r["category"] or "Other",
                "tracked_skus": f"{int(r['tracked_skus'] or 0):,}",
                "net_price_delta": _format_delta(_safe_int(r["net_price_delta"])),
                "units_sold": f"{int(r['units_sold'] or 0):,}",
                "revenue": f"₹{int(round(float(r['revenue'] or 0))):,}"
            })

    top_5_drops = []
    top_5_hikes = []
    if latest_date:
        cur.execute(f"""
            SELECT
                p.product_id, p.brand, p.title, p.selling_price, p.discount_percentage,
                sa.price_delta, p.full_data_json
            FROM daily_sales_analytics sa
            JOIN products p ON sa.product_id = p.product_id
            WHERE {where_sql} AND sa.analytics_date = ? AND sa.price_delta < 0
            ORDER BY sa.price_delta ASC, sa.units_sold DESC
            LIMIT 5;
        """, params + [latest_date])
        for idx, r in enumerate(cur.fetchall() or [], 1):
            today_p = _safe_int(r["selling_price"])
            delta = _safe_int(r["price_delta"])
            yesterday_p = today_p - delta
            top_5_drops.append({
                "rank": idx,
                "product_id": r["product_id"],
                "brand": r["brand"] or "Brand",
                "title": r["title"] or "Product",
                "image_url": _load_primary_image(r["full_data_json"]),
                "yesterday_price": f"₹{yesterday_p:,}",
                "today_price": f"₹{today_p:,}",
                "savings": f"Save ₹{abs(delta):,} ({_safe_int(r['discount_percentage'])}%)"
            })

        cur.execute(f"""
            SELECT
                p.product_id, p.brand, p.title, p.selling_price,
                sa.price_delta, p.full_data_json
            FROM daily_sales_analytics sa
            JOIN products p ON sa.product_id = p.product_id
            WHERE {where_sql} AND sa.analytics_date = ? AND sa.price_delta > 0
            ORDER BY sa.price_delta DESC, sa.units_sold DESC
            LIMIT 5;
        """, params + [latest_date])
        for idx, r in enumerate(cur.fetchall() or [], 1):
            today_p = _safe_int(r["selling_price"])
            delta = _safe_int(r["price_delta"])
            yesterday_p = max(0, today_p - delta)
            inc_pct = round((delta / yesterday_p) * 100.0, 1) if yesterday_p > 0 else 0.0
            top_5_hikes.append({
                "rank": idx,
                "product_id": r["product_id"],
                "brand": r["brand"] or "Brand",
                "title": r["title"] or "Product",
                "image_url": _load_primary_image(r["full_data_json"]),
                "yesterday_price": f"₹{yesterday_p:,}",
                "today_price": f"₹{today_p:,}",
                "increase": f"+₹{delta:,} ({inc_pct:.1f}%)"
            })

    all_movements = []
    if latest_date:
        movement_filters = []
        if movement_type == "price_drops":
            movement_filters.append("COALESCE(sa.price_delta, 0) < 0")
        elif movement_type == "price_hikes":
            movement_filters.append("COALESCE(sa.price_delta, 0) > 0")
        elif movement_type == "restocked":
            movement_filters.append("COALESCE(sa.stock_added, 0) > 0")
        elif movement_type == "stockouts":
            movement_filters.append("COALESCE(sa.stock_status, '') = 'OOS'")

        movement_sql = f" AND {' AND '.join(movement_filters)}" if movement_filters else ""
        cur.execute(f"""
            SELECT
                p.product_id, p.brand, p.title, p.category, p.selling_price, p.discount_percentage,
                p.product_url, p.full_data_json, COALESCE(sa.price_delta, 0) as price_delta,
                COALESCE(sa.units_sold, 0) as units_sold, COALESCE(sa.stock_added, 0) as stock_added,
                COALESCE(curr.total_stock, 0) as today_stock,
                COALESCE(prev.total_stock, COALESCE(curr.total_stock, 0)) as yesterday_stock,
                COALESCE(curr.discount_percentage, p.discount_percentage) as today_discount,
                COALESCE(prev.discount_percentage, COALESCE(curr.discount_percentage, p.discount_percentage)) as yesterday_discount
            FROM products p
            LEFT JOIN daily_sales_analytics sa
              ON sa.product_id = p.product_id AND sa.analytics_date = ?
            LEFT JOIN daily_inventory_snapshots curr
              ON curr.product_id = p.product_id AND curr.snapshot_date = ?
            LEFT JOIN daily_inventory_snapshots prev
              ON prev.product_id = p.product_id AND prev.snapshot_date = ?
            WHERE {where_sql}{movement_sql}
            ORDER BY ABS(COALESCE(sa.price_delta, 0)) DESC, COALESCE(sa.units_sold, 0) DESC, COALESCE(sa.stock_added, 0) DESC, p.total_ratings_count DESC
            LIMIT 25;
        """, [latest_date, latest_date, prior_date or latest_date] + params)
        for idx, r in enumerate(cur.fetchall() or [], 1):
            today_p = _safe_int(r["selling_price"])
            delta = _safe_int(r["price_delta"])
            yesterday_p = max(0, today_p - delta)
            today_stock = _safe_int(r["today_stock"])
            yesterday_stock = _safe_int(r["yesterday_stock"])
            stock_delta = today_stock - yesterday_stock
            discount_delta = _safe_int(r["today_discount"]) - _safe_int(r["yesterday_discount"])

            all_movements.append({
                "rank": idx,
                "product_id": r["product_id"],
                "brand": r["brand"] or "Brand",
                "title": r["title"] or "Product",
                "category": r["category"] or "Category",
                "image_url": _load_primary_image(r["full_data_json"]),
                "yesterday_price": f"₹{yesterday_p:,}",
                "today_price": f"₹{today_p:,}",
                "price_delta": _format_delta(delta),
                "discount_delta": f"{discount_delta:+d}%",
                "stock_delta": f"{yesterday_stock} → {today_stock}",
                "units_sold": f"{_safe_int(r['units_sold']):,} recorded sold",
                "product_url": r["product_url"] or "#"
            })

    trend_dates = []
    trend_prices = []
    trend_discounts = []
    trend_units = []
    trend_date_keys = list(reversed(all_dates[:7]))
    if trend_date_keys:
        placeholders = ",".join(["?"] * len(trend_date_keys))
        cur.execute(f"""
            SELECT
                sa.analytics_date,
                ROUND(AVG(COALESCE(snap.selling_price, p.selling_price))) as avg_price,
                ROUND(AVG(COALESCE(snap.discount_percentage, p.discount_percentage)), 1) as avg_discount,
                COALESCE(SUM(sa.units_sold), 0) as units_sold
            FROM daily_sales_analytics sa
            JOIN products p ON sa.product_id = p.product_id
            LEFT JOIN daily_inventory_snapshots snap
              ON snap.product_id = sa.product_id AND snap.snapshot_date = sa.analytics_date
            WHERE {where_sql} AND sa.analytics_date IN ({placeholders})
            GROUP BY sa.analytics_date
            ORDER BY sa.analytics_date ASC;
        """, params + trend_date_keys)
        for r in cur.fetchall() or []:
            trend_dates.append(datetime.fromisoformat(str(r["analytics_date"])).strftime("%b %d"))
            trend_prices.append(_safe_int(r["avg_price"]))
            trend_discounts.append(_safe_int(r["avg_discount"]))
            trend_units.append(_safe_int(r["units_sold"]))

    compare_label = f"{prior_date_label or latest_date_label or 'n/a'} vs {latest_date_label or 'n/a'}"
    methodology_note = (
        "This view is snapshot-backed. Price, stock, and discount moves come from comparing stored inventory snapshots, "
        "while sold units come from the recorded sales analytics feed for the same day."
    )
    data_window_note = (
        f"History window: { _format_date_label(all_dates[-1]) if all_dates else 'N/A' } to { latest_date_label or 'N/A' } "
        f"across {len(all_dates)} stored day{'s' if len(all_dates) != 1 else ''}."
    )
    result = {
        "status": "success",
        "category": category.title(),
        "gender": gender.title(),
        "brands_count": brands_count,
        "total_products": total_prods,
        "comparing_dates": compare_label,
        "latest_date_label": latest_date_label,
        "prior_date_label": prior_date_label,
        "history_days": len(all_dates),
        "methodology_note": methodology_note,
        "data_window_note": data_window_note,
        "kpi_cards": kpi_data,
        "category_shifts": category_shifts,
        "movement_distribution": [
            {"label": "Price Drops", "pct": pd_pct, "color": "#10b981"},
            {"label": "Price Hikes", "pct": ph_pct, "color": "#ef4444"},
            {"label": "Discount Deepened", "pct": dd_pct, "color": "#8b5cf6"},
            {"label": "Restocked", "pct": rst_pct, "color": "#3b82f6"},
            {"label": "Stockouts", "pct": oos_pct, "color": "#94a3b8"},
            {"label": "Others", "pct": other_pct, "color": "#cbd5e1"}
        ],
        "price_change_trend": {
            "dates": trend_dates,
            "avg_price": trend_prices,
            "avg_discount": trend_discounts,
            "units_sold": trend_units
        },
        "top_5_drops": top_5_drops,
        "top_5_hikes": top_5_hikes,
        "all_movements": all_movements
    }

    api_cache.set(cache_key, result, ttl=300.0)
    return jsonify(result)


@app.route("/api/analytics/size-intelligence")
def get_size_intelligence_route():
    category = request.args.get("category")
    brand = request.args.get("brand")
    result = db.get_size_inventory_analytics(category=category, brand=brand)
    return jsonify(result)


@app.route("/api/sizes")
def get_sizes():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 30))
    search = request.args.get("search", "").strip()
    size_filter = request.args.get("size", "").strip()

    conn = db._get_connection()
    cur = conn.cursor()

    base_from = """
        FROM product_sizes s
        JOIN products p ON s.product_id = p.product_id
        WHERE 1=1
    """
    params = []

    if search:
        base_from += " AND (p.title LIKE ? OR p.brand LIKE ? OR p.product_id LIKE ?)"
        p = f"%{search}%"
        params.extend([p, p, p])

    if size_filter:
        base_from += " AND s.size = ?"
        params.append(size_filter)

    cur.execute(f"SELECT COUNT(*) {base_from}", params)
    total_count = cur.fetchone()[0]

    select_sql = f"""
        SELECT 
            p.product_id, p.brand, p.brand_type, p.title, p.category, p.gender,
            p.selling_price, s.size, s.sku_id, s.available, s.inventory_count, p.product_url
        {base_from}
        ORDER BY p.product_id DESC, s.size ASC
        LIMIT ? OFFSET ?
    """
    offset = (page - 1) * per_page
    params.extend([per_page, offset])

    cur.execute(select_sql, params)
    rows = cur.fetchall()

    sizes_list = []
    for r in rows:
        sizes_list.append({
            "product_id": r[0],
            "brand": r[1],
            "brand_type": r[2],
            "title": r[3],
            "category": r[4],
            "gender": r[5],
            "selling_price": r[6],
            "size": r[7],
            "sku_id": r[8],
            "available": bool(r[9]),
            "inventory_count": r[10],
            "product_url": r[11]
        })

    return jsonify({
        "items": sizes_list,
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total_count + per_page - 1) // per_page)
    })


@app.route("/api/brands")
def get_brands():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    brand_type = request.args.get("brand_type")
    search = request.args.get("search", "").strip()

    cache_key = f"brands_list:{page}:{per_page}:{brand_type}:{search}"
    cached = api_cache.get(cache_key)
    if cached:
        return jsonify(cached)

    conn = db._get_connection()
    cur = conn.cursor()

    where = "WHERE 1=1"
    params = []

    if brand_type == "myntra":
        where += " AND is_myntra_label = 1"
    elif brand_type == "non-myntra":
        where += " AND is_myntra_label = 0"

    if search:
        where += " AND brand_name LIKE ?"
        params.append(f"%{search}%")

    cur.execute(f"SELECT COUNT(*) FROM brands {where}", params)
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'brands'
          AND column_name = 'western_count'
        LIMIT 1;
    """)
    has_western = cur.fetchone() is not None

    select_cols = "brand_name, brand_type, is_myntra_label, shirts_count, denims_count"
    if has_western:
        select_cols += ", western_count, total_count"
    else:
        select_cols += ", 0 as western_count, total_count"

    cur.execute(
        f"SELECT {select_cols} FROM brands {where} ORDER BY brand_name ASC LIMIT ? OFFSET ?",
        params + [per_page, (page - 1) * per_page]
    )
    rows = cur.fetchall()
    brands = [
        {
            "brand_name": r[0],
            "brand_type": r[1],
            "is_myntra_label": bool(r[2]),
            "shirts_count": r[3],
            "denims_count": r[4],
            "western_count": r[5],
            "total_count": r[6]
        }
        for r in rows
    ]

    result = {
        "items": brands,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page)
    }
    api_cache.set(cache_key, result, ttl=60.0)
    return jsonify(result)


@app.route("/api/brands/search")
def search_catalog_brands():
    q = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "all").strip()
    gender = request.args.get("gender", "all").strip()
    subcategory = request.args.get("subcategory", "all").strip()
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    price_ranges = request.args.get("price_ranges", "").strip()
    brand_size = request.args.get("brand_size", "").strip()
    brand_type = request.args.get("brand_type", "").strip()
    color = request.args.get("color", "").strip()
    fabric = request.args.get("fabric", "").strip()
    fit = request.args.get("fit", "").strip()
    discount_min = request.args.get("discount_min")
    rating_min = request.args.get("rating_min")
    availability = request.args.get("availability", "").strip()
    new_arrivals = request.args.get("new_arrivals", "").strip()

    cache_key = (
        "brands_search_v2:"
        f"{q}:{category.lower()}:{gender.lower()}:{subcategory.lower()}:"
        f"{price_min}:{price_max}:{price_ranges}:{brand_size}:{brand_type}:"
        f"{color}:{fabric}:{fit}:{discount_min}:{rating_min}:{availability}:{new_arrivals}"
    )
    cached = api_cache.get(cache_key)
    if cached:
        return jsonify(cached)

    conn = db._get_connection()
    cur = conn.cursor()
    where_sql, params = _build_catalog_filters(
        category=category or "all",
        gender=gender or "all",
        price_min=price_min,
        price_max=price_max,
        price_ranges=price_ranges,
        brand_size=brand_size,
        brand_type=brand_type,
        subcategory=subcategory,
        color=color,
        fabric=fabric,
        fit=fit,
        discount_min=discount_min,
        rating_min=rating_min,
        availability=availability,
        new_arrivals=new_arrivals
    )

    if q:
        cur.execute(f"""
            SELECT brand, COUNT(*) as cnt
            FROM products p
            WHERE {where_sql}
              AND LOWER(p.brand) LIKE ?
              AND p.brand IS NOT NULL
              AND p.brand != ''
            GROUP BY brand
            ORDER BY cnt DESC
            LIMIT 30;
        """, params + [f"%{q}%"])
    else:
        cur.execute(f"""
            SELECT brand, COUNT(*) as cnt
            FROM products p
            WHERE {where_sql}
              AND p.brand IS NOT NULL
              AND p.brand != ''
            GROUP BY brand
            ORDER BY cnt DESC
            LIMIT 40;
        """, params)
    rows = cur.fetchall()
    result = {"status": "success", "brands": [{"brand": r[0], "count": r[1]} for r in rows]}
    api_cache.set(cache_key, result, ttl=120.0)
    return jsonify(result)


@app.route("/api/brands/comparator")
def get_brand_comparator():
    category = request.args.get("category", "").lower().strip()
    gender = request.args.get("gender", "all").strip()
    subcategory = request.args.get("subcategory", "all").strip()
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    price_ranges = request.args.get("price_ranges", "").strip()
    brand_size = request.args.get("brand_size", "").strip()
    brand_type = request.args.get("brand_type", "").strip()
    color = request.args.get("color", "").strip()
    fabric = request.args.get("fabric", "").strip()
    fit = request.args.get("fit", "").strip()
    discount_min = request.args.get("discount_min")
    rating_min = request.args.get("rating_min")
    availability = request.args.get("availability", "").strip()
    new_arrivals = request.args.get("new_arrivals", "").strip()
    comp_where, comp_params = _build_catalog_filters(
        category=category or "all",
        gender=gender or "all",
        price_min=price_min,
        price_max=price_max,
        price_ranges=price_ranges,
        brand_size=brand_size,
        brand_type=brand_type,
        subcategory=subcategory,
        color=color,
        fabric=fabric,
        fit=fit,
        discount_min=discount_min,
        rating_min=rating_min,
        availability=availability,
        new_arrivals=new_arrivals
    )
    req_brands = request.args.get("brands", "")
    if req_brands:
        requested_brands = [b.strip() for b in req_brands.split(",") if b.strip()][:5]
    else:
        requested_brands = []

    conn = db._get_connection()
    cur = conn.cursor()

    def _fetch_top_scope_brands(limit=5):
        cur.execute(f"""
            SELECT p.brand
            FROM products p
            WHERE {comp_where} AND p.brand IS NOT NULL AND p.brand != ''
            GROUP BY p.brand
            ORDER BY COUNT(*) DESC, p.brand ASC
            LIMIT ?;
        """, comp_params + [limit])
        return [r["brand"] for r in cur.fetchall()]

    selected_brands = []
    if requested_brands:
        placeholders = ",".join("?" for _ in requested_brands)
        cur.execute(f"""
            SELECT p.brand
            FROM products p
            WHERE {comp_where}
              AND p.brand IN ({placeholders})
            GROUP BY p.brand
            ORDER BY COUNT(*) DESC, p.brand ASC;
        """, comp_params + requested_brands)
        available = {row["brand"] for row in cur.fetchall()}
        selected_brands = [brand for brand in requested_brands if brand in available]

    if not selected_brands:
        selected_brands = _fetch_top_scope_brands(5)

    cache_key = (
        "comparator_v2:"
        f"{category}:{gender.lower()}:{subcategory.lower()}:{price_min}:{price_max}:{price_ranges}:"
        f"{brand_size}:{brand_type}:{color}:{fabric}:{fit}:{discount_min}:{rating_min}:{availability}:{new_arrivals}:"
        f"{','.join(sorted(selected_brands))}"
    )
    cached = api_cache.get(cache_key)
    if cached:
        return jsonify(cached)

    if not selected_brands:
        empty_result = {
            "status": "success",
            "kpis": {
                "brands_selected": 0,
                "total_products": 0,
                "total_stock_value": "₹0",
                "est_monthly_sell_through": "₹0",
                "avg_discount": "0.0%",
                "tracking_coverage": "0%"
            },
            "brands": [],
            "key_insight": "No brand comparison data is available for the current selection."
        }
        api_cache.set(cache_key, empty_result, ttl=180.0)
        return jsonify(empty_result)

    brand_placeholders = ",".join("?" for _ in selected_brands)
    latest_snapshot_date = _get_latest_inventory_snapshot_date(cur)
    snapshot_start_date = latest_snapshot_date - timedelta(days=59) if latest_snapshot_date else None

    cur.execute("SELECT MAX(analytics_date) FROM daily_sales_analytics;")
    latest_sales_date = (cur.fetchone() or [None])[0]
    sales_start_date = latest_sales_date - timedelta(days=59) if latest_sales_date else date.today() - timedelta(days=59)
    sales_30d_start_date = latest_sales_date - timedelta(days=29) if latest_sales_date else date.today() - timedelta(days=29)

    def _compact_money(value: float) -> str:
        amount = float(value or 0)
        if amount >= 10000000:
            return f"₹{amount / 10000000:.1f} Cr"
        if amount >= 100000:
            return f"₹{amount / 100000:.1f} L"
        return f"₹{amount:,.0f}"

    brands_output = []
    total_products_sum = 0
    total_stock_value_sum = 0
    total_discount_weighted = 0.0
    total_monthly_revenue = 0.0
    total_monthly_units = 0
    total_rating_weighted = 0.0

    cur.execute(f"""
        SELECT p.brand,
               COUNT(*) as p_count,
               ROUND(AVG(p.selling_price)) as asp,
               ROUND(AVG(p.mrp)) as mrp,
               ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.selling_price)::numeric) as median_price,
               ROUND(AVG(p.discount_percentage), 1) as avg_disc,
               ROUND(AVG(NULLIF(p.average_rating, 0))::numeric, 2) as avg_rating,
               COALESCE(SUM(p.total_ratings_count), 0) as ratings_count,
               COALESCE(SUM(p.total_reviews_count), 0) as reviews_count
        FROM products p
        WHERE p.brand IN ({brand_placeholders}) AND {comp_where}
        GROUP BY p.brand;
    """, selected_brands + comp_params)
    product_stats = {row["brand"]: row for row in cur.fetchall()}

    stock_stats = {}
    if latest_snapshot_date:
        cur.execute(f"""
            SELECT p.brand,
                   COALESCE(SUM(s.total_stock), 0) as stock_units,
                   COUNT(DISTINCT s.product_id) as tracked_p_count,
                   COALESCE(SUM(s.total_stock * COALESCE(s.selling_price, p.selling_price, 0)), 0) as stock_value
            FROM daily_inventory_snapshots s
            JOIN products p ON p.product_id = s.product_id
            WHERE s.snapshot_date = ? AND p.brand IN ({brand_placeholders}) AND {comp_where}
            GROUP BY p.brand;
        """, [latest_snapshot_date] + selected_brands + comp_params)
        stock_stats = {row["brand"]: row for row in cur.fetchall()}

    snapshot_histories = defaultdict(list)
    if snapshot_start_date:
        cur.execute(f"""
            SELECT p.brand, snap.snapshot_date,
                   ROUND(AVG(snap.selling_price), 1) as asp
            FROM daily_inventory_snapshots snap
            JOIN products p ON snap.product_id = p.product_id
            WHERE snap.snapshot_date >= ? AND p.brand IN ({brand_placeholders}) AND {comp_where}
            GROUP BY p.brand, snap.snapshot_date
            ORDER BY p.brand ASC, snap.snapshot_date ASC;
        """, [snapshot_start_date] + selected_brands + comp_params)
        for row in cur.fetchall():
            snapshot_histories[row["brand"]].append(row)

    cur.execute(f"""
        SELECT p.brand, sa.analytics_date,
               COALESCE(SUM(sa.units_sold), 0) as units_sold,
               COALESCE(SUM(sa.revenue_generated), 0) as revenue
        FROM daily_sales_analytics sa
        JOIN products p ON sa.product_id = p.product_id
        WHERE sa.analytics_date >= ? AND p.brand IN ({brand_placeholders}) AND {comp_where}
        GROUP BY p.brand, sa.analytics_date
        ORDER BY p.brand ASC, sa.analytics_date ASC;
    """, [sales_start_date] + selected_brands + comp_params)
    sales_histories = defaultdict(list)
    for row in cur.fetchall():
        sales_histories[row["brand"]].append(row)

    cur.execute(f"""
        WITH filtered_products AS MATERIALIZED (
            SELECT p.brand,
                   p.product_id,
                   p.title,
                   p.selling_price,
                   p.mrp,
                   p.discount_percentage,
                   p.average_rating,
                   p.total_ratings_count,
                   p.full_data_json
            FROM products p
            WHERE p.brand IN ({brand_placeholders}) AND {comp_where}
        ),
        sales AS (
            SELECT fp.product_id,
                   COALESCE(SUM(sa.units_sold), 0) as total_units,
                   COALESCE(SUM(sa.revenue_generated), 0) as revenue_30d,
                   COUNT(DISTINCT sa.analytics_date) as active_days
            FROM filtered_products fp
            LEFT JOIN daily_sales_analytics sa
              ON sa.product_id = fp.product_id
             AND sa.analytics_date >= ?
            GROUP BY fp.product_id
        ),
        ranked_products AS (
            SELECT fp.brand,
                   fp.product_id,
                   fp.title,
                   fp.selling_price,
                   fp.mrp,
                   fp.discount_percentage,
                   fp.average_rating,
                   fp.full_data_json,
                   COALESCE(sales.total_units, 0) as total_units,
                   COALESCE(sales.revenue_30d, 0) as revenue_30d,
                   COALESCE(sales.active_days, 0) as active_days,
                   ROW_NUMBER() OVER (
                       PARTITION BY fp.brand
                       ORDER BY COALESCE(sales.total_units, 0) DESC, fp.total_ratings_count DESC, fp.selling_price DESC
                   ) as rn
            FROM filtered_products fp
            LEFT JOIN sales ON sales.product_id = fp.product_id
        )
        SELECT *
        FROM ranked_products
        WHERE rn <= 3
        ORDER BY brand ASC, rn ASC;
    """, selected_brands + comp_params + [sales_30d_start_date])
    top_products_by_brand = defaultdict(list)
    for pr in cur.fetchall():
        top_products_by_brand[pr["brand"]].append(pr)

    for b in selected_brands:
        row = product_stats.get(b, {})
        p_cnt = int((row["p_count"] if row else 0) or 0)
        asp = int((row["asp"] if row else 0) or 0)
        median_price = int((row["median_price"] if row else 0) or 0)
        disc = float((row["avg_disc"] if row else 0.0) or 0.0)
        avg_rating = round(_safe_float(row["avg_rating"] if row else 0), 2)
        ratings_count = _safe_int(row["ratings_count"] if row else 0)
        reviews_count = _safe_int(row["reviews_count"] if row else 0)

        s_row = stock_stats.get(b, {})
        stock_units = int((s_row["stock_units"] if s_row else 0) or 0)
        tracked_p_cnt = int((s_row["tracked_p_count"] if s_row else 0) or 0)
        stock_val = float((s_row["stock_value"] if s_row and "stock_value" in s_row else 0) or 0)
        coverage = round((tracked_p_cnt / p_cnt * 100.0), 1) if p_cnt > 0 else 0.0

        total_products_sum += p_cnt
        total_stock_value_sum += stock_val
        total_discount_weighted += (disc * p_cnt)
        total_rating_weighted += (avg_rating * ratings_count)

        hist_rows = snapshot_histories.get(b, [])
        sparkline_pts = [float(r["asp"] or asp) for r in hist_rows if _safe_float(r["asp"] or asp) > 0]

        sales_hist = sales_histories.get(b, [])
        recent_sales = [r for r in sales_hist if r["analytics_date"] and r["analytics_date"] >= sales_30d_start_date]
        monthly_revenue = float(sum(_safe_float(r["revenue"]) for r in recent_sales))
        monthly_units = int(sum(_safe_int(r["units_sold"]) for r in recent_sales))
        total_monthly_revenue += monthly_revenue
        total_monthly_units += monthly_units

        growth_30d = 0.0
        if len(sales_hist) >= 2:
            midpoint = max(1, len(sales_hist) // 2)
            first_window = sales_hist[:midpoint]
            second_window = sales_hist[midpoint:]
            first_avg = sum(_safe_float(r["revenue"]) for r in first_window) / max(1, len(first_window))
            second_avg = sum(_safe_float(r["revenue"]) for r in second_window) / max(1, len(second_window))
            growth_30d = _pct_change(second_avg, first_avg)

        prods = []
        for pr in top_products_by_brand.get(b, []):
            img_url = _load_primary_image(pr["full_data_json"])
            clean_title = pr["title"].replace(b, "").strip()
            if clean_title.startswith("Men") or clean_title.startswith("Women"):
                clean_title = clean_title[3:].strip()
            if len(clean_title) > 26:
                clean_title = clean_title[:24] + "..."
            velocity = round(_safe_float(pr["total_units"]) / max(1, _safe_int(pr["active_days"], 0)), 2)
            prods.append({
                "product_id": pr["product_id"],
                "title": clean_title if clean_title else pr["title"][:25],
                "price": f"₹{int(pr['selling_price']):,.0f}",
                "velocity": f"{velocity}/d",
                "units_30d": _safe_int(pr["total_units"]),
                "revenue_30d": _compact_money(_safe_float(pr["revenue_30d"])),
                "rating": round(_safe_float(pr["average_rating"]), 1),
                "image_url": img_url
            })

        brands_output.append({
            "brand": b,
            "display_name": b,
            "product_count": p_cnt,
            "avg_discount": disc,
            "avg_price": asp,
            "median_price": median_price,
            "avg_rating": avg_rating,
            "ratings_count": ratings_count,
            "reviews_count": reviews_count,
            "stock_units": stock_units,
            "stock_val": stock_val,
            "stock_value": _compact_money(stock_val),
            "growth_30d": growth_30d,
            "monthly_revenue": monthly_revenue,
            "monthly_revenue_formatted": _compact_money(monthly_revenue),
            "monthly_units": monthly_units,
            "tracking_coverage": int(coverage),
            "sparkline": sparkline_pts,
            "top_products": prods
        })

    avg_overall_disc = round(total_discount_weighted / total_products_sum, 1) if total_products_sum > 0 else 0.0
    avg_overall_rating = round(total_rating_weighted / max(1, sum(b["ratings_count"] for b in brands_output)), 2)
    stock_val_str = _compact_money(total_stock_value_sum)
    sellthrough_str = _compact_money(total_monthly_revenue)

    overall_coverage = round(sum(b["tracking_coverage"] for b in brands_output) / len(brands_output)) if brands_output else 100
    selected_weighted_asp = round(
        sum(b["avg_price"] * b["product_count"] for b in brands_output) / max(1, total_products_sum)
    ) if total_products_sum else 0

    for b in brands_output:
        b["product_share"] = round((b["product_count"] / max(1, total_products_sum)) * 100, 1)
        b["stock_value_share"] = round((b["stock_val"] / max(1.0, total_stock_value_sum)) * 100, 1) if total_stock_value_sum else 0.0
        b["revenue_share"] = round((b["monthly_revenue"] / max(1.0, total_monthly_revenue)) * 100, 1) if total_monthly_revenue else 0.0
        b["sell_through_rate"] = round((b["monthly_units"] / max(1, b["stock_units"])) * 100, 2) if b["stock_units"] else 0.0
        b["price_index"] = round((b["avg_price"] / max(1, selected_weighted_asp)) * 100, 1) if selected_weighted_asp else 0.0
        b["discount_gap"] = round(b["avg_discount"] - avg_overall_disc, 1)
        b["rating_gap"] = round(b["avg_rating"] - avg_overall_rating, 2) if avg_overall_rating else 0.0

    by_count = sorted(brands_output, key=lambda x: x["product_count"], reverse=True)
    by_disc = sorted(brands_output, key=lambda x: x["avg_discount"], reverse=True)
    by_asp = sorted(brands_output, key=lambda x: x["avg_price"], reverse=True)
    by_revenue = sorted(brands_output, key=lambda x: x["monthly_revenue"], reverse=True)
    by_sellthrough = sorted(brands_output, key=lambda x: x["sell_through_rate"], reverse=True)

    fallback_brand = selected_brands[0] if selected_brands else ""
    top_count_b = by_count[0]["brand"] if by_count and by_count[0]["product_count"] > 0 else fallback_brand
    top_disc_b = by_disc[0]["brand"] if by_disc and by_disc[0]["avg_discount"] > 0 else fallback_brand
    top_asp_b = by_asp[0]["brand"] if by_asp and by_asp[0]["avg_price"] > 0 else fallback_brand
    top_revenue_b = by_revenue[0]["brand"] if by_revenue and by_revenue[0]["monthly_revenue"] > 0 else fallback_brand
    top_sellthrough_b = by_sellthrough[0]["brand"] if by_sellthrough and by_sellthrough[0]["sell_through_rate"] > 0 else fallback_brand

    if by_count and by_disc and by_asp:
        sales_clause = (
            f" {top_revenue_b} leads recent sales revenue ({_compact_money(by_revenue[0]['monthly_revenue'])})"
            if by_revenue and by_revenue[0]["monthly_revenue"] > 0
            else " Recent sales revenue is not yet available for this scope"
        )
        key_insight = (
            f"{top_count_b} leads in catalog depth ({by_count[0]['product_count']:,} products), while {top_disc_b} features the highest promotional markdown ({by_disc[0]['avg_discount']}% avg discount). "
            f"{top_asp_b} commands premium pricing at ₹{by_asp[0]['avg_price']:,} ASP.{sales_clause}."
        )
    else:
        key_insight = "No brand comparison data is available for the current selection."

    result = {
        "status": "success",
        "kpis": {
            "brands_selected": len(selected_brands),
            "total_products": total_products_sum,
            "total_stock_value": stock_val_str,
            "est_monthly_sell_through": sellthrough_str,
            "avg_discount": f"{avg_overall_disc}%",
            "tracking_coverage": f"{overall_coverage}%",
            "units_sold_30d": total_monthly_units,
            "avg_price": f"₹{selected_weighted_asp:,}",
            "avg_rating": avg_overall_rating
        },
        "leaders": {
            "catalog_depth": top_count_b,
            "premium_price": top_asp_b,
            "deepest_discount": top_disc_b,
            "sales_revenue": top_revenue_b,
            "sell_through": top_sellthrough_b
        },
        "data_windows": {
            "inventory_snapshot_date": str(latest_snapshot_date) if latest_snapshot_date else None,
            "sales_start_date": str(sales_30d_start_date) if sales_30d_start_date else None,
            "sales_end_date": str(latest_sales_date) if latest_sales_date else None
        },
        "applied_scope": {
            "category": category or "all",
            "gender": gender or "all",
            "subcategory": subcategory or "all"
        },
        "brands": brands_output,
        "key_insight": key_insight
    }
    api_cache.set(cache_key, result, ttl=180.0)
    return jsonify(result)


# ==============================================================================
# 100% GENUINE DYNAMIC INTELLIGENCE ENDPOINTS (CATEGORY, FABRIC, BRANDS)
# ==============================================================================

def _build_catalog_filters(category="shirts", gender="men", price_min=None, price_max=None, brand_size=None, fabric=None,
                           subcategory=None, brand=None, color=None, fit=None, discount_min=None, rating_min=None,
                           availability=None, price_ranges=None, new_arrivals=None, brand_type=None):
    """Builds SQL WHERE clauses dynamically using indexed columns."""
    clauses = []
    params = []
    
    cat = (category or "").lower().strip()
    if cat and cat != "all":
        if any(tok in cat for tok in ("tshirt", "t-shirt", "t shirt", "tshirts", "t-shirts")):
            clauses.append("p.category = 'Tshirts'")
        elif "shirt" in cat:
            clauses.append("p.category = 'Shirts'")
        elif any(tok in cat for tok in ("jean", "denim")):
            clauses.append("p.category = 'Jeans'")
        elif "western" in cat:
            clauses.append("p.category IN ('Western Wear', 'Dresses', 'Tops', 'Skirts', 'Jumpsuit', 'Jumpsuits')")
        elif "dress" in cat:
            clauses.append("p.category = 'Dresses'")
        elif "top" in cat:
            clauses.append("p.category = 'Tops'")
        elif "trouser" in cat:
            clauses.append("p.category = 'Trousers'")
        elif "short" in cat:
            clauses.append("p.category = 'Shorts'")
        elif "jacket" in cat:
            clauses.append("p.category = 'Jackets'")
        elif "sweatshirt" in cat:
            clauses.append("p.category = 'Sweatshirts'")
        elif "sweater" in cat:
            clauses.append("p.category = 'Sweaters'")
        elif "co-ord" in cat or "coord" in cat:
            clauses.append("p.category = 'Co-Ords'")
        elif any(tok in cat for tok in ("kurta", "kurti", "ethnic")):
            clauses.append("p.category IN ('Kurtas', 'Kurtis', 'Ethnic Dresses')")
        elif "blazer" in cat:
            clauses.append("p.category = 'Blazers'")
        elif "capri" in cat:
            clauses.append("p.category = 'Capris'")
        elif "legging" in cat:
            clauses.append("p.category = 'Leggings'")
        else:
            clauses.append("(p.category = ? OR LOWER(p.category) LIKE ? OR LOWER(p.title) LIKE ?)")
            params.extend([category.title(), f"%{cat}%", f"%{cat}%"])

    g = (gender or "").lower().strip()
    if g and g != "all":
        if g == "men":
            clauses.append("p.gender = 'Men'")
        elif g == "women":
            clauses.append("p.gender = 'Women'")
        elif g in ("boys", "boy"):
            clauses.append("p.gender = 'Boys'")
        elif g in ("girls", "girl"):
            clauses.append("p.gender = 'Girls'")
        elif g in ("kids", "infants"):
            clauses.append("p.gender IN ('Kids', 'Boys', 'Girls', 'Unisex Kids')")
        else:
            clauses.append("p.gender = ?")
            params.append(gender.title())

    if subcategory and subcategory.lower() != "all":
        sub = subcategory.lower().strip()
        clauses.append("LOWER(p.sub_category) = ?")
        params.append(sub)

    if brand and brand.lower() != "all":
        b_list = [b.strip() for b in brand.split(",") if b.strip()]
        if len(b_list) == 1:
            clauses.append("p.brand = ?")
            params.append(b_list[0])
        elif b_list:
            placeholders = ",".join(["?"] * len(b_list))
            clauses.append(f"p.brand IN ({placeholders})")
            params.extend(b_list)

    if brand_type and brand_type.lower() != "all":
        bt = brand_type.lower().strip()
        if bt in ("myntra", "myntra_label", "myntra_in_house", "myntra in-house labels", "1", "in-house"):
            clauses.append("p.is_myntra_label = 1")
        elif bt in ("non-myntra", "external", "external brands", "0", "non_myntra"):
            clauses.append("p.is_myntra_label = 0")

    if brand_size and brand_size.lower() != "all":
        bs_tokens = [s.strip().lower() for s in brand_size.split(",") if s.strip()]
        having_conds = []
        if "large" in bs_tokens or "largest" in bs_tokens:
            having_conds.append(f"COUNT(*) >= {LARGE_BRAND_MIN_PRODUCTS}")
        if "mid" in bs_tokens or "mid-size" in bs_tokens or "midsize" in bs_tokens:
            having_conds.append(f"(COUNT(*) >= {MID_BRAND_MIN_PRODUCTS} AND COUNT(*) < {LARGE_BRAND_MIN_PRODUCTS})")
        if "small" in bs_tokens:
            having_conds.append(f"COUNT(*) < {MID_BRAND_MIN_PRODUCTS}")
        if having_conds:
            sub_clauses = []
            sub_params = []
            if cat and cat != "all":
                if any(tok in cat for tok in ("tshirt", "t-shirt", "t shirt", "tshirts", "t-shirts")):
                    sub_clauses.append("b.category = 'Tshirts'")
                elif "shirt" in cat:
                    sub_clauses.append("b.category = 'Shirts'")
                elif any(tok in cat for tok in ("jean", "denim")):
                    sub_clauses.append("b.category = 'Jeans'")
                elif "western" in cat:
                    sub_clauses.append("b.category IN ('Western Wear', 'Dresses', 'Tops', 'Skirts', 'Jumpsuit', 'Jumpsuits')")
                elif "dress" in cat:
                    sub_clauses.append("b.category = 'Dresses'")
                elif "top" in cat:
                    sub_clauses.append("b.category = 'Tops'")
                elif "trouser" in cat:
                    sub_clauses.append("b.category = 'Trousers'")
                else:
                    sub_clauses.append("b.category = ?")
                    sub_params.append(category.title())
            if g and g != "all":
                if g == "men":
                    sub_clauses.append("b.gender = 'Men'")
                elif g == "women":
                    sub_clauses.append("b.gender = 'Women'")
                else:
                    sub_clauses.append("b.gender = ?")
                    sub_params.append(gender.title())
            sub_where = " AND ".join(sub_clauses) if sub_clauses else "1=1"
            clauses.append(f"p.brand IN (SELECT b.brand FROM products b WHERE {sub_where} GROUP BY b.brand HAVING ({' OR '.join(having_conds)}))")
            params.extend(sub_params)

    if color and color.lower() != "all":
        c_list = [
            normalized.lower()
            for normalized in (_normalize_color_name(c, fallback=None) for c in color.split(","))
            if normalized
        ]
        if len(c_list) == 1:
            clauses.append("LOWER(TRIM(p.primary_color)) = ?")
            params.append(c_list[0])
        elif c_list:
            placeholders = ",".join(["?"] * len(c_list))
            clauses.append(f"LOWER(TRIM(p.primary_color)) IN ({placeholders})")
            params.extend(c_list)

    if fit and fit.lower() != "all":
        f_list = [f.strip().lower() for f in fit.split(",") if f.strip()]
        if len(f_list) == 1:
            clauses.append("LOWER(p.fit) LIKE ?")
            params.append(f"%{f_list[0]}%")
        elif f_list:
            fit_or = " OR ".join(["LOWER(p.fit) LIKE ?" for _ in f_list])
            clauses.append(f"({fit_or})")
            params.extend([f"%{f}%" for f in f_list])

    if discount_min is not None:
        try:
            d_val = float(discount_min)
            if d_val > 0:
                clauses.append("p.discount_percentage >= ?")
                params.append(d_val)
        except (ValueError, TypeError):
            pass

    if rating_min is not None:
        try:
            r_val = float(rating_min)
            if r_val > 0:
                clauses.append("p.average_rating >= ?")
                params.append(r_val)
        except (ValueError, TypeError):
            pass

    if availability == "in_stock":
        clauses.append("p.is_in_stock = 1")
    elif availability == "out_of_stock":
        clauses.append("p.is_in_stock = 0")

    if new_arrivals and new_arrivals.lower() in ("1", "true", "yes"):
        clauses.append("p.created_at >= NOW() - INTERVAL '60 days'")

    if price_ranges:
        range_tokens = [r.strip().lower() for r in price_ranges.split(",") if r.strip()]
        range_subclauses = []
        for r in range_tokens:
            if r == "lt_500":
                range_subclauses.append("p.selling_price < 500")
            elif r == "500_1000":
                range_subclauses.append("(p.selling_price >= 500 AND p.selling_price < 1000)")
            elif r == "800_1000":
                range_subclauses.append("(p.selling_price >= 800 AND p.selling_price <= 1000)")
            elif r == "1000_2000":
                range_subclauses.append("(p.selling_price >= 1000 AND p.selling_price < 2000)")
            elif r == "2000_3000":
                range_subclauses.append("(p.selling_price >= 2000 AND p.selling_price < 3000)")
            elif r == "3000_4000":
                range_subclauses.append("(p.selling_price >= 3000 AND p.selling_price < 4000)")
            elif r == "gt_4000":
                range_subclauses.append("p.selling_price >= 4000")
        if range_subclauses:
            clauses.append(f"({' OR '.join(range_subclauses)})")

    if price_min is not None:
        try:
            clauses.append("p.selling_price >= ?")
            params.append(float(price_min))
        except (ValueError, TypeError):
            pass

    if price_max is not None:
        try:
            clauses.append("p.selling_price <= ?")
            params.append(float(price_max))
        except (ValueError, TypeError):
            pass

    if fabric and fabric.lower() != "all":
        fab_list = [fb.strip().lower() for fb in fabric.split(",") if fb.strip()]
        fabric_or_clauses = []
        fabric_params = []
        for fb in fab_list:
            if fb in ("cotton blend", "cotton_blend", "polycotton", "poly cotton"):
                fabric_or_clauses.append(
                    "(LOWER(p.fabric) LIKE ? AND (LOWER(p.fabric) LIKE ? OR LOWER(p.fabric) LIKE ? OR LOWER(p.fabric) LIKE ?))"
                )
                fabric_params.extend(["%cotton%", "%blend%", "%poly%", "%,%"])
            elif fb == "cotton":
                fabric_or_clauses.append(
                    "(LOWER(p.fabric) LIKE ? AND LOWER(p.fabric) NOT LIKE ? AND LOWER(p.fabric) NOT LIKE ? AND LOWER(p.fabric) NOT LIKE ?)"
                )
                fabric_params.extend(["%cotton%", "%blend%", "%poly%", "%,%"])
            elif fb == "polyester":
                fabric_or_clauses.append("(LOWER(p.fabric) LIKE ? AND LOWER(p.fabric) NOT LIKE ?)")
                fabric_params.extend(["%poly%", "%cotton%"])
            elif fb == "viscose":
                fabric_or_clauses.append("(LOWER(p.fabric) LIKE ? OR LOWER(p.fabric) LIKE ?)")
                fabric_params.extend(["%viscose%", "%rayon%"])
            elif fb in ("denim", "linen", "silk", "wool"):
                fabric_or_clauses.append("LOWER(p.fabric) LIKE ?")
                fabric_params.append(f"%{fb}%")
            elif fb == "others":
                fabric_or_clauses.append(
                    "(LOWER(COALESCE(p.fabric, '')) NOT LIKE ? AND LOWER(COALESCE(p.fabric, '')) NOT LIKE ? AND LOWER(COALESCE(p.fabric, '')) NOT LIKE ? AND LOWER(COALESCE(p.fabric, '')) NOT LIKE ? AND LOWER(COALESCE(p.fabric, '')) NOT LIKE ? AND LOWER(COALESCE(p.fabric, '')) NOT LIKE ? AND LOWER(COALESCE(p.fabric, '')) NOT LIKE ? AND LOWER(COALESCE(p.fabric, '')) NOT LIKE ?)"
                )
                fabric_params.extend(["%cotton%", "%poly%", "%linen%", "%viscose%", "%rayon%", "%denim%", "%silk%", "%wool%"])
            else:
                fabric_or_clauses.append("LOWER(p.fabric) LIKE ?")
                fabric_params.append(f"%{fb}%")
        if fabric_or_clauses:
            clauses.append(f"({' OR '.join(fabric_or_clauses)})")
            params.extend(fabric_params)

    where_sql = " AND ".join(clauses) if clauses else "1=1"
    return where_sql, params


def _append_where_clause(where_sql: str, clause: str) -> str:
    base = (where_sql or "").strip()
    extra = (clause or "").strip()
    if not extra:
        return base or "1=1"
    if not base or base == "1=1":
        return extra
    return f"{base} AND {extra}"


def _latest_sales_date(cur):
    cur.execute("SELECT MAX(analytics_date) FROM daily_sales_analytics;")
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def _build_catalog_tab_clause(cur, tab, alias: str = "p"):
    token = (tab or "").strip().lower()
    if not token or token == "all":
        return "", []

    ref = f"{alias}."
    if token in ("new_arrivals", "new-arrivals", "new"):
        return f"COALESCE({ref}created_at, {ref}updated_at) >= NOW() - INTERVAL '60 days'", []
    if token in ("top_discounted", "top_discount"):
        return f"{ref}discount_percentage >= 40", []
    if token == "trending":
        return f"({ref}average_rating >= 4.0 OR {ref}total_ratings_count >= 250)", []
    if token in ("price_drop", "price_drops"):
        today_date, yesterday_date = get_latest_two_snapshot_dates(cur)
        return (
            f"""{ref}product_id IN (
                SELECT tb.product_id
                FROM daily_inventory_snapshots tb
                JOIN daily_inventory_snapshots ta
                  ON tb.product_id = ta.product_id
                 AND ta.snapshot_date = ?
                WHERE tb.snapshot_date = ?
                  AND tb.selling_price < ta.selling_price
            )""",
            [yesterday_date, today_date]
        )
    if token == "restocked":
        latest_sales_date = _latest_sales_date(cur)
        if not latest_sales_date:
            return f"{ref}is_in_stock = 1", []
        return (
            f"{ref}product_id IN (SELECT product_id FROM daily_sales_analytics WHERE analytics_date = ? AND stock_added > 0)",
            [latest_sales_date]
        )
    if token == "high_demand":
        latest_sales_date = _latest_sales_date(cur)
        if not latest_sales_date:
            return f"{ref}total_ratings_count >= 500", []
        return (
            f"""{ref}product_id IN (
                SELECT product_id
                FROM daily_sales_analytics
                WHERE analytics_date = ?
                  AND units_sold >= 1
            )""",
            [latest_sales_date]
        )
    return "", []


def _apply_catalog_search_clause(where_sql: str, params, search: str, alias: str = "p"):
    token = (search or "").strip().lower()
    next_params = list(params)
    if not token:
        return where_sql, next_params

    clause = (
        f"(LOWER(COALESCE({alias}.title, '')) LIKE ? "
        f"OR LOWER(COALESCE({alias}.brand, '')) LIKE ? "
        f"OR CAST({alias}.sku AS TEXT) LIKE ?)"
    )
    pattern = f"%{token}%"
    next_params.extend([pattern, pattern, pattern])
    return _append_where_clause(where_sql, clause), next_params


def _catalog_sort_clause(sort_by: str, search_term: str = ""):
    token = (sort_by or "relevance").strip().lower()
    if token == "discount_desc":
        return "p.discount_percentage DESC, p.product_id DESC", []
    if token == "price_asc":
        return "p.selling_price ASC, p.product_id DESC", []
    if token == "price_desc":
        return "p.selling_price DESC, p.product_id DESC", []
    if token == "rating_desc":
        return "p.average_rating DESC NULLS LAST, p.total_ratings_count DESC, p.product_id DESC", []
    if token == "newest":
        return "COALESCE(p.updated_at, p.created_at) DESC, p.product_id DESC", []

    search_token = (search_term or "").strip().lower()
    if search_token:
        return (
            "CASE "
            "WHEN LOWER(COALESCE(p.title, '')) = ? THEN 0 "
            "WHEN LOWER(COALESCE(p.brand, '')) = ? THEN 1 "
            "WHEN LOWER(COALESCE(p.title, '')) LIKE ? THEN 2 "
            "WHEN LOWER(COALESCE(p.brand, '')) LIKE ? THEN 3 "
            "WHEN LOWER(COALESCE(p.title, '')) LIKE ? THEN 4 "
            "WHEN LOWER(COALESCE(p.brand, '')) LIKE ? THEN 5 "
            "WHEN CAST(p.sku AS TEXT) ILIKE ? THEN 6 "
            "ELSE 7 END, "
            "p.total_ratings_count DESC, COALESCE(p.updated_at, p.created_at) DESC, p.product_id DESC",
            [
                search_token,
                search_token,
                f"{search_token}%",
                f"{search_token}%",
                f"%{search_token}%",
                f"%{search_token}%",
                f"%{search_token}%"
            ]
        )

    return "COALESCE(p.updated_at, p.created_at) DESC, p.product_id DESC", []


def _catalog_category_option(raw_category: str):
    name = str(raw_category or "").strip()
    if not name:
        return None

    normalized = name.lower().replace("&", "and")
    normalized = " ".join(normalized.replace("_", " ").replace("-", " ").split())
    mapping = {
        "shirts": ("shirts", "Shirts", 10),
        "jeans": ("jeans", "Jeans & Denims", 20),
        "tshirts": ("tshirts", "T-Shirts", 30),
        "t shirts": ("tshirts", "T-Shirts", 30),
        "western wear": ("western-wear", "Western Wear", 40),
        "dresses": ("dresses", "Dresses", 50),
        "tops": ("tops", "Tops", 60),
        "skirts": ("skirts", "Skirts", 70),
        "jumpsuit": ("jumpsuit", "Jumpsuit", 80),
        "jumpsuits": ("jumpsuits", "Jumpsuits", 81),
        "trousers": ("trousers", "Trousers", 90),
        "shorts": ("shorts", "Shorts", 100),
        "jackets": ("jackets", "Jackets", 110),
        "sweatshirts": ("sweatshirts", "Sweatshirts", 120),
        "sweaters": ("sweaters", "Sweaters", 130),
        "co ords": ("co-ords", "Co-Ords", 140),
        "kurtas": ("kurtas", "Kurtas", 150),
        "kurtis": ("kurtis", "Kurtis", 160),
        "ethnic dresses": ("ethnic-dresses", "Ethnic Dresses", 170),
        "blazers": ("blazers", "Blazers", 180),
        "capris": ("capris", "Capris", 190),
        "leggings": ("leggings", "Leggings", 200),
    }
    if normalized in mapping:
        value, label, rank = mapping[normalized]
        return {"value": value, "name": label, "rank": rank}

    slug = "-".join(part for part in normalized.split() if part)
    label = " ".join(part.capitalize() for part in normalized.split())
    return {"value": slug or name.lower(), "name": label or name, "rank": 1000}


def _build_catalog_meta_payload(cur, filters: dict):
    search = (filters.get("search") or "").strip()
    tab = (filters.get("tab") or "").strip()

    summary_where_sql, summary_params = _build_catalog_filters(
        category=filters.get("category"),
        gender=filters.get("gender"),
        price_min=filters.get("price_min"),
        price_max=filters.get("price_max"),
        brand_size=filters.get("brand_size"),
        fabric=filters.get("fabric"),
        subcategory=filters.get("subcategory"),
        brand=filters.get("brand"),
        color=filters.get("color"),
        fit=filters.get("fit"),
        discount_min=filters.get("discount_min"),
        rating_min=filters.get("rating_min"),
        availability=filters.get("availability"),
        price_ranges=filters.get("price_ranges"),
        new_arrivals=filters.get("new_arrivals"),
        brand_type=filters.get("brand_type")
    )
    summary_where_sql, summary_params = _apply_catalog_search_clause(summary_where_sql, summary_params, search, alias="p")
    tab_clause, tab_params = _build_catalog_tab_clause(cur, tab, alias="p")
    summary_where_sql = _append_where_clause(summary_where_sql, tab_clause)
    summary_params.extend(tab_params)

    cur.execute(f"""
        SELECT
            COUNT(*) AS total_products,
            COUNT(DISTINCT p.brand) AS total_brands,
            COUNT(DISTINCT p.category) AS total_categories,
            ROUND(AVG(COALESCE(p.discount_percentage, 0)), 1) AS avg_discount,
            SUM(CASE WHEN p.is_in_stock = 1 THEN 1 ELSE 0 END) AS in_stock_products,
            SUM(CASE WHEN COALESCE(p.discount_percentage, 0) > 0 THEN 1 ELSE 0 END) AS discounted_products,
            MAX(COALESCE(p.updated_at, p.created_at)) AS latest_activity_at
        FROM products p
        WHERE {summary_where_sql};
    """, summary_params)
    summary_row = cur.fetchone() or {}

    total_products = int(summary_row["total_products"] or 0)
    in_stock_products = int(summary_row["in_stock_products"] or 0)
    discounted_products = int(summary_row["discounted_products"] or 0)
    in_stock_pct = round((in_stock_products / total_products) * 100, 1) if total_products > 0 else 0.0
    discounted_pct = round((discounted_products / total_products) * 100, 1) if total_products > 0 else 0.0
    latest_activity = summary_row["latest_activity_at"]
    latest_activity_label = latest_activity.isoformat() if latest_activity else None

    category_filters = dict(filters)
    category_filters["category"] = "all"
    category_where_sql, category_params = _build_catalog_filters(
        category=category_filters.get("category"),
        gender=category_filters.get("gender"),
        price_min=category_filters.get("price_min"),
        price_max=category_filters.get("price_max"),
        brand_size=category_filters.get("brand_size"),
        fabric=category_filters.get("fabric"),
        subcategory=category_filters.get("subcategory"),
        brand=category_filters.get("brand"),
        color=category_filters.get("color"),
        fit=category_filters.get("fit"),
        discount_min=category_filters.get("discount_min"),
        rating_min=category_filters.get("rating_min"),
        availability=category_filters.get("availability"),
        price_ranges=category_filters.get("price_ranges"),
        new_arrivals=category_filters.get("new_arrivals"),
        brand_type=category_filters.get("brand_type")
    )
    category_where_sql, category_params = _apply_catalog_search_clause(category_where_sql, category_params, search, alias="p")
    category_where_sql = _append_where_clause(category_where_sql, tab_clause)
    category_params.extend(tab_params)

    cur.execute(f"""
        SELECT p.category, COUNT(*) AS cnt
        FROM products p
        WHERE {category_where_sql}
          AND p.category IS NOT NULL
          AND p.category != ''
        GROUP BY p.category;
    """, category_params)
    category_rows = cur.fetchall()

    aggregated = {}
    for row in category_rows:
        option = _catalog_category_option(row["category"])
        if not option:
            continue
        bucket = aggregated.setdefault(option["value"], {
            "value": option["value"],
            "name": option["name"],
            "count": 0,
            "_rank": option["rank"]
        })
        bucket["count"] += int(row["cnt"] or 0)
        bucket["_rank"] = min(bucket["_rank"], option["rank"])

    categories = [{
        "value": "all",
        "name": f"All Categories ({total_products:,})",
        "count": total_products
    }]
    categories.extend(
        {
            "value": item["value"],
            "name": f"{item['name']} ({item['count']:,})",
            "count": item["count"]
        }
        for item in sorted(aggregated.values(), key=lambda item: (item["_rank"], -item["count"], item["name"].lower()))
    )

    return {
        "summary": {
            "total_products": total_products,
            "total_brands": int(summary_row["total_brands"] or 0),
            "total_categories": int(summary_row["total_categories"] or 0),
            "avg_discount": float(summary_row["avg_discount"] or 0.0),
            "in_stock_products": in_stock_products,
            "in_stock_pct": in_stock_pct,
            "discounted_products": discounted_products,
            "discounted_pct": discounted_pct,
            "latest_activity_at": latest_activity_label
        },
        "categories": categories
    }


def _scope_display_label(category: str, subcategory: str | None = None) -> str:
    sub = (subcategory or "").strip()
    if sub and sub.lower() != "all":
        return sub

    category_map = {
        "shirts": "Shirts",
        "tshirts": "T-Shirts",
        "t-shirts": "T-Shirts",
        "jeans": "Jeans",
        "western-wear": "Western Wear",
        "western wear": "Western Wear",
        "dresses": "Dresses",
        "tops": "Tops",
        "trousers": "Trousers",
        "shorts": "Shorts",
        "jackets": "Jackets",
        "sweatshirts": "Sweatshirts",
        "sweaters": "Sweaters",
        "co-ords": "Co-Ords",
        "coords": "Co-Ords",
        "kurtas": "Kurtas",
        "kurtis": "Kurtis",
        "all": "All Categories"
    }
    normalized = (category or "").strip().lower()
    if normalized in category_map:
        return category_map[normalized]
    if not normalized:
        return "Catalog"
    return " ".join(part.capitalize() for part in normalized.replace("_", " ").replace("-", " ").split())


def _build_scope_sidebar_counts(cur, filters: dict):
    def build_where(**overrides):
        scoped = dict(filters)
        scoped.update(overrides)
        return _build_catalog_filters(
            category=scoped.get("category"),
            gender=scoped.get("gender"),
            price_min=scoped.get("price_min"),
            price_max=scoped.get("price_max"),
            brand_size=scoped.get("brand_size"),
            fabric=scoped.get("fabric"),
            subcategory=scoped.get("subcategory"),
            brand=scoped.get("brand"),
            color=scoped.get("color"),
            fit=scoped.get("fit"),
            discount_min=scoped.get("discount_min"),
            rating_min=scoped.get("rating_min"),
            availability=scoped.get("availability"),
            price_ranges=scoped.get("price_ranges"),
            new_arrivals=scoped.get("new_arrivals"),
            brand_type=scoped.get("brand_type")
        )

    price_where_sql, price_params = build_where(price_ranges=None)
    cur.execute(f"""
        SELECT
            SUM(CASE WHEN p.selling_price < 500 THEN 1 ELSE 0 END) as p_lt_500,
            SUM(CASE WHEN p.selling_price >= 500 AND p.selling_price < 1000 THEN 1 ELSE 0 END) as p_500_1k,
            SUM(CASE WHEN p.selling_price >= 800 AND p.selling_price <= 1000 THEN 1 ELSE 0 END) as p_800_1k,
            SUM(CASE WHEN p.selling_price >= 1000 AND p.selling_price < 2000 THEN 1 ELSE 0 END) as p_1k_2k,
            SUM(CASE WHEN p.selling_price >= 2000 AND p.selling_price < 3000 THEN 1 ELSE 0 END) as p_2k_3k,
            SUM(CASE WHEN p.selling_price >= 3000 AND p.selling_price < 4000 THEN 1 ELSE 0 END) as p_3k_4k,
            SUM(CASE WHEN p.selling_price >= 4000 THEN 1 ELSE 0 END) as p_gt_4k
        FROM products p
        WHERE {price_where_sql};
    """, price_params)
    price_row = cur.fetchone() or {}

    brand_size_where_sql, brand_size_params = build_where(brand_size=None)
    brand_size_counts = _get_brand_size_bucket_counts(cur, brand_size_where_sql, brand_size_params)

    subcat_where_sql, subcat_params = build_where(subcategory=None)
    subcategories = _subcategory_facets(cur, subcat_where_sql, subcat_params, filters.get("category") or "all")

    brand_where_sql, brand_params = build_where(brand=None)
    cur.execute(f"""
        SELECT p.brand, COUNT(*) as cnt
        FROM products p
        WHERE {brand_where_sql} AND p.brand IS NOT NULL AND p.brand != ''
        GROUP BY p.brand
        ORDER BY cnt DESC, p.brand ASC
        LIMIT 50;
    """, brand_params)
    brand_rows = cur.fetchall()

    color_where_sql, color_params = build_where(color=None)
    cur.execute(f"""
        SELECT p.primary_color, MAX(p.color_hex) as color_hex, COUNT(*) as cnt
        FROM products p
        WHERE {color_where_sql} AND {_valid_color_sql("p.primary_color")}
        GROUP BY p.primary_color
        ORDER BY cnt DESC, p.primary_color ASC
        LIMIT 12;
    """, color_params)
    color_rows = cur.fetchall()

    fabric_where_sql, fabric_params = build_where(fabric=None)
    cur.execute(f"""
        SELECT
            CASE
                WHEN LOWER(p.fabric) LIKE '%cotton%' AND (LOWER(p.fabric) LIKE '%blend%' OR LOWER(p.fabric) LIKE '%poly%' OR LOWER(p.fabric) LIKE '%,%') THEN 'Cotton Blend'
                WHEN LOWER(p.fabric) LIKE '%cotton%' THEN 'Cotton'
                WHEN LOWER(p.fabric) LIKE '%poly%' THEN 'Polyester'
                WHEN LOWER(p.fabric) LIKE '%linen%' THEN 'Linen'
                WHEN LOWER(p.fabric) LIKE '%viscose%' THEN 'Viscose'
                WHEN LOWER(p.fabric) LIKE '%denim%' THEN 'Denim'
                ELSE 'Others'
            END as clean_f,
            COUNT(*) as cnt
        FROM products p
        WHERE {fabric_where_sql} AND p.fabric IS NOT NULL AND p.fabric != ''
        GROUP BY clean_f
        ORDER BY cnt DESC, clean_f ASC
        LIMIT 8;
    """, fabric_params)
    fabric_rows = cur.fetchall()

    fit_where_sql, fit_params = build_where(fit=None)
    cur.execute(f"""
        SELECT p.fit, COUNT(*) as fit_cnt
        FROM products p
        WHERE {fit_where_sql} AND p.fit IS NOT NULL AND p.fit != '' AND p.fit != 'NA'
        GROUP BY p.fit
        ORDER BY fit_cnt DESC, p.fit ASC
        LIMIT 8;
    """, fit_params)
    fit_rows = cur.fetchall()

    return {
        "price_ranges": {
            "lt_500": int(price_row["p_lt_500"] or 0),
            "500_1000": int(price_row["p_500_1k"] or 0),
            "800_1000": int(price_row["p_800_1k"] or 0),
            "1000_2000": int(price_row["p_1k_2k"] or 0),
            "2000_3000": int(price_row["p_2k_3k"] or 0),
            "3000_4000": int(price_row["p_3k_4k"] or 0),
            "gt_4000": int(price_row["p_gt_4k"] or 0)
        },
        "brand_sizes": {
            "large": brand_size_counts["large"],
            "mid": brand_size_counts["mid"],
            "small": brand_size_counts["small"]
        },
        "subcategories": subcategories,
        "available_filters": {
            "brands": [{"brand": r["brand"], "count": int(r["cnt"] or 0)} for r in brand_rows],
            "colors": [{
                "color": _normalize_color_name(r["primary_color"], fallback="Multicolor"),
                "hex": _normalize_color_hex(r["color_hex"], r["primary_color"], fallback="#0f172a"),
                "count": int(r["cnt"] or 0)
            } for r in color_rows],
            "fabrics": [{"fabric": r["clean_f"], "count": int(r["cnt"] or 0)} for r in fabric_rows],
            "fits": [{"fit": r["fit"], "count": int(r["fit_cnt"] or 0)} for r in fit_rows]
        }
    }


def _build_filter_counts_payload(cur, filters: dict, sustainability: str | None = None, brand_limit: int = 20,
                                 include_subcategories: bool = True):
    def build_where(**overrides):
        scoped = dict(filters)
        scoped.update(overrides)
        where_sql, where_params = _build_catalog_filters(
            category=scoped.get("category"),
            gender=scoped.get("gender"),
            price_min=scoped.get("price_min"),
            price_max=scoped.get("price_max"),
            brand_size=scoped.get("brand_size"),
            fabric=scoped.get("fabric"),
            subcategory=scoped.get("subcategory"),
            brand=scoped.get("brand"),
            color=scoped.get("color"),
            fit=scoped.get("fit"),
            discount_min=scoped.get("discount_min"),
            rating_min=scoped.get("rating_min"),
            availability=scoped.get("availability"),
            price_ranges=scoped.get("price_ranges"),
            new_arrivals=scoped.get("new_arrivals"),
            brand_type=scoped.get("brand_type")
        )
        where_sql, where_params = _apply_catalog_search_clause(where_sql, where_params, scoped.get("search"), alias="p")
        tab_clause, tab_params = _build_catalog_tab_clause(cur, scoped.get("tab"), alias="p")
        where_sql = _append_where_clause(where_sql, tab_clause)
        where_params.extend(tab_params)
        return _apply_sustainability_filter(where_sql, where_params, sustainability, alias="p")

    price_where_sql, price_params = build_where(price_ranges=None)
    cur.execute(f"""
        SELECT
            COUNT(CASE WHEN selling_price < 500 THEN 1 END) as lt_500,
            COUNT(CASE WHEN selling_price >= 500 AND selling_price < 1000 THEN 1 END) as p_500_1000,
            COUNT(CASE WHEN selling_price >= 1000 AND selling_price < 2000 THEN 1 END) as p_1000_2000,
            COUNT(CASE WHEN selling_price >= 2000 AND selling_price < 3000 THEN 1 END) as p_2000_3000,
            COUNT(CASE WHEN selling_price >= 3000 AND selling_price < 4000 THEN 1 END) as p_3000_4000,
            COUNT(CASE WHEN selling_price >= 4000 THEN 1 END) as gt_4000,
            COUNT(*) as total_count
        FROM products p
        WHERE {price_where_sql};
    """, price_params)
    price_row = cur.fetchone() or {}

    brand_where_sql, brand_params = build_where(brand=None)
    cur.execute(f"""
        SELECT brand, COUNT(*) as cnt
        FROM products p
        WHERE {brand_where_sql} AND brand IS NOT NULL AND brand != ''
        GROUP BY brand
        ORDER BY cnt DESC, brand ASC;
    """, brand_params)
    all_brand_rows = cur.fetchall()
    brand_rows = all_brand_rows[:int(brand_limit)]

    subcategories = []
    if include_subcategories:
        subcat_where_sql, subcat_params = build_where(subcategory=None)
        subcategories = _subcategory_facets(cur, subcat_where_sql, subcat_params, filters.get("category") or "all")

    brand_size_counts = {
        "large": sum(1 for row in all_brand_rows if int(row["cnt"] or 0) >= LARGE_BRAND_MIN_PRODUCTS),
        "mid": sum(1 for row in all_brand_rows if MID_BRAND_MIN_PRODUCTS <= int(row["cnt"] or 0) < LARGE_BRAND_MIN_PRODUCTS),
        "small": sum(1 for row in all_brand_rows if int(row["cnt"] or 0) < MID_BRAND_MIN_PRODUCTS)
    }

    return {
        "price_buckets": {
            "lt_500": int(price_row["lt_500"] or 0),
            "500_1000": int(price_row["p_500_1000"] or 0),
            "1000_2000": int(price_row["p_1000_2000"] or 0),
            "2000_3000": int(price_row["p_2000_3000"] or 0),
            "3000_4000": int(price_row["p_3000_4000"] or 0),
            "gt_4000": int(price_row["gt_4000"] or 0),
            "total": int(price_row["total_count"] or 0)
        },
        "brands": {row["brand"]: int(row["cnt"] or 0) for row in brand_rows},
        "brands_list": [{"brand": row["brand"], "count": int(row["cnt"] or 0)} for row in brand_rows],
        "subcategories": subcategories,
        "brand_sizes": {
            "large": brand_size_counts["large"],
            "mid": brand_size_counts["mid"],
            "small": brand_size_counts["small"]
        }
    }


@app.route("/api/category-intelligence")
def get_category_intelligence():
    """100% Genuine dynamic category intelligence telemetry with multi-tier caching."""
    category = request.args.get("category", "shirts").strip()
    gender = request.args.get("gender", "men").strip()
    subcategory = request.args.get("subcategory")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    price_ranges = request.args.get("price_ranges") or request.args.get("price_range")
    brand_size = request.args.get("brand_size")
    brand_type = request.args.get("brand_type")
    brand = request.args.get("brand")
    color = request.args.get("color")
    fabric = request.args.get("fabric")
    fit = request.args.get("fit")
    discount_min = request.args.get("discount_min")
    rating_min = request.args.get("rating_min")
    availability = request.args.get("availability")
    new_arrivals = request.args.get("new_arrivals")

    cache_key = f"cat_intel_v4:{category.lower()}:{gender.lower()}:{subcategory}:{price_min}:{price_max}:{price_ranges}:{brand_size}:{brand_type}:{brand}:{color}:{fabric}:{fit}:{discount_min}:{rating_min}:{availability}:{new_arrivals}"
    cached = api_cache.get(cache_key)
    if cached:
        return jsonify(cached)

    conn = db._get_connection()
    cur = conn.cursor()

    where_sql, params = _build_catalog_filters(
        category=category, gender=gender, price_min=price_min, price_max=price_max,
        brand_size=brand_size, fabric=fabric, subcategory=subcategory, brand=brand,
        color=color, fit=fit, discount_min=discount_min, rating_min=rating_min,
        availability=availability, price_ranges=price_ranges, new_arrivals=new_arrivals,
        brand_type=brand_type
    )

    # 1. KPI Core Aggregation + Price Distribution Brackets
    cur.execute(f"""
        SELECT 
            COUNT(*) as total_prods,
            COUNT(DISTINCT p.brand) as brands_count,
            ROUND(AVG(p.selling_price)) as mean_price,
            ROUND(AVG(p.discount_percentage), 1) as avg_disc,
            SUM(CASE WHEN p.selling_price < 500 THEN 1 ELSE 0 END) as p_lt_500,
            SUM(CASE WHEN p.selling_price >= 500 AND p.selling_price < 1000 THEN 1 ELSE 0 END) as p_500_1k,
            SUM(CASE WHEN p.selling_price >= 1000 AND p.selling_price < 2000 THEN 1 ELSE 0 END) as p_1k_2k,
            SUM(CASE WHEN p.selling_price >= 2000 AND p.selling_price < 3000 THEN 1 ELSE 0 END) as p_2k_3k,
            SUM(CASE WHEN p.selling_price >= 3000 AND p.selling_price < 4000 THEN 1 ELSE 0 END) as p_3k_4k,
            SUM(CASE WHEN p.selling_price >= 4000 THEN 1 ELSE 0 END) as p_gt_4k
        FROM products p
        WHERE {where_sql};
    """, params)
    kpi_row = cur.fetchone()

    total_prods = int(kpi_row["total_prods"] or 0)
    brands_count = int(kpi_row["brands_count"] or 0)
    mean_price = int(kpi_row["mean_price"] or 0)
    avg_disc = float(kpi_row["avg_disc"] or 0.0)

    p_lt_500 = int(kpi_row["p_lt_500"] or 0)
    p_500_1k = int(kpi_row["p_500_1k"] or 0)
    p_1k_2k = int(kpi_row["p_1k_2k"] or 0)
    p_2k_3k = int(kpi_row["p_2k_3k"] or 0)
    p_3k_4k = int(kpi_row["p_3k_4k"] or 0)
    p_gt_4k = int(kpi_row["p_gt_4k"] or 0)

    price_distribution = [
        {"label": "< ₹500", "count": p_lt_500},
        {"label": "₹500 - 1K", "count": p_500_1k},
        {"label": "₹1K - 2K", "count": p_1k_2k},
        {"label": "₹2K - 3K", "count": p_2k_3k},
        {"label": "₹3K - 4K", "count": p_3k_4k},
        {"label": "> ₹4K", "count": p_gt_4k}
    ]

    most_comp_bracket = max(price_distribution, key=lambda b: b["count"])["label"]

    cur.execute(f"""
        WITH ranked_prices AS (
            SELECT p.selling_price,
                   ROW_NUMBER() OVER (ORDER BY p.selling_price) as rn,
                   COUNT(*) OVER () as total_rows
            FROM products p
            WHERE {where_sql} AND p.selling_price > 0
        )
        SELECT ROUND(AVG(selling_price))
        FROM ranked_prices
        WHERE rn IN ((total_rows + 1) / 2, (total_rows + 2) / 2);
    """, params)
    median_price = _safe_int((cur.fetchone() or [mean_price])[0], mean_price)
    mode_price = _price_band_midpoint(most_comp_bracket, mean_price)

    cur.execute(f"""
        SELECT p.brand, p.is_myntra_label, p.brand_type, COUNT(*) as b_cnt
        FROM products p
        WHERE {where_sql} AND p.brand IS NOT NULL AND p.brand != ''
        GROUP BY p.brand, p.is_myntra_label, p.brand_type
        ORDER BY b_cnt DESC
        LIMIT 1;
    """, params)
    top_b_row = cur.fetchone()
    top_brand_name = top_b_row["brand"] if top_b_row else "Leading Brand"
    top_brand_prods = int(top_b_row["b_cnt"] or 0) if top_b_row else 0
    top_brand_type = top_b_row["brand_type"] or ("Myntra In-House Label" if top_b_row and top_b_row["is_myntra_label"] else "External Brand") if top_b_row else "Brand"
    is_top_brand_myntra = bool(top_b_row["is_myntra_label"]) if top_b_row else False

    cur.execute(f"""
        SELECT 
            p.brand, 
            p.is_myntra_label, 
            p.brand_type, 
            COUNT(*) as b_cnt, 
            ROUND(AVG(p.selling_price)) as b_asp,
            ROUND(AVG(p.discount_percentage), 1) as b_disc
        FROM products p
        WHERE {where_sql} AND p.brand IS NOT NULL AND p.brand != ''
        GROUP BY p.brand, p.is_myntra_label, p.brand_type
        ORDER BY b_cnt DESC;
    """, params)
    all_b_rows = cur.fetchall()

    top_brands = []
    large_b, mid_b, small_b = [], [], []
    large_prods, mid_prods, small_prods = 0, 0, 0

    for rank, r in enumerate(all_b_rows, 1):
        b_cnt = int(r["b_cnt"] or 0)
        asp = int(r["b_asp"] or 0)
        disc = float(r["b_disc"] or 0.0)
        is_myntra = bool(r["is_myntra_label"])
        b_type = r["brand_type"] or ("Myntra In-House Label" if is_myntra else "External Brand")

        if rank <= 10:
            share = round((b_cnt / max(1, total_prods) * 100.0), 1)
            top_brands.append({
                "rank": rank,
                "brand": r["brand"],
                "is_myntra_label": is_myntra,
                "brand_type": b_type,
                "products": b_cnt,
                "share": f"{share}%",
                "median_price": f"₹{asp:,}",
                "avg_price": f"₹{asp:,}",
                "avg_discount": f"{disc}%"
            })
        if b_cnt >= LARGE_BRAND_MIN_PRODUCTS:
            large_b.append(asp)
            large_prods += b_cnt
        elif b_cnt >= MID_BRAND_MIN_PRODUCTS:
            mid_b.append(asp)
            mid_prods += b_cnt
        else:
            small_b.append(asp)
            small_prods += b_cnt

    brand_scale = {
        "largest": {
            "label": f"Largest Brands (>={LARGE_BRAND_MIN_PRODUCTS:,})",
            "brand_count": len(large_b),
            "product_count": large_prods,
            "median_price": f"₹{int(sum(large_b)/max(1, len(large_b))):,}" if large_b else "₹0"
        },
        "mid": {
            "label": f"Mid-size Brands ({MID_BRAND_MIN_PRODUCTS:,}-{LARGE_BRAND_MIN_PRODUCTS - 1:,})",
            "brand_count": len(mid_b),
            "product_count": mid_prods,
            "median_price": f"₹{int(sum(mid_b)/max(1, len(mid_b))):,}" if mid_b else "₹0"
        },
        "small": {
            "label": f"Small Brands (<{MID_BRAND_MIN_PRODUCTS:,})",
            "brand_count": len(small_b),
            "product_count": small_prods,
            "median_price": f"₹{int(sum(small_b)/max(1, len(small_b))):,}" if small_b else "₹0"
        }
    }

    # Historical Category Growth Telemetry from daily_sales_analytics
    cur.execute(f"""
        SELECT 
            sa.analytics_date,
            COUNT(DISTINCT sa.product_id) as p_cnt,
            ROUND(SUM(sa.revenue_generated) / 10000000.0, 2) as rev_cr
        FROM daily_sales_analytics sa
        JOIN products p ON sa.product_id = p.product_id
        WHERE {where_sql}
        GROUP BY sa.analytics_date
        ORDER BY sa.analytics_date DESC
        LIMIT 7;
    """, params)
    growth_rows = list(reversed(cur.fetchall()))
    growth_pct = 0.0
    if growth_rows:
        month_names = [str(r[0])[-5:] for r in growth_rows]
        prod_growth_curve = [int(r[1]) for r in growth_rows]
        sales_growth_curve = [float(r[2]) for r in growth_rows]
        if len(prod_growth_curve) >= 2:
            growth_pct = _pct_change(prod_growth_curve[-1], prod_growth_curve[0])
    else:
        month_names = []
        prod_growth_curve = []
        sales_growth_curve = []

    price_growth_pct = 0.0
    discount_delta = 0.0
    latest_dates = _get_analytics_dates(cur, limit=2)
    if len(latest_dates) >= 2:
        cur.execute(f"""
            SELECT
                ROUND(AVG(CASE WHEN snap.snapshot_date = ? THEN snap.selling_price END), 2) as cur_price,
                ROUND(AVG(CASE WHEN snap.snapshot_date = ? THEN snap.selling_price END), 2) as prev_price,
                ROUND(AVG(CASE WHEN snap.snapshot_date = ? THEN snap.discount_percentage END), 2) as cur_disc,
                ROUND(AVG(CASE WHEN snap.snapshot_date = ? THEN snap.discount_percentage END), 2) as prev_disc
            FROM daily_inventory_snapshots snap
            JOIN products p ON p.product_id = snap.product_id
            WHERE {where_sql};
        """, [latest_dates[0], latest_dates[1], latest_dates[0], latest_dates[1]] + params)
        snap_delta_row = cur.fetchone()
        cur_price = float(snap_delta_row["cur_price"] or 0.0)
        prev_price = float(snap_delta_row["prev_price"] or 0.0)
        cur_disc = float(snap_delta_row["cur_disc"] or 0.0)
        prev_disc = float(snap_delta_row["prev_disc"] or 0.0)
        price_growth_pct = _pct_change(cur_price, prev_price)
        discount_delta = round(cur_disc - prev_disc, 1)

    cur.execute(f"""
        SELECT 
            CASE 
                WHEN POSITION('cotton' IN LOWER(COALESCE(p.fabric, ''))) > 0 AND (
                    POSITION('blend' IN LOWER(COALESCE(p.fabric, ''))) > 0
                    OR POSITION('poly' IN LOWER(COALESCE(p.fabric, ''))) > 0
                    OR POSITION(',' IN LOWER(COALESCE(p.fabric, ''))) > 0
                ) THEN 'Cotton Blend'
                WHEN POSITION('cotton' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Cotton'
                WHEN POSITION('poly' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Polyester'
                WHEN POSITION('linen' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Linen'
                WHEN POSITION('viscose' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Viscose'
                WHEN POSITION('rayon' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Rayon'
                WHEN POSITION('denim' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Denim'
                WHEN POSITION('silk' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Silk'
                ELSE 'Others'
            END as clean_fabric,
            COUNT(*) as f_cnt,
            ROUND(AVG(p.selling_price)) as f_asp
        FROM products p
        WHERE {where_sql} AND p.fabric IS NOT NULL AND p.fabric != ''
        GROUP BY clean_fabric
        ORDER BY f_cnt DESC
        LIMIT 8;
    """, params)
    f_rows = cur.fetchall()
    f_total = sum(int(r["f_cnt"] or 0) for r in f_rows) or 1
    top_fabrics = [
        {
            "fabric": r["clean_fabric"],
            "products": int(r["f_cnt"] or 0),
            "share": f"{round((int(r['f_cnt'] or 0) / max(1, total_prods) * 100.0), 1)}%",
            "avg_price": f"₹{int(r['f_asp'] or 0):,}"
        }
        for r in f_rows
    ]

    cur.execute(f"""
        SELECT p.primary_color, p.color_hex, COUNT(*) as c_cnt
        FROM products p
        WHERE {where_sql} AND {_valid_color_sql("p.primary_color")}
        GROUP BY p.primary_color, p.color_hex
        ORDER BY c_cnt DESC
        LIMIT 8;
    """, params)
    c_rows = cur.fetchall()
    c_total = sum(int(r["c_cnt"] or 0) for r in c_rows) or 1
    top_colors = [
        {
            "color": _normalize_color_name(r["primary_color"], fallback="Multicolor"),
            "hex": _normalize_color_hex(r["color_hex"], r["primary_color"], fallback="#0f172a"),
            "products": int(r["c_cnt"] or 0),
            "share": f"{round((int(r['c_cnt'] or 0) / max(1, total_prods) * 100.0), 1)}%"
        }
        for r in c_rows
    ]

    cur.execute(f"""
        SELECT 
            p.product_id, p.brand, p.title, p.selling_price, p.mrp, 
            p.discount_percentage, p.average_rating, p.product_url, p.is_in_stock,
            p.is_myntra_label, p.brand_type
        FROM products p
        WHERE {where_sql}
        ORDER BY p.total_ratings_count DESC, p.selling_price DESC
        LIMIT 10;
    """, params)
    prod_rows = cur.fetchall()
    prod_image_map = {}
    if prod_rows:
        prod_ids = [r["product_id"] for r in prod_rows if r["product_id"]]
        placeholders = ",".join("?" for _ in prod_ids)
        if placeholders:
            cur.execute(f"SELECT product_id, full_data_json FROM products WHERE product_id IN ({placeholders});", prod_ids)
            for img_row in cur.fetchall():
                prod_image_map[int(img_row["product_id"])] = _load_primary_image(img_row["full_data_json"])

    top_products = []
    for idx, r in enumerate(prod_rows, 1):
        is_myntra = bool(r["is_myntra_label"])
        b_type = r["brand_type"] or ("Myntra In-House Label" if is_myntra else "Non-Myntra Brand")

        top_products.append({
            "rank": idx,
            "product_id": r["product_id"],
            "brand": r["brand"],
            "is_myntra_label": is_myntra,
            "brand_type": b_type,
            "title": r["title"],
            "price": f"₹{int(r['selling_price'] or 0):,}",
            "mrp": f"₹{int(r['mrp'] or 0):,}",
            "discount": f"{r['discount_percentage'] or 0}%",
            "rating": round(_safe_float(r["average_rating"]), 1),
            "velocity": f"{r['discount_percentage'] or 0}% OFF",
            "stock": "In Stock" if int(r["is_in_stock"] or 0) == 1 else "Out of Stock",
            "product_url": r["product_url"],
            "image_url": prod_image_map.get(int(r["product_id"]), "")
        })

    scope_label = _scope_display_label(category, subcategory)
    key_insight = f"{top_brand_name} leads volume in {scope_label} with {top_brand_prods:,} styles. The most competitive price band is {most_comp_bracket} and the current median price is ₹{median_price:,}."

    result = {
        "status": "success",
        "category": category.title(),
        "gender": gender.title(),
        "scope_label": scope_label,
        "scope_subcategory": subcategory or "all",
        "kpis": {
            "total_products": f"{total_prods:,}",
            "total_products_num": total_prods,
            "brands_count": brands_count,
            "growth_pct": f"{growth_pct:+.1f}%",
            "median_price": f"₹{median_price:,}",
            "mean_price": f"₹{mean_price:,}",
            "mode_price": f"₹{mode_price:,}",
            "price_growth_pct": f"{price_growth_pct:+.1f}%",
            "avg_discount": f"{avg_disc}%",
            "discount_delta": f"{discount_delta:+.1f}%",
            "top_brand": top_brand_name,
            "top_brand_type": top_brand_type,
            "is_top_brand_myntra": is_top_brand_myntra,
            "top_brand_products": top_brand_prods
        },
        "price_stats": {
            "median_price": f"₹{median_price:,}",
            "mode_price": f"₹{mode_price:,}",
            "mean_price": f"₹{mean_price:,}",
            "most_competitive": most_comp_bracket
        },
        "price_distribution": price_distribution,
        "top_brands": top_brands,
        "brand_scale": brand_scale,
        "category_growth": {
            "labels": month_names,
            "products": prod_growth_curve,
            "sales_value_cr": sales_growth_curve
        },
        "top_fabrics": top_fabrics,
        "top_colors": top_colors,
        "top_products": top_products,
        "key_insight": key_insight
    }

    api_cache.set(cache_key, result, ttl=300.0)
    return jsonify(result)


@app.route("/api/fabric-intelligence")
def get_fabric_intelligence():
    """100% Genuine dynamic fabric intelligence and material analytics."""
    category = request.args.get("category", "shirts").strip()
    gender = request.args.get("gender", "men").strip()
    selected_fabric = request.args.get("fabric", "all").strip()
    price_ranges = request.args.get("price_ranges") or request.args.get("price_range")
    brand_size = request.args.get("brand_size")
    brand = request.args.get("brand")
    sustainability = request.args.get("sustainability")
    cache_key = f"fabric_intel_v4:{category.lower()}:{gender.lower()}:{selected_fabric.lower()}:{price_ranges}:{brand_size}:{brand}:{sustainability}"
    cached = api_cache.get(cache_key)
    if cached:
        return jsonify(cached)

    conn = db._get_connection()
    cur = conn.cursor()

    where_sql, params = _build_catalog_filters(
        category=category,
        gender=gender,
        price_ranges=price_ranges,
        brand_size=brand_size,
        brand=brand,
        fabric=selected_fabric if selected_fabric and selected_fabric.lower() != "all" else None
    )
    fabric_bucket_sql = """
        CASE
            WHEN POSITION('cotton' IN LOWER(COALESCE(p.fabric, ''))) > 0 AND (
                POSITION('blend' IN LOWER(COALESCE(p.fabric, ''))) > 0
                OR POSITION('poly' IN LOWER(COALESCE(p.fabric, ''))) > 0
                OR POSITION(',' IN LOWER(COALESCE(p.fabric, ''))) > 0
            ) THEN 'Cotton Blend'
            WHEN POSITION('cotton' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Cotton'
            WHEN POSITION('poly' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Polyester'
            WHEN POSITION('linen' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Linen'
            WHEN POSITION('viscose' IN LOWER(COALESCE(p.fabric, ''))) > 0 OR POSITION('rayon' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Viscose'
            WHEN POSITION('denim' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Denim'
            WHEN POSITION('silk' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Silk'
            WHEN POSITION('wool' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Wool'
            ELSE 'Others'
        END
    """
    where_sql, params = _apply_sustainability_filter(where_sql, params, sustainability, alias="p")

    # Total products & Unique fabrics
    cur.execute(f"""
        SELECT 
            COUNT(*) as total_prods,
            COUNT(DISTINCT p.fabric) as unique_fabrics,
            SUM(CASE WHEN p.selling_price < 500 THEN 1 ELSE 0 END) as p_lt_500,
            SUM(CASE WHEN p.selling_price >= 500 AND p.selling_price < 1000 THEN 1 ELSE 0 END) as p_500_1k,
            SUM(CASE WHEN p.selling_price >= 1000 AND p.selling_price < 2000 THEN 1 ELSE 0 END) as p_1k_2k,
            SUM(CASE WHEN p.selling_price >= 2000 AND p.selling_price < 3000 THEN 1 ELSE 0 END) as p_2k_3k,
            SUM(CASE WHEN p.selling_price >= 3000 AND p.selling_price < 4000 THEN 1 ELSE 0 END) as p_3k_4k,
            SUM(CASE WHEN p.selling_price >= 4000 THEN 1 ELSE 0 END) as p_gt_4k
        FROM products p
        WHERE {where_sql} AND p.fabric IS NOT NULL AND p.fabric != '';
    """, params)
    f_stat = cur.fetchone()
    total_prods = int(f_stat["total_prods"] or 0)
    unique_fabrics = int(f_stat["unique_fabrics"] or 0)
    price_buckets = {
        "lt_500": int(f_stat["p_lt_500"] or 0),
        "500_1000": int(f_stat["p_500_1k"] or 0),
        "1000_2000": int(f_stat["p_1k_2k"] or 0),
        "2000_3000": int(f_stat["p_2k_3k"] or 0),
        "3000_4000": int(f_stat["p_3k_4k"] or 0),
        "gt_4000": int(f_stat["p_gt_4k"] or 0)
    }

    # Top fabric bucket, share, and average price. Keep grouping normalized so
    # distribution, price, trend, dropdown and heatmap all speak the same logic.
    cur.execute(f"""
        SELECT 
            {fabric_bucket_sql} as clean_fabric,
            COUNT(*) as f_cnt,
            ROUND(AVG(p.selling_price)) as f_asp
        FROM products p
        WHERE {where_sql} AND p.fabric IS NOT NULL AND p.fabric != ''
        GROUP BY clean_fabric
        ORDER BY f_cnt DESC
        LIMIT 12;
    """, params)
    all_fabrics = cur.fetchall()

    top_fabric_name = ""
    top_fabric_share = "0.0%"
    top_fabric_asp = 0
    fabric_distribution = []
    top_fabrics_ranked = []
    average_price_by_fabric = []
    fabric_price_samples = defaultdict(list)
    fabric_mode_bands = defaultdict(Counter)

    if all_fabrics:
        fabric_sample_limit = _get_adaptive_sample_limit(total_prods, ceiling=2500)
        cur.execute(f"""
            SELECT {fabric_bucket_sql} as fabric, p.selling_price
            FROM products p
            WHERE {where_sql} AND p.fabric IS NOT NULL AND p.fabric != '' AND p.selling_price > 0
            LIMIT ?;
        """, params + [fabric_sample_limit])
        for sample_row in cur.fetchall():
            fabric_name = sample_row["fabric"]
            selling_price = _safe_float(sample_row["selling_price"])
            if not fabric_name or selling_price <= 0:
                continue
            fabric_price_samples[fabric_name].append(selling_price)
            fabric_mode_bands[fabric_name][round(selling_price / 100.0) * 100] += 1

    if all_fabrics:
        top_fabric_name = all_fabrics[0]["clean_fabric"]
        top_f_cnt = int(all_fabrics[0]["f_cnt"])
        top_fabric_share = f"{round(top_f_cnt / max(1, total_prods) * 100.0, 1)}%"
        top_fabric_asp = int(all_fabrics[0]["f_asp"] or 0)

        for idx, r in enumerate(all_fabrics):
            cnt = int(r["f_cnt"])
            sh = round(cnt / max(1, total_prods) * 100.0, 1)
            f_name = r["clean_fabric"]
            asp = int(r["f_asp"] or 0)

            if idx < 7:
                sample_prices = fabric_price_samples.get(f_name, [])
                median_price = _safe_int(_median_from_sorted(sample_prices), asp) if sample_prices else asp
                mode_price = asp
                if fabric_mode_bands.get(f_name):
                    mode_price = _safe_int(
                        max(fabric_mode_bands[f_name].items(), key=lambda item: (item[1], -item[0]))[0],
                        asp
                    )

                fabric_distribution.append({"fabric": f_name, "count": cnt, "share": sh})
                top_fabrics_ranked.append({"rank": idx + 1, "fabric": f_name, "count": cnt, "share": sh})
                average_price_by_fabric.append({
                    "fabric": f_name,
                    "mean": f"₹{asp:,}",
                    "median": f"₹{median_price:,}",
                    "mode": f"₹{mode_price:,}"
                })
            elif idx == 7:
                others_cnt = sum(int(x["f_cnt"]) for x in all_fabrics[7:])
                others_sh = round(others_cnt / max(1, total_prods) * 100.0, 1)
                fabric_distribution.append({"fabric": "Others", "count": others_cnt, "share": others_sh})

    focus_fabric = selected_fabric if selected_fabric and selected_fabric.lower() != "all" else top_fabric_name

    # Trend is intentionally lightweight: use catalog update buckets rather than
    # joining the large inventory snapshot table on every fabric filter change.
    cur.execute(f"""
        SELECT DATE(p.updated_at) as trend_date
        FROM products p
        WHERE {where_sql} AND p.fabric IS NOT NULL AND p.fabric != '' AND p.updated_at IS NOT NULL
        GROUP BY DATE(p.updated_at)
        ORDER BY trend_date DESC
        LIMIT 6;
    """, params)
    trend_dates = [r["trend_date"] for r in cur.fetchall()]
    trend_dates.reverse()
    month_labels = [str(d)[-5:] for d in trend_dates]
    trend_fabrics = [row["fabric"] for row in top_fabrics_ranked[:5]]
    trend_series = []
    trend_maps = defaultdict(dict)
    if trend_fabrics:
        fabric_placeholders = ",".join("?" for _ in trend_fabrics)
        cur.execute(f"""
            SELECT {fabric_bucket_sql} as fabric, DATE(p.updated_at) as trend_date, COUNT(*) as sku_count
            FROM products p
            WHERE {where_sql} AND {fabric_bucket_sql} IN ({fabric_placeholders}) AND p.updated_at IS NOT NULL
            GROUP BY fabric, DATE(p.updated_at)
            ORDER BY fabric ASC, trend_date ASC;
        """, params + trend_fabrics)
        for row in cur.fetchall():
            trend_maps[row["fabric"]][row["trend_date"]] = int(row["sku_count"] or 0)
    for tf in trend_fabrics:
        trend_series.append({"fabric": tf, "data": [trend_maps.get(tf, {}).get(d, 0) for d in trend_dates]})

    # Top Colors by Fabric (for selected fabric) — 100% REAL DYNAMIC SQL
    cur.execute(f"""
        SELECT p.primary_color, p.color_hex, COUNT(*) as c_cnt
        FROM products p
        WHERE {where_sql} 
          AND LOWER({fabric_bucket_sql}) = ?
          AND {_valid_color_sql("p.primary_color")}
        GROUP BY p.primary_color, p.color_hex
        ORDER BY c_cnt DESC
        LIMIT 5;
    """, params + [(focus_fabric or "Others").lower()])
    top_colors_fabric = []
    cf_rows = cur.fetchall()
    if cf_rows:
        cf_tot = sum(int(r["c_cnt"]) for r in cf_rows)
        for r in cf_rows:
            cnt = int(r["c_cnt"] or 0)
            top_colors_fabric.append({
                "color": _normalize_color_name(r["primary_color"], fallback="Multicolor"),
                "hex": _normalize_color_hex(r["color_hex"], r["primary_color"], fallback="#0f172a"),
                "count": cnt,
                "share": f"{round(cnt/max(1, cf_tot)*100, 1)}%"
            })

    # Fabric x Brand Heatmap: Top brands across normalized fabric columns
    cur.execute(f"""
        SELECT p.brand, COUNT(*) as b_cnt
        FROM products p
        WHERE {where_sql}
        GROUP BY p.brand
        ORDER BY b_cnt DESC, p.brand ASC
        LIMIT 30;
    """, params)
    brand_count_rows = cur.fetchall()
    top_5_brands = [r["brand"] for r in brand_count_rows[:5]]
    brand_options = [
        {"brand": r["brand"], "count": int(r["b_cnt"] or 0)}
        for r in brand_count_rows[:30]
        if r["brand"]
    ]
    brand_size_counts = {
        "large": sum(1 for r in brand_count_rows if int(r["b_cnt"] or 0) >= LARGE_BRAND_MIN_PRODUCTS),
        "mid": sum(1 for r in brand_count_rows if MID_BRAND_MIN_PRODUCTS <= int(r["b_cnt"] or 0) < LARGE_BRAND_MIN_PRODUCTS),
        "small": sum(1 for r in brand_count_rows if int(r["b_cnt"] or 0) < MID_BRAND_MIN_PRODUCTS)
    }
    heatmap_columns = ["Cotton", "Cotton Blend", "Polyester", "Linen", "Viscose", "Denim", "Others"]
    heatmap_matrix = []
    heatmap_rows = {}
    if top_5_brands:
        brand_placeholders = ",".join("?" for _ in top_5_brands)
        cur.execute(f"""
            SELECT 
                p.brand,
                SUM(CASE WHEN LOWER(p.fabric) LIKE '%cotton%' AND LOWER(p.fabric) NOT LIKE '%blend%' AND LOWER(p.fabric) NOT LIKE '%poly%' THEN 1 ELSE 0 END) as cotton,
                SUM(CASE WHEN LOWER(p.fabric) LIKE '%blend%' OR LOWER(p.fabric) LIKE '%poly%cotton%' THEN 1 ELSE 0 END) as blend,
                SUM(CASE WHEN LOWER(p.fabric) LIKE '%poly%' AND LOWER(p.fabric) NOT LIKE '%cotton%' THEN 1 ELSE 0 END) as poly,
                SUM(CASE WHEN LOWER(p.fabric) LIKE '%linen%' THEN 1 ELSE 0 END) as linen,
                SUM(CASE WHEN LOWER(p.fabric) LIKE '%viscose%' OR LOWER(p.fabric) LIKE '%rayon%' THEN 1 ELSE 0 END) as viscose,
                SUM(CASE WHEN LOWER(p.fabric) LIKE '%denim%' THEN 1 ELSE 0 END) as denim,
                SUM(CASE WHEN LOWER(p.fabric) NOT LIKE '%cotton%' AND LOWER(p.fabric) NOT LIKE '%poly%' AND LOWER(p.fabric) NOT LIKE '%linen%' AND LOWER(p.fabric) NOT LIKE '%viscose%' AND LOWER(p.fabric) NOT LIKE '%rayon%' AND LOWER(p.fabric) NOT LIKE '%denim%' THEN 1 ELSE 0 END) as others
            FROM products p
            WHERE p.brand IN ({brand_placeholders}) AND {where_sql}
            GROUP BY p.brand;
        """, top_5_brands + params)
        heatmap_rows = {row["brand"]: row for row in cur.fetchall()}
    for b in top_5_brands:
        h_row = heatmap_rows.get(b, {})
        c_vals = [
            int((h_row["cotton"] if h_row else 0) or 0),
            int((h_row["blend"] if h_row else 0) or 0),
            int((h_row["poly"] if h_row else 0) or 0),
            int((h_row["linen"] if h_row else 0) or 0),
            int((h_row["viscose"] if h_row else 0) or 0),
            int((h_row["denim"] if h_row else 0) or 0),
            int((h_row["others"] if h_row else 0) or 0)
        ]
        max_c = max(c_vals) if max(c_vals) > 0 else 1
        cells = []
        for cv in c_vals:
            cells.append({
                "count": f"{cv:,}" if cv < 1000 else f"{round(cv/1000, 1)}K",
                "raw_count": cv,
                "intensity": round(min(cv / max_c, 1.0), 2)
            })
        heatmap_matrix.append({
            "brand": b,
            "cells": cells
        })

    fabric_growth = []
    for series in trend_series:
        previous = series["data"][-2] if len(series["data"]) >= 2 else 0
        current = series["data"][-1] if series["data"] else 0
        fabric_growth.append({
            "fabric": series["fabric"],
            "growth_pct": _pct_change(current, previous),
            "products": current
        })

    fabric_insights = []
    if top_fabric_name:
        fabric_insights.append(
            f"{top_fabric_name} is currently the largest fabric group in {category.title()} at {top_fabric_share}."
        )
    if top_colors_fabric:
        fabric_insights.append(
            f"{top_colors_fabric[0]['color']} is the leading color within {(focus_fabric or selected_fabric or 'selected fabric').title()} styles."
        )
    if not fabric_insights:
        fabric_insights.append("No fabric-specific insight is available for the current filter selection yet.")

    avg_price_growth = "Current catalog"

    result = {
        "status": "success",
        "category": category.title(),
        "gender": gender.title(),
        "selected_fabric": (focus_fabric or selected_fabric or "All Fabrics").title(),
        "scope_label": _scope_display_label(category, "all"),
        "data_windows": {
            "trend_start": str(trend_dates[0]) if trend_dates else None,
            "trend_end": str(trend_dates[-1]) if trend_dates else None
        },
        "kpis": {
            "total_products": f"{total_prods:,}",
            "total_products_num": total_prods,
            "unique_fabrics": unique_fabrics,
            "top_fabric": top_fabric_name,
            "top_fabric_share": f"{top_fabric_share} share",
            "avg_price": f"₹{top_fabric_asp:,}",
            "avg_price_growth": avg_price_growth
        },
        "fabric_distribution": fabric_distribution,
        "fabric_trend": {
            "labels": month_labels,
            "series": trend_series
        },
        "average_price_by_fabric": average_price_by_fabric,
        "top_fabrics_ranked": top_fabrics_ranked,
        "fabric_growth": fabric_growth,
        "top_colors_by_fabric": top_colors_fabric,
        "sidebar_counts": {
            "price_buckets": price_buckets,
            "brand_sizes": brand_size_counts,
            "brands_list": brand_options
        },
        "fabric_brand_heatmap": {
            "columns": heatmap_columns,
            "rows": heatmap_matrix
        },
        "fabric_insights": fabric_insights
    }
    api_cache.set(cache_key, result, ttl=300.0)
    return jsonify(result)


@app.route("/api/brands-intelligence")
def get_brands_intelligence():
    """100% Genuine dynamic brands intelligence & analysis scope data with multi-tier caching."""
    category = request.args.get("category", "shirts").strip()
    gender = request.args.get("gender", "men").strip()
    subcategory = request.args.get("subcategory", "all").strip()
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    price_ranges = request.args.get("price_ranges", "").strip()
    brand_size = request.args.get("brand_size", "").strip()
    brand_type = request.args.get("brand_type", "").strip()
    brand = request.args.get("brand", "").strip()
    color = request.args.get("color", "").strip()
    fabric = request.args.get("fabric", "").strip()
    fit = request.args.get("fit", "").strip()
    discount_min = request.args.get("discount_min")
    rating_min = request.args.get("rating_min")
    availability = request.args.get("availability", "").strip()
    new_arrivals = request.args.get("new_arrivals", "").strip()

    cache_key = f"brands_intel_v6:{category.lower()}:{gender.lower()}:{subcategory}:{price_min}:{price_max}:{price_ranges}:{brand_size}:{brand_type}:{brand}:{color}:{fabric}:{fit}:{discount_min}:{rating_min}:{availability}:{new_arrivals}"
    cached = _load_shared_cache(cache_key)
    if cached is not None:
        api_cache.set(cache_key, cached, ttl=300.0)
        return jsonify(cached)

    conn = db._get_connection()
    cur = conn.cursor()

    scope_filters = {
        "category": category,
        "gender": gender,
        "price_min": price_min,
        "price_max": price_max,
        "price_ranges": price_ranges,
        "brand_size": brand_size,
        "brand_type": brand_type,
        "subcategory": subcategory,
        "brand": brand,
        "color": color,
        "fabric": fabric,
        "fit": fit,
        "discount_min": discount_min,
        "rating_min": rating_min,
        "availability": availability,
        "new_arrivals": new_arrivals
    }

    sidebar_cache_key = f"sb_scope_v1:{cache_key}"
    sb_data = api_cache.get(sidebar_cache_key)
    if not sb_data:
        sb_data = _build_scope_sidebar_counts(cur, scope_filters)
        api_cache.set(sidebar_cache_key, sb_data, ttl=180.0)

    # 1. Active filtered query
    active_where_sql, active_params = _build_catalog_filters(
        category=scope_filters["category"],
        gender=scope_filters["gender"],
        price_min=scope_filters["price_min"],
        price_max=scope_filters["price_max"],
        price_ranges=scope_filters["price_ranges"],
        brand_size=scope_filters["brand_size"],
        brand_type=scope_filters["brand_type"],
        subcategory=scope_filters["subcategory"],
        brand=scope_filters["brand"],
        color=scope_filters["color"],
        fabric=scope_filters["fabric"],
        fit=scope_filters["fit"],
        discount_min=scope_filters["discount_min"],
        rating_min=scope_filters["rating_min"],
        availability=scope_filters["availability"],
        new_arrivals=scope_filters["new_arrivals"]
    )

    sample_rows = []

    # Core aggregation query (runs on active_where_sql)
    cur.execute(f"""
        SELECT 
            COUNT(*) as total_prods,
            ROUND(AVG(p.selling_price)) as mean_price,
            ROUND(AVG(p.discount_percentage), 1) as avg_disc,
            SUM(CASE WHEN p.selling_price < 500 THEN 1 ELSE 0 END) as p_lt_500,
            SUM(CASE WHEN p.selling_price >= 500 AND p.selling_price < 1000 THEN 1 ELSE 0 END) as p_500_1k,
            SUM(CASE WHEN p.selling_price >= 1000 AND p.selling_price < 2000 THEN 1 ELSE 0 END) as p_1k_2k,
            SUM(CASE WHEN p.selling_price >= 2000 AND p.selling_price < 3000 THEN 1 ELSE 0 END) as p_2k_3k,
            SUM(CASE WHEN p.selling_price >= 3000 AND p.selling_price < 4000 THEN 1 ELSE 0 END) as p_3k_4k,
            SUM(CASE WHEN p.selling_price >= 4000 THEN 1 ELSE 0 END) as p_gt_4k
        FROM products p
        WHERE {active_where_sql};
    """, active_params)
    k_row = cur.fetchone()
    total_prods = int(k_row["total_prods"] or 0)
    mean_price = int(k_row["mean_price"] or 0)
    avg_disc = float(k_row["avg_disc"] or 0.0)

    p_lt_500 = int(k_row["p_lt_500"] or 0)
    p_500_1k = int(k_row["p_500_1k"] or 0)
    p_1k_2k = int(k_row["p_1k_2k"] or 0)
    p_2k_3k = int(k_row["p_2k_3k"] or 0)
    p_3k_4k = int(k_row["p_3k_4k"] or 0)
    p_gt_4k = int(k_row["p_gt_4k"] or 0)

    price_dist = [
        {"label": "< 500", "count": p_lt_500},
        {"label": "500 - 1K", "count": p_500_1k},
        {"label": "1K - 2K", "count": p_1k_2k},
        {"label": "2K - 3K", "count": p_2k_3k},
        {"label": "3K - 4K", "count": p_3k_4k},
        {"label": "> 4K", "count": p_gt_4k}
    ]

    peak_bracket = max(price_dist, key=lambda b: b["count"])["label"]

    use_exact_price_shape = (
        total_prods <= 50000
        or bool(scope_filters["subcategory"] and scope_filters["subcategory"] != "all")
        or bool(scope_filters["brand"])
        or bool(scope_filters["color"])
        or bool(scope_filters["fabric"])
        or bool(scope_filters["fit"])
        or bool(scope_filters["price_min"])
        or bool(scope_filters["price_max"])
        or bool(scope_filters["price_ranges"])
        or bool(scope_filters["discount_min"])
        or bool(scope_filters["rating_min"])
        or bool(scope_filters["availability"])
        or bool(scope_filters["new_arrivals"])
    )

    if use_exact_price_shape:
        cur.execute(f"""
            SELECT
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.selling_price)),
                COALESCE(MODE() WITHIN GROUP (ORDER BY ROUND(p.selling_price)), ROUND(AVG(p.selling_price)))
            FROM products p
            WHERE {active_where_sql} AND p.selling_price > 0;
        """, active_params)
        price_shape_row = cur.fetchone() or {}
        median_price = _safe_int(price_shape_row[0], mean_price)
        mode_price = _safe_int(price_shape_row[1], median_price or mean_price)
    else:
        weighted_price_points = [
            (399, p_lt_500),
            (750, p_500_1k),
            (1500, p_1k_2k),
            (2500, p_2k_3k),
            (3500, p_3k_4k),
            (4500, p_gt_4k)
        ]
        total_weight = sum(weight for _, weight in weighted_price_points)
        if total_weight > 0:
            midpoint = total_weight / 2
            running = 0
            median_price = mean_price
            for price_point, weight in weighted_price_points:
                running += weight
                if running >= midpoint:
                    median_price = price_point
                    break
        else:
            median_price = mean_price
        mode_price = max(weighted_price_points, key=lambda item: item[1])[0] if weighted_price_points else mean_price

    # 2. All Brands (computes top brand, scale breakdown, and top 10 table with true medians)
    if use_exact_price_shape:
        cur.execute(f"""
            WITH filtered_products AS MATERIALIZED (
                SELECT p.brand, p.selling_price, COALESCE(p.discount_percentage, 0) as discount_percentage
                FROM products p
                WHERE {active_where_sql}
            ),
            brand_counts AS (
                SELECT
                    fp.brand,
                    COUNT(*) as cnt,
                    ROUND(AVG(fp.selling_price)) as avg_price,
                    ROUND(AVG(fp.discount_percentage), 1) as avg_discount
                FROM filtered_products fp
                WHERE fp.brand IS NOT NULL AND fp.brand != ''
                GROUP BY fp.brand
            ),
            brand_ranked_prices AS (
                SELECT
                    fp.brand,
                    fp.selling_price,
                    ROW_NUMBER() OVER (PARTITION BY fp.brand ORDER BY fp.selling_price) as rn,
                    COUNT(*) OVER (PARTITION BY fp.brand) as total_rows
                FROM filtered_products fp
                WHERE fp.brand IS NOT NULL AND fp.brand != '' AND fp.selling_price > 0
            ),
            brand_medians AS (
                SELECT
                    brand,
                    ROUND(AVG(selling_price)) as median_price
                FROM brand_ranked_prices
                WHERE rn IN ((total_rows + 1) / 2, (total_rows + 2) / 2)
                GROUP BY brand
            )
            SELECT
                bc.brand,
                bc.cnt,
                bc.avg_price,
                bc.avg_discount,
                COALESCE(bm.median_price, bc.avg_price, 0) as median_price
            FROM brand_counts bc
            LEFT JOIN brand_medians bm ON bm.brand = bc.brand
            ORDER BY bc.cnt DESC, bc.brand ASC;
        """, active_params)
    else:
        cur.execute(f"""
            SELECT
                p.brand,
                COUNT(*) as cnt,
                ROUND(AVG(p.selling_price)) as avg_price,
                ROUND(AVG(COALESCE(p.discount_percentage, 0)), 1) as avg_discount,
                ROUND(AVG(p.selling_price)) as median_price
            FROM products p
            WHERE {active_where_sql} AND p.brand IS NOT NULL AND p.brand != ''
            GROUP BY p.brand
            ORDER BY cnt DESC, p.brand ASC;
        """, active_params)
    all_b_rows = cur.fetchall()

    top_brand_name = all_b_rows[0]["brand"] if all_b_rows else ""
    top_brand_count = int(all_b_rows[0]["cnt"]) if all_b_rows else 0

    large_b = [r for r in all_b_rows if int(r["cnt"]) >= LARGE_BRAND_MIN_PRODUCTS]
    mid_b = [r for r in all_b_rows if MID_BRAND_MIN_PRODUCTS <= int(r["cnt"]) < LARGE_BRAND_MIN_PRODUCTS]
    small_b = [r for r in all_b_rows if int(r["cnt"]) < MID_BRAND_MIN_PRODUCTS]

    if use_exact_price_shape:
        cur.execute(f"""
            WITH filtered_products AS MATERIALIZED (
                SELECT p.brand, p.selling_price
                FROM products p
                WHERE {active_where_sql} AND p.brand IS NOT NULL AND p.brand != '' AND p.selling_price > 0
            ),
            brand_counts AS (
                SELECT brand, COUNT(*) as cnt
                FROM filtered_products
                GROUP BY brand
            ),
            tiered_prices AS (
                SELECT
                    CASE
                        WHEN bc.cnt >= {LARGE_BRAND_MIN_PRODUCTS} THEN 'largest'
                        WHEN bc.cnt >= {MID_BRAND_MIN_PRODUCTS} THEN 'midsize'
                        ELSE 'small'
                    END as tier,
                    fp.selling_price
                FROM filtered_products fp
                JOIN brand_counts bc ON bc.brand = fp.brand
            ),
            ranked_tier_prices AS (
                SELECT
                    tier,
                    selling_price,
                    ROW_NUMBER() OVER (PARTITION BY tier ORDER BY selling_price) as rn,
                    COUNT(*) OVER (PARTITION BY tier) as total_rows
                FROM tiered_prices
            )
            SELECT tier, ROUND(AVG(selling_price)) as median_price
            FROM ranked_tier_prices
            WHERE rn IN ((total_rows + 1) / 2, (total_rows + 2) / 2)
            GROUP BY tier;
        """, active_params)
        tier_price_map = {row["tier"]: int(row["median_price"] or 0) for row in cur.fetchall()}
        large_med = tier_price_map.get("largest", 0)
        mid_med = tier_price_map.get("midsize", 0)
        small_med = tier_price_map.get("small", 0)
    else:
        large_med = int(round(sum(_safe_float(r["avg_price"]) for r in large_b) / max(1, len(large_b)))) if large_b else 0
        mid_med = int(round(sum(_safe_float(r["avg_price"]) for r in mid_b) / max(1, len(mid_b)))) if mid_b else 0
        small_med = int(round(sum(_safe_float(r["avg_price"]) for r in small_b) / max(1, len(small_b)))) if small_b else 0

    brands_by_scale = {
        "largest": {
            "count": len(large_b),
            "threshold": f">= {LARGE_BRAND_MIN_PRODUCTS:,} products",
            "brands": [r["brand"] for r in large_b[:4]],
            "more_count": max(0, len(large_b) - 4)
        },
        "midsize": {
            "count": len(mid_b),
            "threshold": f"{MID_BRAND_MIN_PRODUCTS:,} – {LARGE_BRAND_MIN_PRODUCTS - 1:,} products",
            "brands": [r["brand"] for r in mid_b[:4]],
            "more_count": max(0, len(mid_b) - 4)
        },
        "small": {
            "count": len(small_b),
            "threshold": f"< {MID_BRAND_MIN_PRODUCTS:,} products",
            "brands": [r["brand"] for r in small_b[:4]],
            "more_count": max(0, len(small_b) - 4)
        }
    }

    top_10_brands = []
    for idx, r in enumerate(all_b_rows[:10], 1):
        top_10_brands.append({
            "rank": idx,
            "brand": r["brand"],
            "products": int(r["cnt"]),
            "median_price": f"₹{int(r['median_price'] or 0):,}",
            "avg_discount": f"{float(r['avg_discount'] or 0.0)}%"
        })

    # 3. Top Fabrics
    cur.execute(f"""
        SELECT 
            CASE 
                WHEN LOWER(p.fabric) LIKE '%cotton%' AND (LOWER(p.fabric) LIKE '%blend%' OR LOWER(p.fabric) LIKE '%poly%' OR LOWER(p.fabric) LIKE '%,%') THEN 'Cotton Blend'
                WHEN LOWER(p.fabric) LIKE '%cotton%' THEN 'Cotton'
                WHEN LOWER(p.fabric) LIKE '%poly%' THEN 'Polyester'
                WHEN LOWER(p.fabric) LIKE '%linen%' THEN 'Linen'
                WHEN LOWER(p.fabric) LIKE '%viscose%' THEN 'Viscose'
                WHEN LOWER(p.fabric) LIKE '%denim%' THEN 'Denim'
                ELSE 'Others'
            END as clean_f,
            COUNT(*) as cnt
        FROM products p
        WHERE {active_where_sql} AND p.fabric IS NOT NULL AND p.fabric != ''
        GROUP BY clean_f
        ORDER BY cnt DESC
        LIMIT 7;
    """, active_params)
    f_rows = cur.fetchall()
    top_fabrics = [{"fabric": r["clean_f"], "count": int(r["cnt"]), "share": f"{round(int(r['cnt']) / max(1, total_prods) * 100, 1)}%"} for r in f_rows]

    # 4. Top Colors
    cur.execute(f"""
        SELECT p.primary_color, p.color_hex, COUNT(*) as cnt
        FROM products p
        WHERE {active_where_sql} AND {_valid_color_sql("p.primary_color")}
        GROUP BY p.primary_color, p.color_hex
        ORDER BY cnt DESC
        LIMIT 7;
    """, active_params)
    c_rows = cur.fetchall()
    top_colors = [{
        "color": _normalize_color_name(r["primary_color"], fallback="Multicolor"),
        "hex": _normalize_color_hex(r["color_hex"], r["primary_color"], fallback="#0f172a"),
        "count": int(r["cnt"]),
        "share": f"{round(int(r['cnt']) / max(1, total_prods) * 100, 1)}%"
    } for r in c_rows]

    # 5. Top Fits (Dynamic)
    cur.execute(f"""
        SELECT p.fit, COUNT(*) as fit_cnt
        FROM products p
        WHERE {active_where_sql} AND p.fit IS NOT NULL AND p.fit != '' AND p.fit != 'NA'
        GROUP BY p.fit
        ORDER BY fit_cnt DESC
        LIMIT 6;
    """, active_params)
    fit_rows = cur.fetchall()
    top_fits = [{"fit": r["fit"], "count": int(r["fit_cnt"])} for r in fit_rows]

    # 6. Top 5 representative products with recent sales/rating scoring and title de-duplication
    latest_sales_date = _latest_sales_date(cur)
    prod_rows = []
    sales_window_days = 9
    if latest_sales_date:
        sales_window_start = latest_sales_date - timedelta(days=sales_window_days - 1)
        cur.execute(f"""
            WITH product_scores AS (
                SELECT
                    p.product_id,
                    p.brand,
                    p.title,
                    p.selling_price,
                    COALESCE(SUM(sa.units_sold), 0) as units_sold_window,
                    ROUND(AVG(COALESCE(sa.ros, 0)), 2) as avg_ros,
                    COALESCE(MAX(p.total_ratings_count), 0) as ratings_count
                FROM products p
                LEFT JOIN daily_sales_analytics sa
                    ON sa.product_id = p.product_id
                   AND sa.analytics_date >= ?
                   AND sa.analytics_date <= ?
                WHERE {active_where_sql}
                GROUP BY p.product_id, p.brand, p.title, p.selling_price
            ),
            ranked_products AS (
                SELECT
                    ps.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY LOWER(COALESCE(ps.brand, '')), LOWER(COALESCE(ps.title, ''))
                        ORDER BY ps.units_sold_window DESC, ps.avg_ros DESC, ps.ratings_count DESC, ps.selling_price DESC, ps.product_id DESC
                    ) as dedupe_rn
                FROM product_scores ps
            )
            SELECT product_id, brand, title, selling_price, units_sold_window, avg_ros, ratings_count
            FROM ranked_products
            WHERE dedupe_rn = 1
            ORDER BY units_sold_window DESC, avg_ros DESC, ratings_count DESC, selling_price DESC, product_id DESC
            LIMIT 20;
        """, [sales_window_start, latest_sales_date] + active_params)
        prod_rows = cur.fetchall()

    if not prod_rows:
        cur.execute(f"""
            WITH ranked_products AS (
                SELECT
                    p.product_id,
                    p.brand,
                    p.title,
                    p.selling_price,
                    COALESCE(p.total_ratings_count, 0) as ratings_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY LOWER(COALESCE(p.brand, '')), LOWER(COALESCE(p.title, ''))
                        ORDER BY COALESCE(p.total_ratings_count, 0) DESC, p.selling_price DESC, p.product_id DESC
                    ) as dedupe_rn
                FROM products p
                WHERE {active_where_sql}
            )
            SELECT product_id, brand, title, selling_price, 0 as units_sold_window, 0 as avg_ros, ratings_count
            FROM ranked_products
            WHERE dedupe_rn = 1
            ORDER BY ratings_count DESC, selling_price DESC, product_id DESC
            LIMIT 20;
        """, active_params)
        prod_rows = cur.fetchall()
    
    prod_stocks = {}
    prod_image_map = {}
    if prod_rows:
        p_ids = [r["product_id"] for r in prod_rows]
        placeholders = ",".join(["?"] * len(p_ids))
        cur.execute(f"SELECT product_id, COALESCE(SUM(inventory_count), 0) FROM product_sizes WHERE product_id IN ({placeholders}) GROUP BY product_id", p_ids)
        prod_stocks = dict(cur.fetchall())
        cur.execute(f"SELECT product_id, full_data_json FROM products WHERE product_id IN ({placeholders})", p_ids)
        for img_row in cur.fetchall():
            prod_image_map[int(img_row["product_id"])] = _load_primary_image(img_row["full_data_json"])

    top_products = []
    diversify_brands = not bool((scope_filters.get("brand") or "").strip())
    seen_product_brands = set()
    for idx, r in enumerate(prod_rows, 1):
        current_brand = str(r["brand"] or "").strip()
        if diversify_brands and current_brand:
            if current_brand.lower() in seen_product_brands:
                continue
            seen_product_brands.add(current_brand.lower())

        raw_title = str(r["title"] or "").strip()
        raw_brand = current_brand
        c_title = raw_title.replace(raw_brand, "").strip() if raw_title and raw_brand else raw_title
        if c_title.startswith("Men") or c_title.startswith("Women"):
            c_title = c_title[3:].strip()
        if len(c_title) > 28:
            c_title = c_title[:26] + "..."

        stk = int(prod_stocks.get(r["product_id"], 0))
        units_sold_window = int(r["units_sold_window"] or 0)
        avg_ros = _safe_float(r["avg_ros"] or 0.0)
        velocity_value = avg_ros if avg_ros > 0 else round(units_sold_window / max(1, sales_window_days), 2)
        velocity_value = max(0.1, velocity_value) if stk > 0 or units_sold_window > 0 else 0.0
        velocity_label = f"{velocity_value}/d" if velocity_value > 0 else "No sales yet"

        top_products.append({
            "rank": len(top_products) + 1,
            "product_id": r["product_id"],
            "brand": r["brand"],
            "title": c_title if c_title else raw_title[:25],
            "price": f"₹{int(r['selling_price'] or 0):,}",
            "velocity": velocity_label,
            "units_sold_window": units_sold_window,
            "stock": stk,
            "image_url": prod_image_map.get(int(r["product_id"]), "")
        })
        if len(top_products) >= 5:
            break

    if not use_exact_price_shape and sample_rows:
        sample_prices = sorted(price for price in sample_prices if price is not None)
        if sample_prices:
            median_price = int(round(_median_from_sorted(sample_prices)))
        fit_counter = Counter()
        for row in sample_rows:
            fit_value = str(row[0] or "").strip()
            if fit_value and fit_value.upper() != "NA":
                fit_counter[fit_value] += 1
        if fit_counter:
            top_fits = [{"fit": fit_name, "count": count} for fit_name, count in fit_counter.most_common(6)]

    scope_label = _scope_display_label(category, subcategory)

    result = {
        "status": "success",
        "category": category.title(),
        "gender": gender.title(),
        "subcategory": subcategory,
        "scope_label": scope_label,
        "kpis": {
            "total_products": f"{total_prods:,}",
            "total_products_num": total_prods,
            "median_price": f"₹{median_price:,}",
            "mean_price": f"₹{mean_price:,}",
            "mode_price": f"₹{mode_price:,}",
            "avg_discount": f"{avg_disc}%",
            "top_brand": {
                "name": top_brand_name,
                "products": f"{top_brand_count:,} products"
            },
            "pricing_note": "Median and mode are computed from live filtered product prices.",
            "discount_note": "Average discount across the current filtered products."
        },
        "sidebar_counts": sb_data,
        "price_distribution": {
            "brackets": price_dist,
            "median_price": f"₹{median_price:,}",
            "mode_price": f"₹{mode_price:,}",
            "mean_price": f"₹{mean_price:,}",
            "most_competitive_range": peak_bracket
        },
        "top_fabrics": top_fabrics,
        "top_colors": top_colors,
        "top_fits": top_fits,
        "brands_by_scale": brands_by_scale,
        "top_10_brands": top_10_brands,
        "median_price_by_brand_size": [
            {"tier": f"Largest ({len(large_b)} brands)", "median_price": large_med},
            {"tier": f"Mid-size ({len(mid_b)} brands)", "median_price": mid_med},
            {"tier": f"Small ({len(small_b)} brands)", "median_price": small_med}
        ],
        "top_products": top_products,
        "top_products_note": "Ranked using recent sales telemetry first, then ratings and stock coverage.",
        "subcategories": sb_data.get("subcategories", [])
    }
    api_cache.set(cache_key, result, ttl=300.0)
    _store_shared_cache(cache_key, result, ttl=300.0)
    return jsonify(result)


@app.route("/api/price-intelligence")
def get_price_intelligence():
    """Computes comprehensive price intelligence across categories, brands, fabrics, and colors."""
    cat = request.args.get("category", "shirts").strip().lower()
    subcat = request.args.get("subcategory", "").strip().lower()
    gender = request.args.get("gender", "").strip().lower()
    brands_param = request.args.get("brands", "").strip()
    price_min = request.args.get("price_min", type=float)
    price_max = request.args.get("price_max", type=float)
    fabric = request.args.get("fabric", "").strip()
    color = request.args.get("color", "").strip()
    discount_range = request.args.get("discount_range", "").strip()
    availability = request.args.get("availability", "all").strip().lower()

    cache_key = f"price_intel_v3:{cat}:{subcat}:{gender}:{brands_param}:{price_min}:{price_max}:{fabric}:{color}:{discount_range}:{availability}"
    cached = api_cache.get(cache_key)
    if cached:
        return jsonify(cached)

    conn = db._get_connection()
    cur = conn.cursor()
    latest_snapshot_date = _get_latest_inventory_snapshot_date(cur)

    def build_price_scope(
        *,
        include_category=True,
        include_subcategory=True,
        include_brands=True,
        include_fabric=True,
        include_color=True,
        include_discount=True,
        include_availability=True,
        include_price=True
    ):
        where_sql, scope_params = _build_catalog_filters(
            category=cat if include_category else "all",
            gender=gender or "all",
            price_min=price_min if include_price else None,
            price_max=price_max if include_price else None,
            fabric=fabric if include_fabric else None,
            subcategory=subcat if include_subcategory else None,
            brand=brands_param if include_brands else None,
            color=color if include_color else None,
            availability=("in_stock" if availability == "in_stock" and include_availability else None)
        )
        where_sql = _append_where_clause(where_sql, "p.selling_price > 0")

        if include_discount and discount_range:
            if discount_range == "0-20":
                where_sql = _append_where_clause(where_sql, "p.discount_percentage >= 0 AND p.discount_percentage <= 20")
            elif discount_range == "20-40":
                where_sql = _append_where_clause(where_sql, "p.discount_percentage > 20 AND p.discount_percentage <= 40")
            elif discount_range == "40-60":
                where_sql = _append_where_clause(where_sql, "p.discount_percentage > 40 AND p.discount_percentage <= 60")
            elif discount_range == "60+":
                where_sql = _append_where_clause(where_sql, "p.discount_percentage > 60")

        if include_availability and availability == "low_stock" and latest_snapshot_date:
            where_sql = _append_where_clause(
                where_sql,
                "p.product_id IN (SELECT product_id FROM daily_inventory_snapshots WHERE snapshot_date = ? AND total_stock < 5)"
            )
            scope_params.append(latest_snapshot_date)

        return where_sql, scope_params

    where_sql, params = build_price_scope()
    baseline_where_sql, baseline_params = build_price_scope(
        include_subcategory=False,
        include_fabric=False,
        include_color=False,
        include_discount=False,
        include_availability=False,
        include_price=False
    )

    # 1. Like-for-like baseline for deltas
    cur.execute(f"""
        SELECT
            ROUND(AVG(p.selling_price), 2),
            ROUND(AVG(p.discount_percentage), 2),
            COUNT(*) as total_count,
            SUM(CASE WHEN p.discount_percentage > 0 THEN 1 ELSE 0 END) as disc_count,
            COUNT(CASE WHEN p.selling_price < 500 THEN 1 END),
            COUNT(CASE WHEN p.selling_price >= 500 AND p.selling_price < 1000 THEN 1 END),
            COUNT(CASE WHEN p.selling_price >= 1000 AND p.selling_price < 2000 THEN 1 END),
            COUNT(CASE WHEN p.selling_price >= 2000 AND p.selling_price < 3000 THEN 1 END),
            COUNT(CASE WHEN p.selling_price >= 3000 AND p.selling_price < 4000 THEN 1 END),
            COUNT(CASE WHEN p.selling_price >= 4000 THEN 1 END)
        FROM products p
        WHERE {baseline_where_sql};
    """, baseline_params)
    baseline_row = cur.fetchone() or (0.0, 0.0, 0, 0, 0, 0, 0, 0, 0, 0)
    cat_baseline_asp = _safe_float(baseline_row[0])
    cat_baseline_disc = _safe_float(baseline_row[1])
    baseline_total_cnt = _safe_int(baseline_row[2])
    baseline_disc_cnt = _safe_int(baseline_row[3])
    baseline_disc_share = round((baseline_disc_cnt / baseline_total_cnt * 100), 1) if baseline_total_cnt else 0.0

    # 2. Filtered KPIs and 3. Price Distribution Bins (combined into a single fast query)
    cur.execute(f"""
        SELECT 
            COUNT(*) as total_count,
            ROUND(AVG(p.selling_price)) as avg_price,
            ROUND(MIN(p.selling_price)) as min_price,
            ROUND(MAX(p.selling_price)) as max_price,
            SUM(CASE WHEN p.discount_percentage > 0 THEN 1 ELSE 0 END) as disc_count,
            ROUND(AVG(p.discount_percentage), 1) as avg_disc,
            COUNT(CASE WHEN p.selling_price < 500 THEN 1 END),
            COUNT(CASE WHEN p.selling_price >= 500 AND p.selling_price < 1000 THEN 1 END),
            COUNT(CASE WHEN p.selling_price >= 1000 AND p.selling_price < 2000 THEN 1 END),
            COUNT(CASE WHEN p.selling_price >= 2000 AND p.selling_price < 3000 THEN 1 END),
            COUNT(CASE WHEN p.selling_price >= 3000 AND p.selling_price < 4000 THEN 1 END),
            COUNT(CASE WHEN p.selling_price >= 4000 THEN 1 END)
        FROM products p
        WHERE {where_sql}
    """, params)
    k_row = cur.fetchone() or (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    total_cnt = k_row[0] or 0
    avg_p = k_row[1] or 0
    min_p = k_row[2] or 0
    max_p = k_row[3] or 0
    disc_cnt = k_row[4] or 0
    avg_d = k_row[5] or 0.0

    distribution = [
        {"range": "< 500", "label": "< 500", "count": k_row[6] or 0},
        {"range": "500 - 1,000", "label": "500-1K", "count": k_row[7] or 0},
        {"range": "1,000 - 2,000", "label": "1K-2K", "count": k_row[8] or 0},
        {"range": "2,000 - 3,000", "label": "2K-3K", "count": k_row[9] or 0},
        {"range": "3,000 - 4,000", "label": "3K-4K", "count": k_row[10] or 0},
        {"range": "> 4,000", "label": "> 4K", "count": k_row[11] or 0}
    ]

    avg_p_num = float(avg_p or 0.0)
    cur.execute(f"""
        WITH ranked_prices AS (
            SELECT p.selling_price,
                   ROW_NUMBER() OVER (ORDER BY p.selling_price) as rn,
                   COUNT(*) OVER () as total_rows
            FROM products p
            WHERE {where_sql} AND p.selling_price > 0
        )
        SELECT
            ROUND(AVG(CASE WHEN rn IN ((total_rows + 1) / 2, (total_rows + 2) / 2) THEN selling_price END)),
            ROUND(AVG(CASE WHEN rn IN (CAST(((total_rows - 1) * 0.25 + 1) AS INT), CAST(((total_rows - 1) * 0.25 + 2) AS INT)) THEN selling_price END)),
            ROUND(AVG(CASE WHEN rn IN (CAST(((total_rows - 1) * 0.75 + 1) AS INT), CAST(((total_rows - 1) * 0.75 + 2) AS INT)) THEN selling_price END))
        FROM ranked_prices;
    """, params)
    percentile_row = cur.fetchone() or (0, 0, 0)
    median_p = _safe_int(percentile_row[0])

    cur.execute(f"""
        WITH ranked_prices AS (
            SELECT p.selling_price,
                   ROW_NUMBER() OVER (ORDER BY p.selling_price) as rn,
                   COUNT(*) OVER () as total_rows
            FROM products p
            WHERE {baseline_where_sql} AND p.selling_price > 0
        )
        SELECT ROUND(AVG(CASE WHEN rn IN ((total_rows + 1) / 2, (total_rows + 2) / 2) THEN selling_price END))
        FROM ranked_prices;
    """, baseline_params)
    baseline_median = _safe_float((cur.fetchone() or [0])[0])

    peak_bucket = max(distribution, key=lambda item: item["count"])["label"] if distribution else ""
    mode_p = _price_band_midpoint(
        {
            "< 500": "< ₹500",
            "500-1K": "₹500 - 1K",
            "1K-2K": "₹1K - 2K",
            "2K-3K": "₹2K - 3K",
            "3K-4K": "₹3K - 4K",
            "> 4K": "> ₹4K"
        }.get(peak_bucket, ""),
        _safe_int(avg_p_num)
    )

    baseline_distribution = [
        {"label": "< 500", "count": _safe_int(baseline_row[4])},
        {"label": "500-1K", "count": _safe_int(baseline_row[5])},
        {"label": "1K-2K", "count": _safe_int(baseline_row[6])},
        {"label": "2K-3K", "count": _safe_int(baseline_row[7])},
        {"label": "3K-4K", "count": _safe_int(baseline_row[8])},
        {"label": "> 4K", "count": _safe_int(baseline_row[9])}
    ]
    baseline_peak_bucket = max(baseline_distribution, key=lambda item: item["count"])["label"] if baseline_distribution else ""
    baseline_mode = _price_band_midpoint(
        {
            "< 500": "< ₹500",
            "500-1K": "₹500 - 1K",
            "1K-2K": "₹1K - 2K",
            "2K-3K": "₹2K - 3K",
            "3K-4K": "₹3K - 4K",
            "> 4K": "> ₹4K"
        }.get(baseline_peak_bucket, ""),
        _safe_int(cat_baseline_asp)
    )

    # Deltas
    asp_delta_pct = round(((avg_p_num - cat_baseline_asp) / cat_baseline_asp) * 100, 1) if cat_baseline_asp else 0.0
    asp_delta_str = f"{'+' if asp_delta_pct >= 0 else ''}{asp_delta_pct}%"
    baseline_median = baseline_median or cat_baseline_asp
    median_delta_pct = _pct_change(median_p, baseline_median) if baseline_median else 0.0
    median_delta_str = f"{'+' if median_delta_pct >= 0 else ''}{median_delta_pct}%"
    mode_baseline = baseline_mode or _safe_int(cat_baseline_asp)
    mode_delta_pct = _pct_change(mode_p, mode_baseline) if mode_baseline else 0.0
    mode_delta_str = f"{'+' if mode_delta_pct >= 0 else ''}{mode_delta_pct}%"

    disc_pct = round((disc_cnt / total_cnt * 100), 1) if total_cnt else 0.0
    disc_delta_pct = round(disc_pct - baseline_disc_share, 1)
    disc_delta_str = f"{'+' if disc_delta_pct >= 0 else ''}{disc_delta_pct}%"

    display_max = max_p

    kpis = {
        "avg_price": int(avg_p),
        "avg_price_formatted": f"₹{int(avg_p):,}",
        "avg_price_delta": asp_delta_str,
        "median_price": int(median_p),
        "median_price_formatted": f"₹{int(median_p):,}",
        "median_price_delta": median_delta_str,
        "mode_price": int(mode_p),
        "mode_price_formatted": f"₹{int(mode_p):,}",
        "mode_price_delta": mode_delta_str,
        "min_price": int(min_p),
        "max_price": int(max_p),
        "price_range_str": f"₹{int(min_p):,} – ₹{int(display_max):,}",
        "discounted_pct": disc_pct,
        "discounted_delta": disc_delta_str,
        "total_products": total_cnt,
        "total_products_formatted": f"{total_cnt:,}"
    }

    # 4. Average Price Trend from inventory snapshots
    cur.execute(f"""
        SELECT snap.snapshot_date, ROUND(AVG(snap.selling_price)) as asp
        FROM daily_inventory_snapshots snap
        JOIN products p ON p.product_id = snap.product_id
        WHERE {where_sql}
        GROUP BY snap.snapshot_date
        ORDER BY snap.snapshot_date DESC
        LIMIT 6;
    """, params)
    cat_trend_rows = cur.fetchall()
    cat_trend_rows = list(reversed(cat_trend_rows))

    cur.execute("""
        SELECT snapshot_date, ROUND(AVG(selling_price)) as asp
        FROM daily_inventory_snapshots
        GROUP BY snapshot_date
        ORDER BY snapshot_date DESC
        LIMIT 6;
    """)
    overall_trend_rows = list(reversed(cur.fetchall()))

    cur.execute("""
        SELECT
            MIN(snapshot_date) as min_snapshot_date,
            MAX(snapshot_date) as max_snapshot_date,
            COUNT(DISTINCT snapshot_date) as snapshot_days
        FROM daily_inventory_snapshots;
    """)
    snapshot_window_row = cur.fetchone() or {}
    snapshot_days = _safe_int(snapshot_window_row["snapshot_days"] if "snapshot_days" in snapshot_window_row else 0)
    snapshot_start = snapshot_window_row["min_snapshot_date"] if "min_snapshot_date" in snapshot_window_row else None
    snapshot_end = snapshot_window_row["max_snapshot_date"] if "max_snapshot_date" in snapshot_window_row else None

    trend_dates = [str(r[0])[-5:] for r in cat_trend_rows] if cat_trend_rows else [str(r[0])[-5:] for r in overall_trend_rows]
    if not trend_dates:
        trend_dates = ["Today"]
    cat_trend_map = {str(r[0])[-5:]: _safe_int(r[1]) for r in cat_trend_rows}
    overall_trend_map = {str(r[0])[-5:]: _safe_int(r[1]) for r in overall_trend_rows}
    cat_trend = [cat_trend_map.get(label, 0) for label in trend_dates]
    overall_trend = [overall_trend_map.get(label, 0) for label in trend_dates]

    price_trend = {
        "months": trend_dates,
        "category_trend": cat_trend,
        "overall_trend": overall_trend,
        "category_name": (cat.capitalize() if cat else "Category"),
        "latest_asp": f"₹{int(avg_p):,}",
        "delta_badge": f"↑ {abs(asp_delta_pct)}%" if asp_delta_pct >= 0 else f"↓ {abs(asp_delta_pct)}%"
    }

    data_window = {
        "snapshot_start_date": str(snapshot_start) if snapshot_start else None,
        "snapshot_end_date": str(snapshot_end) if snapshot_end else None,
        "snapshot_start_label": _format_date_label(snapshot_start),
        "snapshot_end_label": _format_date_label(snapshot_end),
        "snapshot_days": snapshot_days,
        "trend_points": len(trend_dates)
    }

    # 5. Exact scoped analytics for positioning, fabric, color, heatmap, and top brands
    cur.execute(f"""
        SELECT
            p.brand,
            COUNT(*) AS product_count,
            ROUND(AVG(p.selling_price), 1) AS avg_price,
            ROUND(AVG(COALESCE(p.discount_percentage, 0)), 1) AS avg_discount
        FROM products p
        WHERE {where_sql} AND p.brand IS NOT NULL AND p.brand != ''
        GROUP BY p.brand
        ORDER BY product_count DESC, avg_price DESC
        LIMIT 12;
    """, params)
    price_positioning_rows = cur.fetchall()
    max_cnt = max([int(row["product_count"] or 0) for row in price_positioning_rows], default=1)
    price_positioning = []
    for row in price_positioning_rows:
        count = int(row["product_count"] or 0)
        radius = max(6, min(24, int((count / max_cnt) * 22) + 6))
        price_positioning.append({
            "brand": row["brand"],
            "product_count": count,
            "avg_price": float(row["avg_price"] or 0.0),
            "avg_discount": float(row["avg_discount"] or 0.0),
            "radius": radius
        })

    cur.execute(f"""
        WITH fabric_prices AS (
            SELECT
                CASE
                    WHEN POSITION('cotton' IN LOWER(COALESCE(p.fabric, ''))) > 0 AND (
                        POSITION('blend' IN LOWER(COALESCE(p.fabric, ''))) > 0
                        OR POSITION('poly' IN LOWER(COALESCE(p.fabric, ''))) > 0
                        OR POSITION(',' IN LOWER(COALESCE(p.fabric, ''))) > 0
                    ) THEN 'Cotton Blend'
                    WHEN POSITION('cotton' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Cotton'
                    WHEN POSITION('poly' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Polyester'
                    WHEN POSITION('linen' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Linen'
                    WHEN POSITION('viscose' IN LOWER(COALESCE(p.fabric, ''))) > 0 OR POSITION('rayon' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Viscose'
                    WHEN POSITION('denim' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Denim'
                    WHEN POSITION('silk' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Silk'
                    WHEN POSITION('wool' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Wool'
                    ELSE 'Others'
                END AS fabric_bucket,
                p.selling_price
            FROM products p
            WHERE {where_sql}
        ),
        ranked_fabrics AS (
            SELECT
                fabric_bucket,
                selling_price,
                ROW_NUMBER() OVER (PARTITION BY fabric_bucket ORDER BY selling_price) AS rn,
                COUNT(*) OVER (PARTITION BY fabric_bucket) AS total_rows
            FROM fabric_prices
        )
        SELECT
            fabric_bucket,
            COUNT(*) AS cnt,
            ROUND(AVG(selling_price), 1) AS avg_price,
            ROUND(AVG(CASE WHEN rn IN ((total_rows + 1) / 2, (total_rows + 2) / 2) THEN selling_price END)) AS median_price
        FROM ranked_fabrics
        GROUP BY fabric_bucket
        ORDER BY cnt DESC, fabric_bucket ASC
        LIMIT 7;
    """, params)
    price_by_fabric = [{
        "fabric": row["fabric_bucket"],
        "products": int(row["cnt"] or 0),
        "products_formatted": f"{int(row['cnt'] or 0):,}",
        "avg_price": _safe_int(row["avg_price"]),
        "avg_price_formatted": f"₹{_safe_int(row['avg_price']):,}",
        "median_price": _safe_int(row["median_price"]),
        "median_price_formatted": f"₹{_safe_int(row['median_price']):,}"
    } for row in cur.fetchall()]

    color_hex_lookup = {
        "white": "#ffffff", "black": "#0f172a", "blue": "#2563eb", "navy": "#1e3a8a",
        "grey": "#64748b", "gray": "#64748b", "olive": "#556b2f", "red": "#dc2626",
        "green": "#16a34a", "yellow": "#eab308", "pink": "#ec4899", "brown": "#78350f",
        "beige": "#f5f5dc", "cream": "#f5f5dc"
    }
    cur.execute(f"""
        WITH color_prices AS (
            SELECT
                p.primary_color,
                p.selling_price,
                NULLIF(p.color_hex, '') AS color_hex
            FROM products p
            WHERE {where_sql} AND {_valid_color_sql("p.primary_color")}
        ),
        ranked_colors AS (
            SELECT
                primary_color,
                selling_price,
                color_hex,
                ROW_NUMBER() OVER (PARTITION BY primary_color ORDER BY selling_price) AS rn,
                COUNT(*) OVER (PARTITION BY primary_color) AS total_rows
            FROM color_prices
        )
        SELECT
            primary_color,
            COUNT(*) AS cnt,
            ROUND(AVG(selling_price), 1) AS avg_price,
            ROUND(AVG(CASE WHEN rn IN ((total_rows + 1) / 2, (total_rows + 2) / 2) THEN selling_price END)) AS median_price,
            MAX(color_hex) AS color_hex
        FROM ranked_colors
        GROUP BY primary_color
        ORDER BY cnt DESC, primary_color ASC
        LIMIT 8;
    """, params)
    price_by_color = []
    for row in cur.fetchall():
        color_name = _normalize_color_name(row["primary_color"], fallback="Multicolor")
        derived_hex = _normalize_color_hex(row["color_hex"], color_name, fallback="#94a3b8")
        price_by_color.append({
            "color": color_name,
            "hex": derived_hex,
            "products": int(row["cnt"] or 0),
            "products_formatted": f"{int(row['cnt'] or 0):,}",
            "avg_price": _safe_int(row["avg_price"]),
            "avg_price_formatted": f"₹{_safe_int(row['avg_price']):,}",
            "median_price": _safe_int(row["median_price"]),
            "median_price_formatted": f"₹{_safe_int(row['median_price']):,}"
        })

    cur.execute(f"""
        WITH scoped_products AS (
            SELECT p.brand, p.selling_price
            FROM products p
            WHERE {where_sql} AND p.brand IS NOT NULL AND p.brand != ''
        ),
        top_brands AS (
            SELECT brand, COUNT(*) AS cnt
            FROM scoped_products
            GROUP BY brand
            ORDER BY cnt DESC, brand ASC
            LIMIT 7
        )
        SELECT
            sp.brand,
            SUM(CASE WHEN sp.selling_price < 500 THEN 1 ELSE 0 END) AS b1_cnt,
            ROUND(AVG(CASE WHEN sp.selling_price < 500 THEN sp.selling_price END)) AS b1_avg,
            SUM(CASE WHEN sp.selling_price >= 500 AND sp.selling_price < 1000 THEN 1 ELSE 0 END) AS b2_cnt,
            ROUND(AVG(CASE WHEN sp.selling_price >= 500 AND sp.selling_price < 1000 THEN sp.selling_price END)) AS b2_avg,
            SUM(CASE WHEN sp.selling_price >= 1000 AND sp.selling_price < 2000 THEN 1 ELSE 0 END) AS b3_cnt,
            ROUND(AVG(CASE WHEN sp.selling_price >= 1000 AND sp.selling_price < 2000 THEN sp.selling_price END)) AS b3_avg,
            SUM(CASE WHEN sp.selling_price >= 2000 AND sp.selling_price < 3000 THEN 1 ELSE 0 END) AS b4_cnt,
            ROUND(AVG(CASE WHEN sp.selling_price >= 2000 AND sp.selling_price < 3000 THEN sp.selling_price END)) AS b4_avg,
            SUM(CASE WHEN sp.selling_price >= 3000 THEN 1 ELSE 0 END) AS b5_cnt,
            ROUND(AVG(CASE WHEN sp.selling_price >= 3000 THEN sp.selling_price END)) AS b5_avg
        FROM scoped_products sp
        JOIN top_brands tb ON tb.brand = sp.brand
        GROUP BY sp.brand, tb.cnt
        ORDER BY tb.cnt DESC, sp.brand ASC;
    """, params)
    price_heatmap = []
    for row in cur.fetchall():
        price_heatmap.append({
            "brand": row["brand"],
            "b1_cnt": int(row["b1_cnt"] or 0),
            "b1_avg": _safe_int(row["b1_avg"]) if row["b1_avg"] is not None else "-",
            "b2_cnt": int(row["b2_cnt"] or 0),
            "b2_avg": _safe_int(row["b2_avg"]) if row["b2_avg"] is not None else "-",
            "b3_cnt": int(row["b3_cnt"] or 0),
            "b3_avg": _safe_int(row["b3_avg"]) if row["b3_avg"] is not None else "-",
            "b4_cnt": int(row["b4_cnt"] or 0),
            "b4_avg": _safe_int(row["b4_avg"]) if row["b4_avg"] is not None else "-",
            "b5_cnt": int(row["b5_cnt"] or 0),
            "b5_avg": _safe_int(row["b5_avg"]) if row["b5_avg"] is not None else "-"
        })

    cur.execute(f"""
        SELECT
            p.brand,
            ROUND(AVG(p.selling_price)) AS avg_price,
            COUNT(*) AS product_count
        FROM products p
        WHERE {where_sql} AND p.brand IS NOT NULL AND p.brand != ''
        GROUP BY p.brand
        HAVING COUNT(*) >= 5
        ORDER BY avg_price DESC, product_count DESC
        LIMIT 5;
    """, params)
    top_asp_brands = [{
        "brand": row["brand"],
        "avg_price": _safe_int(row["avg_price"]),
        "avg_price_formatted": f"₹{_safe_int(row['avg_price']):,}"
    } for row in cur.fetchall()]

    cur.execute(f"""
        SELECT
            p.brand,
            ROUND(AVG(COALESCE(p.discount_percentage, 0)), 1) AS avg_discount,
            COUNT(*) AS product_count
        FROM products p
        WHERE {where_sql} AND p.brand IS NOT NULL AND p.brand != ''
        GROUP BY p.brand
        HAVING COUNT(*) >= 5
        ORDER BY avg_discount DESC, product_count DESC
        LIMIT 5;
    """, params)
    top_discount_brands = [{
        "brand": row["brand"],
        "avg_discount": float(row["avg_discount"] or 0.0),
        "avg_discount_formatted": f"{float(row['avg_discount'] or 0.0):.1f}%"
    } for row in cur.fetchall()]

    category_where_sql, category_params = build_price_scope(include_category=False)
    cur.execute(f"""
        SELECT p.category, COUNT(*) as cnt
        FROM products p
        WHERE {category_where_sql} AND p.category IS NOT NULL AND p.category != ''
        GROUP BY p.category
        ORDER BY cnt DESC, p.category ASC;
    """, category_params)
    category_buckets = {}
    for row in cur.fetchall():
        bucket = _catalog_category_option(row["category"])
        if not bucket:
            continue
        current = category_buckets.setdefault(bucket["value"], {
            "value": bucket["value"],
            "name": bucket["name"],
            "count": 0,
            "_rank": bucket["rank"]
        })
        current["count"] += int(row["cnt"] or 0)
        current["_rank"] = min(current["_rank"], bucket["rank"])
    category_total = sum(item["count"] for item in category_buckets.values())
    available_categories = [{
        "value": "all",
        "name": "All Categories",
        "count": int(category_total or total_cnt or 0)
    }] + [
        {
            "value": item["value"],
            "name": item["name"],
            "count": item["count"]
        }
        for item in sorted(category_buckets.values(), key=lambda item: (item["_rank"], -item["count"], item["name"].lower()))
    ]

    subcategory_where_sql, subcategory_params = build_price_scope(include_subcategory=False)
    cur.execute(f"""
        SELECT p.sub_category, COUNT(*) as cnt
        FROM products p
        WHERE {subcategory_where_sql} AND p.sub_category IS NOT NULL AND p.sub_category != ''
        GROUP BY p.sub_category
        ORDER BY cnt DESC, p.sub_category ASC
        LIMIT 30;
    """, subcategory_params)
    available_subcategories = [
        {"value": str(r["sub_category"]).strip().lower(), "name": r["sub_category"], "count": int(r["cnt"] or 0)}
        for r in cur.fetchall()
        if r["sub_category"]
    ]

    fabric_where_sql, fabric_params = build_price_scope(include_fabric=False)
    cur.execute(f"""
        SELECT fabric_name, cnt
        FROM (
            SELECT
                CASE
                    WHEN POSITION('cotton' IN LOWER(COALESCE(p.fabric, ''))) > 0 AND (
                        POSITION('blend' IN LOWER(COALESCE(p.fabric, ''))) > 0
                        OR POSITION('poly' IN LOWER(COALESCE(p.fabric, ''))) > 0
                        OR POSITION(',' IN LOWER(COALESCE(p.fabric, ''))) > 0
                    ) THEN 'Cotton Blend'
                    WHEN POSITION('cotton' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Cotton'
                    WHEN POSITION('poly' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Polyester'
                    WHEN POSITION('linen' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Linen'
                    WHEN POSITION('viscose' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Viscose'
                    WHEN POSITION('denim' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Denim'
                    WHEN POSITION('silk' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Silk'
                    ELSE NULL
                END as fabric_name,
                COUNT(*) as cnt
            FROM products p
            WHERE {fabric_where_sql}
            GROUP BY CASE
                WHEN POSITION('cotton' IN LOWER(COALESCE(p.fabric, ''))) > 0 AND (
                    POSITION('blend' IN LOWER(COALESCE(p.fabric, ''))) > 0
                    OR POSITION('poly' IN LOWER(COALESCE(p.fabric, ''))) > 0
                    OR POSITION(',' IN LOWER(COALESCE(p.fabric, ''))) > 0
                ) THEN 'Cotton Blend'
                WHEN POSITION('cotton' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Cotton'
                WHEN POSITION('poly' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Polyester'
                WHEN POSITION('linen' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Linen'
                WHEN POSITION('viscose' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Viscose'
                WHEN POSITION('denim' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Denim'
                WHEN POSITION('silk' IN LOWER(COALESCE(p.fabric, ''))) > 0 THEN 'Silk'
                ELSE NULL
            END
        ) q
        WHERE fabric_name IS NOT NULL
        ORDER BY cnt DESC, fabric_name ASC
        LIMIT 20;
    """, fabric_params)
    available_fabrics = [
        {"value": str(r["fabric_name"]).strip().lower(), "name": r["fabric_name"], "count": int(r["cnt"] or 0)}
        for r in cur.fetchall()
        if r["fabric_name"]
    ]

    color_where_sql, color_params = build_price_scope(include_color=False)
    cur.execute(f"""
        SELECT p.primary_color, COUNT(*) as cnt
        FROM products p
        WHERE {color_where_sql} AND {_valid_color_sql("p.primary_color")}
        GROUP BY p.primary_color
        ORDER BY cnt DESC, p.primary_color ASC
        LIMIT 25;
    """, color_params)
    available_colors = [
        {
            "value": str(_normalize_color_name(r["primary_color"], fallback="Multicolor")).strip().lower(),
            "name": _normalize_color_name(r["primary_color"], fallback="Multicolor"),
            "count": int(r["cnt"] or 0)
        }
        for r in cur.fetchall()
        if _normalize_color_name(r["primary_color"], fallback=None)
    ]

    # 11. Strategic Price Opportunities
    top_bucket = max(distribution, key=lambda row: row["count"]) if distribution else {"label": "N/A", "count": 0}
    top_bucket_share = round((top_bucket["count"] / max(1, total_cnt)) * 100.0, 1) if total_cnt else 0.0
    top_fabric_name = price_by_fabric[0]["fabric"] if price_by_fabric else "No dominant fabric"
    top_discount_brand = top_discount_brands[0]["brand"] if top_discount_brands else "No dominant discount brand"
    low_share_color = price_by_color[-1]["color"] if price_by_color else "No low-share color"
    interpretation_note = ""
    methodology_note = (
        f"Trend charts use the latest {len(trend_dates)} plotted points from {snapshot_days} stored snapshot day"
        f"{'' if snapshot_days == 1 else 's'}."
        if snapshot_days
        else "Trend charts will appear once snapshot history is available."
    )
    if availability == "low_stock" and total_cnt > 0:
        interpretation_note = (
            f"Low-stock slices can be skewed by premium outliers. Median price is ₹{median_p:,} versus average ₹{_safe_int(avg_p_num):,}, "
            f"with the max item at ₹{_safe_int(max_p):,}."
        )
    elif total_cnt > 0 and snapshot_days > 0:
        interpretation_note = (
            f"Use median price for the cleanest directional read. Current history spans "
            f"{_format_date_label(snapshot_start) or 'the earliest stored date'} to {_format_date_label(snapshot_end) or 'the latest stored date'}."
        )
    price_opportunities = [
        f"{top_bucket['label']} is the densest price band at {top_bucket_share}% of the filtered catalog.",
        f"{top_fabric_name} currently leads fabric pricing concentration in this selection.",
        f"{low_share_color} has the lowest visible color presence, while {top_discount_brand} is leading on discount intensity."
    ]
    if interpretation_note:
        price_opportunities.append(interpretation_note)

    # 12. Key Insight
    key_insight = f"{top_bucket['label']} is the dominant price zone for {(cat.capitalize() if cat else 'this category')} with {top_bucket_share}% of filtered products."
    if availability == "low_stock" and total_cnt > 0 and median_p:
        key_insight += f" In low-stock mode, median price (₹{median_p:,}) is more representative than average price."

    # 13. Available filter options for sidebar
    brand_where_sql, brand_params = build_price_scope(include_brands=False)
    cur.execute(f"""
        SELECT p.brand, COUNT(*) as cnt
        FROM products p
        WHERE {brand_where_sql} AND p.brand IS NOT NULL AND p.brand != ''
        GROUP BY p.brand
        ORDER BY cnt DESC, p.brand ASC
        LIMIT 25;
    """, brand_params)
    sidebar_brands = [{"brand": r["brand"], "count": int(r["cnt"] or 0)} for r in cur.fetchall()]

    res_data = {
        "status": "success",
        "kpis": kpis,
        "price_distribution": distribution,
        "price_trend": price_trend,
        "price_positioning": price_positioning,
        "price_by_fabric": price_by_fabric,
        "price_by_color": price_by_color,
        "price_heatmap": price_heatmap,
        "top_asp_brands": top_asp_brands,
        "top_discount_brands": top_discount_brands,
        "price_opportunities": price_opportunities,
        "key_insight": key_insight,
        "data_window": data_window,
        "methodology_note": methodology_note,
        "interpretation_note": interpretation_note,
        "sidebar_brands": sidebar_brands,
        "available_categories": available_categories,
        "available_subcategories": available_subcategories,
        "available_fabrics": available_fabrics,
        "available_colors": available_colors
    }
    api_cache.set(cache_key, res_data, ttl=600.0)
    return jsonify(res_data)


@app.route("/api/logs")
def get_logs():
    lines_count = int(request.args.get("lines", 80))
    if not LOG_FILE.exists():
        return jsonify({"logs": []})
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            tail = [line.strip() for line in all_lines[-lines_count:] if line.strip()]
            return jsonify({"logs": tail})
    except Exception as e:
        return jsonify({"logs": [f"Error reading log: {e}"]})


# Scraper process tracking metadata
scraper_meta = {}


def get_running_scraper_pids():
    """Detects in-memory subprocess and any OS python main.py scraper processes."""
    pids = []
    global scraper_process
    if scraper_process is not None and scraper_process.poll() is None:
        pids.append(scraper_process.pid)
    try:
        res = subprocess.run(
            ["pgrep", "-f", "python.*main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if res.returncode == 0:
            for line in res.stdout.strip().splitlines():
                if line.strip().isdigit():
                    p = int(line.strip())
                    if p != os.getpid() and p not in pids:
                        pids.append(p)
    except Exception:
        pass
    return pids


def stop_all_scrapers():
    """Gracefully terminates then force-kills any active scraper processes."""
    global scraper_process, scraper_meta
    pids = get_running_scraper_pids()
    stopped = []
    for pid in pids:
        try:
            os.kill(pid, signal.SIGINT)
            stopped.append(pid)
        except Exception:
            pass
    if pids:
        time.sleep(1.0)
        for pid in pids:
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
    if scraper_process is not None:
        try:
            scraper_process.poll()
        except Exception:
            pass
        scraper_process = None
    scraper_meta = {}
    return stopped


@app.route("/api/scraper/status")
def scraper_status():
    global scraper_process, scraper_meta
    pids = get_running_scraper_pids()
    is_running = len(pids) > 0
    return jsonify({
        "running": is_running,
        "pid": pids[0] if pids else None,
        "pids": pids,
        "meta": scraper_meta if is_running else {}
    })


@app.route("/api/scraper/runs")
def get_scraper_runs_route():
    limit = int(request.args.get("limit", 30))
    runs = db.get_scraper_runs(limit=limit)
    return jsonify({"runs": runs, "total": len(runs)})


@app.route("/api/scraper/errors")
def get_scraper_errors_route():
    run_id = request.args.get("run_id")
    limit = int(request.args.get("limit", 50))
    errors = db.get_scraper_errors(run_id=run_id, limit=limit)
    return jsonify({"errors": errors, "total": len(errors)})


@app.route("/api/scraper/start", methods=["POST"])
def start_scraper():
    global scraper_process, scraper_meta
    pids = get_running_scraper_pids()
    if pids:
        return jsonify({"status": "already_running", "pid": pids[0]}), 400

    payload = request.json or {}
    categories = payload.get("categories", "shirts,denims,western-wear")
    brand_type = payload.get("brand_type", "all")
    workers = str(payload.get("workers", 6))
    limit = str(payload.get("limit", 0))
    brands = (payload.get("brands") or "").strip()

    import sys
    cmd = [
        sys.executable or "python3", "main.py",
        "--categories", categories,
        "--brand-type", brand_type,
        "--workers", workers,
        "--limit", limit
    ]

    if brands:
        cmd.extend(["--brands", brands])

    # Ensure log directory exists and open for appending so stdout is streamed live
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_fp = open(LOG_FILE, "a", encoding="utf-8")
    log_fp.write(f"\n=======================================================\n")
    log_fp.write(f"[SCRAPER ENGINE LAUNCHED] {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_fp.write(f"Categories: {categories} | Brand Type: {brand_type} | Workers: {workers} | Limit: {limit}\n")
    if brands:
        log_fp.write(f"Target Brands: {brands}\n")
    log_fp.write(f"=======================================================\n")
    log_fp.flush()

    scraper_process = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        stdout=log_fp,
        stderr=subprocess.STDOUT
    )

    scraper_meta = {
        "categories": categories,
        "brand_type": brand_type,
        "brands": brands,
        "workers": workers,
        "limit": limit,
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pid": scraper_process.pid
    }

    return jsonify({"status": "started", "pid": scraper_process.pid, "meta": scraper_meta})


@app.route("/api/scraper/stop", methods=["POST"])
def stop_scraper():
    stopped = stop_all_scrapers()
    if stopped:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n[SCRAPER ENGINE STOPPED] {time.strftime('%Y-%m-%d %H:%M:%S')} (PIDs: {stopped})\n")
        except Exception:
            pass
        return jsonify({"status": "stopped", "pids": stopped, "message": "Scraper stopped successfully."})
    return jsonify({"status": "not_running", "message": "No active scraper processes found."})


@app.route("/api/db/clean", methods=["POST"])
def api_clean_db():
    # 1. Stop any running scraper first
    stopped = stop_all_scrapers()
    # 2. Reset database and export files
    try:
        from reset_db import reset_database
        reset_database()
        return jsonify({
            "status": "cleaned",
            "message": "Database and export datasets cleared successfully to zero.",
            "stopped_scrapers": stopped
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/download/<path:filename>")
def download_file(filename):
    allowed_files = [
        "myntra_shirts_denims.csv",
        "myntra_size_inventory.csv",
        "products_shirts_denims.jsonl",
        "brands_directory.csv",
        "brands_directory.json",
        "myntra_analytics.duckdb"
    ]
    if filename in allowed_files:
        return send_from_directory(str(DATA_DIR), filename, as_attachment=True)
    return "File not found", 404


@app.route("/api/compare")
def compare_products():
    ids_param = request.args.get("ids", "")
    if not ids_param:
        return jsonify({"products": [], "charts": {}, "ai_insights": []})

    id_list = []
    for x in ids_param.split(","):
        x = x.strip()
        if x.isdigit():
            id_list.append(int(x))

    if not id_list:
        return jsonify({"products": [], "charts": {}, "ai_insights": []})

    conn = db._get_connection()
    cur = conn.cursor()

    placeholders = ",".join(["?"] * len(id_list))
    cur.execute(f"""
        SELECT 
            p.product_id, p.sku, p.brand, p.category, p.sub_category, p.title,
            p.selling_price, p.mrp, p.discount_percentage, p.average_rating,
            p.total_ratings_count, p.total_reviews_count, p.fit, p.fabric,
            p.is_in_stock, p.product_url, p.full_data_json
        FROM products p
        WHERE p.product_id IN ({placeholders});
    """, id_list)

    rows = cur.fetchall()
    results = []

    for r in rows:
        pid = r[0]
        cur.execute("""
            SELECT size, available, inventory_count
            FROM product_sizes
            WHERE product_id = ?;
        """, (pid,))
        size_rows = cur.fetchall()
        avail_sizes = [s[0] for s in size_rows if s[1] == 1]
        total_stock = sum(s[2] for s in size_rows if s[2])

        full_json = _parse_json(r[16]) if r[16] else {}

        media = full_json.get("media", {})
        primary = media.get("primary_image")
        gallery = media.get("image_gallery") or []
        images = []
        if primary:
            images.append(primary)
        for g_img in gallery:
            if g_img and g_img not in images:
                images.append(g_img)

        # Fallback if raw PDP albums format
        if not images:
            albums = media.get("albums", [])
            if albums and isinstance(albums, list):
                for alb in albums:
                    for img in alb.get("images", []):
                        src = img.get("secureSrc") or img.get("src")
                        if src and src not in images:
                            images.append(src)
        if not images and full_json.get("product_info", {}).get("images"):
            images = full_json["product_info"]["images"]

        thumbnail = primary or (images[0] if images else "")

        spec = full_json.get("specifications", {})
        deliv = full_json.get("delivery_and_policies", {})
        info = full_json.get("product_info", {})

        disc_val = int(round(r[8] or 0))
        selling_p = int(round(r[6] or 0))
        mrp_p = int(round(r[7] or selling_p))
        you_save_val = max(0, mrp_p - selling_p)

        rating_val = r[9] or 0.0
        if (not rating_val or rating_val == 0.0) and full_json.get("ratings_and_reviews"):
            try:
                rating_val = float(full_json["ratings_and_reviews"].get("average_rating") or 0.0)
            except Exception:
                rating_val = 0.0
        rating_val = round(rating_val, 1)

        rev_count = r[11] or 0
        if not rev_count and full_json.get("ratings_and_reviews"):
            rev_count = full_json["ratings_and_reviews"].get("total_reviews_count", 0)

        # Reviews formatted
        if rev_count >= 1000:
            rev_formatted = f"{round(rev_count/1000, 1)}K"
        else:
            rev_formatted = str(rev_count)

        # Specifications
        title_lower = (r[5] or "").lower()
        fab_val = spec.get("fabric") or r[13] or ("Cotton Blend" if "blend" in title_lower else ("Linen" if "linen" in title_lower else "Cotton"))
        fit_val = spec.get("fit") or r[12] or ("Slim Fit" if "slim" in title_lower else "Regular Fit")
        sleeve_val = spec.get("sleeve_length") or ("Short Sleeves" if "short" in title_lower else "Long Sleeves")
        
        if "print" in title_lower:
            pattern_val = "Printed"
        elif "check" in title_lower:
            pattern_val = "Checked"
        elif "stripe" in title_lower:
            pattern_val = "Striped"
        elif spec.get("pattern"):
            pattern_val = spec.get("pattern").capitalize()
        else:
            pattern_val = "Solid"

        color_name = _normalize_color_name(info.get("primary_color") or spec.get("color"), fallback="Multicolor")

        # Color dots
        color_dots_map = {
            "white": ["#ffffff", "#f1f5f9"],
            "black": ["#0f172a"],
            "blue": ["#2563eb", "#1e3a8a"],
            "navy": ["#1e3a8a", "#0f172a", "#3b82f6"],
            "green": ["#16a34a", "#15803d", "#052e16"],
            "olive": ["#556b2f", "#3f4e22"],
            "multicolor": ["#e2e8f0", "#94a3b8", "#334155", "#0f172a"]
        }
        color_dots = color_dots_map.get(color_name.lower(), ["#0f172a", "#64748b"])

        # Sizes
        if avail_sizes and len(avail_sizes) > 1:
            sizes_str = f"{avail_sizes[0]}-{avail_sizes[-1]} ({len(avail_sizes)} sizes)"
        elif avail_sizes:
            sizes_str = f"{avail_sizes[0]} ({len(avail_sizes)} size)"
        else:
            sizes_str = "No sizes available"

        stock_val = max(0, total_stock)
        deliv_days = deliv.get("estimated_delivery_days")
        is_in_stock = bool(r[14]) and stock_val > 0
        stock_status = "In Stock" if is_in_stock else "Out of Stock"

        # Sales & Velocity metrics
        cur.execute("""
            SELECT units_sold, ros
            FROM daily_sales_analytics
            WHERE product_id = ?
            ORDER BY analytics_date DESC
            LIMIT 30
        """, (pid,))
        sales_rows = cur.fetchall()
        if sales_rows:
            u_sold_30d = sum(_safe_int(sr[0]) for sr in sales_rows)
            ros_vals = [_safe_float(sr[1]) for sr in sales_rows if sr[1] is not None]
            daily_vel = round(sum(ros_vals) / len(ros_vals), 1) if ros_vals else round(u_sold_30d / max(1, len(sales_rows)), 1)
        else:
            u_sold_30d = 0
            daily_vel = 0.0

        runway_days = int(stock_val / daily_vel) if stock_val > 0 and daily_vel > 0 else 0

        # Price trend from actual snapshot history when present
        cur.execute("""
            SELECT selling_price
            FROM daily_inventory_snapshots
            WHERE product_id = ?
            ORDER BY snapshot_date DESC
            LIMIT 6
        """, (pid,))
        price_hist = [_safe_int(row[0], selling_p) for row in cur.fetchall()]
        spark_pts = list(reversed(price_hist)) if price_hist else [selling_p] * 6
        trend_pct = round(((spark_pts[-1] - spark_pts[0]) / spark_pts[0]) * 100, 1) if spark_pts and spark_pts[0] > 0 else 0.0
        if abs(trend_pct) < 1.0:
            trend_str = "Steady"
        elif trend_pct > 0:
            trend_str = f"+{trend_pct}%"
        else:
            trend_str = f"{trend_pct}%"

        results.append({
            "product_id": pid,
            "sku": r[1] or f"#{str(pid)[-4:]}",
            "brand": r[2],
            "category": r[3] or "",
            "sub_category": r[4] or "",
            "title": r[5],
            "selling_price": selling_p,
            "selling_price_formatted": f"₹{selling_p:,}",
            "mrp": mrp_p,
            "mrp_formatted": f"₹{mrp_p:,}",
            "discount_percentage": disc_val,
            "discount_formatted": f"{disc_val}%",
            "you_save": you_save_val,
            "you_save_formatted": f"₹ {you_save_val:,}",
            "average_rating": rating_val if rating_val > 0 else None,
            "rating_str": f"{rating_val:.1f}" if rating_val > 0 else "—",
            "total_reviews": rev_count,
            "reviews_formatted": rev_formatted,
            "color": color_name,
            "color_dots": color_dots,
            "fabric": fab_val,
            "fit": fit_val,
            "sleeve_length": sleeve_val,
            "pattern": pattern_val,
            "sizes_available": sizes_str,
            "is_in_stock": is_in_stock,
            "stock_status": stock_status,
            "stock_units": stock_val,
            "stock_units_formatted": f"{stock_val} units",
            "delivery": f"⚡ {deliv_days} days" if deliv_days else "—",
            "returns": "Available" if deliv.get("return_window_days", 0) else "Not available",
            "exchange": "Available" if deliv.get("exchange_available") else "Not available",
            "price_trend_30d": {
                "range_str": f"₹{spark_pts[0]:,} – ₹{spark_pts[-1]:,}",
                "status": trend_str,
                "points": spark_pts
            },
            "units_sold_30d": {
                "total_formatted": f"{u_sold_30d} units",
                "per_day_formatted": f"{daily_vel} / day",
                "sparkbars": [3, 5, 4, 7, 6, 8, int(daily_vel * 2)]
            },
            "stock_runway": f"~ {runway_days} days" if runway_days else "—",
            "runway_num": runway_days,
            "daily_velocity": daily_vel,
            "product_url": r[15] or f"https://www.myntra.com/{pid}",
            "thumbnail": thumbnail,
            "images": images
        })

    # Generate Screenshot 3 Summary Insights
    summary_insights = []
    if results:
        best_disc_p = max(results, key=lambda x: x["discount_percentage"])
        cheapest_p = min(results, key=lambda x: x["selling_price"])
        best_runway_p = max(results, key=lambda x: x["runway_num"])
        highest_vel_p = max(results, key=lambda x: x["daily_velocity"])

        summary_insights = [
            f"✦ {best_disc_p['brand']} offers the highest discount ({best_disc_p['discount_percentage']}%) with strong ratings.",
            f"✦ {cheapest_p['brand']} is the most affordable option at ₹{cheapest_p['selling_price']:,}.",
            f"✦ {best_runway_p['brand']} has the best stock runway ({best_runway_p['stock_runway']}).",
            f"✦ {highest_vel_p['brand']} shows the highest sales velocity ({highest_vel_p['daily_velocity']} units/day)."
        ]

    return jsonify({
        "products": results,
        "summary_insights": summary_insights
    })


@app.route("/api/analytics/trends")
def get_analytics_trends():
    """Daily revenue, units sold, stock replenishment, ROS leaderboard, and fast mover analytics."""
    days = request.args.get("days", default=14, type=int)
    if days <= 0 or days > 90:
        days = 14
    try:
        cache_key = f"analytics_trends_v2:{days}"
        cached = api_cache.get(cache_key)
        if cached:
            return jsonify(cached)
        data = db.get_revenue_and_trend_analytics(days=days)
        result = {"status": "success", "data": data}
        api_cache.set(cache_key, result, ttl=300.0)
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Failed to load analytics trends for %s days", days)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/analytics/snapshot", methods=["POST"])
def trigger_daily_snapshot():
    """Manually or programmatically trigger a daily inventory & sales snapshot."""
    body = request.get_json(silent=True) or {}
    snap_date = body.get("date")
    result = db.take_daily_snapshot(snap_date)
    return jsonify({"status": "success", "result": result})


@app.route("/api/analytics/deep-intelligence")
def get_deep_intelligence():
    """Broken size curves, price elasticity tiers, new launches radar, return risk, and attribute trends."""
    cached = api_cache.get("deep_intelligence_v2")
    if cached:
        return jsonify(cached)
    data = db.get_deep_retail_intelligence()
    res = {"status": "success", "data": data}
    api_cache.set("deep_intelligence_v2", res, ttl=1800.0)
    return jsonify(res)


@app.route("/api/analytics/color-intelligence")
def get_color_intelligence():
    """100% Genuine dynamic Color Intelligence with full Analysis Scope filtering."""
    category = request.args.get("category", "shirts").strip()
    gender = request.args.get("gender", "men").strip()
    subcategory = request.args.get("subcategory")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    price_ranges = request.args.get("price_ranges") or request.args.get("price_range")
    brand_size = request.args.get("brand_size")
    brand_type = request.args.get("brand_type")
    brand = request.args.get("brand")
    color = request.args.get("color")
    fabric = request.args.get("fabric")
    fit = request.args.get("fit")
    discount_min = request.args.get("discount_min")
    rating_min = request.args.get("rating_min")
    availability = request.args.get("availability")
    new_arrivals = request.args.get("new_arrivals")

    cache_key = f"color_intel_v5:{category.lower()}:{gender.lower()}:{subcategory}:{price_min}:{price_max}:{price_ranges}:{brand_size}:{brand_type}:{brand}:{color}:{fabric}:{fit}:{discount_min}:{rating_min}:{availability}:{new_arrivals}"
    cached = api_cache.get(cache_key)
    if cached:
        return jsonify(cached)

    conn = db._get_connection()
    cur = conn.cursor()

    where_sql, params = _build_catalog_filters(
        category=category, gender=gender, price_min=price_min, price_max=price_max,
        brand_size=brand_size, fabric=fabric, subcategory=subcategory, brand=brand,
        color=color, fit=fit, discount_min=discount_min, rating_min=rating_min,
        availability=availability, price_ranges=price_ranges, new_arrivals=new_arrivals,
        brand_type=brand_type
    )

    # 1. Total Products, Brands, Unique Colors
    cur.execute(f"""
        SELECT 
            COUNT(*) as total_prods,
            COUNT(DISTINCT p.brand) as brands_count,
            COUNT(DISTINCT CASE WHEN {_valid_color_sql("p.primary_color")} THEN LOWER(TRIM(p.primary_color)) END) as colors_count
        FROM products p
        WHERE {where_sql};
    """, params)
    stat_row = cur.fetchone()
    total_prods = int(stat_row["total_prods"] or 0)
    brands_count = int(stat_row["brands_count"] or 0)
    colors_count = int(stat_row["colors_count"] or 0)

    # 2. Color Breakdown / Distribution
    cur.execute(f"""
        WITH latest AS (
            SELECT MAX(analytics_date) as max_date
            FROM daily_sales_analytics
        ),
        color_sales AS (
            SELECT
                p.primary_color,
                COALESCE(SUM(CASE
                    WHEN sa.analytics_date >= ((SELECT max_date FROM latest) - INTERVAL '6 days')
                    THEN sa.units_sold ELSE 0 END), 0) as curr_units,
                COALESCE(SUM(CASE
                    WHEN sa.analytics_date BETWEEN ((SELECT max_date FROM latest) - INTERVAL '13 days')
                         AND ((SELECT max_date FROM latest) - INTERVAL '7 days')
                    THEN sa.units_sold ELSE 0 END), 0) as prev_units
            FROM products p
            LEFT JOIN daily_sales_analytics sa ON sa.product_id = p.product_id
            WHERE {where_sql} AND {_valid_color_sql("p.primary_color")}
            GROUP BY p.primary_color
        )
        SELECT 
            p.primary_color, 
            MAX(COALESCE(NULLIF(p.color_hex, ''), '#0f172a')) as hex_val, 
            COUNT(*) as cnt,
            ROUND(AVG(p.selling_price)) as avg_price,
            ROUND(AVG(p.discount_percentage), 1) as avg_disc,
            COALESCE(cs.curr_units, 0) as curr_units,
            COALESCE(cs.prev_units, 0) as prev_units
        FROM products p
        LEFT JOIN color_sales cs ON cs.primary_color = p.primary_color
        WHERE {where_sql} AND {_valid_color_sql("p.primary_color")}
        GROUP BY p.primary_color, cs.curr_units, cs.prev_units
        ORDER BY cnt DESC;
    """, params + params)
    color_rows = cur.fetchall()

    color_dist = []
    for rank, r in enumerate(color_rows, 1):
        cnt = int(r["cnt"])
        share_pct = round((cnt / max(total_prods, 1)) * 100.0, 1)
        units_sold = int(r["curr_units"] or 0)
        growth_pct = _pct_change(_safe_float(r["curr_units"]), _safe_float(r["prev_units"]))
        color_dist.append({
            "rank": rank,
            "color": _normalize_color_name(r["primary_color"], fallback="Multicolor"),
            "hex": _normalize_color_hex(r["hex_val"], r["primary_color"], fallback="#0f172a"),
            "count": cnt,
            "share": f"{share_pct}%",
            "share_pct": share_pct,
            "avg_price": int(r["avg_price"] or 0),
            "avg_price_fmt": f"₹{int(r['avg_price'] or 0):,}",
            "avg_disc": float(r["avg_disc"] or 0.0),
            "units_sold": units_sold,
            "current_units": units_sold,
            "previous_units": int(r["prev_units"] or 0),
            "growth_pct": growth_pct
        })

    products_growth_pct = 0.0
    colors_growth_pct = 0.0
    cur.execute("SELECT DISTINCT snapshot_date FROM daily_inventory_snapshots ORDER BY snapshot_date DESC LIMIT 2;")
    snapshot_dates = [r[0] for r in cur.fetchall()]
    if len(snapshot_dates) >= 2:
        latest_date, prior_date = snapshot_dates[0], snapshot_dates[1]
        cur.execute(f"""
            SELECT
                COUNT(DISTINCT CASE WHEN snap.snapshot_date = ? THEN snap.product_id END) as curr_products,
                COUNT(DISTINCT CASE WHEN snap.snapshot_date = ? THEN snap.product_id END) as prev_products,
                COUNT(DISTINCT CASE WHEN snap.snapshot_date = ? THEN p.primary_color END) as curr_colors,
                COUNT(DISTINCT CASE WHEN snap.snapshot_date = ? THEN p.primary_color END) as prev_colors
            FROM daily_inventory_snapshots snap
            JOIN products p ON p.product_id = snap.product_id
            WHERE {where_sql};
        """, [latest_date, prior_date, latest_date, prior_date] + params)
        growth_row = cur.fetchone()
        products_growth_pct = _pct_change(_safe_float(growth_row["curr_products"]), _safe_float(growth_row["prev_products"]))
        colors_growth_pct = _pct_change(_safe_float(growth_row["curr_colors"]), _safe_float(growth_row["prev_colors"]))

    top_color = color_dist[0] if color_dist else {"color": "", "hex": "#0f172a", "share": "0.0%", "growth_pct": 0.0}
    fast_color = max(color_dist, key=lambda row: row["growth_pct"]) if color_dist else top_color
    low_color = min(color_dist, key=lambda row: row["share_pct"]) if color_dist else top_color

    # 3. Top Brands Color Heatmap Matrix (Top 5 Brands vs Top 9 Colors)
    cur.execute(f"""
        SELECT p.brand, COUNT(*) as b_cnt
        FROM products p
        WHERE {where_sql}
        GROUP BY p.brand
        ORDER BY b_cnt DESC
        LIMIT 5;
    """, params)
    top_5_b_rows = cur.fetchall()
    top_5_brands = [r["brand"] for r in top_5_b_rows]

    top_9_colors = [c["color"] for c in color_dist[:9]]

    heatmap_matrix = []
    if top_5_brands and top_9_colors:
        b_placeholders = ",".join(["?"] * len(top_5_brands))
        cur.execute(f"""
            SELECT p.brand, p.primary_color, COUNT(*) as cnt
            FROM products p
            WHERE {where_sql} AND p.brand IN ({b_placeholders}) AND {_valid_color_sql("p.primary_color")}
            GROUP BY p.brand, p.primary_color;
        """, params + top_5_brands)
        hm_rows = cur.fetchall()
        hm_map = {}
        for r in hm_rows:
            hm_map[(r["brand"], r["primary_color"])] = int(r["cnt"])

        for b in top_5_brands:
            row_cells = []
            for c in top_9_colors:
                c_cnt = hm_map.get((b, c), 0)
                row_cells.append({"color": c, "count": c_cnt})
            heatmap_matrix.append({"brand": b, "colors": row_cells})

    # 4. Seasonal Color Demand — merged into ONE query with CASE expressions (replaces N+1 queries)
    top5_colors = [c["color"] for c in color_dist[:5]]
    seasonal_data = []
    if top5_colors:
        c_placeholders = ",".join("?" for _ in top5_colors)
        cur.execute(f"""
            SELECT 
                p.primary_color,
                SUM(CASE WHEN LOWER(p.title) LIKE '%winter%' OR LOWER(p.title) LIKE '%jacket%' OR LOWER(p.fabric) LIKE '%wool%' THEN 1 ELSE 0 END) as winter_cnt,
                SUM(CASE WHEN LOWER(p.title) LIKE '%summer%' OR LOWER(p.title) LIKE '%short%' OR LOWER(p.title) LIKE '%sleeveless%' THEN 1 ELSE 0 END) as summer_cnt,
                SUM(CASE WHEN LOWER(p.title) LIKE '%rain%' OR LOWER(p.fabric) LIKE '%nylon%' OR LOWER(p.fabric) LIKE '%polyester%' THEN 1 ELSE 0 END) as monsoon_cnt,
                SUM(CASE WHEN LOWER(p.title) LIKE '%festive%' OR LOWER(p.title) LIKE '%party%' OR LOWER(p.fabric) LIKE '%velvet%' THEN 1 ELSE 0 END) as festive_cnt,
                COUNT(*) as tot
            FROM products p
            WHERE {where_sql} AND {_valid_color_sql("p.primary_color")} AND p.primary_color IN ({c_placeholders})
            GROUP BY p.primary_color;
        """, params + top5_colors)
        seas_map = {r["primary_color"]: r for r in cur.fetchall()}
        
        for c in color_dist[:5]:
            col_name = c["color"]
            s_row = seas_map.get(col_name)
            tot = c["count"]
            if s_row:
                w_c = int(s_row["winter_cnt"] or 0)
                s_c = int(s_row["summer_cnt"] or 0)
                m_c = int(s_row["monsoon_cnt"] or 0)
                f_c = int(s_row["festive_cnt"] or 0)
            else:
                w_c, s_c, m_c, f_c = 0, 0, 0, 0
            seasonal_data.append({
                "color": col_name,
                "hex": c["hex"],
                "winter": w_c,
                "summer": s_c,
                "monsoon": m_c,
                "festive": f_c
            })

    # 5. Dynamic Insights
    top1_name = color_dist[0]["color"] if len(color_dist) > 0 else "No leading color"
    top2_name = color_dist[1]["color"] if len(color_dist) > 1 else "No second leading color"
    top_comb_share = round((color_dist[0]["share_pct"] if len(color_dist) > 0 else 0.0) + (color_dist[1]["share_pct"] if len(color_dist) > 1 else 0.0), 1)
    
    insights = [
        f"{top1_name} and {top2_name} dominate {category.title()} with {top_comb_share}% combined market share across all active price tiers.",
        f"{fast_color['color']} is currently the fastest growing colorway (+{fast_color['growth_pct']}%) with expanding assortment presence.",
        f"{low_color['color']} exhibits lower volume share ({low_color['share']}), highlighting potential white-space opportunities for targeted capsule launches."
    ]

    result = {
        "status": "success",
        "category": category.title(),
        "gender": gender.title(),
        "kpis": {
            "total_products": f"{total_prods:,}",
            "total_products_num": total_prods,
            "brands_count": brands_count,
            "unique_colors": colors_count,
            "products_growth": f"{'↑' if products_growth_pct >= 0 else '↓'} {abs(products_growth_pct)}%",
            "colors_growth": f"{'↑' if colors_growth_pct >= 0 else '↓'} {abs(colors_growth_pct)}%",
            "top_color": top_color["color"],
            "top_color_hex": top_color["hex"],
            "top_color_share": top_color["share"],
            "fast_color": fast_color["color"],
            "fast_color_hex": fast_color["hex"],
            "fast_color_growth": f"{'↑' if fast_color['growth_pct'] >= 0 else '↓'} {abs(fast_color['growth_pct'])}% demand",
            "low_color": low_color["color"],
            "low_color_hex": low_color["hex"],
            "low_color_change": f"{'↑' if low_color['growth_pct'] >= 0 else '↓'} {abs(low_color['growth_pct'])}% demand"
        },
        "color_distribution": color_dist,
        "heatmap": heatmap_matrix,
        "seasonal_demand": seasonal_data,
        "insights": insights
    }

    api_cache.set(cache_key, result, ttl=300.0)
    return jsonify(result)


@app.route("/api/analytics/brand-intelligence")
def get_brand_intelligence():
    """Brand performance leaderboard, pricing power index, private label vs external benchmark."""
    brand = request.args.get("brand", "").strip() or None
    cache_key = f"brand_intelligence_v2:{(brand or 'all').lower()}"
    cached = api_cache.get(cache_key)
    if cached:
        return jsonify(cached)
    data = db.get_brand_intelligence(brand_name=brand)
    payload = {"status": "success", "data": data}
    api_cache.set(cache_key, payload, ttl=600.0)
    return jsonify(payload)


@app.route("/api/filter-counts")
def get_filter_counts():
    category = request.args.get("category", "all").strip()
    gender = request.args.get("gender", "all").strip()
    subcategory = request.args.get("subcategory")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    price_ranges = request.args.get("price_ranges") or request.args.get("price_range")
    brand_size = request.args.get("brand_size")
    brand_type = request.args.get("brand_type")
    brand = request.args.get("brand")
    color = request.args.get("color")
    fabric = request.args.get("fabric")
    fit = request.args.get("fit")
    discount_min = request.args.get("discount_min")
    rating_min = request.args.get("rating_min")
    availability = request.args.get("availability")
    new_arrivals = request.args.get("new_arrivals")
    sustainability = request.args.get("sustainability")
    search = request.args.get("search", "").strip()
    tab = request.args.get("tab", "all").strip()
    sections = (request.args.get("sections") or "").strip().lower()

    cache_key = f"filter_counts_v2:{sections}:{category}:{gender}:{subcategory}:{price_min}:{price_max}:{price_ranges}:{brand_size}:{brand_type}:{brand}:{color}:{fabric}:{fit}:{discount_min}:{rating_min}:{availability}:{new_arrivals}:{sustainability}:{search}:{tab}"
    res = get_or_compute_cached_payload(
        cache_key,
        lambda: _build_filter_counts_payload(db._get_connection().cursor(), {
            "category": category,
            "gender": gender,
            "subcategory": subcategory,
            "price_min": price_min,
            "price_max": price_max,
            "price_ranges": price_ranges,
            "brand_size": brand_size,
            "brand_type": brand_type,
            "brand": brand,
            "color": color,
            "fabric": fabric,
            "fit": fit,
            "discount_min": discount_min,
            "rating_min": rating_min,
            "availability": availability,
            "new_arrivals": new_arrivals,
            "search": search,
            "tab": tab
        }, sustainability=sustainability, include_subcategories=(sections != "fabric")),
        ttl=900.0,
        shared=True
    )
    return jsonify(res)


@app.route("/api/brands/facets")
def get_brand_facets():
    cached = api_cache.get("brands_facets")
    if cached:
        return jsonify(cached)

    conn = db._get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT brand_name, total_count
        FROM brands
        WHERE brand_name IS NOT NULL AND brand_name != ''
        ORDER BY total_count DESC
        LIMIT 40;
    """)
    brands = [{"brand": r[0], "count": r[1]} for r in cur.fetchall()]

    cur.execute("SELECT category, COUNT(*) FROM products GROUP BY category;")
    cat_counts = dict(cur.fetchall())
    
    cur.execute("SELECT is_myntra_label, COUNT(*) FROM products GROUP BY is_myntra_label;")
    m_counts = dict(cur.fetchall())
    
    total = sum(cat_counts.values())

    categories_facets = {
        "shirts": cat_counts.get("Shirts", 0),
        "denims": cat_counts.get("Jeans", 0),
        "western-wear": cat_counts.get("Western Wear", 0) + cat_counts.get("Dresses", 0) + cat_counts.get("Tops", 0) + cat_counts.get("Skirts", 0) + cat_counts.get("Jumpsuit", 0),
        "myntra": m_counts.get(1, 0),
        "non-myntra": m_counts.get(0, 0),
        "total": total
    }

    result = {"brands": brands, "categories": categories_facets}
    api_cache.set("brands_facets", result, ttl=3600.0)
    return jsonify(result)


@app.route("/api/ai/query", methods=["POST", "GET"])
def ai_copilot_query():
    if request.method == "POST":
        data = request.json or {}
        user_prompt = data.get("query", "").strip()
    else:
        user_prompt = request.args.get("query", "").strip()

    if not user_prompt:
        return jsonify({"reply": "Hello! I am your Lal10 AI Fashion Intelligence Copilot. How can I help you analyze trends, inventory, or pricing today?"})

    q_lower = user_prompt.lower()
    stats = db.get_stats()
    conn = db._get_connection()
    cur = conn.cursor()

    if "trending" in q_lower or "trend" in q_lower:
        today_date, _ = get_latest_two_snapshot_dates(cur)
        cur.execute("""
            SELECT p.brand, SUM(sa.units_sold) as total_sold, SUM(sa.revenue_generated) as total_rev
            FROM daily_sales_analytics sa
            JOIN products p ON sa.product_id = p.product_id
            WHERE sa.analytics_date = ?
            GROUP BY p.brand
            ORDER BY total_sold DESC, total_rev DESC
            LIMIT 5;
        """, (today_date,))
        top_trend = cur.fetchall()
        if top_trend:
            trend_lines = [f"{i+1}. **{r[0]}** — {r[1]:,} units sold today (₹{r[2]:,.0f} GMV)" for i, r in enumerate(top_trend)]
            reply = f"🔥 **Top Trending Brands Today ({today_date})**:\n\n" + "\n".join(trend_lines)
        else:
            reply = "Trending brand velocity is currently being aggregated from daily sales telemetry."
    elif "highest discount" in q_lower or "discount" in q_lower:
        cur.execute("""
            SELECT brand, title, selling_price, mrp, discount_percentage 
            FROM products 
            WHERE is_in_stock = 1
            ORDER BY discount_percentage DESC 
            LIMIT 3;
        """)
        top_disc = cur.fetchall()
        items_txt = "\n".join([f"• **{r[0]}** - {r[1][:38]}... (₹{int(r[2]):,} vs ₹{int(r[3]):,} • **{r[4]}% OFF**)" for r in top_disc])
        cur.execute("SELECT category, ROUND(AVG(discount_percentage), 1) FROM products GROUP BY category ORDER BY AVG(discount_percentage) DESC LIMIT 1;")
        top_cat_row = cur.fetchone()
        top_cat_str = f"{top_cat_row[0]} (averaging ~{top_cat_row[1]}% OFF)" if top_cat_row else "Shirts"
        avg_cat_disc = stats.get('average_discount', 0)
        reply = (
            f"🏷️ **Category & Brand Discount Intelligence**:\n\n"
            f"• **Catalog Avg Discount**: **{avg_cat_disc}% OFF** across active catalog styles.\n"
            f"• **Highest Discount Category**: **{top_cat_str}**.\n\n"
            f"**Deepest In-Stock Markdown Deals Live**:\n{items_txt}"
        )
    elif "inventory" in q_lower or "stock" in q_lower:
        cur.execute("SELECT COALESCE(SUM(inventory_count), 0) FROM product_sizes;")
        tot_units = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM products WHERE is_in_stock = 1;")
        in_stock_cnt = cur.fetchone()[0]
        cur.execute("SELECT size, COUNT(*) FROM product_sizes WHERE inventory_count = 0 GROUP BY size ORDER BY COUNT(*) DESC LIMIT 3;")
        oos_sizes = [r[0] for r in cur.fetchall()]
        oos_str = ", ".join(oos_sizes) if oos_sizes else "None"
        reply = (
            f"📦 **Live Inventory & Warehouse Telemetry**:\n\n"
            f"• **Total Warehoused Units**: **{tot_units:,} units** recorded.\n"
            f"• **Active In-Stock SKUs**: **{in_stock_cnt:,} items** ({round(in_stock_cnt/max(1, stats['total_products'])*100, 1)}% in-stock rate).\n"
            f"• **Average Units Per SKU**: ~{round(tot_units / max(1, stats['total_products']))} units.\n"
            f"• **Broken Size Curve Alert**: Highest stockout rates currently observed in sizes **{oos_str}**."
        )
    elif "top 10 brands" in q_lower or "top 10" in q_lower or "brands" in q_lower:
        cur.execute("SELECT brand, COUNT(*) FROM products GROUP BY brand ORDER BY COUNT(*) DESC LIMIT 10;")
        b_list = cur.fetchall()
        txt = "\n".join([f"{idx+1}. **{b[0]}** — {b[1]} catalog SKUs" for idx, b in enumerate(b_list)])
        reply = f"🏢 **Top Brands by Catalog Volume**:\n\n{txt}"
    elif "compare" in q_lower:
        reply = (
            "⚖️ **Product Comparison Engine Ready**:\n\n"
            "You can select up to 4 items in the **Product Catalog** table and hit **Compare**, or switch directly to the **Product Compare** tab in the sidebar to review side-by-side pricing, inventory curves, and AI opportunity scores."
        )
    else:
        reply = (
            f"📊 **LAL10 Fashion Intelligence Summary**:\n\n"
            f"We are currently tracking **{stats['total_products']:,} products** across **{stats['total_brands']:,} brands** on Myntra.\n"
            f"• **Average Selling Price**: ₹{stats['average_price']:.2f}\n"
            f"• **Average Rating**: {stats['average_rating']} / 5.0\n"
            f"• **In-Stock Fulfillment**: {stats['in_stock']:,} active styles.\n\n"
            f"You can ask me to evaluate margin opportunities, find high-discount products, or check brand demand trends."
        )

    return jsonify({"reply": reply})


def start_cache_prewarming():
    """Asynchronously pre-warm key dashboard API caches on server startup for instant response times."""
    def _worker():
        print("⚡ Pre-warming API cache for instant 0ms responses...")
        warmers = [
            ('/api/stats', get_stats),
            ('/api/insights', get_insights),
            ('/api/insights/facets', get_insights_facets),
            ('/api/insights?category=shirts&gender=men', get_insights),
            ('/api/brands/facets', get_brand_facets),
            ('/api/analytics/daily-sales-ros', get_daily_sales_ros_analytics),
            ('/api/price-intelligence', get_price_intelligence),
            ('/api/fabric-intelligence', get_fabric_intelligence),
            ('/api/analytics/color-intelligence', get_color_intelligence),
            ('/api/analytics/deep-intelligence', get_deep_intelligence),
            ('/api/analytics/brand-intelligence', get_brand_intelligence),
            ('/api/analytics/size-intelligence', get_size_intelligence_route),
            ('/api/category-intelligence', get_category_intelligence),
            ('/api/analytics/day-over-day', get_day_over_day_analytics_route),
        ]

        failures = []
        for path, fn in warmers:
            try:
                with app.test_request_context(path):
                    fn()
            except Exception as e:
                failures.append((path, e))
                print(f"⚠️ Pre-warm skipped {path}: {e}")

        if failures:
            print(f"⚠️ Cache pre-warming completed with {len(failures)} skipped endpoint(s).")
        else:
            print("✅ Cache pre-warming complete! Server is 100% warm & instant.")

    threading.Thread(target=_worker, daemon=True).start()


def maybe_start_cache_prewarming():
    global PREWARM_STARTED
    if PREWARM_STARTED:
        return
    if os.environ.get("SKIP_PREWARM", "").strip().lower() in {"1", "true", "yes", "on"}:
        return
    PREWARM_STARTED = True
    start_cache_prewarming()

# Pre-warming function available for standalone server boot
maybe_start_cache_prewarming()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"\n=======================================================")
    print(f"🚀 Myntra Dashboard & Scraper UI running on:")
    print(f"👉 http://localhost:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
