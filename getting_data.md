# Tải dữ liệu Olist

Dataset gốc nằm trên Kaggle và **yêu cầu tài khoản**. Dự án dùng mirror công khai
trên Hugging Face để tải được mà không cần đăng nhập.

## Cách 1 — Dùng script của dự án (khuyến nghị)

```bash
python -m src.etl.download_data
```

Script sẽ:
1. Tải 9 file CSV vào `data/raw/`
2. Kiểm tra **kích thước từng file** khớp với bản gốc
3. Tự động thử lại tối đa 5 lần nếu kết nối bị ngắt (Hugging Face hay chặn khi tải liên tiếp)

Tổng dung lượng: **~135 MB**. Thời gian: 1–5 phút tuỳ mạng.

## Cách 2 — Tải thủ công bằng trình duyệt

Vào https://huggingface.co/datasets/bulutttt/olist-raw-data/tree/main
rồi tải 9 file sau vào `data/raw/`:

```
olist_customers_dataset.csv                   9,0 MB
olist_geolocation_dataset.csv                61,3 MB
olist_order_items_dataset.csv                15,4 MB
olist_order_payments_dataset.csv              5,8 MB
olist_order_reviews_dataset.csv              14,5 MB
olist_orders_dataset.csv                     17,7 MB
olist_products_dataset.csv                    2,4 MB
olist_sellers_dataset.csv                     0,2 MB
product_category_name_translation.csv         2,6 KB
```

## Cách 3 — Từ Kaggle (nếu bro có tài khoản)

```bash
pip install kaggle
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
```

Cần đặt `kaggle.json` (API token) vào `~/.kaggle/`.

## Kiểm tra sau khi tải

```bash
python -c "import pandas as pd; print(pd.read_csv('data/raw/olist_orders_dataset.csv').shape)"
```

Kết quả đúng phải là: `(99441, 8)`

Nếu đúng số dòng này thì dữ liệu đã tải thành công.
