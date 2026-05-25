"""Faz 6.5 smoke test: batch.py modulu import + regex extract testi (OFFLINE).

Calistirma:
    .venv\\Scripts\\python.exe topla\\scripts\\smoke_test_batch.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from topla.batch import BRANDS, existing_product_keys, extract_product_urls

print("=== BRANDS registry ===")
print(f"Toplam marka: {len(BRANDS)}")
for slug, spec in BRANDS.items():
    pattern_durum = "var" if spec.get("product_url_regex") else "YOK (Faz 7)"
    print(f"  {slug:20s} region={spec['region']:8s} regex={pattern_durum}")

print()
print("=== Mevcut JSON keys ===")
for slug in BRANDS:
    keys = existing_product_keys(slug)
    print(f"  {slug:20s} {len(keys)} dosya")

print()
print("=== Regex extract test (offline) ===")
sample_html = """
<html><body>
<a href="https://www.kvadrat.dk/en/products/curtains/5539-air-line">Air Line</a>
<a href="https://www.kvadrat.dk/en/products/curtains/5544-alpaca-leno">Alpaca Leno</a>
<a href="https://www.kvadrat.dk/en/products/curtains/9999-yeni-kumas">Yeni Kumas</a>
<a href="https://dedar.com/cobra/">Cobra</a>
<a href="https://dedar.com/days-like-now/">Days Like Now</a>
<a href="https://dedar.com/yeni-urun/">Yeni Urun</a>
<a href="https://www.rubelli.com/en/charles-30750">Charles</a>
<a href="https://www.rubelli.com/en/filicudi-30764">Filicudi</a>
<a href="https://www.rubelli.com/en/yeni-99999">Yeni</a>
<a href="/en/product-finder/details/melange-linen-10969-980">Melange Linen</a>
<a href="/en/product-finder/details/yeni-zr-99999-100">Yeni Z+R</a>
<a href="/en/product-finder/details/ora-3018-914">ORA</a>
<a href="/en/product-finder/details/yeni-ado-9999-100">Yeni ADO</a>
</body></html>
"""

for slug in ["kvadrat", "dedar", "rubelli", "zimmer_rohde", "ado_goldkante"]:
    products = extract_product_urls(slug, sample_html)
    print(f"\n  [{slug}] -> {len(products)} URL extract:")
    for p in products:
        print(f"    code={p['code']!s:10s} slug={p['slug']!s:25s} key={p['key']}")

print()
print("=== Diff with existing ===")
from topla.batch import diff_with_existing
for slug in ["kvadrat", "dedar", "rubelli", "zimmer_rohde", "ado_goldkante"]:
    products = extract_product_urls(slug, sample_html)
    diff = diff_with_existing(slug, products)
    print(f"  [{slug}] yeni={len(diff['yeni'])} bilinen={len(diff['bilinen'])}")
    for p in diff["yeni"]:
        print(f"    YENI: {p['key']} -> {p['url']}")

print()
print("OK — smoke test gecti.")
