#!/usr/bin/env python3

import os
import tempfile
from datetime import datetime

import psycopg2


def _connect(prefix: str):
    return psycopg2.connect(
        host=os.environ[f"{prefix}_PG_HOST"],
        port=os.environ[f"{prefix}_PG_PORT"],
        user=os.environ[f"{prefix}_PG_USER"],
        password=os.environ[f"{prefix}_PG_PASSWORD"],
        dbname=os.environ[f"{prefix}_PG_DBNAME"],
    )


def main():
    broken_pattern = '%"primary_image": "https://assets.myntassets.com/h_720"%'
    backup_table = f"products_media_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    local_conn = _connect("LOCAL")
    remote_conn = _connect("REMOTE")
    local_cur = local_conn.cursor()
    remote_cur = remote_conn.cursor()

    remote_cur.execute(
        """
        SELECT COUNT(*)
        FROM products
        WHERE full_data_json LIKE %s
        """,
        (broken_pattern,),
    )
    affected_count = int(remote_cur.fetchone()[0] or 0)
    print(f"affected_rows={affected_count}", flush=True)
    if not affected_count:
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
        WHERE full_data_json LIKE %s;
        """,
        (broken_pattern,),
    )
    remote_conn.commit()
    print(f"backup_table={backup_table}", flush=True)

    remote_cur.execute(
        """
        CREATE TEMP TABLE tmp_media_repair_all (
            product_id BIGINT PRIMARY KEY,
            full_data_json TEXT,
            primary_color TEXT,
            color_hex TEXT
        ) ON COMMIT DROP;
        """
    )

    with tempfile.NamedTemporaryFile(mode="w+b", suffix=".csv") as tmp:
        export_sql = """
            COPY (
                SELECT product_id, full_data_json, primary_color, color_hex
                FROM products
                ORDER BY product_id
            )
            TO STDOUT WITH CSV
        """
        local_cur.copy_expert(export_sql, tmp)
        tmp.flush()
        size_mb = tmp.tell() / (1024 * 1024)
        print(f"exported_mb={size_mb:.1f}", flush=True)
        tmp.seek(0)
        remote_cur.copy_expert(
            """
            COPY tmp_media_repair_all (product_id, full_data_json, primary_color, color_hex)
            FROM STDIN WITH CSV
            """,
            tmp,
        )

    remote_cur.execute(
        f"""
        UPDATE products p
        SET full_data_json = t.full_data_json,
            primary_color = t.primary_color,
            color_hex = t.color_hex
        FROM tmp_media_repair_all t
        JOIN {backup_table} b ON b.product_id = t.product_id
        WHERE p.product_id = t.product_id;
        """
    )
    print(f"updated_rows={remote_cur.rowcount}", flush=True)

    remote_cur.execute("ANALYZE products;")
    remote_cur.execute("ANALYZE product_sizes;")
    remote_cur.execute("ANALYZE daily_inventory_snapshots;")
    remote_cur.execute("ANALYZE daily_sales_analytics;")
    remote_conn.commit()
    print("analyze_complete=true", flush=True)

    local_cur.close()
    remote_cur.close()
    local_conn.close()
    remote_conn.close()


if __name__ == "__main__":
    main()
