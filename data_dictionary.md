# Từ điển dữ liệu — Olist

Mô tả **9 bảng gốc** kèm số liệu thật đo được trên dataset (không phải lý thuyết).

---

## 1. `olist_orders_dataset.csv` — 99.441 dòng

| Cột | Kiểu | Ý nghĩa | Ghi chú |
|---|---|---|---|
| `order_id` | text | Mã đơn | **Duy nhất** (99.441/99.441) |
| `customer_id` | text | Mã khách **theo đơn** | ⚠️ **Không phải** con người — xem bẫy B1 |
| `order_status` | text | Trạng thái | 8 giá trị, `delivered` chiếm 97,02% |
| `order_purchase_timestamp` | datetime | Thời điểm đặt | 0 NULL |
| `order_approved_at` | datetime | Thời điểm duyệt thanh toán | 160 NULL (0,2%) |
| `order_delivered_carrier_date` | datetime | Ngày **bàn giao cho đơn vị vận chuyển** | 1.783 NULL (1,8%) |
| `order_delivered_customer_date` | datetime | Ngày **khách nhận được** | 2.965 NULL (3,0%) |
| `order_estimated_delivery_date` | datetime | Ngày **hứa giao** | 0 NULL |

### Phân bố trạng thái

| Trạng thái | Số đơn | % |
|---|---:|---:|
| delivered | 96.478 | 97,02% |
| shipped | 1.107 | 1,11% |
| canceled | 625 | 0,63% |
| unavailable | 609 | 0,61% |
| invoiced | 314 | 0,32% |
| processing | 301 | 0,30% |
| created | 5 | 0,01% |
| approved | 2 | 0,00% |

### Dòng thời gian của một đơn

```
order_purchase_timestamp    ← khách bấm đặt
        ↓
order_approved_at           ← thanh toán được duyệt
        ↓
order_delivered_carrier_date ← Olist giao cho đơn vị vận chuyển
        ↓
order_delivered_customer_date ← khách nhận hàng
        ↑
order_estimated_delivery_date ← ngày Olist HỨA (có thể sau ngày thực tế)
```

**Ba chỉ số thời gian tách ra từ chuỗi này:**

| Chỉ số | Công thức | Ý nghĩa nghiệp vụ |
|---|---|---|
| `lead_time_days` | `delivered - purchase` | Tổng thời gian khách phải chờ |
| `carrier_handover_days` | `carrier_date - approved_at` | Olist xử lý chậm hay nhanh |
| `transit_days` | `delivered - carrier_date` | Đơn vị vận chuyển chậm hay nhanh |

> Tách 3 chỉ số này rất quan trọng: nếu chỉ nhìn `lead_time_days`, không biết
> **lỗi thuộc về ai**. Đây là điểm phân biệt phân tích nông và phân tích sâu.

---

## 2. `olist_order_items_dataset.csv` — 112.650 dòng

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `order_id` | text | Mã đơn |
| `order_item_id` | int | Thứ tự dòng hàng **trong đơn** (1, 2, 3...) |
| `product_id` | text | Mã sản phẩm |
| `seller_id` | text | Mã người bán |
| `shipping_limit_date` | datetime | Hạn chót người bán phải gửi hàng |
| `price` | float | Giá sản phẩm (BRL) |
| `freight_value` | float | Phí vận chuyển (BRL) |

**Thống kê thật:**

| Chỉ số | Giá trị |
|---|---|
| Giá nhỏ nhất | 0,85 BRL |
| Giá lớn nhất | 6.735,00 BRL |
| Giá trung bình | 120,65 BRL |
| Phí ship trung bình | 19,99 BRL |
| Phí ship = 0 | 383 dòng |
| Số dòng hàng / đơn | TB 1,14 — tối đa 21 |

> ⚠️ `order_item_id` **không unique toàn bảng**, chỉ unique trong phạm vi 1 đơn.
> Khoá chính phải là **(`order_id`, `order_item_id`)**.

---

## 3. `olist_order_payments_dataset.csv` — 103.886 dòng

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `order_id` | text | Mã đơn |
| `payment_sequential` | int | Thứ tự lần thanh toán |
| `payment_type` | text | Phương thức |
| `payment_installments` | int | Số kỳ trả góp |
| `payment_value` | float | Số tiền (BRL) |

| Phương thức | Số lần | % |
|---|---:|---:|
| credit_card | 76.795 | 73,9% |
| boleto | 19.784 | 19,0% |
| voucher | 5.775 | 5,6% |
| debit_card | 1.529 | 1,5% |
| not_defined | 3 | 0,003% |

- Trả góp: **tối đa 24 kỳ**, trung bình 2,85 kỳ.
- Trung bình **1,04 lần thanh toán / đơn** (có đơn trả bằng 2 thẻ).

> **`boleto`** là hình thức thanh toán bằng phiếu ngân hàng phổ biến ở Brazil —
> khách in phiếu ra rồi ra ngân hàng trả. Đây là lý do có 160 đơn chưa `approved`
> và tỷ lệ huỷ cao hơn các phương thức khác.

---

## 4. `olist_order_reviews_dataset.csv` — 99.224 dòng

| Cột | Kiểu | Ý nghĩa | Ghi chú |
|---|---|---|---|
| `review_id` | text | Mã review | |
| `order_id` | text | Mã đơn | ⚠️ **KHÔNG unique** — 547 đơn có 2–3 review |
| `review_score` | int | Điểm 1–5 | TB **4,086** |
| `review_comment_title` | text | Tiêu đề | 88,3% NULL |
| `review_comment_message` | text | Nội dung | 58,7% NULL |
| `review_creation_date` | datetime | Ngày tạo | |
| `review_answer_timestamp` | datetime | Ngày khách phản hồi | Dùng để chọn review mới nhất |

### Phân bố điểm

| Sao | Số lượng | % |
|---|---:|---:|
| 1 ⭐ | 11.424 | 11,51% |
| 2 ⭐ | 3.151 | 3,18% |
| 3 ⭐ | 8.179 | 8,24% |
| 4 ⭐ | 19.142 | 19,29% |
| 5 ⭐ | 57.328 | 57,78% |

> Nhìn con số 4,086 điểm trung bình rất đẹp — nhưng **14,7% khách cho 1–2 sao**.
> Điểm trung bình che mất nhóm khách bất mãn. Đây chính là điểm khởi đầu của dự án.

---

## 5. `olist_customers_dataset.csv` — 99.441 dòng

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `customer_id` | text | Mã khách **theo đơn** — duy nhất 1-1 với đơn |
| `customer_unique_id` | text | Mã **con người thật** |
| `customer_zip_code_prefix` | int | 5 số đầu mã bưu chính |
| `customer_city` | text | Thành phố |
| `customer_state` | text | Bang (2 ký tự) |

### ⚠️ Bẫy quan trọng nhất của cả dataset

```
customer_id         : 99.441 giá trị  (1 đơn = 1 giá trị)
customer_unique_id  :  96.096 giá trị  (1 người = 1 giá trị)
```

Nếu dùng `customer_id` để đếm khách quay lại → **kết quả luôn bằng 0%**, vì
mỗi đơn có một mã khách riêng. Đây là lỗi rất nhiều bài phân tích Olist trên
internet mắc phải.

**Sự thật:** 96,88% khách chỉ mua **1 lần**. Người mua nhiều nhất: 17 đơn.

---

## 6. `olist_products_dataset.csv` — 32.951 dòng

| Cột | Kiểu | Ý nghĩa | Ghi chú |
|---|---|---|---|
| `product_id` | text | Mã sản phẩm | |
| `product_category_name` | text | Danh mục (tiếng Bồ) | 610 NULL (1,9%) |
| `product_name_lenght` | int | Độ dài tên | ⚠️ **sai chính tả** trong dataset gốc |
| `product_description_lenght` | int | Độ dài mô tả | ⚠️ **sai chính tả** |
| `product_photos_qty` | int | Số ảnh | 610 NULL |
| `product_weight_g` | int | Khối lượng (gram) | 2 NULL |
| `product_length_cm` | int | Dài | 2 NULL |
| `product_height_cm` | int | Cao | 2 NULL |
| `product_width_cm` | int | Rộng | 2 NULL |

- **73 danh mục** trong dữ liệu sản phẩm.
- 610 sản phẩm không có danh mục và cũng không có số ảnh — nhiều khả năng là
  sản phẩm lỗi/chưa hoàn thiện.

---

## 7. `olist_sellers_dataset.csv` — 3.095 dòng

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `seller_id` | text | Mã người bán |
| `seller_zip_code_prefix` | int | Mã bưu chính |
| `seller_city` | text | Thành phố |
| `seller_state` | text | Bang |

- Người bán tập trung cực đoan ở **São Paulo (SP): 1.849 seller (59,7%)**.
- 509 seller chỉ bán được **1 món**.
- Top 10 seller chiếm **13,1%** doanh thu → thị trường phân tán, không độc quyền.

---

## 8. `olist_geolocation_dataset.csv` — 1.000.163 dòng

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `geolocation_zip_code_prefix` | int | 5 số đầu mã bưu chính |
| `geolocation_lat` | float | Vĩ độ |
| `geolocation_lng` | float | Kinh độ |
| `geolocation_city` | text | Thành phố |
| `geolocation_state` | text | Bang |

**Đặc điểm:** 1.000.163 dòng nhưng chỉ có **19.015 mã zip** → trung bình 52 dòng/zip,
zip nhiều nhất có **1.146 dòng**. Đây là dữ liệu điểm GPS thô.

> ⚠️ Join trực tiếp bảng này vào `orders` sẽ khiến 99.441 dòng biến thành
> **hàng triệu dòng**. Phải `GROUP BY zip` lấy trung bình lat/lng trước (bẫy B4).

**Toạ độ lỗi:** 42 dòng nằm ngoài lãnh thổ Brazil
(lat tới 45,07; lng tới 121,10 — tức ở châu Á). Đã loại.

---

## 9. `product_category_name_translation.csv` — 71 dòng

| Cột | Ý nghĩa |
|---|---|
| `product_category_name` | Tên tiếng Bồ |
| `product_category_name_english` | Tên tiếng Anh |

> ⚠️ Có **73** danh mục trong bảng products nhưng bảng dịch chỉ có **71**.
> Hai danh mục thiếu: `pc_gamer` và
> `portateis_cozinha_e_preparadores_de_alimentos` (đồ gia dụng nhà bếp).
> Cần xử lý để báo cáo không hiện `<NA>`.

---

## Bảng tổng hợp khoá

| Bảng | Khoá chính | Khoá ngoại |
|---|---|---|
| orders | `order_id` | `customer_id` → customers |
| order_items | (`order_id`, `order_item_id`) | `order_id`, `product_id`, `seller_id` |
| order_payments | (`order_id`, `payment_sequential`) | `order_id` |
| order_reviews | `review_id` | `order_id` |
| customers | `customer_id` | — |
| products | `product_id` | — |
| sellers | `seller_id` | — |
| geolocation | (không có — phải gộp theo zip) | — |
| translation | `product_category_name` | — |
