# Olist E-Commerce Analytics — Thiết kế dự án

> **Mục đích:** dự án portfolio phân tích dữ liệu end-to-end trên dataset **thật**
> của Olist (sàn TMĐT Brazil), stack **Python + SQLite**, kết quả gồm **SQL + CSV + chart + báo cáo**.
>
> **Khác biệt cốt lõi so với dự án `supplier-analytics`:** dữ liệu ở đây là **quan hệ thật**
> (99.441 đơn, 9 bảng có khoá ngoại thật), nên **mọi insight đều rút ra từ dữ liệu**,
> không phải do mình cài vào.

---

## 1. Câu hỏi kinh doanh cốt lõi

Dự án xoay quanh **một câu hỏi lớn**:

> **Olist tăng trưởng nhanh nhưng khách không quay lại — vấn đề nằm ở đâu?**

Từ đó tách thành 9 câu hỏi cụ thể (xem mục 7). Câu hỏi quan trọng nhất:

**"Giao hàng trễ ảnh hưởng bao nhiêu đến điểm đánh giá của khách?"**

Đây là câu hỏi có **tương quan thật** trong dữ liệu, và trả lời được nó là
trả lời được luôn vì sao khách không quay lại.

---

## 2. Quyết định thiết kế

| Mã | Quyết định | Lý do |
|---|---|---|
| **D1** | Tách **2 bảng fact**: `fact_orders` (grain = đơn) và `fact_order_items` (grain = dòng hàng) | Tránh lỗi **fan-out**: join items × payments sẽ nhân đôi doanh thu. Đây là lỗi phổ biến nhất khi phân tích Olist. |
| **D2** | Khoá khách hàng = **`customer_unique_id`**, không dùng `customer_id` | `customer_id` là **duy nhất theo từng đơn** (99.441 giá trị cho 99.441 đơn). Dùng nó thì **100% khách là khách mới** — phân tích giữ chân sẽ sai hoàn toàn. |
| **D3** | Mỗi đơn chỉ lấy **1 review** (review mới nhất theo `review_answer_timestamp`) | 547 đơn có 2–3 review. Nếu không dedupe, join sẽ nhân dòng. |
| **D4** | Cửa sổ phân tích: **2017-01-01 → 2018-08-31** | 2016 chỉ có 329 đơn, 9–10/2018 chỉ có 20 đơn → biểu đồ xu hướng sẽ "sụp" ở hai đầu gây hiểu sai. Cờ `in_analysis_window` tính sẵn trong `fact_orders`. |
| **D5** | Doanh thu ghi nhận trên đơn **không huỷ**: loại `canceled` + `unavailable` (1.234 đơn), giữ cả đơn đang xử lý | Hai trạng thái này không phải doanh thu thực. Cờ `is_revenue_order` được tính sẵn trong `fact_orders`. |
| **D6** | Không đưa `customer_zip_code_prefix` vào fact, mà join qua `dim_geolocation` | Geolocation có 1.000.163 dòng cho 19.015 zip → phải **gộp trước** khi join, nếu không sẽ bùng nổ số dòng. |
| **D7** | Stack giữ nguyên **Python + SQLite + matplotlib** | Tái dùng ~70% khung code của dự án trước (`config`, `util`, `build_db`, `run_marts`). |
| **D8** | Loại 42 dòng toạ độ nằm ngoài lãnh thổ Brazil | Có lat tới 45.07 và lng tới 121.10 — rõ ràng là dữ liệu sai. |

---

## 3. Dataset

**Nguồn:** *Brazilian E-Commerce Public Dataset by Olist* (Kaggle).
Vì Kaggle yêu cầu tài khoản, dự án tải qua mirror công khai trên Hugging Face
(`bulutttt/olist-raw-data`) — kích thước từng file khớp chính xác bản gốc.

### Cấu trúc thật (đã khảo sát)

| Bảng | Số dòng | Số cột | Grain |
|---|---:|---:|---|
| `olist_orders` | 99.441 | 8 | 1 dòng / đơn |
| `olist_order_items` | 112.650 | 7 | 1 dòng / dòng hàng (98.666 đơn) |
| `olist_order_payments` | 103.886 | 5 | 1 dòng / lần thanh toán (1,04 lần/đơn) |
| `olist_order_reviews` | 99.224 | 7 | 1 dòng / review (98.673 đơn có review) |
| `olist_customers` | 99.441 | 5 | 1 dòng / `customer_id` (96.096 người thật) |
| `olist_products` | 32.951 | 9 | 1 dòng / sản phẩm |
| `olist_sellers` | 3.095 | 4 | 1 dòng / người bán |
| `olist_geolocation` | 1.000.163 | 5 | nhiều dòng / mã zip |
| `product_category_name_translation` | 71 | 2 | từ điển PT → EN |

### Chất lượng dữ liệu — điểm mạnh

- **0 orphan** ở toàn bộ 6 quan hệ khoá ngoại đã kiểm tra. Dữ liệu quan hệ **sạch**.
- Không có NULL ở các cột khoá.
- Thời gian: 2016-09-04 → 2018-10-17.

### Chất lượng dữ liệu — 6 bẫy phải xử lý

| # | Bẫy | Quy mô | Hậu quả nếu bỏ qua |
|---|---|---|---|
| B1 | `customer_id` **không phải** khách hàng | 99.441 giá trị | Tỷ lệ khách quay lại = **0%** (sai hoàn toàn) |
| B2 | Nhiều review cho 1 đơn | 547 đơn (tối đa 3) | Join nhân dòng, điểm TB lệch |
| B3 | `order_id` trong bảng reviews **không unique** | — | Cùng B2 |
| B4 | Geolocation nhiều dòng / zip | 1.000.163 → 19.015 | Join trực tiếp làm nổ số dòng |
| B5 | Toạ độ sai ngoài Brazil | 42 dòng | Bản đồ có điểm ở châu Á |
| B6 | 2 category thiếu bản dịch | `pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos` | Báo cáo có ô `<NA>` |

**Lỗi chính tả trong chính dataset:** `product_name_lenght`, `product_description_lenght`
(đúng ra là *length*). Phải giữ nguyên tên gốc ở tầng staging, chỉ đổi tên ở tầng mart.

---

## 4. Phân tích cột

### 4.1 Giữ nguyên → staging

Toàn bộ 9 file được nạp nguyên trạng vào `stg_*`, **không sửa một giá trị nào**.
Mọi phép biến đổi diễn ra ở tầng `dim_*` / `fact_*`.

### 4.2 Cột dẫn xuất cần tạo

| Cột mới | Công thức | Dùng cho |
|---|---|---|
| `customer_unique_id` | từ `customers` | Khoá khách hàng thật (D2) |
| `lead_time_days` | `delivered - purchase` | Phân tích giao vận |
| `carrier_handover_days` | `carrier_date - approved_at` | Thời gian Olist xử lý |
| `transit_days` | `delivered - carrier_date` | Thời gian vận chuyển |
| `is_late` | `delivered > estimated` | Biến trung tâm của dự án |
| `delay_days` | `delivered - estimated` | Mức độ trễ |
| `estimated_buffer_days` | `estimated - delivered` (khi đúng hạn) | Olist dự phòng bao nhiêu ngày |
| `order_total` | `sum(price) + sum(freight)` | Giá trị đơn |
| `freight_ratio` | `freight / (price + freight)` | Gánh nặng phí ship |
| `product_volume_cm3` | `dài × rộng × cao` | Phân tích cồng kềnh |
| `category_en` | dịch từ `product_category_name` | Báo cáo tiếng Anh |
| `is_repeat_customer` | `count(orders) by customer > 1` | Phân tích giữ chân |
| `period` | `YYYY-MM` | Trục thời gian |

### 4.3 Cột bỏ đi

| Cột | Lý do |
|---|---|
| `review_comment_title` (88,3% NULL) | Quá thưa để phân tích |
| `review_comment_message` | Tiếng Bồ Đào Nha, ngoài scope (không làm NLP) |
| `geolocation_city/state` thô | Trùng lặp, sai chính tả; dùng bản gộp theo zip |
| `payment_sequential` | Chỉ là thứ tự, không mang thông tin |

---

## 5. Gap analysis — dự án KHÔNG trả lời được gì

Trung thực ngay từ đầu để không hứa hão:

| Mã | Không trả lời được | Vì sao |
|---|---|---|
| **G1** | Lợi nhuận / margin thật | **Không có giá vốn**. Chỉ có doanh thu. |
| **G2** | Tồn kho, stockout | Không có dữ liệu kho |
| **G3** | CAC, LTV, ROI marketing | Không có chi phí marketing |
| **G4** | Nhân khẩu khách (tuổi, giới tính, thu nhập) | Không có |
| **G5** | Tỷ lệ chuyển đổi (conversion rate) | Không có dữ liệu traffic/impression |
| **G6** | Lý do huỷ đơn | Chỉ có trạng thái, không có lý do |
| **G7** | Đơn vị vận chuyển nào chậm | Không có tên carrier, chỉ có ngày bàn giao |
| **G8** | Nội dung phản hồi của khách | Comment tiếng Bồ, không làm NLP |
| **G9** | Xu hướng 2016 và cuối 2018 | Quá ít đơn (329 và 20) |

**Điểm mạnh bù lại:** những gì dữ liệu **có** thì rất mạnh — chuỗi
*đặt hàng → duyệt → bàn giao → giao → đánh giá* là **đủ dài** để phân tích
nguyên nhân gốc của sự bất mãn.

---

## 6. Mô hình dữ liệu (star schema)

```
                    dim_date
                       |
   dim_customer ── fact_orders ── dim_payment (loại thẻ)
                       |    |
                       |    └── dim_geolocation (theo zip)
                       |
              fact_order_items ── dim_product ── dim_seller
                       |
                   fact_payments
```

### Dimensions

| Bảng | Số dòng (dự kiến) | Nội dung |
|---|---:|---|
| `dim_customer` | 96.096 | `customer_unique_id`, city, state, zip |
| `dim_product` | 32.951 | category PT/EN, weight, volume, photos |
| `dim_seller` | 3.095 | city, state, zip |
| `dim_geolocation` | ~19.015 | zip → lat/lng trung bình, city, state |
| `dim_date` | ~800 | năm, quý, tháng, tuần, thứ, cuối tuần |

### Facts

| Bảng | Grain | Số dòng | Cột đo lường |
|---|---|---:|---|
| `fact_orders` | 1 đơn | 99.441 | order_total, freight_total, items, lead_time, is_late, delay_days, review_score |
| `fact_order_items` | 1 dòng hàng | 112.650 | price, freight_value |
| `fact_payments` | 1 lần thanh toán | 103.886 | payment_value, installments |

### Tầng mart

9 bảng `mart_*` sinh ra từ SQL trong `sql/03_analysis/`.

---

## 7. 9 mảng phân tích

| # | Mảng | Câu hỏi trung tâm | Tín hiệu |
|---|---|---|---|
| **1** | **Giao vận & hài lòng** | Giao trễ làm điểm review giảm bao nhiêu sao? | 🟢 **Rất mạnh** — đây là trái tim dự án |
| **2** | **Seller scorecard** | Ai đáng giữ, ai nên loại? | 🟢 Mạnh (3.095 seller, phân hoá rõ) |
| **3** | **RFM & giữ chân** | Khách có quay lại không? Vì sao không? | 🟢 Mạnh (khám phá: chỉ 3,12% quay lại) |
| **4** | **Danh mục & sản phẩm** | Ngành hàng nào bán chạy, ship đắt, review thấp? | 🟢 Mạnh (73 category) |
| **5** | **Địa lý & giao vận** | Bang nào mua nhiều, chờ lâu, trả ship cao? | 🟢 Mạnh (27 bang) |
| **6** | **Thanh toán & trả góp** | Trả góp có làm đơn giá trị cao hơn? | 🟢 Mạnh (tới 24 kỳ) |
| **7** | **Mùa vụ** | Black Friday 11/2017 lớn cỡ nào? | 🟢 Mạnh (đỉnh 7.544 đơn) |
| **8** | **Kinh tế phí vận chuyển** | Phí ship chiếm bao nhiêu % đơn hàng? | 🟢 Mạnh (TB 19,99 BRL/dòng) |
| **9** | **Thuộc tính sản phẩm** | Hàng nặng/cồng kềnh có bị đánh giá thấp? | 🟡 Trung bình |

### Vì sao đây là dự án mạnh hơn dự án trước

Dự án `supplier-analytics` có **3/9 mảng phải báo "không có tín hiệu"** vì dataset gốc là nhiễu.
Ở đây **8/9 mảng có tín hiệu thật**. Ví dụ đã kiểm chứng:

```
Điểm review trung bình theo trạng thái đơn:
  delivered     4,16  (96.361 đơn)
  shipped       2,01
  canceled      1,81
  unavailable   1,53
  processing    1,28
```

Không cần vẽ biểu đồ cũng thấy: **đơn không giao được → khách cho 1–2 sao**.
Câu chuyện của dự án nằm ở việc **định lượng** khoảng cách đó.

---

## 8. Cấu trúc dự án

```
olist-analytics/
├── run_all.py                  # chạy toàn pipeline 1 lệnh
├── requirements.txt
├── docs/
│   ├── 00_START_HERE.md
│   ├── idea.md                 # tài liệu này
│   ├── data_dictionary.md      # ý nghĩa cột + profile thật
│   ├── getting_data.md         # cách tải dữ liệu
│   └── findings.md             # báo cáo kết quả (sinh sau)
├── sql/
│   ├── schema.sql
│   └── 03_analysis/            # 9 file .sql, mỗi file 1 mảng
├── src/
│   ├── etl/
│   │   ├── config.py
│   │   ├── download_data.py    # tải 9 CSV từ Hugging Face
│   │   ├── build_db.py         # CSV -> SQLite (staging)
│   │   ├── transform.py        # stg -> dim/fact
│   │   └── validate.py         # kiểm tra chất lượng
│   └── analysis/
│       └── run_marts.py        # chạy 9 mart + vẽ chart
├── notebooks/01_explore.ipynb
├── data/
│   ├── raw/                    # 9 CSV gốc (KHÔNG commit)
│   └── processed/              # olist.db + CSV mart (KHÔNG commit)
└── reports/figures/            # 14+ chart PNG
```

---

## 9. Roadmap

| GĐ | Việc | Output | Trạng thái |
|---|---|---|---|
| 1 | Tải dữ liệu | 9 CSV, 135 MB | ✅ xong |
| 2 | Khảo sát & thiết kế | `docs/idea.md` | ✅ xong |
| 3 | Build staging + dim/fact | `olist.db` (288 MB) | ✅ xong |
| 4 | Kiểm tra chất lượng | `mart_data_quality` — 40 PASS / 0 FAIL | ✅ xong |
| 5 | 9 mảng phân tích | 14 bảng `mart_*` + 14 CSV | ✅ xong |
| 6 | Chart + báo cáo | 17 PNG, `docs/findings.md`, notebook | ✅ xong |

---

## 10. Tiêu chí thành công

Dự án được coi là đạt nếu trả lời được **4 con số**:

1. **Bao nhiêu % đơn giao trễ?** → 6,79% (6.532 đơn trong cửa sổ)
2. **Giao trễ làm mất bao nhiêu sao?** → **2,02 sao** (4,29 → 2,27)
3. **Bao nhiêu % khách quay lại?** → **3,04%**
4. **Bang nào tệ nhất?** → **MA** (17,56% trễ); nặng nhất về quy mô là **RJ** (12.648 đơn, 12,15% trễ)

Và quan trọng nhất: **mỗi con số phải có chart chứng minh và SQL tái lập được.**

→ Xem kết quả đầy đủ tại `docs/findings.md`.
