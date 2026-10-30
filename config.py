"""Cấu hình đường dẫn và hằng số cho toàn dự án."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DOCS = PROJECT_ROOT / "docs"
SQL_DIR = PROJECT_ROOT / "sql"
FIGURES = PROJECT_ROOT / "reports" / "figures"
NOTEBOOKS = PROJECT_ROOT / "notebooks"

DB_PATH = DATA_PROCESSED / "olist.db"

# Nguồn dữ liệu: mirror trên Hugging Face (không cần tài khoản Kaggle).
# Kích thước dùng để kiểm tra file tải về có đủ và không hỏng.
DATASET_BASE_URL = (
    "https://huggingface.co/datasets/bulutttt/olist-raw-data/resolve/main/"
)

RAW_FILES: dict[str, int] = {
    "olist_customers_dataset.csv": 9_033_957,
    "olist_geolocation_dataset.csv": 61_273_883,
    "olist_order_items_dataset.csv": 15_438_671,
    "olist_order_payments_dataset.csv": 5_777_138,
    "olist_order_reviews_dataset.csv": 14_451_670,
    "olist_orders_dataset.csv": 17_654_914,
    "olist_products_dataset.csv": 2_379_446,
    "olist_sellers_dataset.csv": 174_703,
    "product_category_name_translation.csv": 2_613,
}

# Ngưỡng dùng cho phân tích
HIGH_VALUE_ORDER_BRL = 500.0  # đơn hàng giá trị cao (đơn vị: BRL)
LATE_DELIVERY_DAYS = 1  # trễ nếu giao sau ngày dự kiến >= 1 ngày
REVIEW_LOW_SCORE = 2  # review 1-2 sao = tiêu cực
REVIEW_HIGH_SCORE = 4  # review 4-5 sao = tích cực

# D4: cửa sổ phân tích (bỏ 2016 và 9-10/2018 vì quá thưa đơn)
ANALYSIS_START = "2017-01-01"
ANALYSIS_END = "2018-08-31"

# D5: doanh thu chỉ ghi nhận trên đơn không bị huỷ / không giao được
NON_REVENUE_STATUSES = ("canceled", "unavailable")

# D8: hộp bao lãnh thổ Brazil — dùng để loại toạ độ sai
BRAZIL_BBOX = {"lat_min": -34.0, "lat_max": 6.0, "lng_min": -74.0, "lng_max": -34.0}

# Hai danh mục thiếu trong bảng dịch (bẫy B6)
MANUAL_CATEGORY_EN = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "kitchen_food_preparers",
}

RANDOM_SEED = 42
