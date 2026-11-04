"""Giai đoạn 3a — Dựng database và nạp 9 file CSV vào tầng staging.

Nguyên tắc: tầng staging là **bản sao nguyên trạng**. Mọi cột được đọc dưới dạng
chuỗi (dtype=str) để không có bất kỳ phép ép kiểu nào làm thay đổi giá trị gốc.

Chạy:
    python -m src.etl.build_db
"""

from __future__ import annotations

import sqlite3
import time

import pandas as pd

from .config import DB_PATH, SQL_DIR
from .util import force_utf8_stdout

# (tên bảng staging, tên file CSV)
STAGING_LOAD_ORDER: list[tuple[str, str]] = [
    ("stg_customers", "olist_customers_dataset.csv"),
    ("stg_geolocation", "olist_geolocation_dataset.csv"),
    ("stg_products", "olist_products_dataset.csv"),
    ("stg_sellers", "olist_sellers_dataset.csv"),
    ("stg_category_translation", "product_category_name_translation.csv"),
    ("stg_orders", "olist_orders_dataset.csv"),
    ("stg_order_items", "olist_order_items_dataset.csv"),
    ("stg_order_payments", "olist_order_payments_dataset.csv"),
    ("stg_order_reviews", "olist_order_reviews_dataset.csv"),
]


def main() -> None:
    force_utf8_stdout()

    raw_dir = DB_PATH.parent.parent / "raw"
    missing = [f for _, f in STAGING_LOAD_ORDER if not (raw_dir / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"Thiếu {len(missing)} file CSV trong {raw_dir}. "
            "Chạy trước: python -m src.etl.download_data"
        )

    if DB_PATH.exists():
        DB_PATH.unlink()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    line = "=" * 74
    print(line)
    print("DỰNG DATABASE + NẠP STAGING (GIAI ĐOẠN 3a)")
    print(line)
    print(f"Database: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")

        schema_sql = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()
        print("Đã tạo schema.\n")

        total_rows = 0
        for i, (table, filename) in enumerate(STAGING_LOAD_ORDER, start=1):
            t0 = time.perf_counter()
            df = pd.read_csv(raw_dir / filename, dtype=str, keep_default_na=False, na_values=[""])

            df.to_sql(table, conn, if_exists="append", index=False, chunksize=10_000)

            n_rows = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            elapsed = time.perf_counter() - t0
            total_rows += n_rows
            print(
                f"[{i}/{len(STAGING_LOAD_ORDER)}] {table:<24} "
                f"{n_rows:>9,} dòng x {df.shape[1]:>2} cột   ({elapsed:5.1f}s)"
            )

        conn.commit()

        print()
        print(line)
        print(f"TỔNG: {total_rows:,} dòng trong {len(STAGING_LOAD_ORDER)} bảng staging")
        size_mb = DB_PATH.stat().st_size / 1e6
        print(f"Dung lượng database: {size_mb:.1f} MB")
        print(line)
    finally:
        conn.close()

    print("\nBước tiếp theo: python -m src.etl.transform")


if __name__ == "__main__":
    main()
