"""v4.0-part-2 Sprint 4 + Sprint 5 — Notepad'tan tek seferlik bulk import.

Önce supabase_schema_v4_0_part_2_adim8.sql Supabase'de çalışmış olmalı
(research_pool tablosu + products.status/country_code/source_url_hash sütunları).

Kullanım:
  python scripts/bulk_import_arastirma_initial.py --dry-run
  python scripts/bulk_import_arastirma_initial.py

Yaptıkları:
  1. brands_registry — yeni firmaları ekle, mevcutları güncelle (+ default_master_url).
  2. research_pool — her ürün URL'i için bir satır ekle (duplicate'lar atlanır).
  3. Master-only firmalar (ürün URL'i olmayan) sadece brand_registry'e kaydedilir.

Sprint 5: og:image fetch artık yapılmaz — önizleme client-side Google s2 favicon
ile gösterilir. Bu yüzden --no-thumb flag'i kaldırıldı (gereksiz hızlandırma).

Idempotent: tekrar çalıştırmak güvenli.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Windows console için UTF-8 — Türkçe karakterler bozulmasın
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

# .env + web/ path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import store  # noqa: E402
import app    # noqa: E402  (brand_slugify, norm_country, _country_iso, now_iso)


# ============================================================
# VERİ — kullanıcı notepad'ından parse edilmiş
# ============================================================
DATA: list[dict] = [
    # === Ürün URL'i olan firmalar (pool'a satır gider) ===
    {
        "brand": "Maharam", "country": "ABD",
        "master": "https://www.maharam.com/maharam/products/window-covering/search",
        "products": [
            "https://www.maharam.com/maharam/products/radia/colors/004-afterparty",
        ],
    },
    {
        "brand": "Ludvig Svensson", "country": "İsveç",
        "master": "https://www.ludvigsvensson.com/en/interior-textiles/product-categories",
        "products": [
            "https://www.ludvigsvensson.com/en/interior-textiles/product/day-8000",
        ],
    },
    {
        "brand": "Drapilux by Sotexpro", "country": "Almanya",
        "master": "https://stoffbibliothek.drapilux.com/fabrics?isfabric=1&q=&r%5B%5D=6&u%5B%5D=19&act=0&acmin=0&acmax=1",
        "products": [
            "https://stoffbibliothek.drapilux.com/en/p-3141r-folk-mastic-48/25859",
        ],
    },
    {
        "brand": "Carlucci Jab", "country": "Almanya",
        "master": "https://carlucci.jab.de/tr/en/productadvancedsearch?searchTerm=&b=CA&page=1&d=008&d=001&d=007&d=003",
        "products": [
            "https://carlucci.jab.de/tr/en/p/CA1860/020",
            "https://carlucci.jab.de/tr/en/p/CA1766/021",
            "https://carlucci.jab.de/tr/en/p/JA6134-092",
        ],
    },
    {
        "brand": "Kvadrat", "country": "Danimarka",  # mevcut registry'de var — sadece master güncellenir
        "master": "https://www.kvadrat.dk/en/products/curtains?categories=Curtains&lastFacet=width&width=2.8-&width=3-",
        "products": [
            "https://www.kvadrat.dk/en/products/curtains/1073-daybreak-3",
        ],
    },
    {
        "brand": "Nya Nordiska", "country": "Almanya",  # mevcut registry'de var
        "master": "https://nya.com/en/product-catalogue/page/1/?filters=anwendung[12512]|verwendung[12663]",
        "products": [
            "https://nya.com/en/product/almina/",
            "https://nya.com/en/product/alma/",
            "https://nya.com/en/product/aalto/",
        ],
    },
    {
        "brand": "Etoffe", "country": "Fransa",
        "master": "https://www.etoffe.com/en/426-curtain-fabrics?range%5Bproperties.width%5D=280%3A",
        "products": [
            "https://www.etoffe.com/en/furnishing-fabrics/49612-huipil-outdoor-fabric-coordonne.html",
            "https://www.etoffe.com/en/furnishing-fabrics/11414-cosia-sheer-designers-guild.html#11414-74208",
            "https://www.etoffe.com/en/furnishing-fabrics/45010-belize-veil-nobilis.html#45010-407774",
            "https://www.etoffe.com/en/furnishing-fabrics/45018-mallorca-veil-nobilis.html",
        ],
    },
    {
        "brand": "Mark Alexander", "country": "İngiltere",
        "master": "https://www.markalexander.com/collections/all-collections",
        "products": [
            "https://www.markalexander.com/collections/sheers/solitude/solitude/grey-mist",
        ],
    },
    {
        "brand": "Fischbacher 1819", "country": "İsviçre",
        "master": "https://fischbacher1819.com/en/fabrics?cf_category%5B0%5D=Semi-sheer&cf_category%5B1%5D=Sheers",
        "products": [
            "https://fischbacher1819.com/en/fabrics/shirin-14783-327",
            "https://fischbacher1819.com/en/fabrics/benu-mambo-recycled-fr-14752-202",
            "https://fischbacher1819.com/en/fabrics/cusi-2998-805",
            "https://fischbacher1819.com/en/fabrics/inca-3006-627",
        ],
    },
    {
        "brand": "Casamance", "country": "Fransa",  # notepad'da Senegal, kullanıcı onayıyla Fransa
        "master": "https://www.casamance.com/en/catalog/category/view/s/tissus/id/355/?query=*&channel=casamance-en&sid=WjtcVW1NXjM8A9wx2kPVeOs61naOHN&filterSupportName=Fabrics&filterBrand=CASAMANCE~~~MAISON+CASAMANCE",
        "products": [
            "https://www.casamance.com/en/catalog/product/view/id/52683/s/les-precieuses-80090433/",
        ],
    },
    {
        # Camengo — Casamance ile kardeş marka (kullanıcı onayıyla ayrı kayıt)
        "brand": "Camengo", "country": "Fransa",
        "master": "https://www.camengo.com/en/collections/index/index/type/275/",
        "products": [
            "https://www.camengo.com/en/collections/single/view/id/5494/aria-des-voiles-2",
            "https://www.camengo.com/en/catalog/product/view/id/50871/s/hauckland-A11660344/",
            "https://www.camengo.com/en/collections/single/view/id/5391/eole",
            "https://www.camengo.com/en/catalog/product/view/id/43630/s/eole-49950482/",
            "https://www.camengo.com/en/catalog/product/view/id/43659/s/scirion-50051019/",
        ],
    },
    {
        "brand": "Designers Guild", "country": "İngiltere",  # notepad'da eksikti, kullanıcı onayıyla İngiltere
        "master": "https://www.designersguild.com/row/fabric/voiles-and-sheers/l1111",
        "products": [
            "https://www.designersguild.com/row/fabric/woven-fabric/l1108",
            "https://www.designersguild.com/row/fabric/designers-guild/aliseda-fabrics/c326",
        ],
    },

    # === Master-only firmalar (sadece brand_registry'e gider) ===
    {"brand": "Delius", "country": "Almanya",
     "master": "https://delius.de/en/products/contract-fabrics/", "products": []},
    {"brand": "FR-One", "country": "Belçika",
     "master": "https://www.fr-one.com/en/Products?country=TR&page=1&filter=nfpa701_2010_result.eq.true&page_size=50&sidebarView=facets",
     "products": []},
    {"brand": "Création Baumann", "country": "İsviçre",  # mevcut registry'de var
     "master": "https://creationbaumann.com/en/textil-finder/", "products": []},
    {"brand": "Vescom", "country": "Hollanda",
     "master": "https://vescom.com/en-us/curtain", "products": []},
    {"brand": "Romo", "country": "İngiltere",
     "master": "https://www.romo.com/collections/plains", "products": []},
    {"brand": "Villa Nova", "country": "İngiltere",
     "master": "https://www.villanova.co.uk/collections/plains", "products": []},
    {"brand": "Elitis", "country": "Fransa",
     "master": "https://elitis.fr/en/collections/fabric", "products": []},
]


# ============================================================
# REGISTRY GÜNCELLEME
# ============================================================

def update_registry(dry_run: bool) -> tuple[int, int]:
    """Yeni firmaları registry'e ekle, mevcutları default_master_url ile güncelle.
    Returns (yeni_eklenen, güncellenen)."""
    reg = store.get_app_state(app.BRANDS_REGISTRY_KEY) or {}
    if not isinstance(reg, dict):
        reg = {}
    brands_list = reg.get("brands") or []
    if not brands_list:
        # Boşsa app.seed_brands_registry() çağrısı yapmaktansa,
        # mevcut TRACKED_BRANDS'i koruyacak bir seed beklenir. Yine de boş başlatma güvenli.
        brands_list = app.seed_brands_registry()
        # seed sonrası registry diskten taze çekilebilir
        reg = store.get_app_state(app.BRANDS_REGISTRY_KEY) or {}
        brands_list = reg.get("brands") or brands_list

    by_slug = {b.get("slug"): b for b in brands_list if b.get("slug")}
    now = app.now_iso()
    added = 0
    updated = 0

    for entry in DATA:
        name = entry["brand"]
        slug = app.brand_slugify(name)
        country = app.norm_country(entry["country"])
        master = entry["master"]

        if slug in by_slug:
            b = by_slug[slug]
            changed = False
            if b.get("default_master_url") != master:
                b["default_master_url"] = master
                changed = True
            if not b.get("country") and country:
                b["country"] = country
                changed = True
            if changed:
                b["updated_at"] = now
                updated += 1
        else:
            by_slug[slug] = {
                "slug": slug,
                "name": name,
                "country": country,
                "website": None,
                "default_master_url": master,
                "created_at": now,
                "updated_at": now,
            }
            added += 1

    reg["brands"] = list(by_slug.values())
    reg.setdefault("_seeded_at", now)
    reg["_seed_version"] = app.BRANDS_REGISTRY_VERSION + "+sprint4"

    if not dry_run:
        store.set_app_state(app.BRANDS_REGISTRY_KEY, reg)

    return added, updated


# ============================================================
# POOL'A SATIR INSERT
# ============================================================

def insert_pool(dry_run: bool) -> tuple[int, int, int]:
    """Her ürün URL'i için research_pool'a satır ekle.
    Sprint 5: thumb_url=None — önizleme client-side favicon ile gösterilir.
    Returns (eklenen, duplicate_atlanan, hata)."""
    inserted = 0
    skipped = 0
    errors = 0

    for entry in DATA:
        products = entry.get("products") or []
        if not products:
            continue
        name = entry["brand"]
        slug = app.brand_slugify(name)
        country = app.norm_country(entry["country"])
        cc = app._country_iso(country)
        master = entry["master"]

        for purl in products:
            h = store.url_hash(purl)
            # Hızlı dedup kontrol — DB'ye yazmadan önce
            existing = None
            try:
                existing = store.research_find_by_hash(h) if h else None
            except Exception:
                existing = None
            if existing:
                skipped += 1
                print(f"  - SKIP duplicate: {name} -> {_short(purl)}")
                continue

            payload = {
                "master_url": master,
                "product_url": purl,
                "brand": name,
                "brand_slug": slug,
                "country": country,
                "country_code": cc,
                "thumb_url": None,   # Sprint 5: client-side favicon
            }

            if dry_run:
                print(f"  + DRY {name} -> {_short(purl)}")
                inserted += 1
                continue

            try:
                store.research_add(payload)
                inserted += 1
                print(f"  + {name} -> {_short(purl)}")
            except Exception as e:
                msg = str(e).lower()
                if "duplicate" in msg or "23505" in msg or "unique" in msg:
                    skipped += 1
                    print(f"  - DB dup: {name} -> {_short(purl)}")
                else:
                    errors += 1
                    print(f"  ! HATA: {name} -> {_short(purl)} | {e}")

    return inserted, skipped, errors


def _short(url: str, n: int = 60) -> str:
    return url if len(url) <= n else url[:n - 3] + "..."


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="DB'ye yazma, sadece raporla")
    args = ap.parse_args()

    print(f"[i] dry_run={args.dry_run}")
    print(f"[i] Toplam giriş: {len(DATA)} firma "
          f"({sum(len(e.get('products') or []) for e in DATA)} ürün URL'i)")
    print()

    print("=== 1) brands_registry güncellemesi ===")
    added, updated = update_registry(args.dry_run)
    print(f"    + {added} yeni firma  /  ~ {updated} güncellenmiş firma")
    print()

    print("=== 2) research_pool insert ===")
    inserted, skipped, errors = insert_pool(args.dry_run)
    print()
    print("=== ÖZET ===")
    print(f"    Eklenen pool satırı: {inserted}")
    print(f"    Duplicate atlanan  : {skipped}")
    print(f"    Hata               : {errors}")
    print(f"    Registry yeni      : {added}")
    print(f"    Registry güncel    : {updated}")
    if args.dry_run:
        print("    (dry-run — DB'ye yazılmadı)")


if __name__ == "__main__":
    main()
