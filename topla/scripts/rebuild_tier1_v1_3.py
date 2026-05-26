"""Faz 6.11: 3 Tier 1 urun (Baobab haric, zaten v1.3) v1.3 scraper ile re-scrape.

variant page full gallery (her variant 2-3 image: kumas + lifestyle + main).
"""
import sys
import time
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from topla.topla import scrape_and_score


URLS = [
    "https://dedar.com/wide-linen-atelier-1930/",
    "https://dedar.com/wide-linen-signor-darcy/",
    "https://dedar.com/twillman/",
]


def main():
    print(f"=== v1.3 rebuild: {len(URLS)} URL ===\n")
    for i, url in enumerate(URLS, start=1):
        print(f"\n[{i}/{len(URLS)}] {url}", flush=True)
        try:
            r = scrape_and_score(url)
            print(f"  Urun: {r.get('product_name')} | gorsel: {len(r.get('gorseller') or [])} dosya", flush=True)
        except Exception as e:
            print(f"  HATA: {e}", flush=True)
        if i < len(URLS):
            time.sleep(3)


if __name__ == "__main__":
    main()
