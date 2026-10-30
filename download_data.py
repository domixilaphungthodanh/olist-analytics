"""Giai đoạn 1 — Tải 9 file CSV gốc của Olist.

Dataset gốc: "Brazilian E-Commerce Public Dataset by Olist" (Kaggle).
Kaggle yêu cầu tài khoản, nên dự án dùng mirror công khai trên Hugging Face:
    https://huggingface.co/datasets/bulutttt/olist-raw-data

Chạy:
    python -m src.etl.download_data
"""

from __future__ import annotations

import time
import urllib.request

from .config import DATA_RAW, DATASET_BASE_URL, RAW_FILES
from .util import force_utf8_stdout

CHUNK = 1024 * 256  # 256 KB
MAX_RETRIES = 5
RETRY_WAIT = 3  # giây, tăng dần theo số lần thử


def _fetch_once(name: str, expected_size: int, target) -> None:
    """Tải 1 lần, ghi ra file tạm. Ném exception nếu lỗi."""
    url = DATASET_BASE_URL + name
    req = urllib.request.Request(url, headers={"User-Agent": "olist-analytics"})

    tmp = target.with_suffix(target.suffix + ".part")
    downloaded = 0
    next_mark = 25

    with urllib.request.urlopen(req, timeout=180) as resp, open(tmp, "wb") as out:
        while True:
            chunk = resp.read(CHUNK)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if expected_size:
                pct = downloaded * 100 / expected_size
                if pct >= next_mark:
                    print(f"      ... {next_mark:>3}%  ({downloaded / 1e6:5.1f} MB)")
                    next_mark += 25

    actual = tmp.stat().st_size
    if actual != expected_size:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"sai kích thước: {actual:,} B (cần {expected_size:,} B)")

    tmp.replace(target)


def download_one(name: str, expected_size: int) -> tuple[bool, str]:
    """Tải 1 file, có retry. Trả về (đã_tải, ghi_chú)."""
    target = DATA_RAW / name

    if target.exists():
        actual = target.stat().st_size
        if actual == expected_size:
            return False, f"đã có ({actual:,} B)"
        target.unlink()

    last_error = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _fetch_once(name, expected_size, target)
            return True, f"{expected_size:,} B"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            print(f"      lần {attempt}/{MAX_RETRIES} lỗi: {exc}")
            target.with_suffix(target.suffix + ".part").unlink(missing_ok=True)
            if attempt < MAX_RETRIES:
                wait = RETRY_WAIT * attempt
                print(f"      chờ {wait}s rồi thử lại...")
                time.sleep(wait)

    return False, f"THẤT BẠI sau {MAX_RETRIES} lần: {last_error}"


def main() -> None:
    force_utf8_stdout()
    DATA_RAW.mkdir(parents=True, exist_ok=True)

    line = "=" * 74
    print(line)
    print("TẢI DỮ LIỆU OLIST (GIAI ĐOẠN 1)")
    print(line)
    print(f"Nguồn : {DATASET_BASE_URL}")
    print(f"Đích  : {DATA_RAW}")
    print(f"Số file: {len(RAW_FILES)}\n")

    total_new = 0
    failed: list[str] = []

    for i, (name, size) in enumerate(RAW_FILES.items(), start=1):
        print(f"[{i}/{len(RAW_FILES)}] {name}")
        try:
            downloaded, note = download_one(name, size)
        except Exception as exc:  # noqa: BLE001
            print(f"      LỖI: {exc}")
            failed.append(name)
            continue
        if downloaded:
            total_new += 1
        print(f"      -> {note}" + ("  [mới tải]" if downloaded else ""))

    print()
    print(line)
    if failed:
        print(f"THẤT BẠI: {len(failed)} file")
        for f in failed:
            print(f"  - {f}")
    else:
        print(f"HOÀN TẤT: {len(RAW_FILES)} file, {total_new} file mới tải")
        total_size = sum((DATA_RAW / n).stat().st_size for n in RAW_FILES)
        print(f"Tổng dung lượng: {total_size / 1e6:.1f} MB")
    print(line)


if __name__ == "__main__":
    main()
