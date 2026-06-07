"""OnCalisma-V2 (Problem 2) — taksonomi doğrulama helper'ları birim testleri (DB'siz, saf).

Çalıştırma:  python scripts/test_taxonomy_validation.py
(Supabase bağlantısı gerektirmez; validate_* saf fonksiyonlardır.)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web"))
import store  # noqa: E402


def main() -> int:
    fails = 0

    def check(label, got, exp):
        nonlocal fails
        ok = got == exp
        if not ok:
            fails += 1
        print(f"{'OK  ' if ok else 'FAIL'}  {label:48} -> {got!r}  (beklenen {exp!r})")

    # --- enum (category / pattern / color_family): geçerli geçer, normalize, geçersiz None
    check("category 'tul'", store.validate_category("tul"), "tul")
    check("category 'TUL' (normalize)", store.validate_category("TUL"), "tul")
    check("category '  Outdoor ' (trim+lower)", store.validate_category("  Outdoor "), "outdoor")
    check("category 'banana' (gecersiz)", store.validate_category("banana"), None)
    check("category None", store.validate_category(None), None)
    check("category '' ", store.validate_category(""), None)
    check("pattern 'cizgili'", store.validate_pattern("cizgili"), "cizgili")
    check("pattern 'yari-duz'", store.validate_pattern("yari-duz"), "yari-duz")
    check("pattern 'zikzak' (gecersiz)", store.validate_pattern("zikzak"), None)
    check("color_family 'krem-bej'", store.validate_color_family("krem-bej"), "krem-bej")
    check("color_family 'gold' (gecersiz)", store.validate_color_family("gold"), None)

    # --- weave_tags: karışık listede sadece geçerliler, normalize, tekrar/boş atılır, sıra korunur
    check("weave_tags karisik",
          store.validate_enum_list(["VUAL", "banana", "leno", "", "vual"], store.VALID_WEAVE_TAGS),
          ["vual", "leno"])
    check("weave_tags hepsi gecersiz",
          store.validate_enum_list(["xxx", "yyy"], store.VALID_WEAVE_TAGS), [])
    check("weave_tags None", store.validate_enum_list(None, store.VALID_WEAVE_TAGS), [])

    # --- style_tags: serbest, trim, boş at, tekrar at (içerik doğrulanmaz)
    check("style_tags trim+dedup",
          store.validate_str_list(["  premium ", "premium", "", "minimal"]),
          ["premium", "minimal"])
    check("style_tags serbest (banana gecerli)",
          store.validate_str_list(["banana", "her sey"]), ["banana", "her sey"])
    check("style_tags None", store.validate_str_list(None), [])

    print("-" * 60)
    print("SONUC:", "TUM TESTLER GECTI (PASS)" if fails == 0 else f"{fails} HATA (FAIL)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
