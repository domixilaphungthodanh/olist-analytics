"""Giai đoạn 4 — Kiểm tra chất lượng dữ liệu.

Sinh ra 2 bảng:
    mart_data_quality          : từng luật kiểm tra + kết quả
    mart_data_quality_summary  : tổng hợp PASS / FAIL / INFO

Bốn nhóm kiểm tra:
    A. Số dòng      — staging có đủ số dòng như file CSV gốc
    B. Toàn vẹn gốc — hash từng dòng, chứng minh staging KHÔNG sửa giá trị nào
    C. Khoá ngoại   — không có orphan
    D. Nghiệp vụ    — các ràng buộc logic của star schema

Chạy:
    python -m src.etl.validate
"""

from __future__ import annotations

import sqlite3
import sys

import pandas as pd

from .config import DATA_RAW, DB_PATH, NON_REVENUE_STATUSES
from .util import force_utf8_stdout

RAW_FILES: dict[str, str] = {
    "stg_customers": "olist_customers_dataset.csv",
    "stg_geolocation": "olist_geolocation_dataset.csv",
    "stg_products": "olist_products_dataset.csv",
    "stg_sellers": "olist_sellers_dataset.csv",
    "stg_category_translation": "product_category_name_translation.csv",
    "stg_orders": "olist_orders_dataset.csv",
    "stg_order_items": "olist_order_items_dataset.csv",
    "stg_order_payments": "olist_order_payments_dataset.csv",
    "stg_order_reviews": "olist_order_reviews_dataset.csv",
}

results: list[dict] = []


def add(group: str, name: str, status: str, expected, actual, detail: str = "") -> None:
    results.append(
        {
            "check_group": group,
            "check_name": name,
            "status": status,
            "expected": "" if expected is None else str(expected),
            "actual": "" if actual is None else str(actual),
            "detail": detail,
        }
    )


def check_equal(group: str, name: str, expected, actual, detail: str = "") -> None:
    add(group, name, "PASS" if expected == actual else "FAIL", expected, actual, detail)


def check_close(group: str, name: str, expected: float, actual: float, tol: float = 0.01) -> None:
    """So sánh số thực có sai số — tránh false-fail do thứ tự cộng số thực."""
    ok = abs(expected - actual) <= tol
    add(
        group, name, "PASS" if ok else "FAIL",
        f"{expected:,.2f}", f"{actual:,.2f}", f"sai lệch {abs(expected - actual):.6f}",
    )


def main() -> None:
    force_utf8_stdout()
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Chưa có database: {DB_PATH}")

    line = "=" * 74
    print(line)
    print("KIỂM TRA CHẤT LƯỢNG DỮ LIỆU (GIAI ĐOẠN 4)")
    print(line)

    conn = sqlite3.connect(DB_PATH)
    n_fail = 0
    try:
        q = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731

        # =====================================================================
        # A. SỐ DÒNG: staging == file CSV
        # =====================================================================
        print("\nA. Số dòng staging so với file CSV gốc")
        for table, filename in RAW_FILES.items():
            # Đếm BẢN GHI (không đếm dòng vật lý): file reviews có 5.495 dòng vật lý
            # dư ra vì nội dung bình luận chứa ký tự xuống dòng trong dấu ngoặc kép.
            path = DATA_RAW / filename
            csv_rows = sum(
                len(chunk)
                for chunk in pd.read_csv(
                    path, dtype=str, keep_default_na=False, na_values=[""],
                    chunksize=100_000,
                )
            )
            stg_rows = q(f"SELECT COUNT(*) FROM {table}")
            check_equal("A. row_count", f"{table} = {csv_rows:,} dòng", csv_rows, stg_rows)
            marker = "OK" if csv_rows == stg_rows else "SAI"
            print(f"   {table:<26} {stg_rows:>9,}  {marker}")

        # =====================================================================
        # B. TOÀN VẸN GỐC: hash từng dòng
        # =====================================================================
        print("\nB. Toàn vẹn dữ liệu gốc (hash từng dòng, không sửa giá trị nào)")
        for table, filename in RAW_FILES.items():
            csv_df = pd.read_csv(
                DATA_RAW / filename, dtype=str, keep_default_na=False, na_values=[""]
            )
            stg_df = pd.read_sql_query(f"SELECT * FROM {table}", conn)

            # Chuẩn hoá NaN/None về chuỗi rỗng ở cả hai phía rồi mới hash
            h_csv = int(
                pd.util.hash_pandas_object(
                    csv_df.fillna("").astype(str), index=False
                ).sum()
            )
            h_stg = int(
                pd.util.hash_pandas_object(
                    stg_df.fillna("").astype(str), index=False
                ).sum()
            )
            same = h_csv == h_stg
            add(
                "B. raw_fidelity",
                f"{table} giữ nguyên 100% giá trị gốc",
                "PASS" if same else "FAIL",
                h_csv,
                h_stg,
                f"{len(csv_df):,} dòng",
            )
            print(f"   {table:<26} {'GIỐNG HỆT' if same else 'KHÁC (!)'}")

        # =====================================================================
        # C. KHOÁ NGOẠI
        # =====================================================================
        print("\nC. Toàn vẹn khoá ngoại (orphan)")
        fk_checks = [
            ("fact_orders -> dim_customer",
             "SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_customer d "
             "ON d.customer_unique_id = f.customer_unique_id WHERE d.customer_unique_id IS NULL"),
            ("fact_orders -> dim_date",
             "SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_date d "
             "ON d.date = f.order_date WHERE d.date IS NULL"),
            ("fact_order_items -> fact_orders",
             "SELECT COUNT(*) FROM fact_order_items i LEFT JOIN fact_orders o "
             "ON o.order_id = i.order_id WHERE o.order_id IS NULL"),
            ("fact_order_items -> dim_product",
             "SELECT COUNT(*) FROM fact_order_items i LEFT JOIN dim_product p "
             "ON p.product_id = i.product_id WHERE p.product_id IS NULL"),
            ("fact_order_items -> dim_seller",
             "SELECT COUNT(*) FROM fact_order_items i LEFT JOIN dim_seller s "
             "ON s.seller_id = i.seller_id WHERE s.seller_id IS NULL"),
            ("fact_payments -> fact_orders",
             "SELECT COUNT(*) FROM fact_payments p LEFT JOIN fact_orders o "
             "ON o.order_id = p.order_id WHERE o.order_id IS NULL"),
        ]
        for name, sql in fk_checks:
            orphan = q(sql)
            check_equal("C. foreign_key", name, 0, orphan)
            print(f"   {name:<40} orphan={orphan:<6} {'OK' if orphan == 0 else 'SAI'}")

        # =====================================================================
        # D. NGHIỆP VỤ
        # =====================================================================
        print("\nD. Ràng buộc nghiệp vụ")
        n_orders = q("SELECT COUNT(*) FROM stg_orders")
        n_items = q("SELECT COUNT(*) FROM stg_order_items")
        n_payments = q("SELECT COUNT(*) FROM stg_order_payments")

        check_equal("D. business", "fact_orders cùng số dòng với stg_orders",
                    n_orders, q("SELECT COUNT(*) FROM fact_orders"))
        check_equal("D. business", "fact_order_items cùng số dòng với stg_order_items",
                    n_items, q("SELECT COUNT(*) FROM fact_order_items"))
        check_equal("D. business", "fact_payments cùng số dòng với stg_order_payments",
                    n_payments, q("SELECT COUNT(*) FROM fact_payments"))

        items_sum = q("SELECT SUM(items_count) FROM fact_orders")
        check_equal("D. business", "tổng items_count = số dòng hàng", n_items, items_sum)

        # tổng tiền phải khớp tuyệt đối
        stg_total = q(
            "SELECT SUM(CAST(price AS REAL) + CAST(freight_value AS REAL)) "
            "FROM stg_order_items"
        )
        fact_total = q("SELECT SUM(order_total) FROM fact_orders")
        check_close("D. business", "tổng order_total = tổng price + freight",
                    float(stg_total), float(fact_total))
        print(f"   {'Tiền hàng + ship (stg)':<40} {stg_total:>16,.2f} BRL")
        print(f"   {'Tiền hàng + ship (fact)':<40} {fact_total:>16,.2f} BRL")

        # is_late chỉ có giá trị khi có đủ 2 mốc ngày
        bad_late = q(
            "SELECT COUNT(*) FROM fact_orders "
            "WHERE (delivered_ts IS NULL OR estimated_ts IS NULL) AND is_late IS NOT NULL"
        )
        check_equal("D. business", "is_late chỉ có giá trị khi đủ 2 mốc ngày", 0, bad_late)

        # cờ doanh thu
        n_non_rev = q(
            "SELECT COUNT(*) FROM stg_orders WHERE order_status IN ("
            + ",".join(f"'{s}'" for s in NON_REVENUE_STATUSES)
            + ")"
        )
        check_equal("D. business", "số đơn KHÔNG tính doanh thu (canceled + unavailable)",
                    n_non_rev, q("SELECT COUNT(*) FROM fact_orders WHERE is_revenue_order = 0"))

        # giá trị âm
        check_equal("D. business", "không có price âm",
                    0, q("SELECT COUNT(*) FROM fact_order_items WHERE price < 0"))
        check_equal("D. business", "không có freight âm",
                    0, q("SELECT COUNT(*) FROM fact_order_items WHERE freight_value < 0"))
        check_equal("D. business", "không có payment âm",
                    0, q("SELECT COUNT(*) FROM fact_payments WHERE payment_value < 0"))

        # review trong khoảng 1..5
        bad_review = q(
            "SELECT COUNT(*) FROM fact_orders "
            "WHERE review_score IS NOT NULL AND (review_score < 1 OR review_score > 5)"
        )
        check_equal("D. business", "review_score nằm trong 1..5", 0, bad_review)

        # thời gian không âm
        bad_lead = q("SELECT COUNT(*) FROM fact_orders WHERE lead_time_days < 0 AND lead_time_days IS NOT NULL")
        check_equal("D. business", "lead_time_days không âm", 0, bad_lead)

        # dim unique
        check_equal("D. business", "dim_customer duy nhất theo customer_unique_id",
                    q("SELECT COUNT(*) FROM dim_customer"),
                    q("SELECT COUNT(DISTINCT customer_unique_id) FROM dim_customer"))

        # toạ độ trong lãnh thổ Brazil
        bad_geo = q(
            "SELECT COUNT(*) FROM dim_geolocation "
            "WHERE lat < -34 OR lat > 6 OR lng < -74 OR lng > -34"
        )
        check_equal("D. business", "toạ độ dim_geolocation nằm trong Brazil", 0, bad_geo)

        # không còn danh mục 'unknown' do thiếu bản dịch (bẫy B6)
        unknown = q(
            "SELECT COUNT(*) FROM dim_product "
            "WHERE category_en = 'unknown' AND category_pt IS NOT NULL"
        )
        check_equal("D. business", "0 sản phẩm bị 'unknown' do thiếu bản dịch", 0, unknown)

        # mỗi đơn chỉ có đúng 1 dòng trong fact_orders
        check_equal("D. business", "fact_orders.order_id duy nhất",
                    q("SELECT COUNT(*) FROM fact_orders"),
                    q("SELECT COUNT(DISTINCT order_id) FROM fact_orders"))

        # =====================================================================
        # E. THÔNG TIN ĐÃ BIẾT (INFO, không phải lỗi)
        # =====================================================================
        print("\nE. Đặc điểm đã biết — ghi nhận, KHÔNG phải lỗi")
        # File reviews: dòng vật lý nhiều hơn bản ghi vì comment có ký tự xuống dòng
        with open(DATA_RAW / "olist_order_reviews_dataset.csv", encoding="utf-8") as fh:
            physical_lines = sum(1 for _ in fh) - 1
        add(
            "E. info",
            "dòng vật lý dư trong file reviews (comment nhiều dòng)",
            "INFO",
            None,
            physical_lines - 99_224,
            f"{physical_lines:,} dòng vật lý / 99.224 bản ghi",
        )
        print(f"   {'dòng vật lý dư trong file reviews':<52} {physical_lines - 99_224:>7,}")

        info_checks = [
            ("đơn không có dòng hàng nào (canceled/unavailable)",
             "SELECT COUNT(*) FROM fact_orders WHERE items_count = 0"),
            ("đơn nằm ngoài cửa sổ phân tích 2017-01..2018-08",
             "SELECT COUNT(*) FROM fact_orders WHERE in_analysis_window = 0"),
            ("đơn có nhiều hơn 1 review trong dữ liệu gốc", None),
            ("dòng hàng không tính được khoảng cách (thiếu mã zip)",
             "SELECT COUNT(*) FROM fact_order_items WHERE distance_km IS NULL"),
        ]
        for name, sql in info_checks:
            if sql is None:
                n = 547  # đo ở transform
            else:
                n = q(sql)
            add("E. info", name, "INFO", None, n)
            print(f"   {name:<52} {n:>7,}")

        # =====================================================================
        # GHI KẾT QUẢ
        # =====================================================================
        dq = pd.DataFrame(results)
        dq.to_sql("mart_data_quality", conn, if_exists="replace", index=False)

        summary = (
            dq.groupby(["check_group", "status"], as_index=False)
            .size()
            .rename(columns={"size": "n_checks"})
        )
        summary.to_sql("mart_data_quality_summary", conn, if_exists="replace", index=False)
        conn.commit()

        n_pass = int((dq["status"] == "PASS").sum())
        n_fail = int((dq["status"] == "FAIL").sum())
        n_info = int((dq["status"] == "INFO").sum())

        print("\n" + line)
        print(f"KẾT QUẢ: {n_pass} PASS | {n_fail} FAIL | {n_info} INFO")
        if n_fail:
            print("\nCác luật KHÔNG ĐẠT:")
            for _, r in dq[dq["status"] == "FAIL"].iterrows():
                print(f"  - [{r['check_group']}] {r['check_name']}")
                print(f"      kỳ vọng={r['expected']}  thực tế={r['actual']}")
        print(line)
        print("Bảng kết quả: mart_data_quality, mart_data_quality_summary")
    finally:
        conn.close()

    if n_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
