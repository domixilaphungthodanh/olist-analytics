"""Giai đoạn 3b — Biến đổi staging thành star schema (dim_* / fact_*).

Xử lý 6 bẫy đã phát hiện:
  B1  customer_id -> customer_unique_id
  B2  dedupe review (547 đơn có nhiều review)
  B4  gộp geolocation theo zip (1.000.163 dòng -> ~19.015)
  B5  loại toạ độ ngoài lãnh thổ Brazil
  B6  bổ sung 2 danh mục thiếu bản dịch
  B7  gắn cờ cửa sổ phân tích

Chạy:
    python -m src.etl.transform
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from .config import (
    ANALYSIS_END,
    ANALYSIS_START,
    BRAZIL_BBOX,
    DB_PATH,
    MANUAL_CATEGORY_EN,
    NON_REVENUE_STATUSES,
)
from .util import force_utf8_stdout

EARTH_RADIUS_KM = 6371.0

DATE_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def read_table(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    return pd.read_sql_query(f"SELECT * FROM {table}", conn)


def haversine_km(lat1, lon1, lat2, lon2):
    """Khoảng cách đường chim bay giữa 2 toạ độ (km)."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def build_dim_date(conn: sqlite3.Connection) -> pd.DataFrame:
    """Sinh lịch từ 2016-09-01 tới 2018-11-30 (phủ toàn bộ dải ngày của dữ liệu)."""
    days = pd.date_range("2016-09-01", "2018-11-30", freq="D")
    df = pd.DataFrame({"date": days})
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["period"] = df["date"].dt.strftime("%Y-%m")
    df["week"] = df["date"].dt.isocalendar().week.astype(int)
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_name"] = df["date"].dt.strftime("%a")
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df


def build_dim_geolocation(stg_geo: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """B4 + B5: lọc toạ độ sai rồi gộp theo mã zip."""
    geo = stg_geo.copy()
    geo["lat"] = pd.to_numeric(geo["geolocation_lat"], errors="coerce")
    geo["lng"] = pd.to_numeric(geo["geolocation_lng"], errors="coerce")
    geo["zip"] = geo["geolocation_zip_code_prefix"].astype(str)

    rows_before = len(geo)
    valid = (
        geo["lat"].between(BRAZIL_BBOX["lat_min"], BRAZIL_BBOX["lat_max"])
        & geo["lng"].between(BRAZIL_BBOX["lng_min"], BRAZIL_BBOX["lng_max"])
    )
    geo = geo[valid].copy()
    dropped = rows_before - len(geo)

    agg = geo.groupby("zip", as_index=False).agg(
        lat=("lat", "mean"),
        lng=("lng", "mean"),
        point_count=("lat", "size"),
    )

    # city/state: lấy giá trị xuất hiện nhiều nhất trong mỗi zip
    for col, out in (("geolocation_city", "city"), ("geolocation_state", "state")):
        top = (
            geo.groupby(["zip", col], as_index=False)
            .size()
            .sort_values(["zip", "size"], ascending=[True, False])
            .drop_duplicates("zip")[["zip", col]]
            .rename(columns={col: out})
        )
        agg = agg.merge(top, on="zip", how="left")

    agg = agg.rename(columns={"zip": "zip_code_prefix"})
    agg["lat"] = agg["lat"].round(6)
    agg["lng"] = agg["lng"].round(6)
    return agg, {"rows_before": rows_before, "rows_dropped": dropped, "zips": len(agg)}


def build_dim_customer(stg_cust: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """B1: gộp về đúng 1 dòng / con người (customer_unique_id)."""
    cust = stg_cust.copy()

    # Kiểm tra 1 người có bị ghi nhiều city/state khác nhau không
    nunique = cust.groupby("customer_unique_id")[["customer_city", "customer_state"]].nunique()
    inconsistent = int((nunique > 1).any(axis=1).sum())

    dim = (
        cust.sort_values("customer_id")
        .drop_duplicates("customer_unique_id", keep="first")
        .rename(
            columns={
                "customer_city": "city",
                "customer_state": "state",
                "customer_zip_code_prefix": "zip_code_prefix",
            }
        )[["customer_unique_id", "city", "state", "zip_code_prefix"]]
        .reset_index(drop=True)
    )
    dim["zip_code_prefix"] = dim["zip_code_prefix"].astype(str)
    return dim, {"rows": len(dim), "inconsistent": inconsistent}


def build_dim_product(stg_prod: pd.DataFrame, stg_trans: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """B6: bổ sung 2 danh mục thiếu bản dịch."""
    prod = stg_prod.copy()
    for col in ["product_photos_qty", "product_weight_g", "product_length_cm",
                "product_height_cm", "product_width_cm"]:
        prod[col] = pd.to_numeric(prod[col], errors="coerce").astype("Int64")

    mapping = dict(
        zip(stg_trans["product_category_name"], stg_trans["product_category_name_english"])
    )
    mapping.update(MANUAL_CATEGORY_EN)  # 2 danh mục thiếu

    prod["category_en"] = prod["product_category_name"].map(mapping)
    missing_after = int(prod["category_en"].isna().sum())
    prod["category_en"] = prod["category_en"].fillna("unknown")

    dim = pd.DataFrame(
        {
            "product_id": prod["product_id"],
            "category_pt": prod["product_category_name"],
            "category_en": prod["category_en"],
            "photos_qty": prod["product_photos_qty"],
            "weight_g": prod["product_weight_g"],
            "length_cm": prod["product_length_cm"],
            "height_cm": prod["product_height_cm"],
            "width_cm": prod["product_width_cm"],
            "volume_cm3": (
                prod["product_length_cm"].astype("Float64")
                * prod["product_height_cm"].astype("Float64")
                * prod["product_width_cm"].astype("Float64")
            ).round(2),
            "has_category": prod["product_category_name"].notna().astype(int),
        }
    )
    return dim, {"missing_after": missing_after}


def build_dim_seller(stg_seller: pd.DataFrame) -> pd.DataFrame:
    dim = stg_seller.rename(
        columns={
            "seller_city": "city",
            "seller_state": "state",
            "seller_zip_code_prefix": "zip_code_prefix",
        }
    )[["seller_id", "city", "state", "zip_code_prefix"]].copy()
    dim["zip_code_prefix"] = dim["zip_code_prefix"].astype(str)
    return dim


def build_facts(
    stg_orders, stg_items, stg_payments, stg_reviews, stg_customers,
    dim_customer, dim_seller, dim_geo
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:

    info: dict = {}

    # ---------- orders: ép kiểu thời gian ----------
    orders = stg_orders.copy()
    for col in DATE_COLS:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")

    # ---------- items: tổng hợp về cấp đơn ----------
    items = stg_items.copy()
    items["order_item_id"] = pd.to_numeric(items["order_item_id"], errors="raise").astype(int)
    items["price"] = pd.to_numeric(items["price"], errors="raise")
    items["freight_value"] = pd.to_numeric(items["freight_value"], errors="raise")
    items["shipping_limit_ts"] = pd.to_datetime(items["shipping_limit_date"], errors="coerce")

    item_agg = items.groupby("order_id", as_index=False).agg(
        items_count=("order_item_id", "count"),
        order_price=("price", "sum"),
        order_freight=("freight_value", "sum"),
    )

    # ---------- payments: tổng hợp về cấp đơn ----------
    pay = stg_payments.copy()
    pay["payment_sequential"] = pd.to_numeric(pay["payment_sequential"]).astype(int)
    pay["installments"] = pd.to_numeric(pay["payment_installments"]).astype("Int64")
    pay["payment_value"] = pd.to_numeric(pay["payment_value"])

    pay_agg = pay.groupby("order_id", as_index=False).agg(
        payment_total=("payment_value", "sum"),
        max_installments=("installments", "max"),
    )
    # phương thức chiếm nhiều TIỀN nhất trong đơn
    by_type = (
        pay.groupby(["order_id", "payment_type"], as_index=False)["payment_value"]
        .sum()
        .sort_values(["order_id", "payment_value"], ascending=[True, False])
        .drop_duplicates("order_id")[["order_id", "payment_type"]]
        .rename(columns={"payment_type": "payment_type_main"})
    )

    # ---------- reviews: B2 dedupe, lấy review mới nhất ----------
    rev = stg_reviews.copy()
    rev["review_score"] = pd.to_numeric(rev["review_score"], errors="coerce").astype("Int64")
    rev["answer_ts"] = pd.to_datetime(rev["review_answer_timestamp"], errors="coerce")
    review_count = rev.groupby("order_id").size().rename("review_count").reset_index()
    rev_latest = (
        rev.sort_values(["order_id", "answer_ts"])
        .drop_duplicates("order_id", keep="last")[["order_id", "review_score"]]
    )
    info["multi_review_orders"] = int((review_count["review_count"] > 1).sum())

    # ---------- gộp tất cả vào fact_orders ----------
    f = orders.merge(
        stg_customers[["customer_id", "customer_unique_id"]], on="customer_id", how="left"
    )
    f = f.merge(item_agg, on="order_id", how="left")
    f = f.merge(pay_agg, on="order_id", how="left")
    f = f.merge(by_type, on="order_id", how="left")
    f = f.merge(review_count, on="order_id", how="left")
    f = f.merge(rev_latest, on="order_id", how="left")

    f["items_count"] = f["items_count"].fillna(0).astype(int)
    f["review_count"] = f["review_count"].fillna(0).astype(int)

    # customer_unique_id đã được merge ở trên (B1)

    # ---------- đo lường thời gian ----------
    day = pd.Timedelta(days=1)
    f["lead_time_days"] = (
        (f["order_delivered_customer_date"] - f["order_purchase_timestamp"]) / day
    ).round(2)
    f["handover_days"] = (
        (f["order_delivered_carrier_date"] - f["order_approved_at"]) / day
    ).round(2)
    f["transit_days"] = (
        (f["order_delivered_customer_date"] - f["order_delivered_carrier_date"]) / day
    ).round(2)

    # So sánh theo NGÀY, không theo giờ: ngày hứa luôn là 00:00:00, nên nếu so
    # theo giờ thì đơn giao lúc 15:00 cùng ngày sẽ bị coi là trễ 0,6 ngày.
    delivered_date = f["order_delivered_customer_date"].dt.normalize()
    estimated_date = f["order_estimated_delivery_date"].dt.normalize()
    f["delay_days"] = (delivered_date - estimated_date).dt.days.astype("Int64")
    f["buffer_days"] = (-f["delay_days"].astype("Float64")).astype("Int64")

    f["is_late"] = pd.array(
        np.where(f["delay_days"].isna(), pd.NA, (f["delay_days"] > 0).astype("Int64")),
        dtype="Int64",
    )

    # ---------- đo lường tiền ----------
    f["order_total"] = f["order_price"] + f["order_freight"]
    f["freight_ratio"] = np.where(
        f["order_total"] > 0, f["order_freight"] / f["order_total"], np.nan
    )

    # ---------- cờ nghiệp vụ ----------
    f["is_revenue_order"] = (~f["order_status"].isin(NON_REVENUE_STATUSES)).astype(int)
    f["order_date"] = f["order_purchase_timestamp"].dt.strftime("%Y-%m-%d")
    in_window = f["order_date"].between(ANALYSIS_START, ANALYSIS_END)
    f["in_analysis_window"] = in_window.astype(int)

    info["late_orders"] = int((f["is_late"] == 1).sum())
    info["late_pct"] = float((f["is_late"] == 1).mean() * 100)

    # Đổi tên mốc thời gian cho khớp schema và ép về chuỗi ISO
    ts_map = {
        "order_purchase_timestamp": "purchase_ts",
        "order_approved_at": "approved_ts",
        "order_delivered_carrier_date": "carrier_ts",
        "order_delivered_customer_date": "delivered_ts",
        "order_estimated_delivery_date": "estimated_ts",
    }
    for src, dst in ts_map.items():
        f[dst] = f[src].dt.strftime("%Y-%m-%d %H:%M:%S")

    fact_orders = f[
        [
            "order_id", "customer_unique_id", "order_date", "order_status",
            "purchase_ts", "approved_ts", "carrier_ts", "delivered_ts", "estimated_ts",
            "lead_time_days", "handover_days", "transit_days",
            "is_late", "delay_days", "buffer_days",
            "items_count", "order_price", "order_freight", "order_total",
            "freight_ratio",
            "review_score", "review_count",
            "payment_type_main", "payment_total", "max_installments",
            "is_revenue_order", "in_analysis_window",
        ]
    ].copy()

    return fact_orders, items, pay, info


def main() -> None:
    force_utf8_stdout()
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Chưa có database: {DB_PATH}. Chạy: python -m src.etl.build_db")

    line = "=" * 74
    print(line)
    print("TRANSFORM: STAGING -> STAR SCHEMA (GIAI ĐOẠN 3b)")
    print(line)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        # Xoá sạch tầng dim/fact để chạy lại nhiều lần không bị nhân đôi dữ liệu
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in [
            "fact_order_items", "fact_payments", "fact_orders",
            "dim_date", "dim_geolocation", "dim_customer",
            "dim_product", "dim_seller",
        ]:
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        stg = {
            name: read_table(conn, f"stg_{name}")
            for name in ["orders", "order_items", "order_payments",
                         "order_reviews", "customers", "products",
                         "sellers", "geolocation", "category_translation"]
        }

        # ---------- DIMENSIONS ----------
        dim_date = build_dim_date(conn)
        dim_geo, geo_info = build_dim_geolocation(stg["geolocation"])
        dim_customer, cust_info = build_dim_customer(stg["customers"])
        dim_product, prod_info = build_dim_product(stg["products"], stg["category_translation"])
        dim_seller = build_dim_seller(stg["sellers"])

        print(f"\ndim_date        {len(dim_date):>9,} dòng  (2016-09-01 -> 2018-11-30)")
        print(f"dim_geolocation {len(dim_geo):>9,} dòng  "
              f"(gộp từ {geo_info['rows_before']:,}, loại {geo_info['rows_dropped']} toạ độ sai)")
        print(f"dim_customer    {len(dim_customer):>9,} dòng  "
              f"(gộp từ {len(stg['customers']):,} customer_id)")
        print(f"dim_product     {len(dim_product):>9,} dòng")
        print(f"dim_seller      {len(dim_seller):>9,} dòng")

        for name, df in [
            ("dim_date", dim_date),
            ("dim_geolocation", dim_geo),
            ("dim_customer", dim_customer),
            ("dim_product", dim_product),
            ("dim_seller", dim_seller),
        ]:
            df.to_sql(name, conn, if_exists="append", index=False)

        # ---------- FACTS ----------
        print("\nĐang dựng fact...")
        fact_orders, items, pay, info = build_facts(
            stg["orders"], stg["order_items"], stg["order_payments"],
            stg["order_reviews"], stg["customers"],
            dim_customer, dim_seller, dim_geo,
        )

        fact_orders.to_sql("fact_orders", conn, if_exists="append", index=False)
        print(f"fact_orders     {len(fact_orders):>9,} dòng")

        # fact_payments
        pay["installments"] = pd.to_numeric(pay["installments"]).astype("Int64")
        fact_payments = pay[[
            "order_id", "payment_sequential", "payment_type",
            "installments", "payment_value",
        ]]
        fact_payments.to_sql("fact_payments", conn, if_exists="append", index=False)
        print(f"fact_payments   {len(fact_payments):>9,} dòng")

        # fact_order_items + distance_km
        print("Đang tính khoảng cách seller -> customer...")
        cust_zip = dim_customer[["customer_unique_id", "zip_code_prefix"]].rename(
            columns={"zip_code_prefix": "cust_zip"}
        )
        seller_zip = dim_seller[["seller_id", "zip_code_prefix"]].rename(
            columns={"zip_code_prefix": "sell_zip"}
        )
        coords = dim_geo[["zip_code_prefix", "lat", "lng"]]

        order_cust = (
            stg["orders"][["order_id", "customer_id"]]
            .merge(stg["customers"][["customer_id", "customer_unique_id"]], on="customer_id")
            .merge(cust_zip, on="customer_unique_id", how="left")
            .merge(coords.rename(columns={"zip_code_prefix": "cust_zip",
                                          "lat": "cust_lat", "lng": "cust_lng"}),
                   on="cust_zip", how="left")
        )
        items = items.merge(order_cust[["order_id", "cust_lat", "cust_lng"]], on="order_id", how="left")
        items = items.merge(seller_zip, on="seller_id", how="left")
        items = items.merge(
            coords.rename(columns={"zip_code_prefix": "sell_zip",
                                   "lat": "sell_lat", "lng": "sell_lng"}),
            on="sell_zip", how="left",
        )

        items["distance_km"] = haversine_km(
            items["sell_lat"], items["sell_lng"], items["cust_lat"], items["cust_lng"]
        ).round(1)
        coverage = items["distance_km"].notna().mean() * 100

        fact_items = items[[
            "order_id", "order_item_id", "product_id", "seller_id",
            "price", "freight_value", "shipping_limit_ts", "distance_km",
        ]].copy()
        fact_items["shipping_limit_ts"] = fact_items["shipping_limit_ts"].dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        fact_items.to_sql("fact_order_items", conn, if_exists="append", index=False)
        print(f"fact_order_items{len(fact_items):>9,} dòng  "
              f"(có khoảng cách: {coverage:.1f}%)")

        # ---------- cập nhật avg_distance vào fact_orders ----------
        dist = (
            fact_items.groupby("order_id", as_index=False)["distance_km"]
            .mean().rename(columns={"distance_km": "avg_distance_km"})
        )
        conn.execute("DROP TABLE IF EXISTS tmp_dist")
        dist.to_sql("tmp_dist", conn, if_exists="replace", index=False)
        conn.execute(
            "UPDATE fact_orders SET avg_distance_km = "
            "(SELECT avg_distance_km FROM tmp_dist WHERE tmp_dist.order_id = fact_orders.order_id)"
        )
        conn.execute("DROP TABLE tmp_dist")
        conn.commit()

        # ---------- KIỂM TRA ----------
        print("\n" + line)
        print("KIỂM TRA NHANH")
        print(line)
        checks = [
            ("số đơn", "SELECT COUNT(*) FROM fact_orders", 99_441),
            ("số dòng hàng", "SELECT COUNT(*) FROM fact_order_items", 112_650),
            ("số thanh toán", "SELECT COUNT(*) FROM fact_payments", 103_886),
            ("orphan customer", "SELECT COUNT(*) FROM fact_orders WHERE customer_unique_id IS NULL", 0),
            ("đơn giao trễ", "SELECT COUNT(*) FROM fact_orders WHERE is_late = 1", info["late_orders"]),
        ]
        for label, sql, expected in checks:
            actual = conn.execute(sql).fetchone()[0]
            flag = "OK" if actual == expected else "SAI"
            print(f"  {label:<20} {actual:>9,}   (kỳ vọng {expected:>9,})  {flag}")

        print(f"  {'tỷ lệ trễ':<20} {info['late_pct']:>8.2f}%")
        print(f"  {'đơn nhiều review':<20} {info['multi_review_orders']:>9,}")
        print(f"  {'đơn trong cửa sổ':<20} "
              f"{conn.execute('SELECT COUNT(*) FROM fact_orders WHERE in_analysis_window=1').fetchone()[0]:>9,}")
        print(f"  {'đơn tính doanh thu':<20} "
              f"{conn.execute('SELECT COUNT(*) FROM fact_orders WHERE is_revenue_order=1').fetchone()[0]:>9,}")

        orphan = conn.execute(
            "SELECT COUNT(*) FROM fact_order_items f LEFT JOIN fact_orders o "
            "ON o.order_id = f.order_id WHERE o.order_id IS NULL"
        ).fetchone()[0]
        print(f"  {'orphan order_items':<20} {orphan:>9,}   {'OK' if orphan == 0 else 'SAI'}")

        print(line)
    finally:
        conn.close()

    print(f"\nDatabase: {DB_PATH}  ({DB_PATH.stat().st_size / 1e6:.1f} MB)")
    print("Bước tiếp theo: python -m src.etl.validate")


if __name__ == "__main__":
    main()
