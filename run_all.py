"""Chạy toàn bộ pipeline bằng một lệnh.

    python run_all.py

Thứ tự bắt buộc:
    download_data -> build_db -> transform -> validate -> run_marts
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from src.etl.util import force_utf8_stdout

ROOT = Path(__file__).resolve().parent

STEPS: list[tuple[str, list[str]]] = [
    ("Giai đoạn 1 — Tải dữ liệu (9 CSV)", ["-m", "src.etl.download_data"]),
    ("Giai đoạn 3a — Nạp staging vào SQLite", ["-m", "src.etl.build_db"]),
    ("Giai đoạn 3b — Transform sang star schema", ["-m", "src.etl.transform"]),
    ("Giai đoạn 4 — Kiểm tra chất lượng", ["-m", "src.etl.validate"]),
    ("Giai đoạn 5 — Phân tích, CSV, chart", ["-m", "src.analysis.run_marts"]),
]


def main() -> int:
    force_utf8_stdout()
    os.chdir(ROOT)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

    line = "=" * 74
    print(line)
    print("OLIST E-COMMERCE ANALYTICS — CHẠY TOÀN BỘ PIPELINE")
    print(line)
    print(f"Thư mục: {ROOT}\n")

    for i, (title, args) in enumerate(STEPS, start=1):
        print(f"\n{'#' * 74}")
        print(f"# BƯỚC {i}/{len(STEPS)}: {title}")
        print(f"{'#' * 74}\n")
        result = subprocess.run([sys.executable, *args], env=env, check=False)
        if result.returncode != 0:
            print(f"\nDỪNG: bước {i} thất bại (exit code {result.returncode}).")
            return result.returncode

    print(f"\n{line}")
    print("HOÀN TẤT PIPELINE")
    print(f"  Database : {ROOT / 'data' / 'processed' / 'olist.db'}")
    print(f"  CSV      : {ROOT / 'reports'}")
    print(f"  Chart    : {ROOT / 'reports' / 'figures'}")
    print(f"  Báo cáo  : {ROOT / 'docs' / 'findings.md'}")
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
