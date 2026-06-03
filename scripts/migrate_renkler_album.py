"""v4.0-part-2 Sprint 13.1 — "Renkler" albümü migration

Mevcut tüm ürünleri tara; albümleri arasında "Renkler" yoksa ekle.
Idempotent: tekrar çalıştırmak güvenli (varsa atlar).

Kullanım:
  python scripts/migrate_renkler_album.py            # uygula
  python scripts/migrate_renkler_album.py --dry-run  # sadece raporla
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT / "web"))
import store

SENTINEL = {"slug": "renkler", "name": "Renkler"}


def has_renkler(albums) -> bool:
    """Mevcut albümler arasında 'Renkler' var mı? (slug veya name eşleşmesi)"""
    for a in (albums or []):
        if not isinstance(a, dict):
            continue
        slug = (a.get("slug") or "").lower()
        name = (a.get("name") or "").strip().lower()
        if slug == "renkler" or name == "renkler":
            return True
    return False


def main(dry_run: bool = False):
    products = store.get_all()
    total = len(products)
    print(f"Toplam {total} urun taraniyor...\n")

    updated = 0
    skipped = 0
    for p in products:
        urun_id = p.get("urun_id", "?")
        if has_renkler(p.get("albums")):
            skipped += 1
            continue
        albums = list(p.get("albums") or [])
        albums.append(SENTINEL.copy())
        p["albums"] = albums
        if not dry_run:
            try:
                store.upsert(p)
                print(f"  OK  {urun_id}")
            except Exception as e:
                print(f"  X   {urun_id}  -> hata: {e}")
                continue
        else:
            print(f"  DRY {urun_id}  (eklenebilir)")
        updated += 1

    mode = " (DRY RUN — DB'ye yazilmadi)" if dry_run else ""
    print(f"\nSonuc{mode}:")
    print(f"  Eklenen:  {updated}")
    print(f"  Mevcuttu: {skipped}")
    print(f"  Toplam:   {total}")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
