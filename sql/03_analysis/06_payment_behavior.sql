-- =============================================================================
-- Module 6: THANH TOÁN & TRẢ GÓP
-- Câu hỏi: trả góp có làm giá trị đơn hàng cao hơn không?
-- Lưu ý: payment_type_main = phương thức chiếm nhiều TIỀN nhất trong đơn
--        (một đơn có thể trả bằng nhiều phương thức).
-- =============================================================================

DROP TABLE IF EXISTS mart_payment_behavior;
CREATE TABLE mart_payment_behavior AS
SELECT
    payment_type_main                                           AS payment_type,
    COUNT(*)                                                    AS orders,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)          AS pct_orders,
    ROUND(SUM(order_total), 2)                                  AS revenue,
    ROUND(SUM(order_total) * 100.0
          / SUM(SUM(order_total)) OVER (), 2)                   AS pct_revenue,
    ROUND(AVG(order_total), 2)                                  AS avg_order_value,
    ROUND(AVG(max_installments), 2)                             AS avg_installments,
    ROUND(SUM(CASE WHEN max_installments >= 6 THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                AS pct_installments_6plus,
    ROUND(AVG(review_score), 3)                                 AS avg_review_score,
    ROUND(AVG(CASE WHEN is_late IS NOT NULL THEN is_late END)
          * 100, 2)                                             AS late_rate_pct
FROM fact_orders
WHERE in_analysis_window = 1
  AND is_revenue_order = 1
GROUP BY payment_type_main
ORDER BY revenue DESC;


-- Trả góp: số kỳ càng nhiều thì giá trị đơn càng lớn?
DROP TABLE IF EXISTS mart_installments_band;
CREATE TABLE mart_installments_band AS
WITH b AS (
    SELECT
        CASE
            WHEN max_installments = 1              THEN '1_1_ky'
            WHEN max_installments BETWEEN 2 AND 3  THEN '2_2_3_ky'
            WHEN max_installments BETWEEN 4 AND 6  THEN '3_4_6_ky'
            WHEN max_installments BETWEEN 7 AND 12 THEN '4_7_12_ky'
            ELSE                                        '5_13_ky_tro_len'
        END AS installment_band,
        CASE
            WHEN max_installments = 1              THEN 1
            WHEN max_installments BETWEEN 2 AND 3  THEN 2
            WHEN max_installments BETWEEN 4 AND 6  THEN 3
            WHEN max_installments BETWEEN 7 AND 12 THEN 4
            ELSE                                        5
        END AS sort_order,
        order_total, review_score
    FROM fact_orders
    WHERE in_analysis_window = 1
      AND is_revenue_order = 1
      AND max_installments IS NOT NULL
)
SELECT
    sort_order,
    installment_band,
    COUNT(*)                                                    AS orders,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)          AS pct_orders,
    ROUND(AVG(order_total), 2)                                  AS avg_order_value,
    ROUND(SUM(order_total), 2)                                  AS revenue,
    ROUND(AVG(review_score), 3)                                 AS avg_review_score
FROM b
GROUP BY sort_order, installment_band
ORDER BY sort_order;
