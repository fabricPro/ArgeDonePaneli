"""Cobra canli test — Dedar scraper'i Cobra URL'iyle calistirir, ham cikti uretir.

Anayasa kural #9: Python mekanik veri toplama; Claude Code sonra denetim yapar.
Kural #6: Bu cikti topla/ham_cikti/'ya yazilir. markalar/urunler/'e gecisi Claude denetim
sonrasi olur.
"""
import sys
import json
from pathlib import Path

# topla paketi parent dizinden import (script topla/scripts/ altinda)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from topla.topla import scrape_and_score

URL = "https://dedar.com/cobra/?sku=00T1906300004"
print(f"Cobra canli test basliyor: {URL}")
print("Playwright Chromium headless baslatiliyor (~30-60 sn)...")
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
print(f"Weave type: {result.get('weave_type')}")
print(f"Country of origin: {result.get('country_of_origin')}")
print(f"Certifications: {result.get('certifications')}")
print(f"Staubli score: {result.get('staubli_score')}/5")
print(f"Staubli reasons: {result.get('staubli_reasons')}")
print(f"Mobidik score: {result.get('mobidik_score')}/100")
print(f"Strategic note (ilk 200 karakter):")
note = result.get('strategic_note', '')
print(f"  {note[:200]}")
print(f"Gorsel sayisi: {len(result.get('gorseller', []))}")
print(f"Ham cikti dosyasi: {result.get('ham_cikti_path')}")
