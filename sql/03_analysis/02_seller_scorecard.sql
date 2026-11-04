-- =============================================================================
-- Module 2: SELLER SCORECARD
-- Câu hỏi: người bán nào đáng giữ, người bán nào đang gây rủi ro?
--
-- Ngưỡng phân loại (ghi rõ để tái lập được):
--   low_volume : < 20 đơn        -> chưa đủ mẫu để đánh giá
--   at_risk    : trễ > 15% hoặc điểm review < 3,5
--   watch      : trễ > 8%  hoặc điểm review < 4,0
--   healthy    : còn lại
-- =============================================================================

DROP TABLE IF EXISTS mart_seller_scorecard;
CREATE TABLE mart_seller_scorecard AS
WITH seller_order AS (
    SELECT
        i.seller_id,
        i.order_id,
        COUNT(*)                AS items,
        SUM(i.price)            AS revenue,
        SUM(i.freight_value)    AS freight,
        AVG(i.distance_km)      AS distance_km
    FROM fact_order_items i
    GROUP BY i.seller_id, i.order_id
),
agg AS (
    SELECT
        so.seller_id,
        s.state                                                   AS seller_state,
        COUNT(*)                                                  AS orders,
        SUM(so.items)                                             AS items_sold,
        SUM(so.revenue)                                           AS revenue,
        SUM(so.freight)                                           AS freight,
        AVG(so.distance_km)                                       AS avg_distance_km,
        AVG(CASE WHEN o.is_late IS NOT NULL THEN o.is_late END)   AS late_rate,
        AVG(CASE WHEN o.order_status IN ('canceled', 'unavailable')
                 THEN 1.0 ELSE 0.0 END)                           AS cancel_rate,
        AVG(o.lead_time_days)                                     AS avg_lead_time_days,
        AVG(o.review_score)                                       AS avg_review_score,
        SUM(CASE WHEN o.review_score <= 2 THEN 1 ELSE 0 END)      AS low_reviews,
        COUNT(o.review_score)                                     AS reviews
    FROM seller_order so
    JOIN fact_orders o ON o.order_id = so.order_id
    JOIN dim_seller s  ON s.seller_id = so.seller_id
    WHERE o.in_analysis_window = 1
    GROUP BY so.seller_id, s.state
    HAVING COUNT(*) >= 5          -- loại seller quá ít đơn, không đủ mẫu
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY revenue DESC) AS revenue_rank,
        SUM(revenue) OVER (
            ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) / SUM(revenue) OVER () AS cum_share
    FROM agg
)
SELECT
    seller_id,
    seller_state,
    orders,
    items_sold,
    ROUND(revenue, 2)                                            AS revenue,
    ROUND(revenue * 100.0 / SUM(revenue) OVER (), 2)             AS pct_revenue,
    ROUND(cum_share * 100, 2)                                    AS cum_revenue_pct,
    CASE WHEN cum_share <= 0.80 THEN 'A'
         WHEN cum_share <= 0.95 THEN 'B'
         ELSE 'C' END                                            AS abc_class,
    revenue_rank,
    ROUND(revenue / orders, 2)                                   AS revenue_per_order,
    ROUND(avg_review_score, 3)                                   AS avg_review_score,
    reviews,
    ROUND(low_reviews * 100.0 / NULLIF(reviews, 0), 2)           AS pct_low_review,
    ROUND(late_rate * 100, 2)                                    AS late_rate_pct,
    ROUND(cancel_rate * 100, 2)                                  AS cancel_rate_pct,
    ROUND(avg_lead_time_days, 2)                                 AS avg_lead_time_days,
    ROUND(avg_distance_km, 1)                                    AS avg_distance_km,
    CASE
        WHEN orders < 20 THEN 'low_volume'
        WHEN late_rate > 0.15 OR avg_review_score < 3.5 THEN 'at_risk'
        WHEN late_rate > 0.08 OR avg_review_score < 4.0 THEN 'watch'
        ELSE 'healthy'
    END                                                          AS health_flag
FROM ranked
ORDER BY revenue DESC;


-- Tổng hợp: mỗi nhóm cờ chiếm bao nhiêu seller / doanh thu
DROP TABLE IF EXISTS mart_seller_flags;
CREATE TABLE mart_seller_flags AS
SELECT
    health_flag,
    COUNT(*)                                                     AS sellers,
    SUM(orders)                                                  AS orders,
    ROUND(SUM(revenue), 2)                                       AS revenue,
    ROUND(SUM(revenue) * 100.0
          / (SELECT SUM(revenue) FROM mart_seller_scorecard), 2) AS pct_revenue,
    ROUND(AVG(avg_review_score), 3)                              AS avg_review_score,
    ROUND(AVG(late_rate_pct), 2)                                 AS avg_late_rate_pct
FROM mart_seller_scorecard
GROUP BY health_flag
ORDER BY revenue DESC;
