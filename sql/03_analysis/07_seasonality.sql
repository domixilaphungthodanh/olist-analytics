-- =============================================================================
-- Module 7: MÙA VỤ
-- Câu hỏi: doanh thu biến động thế nào theo tháng? Black Friday 11/2017 lớn cỡ nào?
-- Cửa sổ 2017-01 -> 2018-08 (D4) để hai đầu không bị "sụp" vì thiếu dữ liệu.
-- =============================================================================

DROP TABLE IF EXISTS mart_monthly_trend;
CREATE TABLE mart_monthly_trend AS
WITH m AS (
    SELECT
        substr(order_date, 1, 7)        AS period,
        COUNT(*)                        AS orders,
        SUM(order_total)                AS revenue,
        AVG(order_total)                AS aov,
        AVG(review_score)               AS avg_review,
        AVG(CASE WHEN is_late IS NOT NULL THEN is_late END) AS late_rate
    FROM fact_orders
    WHERE in_analysis_window = 1
      AND is_revenue_order = 1
    GROUP BY period
)
SELECT
    period,
    orders,
    ROUND(revenue, 2)                                           AS revenue,
    ROUND(aov, 2)                                               AS avg_order_value,
    ROUND(avg_review, 3)                                        AS avg_review_score,
    ROUND(late_rate * 100, 2)                                   AS late_rate_pct,
    ROUND((revenue - LAG(revenue) OVER (ORDER BY period)) * 100.0
          / NULLIF(LAG(revenue) OVER (ORDER BY period), 0), 2)  AS revenue_mom_pct,
    ROUND((orders - LAG(orders) OVER (ORDER BY period)) * 100.0
          / NULLIF(LAG(orders) OVER (ORDER BY period), 0), 2)   AS orders_mom_pct
FROM m
ORDER BY period;


-- Mua hàng theo thứ trong tuần
DROP TABLE IF EXISTS mart_weekday_pattern;
CREATE TABLE mart_weekday_pattern AS
SELECT
    d.day_of_week,
    d.day_name,
    d.is_weekend,
    COUNT(*)                                                    AS orders,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)          AS pct_orders,
    ROUND(SUM(o.order_total), 2)                                AS revenue,
    ROUND(AVG(o.order_total), 2)                                AS avg_order_value
FROM fact_orders o
JOIN dim_date d ON d.date = o.order_date
WHERE o.in_analysis_window = 1
  AND o.is_revenue_order = 1
GROUP BY d.day_of_week, d.day_name, d.is_weekend
ORDER BY d.day_of_week;
