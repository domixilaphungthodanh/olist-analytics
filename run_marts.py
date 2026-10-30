"""Giai đoạn 5 — Chạy 9 mảng phân tích, xuất CSV và vẽ chart.

Quy trình:
    1. Thực thi toàn bộ file .sql trong sql/03_analysis/ theo thứ tự tên file
    2. Tự phát hiện mọi bảng mart_* vừa sinh ra (trừ bảng chất lượng dữ liệu)
    3. Xuất từng bảng ra reports/<ten_bang>.csv
    4. Vẽ chart theo CHART_SPECS

Chạy:
    python -m src.analysis.run_marts
"""

from __future__ import annotations

import sqlite3
import textwrap
from pathlib import Path

import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from ..etl.config import DB_PATH, FIGURES, PROJECT_ROOT, SQL_DIR  # noqa: E402
from ..etl.util import force_utf8_stdout  # noqa: E402

REPORTS = PROJECT_ROOT / "reports"
ANALYSIS_DIR = SQL_DIR / "03_analysis"

# Bảng của tầng kiểm tra chất lượng — không xuất như mart phân tích
EXCLUDED = {"mart_data_quality", "mart_data_quality_summary"}

plt.rcParams.update(
    {
        "figure.dpi": 130,
        "savefig.dpi": 130,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.autolayout": True,
    }
)

BLUE = "#1f4e79"
ORANGE = "#c55a11"
GREEN = "#2e7d32"
GREY = "#7f7f7f"

# Nhãn hiển thị thân thiện (giá trị gốc trong SQL vẫn giữ dạng khoá để sắp xếp)
DELIVERY_LABELS = {
    "on_time_or_early": "Đúng hạn",
    "late_1_3d": "Trễ 1–3 ngày",
    "late_4_7d": "Trễ 4–7 ngày",
    "late_8d_plus": "Trễ ≥ 8 ngày",
    "not_delivered": "Không giao được",
}

DISTANCE_LABELS = {
    "1_0_100_km": "0–100 km",
    "2_100_300_km": "100–300 km",
    "3_300_600_km": "300–600 km",
    "4_600_1000_km": "600–1.000 km",
    "5_1000_1500_km": "1.000–1.500 km",
    "7_1500_km_tro_len": "> 1.500 km",
}

WEIGHT_LABELS = {
    "1_0_500_g": "0–500 g",
    "2_500g_1kg": "500 g–1 kg",
    "3_1_5_kg": "1–5 kg",
    "4_5_15_kg": "5–15 kg",
    "5_tren_15_kg": "> 15 kg",
}

INSTALLMENT_LABELS = {
    "1_1_ky": "1 kỳ",
    "2_2_3_ky": "2–3 kỳ",
    "3_4_6_ky": "4–6 kỳ",
    "4_7_12_ky": "7–12 kỳ",
    "5_13_ky_tro_len": "13+ kỳ",
}


def labels(series: pd.Series, mapping: dict[str, str]) -> list[str]:
    return [mapping.get(v, v) for v in series]


def run_sql_files(conn: sqlite3.Connection) -> list[str]:
    """Chạy mọi file SQL phân tích theo thứ tự.

    Tên bảng được đọc trực tiếp từ câu CREATE TABLE trong file (không dò
    sqlite_master), để chạy lại nhiều lần vẫn xác định đúng.
    """
    files = sorted(ANALYSIS_DIR.glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"Không tìm thấy file SQL nào trong {ANALYSIS_DIR}")

    pattern = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_]\w*)", re.I)
    made: list[str] = []
    for path in files:
        sql = path.read_text(encoding="utf-8")
        tables = [t for t in pattern.findall(sql) if t.startswith("mart_")]
        conn.executescript(sql)
        conn.commit()
        made.extend(tables)
        print(f"  {path.name:<32} -> {', '.join(tables) if tables else '(không tạo bảng)'}")
    return made


def _all_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'mart_%'"
    ).fetchall()
    return [r[0] for r in rows]


# =============================================================================
# CHART
# =============================================================================
def _bar(ax, x, y, color=BLUE, fmt="{:.2f}", rotation=0):  # noqa: ANN001
    bars = ax.bar(x, y, color=color)
    for b, v in zip(bars, y):
        ax.annotate(
            fmt.format(v),
            (b.get_x() + b.get_width() / 2, b.get_height()),
            ha="center", va="bottom", fontsize=8,
        )
    if rotation:
        ax.tick_params(axis="x", rotation=rotation)


def chart_delivery_impact(df: pd.DataFrame) -> None:
    d = df[df["delivery_bucket"] != "not_delivered"]
    x = labels(d["delivery_bucket"], DELIVERY_LABELS)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))

    ax = axes[0]
    _bar(ax, x, d["avg_review_score"], BLUE, "{:.2f}", 15)
    ax.set_title("Điểm đánh giá trung bình theo mức độ trễ")
    ax.set_ylabel("Điểm review (1–5)")
    ax.set_ylim(0, 5)

    ax = axes[1]
    _bar(ax, x, d["pct_low_review"], ORANGE, "{:.1f}%", 15)
    ax.set_title("Tỷ lệ khách cho 1–2 sao theo mức độ trễ")
    ax.set_ylabel("% đơn bị đánh giá thấp")
    ax.set_xlabel("Mức độ giao hàng")

    fig.suptitle("GIAO TRỄ PHÁ HUỶ ĐIỂM ĐÁNH GIÁ", fontsize=13, fontweight="bold")
    fig.savefig(FIGURES / "01_delivery_impact.png")
    plt.close(fig)


def chart_delivery_gap(df: pd.DataFrame) -> None:
    r = df.iloc[0]
    fig, ax = plt.subplots(figsize=(7, 4.4))
    labels = ["Đúng hạn / sớm", "Giao trễ"]
    values = [r["avg_review_on_time"], r["avg_review_late"]]
    bars = ax.bar(labels, values, color=[GREEN, ORANGE], width=0.55)
    for b, v in zip(bars, values):
        ax.annotate(f"{v:.2f} ★", (b.get_x() + b.get_width() / 2, v),
                    ha="center", va="bottom", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 5)
    ax.set_ylabel("Điểm review trung bình")
    ax.set_title(
        f"Giao trễ mất {r['review_gap']:.2f} sao\n"
        f"({int(r['orders_late']):,} đơn trễ / {r['late_rate_pct']:.2f}%)"
    )
    fig.savefig(FIGURES / "02_delivery_gap.png")
    plt.close(fig)


def chart_low_review_share(df: pd.DataFrame) -> None:
    d = df[df["delivery_bucket"] != "not_delivered"]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = range(len(d))
    ax.bar(x, d["pct_low_review"], color=ORANGE, label="1–2 sao")
    ax.bar(x, d["pct_five_star"], bottom=d["pct_low_review"], color=GREEN, label="5 sao")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels(d["delivery_bucket"], DELIVERY_LABELS), rotation=15)
    ax.set_ylabel("% đơn có review")
    ax.set_title("Cơ cấu điểm đánh giá theo mức độ trễ")
    ax.legend()
    fig.savefig(FIGURES / "03_review_mix.png")
    plt.close(fig)


def chart_seller_scatter(df: pd.DataFrame) -> None:
    d = df[df["orders"] >= 20].copy()
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = d["health_flag"].map(
        {"healthy": GREEN, "watch": "#f0a020", "at_risk": "#c00000", "low_volume": GREY}
    )
    ax.scatter(d["late_rate_pct"], d["avg_review_score"], s=d["orders"] / 4,
               c=colors, alpha=0.6, edgecolors="white", linewidths=0.4)
    ax.axvline(8, ls="--", lw=1, color=GREY)
    ax.axhline(4.0, ls="--", lw=1, color=GREY)
    ax.set_xlabel("Tỷ lệ giao trễ (%)")
    ax.set_ylabel("Điểm review trung bình")
    ax.set_title("Bản đồ seller: trễ càng cao, điểm càng thấp\n(kích thước điểm = số đơn)")
    fig.savefig(FIGURES / "04_seller_scatter.png")
    plt.close(fig)


def chart_seller_top(df: pd.DataFrame) -> None:
    d = df.nlargest(15, "revenue").sort_values("revenue")
    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.barh(d["seller_id"].str[:10], d["revenue"] / 1000, color=BLUE)
    ax.set_xlabel("Doanh thu (nghìn BRL)")
    ax.set_title("Top 15 seller theo doanh thu")
    fig.savefig(FIGURES / "05_seller_top15.png")
    plt.close(fig)


def chart_seller_flags(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    _bar(ax, df["health_flag"], df["pct_revenue"], ORANGE, "{:.1f}%", 10)
    ax.set_ylabel("% doanh thu")
    ax.set_title("Tỷ trọng doanh thu theo mức độ rủi ro của seller")
    fig.savefig(FIGURES / "06_seller_flags.png")
    plt.close(fig)


def chart_customer_segments(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    _bar(axes[0], df["segment"], df["pct_customers"], BLUE, "{:.2f}%", 10)
    axes[0].set_title("% số khách hàng")
    axes[0].set_ylabel("% khách")
    _bar(axes[1], df["segment"], df["pct_revenue"], GREEN, "{:.1f}%", 10)
    axes[1].set_title("% doanh thu")
    axes[1].set_ylabel("% doanh thu")
    fig.suptitle("KHÁCH QUAY LẠI: ÍT NHƯNG GIÁ TRỊ CAO", fontsize=13, fontweight="bold")
    fig.savefig(FIGURES / "07_customer_segments.png")
    plt.close(fig)


def chart_new_vs_returning(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.bar(df["period"], df["new_customer_orders"], label="Khách mới", color=BLUE)
    ax.bar(df["period"], df["returning_orders"],
           bottom=df["new_customer_orders"], label="Khách quay lại", color=ORANGE)
    ax.set_ylabel("Số đơn")
    ax.set_title("Đơn của khách mới vs khách quay lại theo tháng")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    fig.savefig(FIGURES / "08_new_vs_returning.png")
    plt.close(fig)


def chart_category(df: pd.DataFrame, top: int = 15) -> None:
    d = df.nlargest(top, "product_revenue").sort_values("product_revenue")
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    ax.barh(d["category"], d["product_revenue"] / 1000, color=BLUE)
    ax.set_xlabel("Doanh thu (nghìn BRL)")
    ax.set_title(f"Top {top} ngành hàng theo doanh thu")
    fig.savefig(FIGURES / "09_category_top15.png")
    plt.close(fig)


def chart_category_quality(df: pd.DataFrame) -> None:
    d = df[df["orders"] >= 100]
    fig, ax = plt.subplots(figsize=(9, 5))
    sc = ax.scatter(d["freight_ratio_pct"], d["avg_review_score"],
                    s=d["product_revenue"] / 2000, c=d["late_rate_pct"],
                    cmap="OrRd", alpha=0.75, edgecolors="white", linewidths=0.5)
    fig.colorbar(sc, ax=ax, label="Tỷ lệ giao trễ (%)")
    ax.set_xlabel("Phí ship / giá trị đơn (%)")
    ax.set_ylabel("Điểm review trung bình")
    ax.set_title("Ngành hàng: phí ship cao có đi kèm điểm thấp?\n"
                 "(kích thước điểm = doanh thu)")
    fig.savefig(FIGURES / "10_category_quality.png")
    plt.close(fig)


def chart_state(df: pd.DataFrame, top: int = 12) -> None:
    d = df.nlargest(top, "revenue").sort_values("revenue")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    axes[0].barh(d["state"], d["revenue"] / 1e6, color=BLUE)
    axes[0].set_xlabel("Doanh thu (triệu BRL)")
    axes[0].set_title(f"Top {top} bang theo doanh thu")

    d2 = df[df["orders"] >= 100].sort_values("avg_lead_time_days")
    axes[1].barh(d2["state"], d2["avg_lead_time_days"], color=ORANGE)
    axes[1].set_xlabel("Ngày chờ trung bình")
    axes[1].set_title("Thời gian giao hàng theo bang")
    fig.savefig(FIGURES / "11_state_performance.png")
    plt.close(fig)


def chart_payment(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    _bar(ax, df["payment_type"], df["pct_orders"], BLUE, "{:.1f}%", 10)
    ax.set_ylabel("% số đơn")
    ax.set_title("Phương thức thanh toán")
    fig.savefig(FIGURES / "12_payment_type.png")
    plt.close(fig)


def chart_installments(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.4))
    _bar(ax, labels(df["installment_band"], INSTALLMENT_LABELS),
         df["avg_order_value"], GREEN, "{:.0f}", 0)
    ax.set_ylabel("Giá trị đơn trung bình (BRL)")
    ax.set_xlabel("Số kỳ trả góp")
    ax.set_title("Trả góp càng nhiều kỳ, giá trị đơn càng cao")
    fig.savefig(FIGURES / "13_installments.png")
    plt.close(fig)


def chart_monthly(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.bar(df["period"], df["orders"], color=BLUE, alpha=0.85)
    ax.set_ylabel("Số đơn")
    ax.set_title("Số đơn theo tháng (2017-01 → 2018-08)")
    ax.tick_params(axis="x", rotation=45)
    peak = df.loc[df["orders"].idxmax()]
    ax.annotate(f"đỉnh {int(peak['orders']):,}", (peak["period"], peak["orders"]),
                ha="center", va="bottom", fontsize=9, fontweight="bold", color=ORANGE)
    fig.savefig(FIGURES / "14_monthly_orders.png")
    plt.close(fig)


def chart_weekday(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    _bar(ax, df["day_name"], df["pct_orders"], BLUE, "{:.1f}%")
    ax.set_ylabel("% số đơn")
    ax.set_title("Mua hàng theo thứ trong tuần")
    fig.savefig(FIGURES / "15_weekday.png")
    plt.close(fig)


def chart_distance(df: pd.DataFrame) -> None:
    d = df[~df["distance_band"].str.startswith("6_")]
    x = labels(d["distance_band"], DISTANCE_LABELS)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    _bar(axes[0], x, d["avg_freight"], BLUE, "{:.1f}", 25)
    axes[0].set_ylabel("Phí ship trung bình (BRL)")
    axes[0].set_title("Phí ship theo khoảng cách")
    _bar(axes[1], x, d["avg_lead_time_days"], ORANGE, "{:.1f}", 25)
    axes[1].set_ylabel("Ngày chờ trung bình")
    axes[1].set_title("Thời gian giao theo khoảng cách")
    fig.savefig(FIGURES / "16_distance_freight.png")
    plt.close(fig)


def chart_weight(df: pd.DataFrame) -> None:
    d = df[~df["weight_band"].str.startswith("6_")]
    x = labels(d["weight_band"], WEIGHT_LABELS)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    _bar(axes[0], x, d["avg_freight"], BLUE, "{:.1f}", 20)
    axes[0].set_ylabel("Phí ship trung bình (BRL)")
    axes[0].set_title("Phí ship theo khối lượng")
    _bar(axes[1], x, d["avg_review_score"], GREEN, "{:.2f}", 20)
    axes[1].set_ylabel("Điểm review trung bình")
    axes[1].set_ylim(0, 5)
    axes[1].set_title("Điểm đánh giá theo khối lượng")
    fig.savefig(FIGURES / "17_weight_impact.png")
    plt.close(fig)


CHART_SPECS: list[tuple[str, object]] = [
    ("mart_delivery_impact", chart_delivery_impact),
    ("mart_delivery_gap", chart_delivery_gap),
    ("mart_delivery_impact", chart_low_review_share),
    ("mart_seller_scorecard", chart_seller_scatter),
    ("mart_seller_scorecard", chart_seller_top),
    ("mart_seller_flags", chart_seller_flags),
    ("mart_customer_segments", chart_customer_segments),
    ("mart_new_vs_returning_monthly", chart_new_vs_returning),
    ("mart_category_performance", chart_category),
    ("mart_category_performance", chart_category_quality),
    ("mart_state_performance", chart_state),
    ("mart_payment_behavior", chart_payment),
    ("mart_installments_band", chart_installments),
    ("mart_monthly_trend", chart_monthly),
    ("mart_weekday_pattern", chart_weekday),
    ("mart_freight_by_distance", chart_distance),
    ("mart_product_attributes", chart_weight),
]


def main() -> None:
    force_utf8_stdout()
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Chưa có database: {DB_PATH}")

    REPORTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    line = "=" * 74
    print(line)
    print("CHẠY 9 MẢNG PHÂN TÍCH + XUẤT CSV + VẼ CHART (GIAI ĐOẠN 5)")
    print(line)

    conn = sqlite3.connect(DB_PATH)
    try:
        print("\n[A] Thực thi SQL")
        tables = run_sql_files(conn)

        print(f"\n[B] Xuất CSV ({len(tables)} bảng)")
        data: dict[str, pd.DataFrame] = {}
        for t in tables:
            df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
            data[t] = df
            df.to_csv(REPORTS / f"{t}.csv", index=False, encoding="utf-8-sig")
            print(f"  {t:<32} {len(df):>6,} dòng -> reports/{t}.csv")

        print("\n[C] Vẽ chart")
        n_chart = 0
        for table, fn in CHART_SPECS:
            if table in data:
                fn(data[table])  # type: ignore[operator]
                n_chart += 1
                print(f"  {table:<32} -> {fn.__name__}")
        print(f"  Tổng: {n_chart} chart trong {FIGURES}")

        print("\n[D] Xem nhanh kết quả")
        for t in ["mart_delivery_gap", "mart_delivery_impact", "mart_customer_segments",
                  "mart_seller_flags", "mart_payment_behavior"]:
            if t in data:
                print(f"\n--- {t} ---")
                with pd.option_context("display.width", 160, "display.max_columns", 30):
                    print(data[t].to_string(index=False))
    finally:
        conn.close()

    print(f"\n{line}")
    print("Xong. Xem chart trong:", FIGURES)
    print(line)


if __name__ == "__main__":
    main()
