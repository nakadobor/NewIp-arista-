import json
import requests
import os

OUTPUT_FILE = "output/ip_bank.txt"

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_source(url, limit=None):
    try:
        r = requests.get(url, timeout=30)
        if r.ok:
            lines = r.text.splitlines()
            if limit and len(lines) > limit:
                return lines[:limit]
            return lines
    except:
        pass
    return []

def download_sources():
    cfg = load_config()
    all_ips = []
    ips_per_source = cfg.get("ips_per_source", 5000)
    
    for url in cfg.get("sources", []):
        ips = fetch_source(url, ips_per_source)
        if ips:
            all_ips.extend(ips)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(all_ips))

if __name__ == "__main__":
    download_sources()
