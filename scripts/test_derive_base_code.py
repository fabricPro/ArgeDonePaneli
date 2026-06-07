"""OnCalisma-V2 (Problem 1) — derive_base_code() birim testleri (DB'siz, saf fonksiyon).

Çalıştırma:  python scripts/test_derive_base_code.py
(Supabase bağlantısı gerektirmez; store.derive_base_code saf bir fonksiyondur.)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web"))
import store  # noqa: E402

CASES = [
    # (product_url, brand_slug, beklenen base_code)
    ("https://www.jab.de/p/CA1580/092", "jab", "ca1580"),
    ("https://www.jab.de/p/CA1580/072", "jab", "ca1580"),
    ("https://www.jab.de/p/CA1580/070", "jab", "ca1580"),
    ("https://www.carlucci.com/p/JA7108-072", "carlucci", "ja7108"),
    ("https://www.carlucci.com/p/JA7108-060", "carlucci", "ja7108"),
    ("https://site.com/fabric/aurora?color=red", "x", "aurora"),
    ("https://site.com/fabric/aurora?color=blue", "x", "aurora"),
    ("https://site.com/fabric/aurora?colour=Green&utm_source=fb", "x", "aurora"),
    ("https://shop.com/p?id=9&color=red", "y", "p?id=9"),
    ("https://shop.com/p?id=9&color=blue", "y", "p?id=9"),
    # tuhaf / eşleşmeyen — fallback, hatasız:
    ("", "z", ""),
    ("not a url", "z", "not a url"),
    ("https://x.com/", "z", "x.com"),
]


def main() -> int:
    fails = 0
    seen_family = {}
    for url, bslug, exp_base in CASES:
        try:
            base, fk = store.derive_base_code(url, bslug)
        except Exception as e:  # asla olmamalı
            print(f"FAIL (exception): {url!r} -> {e}")
            fails += 1
            continue
        ok = (base == exp_base) and (fk == f"{bslug}:{exp_base}")
        print(f"{'OK  ' if ok else 'FAIL'}  {url!r:55} brand={bslug:9} -> base={base!r}  family={fk!r}")
        if not ok:
            fails += 1
        seen_family.setdefault(bslug, {}).setdefault(exp_base, set()).add(fk)

    # Varyant grup teyidi: aynı (brand, base) → aynı family_key
    for bslug, bases in seen_family.items():
        for b, fks in bases.items():
            if len(fks) != 1:
                print(f"FAIL (family tutarsız): {bslug}:{b} -> {fks}")
                fails += 1

    print("-" * 60)
    print("SONUC:", "TUM TESTLER GECTI (PASS)" if fails == 0 else f"{fails} HATA (FAIL)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
