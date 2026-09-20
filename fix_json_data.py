"""
One-time migration: rebuild full_data_json from individual product columns + extract images from old format.
Processes in batches of 2000.
"""
import json
import re
import psycopg2
import psycopg2.extras

PG_DSN = {
    'host': '127.0.0.1',
    'port': 5432,
    'user': 'postgres',
    'password': 'alan1234',
    'dbname': 'myntra'
}


def extract_images_from_old_format(old_str: str):
    """Extract image URLs from the unquoted custom format using regex."""
    if not old_str:
        return "", []
    imgs = re.findall(r'https://assets\.myntassets\.com/[^\s,\]\}]+', old_str)
    imgs = [i.rstrip('.,]})') for i in imgs]
    primary = imgs[0] if imgs else ""
    gallery = imgs[1:] if len(imgs) > 1 else []
    return primary, gallery


def extract_field(old_str: str, field_name: str) -> str:
    """Extract a simple string field value from the old format."""
    pattern = rf'{re.escape(field_name)}:\s*([^,\{{\}}]+?)(?=[,\{{\}}]|$)'
    m = re.search(pattern, old_str)
    if m:
        val = m.group(1).strip().strip('"').strip("'")
        return val if val not in ('null', 'None', '') else ''
    return ''


def rebuild_json(row, old_json_str: str) -> str:
    """Build a proper JSON blob from individual product columns + extract images from old format."""
    (product_id, sku, brand, is_myntra_label, brand_type, title, category,
     sub_category, gender, product_url, mrp, selling_price, discount_percentage,
     primary_color, color_hex, is_in_stock, average_rating, total_ratings_count,
     total_reviews_count, fit, fabric, pattern) = row

    primary_img, gallery = extract_images_from_old_format(old_json_str)

    data = {
        "product_info": {
            "product_id": product_id,
            "sku": sku or f"M{product_id}",
            "brand": brand or "",
            "is_myntra_label": bool(is_myntra_label),
            "brand_type": brand_type or ("Myntra In-House Label" if is_myntra_label else "Non-Myntra Brand"),
            "title": title or "",
            "category": category or "",
            "sub_category": sub_category or "",
            "gender": gender or "",
            "product_url": product_url or "",
            "primary_color": primary_color or "",
            "color_hex": color_hex or "#0f172a",
        },
        "pricing": {
            "mrp": float(mrp or 0),
            "selling_price": float(selling_price or 0),
            "discount_percentage": float(discount_percentage or 0),
            "currency": "INR",
            "taxes_included": True,
            "available_offers": []
        },
        "media": {
            "primary_image": primary_img,
            "image_gallery": gallery,
            "video_url": None
        },
        "inventory_and_sizes": {
            "is_in_stock": bool(is_in_stock),
            "sizes_available": [],
            "fit": fit or "",
            "model_sizing": ""
        },
        "specifications": {
            "fabric": fabric or "",
            "pattern": pattern or "",
            "fit": fit or ""
        },
        "ratings_and_reviews": {
            "average_rating": float(average_rating or 0),
            "total_ratings_count": int(total_ratings_count or 0),
            "total_reviews_count": int(total_reviews_count or 0)
        }
    }
    return json.dumps(data, ensure_ascii=False)


def main():
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(**PG_DSN)
    conn.autocommit = False
    read_cur = conn.cursor('streaming_cursor', cursor_factory=psycopg2.extras.DictCursor)
    update_cur = conn.cursor()

    # Count needing fix
    count_cur = conn.cursor()
    count_cur.execute("SELECT COUNT(*) FROM products WHERE full_data_json NOT LIKE '{\"product_info\"%'")
    needs_fix = count_cur.fetchone()[0]
    print(f"Products needing JSON rebuild: {needs_fix:,}")

    if needs_fix == 0:
        print("All products already have valid JSON. Done.")
        conn.close()
        return

    read_cur.execute("""
        SELECT product_id, sku, brand, is_myntra_label, brand_type, title, category,
               sub_category, gender, product_url, mrp, selling_price, discount_percentage,
               primary_color, color_hex, is_in_stock, average_rating, total_ratings_count,
               total_reviews_count, fit, fabric, pattern,
               full_data_json
        FROM products
        WHERE full_data_json NOT LIKE '{"product_info"%'
        ORDER BY product_id
    """)

    batch_size = 2000
    updated = 0
    batch = []

    for row in read_cur:
        old_json = row['full_data_json'] or ''
        col_row = (
            row['product_id'], row['sku'], row['brand'], row['is_myntra_label'],
            row['brand_type'], row['title'], row['category'], row['sub_category'],
            row['gender'], row['product_url'], row['mrp'], row['selling_price'],
            row['discount_percentage'], row['primary_color'], row['color_hex'],
            row['is_in_stock'], row['average_rating'], row['total_ratings_count'],
            row['total_reviews_count'], row['fit'], row['fabric'], row['pattern']
        )
        new_json = rebuild_json(col_row, old_json)
        batch.append((new_json, row['product_id']))

        if len(batch) >= batch_size:
            psycopg2.extras.execute_batch(
                update_cur,
                "UPDATE products SET full_data_json = %s WHERE product_id = %s",
                batch,
                page_size=500
            )
            conn.commit()
            updated += len(batch)
            batch = []
            pct = (updated / needs_fix * 100) if needs_fix > 0 else 100
            print(f"  Updated {updated:,}/{needs_fix:,} ({pct:.1f}%)", flush=True)

    if batch:
        psycopg2.extras.execute_batch(
            update_cur,
            "UPDATE products SET full_data_json = %s WHERE product_id = %s",
            batch,
            page_size=500
        )
        conn.commit()
        updated += len(batch)

    print(f"\nMigration complete. Total updated: {updated:,}")
    count_cur.execute("SELECT COUNT(*) FROM products WHERE full_data_json LIKE '{\"product_info\"%'")
    valid_count = count_cur.fetchone()[0]
    print(f"Products with valid JSON: {valid_count:,}")
    conn.close()


if __name__ == "__main__":
    main()
