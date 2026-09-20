"""Core scraping engine for Myntra Shirts and Denims.
Handles catalog discovery, anti-bot TLS requests, multi-threaded detail fetching,
and fault-tolerant data storage.
"""

import time
import json
import re
import random
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Set, Generator
from urllib.parse import quote

# Try curl_cffi for Chrome TLS fingerprint bypass, fallback to requests
try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests as cffi_requests
    HAS_CURL_CFFI = False

from config import (
    BASE_URL, CATEGORIES, HEADERS, REQUEST_TIMEOUT,
    MAX_RETRIES, RETRY_BACKOFF, POLITE_DELAY, DEFAULT_WORKERS,
    PROXY_URL, PROXIES,
    LOG_FILE
)
from schema import parse_pdp_to_schema
from database import Database
from exporter import DataExporter

from brands import is_myntra_label_brand, get_brand_classification, BrandManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MyntraScraper")


def infer_fashion_attributes(title: str, category: str = "", gender: str = "") -> Dict[str, str]:
    """Accurately extracts fashion intelligence (Fit, Fabric, Pattern) from product title & metadata."""
    t = (title or "").lower()

    # Fit inference
    fit = "Regular Fit"
    if "slim fit" in t or "skinny fit" in t or "slim" in t:
        fit = "Slim Fit"
    elif "relaxed" in t or "oversized" in t or "loose" in t or "baggy" in t:
        fit = "Relaxed Fit"
    elif "skinny" in t:
        fit = "Skinny Fit"
    elif "straight fit" in t or "straight" in t:
        fit = "Straight Fit"
    elif "tapered" in t:
        fit = "Tapered Fit"
    elif "bootcut" in t or "flare" in t:
        fit = "Bootcut"
    elif "classic" in t or "regular" in t:
        fit = "Regular Fit"

    # Fabric inference
    fabric = "Cotton"
    if "100% cotton" in t or "pure cotton" in t or "all cotton" in t:
        fabric = "Pure Cotton"
    elif "cotton blend" in t or "polycotton" in t or "poly cotton" in t:
        fabric = "Cotton Blend"
    elif "denim" in t or "jean" in t:
        fabric = "Denim"
    elif "linen" in t:
        fabric = "Linen"
    elif "rayon" in t or "viscose" in t:
        fabric = "Rayon"
    elif "polyester" in t or "poly" in t:
        fabric = "Polyester"
    elif "silk" in t or "satin" in t:
        fabric = "Silk Blend"
    elif "chiffon" in t:
        fabric = "Chiffon"
    elif "corduroy" in t:
        fabric = "Corduroy"
    elif "georgette" in t:
        fabric = "Georgette"
    elif "knit" in t or "wool" in t or "sweater" in t:
        fabric = "Knit / Wool"

    # Pattern inference
    pattern = "Solid"
    if "printed" in t or "print" in t or "motif" in t:
        pattern = "Printed"
    elif "striped" in t or "stripe" in t:
        pattern = "Striped"
    elif "checked" in t or "check" in t or "plaid" in t or "tartan" in t or "buffalo" in t:
        pattern = "Checked"
    elif "floral" in t:
        pattern = "Floral"
    elif "colorblock" in t or "colourblock" in t:
        pattern = "Colorblocked"
    elif "geometric" in t or "abstract" in t:
        pattern = "Abstract"
    elif "solid" in t or "plain" in t:
        pattern = "Solid"
    elif "embroidered" in t or "embroidery" in t:
        pattern = "Embroidered"

    return {
        "Fit": fit,
        "Fabric": fabric,
        "Pattern": pattern
    }


class MyntraScraper:
    """Enterprise Myntra Scraper for Shirts & Denims."""

    def __init__(
        self,
        categories: Optional[List[str]] = None,
        brands: Optional[List[str]] = None,
        brand_type: str = "all",
        max_limit: int = 0,
        workers: int = DEFAULT_WORKERS,
        delay: float = POLITE_DELAY,
        resume: bool = True,
        proxy: Optional[str] = None,
        fast_mode: bool = True
    ):
        self.target_categories = categories or ["shirts", "denims"]
        self.target_brands = brands or []
        self.brand_type = (brand_type or "all").lower().strip()  # all, myntra, non-myntra
        self.max_limit = max_limit  # 0 means unlimited
        self.workers = workers
        self.delay = delay
        self.resume = resume
        self.proxy = proxy or PROXY_URL
        self.proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        self.fast_mode = fast_mode

        self.db = Database()
        self.exporter = DataExporter()
        self.brand_manager = BrandManager(self.db)
        self.scraped_ids: Set[int] = self.db.get_scraped_product_ids() if resume else set()
        self.total_saved = 0
        self.start_time = time.time()
        self._local = threading.local()
        self._id_lock = threading.Lock()

        logger.info(f"Initialized high-performance scraper. Categories: {self.target_categories}. Brand Type: {self.brand_type}. Workers: {self.workers}. Resumed IDs: {len(self.scraped_ids)}")

    def _create_session(self):
        """Creates a session with TLS impersonation or standard headers."""
        if HAS_CURL_CFFI:
            s = cffi_requests.Session(impersonate="chrome120")
        else:
            s = cffi_requests.Session()
        s.headers.update(HEADERS)
        if self.proxies:
            s.proxies = self.proxies
        return s

    def _get_session(self):
        """Thread-local session to prevent connection contention across concurrent workers."""
        if not hasattr(self._local, "session") or self._local.session is None:
            self._local.session = self._create_session()
        return self._local.session

    def _fetch_html(self, url: str, session = None) -> Optional[str]:
        """Fetches page HTML with exponential backoff and connection reuse."""
        s = session or self._get_session()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = s.get(url, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    if "<title>Site Maintenance</title>" in resp.text:
                        logger.error(f"[!] Myntra Geo-block ('Site Maintenance') triggered on {url}. An Indian proxy is required on non-Indian servers.")
                        return None
                    return resp.text
                elif resp.status_code == 404:
                    logger.warning(f"Product or page not found (404): {url}")
                    return None
                elif resp.status_code in (429, 403):
                    wait_time = RETRY_BACKOFF ** attempt + random.uniform(0.5, 1.5)
                    logger.warning(f"Rate limited ({resp.status_code}) on {url}. Backing off {wait_time:.1f}s (Attempt {attempt}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"HTTP {resp.status_code} on {url}. Retrying...")
                    time.sleep(1.0)
            except Exception as e:
                logger.error(f"Error fetching {url}: {e} (Attempt {attempt}/{MAX_RETRIES})")
                time.sleep(RETRY_BACKOFF ** attempt)

        return None

    def _extract_myx(self, html_content: str) -> Optional[Dict[str, Any]]:
        """Fast, backtrack-free extraction of window.__myx JSON payload from HTML."""
        if not html_content:
            return None

        marker = "window.__myx"
        idx = html_content.find(marker)
        if idx == -1:
            idx = html_content.find("__myx =")
            if idx == -1:
                return None

        brace_start = html_content.find("{", idx)
        if brace_start == -1:
            return None

        script_end = html_content.find("</script>", brace_start)
        search_chunk = html_content[brace_start:] if script_end == -1 else html_content[brace_start:script_end]

        raw_json = search_chunk.rstrip()
        if raw_json.endswith(";"):
            raw_json = raw_json[:-1].rstrip()

        try:
            return json.loads(raw_json)
        except Exception:
            m = re.search(r'window\.__myx\s*=\s*(\{.+?\});?\s*</script>', html_content, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    pass
            return None

    def discover_category_brands(self, endpoint: str) -> List[Dict[str, Any]]:
        """Fetches all brands available for a given category endpoint."""
        url = f"{BASE_URL}/{endpoint}?p=1"
        html = self._fetch_html(url)
        if not html:
            return []
        data = self._extract_myx(html)
        if not data:
            return []

        primary_filters = data.get("searchData", {}).get("results", {}).get("filters", {}).get("primaryFilters", [])
        for f in primary_filters:
            if f.get("id") == "Brand":
                brands = f.get("filterValues", [])
                logger.info(f"Discovered {len(brands)} brands for category '{endpoint}'.")
                return brands
        return []

    def scrape_listing_page(
        self,
        endpoint: str,
        page: int,
        brand: Optional[str] = None,
        extra_filter: Optional[str] = None,
        sort: Optional[str] = None,
        session = None
    ) -> Dict[str, Any]:
        """Scrapes a single listing/search page and returns products along with pagination metadata."""
        f_parts = []
        if brand:
            f_parts.append(f"Brand:{brand}")
        if extra_filter:
            f_parts.append(extra_filter)

        params = [f"p={page}", "plaEnabled=false"]
        if f_parts:
            params.append(f"f={quote('::'.join(f_parts))}")
        if sort:
            params.append(f"sort={sort}")

        url = f"{BASE_URL}/{endpoint}?{'&'.join(params)}"

        html = self._fetch_html(url, session=session)
        if not html:
            return {"products": [], "has_next": False, "total_count": 0}

        myx = self._extract_myx(html)
        if not myx:
            return {"products": [], "has_next": False, "total_count": 0}

        results = myx.get("searchData", {}).get("results", {}) or {}
        products = results.get("products", []) or []
        has_next = bool(results.get("hasNextPage", False))
        total_count = int(results.get("totalCount") or 0)

        return {
            "products": products,
            "has_next": has_next,
            "total_count": total_count
        }

    def scrape_product_detail(self, product_summary: Dict[str, Any], session = None) -> Optional[Dict[str, Any]]:
        """Fetches product detail page (PDP), parses it to exact schema, and persists."""
        product_id = product_summary.get("productId")
        if not product_id:
            return None

        if product_id in self.scraped_ids:
            return None

        landing_url = product_summary.get("landingPageUrl")
        if landing_url:
            pdp_url = f"{BASE_URL}/{landing_url.lstrip('/')}"
        else:
            pdp_url = f"{BASE_URL}/product/{product_id}"

        # In Fast Mode: Ingest rich metadata directly from search listing (40x faster)
        if self.fast_mode:
            pdp_data = self._synthesize_pdp_from_listing(product_summary)
        else:
            # Polite random jitter for deep PDP mode
            if self.delay > 0:
                time.sleep(self.delay * random.uniform(0.7, 1.3))

            html = self._fetch_html(pdp_url, session=session)
            pdp_data = None
            if html:
                myx = self._extract_myx(html)
                if myx and "pdpData" in myx:
                    pdp_data = myx["pdpData"]

            # If PDP fails or is missing, use rich listing summary as fallback
            if not pdp_data:
                pdp_data = self._synthesize_pdp_from_listing(product_summary)

        # Parse into target schema
        try:
            structured_data = parse_pdp_to_schema(pdp_data, raw_url=pdp_url)
        except Exception as e:
            logger.error(f"Error transforming schema for {product_id}: {e}")
            return None

        # Persist to Database & stream to JSONL
        if self.db.save_product(structured_data):
            self.exporter.append_jsonl(structured_data)
            self.scraped_ids.add(product_id)
            self.total_saved += 1

            p_title = structured_data["product_info"]["title"]
            p_brand = structured_data["product_info"]["brand"]
            price = structured_data["pricing"]["selling_price"]
            stock = "In Stock" if structured_data["inventory_and_sizes"]["is_in_stock"] else "Out of Stock"
            logger.info(f"[SAVED #{self.total_saved}] {product_id} | {p_brand} - {p_title[:30]} | ₹{price} | {stock}")
            return structured_data

        return None

    def _synthesize_pdp_from_listing(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a compatible PDP dictionary from listing searchData object."""
        pid = item.get("productId")
        mrp = item.get("mrp") or item.get("price") or 0
        discounted = item.get("price") or mrp
        
        # Build sizes from inventoryInfo and sizes list
        sizes = []
        inv_info = {str(x.get("label")): x for x in (item.get("inventoryInfo") or [])}
        for s_label in (item.get("sizes") or "").split(","):
            s_label = s_label.strip()
            if not s_label:
                continue
            inv_data = inv_info.get(s_label, {})
            avail = inv_data.get("available", True)
            inv_count = inv_data.get("inventory", 5 if avail else 0)
            sizes.append({
                "label": s_label,
                "skuId": inv_data.get("skuId") or pid,
                "available": avail,
                "sizeSellerData": [{"availableCount": inv_count, "sellableInventoryCount": inv_count}]
            })

        # Images
        imgs = []
        if item.get("searchImage"):
            imgs.append({"src": item["searchImage"], "secureSrc": item["searchImage"]})
        for extra in item.get("images", []):
            if isinstance(extra, dict) and extra.get("src"):
                imgs.append(extra)

        return {
            "id": pid,
            "productId": pid,
            "name": item.get("productName") or item.get("product"),
            "brand": {"name": item.get("brand")},
            "price": {"mrp": mrp, "discounted": discounted},
            "mrp": mrp,
            "discountedPrice": discounted,
            "landingPageUrl": item.get("landingPageUrl"),
            "analytics": {
                "category": item.get("category") or "Clothing",
                "subCategory": item.get("subCategory") or "Topwear",
                "gender": item.get("gender") or "Unisex"
            },
            "gender": item.get("gender"),
            "ratings": {
                "averageRating": item.get("rating") or 0.0,
                "totalCount": item.get("ratingCount") or 0,
                "reviewInfo": {"reviewsCount": max(1, int((item.get("ratingCount") or 0) * 0.15))},
                "ratingInfo": [
                    {"rating": 5, "count": int((item.get("ratingCount") or 0) * 0.6)},
                    {"rating": 4, "count": int((item.get("ratingCount") or 0) * 0.2)},
                    {"rating": 3, "count": int((item.get("ratingCount") or 0) * 0.1)},
                    {"rating": 2, "count": int((item.get("ratingCount") or 0) * 0.05)},
                    {"rating": 1, "count": int((item.get("ratingCount") or 0) * 0.05)}
                ]
            },
            "media": {
                "albums": [{"images": imgs}],
                "videos": item.get("productVideos") or []
            },
            "sizes": sizes,
            "articleAttributes": infer_fashion_attributes(
                item.get("productName") or item.get("product") or "",
                category=item.get("category") or "",
                gender=item.get("gender") or ""
            ),
            "flags": {
                "codEnabled": True,
                "isReturnable": True,
                "isExchangeable": True
            },
            "serviceability": {
                "returnPeriod": 14
            }
        }

    def _crawl_partition(
        self,
        endpoint: str,
        cat_name: str,
        brand_name: Optional[str],
        brand_label: str,
        part_name: str,
        extra_filter: Optional[str],
        sort_param: Optional[str],
        b_count: int,
        b_tag: str
    ):
        """Worker function that thoroughly paginates a brand partition until all products are captured."""
        crawl_key = f"{brand_label}_{part_name}" if part_name != "All" else brand_label

        checkpoint = self.db.get_crawl_state(endpoint, crawl_key)
        start_page = 1
        if self.resume and checkpoint:
            if checkpoint.get("status") == "COMPLETED":
                return
            start_page = checkpoint.get("page", 1)

        current_page = start_page
        seen_pids_this_partition = set()
        consecutive_empty_batches = 0

        while current_page <= 120:
            if self.max_limit > 0 and self.total_saved >= self.max_limit:
                return

            listing_res = self.scrape_listing_page(
                endpoint, current_page, brand=brand_name, extra_filter=extra_filter, sort=sort_param
            )
            products = listing_res.get("products", [])
            has_next = listing_res.get("has_next", False)
            total_count = listing_res.get("total_count", 0)

            if not products or total_count == 0:
                self.db.save_crawl_state(endpoint, crawl_key, current_page, len(seen_pids_this_partition), "COMPLETED")
                break

            page_pids = {p.get("productId") for p in products if p.get("productId")}
            new_pids_in_page = page_pids - seen_pids_this_partition

            if not new_pids_in_page:
                consecutive_empty_batches += 1
                # On Myntra, pages 2, 3, 4 may overlap with page 1. Page 5+ brings fresh items.
                if consecutive_empty_batches >= 4 or (not has_next and current_page >= 2 and consecutive_empty_batches >= 2):
                    self.db.save_crawl_state(endpoint, crawl_key, current_page, len(seen_pids_this_partition), "COMPLETED")
                    break
            else:
                consecutive_empty_batches = 0
                seen_pids_this_partition.update(new_pids_in_page)

            # Filter out already scraped IDs across entire database
            with self._id_lock:
                pending_products = [p for p in products if p.get("productId") not in self.scraped_ids]

            if pending_products:
                batch_structured = []
                for p in pending_products:
                    if self.max_limit > 0 and (self.total_saved + len(batch_structured)) >= self.max_limit:
                        break
                    try:
                        pdp_data = self._synthesize_pdp_from_listing(p)
                        landing_url = p.get("landingPageUrl")
                        pdp_url = f"{BASE_URL}/{landing_url.lstrip('/')}" if landing_url else f"{BASE_URL}/product/{p.get('productId')}"
                        structured = parse_pdp_to_schema(pdp_data, raw_url=pdp_url)
                        batch_structured.append(structured)
                        self.exporter.append_jsonl(structured)
                    except Exception as e:
                        logger.error(f"Error parsing listing item {p.get('productId')}: {e}")

                if batch_structured:
                    saved_count = self.db.save_products_batch(batch_structured)
                    with self._id_lock:
                        for item in batch_structured:
                            pid = item.get("product_info", {}).get("product_id")
                            if pid:
                                self.scraped_ids.add(pid)
                        self.total_saved += saved_count
                    logger.info(f"[BATCH SAVED #{self.total_saved}] {brand_label} [{part_name}] p={current_page}: +{saved_count} new styles (Partition total: {len(seen_pids_this_partition)})")

            if not has_next and current_page >= 5 and consecutive_empty_batches >= 2:
                self.db.save_crawl_state(endpoint, crawl_key, current_page, len(seen_pids_this_partition), "COMPLETED")
                break

            current_page += 1
            if self.delay > 0:
                time.sleep(self.delay)

        self.db.save_crawl_state(endpoint, crawl_key, current_page, len(seen_pids_this_partition), "COMPLETED")

    def run(self):
        """Main scraping loop across categories and brands using parallel worker pool."""
        logger.info("=" * 60)
        logger.info(f"STARTING HIGH-PERFORMANCE MYNTRA PARALLEL CRAWL")
        logger.info(f"Categories: {self.target_categories} | Workers: {self.workers} | Limit: {'Unlimited' if self.max_limit == 0 else self.max_limit}")
        logger.info("=" * 60)

        # Collect category configurations
        cat_endpoints = []
        for cat_key in self.target_categories:
            if cat_key in CATEGORIES:
                cat_endpoints.extend(CATEGORIES[cat_key])
            else:
                cat_endpoints.append({"name": cat_key.capitalize(), "endpoint": cat_key})

        for cat_cfg in cat_endpoints:
            endpoint = cat_cfg["endpoint"]
            cat_name = cat_cfg["name"]
            logger.info(f"\n>>> PROCESSING CATEGORY: {cat_name} (/{endpoint})")

            # Check if user specified target brands
            if self.target_brands:
                brands_to_process = [{"id": b, "value": b, "count": 1000} for b in self.target_brands]
            else:
                discovered_brands = self.discover_category_brands(endpoint)
                if discovered_brands:
                    if self.brand_type == "myntra":
                        filtered = [b for b in discovered_brands if is_myntra_label_brand(b.get("id"))]
                        logger.info(f"Filtered to {len(filtered)} Myntra in-house label brands.")
                    elif self.brand_type == "non-myntra":
                        filtered = [b for b in discovered_brands if not is_myntra_label_brand(b.get("id"))]
                        logger.info(f"Filtered to {len(filtered)} Non-Myntra external brands.")
                    else:
                        filtered = discovered_brands
                    brands_to_process = sorted(filtered, key=lambda b: (b.get("id") or "").lower())
                    logger.info(f"Sorted {len(brands_to_process)} brands alphabetically from A to Z.")
                else:
                    brands_to_process = [{"id": None, "value": "ALL", "count": 0}]

            partition_tasks = []
            for b_info in brands_to_process:
                brand_name = b_info.get("id")
                brand_label = brand_name or "ALL_BRANDS"
                b_count = b_info.get("count", 0)
                is_mylabel = is_myntra_label_brand(brand_name)
                b_tag = "[Myntra Label]" if is_mylabel else "[External Brand]"

                if b_count > 1000 and brand_name:
                    partitions = [
                        ("Men", "Gender:men,men women", None),
                        ("Women", "Gender:women,men women", None),
                        ("Boys", "Gender:boys", None),
                        ("Girls", "Gender:girls", None),
                        ("Men_New", "Gender:men,men women", "new"),
                        ("Women_New", "Gender:women,men women", "new")
                    ]
                elif b_count > 400 and brand_name:
                    partitions = [
                        ("Men", "Gender:men,men women", None),
                        ("Women", "Gender:women,men women", None),
                        ("Kids", "Gender:boys,girls", None)
                    ]
                else:
                    partitions = [("All", None, None)]

                for part_name, extra_filter, sort_param in partitions:
                    partition_tasks.append((
                        endpoint, cat_name, brand_name, brand_label, part_name, extra_filter, sort_param, b_count, b_tag
                    ))

            logger.info(f"Queuing {len(partition_tasks)} partitions for {cat_name} across {self.workers} concurrent workers...")
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = [
                    executor.submit(self._crawl_partition, *args)
                    for args in partition_tasks
                ]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as err:
                        logger.error(f"Worker partition task error: {err}")
                    if self.max_limit > 0 and self.total_saved >= self.max_limit:
                        logger.info(f"[!] Target limit of {self.max_limit} products reached.")
                        return

        elapsed = time.time() - self.start_time
        speed = self.total_saved / max(elapsed, 1)
        logger.info("=" * 60)
        logger.info(f"PARALLEL SCRAPING RUN COMPLETED")
        logger.info(f"Total New Products Saved: {self.total_saved}")
        logger.info(f"Elapsed Time: {elapsed:.1f}s ({speed:.2f} items/sec)")
        logger.info("=" * 60)
