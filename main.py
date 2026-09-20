#!/usr/bin/env python3
"""
Myntra Shirts & Denims Full Catalog Scraper CLI
Extracts products, pricing, discounts, inventory per size, specifications,
ratings/reviews breakdown, delivery policies, and media.
"""

import argparse
import sys
import json
from pathlib import Path

from config import DEFAULT_WORKERS, POLITE_DELAY
from scraper import MyntraScraper
from database import Database
from exporter import DataExporter


def print_banner():
    banner = r"""
  __  __                  _                  _____                                
 |  \/  |                | |                / ____|                               
 | \  / | _   _  _ __   | |_  _ __  __ _  | (___    ___  _ __  __ _  _ __    ___  _ __ 
 | |\/| || | | || '_ \  | __|| '__|/ _` |  \___ \  / __|| '__|/ _` || '_ \  / _ \| '__|
 | |  | || |_| || | | | | |_ | |  | (_| |  ____) || (__ | |  | (_| || |_) ||  __/| |   
 |_|  |_| \__, ||_| |_|  \__||_|   \__,_| |_____/  \___||_|   \__,_|| .__/  \___||_|   
           __/ |                                                    | |                
           |___/    [ Categories: Shirts, Denims & Women's Western Wear ]      |_|                
    """
    print(banner)


from brands import BrandManager


def show_stats():
    db = Database()
    stats = db.get_stats()
    print("\n" + "=" * 55)
    print("CURRENT DATABASE STATISTICS")
    print("=" * 55)
    print(f"Total Products Scraped     : {stats['total_products']:,}")
    print(f"Distinct Brands Count      : {stats['total_brands']:,}")
    print(f"  - Myntra In-House Brands : {stats.get('myntra_brands_count', 0):,}")
    print(f"  - Non-Myntra Brands      : {stats.get('non_myntra_brands_count', 0):,}")
    print(f"Products by Brand Type:")
    print(f"  - Myntra Label Products  : {stats.get('myntra_label_products', 0):,}")
    print(f"  - Non-Myntra Products    : {stats.get('non_myntra_products', 0):,}")
    print(f"In-Stock Products          : {stats['in_stock']:,}")
    print(f"Out-of-Stock Products      : {stats['out_of_stock']:,}")
    print(f"Average Product Rating     : {stats['average_rating']} / 5.0")
    print(f"Average Selling Price      : ₹{stats['average_price']:.2f}")
    print("\nBreakdown by Category:")
    for cat, cnt in stats["categories"].items():
        print(f"  - {cat:<20}: {cnt:,}")
    print("\nBreakdown by Gender:")
    for gen, cnt in stats["genders"].items():
        print(f"  - {gen:<20}: {cnt:,}")
    print("=" * 55 + "\n")


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="Enterprise Scraper for Myntra Shirts, Denims & Women's Western Wear with full inventory, specs, and reviews."
    )
    parser.add_argument(
        "--categories",
        type=str,
        default="shirts,denims,western-wear",
        help="Comma-separated categories: shirts, denims, western-wear (default: shirts,denims,western-wear)"
    )
    parser.add_argument(
        "--brands",
        type=str,
        default="",
        help="Optional comma-separated list of brands to target (e.g. 'Roadster,HIGHLANDER,Levis')"
    )
    parser.add_argument(
        "--brand-type",
        type=str,
        default="all",
        choices=["all", "myntra", "non-myntra"],
        help="Filter by brand type: 'all', 'myntra' (in-house labels only), or 'non-myntra' (external brands only)"
    )
    parser.add_argument(
        "--discover-brands",
        action="store_true",
        help="Discover and catalog all 3,000+ brands on Myntra for shirts and denims, export to CSV/JSON, and exit"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of products to scrape (0 for unlimited full catalog, default: 0)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of parallel worker threads (default: {DEFAULT_WORKERS})"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=POLITE_DELAY,
        help=f"Polite delay between requests in seconds (default: {POLITE_DELAY})"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not resume previous crawl progress; scrape from beginning"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Display statistics of current database and exit"
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Export existing PostgreSQL catalog data to JSONL, CSV, and sample JSON without running scraper"
    )
    parser.add_argument(
        "--proxy",
        type=str,
        default="",
        help="HTTP/SOCKS5 proxy URL (e.g., 'http://user:pass@india-proxy.com:8080' or 'socks5://127.0.0.1:1080')"
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Fetch individual product detail pages (PDP) instead of 40x Turbo listing ingestion"
    )

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.export_only:
        db = Database()
        exporter = DataExporter()
        exporter.export_database_to_all(db)
        show_stats()
        return

    if args.discover_brands:
        scraper = MyntraScraper(workers=2)
        bm = BrandManager()
        bm.discover_all_brands(scraper)
        return

    # Parse categories & brands
    categories = [c.strip().lower() for c in args.categories.split(",") if c.strip()]
    brands = [b.strip() for b in args.brands.split(",") if b.strip()] if args.brands else None

    print(f"[*] Target Categories : {', '.join(categories)}")
    print(f"[*] Brand Type Filter : {args.brand_type.upper()}")
    if brands:
        print(f"[*] Filtered Brands   : {', '.join(brands)}")
    else:
        print(f"[*] Filtered Brands   : ALL BRANDS (Dynamic Discovery)")
    print(f"[*] Product Limit     : {'Unlimited' if args.limit == 0 else f'{args.limit:,}'}")
    print(f"[*] Ingestion Mode    : {'Deep PDP Mode' if args.deep else '40x Turbo Listing Mode'}")
    print(f"[*] Worker Threads    : {args.workers}")
    print(f"[*] Request Delay     : {args.delay}s")
    print(f"[*] Resume Mode       : {'Disabled' if args.no_resume else 'Enabled'}\n")

    # Instantiate and run scraper
    scraper = MyntraScraper(
        categories=categories,
        brands=brands,
        brand_type=args.brand_type,
        max_limit=args.limit,
        workers=args.workers,
        delay=args.delay,
        resume=not args.no_resume,
        proxy=args.proxy,
        fast_mode=not args.deep
    )

    try:
        scraper.run()
    except KeyboardInterrupt:
        print("\n[!] Scraping paused by user. Progress is saved. You can resume anytime!")
    finally:
        # Automatic export after scrape
        db = Database()
        exporter = DataExporter()
        exporter.export_database_to_all(db)
        show_stats()


if __name__ == "__main__":
    main()
