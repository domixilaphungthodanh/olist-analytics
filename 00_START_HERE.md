# Bắt đầu đọc từ đâu?

## Nếu bro có 2 phút

Đọc `README.md` → hiểu dự án làm gì → mở `reports/figures/` xem chart.

## Nếu bro có 10 phút

1. `README.md` — tổng quan
2. `docs/idea.md` mục 1 + mục 7 — câu hỏi kinh doanh và 9 mảng phân tích
3. `docs/findings.md` — kết quả

## Nếu bro muốn hiểu sâu

Đọc theo thứ tự:

| Bước | File | Trả lời câu hỏi |
|---|---|---|
| 1 | `README.md` | Dự án làm gì? |
| 2 | `docs/idea.md` | Vì sao thiết kế như vậy? |
| 3 | `docs/data_dictionary.md` | Từng cột nghĩa là gì? Có bẫy gì? |
| 4 | `sql/schema.sql` | Mô hình dữ liệu ra sao? |
| 5 | `sql/03_analysis/*.sql` | Từng mảng phân tích tính thế nào? |
| 6 | `src/etl/*.py` | Pipeline chạy ra sao? |
| 7 | `docs/findings.md` | Kết luận là gì? |

## Nếu bro muốn tự chạy

```bash
python -m pip install -r requirements.txt
python -m src.etl.download_data
python run_all.py
```

## Ba điều quan trọng nhất của dự án

1. **`customer_unique_id` ≠ `customer_id`** — dùng nhầm là hỏng toàn bộ phân tích giữ chân.
2. **Không join `order_items` với `order_payments`** — sẽ nhân đôi doanh thu (fan-out).
3. **Cửa sổ phân tích là 2017-01 → 2018-08** — hai đầu dữ liệu quá thưa, vẽ vào sẽ gây hiểu sai.
