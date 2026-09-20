"""Configuration settings for Myntra Shirts & Denims Scraper."""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Database Configurations
# PostgreSQL (Application / CRUD Data)
PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", 5432))
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "alan1234")
PG_DBNAME = os.getenv("PG_DBNAME", "myntra")

# DuckDB (Analytics & Reporting)
DUCKDB_PATH = BASE_DIR / os.getenv("DUCKDB_PATH", "data/myntra_analytics.duckdb")

# Export Files
JSONL_PATH = DATA_DIR / "products_shirts_denims.jsonl"
CSV_PATH = DATA_DIR / "myntra_shirts_denims.csv"
SIZE_CSV_PATH = DATA_DIR / "myntra_size_inventory.csv"
JSON_PRETTY_PATH = DATA_DIR / "products_sample.json"

# Log File
LOG_FILE = LOGS_DIR / "scraper.log"

# Target Categories
# Myntra routes for Shirts, Denims, and Women's Western Wear
CATEGORIES = {
    "shirts": [
        {"name": "Casual Shirts", "endpoint": "casual-shirts", "filter": "Categories:Shirts"},
        {"name": "Formal Shirts", "endpoint": "formal-shirts", "filter": "Categories:Shirts"},
        {"name": "Men Casual Shirts", "endpoint": "men-casual-shirts", "filter": "Categories:Shirts"},
        {"name": "Men Formal Shirts", "endpoint": "men-formal-shirts", "filter": "Categories:Shirts"},
        {"name": "Women Shirts", "endpoint": "women-shirts", "filter": "Categories:Shirts"},
        {"name": "Denim Shirts", "endpoint": "denim-shirts", "filter": "Categories:Shirts"},
        {"name": "All Shirts", "endpoint": "shirts", "filter": "Categories:Shirts"}
    ],
    "denims": [
        {"name": "Jeans", "endpoint": "jeans", "filter": "Categories:Jeans"},
        {"name": "Men Jeans", "endpoint": "men-jeans", "filter": "Categories:Jeans"},
        {"name": "Women Jeans", "endpoint": "women-jeans", "filter": "Categories:Jeans"},
        {"name": "Kids Jeans", "endpoint": "kids-jeans", "filter": "Categories:Jeans"},
        {"name": "Denim Jackets", "endpoint": "denim-jackets", "filter": "Categories:Jackets"},
        {"name": "Men Denim Jackets", "endpoint": "men-denim-jackets", "filter": "Categories:Jackets"},
        {"name": "Women Denim Jackets", "endpoint": "women-denim-jackets", "filter": "Categories:Jackets"},
        {"name": "Denim Shirts", "endpoint": "denim-shirts", "filter": "Categories:Shirts"},
        {"name": "Denim Skirts", "endpoint": "denim-skirts", "filter": "Categories:Skirts"},
        {"name": "Denim Shorts", "endpoint": "denim-shorts", "filter": "Categories:Shorts"},
        {"name": "Denim Dresses", "endpoint": "denim-dresses", "filter": "Categories:Dresses"}
    ],
    "jeans": [
        {"name": "Jeans", "endpoint": "jeans", "filter": "Categories:Jeans"},
        {"name": "Men Jeans", "endpoint": "men-jeans", "filter": "Categories:Jeans"},
        {"name": "Women Jeans", "endpoint": "women-jeans", "filter": "Categories:Jeans"},
        {"name": "Kids Jeans", "endpoint": "kids-jeans", "filter": "Categories:Jeans"}
    ],
    "western-wear": [
        {"name": "Women Western Wear", "endpoint": "women-western-wear", "filter": "Categories:Western Wear"},
        {"name": "Dresses", "endpoint": "dresses", "filter": "Categories:Dresses"},
        {"name": "Women Tops", "endpoint": "women-tops", "filter": "Categories:Tops"},
        {"name": "Women Tshirts", "endpoint": "women-tshirts", "filter": "Categories:Tshirts"},
        {"name": "Women Trousers", "endpoint": "women-trousers", "filter": "Categories:Trousers"},
        {"name": "Co-Ords", "endpoint": "co-ords", "filter": "Categories:Co-Ords"},
        {"name": "Women Sweaters & Sweatshirts", "endpoint": "women-sweaters-sweatshirts", "filter": "Categories:Sweaters"},
        {"name": "Women Jackets & Coats", "endpoint": "women-jackets-coats", "filter": "Categories:Jackets"},
        {"name": "Women Shorts", "endpoint": "women-shorts", "filter": "Categories:Shorts"},
        {"name": "Women Skirts", "endpoint": "women-skirts", "filter": "Categories:Skirts"},
        {"name": "Jumpsuits", "endpoint": "jumpsuits", "filter": "Categories:Jumpsuits"},
        {"name": "Shrugs", "endpoint": "shrugs", "filter": "Categories:Shrugs"},
        {"name": "Women Blazers", "endpoint": "women-blazers", "filter": "Categories:Blazers"}
    ]
}

# Synonyms & Aliases
CATEGORIES["women-western-wear"] = CATEGORIES["western-wear"]
CATEGORIES["womens-western-wear"] = CATEGORIES["western-wear"]
CATEGORIES["western"] = CATEGORIES["western-wear"]
CATEGORIES["westernwear"] = CATEGORIES["western-wear"]

# Network & Concurrency Defaults
DEFAULT_WORKERS = 6
REQUEST_TIMEOUT = 25  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  # seconds exponential multiplier
POLITE_DELAY = 0.4  # seconds delay between requests

# Proxy Configuration (Cloudflare WARP proxy on port 40000 bypasses Akamai datacenter geoblock)
PROXY_URL = os.environ.get("PROXY_URL", "").strip()
if not PROXY_URL:
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        if sock.connect_ex(("127.0.0.1", 40000)) == 0:
            PROXY_URL = "socks5://127.0.0.1:40000"
        sock.close()
    except Exception:
        pass

PROXIES = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

# Anti-Bot Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.myntra.com/",
    "Connection": "keep-alive",
    "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

BASE_URL = "https://www.myntra.com"
