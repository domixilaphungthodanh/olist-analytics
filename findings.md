# Kết quả phân tích — Olist E-Commerce

**Cửa sổ phân tích:** 2017-01-01 → 2018-08-31 · **Đơn không huỷ:** 97.910 · **Doanh thu:** 15.683.706,74 BRL
**Khách hàng:** 94.707 · **Giá trị đơn TB:** 160,19 BRL · **Điểm review TB:** 4,117 ⭐

> Mọi con số dưới đây đều tái lập được bằng SQL trong `sql/03_analysis/`,
> xuất ra CSV trong `reports/` và minh hoạ bằng chart trong `reports/figures/`.

---

## TL;DR — 5 con số quan trọng nhất

| # | Phát hiện | Con số |
|---|---|---|
| 1 | Giao trễ làm mất **2,02 sao** | 4,29 ⭐ → 2,27 ⭐ |
| 2 | Khách giao trễ cho 1–2 sao nhiều gấp **6,7 lần** | 62,41% vs 9,25% |
| 3 | Chỉ **3,04%** khách quay lại mua lần 2 | 2.875 / 94.707 |
| 4 | Khách quay lại đáng giá **gấp 1,8–3,1 lần** | 161 → 291 → 503 BRL |
| 5 | **67 seller** gây rủi ro, chiếm 6,15% doanh thu | 18,06% đơn trễ |

---

## 1. Giao trễ là nguyên nhân số một của sự bất mãn

Đây là phát hiện mạnh nhất, và nó **đơn điệu** — càng trễ càng tệ, không có ngoại lệ:

| Mức giao hàng | Số đơn | Điểm TB | % 1–2 sao | Ngày chờ TB |
|---|---:|---:|---:|---:|
| Đúng hạn / sớm | 89.672 | **4,29** ⭐ | 9,25% | 10,98 |
| Trễ 1–3 ngày | 1.869 | 3,29 ⭐ | 32,14% | 23,29 |
| Trễ 4–7 ngày | 1.802 | 2,10 ⭐ | 67,68% | 28,23 |
| Trễ ≥ 8 ngày | 2.861 | **1,70** ⭐ | 79,24% | 44,49 |
| Không giao được | 2.888 | 1,75 ⭐ | 77,79% | — |

**Đọc bảng này:** chỉ cần trễ 1–3 ngày, điểm đã rơi từ 4,29 xuống **3,29** — mất
gần 1 sao. Trễ hơn 1 tuần thì khách gần như chắc chắn cho 1–2 sao (79,24%).

Xét riêng hai nhóm:

| | Đúng hạn | Giao trễ | Chênh lệch |
|---|---:|---:|---:|
| Điểm review TB | 4,291 ⭐ | 2,271 ⭐ | **−2,02 sao** |
| % khách cho 1–2 sao | 9,25% | 62,41% | **×6,7** |
| Thời gian chờ TB | 10,98 ngày | 33,94 ngày | **+23 ngày** |

> ⚠️ **Lưu ý về nhân quả:** dữ liệu là quan sát, không phải thí nghiệm, nên không
> thể khẳng định 100% "trễ → điểm thấp" (có thể sản phẩm dở cũng gây điểm thấp).
> Nhưng xu hướng **đơn điệu qua 4 mức trễ** cộng với việc đơn không giao được
> cũng bị 1,75 ⭐ cho thấy thời gian giao là yếu tố chi phối rất mạnh.

**Tỷ lệ trễ tổng thể: 6,79%** (6.532 / 96.204 đơn đã giao trong cửa sổ).

📊 `01_delivery_impact.png`, `02_delivery_gap.png`, `03_review_mix.png`
📄 `mart_delivery_impact.csv`, `mart_delivery_gap.csv`

---

## 2. Khách gần như không bao giờ quay lại

| Nhóm | Số khách | % khách | % doanh thu | Doanh thu / khách |
|---|---:|---:|---:|---:|
| Mua 1 lần | 91.832 | **96,96%** | 94,35% | 161,14 BRL |
| Mua 2 lần | 2.640 | 2,79% | 4,90% | 290,94 BRL |
| Mua ≥ 3 lần | 235 | 0,25% | 0,75% | **502,90 BRL** |

Khách quay lại chỉ chiếm **3,04%** nhưng giá trị trung bình **gấp 1,8 lần** (mua 2 lần)
và **gấp 3,1 lần** (mua ≥ 3 lần).

Tỷ lệ đơn của khách quay lại theo tháng chỉ dao động **0,38% – 3,40%** — không có
tháng nào thoát khỏi mức này. Đây không phải vấn đề mùa vụ, mà là **cấu trúc**.

> ⚠️ **Bẫy đã tránh:** nếu dùng `customer_id` thay vì `customer_unique_id` thì
> mọi khách đều thành "mua 1 lần" và tỷ lệ quay lại = **0%**. Con số 3,04% ở trên
> chỉ có được nhờ dùng đúng khoá.

📊 `07_customer_segments.png`, `08_new_vs_returning.png`
📄 `mart_customer_segments.csv`, `mart_new_vs_returning_monthly.csv`

---

## 3. Seller: 6% doanh thu đang nằm trong tay nhóm rủi ro

1.787 seller có ≥ 5 đơn (loại seller quá ít đơn vì không đủ mẫu):

| Nhóm | Seller | % doanh thu | Điểm TB | Tỷ lệ trễ TB |
|---|---:|---:|---:|---:|
| `healthy` | 447 | 43,76% | 4,31 ⭐ | 3,53% |
| `watch` | 302 | 35,88% | 3,98 ⭐ | 8,58% |
| `low_volume` | 971 | 14,21% | 4,12 ⭐ | 6,64% |
| `at_risk` | **67** | **6,15%** | **3,47 ⭐** | **18,06%** |

Seller rủi ro lớn nhất: một seller ở **SP** với **982 đơn**, doanh thu **187.924 BRL**
nhưng chỉ **3,49 ⭐** và **9,15% đơn trễ** — tức là ~38.000 BRL doanh thu đang gắn
với trải nghiệm kém.

Seller tệ nhất theo điểm: **2,70 ⭐** với 202 đơn và 11,23% trễ.

**Quan sát:** nhóm `at_risk` chỉ 3,7% số seller nhưng tạo ra 6,15% doanh thu và
18,06% đơn trễ — tức **tỷ lệ trễ cao gấp 5 lần** nhóm healthy.

📊 `04_seller_scatter.png`, `05_seller_top15.png`, `06_seller_flags.png`
📄 `mart_seller_scorecard.csv`, `mart_seller_flags.csv`

---

## 4. Địa lý: khoảng cách quyết định trải nghiệm

| Bang | Đơn | % doanh thu | Ngày chờ | % trễ | Điểm TB |
|---|---:|---:|---:|---:|---:|
| SP (São Paulo) | 41.022 | 37,39% | 8,74 | 4,50% | 4,212 ⭐ |
| RJ (Rio) | 12.648 | 13,42% | 15,30 | **12,15%** | 3,905 ⭐ |
| MG | 11.455 | 11,72% | 11,99 | 4,59% | 4,166 ⭐ |
| MA (Maranhão) | 731 | 0,6% | 21,53 | **17,56%** | 3,774 ⭐ |
| CE (Ceará) | 1.318 | 1,1% | 21,22 | 13,80% | 3,879 ⭐ |
| BA (Bahia) | 3.340 | 3,9% | 19,33 | 12,17% | 3,885 ⭐ |
| PA (Pará) | 965 | 0,9% | **23,76** | 11,25% | 3,860 ⭐ |

**Nghịch lý đáng chú ý:** RJ chỉ cách SP ~430 km nhưng có tỷ lệ trễ **cao gấp 2,7 lần**
(12,15% vs 4,50%) và chờ lâu gấp 1,75 lần. Đây là vấn đề **vận hành theo tuyến**,
không phải vấn đề khoảng cách — vì MA cách xa hơn nhiều nhưng chỉ tệ hơn RJ 1,4 lần.

📊 `11_state_performance.png`
📄 `mart_state_performance.csv`

---

## 5. Càng xa càng đắt, càng chậm, càng bị điểm thấp

| Khoảng cách | Đơn | Phí ship TB | % phí/đơn | Ngày chờ | % trễ | Điểm TB |
|---|---:|---:|---:|---:|---:|---:|
| 0–100 km | 18.057 | 13,35 BRL | 10,51% | 6,48 | 4,48% | **4,243** ⭐ |
| 100–300 km | 13.572 | 18,86 | 12,44% | 9,95 | 5,18% | 4,207 |
| 300–600 km | 31.983 | 22,44 | 14,33% | 12,61 | 6,77% | 4,094 |
| 600–1.000 km | 18.152 | 24,88 | 15,09% | 14,70 | 7,10% | 4,087 |
| 1.000–1.500 km | 6.691 | 29,80 | 15,03% | 17,25 | 8,86% | 4,015 |
| **> 1.500 km** | 8.964 | **39,79 BRL** | **18,48%** | **20,52** | **11,67%** | **3,948** ⭐ |

Đơn ở xa nhất phải trả phí ship **gấp 3 lần**, chờ **gấp 3,2 lần**, và bị đánh giá
thấp hơn **0,3 sao**. Toàn bộ chuỗi này là một đường thẳng — không có điểm gãy.

📊 `16_distance_freight.png`
📄 `mart_freight_by_distance.csv`

---

## 6. Ngành hàng: doanh thu cao không đồng nghĩa khách hài lòng

**Top 5 theo doanh thu:**

| Ngành hàng | Đơn | Doanh thu | Điểm TB | % phí ship |
|---|---:|---:|---:|---:|
| health_beauty | 8.757 | 1.251.146 | 4,154 ⭐ | 12,64% |
| watches_gifts | 5.599 | 1.194.825 | 4,028 ⭐ | 7,72% |
| bed_bath_table | 9.394 | 1.035.485 | 3,902 ⭐ | 16,48% |
| sports_leisure | 7.656 | 977.729 | 4,122 ⭐ | 14,59% |
| computers_accessories | 6.636 | 902.923 | 3,951 ⭐ | 13,94% |

**Nhóm tệ nhất (≥ 200 đơn):**

| Ngành hàng | Đơn | Điểm TB | % phí ship | Ghi chú |
|---|---:|---:|---:|---|
| **office_furniture** | 1.266 | **3,498** ⭐ | **20,03%** | Nội thất văn phòng: nặng, cồng kềnh |
| fixed_telephony | 209 | 3,708 ⭐ | 7,33% | |
| home_confort | 397 | 3,831 ⭐ | 12,67% | |
| audio | 347 | 3,835 ⭐ | 10,10% | 11,67% trễ |
| bed_bath_table | 9.394 | 3,902 ⭐ | 16,48% | Doanh thu #3 nhưng điểm thấp |

**`office_furniture` là trường hợp đáng lo nhất:** phí ship chiếm **20% giá trị đơn**
(gấp đôi mức trung bình 14,25%) và điểm chỉ **3,50 ⭐**. Đây là ngành mà chi phí
vận chuyển đang ăn mòn trải nghiệm.

📊 `09_category_top15.png`, `10_category_quality.png`
📄 `mart_category_performance.csv`

---

## 7. Trả góp: đòn bẩy tăng giá trị đơn rất mạnh

| Số kỳ | Đơn | % đơn | Giá trị đơn TB | Điểm TB |
|---|---:|---:|---:|---:|
| Trả 1 lần | 47.494 | 48,51% | 120,46 BRL | 4,152 ⭐ |
| 2–3 kỳ | 22.485 | 22,96% | 135,69 BRL | 4,110 ⭐ |
| 4–6 kỳ | 15.967 | 16,31% | 182,20 BRL | 4,089 ⭐ |
| 7–12 kỳ | 11.779 | 12,03% | **333,40 BRL** | 4,031 ⭐ |
| 13+ kỳ | 185 | 0,19% | **414,21 BRL** | 3,885 ⭐ |

Khách trả góp 7–12 kỳ chi **gấp 2,8 lần** khách trả 1 lần. Nhưng điểm review giảm
dần (4,15 → 3,89) — có thể do đơn giá trị cao thường là hàng cồng kềnh, dễ trễ.

**Phương thức thanh toán:**

| Phương thức | % đơn | % doanh thu | Giá trị đơn TB |
|---|---:|---:|---:|
| credit_card | 75,43% | 78,42% | 166,54 BRL |
| boleto | 19,89% | 17,96% | 144,65 BRL |
| voucher | 3,13% | 2,26% | 115,77 BRL |
| debit_card | 1,54% | 1,35% | 140,33 BRL |

📊 `12_payment_type.png`, `13_installments.png`
📄 `mart_payment_behavior.csv`, `mart_installments_band.csv`

---

## 8. Mùa vụ: Black Friday 11/2017 và cuộc khủng hoảng logistics đầu 2018

| Tháng | Đơn | Doanh thu | % trễ | Tăng trưởng |
|---|---:|---:|---:|---:|
| 2017-01 | 787 | 136.943 | 2,93% | — |
| 2017-11 | **7.423** | **1.172.192** | **12,40%** | **+53,28%** |
| 2017-12 | 5.620 | 861.527 | 7,46% | −26,50% |
| 2018-02 | 6.625 | 979.486 | **14,13%** | −11,11% |
| 2018-03 | 7.168 | 1.152.657 | **18,96%** | +17,68% |
| 2018-06 | 6.145 | 1.020.382 | **1,16%** | −10,94% |
| 2018-08 | 6.421 | 996.974 | 6,19% | −4,12% |

Hai sự kiện đáng chú ý:

1. **Black Friday 11/2017:** đơn tăng 53% và tỷ lệ trễ nhảy từ 4,18% lên **12,40%** —
   hệ thống vận chuyển không theo kịp đỉnh.
2. **Khủng hoảng 2–3/2018:** dù số đơn *không* tăng, tỷ lệ trễ vọt lên **14,13%**
   rồi **18,96%** — cao nhất toàn bộ dữ liệu. Đến 6/2018 lại rơi về 1,16%.

Sự đảo chiều đột ngột này (1,16% ↔ 18,96%) cho thấy vấn đề **vận hành cục bộ**,
không phải quy luật mùa vụ.

**Theo thứ:** Thứ Hai mua nhiều nhất (16,27% đơn), Thứ Bảy ít nhất (10,95%).
Giá trị đơn gần như không đổi theo thứ (155–163 BRL).

📊 `14_monthly_orders.png`, `15_weekday.png`
📄 `mart_monthly_trend.csv`, `mart_weekday_pattern.csv`

---

## 9. Hàng nặng: phí ship tăng 4,5 lần, điểm giảm

| Khối lượng | Đơn | Phí ship TB | % 1–2 sao | % trễ | Điểm TB |
|---|---:|---:|---:|---:|---:|
| 0–500 g | 35.455 | 15,42 BRL | 12,26% | 6,61% | 4,175 ⭐ |
| 500 g–1 kg | 16.585 | 17,30 | 11,76% | 6,49% | 4,206 ⭐ |
| 1–5 kg | 24.981 | 20,51 | 12,13% | 7,21% | 4,182 ⭐ |
| 5–15 kg | 9.242 | 34,22 | 13,21% | 7,70% | 4,127 ⭐ |
| **> 15 kg** | 1.900 | **70,16 BRL** | **18,18%** | **10,46%** | **3,951** ⭐ |

Hàng trên 15 kg có phí ship **gấp 4,5 lần** hàng nhẹ, tỷ lệ trễ cao gấp 1,6 lần và
tỷ lệ bị 1–2 sao cao gấp 1,5 lần.

📊 `17_weight_impact.png`
📄 `mart_product_attributes.csv`

---

## Khuyến nghị hành động

Xếp theo **tác động trên mỗi đồng công sức**:

| Ưu tiên | Hành động | Cơ sở |
|---|---|---|
| **1** | **Giảm trễ ở RJ, MA, CE, BA, PA.** RJ là ưu tiên cao nhất vì 12.648 đơn + 12,15% trễ | Mỗi 1% trễ giảm ≈ 63 đơn × 2 sao |
| **2** | **Thông báo chủ động khi đơn sắp trễ**, trước ngày hứa | 62,41% khách trễ cho 1–2 sao; cảnh báo sớm thường làm giảm mức phẫn nộ |
| **3** | **Rà soát 67 seller `at_risk`**, bắt đầu từ seller 982 đơn / 187.924 BRL | 6,15% doanh thu, 18,06% trễ |
| **4** | **Chương trình chuyển khách 1 lần → 2 lần** | Nhóm mua 2 lần đáng giá gấp 1,8 lần; hiện chỉ 3,04% khách |
| **5** | **Xem lại `office_furniture`** (phí ship 20%, 3,50 ⭐) | Ngành tệ nhất trong nhóm ≥ 200 đơn |
| **6** | **Chính sách ship cho hàng > 15 kg** | Phí 70 BRL, 18,18% bị 1–2 sao |
| **7** | **Đẩy trả góp 7–12 kỳ cho hàng giá cao** | Giá trị đơn 333 BRL, gấp 2,8 lần |

---

## Hạn chế — những gì dự án KHÔNG kết luận được

| # | Không kết luận được | Vì sao |
|---|---|---|
| 1 | **Biên lợi nhuận** | Dataset không có giá vốn; chỉ có doanh thu |
| 2 | **Chi phí marketing, CAC, LTV** | Không có dữ liệu chi phí |
| 3 | **Tỷ lệ chuyển đổi** | Không có dữ liệu traffic |
| 4 | **Đơn vị vận chuyển nào chậm** | Chỉ có ngày bàn giao, không có tên carrier |
| 5 | **Lý do huỷ đơn** | Chỉ có trạng thái |
| 6 | **Xu hướng 2016 và 9–10/2018** | Quá ít đơn (329 và 20), đã loại khỏi cửa sổ |
| 7 | **Nhân khẩu khách hàng** | Không có tuổi/giới tính/thu nhập |
| 8 | **Nội dung phản hồi** | Comment tiếng Bồ, ngoài scope (không làm NLP) |

**Về nhân quả:** mục 1 và 4 là **tương quan quan sát**, không phải thí nghiệm.
Xu hướng đơn điệu và mạnh, nhưng vẫn có thể còn yếu tố gây nhiễu (chất lượng sản phẩm,
kỳ vọng của khách). Không nên đọc như "giảm trễ 1 ngày chắc chắn tăng 0,3 sao".

**Về khoảng cách:** dùng đường chim bay (haversine), không phải đường bộ thực tế.
Ở Brazil, đường bộ thường dài hơn 20–40% so với đường chim bay.

---

## Bảng đối chiếu: phát hiện → SQL → CSV → chart

| # | Phát hiện | SQL | CSV | Chart |
|---|---|---|---|---|
| 1 | Giao trễ phá huỷ điểm đánh giá | `01_delivery_satisfaction.sql` | `mart_delivery_impact`, `mart_delivery_gap` | 01, 02, 03 |
| 2 | Khách không quay lại | `03_customer_segments.sql` | `mart_customer_segments` | 07, 08 |
| 3 | Seller rủi ro | `02_seller_scorecard.sql` | `mart_seller_scorecard` | 04, 05, 06 |
| 4 | Địa lý & vận hành | `05_geography.sql` | `mart_state_performance` | 11 |
| 5 | Kinh tế phí ship | `08_freight_economics.sql` | `mart_freight_by_distance` | 16 |
| 6 | Ngành hàng | `04_category_performance.sql` | `mart_category_performance` | 09, 10 |
| 7 | Trả góp | `06_payment_behavior.sql` | `mart_payment_behavior` | 12, 13 |
| 8 | Mùa vụ | `07_seasonality.sql` | `mart_monthly_trend` | 14, 15 |
| 9 | Hàng nặng | `09_product_attributes.sql` | `mart_product_attributes` | 17 |
