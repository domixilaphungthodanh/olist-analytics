-- =============================================================================
-- Module 5: ĐỊA LÝ & VẬN CHUYỂN
-- Câu hỏi: bang nào mua nhiều, chờ lâu, trả phí ship cao và chấm điểm thấp?
-- Đơn vị: 27 bang của Brazil (dữ liệu chỉ có 27 bang).
-- =============================================================================

DROP TABLE IF EXISTS mart_state_performance;
CREATE TABLE mart_state_performance AS
WITH base AS (
    SELECT
        c.state,
        o.order_id,
        o.customer_unique_id,
        o.order_total,
        o.order_freight,
        o.review_score,
        o.is_late,
        o.lead_time_days,
        o.avg_distance_km
    FROM fact_orders o
    JOIN dim_customer c ON c.customer_unique_id = o.customer_unique_id
    WHERE o.in_analysis_window = 1
      AND o.is_revenue_order = 1
)
SELECT
    state,
    COUNT(*)                                                    AS orders,
    COUNT(DISTINCT customer_unique_id)                          AS customers,
    ROUND(SUM(order_total), 2)                                  AS revenue,
    ROUND(SUM(order_total) * 100.0
          / SUM(SUM(order_total)) OVER (), 2)                   AS pct_revenue,
    ROUND(AVG(order_total), 2)                                  AS avg_order_value,
    ROUND(AVG(order_freight), 2)                                AS avg_freight,
    ROUND(SUM(order_freight) * 100.0
          / NULLIF(SUM(order_total), 0), 2)                     AS freight_ratio_pct,
    ROUND(AVG(avg_distance_km), 1)                              AS avg_distance_km,
    ROUND(AVG(lead_time_days), 2)                               AS avg_lead_time_days,
    ROUND(AVG(CASE WHEN is_late IS NOT NULL THEN is_late END)
          * 100, 2)                                             AS late_rate_pct,
    ROUND(AVG(review_score), 3)                                 AS avg_review_score,
    ROUND(SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END)
          * 100.0 / NULLIF(COUNT(review_score), 0), 2)          AS pct_low_review,
    ROUND(SUM(order_total) / COUNT(DISTINCT customer_unique_id), 2) AS revenue_per_customer
FROM base
GROUP BY state
ORDER BY revenue DESC;
