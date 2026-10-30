-- =============================================================================
-- Module 8: KINH TẾ PHÍ VẬN CHUYỂN
-- Câu hỏi: càng xa thì phí ship và thời gian giao tăng bao nhiêu?
-- Khoảng cách = đường chim bay giữa mã zip người bán và người mua (haversine).
-- 99,5% số dòng hàng tính được khoảng cách; phần còn lại xếp vào 'unknown'.
-- =============================================================================

DROP TABLE IF EXISTS mart_freight_by_distance;
CREATE TABLE mart_freight_by_distance AS
WITH b AS (
    SELECT
        CASE
            WHEN avg_distance_km IS NULL      THEN '6_khong_ro'
            WHEN avg_distance_km < 100        THEN '1_0_100_km'
            WHEN avg_distance_km < 300        THEN '2_100_300_km'
            WHEN avg_distance_km < 600        THEN '3_300_600_km'
            WHEN avg_distance_km < 1000       THEN '4_600_1000_km'
            WHEN avg_distance_km < 1500       THEN '5_1000_1500_km'
            ELSE                                   '7_1500_km_tro_len'
        END AS distance_band,
        CASE
            WHEN avg_distance_km IS NULL      THEN 9
            WHEN avg_distance_km < 100        THEN 1
            WHEN avg_distance_km < 300        THEN 2
            WHEN avg_distance_km < 600        THEN 3
            WHEN avg_distance_km < 1000       THEN 4
            WHEN avg_distance_km < 1500       THEN 5
            ELSE                                   6
        END AS sort_order,
        avg_distance_km,
        order_total, order_freight, lead_time_days, is_late, review_score
    FROM fact_orders
    WHERE in_analysis_window = 1
      AND is_revenue_order = 1
)
SELECT
    sort_order,
    distance_band,
    COUNT(*)                                                    AS orders,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)          AS pct_orders,
    ROUND(AVG(avg_distance_km), 1)                              AS avg_distance_km,
    ROUND(AVG(order_freight), 2)                                AS avg_freight,
    ROUND(SUM(order_freight) * 100.0
          / NULLIF(SUM(order_total), 0), 2)                     AS freight_ratio_pct,
    ROUND(AVG(order_total), 2)                                  AS avg_order_value,
    ROUND(AVG(lead_time_days), 2)                               AS avg_lead_time_days,
    ROUND(AVG(CASE WHEN is_late IS NOT NULL THEN is_late END)
          * 100, 2)                                             AS late_rate_pct,
    ROUND(AVG(review_score), 3)                                 AS avg_review_score
FROM b
GROUP BY sort_order, distance_band
ORDER BY sort_order;
