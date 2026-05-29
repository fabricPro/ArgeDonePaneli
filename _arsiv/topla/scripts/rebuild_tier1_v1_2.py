"""Faz 6.9: Dedar scraper v1.2 (variant page loop fix) ile 4 Tier 1 urunu rebuild.

product_code fallback eklendi (body'den SKU extract). Variant page loop her renk
icin /?sku=<full_sku> URL'ine ayri gidip gallery'i alir.
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
    "https://dedar.com/wide-linen-baobab/",
    "https://dedar.com/wide-linen-atelier-1930/",
    "https://dedar.com/wide-linen-signor-darcy/",
    "https://dedar.com/twillman/",
]


def main():
    print(f"=== Tier 1 rebuild (scraper v1.2): {len(URLS)} URL ===\n")
    for i, url in enumerate(URLS, start=1):
        print(f"\n[{i}/{len(URLS)}] {url}")
        print("-" * 70)
        try:
            r = scrape_and_score(url)
            print(f"  Urun: {r.get('product_name')}")
            print(f"  En: {r.get('width_cm')} cm")
            print(f"  Stäubli: {r.get('staubli_score')}/5")
            print(f"  Gorsel: {len(r.get('gorseller') or [])} dosya (variant page loop)")
            print(f"  Ham: {r.get('ham_cikti_path')}")
        except Exception as e:
            print(f"  HATA: {e}")

        if i < len(URLS):
            time.sleep(3)


if __name__ == "__main__":
    main()
