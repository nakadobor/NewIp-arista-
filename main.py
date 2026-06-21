import os
import argparse
import json
from datetime import datetime, timedelta

from downloader import download_sources
from cleaner import clean_ips
from splitter import split_file
from cursor import reset_cursor

from scanner import (
    tcp_scan,
    tls_scan,
    https_scan,
    fingerprint_scan,
    geo_scan
)

from domains import extract_domains
from validator import validate_domains
from ranker import rank_results

from cache import optimize_stage_files, compact_cache_files

OUTPUT_DIR = "output"


def ensure_output():
    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )


def load_config():
    with open(
        "config.json",
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def exists(path):
    return (
        os.path.exists(path)
        and
        os.path.getsize(path) > 0
    )


def should_update_bank():
    return True


def prepare():
    ensure_output()

    print("COMPACTING CACHE FILES")
    compact_cache_files()

    if should_update_bank():
        print("DOWNLOAD START")
        download_sources()
        print("CLEAN START")
        clean_ips()
        reset_cursor()
        print("BANK UPDATED - CURSOR RESET")


def run_tcp():
    prepare()

    print(
        "ROLLING SPLIT"
    )

    input_file = split_file()

    if not exists(
        input_file
    ):
        print(
            "NO PART"
        )
        return

    print(
        "TCP START"
    )

    tcp_scan(
        input_file
    )

    print(
        "TCP DONE"
    )


def run_tls():
    prepare()

    if not exists(
        "output/tcp_live.txt"
    ):
        print(
            "NO TCP CACHE"
        )
        return

    print(
        "TLS START"
    )

    tls_scan()

    print(
        "TLS DONE"
    )


def run_https():
    prepare()

    if not exists(
        "output/tls_live.txt"
    ):
        print(
            "NO TLS CACHE"
        )
        return

    print(
        "HTTPS START"
    )

    https_scan()

    print(
        "HTTPS DONE"
    )


def run_fp():
    prepare()

    if not exists(
        "output/https_live.txt"
    ):
        print(
            "NO HTTPS CACHE"
        )
        return

    print(
        "FP START"
    )

    fingerprint_scan()

    print(
        "FP DONE"
    )


def run_geo():
    prepare()

    if not exists(
        "output/fingerprint_results.txt"
    ):
        print(
            "NO FP CACHE"
        )
        return

    print(
        "GEO START"
    )

    geo_scan()

    print(
        "GEO DONE"
    )


def run_finalize():
    prepare()

    # اول چک می‌کنیم فایل خروجی مرحله GEO وجود دارد یا خیر
    if not exists("output/results.txt"):
        print("NO RESULTS")
        return

    print("OPTIMIZE CACHE")
    optimize_stage_files()

    if exists("output/tls_live.txt"):
        print("DOMAIN EXTRACT")
        extract_domains()

    if exists("output/domains_raw.txt"):
        print("DOMAIN VALIDATE")
        validate_domains()

    print("RANK START")
    try:
        rank_results()
    except Exception as e:
        print(f"Ranker encountered an issue: {e}")

    # 🟢 چتر نجات دقیقاً در ایستگاه پایانی:
    # اگر رنکر فایل را نساخت یا خالیش کرد، ما از روی نتایج تایید شده، خودمان فایل را احیا می‌کنیم.
    if not exists("output/best_ips.txt") or os.path.getsize("output/best_ips.txt") == 0:
        print("⚠️ best_ips.txt was missing or empty! Restoring from verified results...")
        try:
            with open("output/results.txt", "r", encoding="utf-8") as rf:
                ips = rf.read()
            with open("output/best_ips.txt", "w", encoding="utf-8") as bf:
                bf.write(ips)
            print("✅ FORCE CREATED BEST_IPS.TXT FROM RESULTS")
        except Exception as e:
            print(f"Error restoring results: {e}")
    else:
        print("✅ best_ips.txt generated successfully by ranker.")

    print("FINAL DONE")


def main():
    ensure_output()

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--tcp",
        action="store_true"
    )

    parser.add_argument(
        "--tls",
        action="store_true"
    )

    parser.add_argument(
        "--https",
        action="store_true"
    )

    parser.add_argument(
        "--fp",
        action="store_true"
    )

    parser.add_argument(
        "--geo",
        action="store_true"
    )

    parser.add_argument(
        "--finalize",
        action="store_true"
    )

    args = parser.parse_args()

    load_config()

    print(
        "ARISTA START"
    )

    if args.tcp:
        run_tcp()

    elif args.tls:
        run_tls()

    elif args.https:
        run_https()

    elif args.fp:
        run_fp()

    elif args.geo:
        run_geo()

    elif args.finalize:
        run_finalize()

    else:
        run_tcp()

    print(
        "ARISTA DONE"
    )


if __name__ == "__main__":
    main()
