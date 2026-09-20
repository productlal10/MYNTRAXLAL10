#!/usr/bin/env python3

import os
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values


FIELDS_TO_SYNC = [
    "product_id",
    "full_data_json",
    "primary_color",
    "color_hex",
]


def _connect(prefix: str):
    return psycopg2.connect(
        host=os.environ[f"{prefix}_PG_HOST"],
        port=os.environ[f"{prefix}_PG_PORT"],
        user=os.environ[f"{prefix}_PG_USER"],
        password=os.environ[f"{prefix}_PG_PASSWORD"],
        dbname=os.environ[f"{prefix}_PG_DBNAME"],
    )


def main():
    batch_size = int(os.environ.get("REPAIR_BATCH_SIZE", "2000"))
    broken_pattern = '%"primary_image": "https://assets.myntassets.com/h_720"%'
    backup_table = f"products_media_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    source_conn = _connect("LOCAL")
    remote_conn = _connect("REMOTE")
    source_cur = source_conn.cursor()
    remote_cur = remote_conn.cursor()

    remote_cur.execute(
        """
        SELECT product_id
        FROM products
        WHERE full_data_json LIKE %s
        ORDER BY product_id
        """,
        (broken_pattern,),
    )
    affected_ids = [row[0] for row in remote_cur.fetchall()]
    print(f"affected_rows={len(affected_ids)}", flush=True)
    if not affected_ids:
        return

    remote_cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {backup_table} AS
        SELECT product_id, full_data_json, primary_color, color_hex, NOW() AS backed_up_at
        FROM products
        WHERE 1 = 0;
        """
    )
    remote_cur.execute(
        f"""
        INSERT INTO {backup_table} (product_id, full_data_json, primary_color, color_hex, backed_up_at)
        SELECT product_id, full_data_json, primary_color, color_hex, NOW()
        FROM products
        WHERE product_id = ANY(%s);
        """,
        (affected_ids,),
    )
    remote_conn.commit()
    print(f"backup_table={backup_table}", flush=True)

    remote_cur.execute(
        """
        CREATE TEMP TABLE tmp_media_repair (
            product_id BIGINT PRIMARY KEY,
            full_data_json TEXT,
            primary_color TEXT,
            color_hex TEXT
        ) ON COMMIT DROP;
        """
    )

    copied = 0
    for start in range(0, len(affected_ids), batch_size):
        batch_ids = affected_ids[start:start + batch_size]
        source_cur.execute(
            """
            SELECT product_id, full_data_json, primary_color, color_hex
            FROM products
            WHERE product_id = ANY(%s)
            """,
            (batch_ids,),
        )
        rows = source_cur.fetchall()
        if not rows:
            continue
        execute_values(
            remote_cur,
            """
            INSERT INTO tmp_media_repair (product_id, full_data_json, primary_color, color_hex)
            VALUES %s
            ON CONFLICT (product_id) DO UPDATE
            SET full_data_json = EXCLUDED.full_data_json,
                primary_color = EXCLUDED.primary_color,
                color_hex = EXCLUDED.color_hex
            """,
            rows,
            page_size=batch_size,
        )
        copied += len(rows)
        print(f"staged_rows={copied}", flush=True)

    remote_cur.execute(
        """
        UPDATE products p
        SET full_data_json = t.full_data_json,
            primary_color = t.primary_color,
            color_hex = t.color_hex
        FROM tmp_media_repair t
        WHERE p.product_id = t.product_id;
        """
    )
    remote_cur.execute("ANALYZE products;")
    remote_cur.execute("ANALYZE product_sizes;")
    remote_cur.execute("ANALYZE daily_inventory_snapshots;")
    remote_cur.execute("ANALYZE daily_sales_analytics;")
    remote_conn.commit()
    print(f"repaired_rows={copied}", flush=True)

    source_cur.close()
    remote_cur.close()
    source_conn.close()
    remote_conn.close()


if __name__ == "__main__":
    main()
