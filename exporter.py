"""Data export module for JSONL, JSON, and CSV formats."""

import csv
import json
from pathlib import Path
from typing import Dict, Any, Iterable
import threading

from config import JSONL_PATH, CSV_PATH, SIZE_CSV_PATH, JSON_PRETTY_PATH
from database import Database


class DataExporter:
    """Thread-safe exporter for real-time JSONL streaming and CSV generation."""

    def __init__(self, jsonl_path: Path = JSONL_PATH, csv_path: Path = CSV_PATH, size_csv_path: Path = SIZE_CSV_PATH):
        self.jsonl_path = jsonl_path
        self.csv_path = csv_path
        self.size_csv_path = size_csv_path
        self._lock = threading.Lock()

    def append_jsonl(self, product_data: Dict[str, Any]):
        """Appends a single product in real-time to JSONL file."""
        line = json.dumps(product_data, ensure_ascii=False)
        with self._lock:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def export_database_to_all(self, db: Database, sample_limit: int = 100):
        """Dumps all database items to JSONL, product CSV, size inventory CSV, and sample pretty JSON."""
        print(f"[*] Exporting all records from database...")
        count = 0
        total_size_rows = 0
        samples = []

        # Open JSONL, product CSV, and size inventory CSV
        with open(self.jsonl_path, "w", encoding="utf-8") as f_jsonl, \
             open(self.csv_path, "w", encoding="utf-8", newline="") as f_csv, \
             open(self.size_csv_path, "w", encoding="utf-8", newline="") as f_size_csv:

            csv_fieldnames = [
                "product_id", "sku", "brand", "brand_type", "is_myntra_label", "title", "category", "sub_category", "gender",
                "mrp", "selling_price", "discount_percentage", "currency", "in_stock",
                "available_sizes", "total_inventory", "fit", "fabric", "weave_type", "pattern",
                "sleeve_length", "collar", "wash_care", "pincode_serviceable", "cod_available",
                "return_window_days", "average_rating", "total_ratings_count", "total_reviews_count",
                "product_url", "primary_image", "video_url"
            ]
            csv_writer = csv.DictWriter(f_csv, fieldnames=csv_fieldnames)
            csv_writer.writeheader()

            size_fieldnames = [
                "product_id", "brand", "brand_type", "title", "category", "gender", "selling_price",
                "size", "sku_id", "available", "inventory_count", "product_url"
            ]
            size_writer = csv.DictWriter(f_size_csv, fieldnames=size_fieldnames)
            size_writer.writeheader()

            for item in db.iterate_all_products():
                count += 1
                # Write to JSONL
                f_jsonl.write(json.dumps(item, ensure_ascii=False) + "\n")

                # Format for CSV
                p_info = item.get("product_info", {})
                pricing = item.get("pricing", {})
                media = item.get("media", {})
                inv = item.get("inventory_and_sizes", {})
                specs = item.get("specifications", {})
                deliv = item.get("delivery_and_policies", {})
                ratings = item.get("ratings_and_reviews", {})

                sizes_list = inv.get("sizes_available", [])
                avail_sizes_str = ",".join([s.get("size", "") for s in sizes_list if s.get("available")])
                total_inv = sum(s.get("inventory_count", 0) for s in sizes_list)

                # Write product level row
                csv_row = {
                    "product_id": p_info.get("product_id"),
                    "sku": p_info.get("sku"),
                    "brand": p_info.get("brand"),
                    "brand_type": p_info.get("brand_type", "Non-Myntra Brand"),
                    "is_myntra_label": "Yes" if p_info.get("is_myntra_label") else "No",
                    "title": p_info.get("title"),
                    "category": p_info.get("category"),
                    "sub_category": p_info.get("sub_category"),
                    "gender": p_info.get("gender"),
                    "mrp": pricing.get("mrp"),
                    "selling_price": pricing.get("selling_price"),
                    "discount_percentage": pricing.get("discount_percentage"),
                    "currency": pricing.get("currency", "INR"),
                    "in_stock": "Yes" if inv.get("is_in_stock") else "No",
                    "available_sizes": avail_sizes_str,
                    "total_inventory": total_inv,
                    "fit": inv.get("fit"),
                    "fabric": specs.get("fabric"),
                    "weave_type": specs.get("weave_type"),
                    "pattern": specs.get("pattern"),
                    "sleeve_length": specs.get("sleeve_length"),
                    "collar": specs.get("collar"),
                    "wash_care": specs.get("wash_care"),
                    "pincode_serviceable": "Yes" if deliv.get("pincode_serviceable") else "No",
                    "cod_available": "Yes" if deliv.get("cod_available") else "No",
                    "return_window_days": deliv.get("return_window_days"),
                    "average_rating": ratings.get("average_rating"),
                    "total_ratings_count": ratings.get("total_ratings_count"),
                    "total_reviews_count": ratings.get("total_reviews_count"),
                    "product_url": p_info.get("product_url"),
                    "primary_image": media.get("primary_image"),
                    "video_url": media.get("video_url")
                }
                csv_writer.writerow(csv_row)

                # Write size-level inventory rows
                for sz in sizes_list:
                    total_size_rows += 1
                    size_writer.writerow({
                        "product_id": p_info.get("product_id"),
                        "brand": p_info.get("brand"),
                        "brand_type": p_info.get("brand_type", "Non-Myntra Brand"),
                        "title": p_info.get("title"),
                        "category": p_info.get("category"),
                        "gender": p_info.get("gender"),
                        "selling_price": pricing.get("selling_price"),
                        "size": sz.get("size"),
                        "sku_id": sz.get("sku_id"),
                        "available": "Yes" if sz.get("available") else "No",
                        "inventory_count": sz.get("inventory_count", 0),
                        "product_url": p_info.get("product_url")
                    })

                if len(samples) < sample_limit:
                    samples.append(item)

        # Write sample JSON
        with open(JSON_PRETTY_PATH, "w", encoding="utf-8") as f_samp:
            json.dump(samples, f_samp, indent=2, ensure_ascii=False)

        print(f"[✓] Export completed: {count} products & {total_size_rows} size inventory rows written to:")
        print(f"    - JSONL:              {self.jsonl_path}")
        print(f"    - Product CSV:        {self.csv_path}")
        print(f"    - Size Inventory CSV: {self.size_csv_path}")
        print(f"    - Sample JSON:        {JSON_PRETTY_PATH}")
