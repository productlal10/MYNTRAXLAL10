"""Brand catalog management, discovery, and classification.
Identifies all brands on Myntra for Shirts and Denims, distinguishes Myntra
in-house private labels from external/third-party brands, and exports brand directories.
"""

import json
import csv
import re
from typing import Dict, Any, List, Set, Tuple
from pathlib import Path

from config import BASE_URL, DATA_DIR
from database import Database

# Known Myntra In-House Private Labels, FWD Labels, and Exclusive Brands
MYNTRA_INHOUSE_BRANDS = {
    "roadster",
    "the roadster life co.",
    "the roadster lifestyle co",
    "the roadster lifestyle co.",
    "r.code by the roadster life co.",
    "mast & harbour",
    "mast and harbour",
    "here&now",
    "here & now",
    "moda rapido",
    "dressberry",
    "anouk",
    "kook n keech",
    "kook & keech",
    "ether",
    "hrx",
    "hrx by hrithik roshan",
    "house of pataudi",
    "all about you",
    "all about you by deepika padukone",
    "invictus",
    "taavi",
    "sangria",
    "sztori",
    "harvard",
    "mod & shy",
    "friskers",
    "u&f",
    "glitchez",
    "stylecast",
    "stylecast x revolte",
    "fwd",
    "slazenger",
    "difference of opinion"
}

BRANDS_CSV_PATH = DATA_DIR / "brands_directory.csv"
BRANDS_JSON_PATH = DATA_DIR / "brands_directory.json"


def is_myntra_label_brand(brand_name: str, system_attrs: List[Any] = None) -> bool:
    """
    Determines if a brand is a Myntra in-house private label or exclusive brand.
    Checks normalized brand name and any Myntra Unique system attributes.
    """
    if not brand_name:
        return False

    b_clean = brand_name.lower().strip()

    # Check known in-house brands
    for inhouse in MYNTRA_INHOUSE_BRANDS:
        if inhouse in b_clean or b_clean == inhouse:
            return True

    # Check system attributes if available (e.g. SA_XT_MYNTRA_UNIQUE)
    if system_attrs:
        for attr in system_attrs:
            if isinstance(attr, dict):
                a_name = str(attr.get("attribute", "")).upper()
                a_val = str(attr.get("value", "")).lower()
                if "MYNTRA_UNIQUE" in a_name or "myntra" in a_val:
                    return True

    return False


def get_brand_classification(brand_name: str, system_attrs: List[Any] = None) -> Tuple[bool, str]:
    """Returns (is_myntra_label, classification_label)."""
    is_myntra = is_myntra_label_brand(brand_name, system_attrs)
    label = "Myntra In-House Label" if is_myntra else "Non-Myntra Brand"
    return is_myntra, label


class BrandManager:
    """Discovers, catalogues, and indexes all Myntra brands for target categories."""

    def __init__(self, db: Database = None):
        self.db = db or Database()

    def discover_all_brands(self, scraper) -> List[Dict[str, Any]]:
        """
        Discovers all brands across shirts and denims, classifies them,
        and saves them to PostgreSQL and export files.
        """
        print("\n" + "=" * 60)
        print("DISCOVERING ALL BRANDS LISTED ON MYNTRA (SHIRTS & DENIMS)")
        print("=" * 60)

        all_brands_map: Dict[str, Dict[str, Any]] = {}

        # 1. Discover for Shirts
        print("[*] Querying all brands in Shirts category...")
        shirts_brands = scraper.discover_category_brands("shirts")
        for b in shirts_brands:
            b_name = b.get("id") or b.get("value")
            if not b_name:
                continue
            count = b.get("count", 0)
            is_myntra, b_type = get_brand_classification(b_name)
            all_brands_map[b_name] = {
                "brand_name": b_name,
                "shirts_count": count,
                "denims_count": 0,
                "western_count": 0,
                "total_count": count,
                "is_myntra_label": is_myntra,
                "brand_type": b_type
            }

        # 2. Discover for Denims (Jeans)
        print("[*] Querying all brands in Denims/Jeans category...")
        denims_brands = scraper.discover_category_brands("jeans")
        for b in denims_brands:
            b_name = b.get("id") or b.get("value")
            if not b_name:
                continue
            count = b.get("count", 0)
            is_myntra, b_type = get_brand_classification(b_name)
            if b_name in all_brands_map:
                all_brands_map[b_name]["denims_count"] = count
                all_brands_map[b_name]["total_count"] += count
            else:
                all_brands_map[b_name] = {
                    "brand_name": b_name,
                    "shirts_count": 0,
                    "denims_count": count,
                    "western_count": 0,
                    "total_count": count,
                    "is_myntra_label": is_myntra,
                    "brand_type": b_type
                }

        # Also check Denim Shirts and Jackets
        for sub_cat in ["denim-shirts", "denim-jackets"]:
            sub_brands = scraper.discover_category_brands(sub_cat)
            for b in sub_brands:
                b_name = b.get("id") or b.get("value")
                if not b_name:
                    continue
                count = b.get("count", 0)
                is_myntra, b_type = get_brand_classification(b_name)
                if b_name in all_brands_map:
                    all_brands_map[b_name]["denims_count"] += count
                    all_brands_map[b_name]["total_count"] += count
                else:
                    all_brands_map[b_name] = {
                        "brand_name": b_name,
                        "shirts_count": 0,
                        "denims_count": count,
                        "western_count": 0,
                        "total_count": count,
                        "is_myntra_label": is_myntra,
                        "brand_type": b_type
                    }

        # 3. Discover for Women's Western Wear
        print("[*] Querying all brands in Women's Western Wear category...")
        western_brands = scraper.discover_category_brands("women-western-wear")
        for b in western_brands:
            b_name = b.get("id") or b.get("value")
            if not b_name:
                continue
            count = b.get("count", 0)
            is_myntra, b_type = get_brand_classification(b_name)
            if b_name in all_brands_map:
                all_brands_map[b_name]["western_count"] = count
                all_brands_map[b_name]["total_count"] += count
            else:
                all_brands_map[b_name] = {
                    "brand_name": b_name,
                    "shirts_count": 0,
                    "denims_count": 0,
                    "western_count": count,
                    "total_count": count,
                    "is_myntra_label": is_myntra,
                    "brand_type": b_type
                }

        sorted_brands = sorted(all_brands_map.values(), key=lambda x: x["total_count"], reverse=True)
        print(f"[✓] Successfully discovered {len(sorted_brands):,} distinct brands across Shirts, Denims, and Women's Western Wear!")

        myntra_count = sum(1 for b in sorted_brands if b["is_myntra_label"])
        non_myntra_count = len(sorted_brands) - myntra_count
        print(f"    - Myntra In-House Label Brands : {myntra_count:,}")
        print(f"    - Non-Myntra / External Brands : {non_myntra_count:,}")

        # Save to database
        self.save_brands_to_db(sorted_brands)

        # Export to CSV & JSON
        self.export_brands_directory(sorted_brands)

        return sorted_brands

    def save_brands_to_db(self, brands_list: List[Dict[str, Any]]):
        """Saves discovered brands into PostgreSQL."""
        conn = self.db._get_connection()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS brands (
                    brand_name TEXT PRIMARY KEY,
                    shirts_count INTEGER DEFAULT 0,
                    denims_count INTEGER DEFAULT 0,
                    western_count INTEGER DEFAULT 0,
                    total_count INTEGER DEFAULT 0,
                    is_myntra_label INTEGER DEFAULT 0,
                    brand_type TEXT,
                    crawled_status TEXT DEFAULT 'PENDING',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            try:
                conn.execute("ALTER TABLE brands ADD COLUMN western_count INTEGER DEFAULT 0;")
            except Exception:
                pass

            records = [
                (
                    b["brand_name"],
                    b.get("shirts_count", 0),
                    b.get("denims_count", 0),
                    b.get("western_count", 0),
                    b["total_count"],
                    1 if b["is_myntra_label"] else 0,
                    b["brand_type"]
                )
                for b in brands_list
            ]
            conn.executemany("""
                INSERT INTO brands (brand_name, shirts_count, denims_count, western_count, total_count, is_myntra_label, brand_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(brand_name) DO UPDATE SET
                    shirts_count=excluded.shirts_count,
                    denims_count=excluded.denims_count,
                    western_count=excluded.western_count,
                    total_count=excluded.total_count,
                    is_myntra_label=excluded.is_myntra_label,
                    brand_type=excluded.brand_type,
                    updated_at=CURRENT_TIMESTAMP;
            """, records)

    def export_brands_directory(self, brands_list: List[Dict[str, Any]]):
        """Exports brands directory to CSV and JSON."""
        with open(BRANDS_CSV_PATH, "w", encoding="utf-8", newline="") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=[
                "brand_name", "brand_type", "is_myntra_label", "shirts_count", "denims_count", "western_count", "total_count"
            ])
            writer.writeheader()
            for b in brands_list:
                writer.writerow(b)

        with open(BRANDS_JSON_PATH, "w", encoding="utf-8") as f_json:
            json.dump(brands_list, f_json, indent=2, ensure_ascii=False)

        print(f"[✓] Brands directory exported to:")
        print(f"    - CSV:  {BRANDS_CSV_PATH}")
        print(f"    - JSON: {BRANDS_JSON_PATH}")

    def get_brands_by_filter(self, brand_type_filter: str = "all") -> List[str]:
        """
        Retrieves list of brand names based on filter:
        - 'myntra': only Myntra in-house brands
        - 'non-myntra': only external brands
        - 'all': all brands
        """
        conn = self.db._get_connection()
        cur = conn.cursor()
        if brand_type_filter == "myntra":
            cur.execute("SELECT brand_name FROM brands WHERE is_myntra_label = 1 ORDER BY total_count DESC;")
        elif brand_type_filter == "non-myntra":
            cur.execute("SELECT brand_name FROM brands WHERE is_myntra_label = 0 ORDER BY total_count DESC;")
        else:
            cur.execute("SELECT brand_name FROM brands ORDER BY total_count DESC;")
        rows = cur.fetchall()
        return [row[0] for row in rows]
