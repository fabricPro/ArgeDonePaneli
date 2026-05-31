"""v4.0-part-2 Adım 8 — DDL sonrası tek seferlik veri backfill.

Önce Supabase SQL Editor'da `supabase_schema_v4_0_part_2_adim8.sql` çalıştır.
Sonra bu script'i çalıştır:

    python scripts/migrate_v4_arastirma_backfill.py [--dry-run]

Ne yapar:
  1. Mevcut tüm ürünler için `country_code` (ISO-2) doldurur — country'den türetir.
  2. Mevcut tüm ürünler için `source_url_hash` doldurur — normalize edilmiş md5.
  3. product.notlar_html dolu olan ürünlerde, eğer aktif sürüm varsa ve
     aktif sürümün notlar_html'i boşsa → o sürüme kopyalar (sürüm-seviyesi nota geçiş).
     product.notlar_html SİLİNMEZ (fallback olarak kalır, geriye uyum).

Idempotent: sadece null/boş alanları doldurur. Tekrar çalıştırmak güvenli.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

# .env yükle (web/store.py ile aynı yöntem)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import store  # noqa: E402

# Ülke → ISO-2 kod eşleşmesi (TRACKED + sık görülen ihracat hedefleri)
COUNTRY_TO_ISO = {
    "türkiye": "TR", "turkiye": "TR", "turkey": "TR",
    "italya": "IT", "italy": "IT", "italia": "IT",
    "danimarka": "DK", "denmark": "DK",
    "almanya": "DE", "germany": "DE", "deutschland": "DE",
    "fransa": "FR", "france": "FR",
    "belçika": "BE", "belcika": "BE", "belgium": "BE",
    "abd": "US", "usa": "US", "united states": "US",
    "isveç": "SE", "isvec": "SE", "sweden": "SE",
    "isviçre": "CH", "isvicre": "CH", "switzerland": "CH",
    "hollanda": "NL", "netherlands": "NL",
    "ingiltere": "GB", "uk": "GB", "united kingdom": "GB",
    "avusturya": "AT", "austria": "AT",
    "hindistan": "IN", "india": "IN",
    "ispanya": "ES", "spain": "ES",
    "portekiz": "PT", "portugal": "PT",
}


def country_to_iso(country: str | None) -> str | None:
    if not country:
        return None
    return COUNTRY_TO_ISO.get(country.strip().lower())


def normalize_url(url: str | None) -> str:
    """Dedup için URL'i normalize et: scheme+host lowercase, fragment kaldır,
    trailing slash normalize, query string KORUNUR (renk varyantları farklı olabilir)."""
    if not url:
        return ""
    try:
        p = urlparse(url.strip())
        scheme = (p.scheme or "https").lower()
        host = (p.netloc or "").lower()
        # www. prefix'i kaldır (dedar.com == www.dedar.com)
        if host.startswith("www."):
            host = host[4:]
        path = p.path.rstrip("/") or "/"
        # Fragment dropped (anchor değil ürün adresi)
        return urlunparse((scheme, host, path, p.params, p.query, ""))
    except Exception:
        return url.strip().lower()


def url_hash(url: str | None) -> str | None:
    n = normalize_url(url)
    if not n:
        return None
    return hashlib.md5(n.encode("utf-8")).hexdigest()


def migrate(dry_run: bool = False) -> None:
    products = store.get_all()
    print(f"[i] Toplam ürün: {len(products)}")

    cc_updates = 0
    hash_updates = 0
    notlar_migrated = 0
    skipped = 0

    for prod in products:
        urun_id = prod.get("urun_id")
        if not urun_id:
            skipped += 1
            continue

        patch: dict = {}

        # 1) country_code
        if not prod.get("country_code"):
            iso = country_to_iso(prod.get("country"))
            if iso:
                patch["country_code"] = iso
                cc_updates += 1

        # 2) source_url_hash
        if not prod.get("source_url_hash") and prod.get("source_url"):
            h = url_hash(prod["source_url"])
            if h:
                patch["source_url_hash"] = h
                hash_updates += 1

        # 3) Ürün-seviyesi notu aktif sürüme kopyala (eğer aktif sürümde yoksa)
        product_note = (prod.get("notlar_html") or "").strip()
        teknik = prod.get("teknik") or {}
        surumler = teknik.get("surumler") or []
        if product_note and surumler:
            aktif_id = teknik.get("aktif_surum_id") or surumler[0].get("id")
            aktif = next((s for s in surumler if s.get("id") == aktif_id), surumler[0])
            if not (aktif.get("notlar_html") or "").strip():
                aktif["notlar_html"] = product_note
                # teknik objesinin tamamını update'e bas (referansla zaten değişti)
                patch["teknik"] = teknik
                notlar_migrated += 1

        if not patch:
            continue

        print(f"  • {urun_id}: {', '.join(patch.keys())}")
        if not dry_run:
            store.client().table(store.TABLE).update(patch).eq("urun_id", urun_id).execute()

    print()
    print("[✓] Backfill özeti:")
    print(f"    country_code  : {cc_updates}")
    print(f"    source_url_hash: {hash_updates}")
    print(f"    notlar→sürüm   : {notlar_migrated}")
    print(f"    atlanan        : {skipped}")
    if dry_run:
        print("    (dry-run — DB'ye yazılmadı)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="DB'ye yazma, sadece raporla")
    args = ap.parse_args()
    migrate(dry_run=args.dry_run)
