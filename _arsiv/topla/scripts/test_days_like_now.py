"""Faz 5.4: Days Like Now canli test — Dedar n=2."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from topla.topla import scrape_and_score

URL = "https://dedar.com/days-like-now/?sku=00T2500700001"
print(f"Days Like Now canli test: {URL}")
print("Playwright Chromium baslatiliyor (~30-60 sn)...")
print()

try:
    result = scrape_and_score(URL)
except Exception as e:
    print(f"HATA: {type(e).__name__}: {e}")
    sys.exit(1)

print("=== SUCCESS ===")
print(f"Brand: {result.get('brand')}")
print(f"Product name: {result.get('product_name')}")
print(f"Composition: {result.get('composition_text')}")
print(f"Width cm: {result.get('width_cm')}")
print(f"Weave: {result.get('weave_type')}")
print(f"Country: {result.get('country_of_origin')}")
print(f"Certifications: {result.get('certifications')}")
print(f"Staubli: {result.get('staubli_score')}/5")
print(f"Mobidik: {result.get('mobidik_score')}/100")
print(f"Gorsel sayisi: {len(result.get('gorseller', []))}")
print(f"Ham cikti: {result.get('ham_cikti_path')}")
