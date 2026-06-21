#!/usr/bin/env python3
import os
from pathlib import Path

OUT = Path("output")

def ensure_output():
    OUT.mkdir(exist_ok=True)

def remove_temp():
    # حذف فایل‌های موقت احتمالی برای سبک شدن اکشنز
    for p in OUT.glob("*.tmp"):
        try:
            p.unlink()
        except Exception:
            pass

if __name__ == "__main__":
    ensure_output()
    remove_temp()
    print("cleanup: done")
