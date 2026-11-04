-- =============================================================================
-- Module 4: DANH MỤC & SẢN PHẨM
-- Câu hỏi: ngành hàng nào tạo doanh thu, ngành nào ship đắt và bị chấm điểm thấp?
--
-- Lưu ý phương pháp:
--   - Doanh thu tính ở cấp DÒNG HÀNG (cộng price + freight thực tế đã trả).
--   - Điểm review tính ở cấp ĐƠN × DANH MỤC: một đơn có nhiều danh mục sẽ được
--     tính cho từng danh mục (DISTINCT order_id), nên tổng số đơn theo danh mục
--     lớn hơn tổng số đơn thực tế.
-- =============================================================================

DROP TABLE IF EXISTS mart_category_performance;
CREATE TABLE mart_category_performance AS
WITH item_agg AS (
    SELECT
        p.category_en                   AS category,
        COUNT(DISTINCT i.order_id)      AS orders,
        COUNT(*)                        AS items,
        SUM(i.price)                    AS product_revenue,
        SUM(i.freight_value)            AS freight,
        AVG(i.price)                    AS avg_price_per_item
    FROM fact_order_items i
    JOIN dim_product p  ON p.product_id = i.product_id
    JOIN fact_orders o  ON o.order_id = i.order_id
    WHERE o.in_analysis_window = 1
      AND o.is_revenue_order = 1
      AND p.has_category = 1
    GROUP BY p.category_en
),
order_agg AS (
    SELECT
        p.category_en                   AS category,
        COUNT(*)                        AS orders_with_category,
        AVG(o.review_score)             AS avg_review_score,
        SUM(CASE WHEN o.review_score <= 2 THEN 1 ELSE 0 END) AS low_reviews,
        COUNT(o.review_score)           AS reviewed,
        AVG(CASE WHEN o.is_late IS NOT NULL THEN o.is_late END) AS late_rate,
        AVG(o.lead_time_days)           AS avg_lead_time_days
    FROM fact_orders o
    JOIN fact_order_items i ON i.order_id = o.order_id
    JOIN dim_product p      ON p.product_id = i.product_id
    WHERE o.in_analysis_window = 1
      AND o.is_revenue_order = 1
      AND p.has_category = 1
    GROUP BY p.category_en
),
ranked AS (
    SELECT
        *,
        SUM(product_revenue) OVER (
            ORDER BY product_revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) / SUM(product_revenue) OVER () AS cum_share,
        ROW_NUMBER() OVER (ORDER BY product_revenue DESC) AS revenue_rank
    FROM item_agg
)
SELECT
    r.category,
    r.revenue_rank,
    r.orders,
    r.items,
    ROUND(r.product_revenue, 2)                                  AS product_revenue,
    ROUND(r.freight, 2)                                          AS freight,
    ROUND(r.product_revenue * 100.0
          / SUM(r.product_revenue) OVER (), 2)                   AS pct_revenue,
    ROUND(r.cum_share * 100, 2)                                  AS cum_revenue_pct,
    CASE WHEN r.cum_share <= 0.80 THEN 'A'
         WHEN r.cum_share <= 0.95 THEN 'B'
         ELSE 'C' END                                            AS abc_class,
    ROUND(r.avg_price_per_item, 2)                               AS avg_price_per_item,
    ROUND(r.freight * 100.0
          / NULLIF(r.product_revenue + r.freight, 0), 2)         AS freight_ratio_pct,
    ROUND(o.avg_review_score, 3)                                 AS avg_review_score,
    ROUND(o.low_reviews * 100.0 / NULLIF(o.reviewed, 0), 2)      AS pct_low_review,
    ROUND(o.late_rate * 100, 2)                                  AS late_rate_pct,
    ROUND(o.avg_lead_time_days, 2)                               AS avg_lead_time_days,
    ROUND(r.product_revenue / NULLIF(r.orders, 0), 2)            AS revenue_per_order
FROM ranked r
JOIN order_agg o ON o.category = r.category
ORDER BY r.product_revenue DESC;
