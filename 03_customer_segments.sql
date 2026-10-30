-- =============================================================================
-- Module 3: KHÁCH HÀNG & GIỮ CHÂN
-- Câu hỏi: khách có quay lại không? Giá trị của nhóm quay lại lớn đến đâu?
--
-- D2: khoá khách hàng là customer_unique_id (KHÔNG dùng customer_id).
-- Mốc tham chiếu recency: ngày cuối của cửa sổ phân tích (2018-08-31).
-- =============================================================================

DROP TABLE IF EXISTS mart_customer_segments;
CREATE TABLE mart_customer_segments AS
WITH cust AS (
    SELECT
        customer_unique_id,
        COUNT(*)        AS orders,
        SUM(order_total) AS revenue,
        MAX(order_date) AS last_order_date,
        AVG(review_score) AS avg_review
    FROM fact_orders
    WHERE in_analysis_window = 1
      AND is_revenue_order = 1
    GROUP BY customer_unique_id
),
seg AS (
    SELECT
        *,
        CAST(julianday('2018-08-31') - julianday(last_order_date) AS INTEGER) AS recency_days,
        CASE WHEN orders >= 3 THEN 'loyal_3plus'
             WHEN orders = 2  THEN 'repeat_2'
             ELSE 'one_time' END AS segment
    FROM cust
)
SELECT
    segment,
    COUNT(*)                                                    AS customers,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)          AS pct_customers,
    SUM(orders)                                                 AS orders,
    ROUND(SUM(revenue), 2)                                      AS revenue,
    ROUND(SUM(revenue) * 100.0 / SUM(SUM(revenue)) OVER (), 2)  AS pct_revenue,
    ROUND(AVG(revenue), 2)                                      AS avg_revenue_per_customer,
    ROUND(AVG(recency_days), 1)                                 AS avg_recency_days,
    ROUND(AVG(avg_review), 3)                                   AS avg_review_score
FROM seg
GROUP BY segment
ORDER BY revenue DESC;


-- Đơn của khách mới vs khách quay lại, theo từng tháng
DROP TABLE IF EXISTS mart_new_vs_returning_monthly;
CREATE TABLE mart_new_vs_returning_monthly AS
WITH first_order AS (
    SELECT customer_unique_id, MIN(order_date) AS first_date
    FROM fact_orders
    WHERE is_revenue_order = 1
    GROUP BY customer_unique_id
),
m AS (
    SELECT
        substr(o.order_date, 1, 7) AS period,
        o.order_total,
        CASE WHEN o.order_date = f.first_date THEN 'new' ELSE 'returning' END AS cust_type
    FROM fact_orders o
    JOIN first_order f ON f.customer_unique_id = o.customer_unique_id
    WHERE o.in_analysis_window = 1
      AND o.is_revenue_order = 1
)
SELECT
    period,
    COUNT(*)                                                        AS orders,
    SUM(CASE WHEN cust_type = 'new' THEN 1 ELSE 0 END)              AS new_customer_orders,
    SUM(CASE WHEN cust_type = 'returning' THEN 1 ELSE 0 END)        AS returning_orders,
    ROUND(SUM(CASE WHEN cust_type = 'returning' THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                    AS pct_returning_orders,
    ROUND(SUM(order_total), 2)                                      AS revenue
FROM m
GROUP BY period
ORDER BY period;
