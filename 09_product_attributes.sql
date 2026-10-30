-- =============================================================================
-- Module 9: THUỘC TÍNH SẢN PHẨM
-- Câu hỏi: hàng nặng / cồng kềnh có bị đánh giá thấp và tốn phí ship hơn không?
--
-- Phương pháp: CHỈ xét đơn có đúng 1 dòng hàng. Nhờ vậy mỗi dòng hàng tương ứng
-- đúng 1 đơn, tránh việc một đơn nhiều sản phẩm bị tính điểm review nhiều lần.
-- =============================================================================

DROP TABLE IF EXISTS mart_product_attributes;
CREATE TABLE mart_product_attributes AS
WITH b AS (
    SELECT
        CASE
            WHEN p.weight_g IS NULL      THEN '6_khong_ro'
            WHEN p.weight_g < 500        THEN '1_0_500_g'
            WHEN p.weight_g < 1000       THEN '2_500g_1kg'
            WHEN p.weight_g < 5000       THEN '3_1_5_kg'
            WHEN p.weight_g < 15000      THEN '4_5_15_kg'
            ELSE                              '5_tren_15_kg'
        END AS weight_band,
        CASE
            WHEN p.weight_g IS NULL      THEN 9
            WHEN p.weight_g < 500        THEN 1
            WHEN p.weight_g < 1000       THEN 2
            WHEN p.weight_g < 5000       THEN 3
            WHEN p.weight_g < 15000      THEN 4
            ELSE                              5
        END AS sort_order,
        p.weight_g,
        i.price,
        i.freight_value,
        i.distance_km,
        o.review_score,
        o.is_late,
        o.lead_time_days
    FROM fact_order_items i
    JOIN dim_product p  ON p.product_id = i.product_id
    JOIN fact_orders o  ON o.order_id = i.order_id
    WHERE o.in_analysis_window = 1
      AND o.is_revenue_order = 1
      AND o.items_count = 1
)
SELECT
    sort_order,
    weight_band,
    COUNT(*)                                                    AS orders,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)          AS pct_orders,
    ROUND(AVG(weight_g), 0)                                     AS avg_weight_g,
    ROUND(AVG(price), 2)                                        AS avg_price,
    ROUND(AVG(freight_value), 2)                                AS avg_freight,
    ROUND(SUM(freight_value) * 100.0
          / NULLIF(SUM(price + freight_value), 0), 2)           AS freight_ratio_pct,
    ROUND(AVG(distance_km), 1)                                  AS avg_distance_km,
    ROUND(AVG(review_score), 3)                                 AS avg_review_score,
    ROUND(SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END)
          * 100.0 / NULLIF(COUNT(review_score), 0), 2)          AS pct_low_review,
    ROUND(AVG(CASE WHEN is_late IS NOT NULL THEN is_late END)
          * 100, 2)                                             AS late_rate_pct,
    ROUND(AVG(lead_time_days), 2)                               AS avg_lead_time_days
FROM b
GROUP BY sort_order, weight_band
ORDER BY sort_order;
