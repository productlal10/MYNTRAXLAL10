#!/usr/bin/env python3

import os
from typing import Iterable

import psycopg2
from psycopg2.extras import execute_values


PRODUCT_COLUMNS = [
    "product_id",
    "sku",
    "brand",
    "is_myntra_label",
    "brand_type",
    "title",
    "category",
    "sub_category",
    "gender",
    "product_url",
    "mrp",
    "selling_price",
    "discount_percentage",
    "is_in_stock",
    "fit",
    "fabric",
    "pattern",
    "primary_color",
    "color_hex",
    "average_rating",
    "total_ratings_count",
    "total_reviews_count",
    "full_data_json",
    "updated_at",
]


def _connect(prefix: str):
    return psycopg2.connect(
        host=os.environ[f"{prefix}_PG_HOST"],
        port=os.environ[f"{prefix}_PG_PORT"],
        user=os.environ[f"{prefix}_PG_USER"],
        password=os.environ[f"{prefix}_PG_PASSWORD"],
        dbname=os.environ[f"{prefix}_PG_DBNAME"],
    )


def _batched(rows: Iterable[tuple], size: int):
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def main():
    batch_size = int(os.environ.get("SYNC_BATCH_SIZE", "1000"))
    source_conn = _connect("LOCAL")
    target_conn = _connect("REMOTE")
    source_cur = source_conn.cursor()
    target_cur = target_conn.cursor()

    source_cur.execute(
        f"SELECT {', '.join(PRODUCT_COLUMNS)} FROM products ORDER BY product_id"
    )

    target_cur.execute(
        """
        CREATE TEMP TABLE tmp_products_sync
        (LIKE products INCLUDING DEFAULTS INCLUDING IDENTITY)
        ON COMMIT DROP;
        """
    )

    copied = 0
    for batch in _batched(source_cur, batch_size):
        execute_values(
            target_cur,
            f"INSERT INTO tmp_products_sync ({', '.join(PRODUCT_COLUMNS)}) VALUES %s",
            batch,
            page_size=batch_size,
        )
        copied += len(batch)
        print(f"staged {copied} products", flush=True)

    update_assignments = ", ".join(
        f"{col} = EXCLUDED.{col}" for col in PRODUCT_COLUMNS if col != "product_id"
    )
    target_cur.execute(
        f"""
        INSERT INTO products ({', '.join(PRODUCT_COLUMNS)})
        SELECT {', '.join(PRODUCT_COLUMNS)}
        FROM tmp_products_sync
        ON CONFLICT (product_id) DO UPDATE
        SET {update_assignments};
        """
    )
    target_conn.commit()
    print(f"synced {copied} products", flush=True)

    source_cur.close()
    target_cur.close()
    source_conn.close()
    target_conn.close()


if __name__ == "__main__":
    main()
