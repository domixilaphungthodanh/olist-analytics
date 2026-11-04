-- =============================================================================
-- Olist E-Commerce Analytics — DDL
--
-- Kiến trúc 3 tầng:
--   stg_*   : bản sao nguyên trạng 9 file CSV (mọi cột TEXT, không sửa 1 giá trị)
--   dim/fact: star schema, kiểu dữ liệu chuẩn hoá
--   mart_*  : bảng kết quả phân tích (do run_marts.py sinh ra)
-- =============================================================================

-- =============================================================================
-- TẦNG 1: STAGING
-- Mọi cột đều TEXT để bảo toàn tuyệt đối giá trị gốc. Việc ép kiểu chỉ xảy ra
-- ở tầng transform. Nhờ vậy luôn chứng minh được "dữ liệu gốc không bị sửa".
-- =============================================================================

DROP TABLE IF EXISTS stg_orders;
CREATE TABLE stg_orders (
    order_id                        TEXT PRIMARY KEY,
    customer_id                     TEXT,
    order_status                    TEXT,
    order_purchase_timestamp        TEXT,
    order_approved_at               TEXT,
    order_delivered_carrier_date    TEXT,
    order_delivered_customer_date   TEXT,
    order_estimated_delivery_date   TEXT
);

DROP TABLE IF EXISTS stg_order_items;
CREATE TABLE stg_order_items (
    order_id            TEXT,
    order_item_id       TEXT,
    product_id          TEXT,
    seller_id           TEXT,
    shipping_limit_date TEXT,
    price               TEXT,
    freight_value       TEXT,
    PRIMARY KEY (order_id, order_item_id)
);

DROP TABLE IF EXISTS stg_order_payments;
CREATE TABLE stg_order_payments (
    order_id            TEXT,
    payment_sequential  TEXT,
    payment_type        TEXT,
    payment_installments TEXT,
    payment_value       TEXT,
    PRIMARY KEY (order_id, payment_sequential)
);

DROP TABLE IF EXISTS stg_order_reviews;
CREATE TABLE stg_order_reviews (
    review_id               TEXT,
    order_id                TEXT,
    review_score            TEXT,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TEXT,
    review_answer_timestamp TEXT
);
-- Không đặt PRIMARY KEY: review_id và order_id đều KHÔNG unique (bẫy B2/B3).

DROP TABLE IF EXISTS stg_customers;
CREATE TABLE stg_customers (
    customer_id             TEXT PRIMARY KEY,
    customer_unique_id      TEXT,
    customer_zip_code_prefix TEXT,
    customer_city           TEXT,
    customer_state          TEXT
);

DROP TABLE IF EXISTS stg_products;
CREATE TABLE stg_products (
    product_id                 TEXT PRIMARY KEY,
    product_category_name      TEXT,
    product_name_lenght        TEXT,
    product_description_lenght TEXT,
    product_photos_qty         TEXT,
    product_weight_g           TEXT,
    product_length_cm          TEXT,
    product_height_cm          TEXT,
    product_width_cm           TEXT
);

DROP TABLE IF EXISTS stg_sellers;
CREATE TABLE stg_sellers (
    seller_id               TEXT PRIMARY KEY,
    seller_zip_code_prefix  TEXT,
    seller_city             TEXT,
    seller_state            TEXT
);

DROP TABLE IF EXISTS stg_geolocation;
CREATE TABLE stg_geolocation (
    geolocation_zip_code_prefix TEXT,
    geolocation_lat             TEXT,
    geolocation_lng             TEXT,
    geolocation_city            TEXT,
    geolocation_state           TEXT
);

DROP TABLE IF EXISTS stg_category_translation;
CREATE TABLE stg_category_translation (
    product_category_name          TEXT PRIMARY KEY,
    product_category_name_english  TEXT
);

-- =============================================================================
-- TẦNG 2: DIMENSIONS
-- =============================================================================

DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date (
    date        TEXT PRIMARY KEY,   -- YYYY-MM-DD
    year        INTEGER NOT NULL,
    quarter     INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    month_name  TEXT NOT NULL,
    period      TEXT NOT NULL,      -- YYYY-MM
    week        INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,   -- 0 = Thứ Hai ... 6 = Chủ Nhật
    day_name    TEXT NOT NULL,
    is_weekend  INTEGER NOT NULL    -- 1 = thứ Bảy / Chủ Nhật
);

DROP TABLE IF EXISTS dim_customer;
CREATE TABLE dim_customer (
    customer_unique_id TEXT PRIMARY KEY,   -- D2: khoá khách hàng THẬT
    city               TEXT,
    state              TEXT,
    zip_code_prefix    TEXT
);

DROP TABLE IF EXISTS dim_product;
CREATE TABLE dim_product (
    product_id      TEXT PRIMARY KEY,
    category_pt     TEXT,
    category_en     TEXT,
    photos_qty      INTEGER,
    weight_g        INTEGER,
    length_cm       INTEGER,
    height_cm       INTEGER,
    width_cm        INTEGER,
    volume_cm3      REAL,
    has_category    INTEGER NOT NULL
);

DROP TABLE IF EXISTS dim_seller;
CREATE TABLE dim_seller (
    seller_id        TEXT PRIMARY KEY,
    city             TEXT,
    state            TEXT,
    zip_code_prefix  TEXT
);

-- B4: geolocation được GỘP theo zip trước khi đưa vào dim.
-- B5: đã loại 42 dòng toạ độ nằm ngoài lãnh thổ Brazil.
DROP TABLE IF EXISTS dim_geolocation;
CREATE TABLE dim_geolocation (
    zip_code_prefix TEXT PRIMARY KEY,
    lat             REAL NOT NULL,
    lng             REAL NOT NULL,
    city            TEXT,
    state           TEXT,
    point_count     INTEGER NOT NULL   -- số điểm GPS gốc đã gộp
);

-- =============================================================================
-- TẦNG 2: FACTS
-- =============================================================================

-- Grain: 1 dòng = 1 ĐƠN HÀNG (99.441)
-- Tồn tại song song fact_order_items để tránh fan-out khi join với payments.
DROP TABLE IF EXISTS fact_orders;
CREATE TABLE fact_orders (
    order_id            TEXT PRIMARY KEY,
    customer_unique_id  TEXT REFERENCES dim_customer(customer_unique_id),
    order_date          TEXT REFERENCES dim_date(date),
    order_status        TEXT NOT NULL,

    -- mốc thời gian
    purchase_ts         TEXT,
    approved_ts         TEXT,
    carrier_ts          TEXT,
    delivered_ts        TEXT,
    estimated_ts        TEXT,

    -- chỉ số thời gian (đơn vị: ngày)
    lead_time_days      REAL,   -- purchase   -> delivered
    handover_days       REAL,   -- approved   -> carrier (Olist xử lý)
    transit_days        REAL,   -- carrier    -> delivered (vận chuyển)
    is_late             INTEGER,-- 1 nếu delivered > estimated
    delay_days          REAL,   -- delivered - estimated (âm = sớm)
    buffer_days         REAL,   -- estimated - delivered (dương = dư thời gian)

    -- đo lường
    items_count         INTEGER NOT NULL DEFAULT 0,
    order_price         REAL,   -- tổng price của các dòng hàng
    order_freight       REAL,   -- tổng freight_value
    order_total         REAL,   -- price + freight
    freight_ratio       REAL,   -- freight / total
    avg_distance_km     REAL,   -- khoảng cách seller -> customer (TB các dòng)

    -- đánh giá
    review_score        INTEGER,-- điểm review mới nhất của đơn
    review_count        INTEGER NOT NULL DEFAULT 0,

    -- thanh toán
    payment_type_main   TEXT,   -- phương thức chiếm nhiều tiền nhất
    payment_total       REAL,
    max_installments    INTEGER,

    -- cờ nghiệp vụ
    is_revenue_order      INTEGER NOT NULL,  -- D5: 0 nếu canceled/unavailable
    in_analysis_window    INTEGER NOT NULL   -- D4: 1 nếu trong 2017-01..2018-08
);

-- Grain: 1 dòng = 1 DÒNG HÀNG trong đơn (112.650)
CREATE TABLE fact_order_items (
    order_id          TEXT NOT NULL REFERENCES fact_orders(order_id),
    order_item_id     INTEGER NOT NULL,
    product_id        TEXT REFERENCES dim_product(product_id),
    seller_id         TEXT REFERENCES dim_seller(seller_id),
    price             REAL NOT NULL,
    freight_value     REAL NOT NULL,
    shipping_limit_ts TEXT,
    distance_km       REAL,
    PRIMARY KEY (order_id, order_item_id)
);

-- Grain: 1 dòng = 1 LẦN THANH TOÁN (103.886)
CREATE TABLE fact_payments (
    order_id           TEXT NOT NULL REFERENCES fact_orders(order_id),
    payment_sequential INTEGER NOT NULL,
    payment_type       TEXT,
    installments       INTEGER,
    payment_value      REAL,
    PRIMARY KEY (order_id, payment_sequential)
);

-- =============================================================================
-- INDEX
-- =============================================================================
CREATE INDEX idx_orders_customer   ON fact_orders(customer_unique_id);
CREATE INDEX idx_orders_date       ON fact_orders(order_date);
CREATE INDEX idx_orders_status     ON fact_orders(order_status);
CREATE INDEX idx_orders_late       ON fact_orders(is_late);
CREATE INDEX idx_orders_revenue    ON fact_orders(is_revenue_order);
CREATE INDEX idx_orders_window     ON fact_orders(in_analysis_window);
CREATE INDEX idx_orders_review     ON fact_orders(review_score);

CREATE INDEX idx_items_product     ON fact_order_items(product_id);
CREATE INDEX idx_items_seller      ON fact_order_items(seller_id);
CREATE INDEX idx_items_order       ON fact_order_items(order_id);

CREATE INDEX idx_payments_type     ON fact_payments(payment_type);
CREATE INDEX idx_payments_order    ON fact_payments(order_id);

CREATE INDEX idx_products_category ON dim_product(category_en);
CREATE INDEX idx_sellers_state     ON dim_seller(state);
CREATE INDEX idx_customers_state   ON dim_customer(state);
CREATE INDEX idx_date_period       ON dim_date(period);

