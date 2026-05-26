"""Faz 6.9: Dedar v1.2 ham_cikti -> gorseller/dedar/<code>/ ve JSON guncelle.

4 Tier 1 urunu, scraper v1.2 variant page loop sonrasi (variant basina ~5 gorsel).
migrate_dedar_gorseller.py'dan template (ayni mantik).
"""
import sys
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# migrate_dedar_gorseller'daki migrate_urun fonksiyonunu kullan
from topla.scripts.migrate_dedar_gorseller import migrate_urun, _latest_ham, GORSELLER


PRODUCTS = [
    ("dedar_wide-linen-baobab_", "00T22044", "wide-linen-baobab", "dedar_00T22044-wide-linen-baobab.json"),
    ("dedar_wide-linen-atelier-1930_", "00T21015", "wide-linen-atelier-1930", "dedar_00T21015-wide-linen-atelier-1930.json"),
    ("dedar_wide-linen-signor-darcy_", "00T19031", "wide-linen-signor-darcy", "dedar_00T19031-wide-linen-signor-darcy.json"),
    ("dedar_twillman_", "00T23046", "twillman", "dedar_00T23046-twillman.json"),
]


def main():
    for prefix, code, slug, json_fname in PRODUCTS:
        try:
            ham = _latest_ham(prefix)
            print(f"\n>>> Latest ham for {prefix}: {ham.name}")
            migrate_urun(
                ham_json_path=ham,
                product_code=code,
                urun_slug=slug,
                urun_json_filename=json_fname,
            )
        except SystemExit as e:
            print(f"HATA: {e}")

    print("\n=== Toplam ===")
    total = sum(1 for _ in (GORSELLER / "dedar").rglob("*.jpg"))
    print(f"gorseller/dedar/ icindeki toplam JPG: {total}")


if __name__ == "__main__":
    main()
