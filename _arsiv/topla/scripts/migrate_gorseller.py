"""Gorsel migrasyonu: 02_gorseller (Cowork iterasyonu) -> gorseller/ (yeni konvansiyon).

Eski:  02_gorseller/<marka>/<urun_kodu><renk_kodu>_<sira>.jpg
Yeni:  gorseller/<marka>/<urun_kodu>/<renk_kodu>_<sira>.jpg

Marka bazli kod parse mantigi:
- kvadrat: urun=ilk 4 hane, renk=sonraki 4 hane (orn. 5539 0101)
- ado_goldkante: urun=ilk 4 hane, renk=son 3 hane (orn. 3009 110)
- zimmer_rohde, etamine, travers: urun=ilk 5 hane, renk=son 3 hane (orn. 10918 294)

Calistirma:
  .venv\\Scripts\\python.exe topla\\scripts\\migrate_gorseller.py --dry-run    # preview
  .venv\\Scripts\\python.exe topla\\scripts\\migrate_gorseller.py              # gercek kopyalama
  .venv\\Scripts\\python.exe topla\\scripts\\migrate_gorseller.py --move       # tasi (default: kopyala)
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "02_gorseller"
DST = ROOT / "gorseller"

# Marka bazli urun_kodu uzunlugu (renk_kodu sayfanin son hanelerini alir)
URUN_KOD_UZUN = {
    "kvadrat": 4,           # 5539 + 0101 (4-hane renk)
    "ado_goldkante": 4,     # 3009 + 110
    "zimmer_rohde": 5,      # 10918 + 294
    "etamine": 5,           # 19621 + 880
    "travers": 5,           # 44187 + 586
}

# Dosya adi pattern: <kod><sira>.jpg
FNAME_PATTERN = re.compile(r"^(\d+)_(\d+)\.jpg$", re.IGNORECASE)


def parse_filename(marka: str, fname: str) -> tuple[str, str, str] | None:
    """fname'i (urun_kodu, renk_kodu, sira) seklinde parse eder."""
    m = FNAME_PATTERN.match(fname)
    if not m:
        return None
    full_kod, sira = m.group(1), m.group(2)
    urun_len = URUN_KOD_UZUN.get(marka)
    if urun_len is None:
        return None
    if len(full_kod) <= urun_len:
        # Kod cok kisa — urun + renk ayirim yapilamiyor
        return None
    urun_kodu = full_kod[:urun_len]
    renk_kodu = full_kod[urun_len:]
    return urun_kodu, renk_kodu, sira


def migrate(dry_run: bool = False, move: bool = False) -> int:
    if not SRC.exists():
        print(f"HATA: kaynak yok: {SRC}", file=sys.stderr)
        return 1

    stats: dict[str, dict] = {}
    skipped: list[str] = []

    for marka_dir in sorted(SRC.iterdir()):
        if not marka_dir.is_dir():
            continue
        marka = marka_dir.name
        if marka not in URUN_KOD_UZUN:
            print(f"UYARI: bilinmeyen marka {marka}, atlandi", file=sys.stderr)
            continue

        marka_stats = {"copied": 0, "moved": 0, "skipped": 0, "parsed_ok": 0, "parsed_fail": 0}

        for jpg in sorted(marka_dir.glob("*.jpg")):
            parsed = parse_filename(marka, jpg.name)
            if parsed is None:
                skipped.append(f"{marka}/{jpg.name}")
                marka_stats["parsed_fail"] += 1
                continue
            marka_stats["parsed_ok"] += 1
            urun_kodu, renk_kodu, sira = parsed
            target_dir = DST / marka / urun_kodu
            target_file = target_dir / f"{renk_kodu}_{sira}.jpg"

            if target_file.exists():
                marka_stats["skipped"] += 1
                continue

            if dry_run:
                print(f"  {marka}/{jpg.name} -> {marka}/{urun_kodu}/{renk_kodu}_{sira}.jpg")
            else:
                target_dir.mkdir(parents=True, exist_ok=True)
                if move:
                    shutil.move(str(jpg), str(target_file))
                    marka_stats["moved"] += 1
                else:
                    shutil.copy2(str(jpg), str(target_file))
                    marka_stats["copied"] += 1

        stats[marka] = marka_stats

    print()
    print("=== Istatistik ===")
    print(f"{'Marka':<18} {'parse_OK':<10} {'parse_FAIL':<12} {'copied':<8} {'moved':<8} {'skipped':<8}")
    for marka, s in stats.items():
        print(
            f"{marka:<18} {s['parsed_ok']:<10} {s['parsed_fail']:<12} "
            f"{s['copied']:<8} {s['moved']:<8} {s['skipped']:<8}"
        )

    if skipped:
        print()
        print(f"=== Parse edilemeyen {len(skipped)} dosya ===")
        for s in skipped[:20]:
            print(f"  {s}")
        if len(skipped) > 20:
            print(f"  ... +{len(skipped) - 20} daha")

    print()
    mode = "DRY-RUN (gercek aksiyon yok)" if dry_run else ("MOVE" if move else "COPY")
    print(f"Mod: {mode}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="02_gorseller -> gorseller/ migrasyonu")
    p.add_argument("--dry-run", action="store_true", help="Sadece preview, dosya tasima/kopyalama yapma")
    p.add_argument("--move", action="store_true", help="Kopyalama yerine tasi (default: kopyala)")
    args = p.parse_args()
    return migrate(dry_run=args.dry_run, move=args.move)


if __name__ == "__main__":
    sys.exit(main())
