"""Faz 5.5.1: Rubelli Filicudi (30764) — perdelik pilot, scraper v1.1 Use fix."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from topla.topla import scrape_and_score

URL = "https://www.rubelli.com/en/filicudi-30764"
print(f"Rubelli Filicudi canli test: {URL}")
print("Playwright Chromium baslatiliyor...")
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
print(f"Use: {result.get('source_data', {}).get('use_text')}" if isinstance(result.get('source_data'), dict) else "")
print(f"Cert: {result.get('certifications')}")
print(f"Staubli: {result.get('staubli_score')}/5")
print(f"Gorsel: {len(result.get('gorseller', []))}")
print(f"Ham cikti: {result.get('ham_cikti_path')}")
