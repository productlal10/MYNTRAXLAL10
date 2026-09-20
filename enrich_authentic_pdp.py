"""High-Throughput Authentic PDP Enrichment Engine.
Fetches real Myntra Product Detail Pages (PDP) for every product in the catalog.
Replaces all synthetic/placeholder inventory (e.g. 5 units) with genuine live warehouse stock,
authentic SKU IDs, verified ratings & reviews, and full garment specifications.
"""

import time
import json
import re
import random
import logging
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List, Tuple

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests as cffi_requests
    HAS_CURL_CFFI = False

from config import HEADERS, BASE_URL, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF
from database import Database
from schema import parse_pdp_to_schema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/enricher.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AuthenticPDPEnricher")


def extract_myx_json(html_content: str) -> Optional[Dict[str, Any]]:
    """Fast, backtrack-free extraction of window.__myx JSON payload from Myntra HTML."""
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


class AuthenticEnricher:
    """Multi-threaded enrichment engine that ensures 100% authentic live data from Myntra."""

    def __init__(self, workers: int = 16, batch_size: int = 25):
        self.workers = workers
        self.batch_size = batch_size
        self.db = Database()
        self._local = threading.local()
        self._counter_lock = threading.Lock()
        self.total_enriched = 0
        self.total_failed = 0
        self.start_time = time.time()

    def _get_session(self):
        if not hasattr(self._local, "session") or self._local.session is None:
            if HAS_CURL_CFFI:
                s = cffi_requests.Session(impersonate="chrome120")
            else:
                s = cffi_requests.Session()
            s.headers.update(HEADERS)
            self._local.session = s
        return self._local.session

    def fetch_pdp(self, product_url: str) -> Optional[Dict[str, Any]]:
        """Fetches live product page and extracts window.__myx.pdpData using fast string indexing."""
        s = self._get_session()
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = s.get(product_url, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    data = extract_myx_json(resp.text)
                    if data:
                        pdp = data.get("pdpData")
                        if pdp:
                            return pdp
                    return None
                elif resp.status_code == 404:
                    return None
                elif resp.status_code in (429, 403):
                    time.sleep(RETRY_BACKOFF ** attempt + random.uniform(0.5, 1.5))
                else:
                    time.sleep(1.0)
            except Exception:
                time.sleep(1.0)
        return None

    def process_product(self, prod_info: Tuple[int, str, str]) -> Optional[Dict[str, Any]]:
        """Worker task: fetches real PDP, validates schema, and returns structured data."""
        pid, p_url, brand = prod_info
        if not p_url:
            return None

        pdp_data = self.fetch_pdp(p_url)
        if not pdp_data:
            return None

        try:
            structured = parse_pdp_to_schema(pdp_data, raw_url=p_url)
            return structured
        except Exception as e:
            logger.error(f"Failed parsing schema for {pid}: {e}")
            return None

    def run(self, specific_brand: Optional[str] = None, limit: int = 0):
        """Processes all products requiring authentic PDP enrichment."""
        logger.info("=" * 60)
        logger.info("STARTING AUTHENTIC PDP ENRICHMENT ENGINE")
        logger.info(f"Workers: {self.workers} | Target Brand: {specific_brand or 'ALL'}")
        logger.info("=" * 60)

        conn = self.db._get_connection()
        query = """
            SELECT DISTINCT p.product_id, p.product_url, p.brand
            FROM products p
            JOIN product_sizes ps ON p.product_id = ps.product_id
            WHERE ps.inventory_count = 5 OR ps.sku_id = p.product_id
        """
        params = []
        if specific_brand:
            query += " AND p.brand LIKE ?"
            params.append(f"%{specific_brand}%")

        query += " ORDER BY p.brand ASC"
        if limit > 0:
            query += f" LIMIT {limit}"

        cur = conn.cursor()
        cur.execute(query, params)
        rows = [(r[0], r[1], r[2]) for r in cur.fetchall()]
        total_targets = len(rows)

        logger.info(f"Found {total_targets} products needing authentic PDP inventory & specification enrichment.")

        if total_targets == 0:
            logger.info("All products already have authentic live PDP inventory. Nothing to enrich!")
            return

        batch_structured = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self.process_product, row): row for row in rows}

            for future in as_completed(futures):
                row = futures[future]
                pid, _, brand = row
                try:
                    res = future.result()
                    if res:
                        batch_structured.append(res)
                        if len(batch_structured) >= self.batch_size:
                            saved = self.db.save_products_batch(batch_structured)
                            with self._counter_lock:
                                self.total_enriched += saved
                                elapsed = time.time() - self.start_time
                                rate = self.total_enriched / max(elapsed, 1)
                                remaining = max(0, total_targets - self.total_enriched)
                                eta_min = (remaining / max(rate, 0.1)) / 60
                                logger.info(
                                    f"[AUTHENTICATED #{self.total_enriched}/{total_targets}] "
                                    f"Batch of {saved} products updated with live warehouse stock! "
                                    f"Rate: {rate:.1f} items/sec | ETA: {eta_min:.1f}m"
                                )
                            batch_structured = []
                    else:
                        with self._counter_lock:
                            self.total_failed += 1
                except Exception as e:
                    logger.error(f"Enrichment worker error for {pid}: {e}")

            # Flush any remaining items in batch
            if batch_structured:
                saved = self.db.save_products_batch(batch_structured)
                with self._counter_lock:
                    self.total_enriched += saved
                    logger.info(f"[AUTHENTICATED FINAL #{self.total_enriched}] Last batch of {saved} products saved.")

        elapsed = time.time() - self.start_time
        logger.info("=" * 60)
        logger.info(f"ENRICHMENT RUN COMPLETED")
        logger.info(f"Total Enriched: {self.total_enriched} | Failed/Inactive: {self.total_failed}")
        logger.info(f"Time Taken: {elapsed:.1f}s ({self.total_enriched / max(elapsed, 1):.1f} items/sec)")
        logger.info("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Enrich catalog with 100% authentic Myntra PDP data.")
    parser.add_argument("--workers", type=int, default=16, help="Concurrent worker threads (default: 16)")
    parser.add_argument("--brand", type=str, default=None, help="Specific brand to enrich first")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of items to enrich (0 = all)")
    args = parser.parse_args()

    enricher = AuthenticEnricher(workers=args.workers)
    enricher.run(specific_brand=args.brand, limit=args.limit)
