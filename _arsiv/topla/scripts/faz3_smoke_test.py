"""Faz 3.1-3.3 smoke test:
- 6 adaptor dosyasinin varligi (kvadrat, dedar, zimmer_rohde, ado_goldkante, etamine, travers)
- 310 gorsel migrasyonu (gorseller/ yeni konvansiyon)
- Mevcut JSON dosyalari parse OK (Kvadrat n=2)
- topla paketi importable

Calistirma: .venv\\Scripts\\python.exe topla\\scripts\\faz3_smoke_test.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    failures: list[str] = []

    # 1. Adaptor dosyalari
    print("[1] Adaptor dosyalari...")
    adaptorler = ROOT / "adaptorler"
    expected = {"kvadrat.md", "dedar.md", "zimmer_rohde.md", "ado_goldkante.md", "etamine.md", "travers.md"}
    found = {p.name for p in adaptorler.glob("*.md")}
    missing = expected - found
    if missing:
        failures.append(f"adaptorler eksik: {missing}")
    for fname in sorted(expected):
        p = adaptorler / fname
        if p.exists():
            lines = sum(1 for _ in p.open(encoding="utf-8"))
            print(f"    {fname}: {lines} satir")
        else:
            print(f"    {fname}: EKSIK")

    # 2. Gorsel migrasyonu
    print("[2] gorseller/ icerigi...")
    gorseller = ROOT / "gorseller"
    if not gorseller.exists():
        failures.append("gorseller/ klasoru yok")
    else:
        total = 0
        for marka_dir in sorted(gorseller.iterdir()):
            if marka_dir.is_dir():
                count = sum(1 for _ in marka_dir.rglob("*.jpg"))
                total += count
                # Marka altinda kac urun klasoru
                urun_dirs = sum(1 for d in marka_dir.iterdir() if d.is_dir())
                print(f"    {marka_dir.name}: {count} JPG, {urun_dirs} urun klasoru")
        print(f"    TOPLAM: {total} JPG")
        if total < 300:
            failures.append(f"gorseller toplam {total}, beklenen 310")

    # 3. Eski 02_gorseller hala duruyor mu (legacy)
    print("[3] Eski 02_gorseller/ (legacy)...")
    old = ROOT / "02_gorseller"
    if old.exists():
        old_count = sum(1 for _ in old.rglob("*.jpg"))
        print(f"    02_gorseller: {old_count} JPG (legacy, taranmiyor)")
    else:
        failures.append("02_gorseller legacy yok (silinmis olabilir)")

    # 4. Sema + marka profili + mevcut urun JSON'lari
    print("[4] JSON dosyalari parse...")
    paths = [
        ROOT / "sema" / "urun.json",
        ROOT / "sema" / "marka_profili.json",
        ROOT / "markalar" / "kvadrat.json",
        ROOT / "markalar" / "urunler" / "kvadrat_5539-air-line.json",
        ROOT / "markalar" / "urunler" / "kvadrat_5544-alpaca-leno.json",
    ]
    for p in paths:
        try:
            with p.open(encoding="utf-8") as f:
                d = json.load(f)
            print(f"    {p.relative_to(ROOT)}: OK")
        except Exception as e:
            failures.append(f"{p.relative_to(ROOT)}: {e}")

    # 5. topla paketi
    print("[5] topla paketi import...")
    sys.path.insert(0, str(ROOT))
    try:
        import topla  # type: ignore
        print(f"    topla {topla.__file__} OK")
    except Exception as e:
        failures.append(f"topla import: {e}")

    print()
    if failures:
        print(f"FAIL ({len(failures)} hata):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS - Faz 3.1-3.3 smoke test basarili")
    return 0


if __name__ == "__main__":
    sys.exit(main())
