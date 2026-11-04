-- =============================================================================
-- Module 1: GIAO VẬN & HÀI LÒNG
-- Câu hỏi: giao trễ làm điểm đánh giá của khách giảm bao nhiêu?
-- Đây là mảng quan trọng nhất của dự án.
-- =============================================================================

DROP TABLE IF EXISTS mart_delivery_impact;
CREATE TABLE mart_delivery_impact AS
WITH base AS (
    SELECT
        CASE
            WHEN is_late IS NULL          THEN 'not_delivered'
            WHEN is_late = 0              THEN 'on_time_or_early'
            WHEN delay_days <= 3          THEN 'late_1_3d'
            WHEN delay_days <= 7          THEN 'late_4_7d'
            ELSE                               'late_8d_plus'
        END AS delivery_bucket,
        CASE
            WHEN is_late IS NULL THEN 5
            WHEN is_late = 0     THEN 1
            WHEN delay_days <= 3 THEN 2
            WHEN delay_days <= 7 THEN 3
            ELSE                      4
        END AS sort_order,
        review_score, lead_time_days, delay_days, order_total, order_freight
    FROM fact_orders
    WHERE in_analysis_window = 1
)
SELECT
    sort_order,
    delivery_bucket,
    COUNT(*)                                                        AS orders,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)              AS pct_orders,
    COUNT(review_score)                                             AS reviewed_orders,
    ROUND(AVG(review_score), 3)                                     AS avg_review_score,
    ROUND(SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) * 100.0
          / NULLIF(COUNT(review_score), 0), 2)                      AS pct_low_review,
    ROUND(SUM(CASE WHEN review_score = 5 THEN 1 ELSE 0 END) * 100.0
          / NULLIF(COUNT(review_score), 0), 2)                      AS pct_five_star,
    ROUND(AVG(lead_time_days), 2)                                   AS avg_lead_time_days,
    ROUND(AVG(delay_days), 2)                                       AS avg_delay_days,
    ROUND(AVG(order_total), 2)                                      AS avg_order_total,
    ROUND(AVG(order_freight), 2)                                    AS avg_freight
FROM base
GROUP BY sort_order, delivery_bucket
ORDER BY sort_order;


-- Bảng 1 dòng: khoảng cách giữa đơn đúng hạn và đơn trễ (con số headline)
-- Số đơn tính trên TOÀN BỘ đơn có đủ 2 mốc ngày; điểm review chỉ tính trên đơn
-- có review (AVG bỏ qua NULL), nên mẫu số của % review được đếm riêng.
DROP TABLE IF EXISTS mart_delivery_gap;
CREATE TABLE mart_delivery_gap AS
SELECT
    SUM(CASE WHEN is_late = 0 THEN 1 ELSE 0 END)                    AS orders_on_time,
    SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END)                    AS orders_late,
    ROUND(SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END) * 100.0
          / COUNT(*), 2)                                            AS late_rate_pct,
    ROUND(AVG(CASE WHEN is_late = 0 THEN review_score END), 3)      AS avg_review_on_time,
    ROUND(AVG(CASE WHEN is_late = 1 THEN review_score END), 3)      AS avg_review_late,
    ROUND(AVG(CASE WHEN is_late = 0 THEN review_score END)
        - AVG(CASE WHEN is_late = 1 THEN review_score END), 3)      AS review_gap,
    ROUND(SUM(CASE WHEN is_late = 0 AND review_score <= 2 THEN 1 ELSE 0 END) * 100.0
          / NULLIF(SUM(CASE WHEN is_late = 0 AND review_score IS NOT NULL
                            THEN 1 ELSE 0 END), 0), 2)              AS pct_low_review_on_time,
    ROUND(SUM(CASE WHEN is_late = 1 AND review_score <= 2 THEN 1 ELSE 0 END) * 100.0
          / NULLIF(SUM(CASE WHEN is_late = 1 AND review_score IS NOT NULL
                            THEN 1 ELSE 0 END), 0), 2)              AS pct_low_review_late,
    ROUND(AVG(CASE WHEN is_late = 0 THEN lead_time_days END), 2)    AS avg_lead_time_on_time,
    ROUND(AVG(CASE WHEN is_late = 1 THEN lead_time_days END), 2)    AS avg_lead_time_late,
    ROUND(AVG(CASE WHEN is_late = 1 THEN delay_days END), 2)        AS avg_delay_when_late
FROM fact_orders
WHERE in_analysis_window = 1
  AND is_late IS NOT NULL;
