# Myntra Shirts & Denims Full Catalog Scraper

A high-performance, enterprise-grade scraper specifically engineered for **Myntra Shirts & Denims** across **all brands** (both Myntra In-House Label brands and Non-Myntra External brands). Extracts rich product info, prices, discounts, ratings breakdown, per-size inventory count, specifications, return policies, and media into PostgreSQL, DuckDB, JSONL, and CSV.

---

## 1. Output Data Schema

Every product is normalized into this exact schema, including the brand classification tags:

```json
{
  "product_info": {
    "product_id": 28749636,
    "sku": "M28749636",
    "brand": "Roadster",
    "brand_type": "Myntra In-House Label",
    "is_myntra_label": true,
    "title": "The Lifestyle Co. Men Pure Cotton Baggy Fit Denim Jeans",
    "category": "Clothing",
    "sub_category": "Bottomwear",
    "gender": "Men",
    "product_url": "https://www.myntra.com/jeans/roadster/product-details"
  },
  "pricing": {
    "mrp": 2499,
    "selling_price": 1090,
    "discount_percentage": 56,
    "currency": "INR",
    "taxes_included": true,
    "available_offers": [
      "10% Instant Discount on SBI Credit Cards",
      "Flat Rs. 100 cashback on Paytm Wallet"
    ]
  },
  "media": {
    "primary_image": "https://assets.myntassets.com/h_720,q_90,w_540/v1/assets/images/28749636/main.jpg",
    "image_gallery": [
      "https://assets.myntassets.com/h_720,q_90,w_540/v1/assets/images/28749636/angle1.jpg"
    ],
    "video_url": "https://assets.myntassets.com/video/upload/v1/assets/videos/rw-28749636"
  },
  "inventory_and_sizes": {
    "is_in_stock": true,
    "sizes_available": [
      {
        "size": "28",
        "sku_id": 92353790,
        "available": true,
        "inventory_count": 1419
      },
      {
        "size": "30",
        "sku_id": 92353792,
        "available": true,
        "inventory_count": 886
      }
    ],
    "fit": "Baggy",
    "model_sizing": "The model (height 6') is wearing a size 28"
  },
  "specifications": {
    "fabric": "100% Cotton",
    "weave_type": "Woven",
    "pattern": "Solid",
    "sleeve_length": "Regular",
    "collar": "Regular Collar",
    "length": "Regular",
    "hemline": "Straight",
    "wash_care": "Machine Wash"
  },
  "delivery_and_policies": {
    "pincode_serviceable": true,
    "estimated_delivery_days": 4,
    "cod_available": true,
    "return_window_days": 14,
    "exchange_available": true
  },
  "ratings_and_reviews": {
    "average_rating": 4.0,
    "total_ratings_count": 21565,
    "total_reviews_count": 3933,
    "rating_breakdown": {
      "5_star": 12772,
      "4_star": 3272,
      "3_star": 1608,
      "2_star": 881,
      "1_star": 3032
    }
  }
}
```

---

## 2. Quick Start & Usage

### A. Discover All 3,800+ Brands on Myntra
Discovers all brands across Shirts and Denims, categorizes them as **Myntra In-House Label** vs **Non-Myntra Brand**, saves them to the database, and exports `brands_directory.csv` and `brands_directory.json`:
```bash
python3 main.py --discover-brands
```

### B. Full Scraping (All Brands, Unlimited)
Runs exhaustive crawling across all 3,800+ brands with multi-partitioning (ensuring zero products missed):
```bash
python3 main.py
```

### C. Scrape ONLY Myntra In-House Label Brands
Targets exclusively Myntra's private labels (Roadster, Mast & Harbour, HERE&NOW, Moda Rapido, DressBerry, StyleCast, etc.):
```bash
python3 main.py --brand-type myntra
```

### D. Scrape ONLY Non-Myntra External Brands
Targets only third-party brands (Levi's, HIGHLANDER, Crimsoune Club, SPYKAR, Flying Machine, Pepe Jeans, etc.):
```bash
python3 main.py --brand-type non-myntra
```

### E. Run by Category
```bash
# Only Shirts
python3 main.py --categories shirts

# Only Denims
python3 main.py --categories denims
```

### F. Target Specific Brands
```bash
python3 main.py --brands "Roadster,HIGHLANDER,Levis,WROGN" --limit 100
```

### G. Adjust Concurrency for High Speed
```bash
python3 main.py --workers 12 --delay 0.2
```

### H. Check Database Statistics
```bash
python3 main.py --stats
```

### I. Re-Export to CSV & JSONL
```bash
python3 main.py --export-only
```

---

## 3. Storage Files & Deliverables

- **PostgreSQL Catalog**: Primary transactional store for `products`, `product_sizes`, `brands`, `crawl_state`, and crawl analytics
- **DuckDB Analytics**: `data/myntra_analytics.duckdb` for fast dashboard aggregations and reporting
- **Brands Directory**:
  - `data/brands_directory.csv` (3,825 brands with counts and classification)
  - `data/brands_directory.json`
- **Real-Time JSONL Stream**: `data/products_shirts_denims.jsonl` (Streams live during scrape)
- **Flattened Product CSV**: `data/myntra_shirts_denims.csv` (Spreadsheet-ready with brand_type, available sizes, specs)
- **Size-Wise Inventory CSV**: `data/myntra_size_inventory.csv` (Dedicated size-by-size inventory table with SKU ID, availability, and stock count)
- **Sample JSON Preview**: `data/products_sample.json`
- **Logs**: `logs/scraper.log` (Full debug and audit logs)

---

## 4. How "Zero Missed Products" is Guaranteed

1. **Brand-by-Brand Iteration**: Rather than relying on generic category pages that truncate at page 12 (approx 350 items), the scraper iterates through all 3,825 individual brand endpoints.
2. **Multi-Partition Sub-Querying**: For brands with >300 products (such as Roadster with 15,000+ items or HIGHLANDER with 9,000+ items), the scraper automatically partitions queries across genders (`Men`, `Women`, `Boys`, `Girls`) and fallback sort orders so that Myntra's pagination window never cuts off products.
3. **Resilient Checkpointing**: State is saved per category, brand, and partition (`Roadster_Men`, `Roadster_Women`, etc.). If stopped or interrupted, it resumes without repeating already scraped items.
# MYNTRAXLAL10
# MYNTRAXLAL10
