"""Faz 1 + 2 smoke test:
- Tum kritik JSON dosyalarinin parse olmasi
- urun.json semasinin ana alanlarinin ürün JSON'larinda mevcut olmasi
- topla paketinin importable olmasi
- ham_cikti'dan iki Kvadrat ürün cikitisinin var olmasi
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check_json_parse(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    failures: list[str] = []

    # 1. Sema parse
    print("[1] Sema JSON parse...")
    try:
        urun_sema = check_json_parse(ROOT / "sema" / "urun.json")
        marka_sema = check_json_parse(ROOT / "sema" / "marka_profili.json")
        print(f"    urun.json v{urun_sema.get('_schema_version', '?')} OK")
        print(f"    marka_profili.json v{marka_sema.get('_schema_version', '?')} OK")
    except Exception as e:
        failures.append(f"sema parse: {e}")

    # 2. Marka profili parse
    print("[2] Marka profili parse...")
    try:
        kvadrat = check_json_parse(ROOT / "markalar" / "kvadrat.json")
        n = kvadrat["product_count_tracked"]
        rel = kvadrat["data_integrity"]["reliability_label"]
        avg = kvadrat["mobidik_strategic_assessment"]["average_feasibility_score"].get(
            "observed_at_n2"
        )
        print(f"    kvadrat.json n={n} reliability={rel} avg_feasibility_n2={avg}")
        if n != 2:
            failures.append(f"kvadrat profile: n={n}, beklenen 2")
    except Exception as e:
        failures.append(f"marka_profili parse: {e}")

    # 3. Urun JSON'lari parse + sema alanlari
    print("[3] Urun JSON parse + sema alani kontrolu...")
    expected_top_keys = {
        "urun_id", "brand", "brand_slug", "product_code", "product_name",
        "source_url", "scraped_at", "last_updated",
        "source_data", "ai_inferences", "image_analysis", "images",
        "mobidik_evaluation", "data_quality",
    }
    expected_source_data_keys = {
        "_provenance", "technical", "variants", "certifications", "commercial",
        "design_credit", "description_original", "description_tr", "style_note",
    }
    for fname in ("kvadrat_5539-air-line.json", "kvadrat_5544-alpaca-leno.json"):
        path = ROOT / "markalar" / "urunler" / fname
        try:
            d = check_json_parse(path)
            top_missing = expected_top_keys - set(d.keys())
            src_missing = expected_source_data_keys - set(d.get("source_data", {}).keys())
            staubli = d["mobidik_evaluation"]["staubli_feasibility"]["score"]
            print(
                f"    {fname}: top_missing={top_missing} src_missing={src_missing} "
                f"staubli={staubli}/5 completeness={d['data_quality']['completeness_percent']}%"
            )
            if top_missing:
                failures.append(f"{fname}: top-level alan eksik: {top_missing}")
            if src_missing:
                failures.append(f"{fname}: source_data alan eksik: {src_missing}")
        except Exception as e:
            failures.append(f"{fname}: {e}")

    # 4. topla paket importable
    print("[4] topla paketi import...")
    sys.path.insert(0, str(ROOT))
    try:
        import topla  # type: ignore
        print(f"    topla {topla.__file__} OK")
    except Exception as e:
        failures.append(f"topla import: {e}")

    # 5. ham_cikti'da Kvadrat ciktilari
    print("[5] ham_cikti/ kontrolu...")
    ham = ROOT / "topla" / "ham_cikti"
    if ham.exists():
        kvadrats = list(ham.glob("kvadrat_*.json"))
        print(f"    ham_cikti'da {len(kvadrats)} Kvadrat ciktisi var")
        if len(kvadrats) == 0:
            failures.append("ham_cikti bos")
    else:
        failures.append("ham_cikti klasoru yok")

    # 6. kapasite tablosu var mi
    print("[6] kapasite tablosu...")
    kap = ROOT / "kapasite" / "staubli_uretim_kapasitesi.md"
    if kap.exists():
        size = kap.stat().st_size
        print(f"    {kap.name} {size} byte")
    else:
        failures.append("kapasite tablosu yok")

    # 7. CLAUDE.md var mi
    print("[7] CLAUDE.md anayasa...")
    cm = ROOT / "CLAUDE.md"
    if cm.exists():
        first_line = cm.read_text(encoding="utf-8").splitlines()[0]
        print(f"    {first_line}")
    else:
        failures.append("CLAUDE.md yok")

    # Sonuc
    print()
    if failures:
        print(f"FAIL ({len(failures)} hata):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS — Faz 1 + 2 smoke test basarili")
    return 0


if __name__ == "__main__":
    sys.exit(main())
