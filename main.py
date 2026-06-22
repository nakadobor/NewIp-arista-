import os
import argparse
import json
from datetime import datetime, timedelta
import ipaddress
import random

# 🔴 اضافه شدن رنج‌های رسمی کلودفلر
CLOUDFLARE_CIDRS = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22"
]

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


# 🔴 تابع جدید و هوشمند تولید آی‌پی‌های ناب کلودفلر با مدیریت کَش چرخشی ۳ روزه
def generate_pure_cloudflare_bank():
    """
    تولید آی‌پی‌های تکی تصادفی از رنج‌های رسمی کلودفلر با حذف تکراری‌ها
    و مکانیسم خودکار پاک‌سازی و ریست کل کَش هر ۳ روز یک‌بار
    """
    print("🔮 GENERATING PURE CLOUDFLARE IP BANK...")
    
    scanned_cache_path = "output/scanned_cache.txt"
    timestamp_path = "output/cache_timestamp.txt"
    os.makedirs("output", exist_ok=True)
    
    # ⏱️ بررسی مکانیسم انقضای ۳ روزه
    current_time = datetime.now()
    should_reset_cache = False
    
    if os.path.exists(timestamp_path):
        try:
            with open(timestamp_path, "r", encoding="utf-8") as tf:
                time_str = tf.read().strip()
                first_scan_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            
            # اگر از زمان اولین اسکن بیشتر از ۳ روز (۷۲ ساعت) گذشته باشه
            if current_time - first_scan_time >= timedelta(days=3):
                should_reset_cache = True
                print("⏰ 3 DAYS PASSED! Expiring old cache for a fresh scan cycle...")
        except Exception as e:
            print(f"⚠️ Error reading cache timestamp, forcing reset: {e}")
            should_reset_cache = True
    else:
        # اگر فایل تایم‌استمپ وجود نداره، یعنی اولین باره و تاریخ الان رو ثبت می‌کنیم
        try:
            with open(timestamp_path, "w", encoding="utf-8") as tf:
                tf.write(current_time.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            print(f"⚠️ Error writing initial timestamp: {e}")

    # 🧹 اجرای ریست کَش در صورت اتمام ۳ روز
    if should_reset_cache:
        if os.path.exists(scanned_cache_path):
            try:
                os.remove(scanned_cache_path)
                print("🗑️ scanned_cache.txt deleted successfully.")
            except Exception as e:
                print(f"⚠️ Could not delete cache file: {e}")
        
        # تاریخ جدید رو برای ۳ روز بعدی ست کن
        try:
            with open(timestamp_path, "w", encoding="utf-8") as tf:
                tf.write(current_time.strftime("%Y-%m-%d %H:%M:%S"))
            print("🆕 New 3-day cycle started.")
        except Exception as e:
            print(f"⚠️ Error updating timestamp: {e}")

    # 📖 خواندن کَش (اگر ریست شده باشه، خالیه)
    scanned_ips = set()
    if os.path.exists(scanned_cache_path):
        with open(scanned_cache_path, "r", encoding="utf-8") as cf:
            scanned_ips = set(line.strip() for line in cf if line.strip())

    pure_ips = []
    ips_per_cidr = 100 
    
    # ⚡ تولید آی‌پی‌ها و عبور از فیلتر تکراری‌ها
    for cidr in CLOUDFLARE_CIDRS:
        try:
            network = ipaddress.ip_network(cidr)
            hosts = list(network.hosts())
            
            available_hosts = [str(ip) for ip in hosts if str(ip) not in scanned_ips]
            
            # اگر کل رنج اسکن شده بود و خالی بود، موقتاً رنج رو باز کن
            if len(available_hosts) < ips_per_cidr:
                available_hosts = [str(ip) for ip in hosts]
                
            sample_size = min(ips_per_cidr, len(available_hosts))
            sampled = random.sample(available_hosts, sample_size)
            for ip in sampled:
                pure_ips.append(ip)
        except Exception as e:
            print(f"⚠️ Error processing CIDR {cidr}: {e}")
            
    # 💾 ذخیره آی‌پی‌های جدید در کَش
    try:
        for ip in pure_ips:
            scanned_ips.add(ip)
        with open(scanned_cache_path, "w", encoding="utf-8") as cf:
            cf.write("\n".join(scanned_ips))
    except Exception as e:
        print(f"⚠️ Warning updating scanned_cache.txt: {e}")

    # 🚀 نوشتن بانک اصلی برای اسکنر لایه TCP
    bank_path = "ip_bank.txt"
    try:
        with open(bank_path, "w", encoding="utf-8") as f:
            f.write("\n".join(pure_ips))
        print(f"✅ SUCCESSFULLY GENERATED {len(pure_ips)} PURE CLOUDFLARE IPS IN {bank_path}")
    except Exception as e:
        print(f"❌ Error writing to bank file: {e}")


def prepare():
    ensure_output()

    print("COMPACTING CACHE FILES")
    try:
        compact_cache_files()
        print("✅ CACHE COMPACTED SUCCESSFULLY")
    except Exception as e:
        print(f"⚠️ Warning during cache compaction (Skipped): {e}")

    if should_update_bank():
        # 🔴 قطع موقت سورس‌های قدیمی گیت‌هاب و استفاده اختصاصی از رنج کلودفلر
        print("🔄 BYPASSING OLD DOWNLOADER - SWITCHING TO PURE CLOUDFLARE RANGE")
        try:
            # download_sources() # ❌ موقتاً قطع شد
            # clean_ips()        # ❌ موقتاً قطع شد
            
            # 💡 جایگزین هوشمند: تزریق مستقیم رنج‌های کلودفلر
            generate_pure_cloudflare_bank()
            
            reset_cursor()
            print("BANK UPDATED WITH PURE CLOUDFLARE - CURSOR RESET")
        except Exception as e:
            print(f"⚠️ Warning during bank update (Skipped): {e}")


def run_tcp():
    prepare()

    print(
        "⚡ BYPASSING SPLIT - SCANNING ALL PURE IPS AT ONCE"
    )

    # مستقیم فایل اصلی بانک را به اسکنر می‌دهد
    input_file = "ip_bank.txt" 

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
    ensure_output()

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
    ensure_output()

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
    ensure_output()

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
    ensure_output()

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
    ensure_output()

    source_file = None
    if exists("output/results.txt"):
        source_file = "output/results.txt"
    elif exists("output/fingerprint_results.txt"):
        source_file = "output/fingerprint_results.txt"
    elif exists("output/https_live.txt"):
        source_file = "output/https_live.txt"

    if not source_file:
        print("NO VERIFIED DATA FOUND ACROSS ANY STAGES")
        return

    print(f"FOUND VALID DATA IN {source_file}, PROCEEDING TO FINALIZE...")

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

    if not exists("output/best_ips.txt") or os.path.getsize("output/best_ips.txt") == 0:
        print(f"⚠️ best_ips.txt was missing or empty! Forcing restore from {source_file}...")
        try:
            with open(source_file, "r", encoding="utf-8") as rf:
                ips = rf.read()
            with open("output/best_ips.txt", "w", encoding="utf-8") as bf:
                bf.write(ips)
            print("✅ FORCE CREATED BEST_IPS.TXT SUCCESSFULLY")
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
