"""Faz 5.5: Rubelli Charles (30750) canli test — Rubelli ilk denetim."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from topla.topla import scrape_and_score

URL = "https://www.rubelli.com/en/charles-30750"
print(f"Rubelli Charles canli test: {URL}")
print("Playwright Chromium baslatiliyor (~60-120 sn — 28 renk varyant loop)...")
print()

try:
    result = scrape_and_score(URL)
except Exception as e:
    print(f"HATA: {type(e).__name__}: {e}")
    sys.exit(1)

print("=== SUCCESS ===")
print(f"Brand: {result.get('brand')}")
print(f"Product: {result.get('product_name')}")
print(f"Composition: {result.get('composition_text')}")
print(f"Width: {result.get('width_cm')} cm")
print(f"Weave: {result.get('weave_type')}")
print(f"Country: {result.get('country_of_origin')}")
print(f"Cert: {result.get('certifications')}")
print(f"Staubli: {result.get('staubli_score')}/5")
print(f"Gorsel: {len(result.get('gorseller', []))}")
print(f"Ham cikti: {result.get('ham_cikti_path')}")
