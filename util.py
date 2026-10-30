"""Tiện ích dùng chung."""

from __future__ import annotations

import sys


def force_utf8_stdout() -> None:
    """Ép stdout/stderr sang UTF-8 để in tiếng Việt trên Windows console."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
