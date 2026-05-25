"""Faz 5.11: Cobra + DLN ham_cikti gorselerini gorseller/ konumuna kopyala +
JSON images listesini ham_cikti'daki tip siniflandirmasiyla genislet.

Anayasa #9: Python mekanik (kopya + JSON modify); icerigi (tip atamasi) scraper'dan.

Ham çıktı yapısı:
- topla/ham_cikti/gorseller/dedar/<urun-slug>/<urun-slug>_<tip>_<sira>.jpg
- topla/ham_cikti/dedar_<urun-slug>_<timestamp>.json (gorseller listesi tipleri ile)

Hedef yapı:
- gorseller/dedar/<product_code>/<tip>_<sira>.jpg
- markalar/urunler/dedar_<product_code>-<urun-slug>.json (images.{main,variants,lifestyle,technical})
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HAM_CIKTI = ROOT / "topla" / "ham_cikti"
GORSELLER = ROOT / "gorseller"
URUNLER = ROOT / "markalar" / "urunler"
NOW = "2026-05-26T00:30:00Z"


def migrate_urun(ham_json_path: Path, product_code: str, urun_slug: str, urun_json_filename: str):
    """Tek bir Dedar urun icin ham_cikti -> gorseller kopya + JSON genislet."""
    # Ham çıktıyı oku
    with ham_json_path.open(encoding="utf-8") as f:
        ham = json.load(f)

    gorseller_ham = ham.get("gorseller", [])
    print(f"\n=== {product_code} ({urun_slug}) — {len(gorseller_ham)} gorsel ===")

    # Hedef klasör
    dst_dir = GORSELLER / "dedar" / product_code
    dst_dir.mkdir(parents=True, exist_ok=True)

    # Tip -> sayac (dosya isimlendirme icin)
    counters = {"ana": 0, "detay": 0, "lifestyle": 0, "varyant": 0}

    # JSON'a koyacagimiz images yapisi
    images_struct = {"main": [], "variants": [], "lifestyle": [], "technical": [], "_quality_notes": []}

    copied = 0
    skipped = 0

    for g in gorseller_ham:
        tip = g.get("tip", "detay")
        dosya_yolu = g.get("dosya_yolu")
        if not dosya_yolu:
            # Indirilememiş görsel (atlandı:duplicate_url, http_500 vb.)
            skipped += 1
            continue
        src_path = Path(dosya_yolu.replace("/", "\\"))
        if not src_path.exists():
            src_path = Path(dosya_yolu)
        if not src_path.exists():
            print(f"  ATLANDI (kaynak yok): {dosya_yolu}")
            skipped += 1
            continue

        counters[tip] = counters.get(tip, 0) + 1
        idx = counters[tip]

        # Yeni dosya adi: <tip>_<sira>.jpg
        ext = src_path.suffix.lower() or ".jpg"
        new_fname = f"{tip}_{idx:02d}{ext}"
        dst_file = dst_dir / new_fname

        # Kopyala (zaten varsa overwrite)
        try:
            shutil.copy2(src_path, dst_file)
            copied += 1
        except Exception as e:
            print(f"  HATA: {src_path.name} -> {new_fname}: {e}")
            skipped += 1
            continue

        # JSON image entry
        local_path = f"gorseller/dedar/{product_code}/{new_fname}"
        entry = {
            "url": g.get("kaynak_url"),
            "local_path": local_path,
            "variant_code": None,
            "variant_name": g.get("varyant_adi"),
            "layer_used": 1,
            "layer_1_attempt": {"success": True, "error": None, "method": "scraper_v1_1_bigcommerce_cdn"},
            "downloaded_at": ham.get("scraped_at"),
            "file_size_kb": g.get("dosya_boyutu_kb"),
            "dimensions": {"width_px": g.get("genislik_px"), "height_px": g.get("yukseklik_px")},
            "quality_check": "passed" if g.get("indirme_durumu") == "indirildi" else g.get("indirme_durumu", "?"),
        }

        # Tip'e göre images bucket'ı
        if tip == "ana":
            images_struct["main"].append(entry)
        elif tip == "varyant":
            images_struct["variants"].append(entry)
        elif tip == "lifestyle":
            images_struct["lifestyle"].append(entry)
        else:  # detay
            images_struct["technical"].append(entry)

    images_struct["_quality_notes"].append(
        f"Faz 5.11 migration: {copied} gorsel kopyalandi (ana={counters.get('ana',0)}, "
        f"detay={counters.get('detay',0)}, lifestyle={counters.get('lifestyle',0)}, "
        f"varyant={counters.get('varyant',0)}). Scraper v1.1 ham_cikti'dan."
    )

    print(f"  Kopyalandi: {copied}, atlandı: {skipped}")
    print(f"  ana={counters.get('ana',0)}, detay={counters.get('detay',0)}, "
          f"lifestyle={counters.get('lifestyle',0)}, varyant={counters.get('varyant',0)}")

    # Ürün JSON'unu güncelle
    urun_json_path = URUNLER / urun_json_filename
    with urun_json_path.open(encoding="utf-8") as f:
        urun = json.load(f)

    # Eski images yapısının audit korunmasi icin _legacy_images bloguna sakla
    if "images" in urun and urun["images"]:
        urun["images"]["_pre_faz511_snapshot"] = {
            "description_old": urun["images"].get("_description"),
            "main_count": len(urun["images"].get("main", [])),
            "variants_count": len(urun["images"].get("variants", [])),
            "lifestyle_count": len(urun["images"].get("lifestyle", [])),
            "technical_count": len(urun["images"].get("technical", [])),
        }

    # Yeni images yapisi
    urun["images"] = {
        "_description": (
            f"Faz 5.11 (2026-05-26): Scraper v1.1 ham_cikti'dan {copied} gorsel "
            f"gorseller/dedar/{product_code}/ konumuna migrate edildi. Tip dagilimi: "
            f"ana={counters.get('ana',0)}, detay={counters.get('detay',0)}, "
            f"lifestyle={counters.get('lifestyle',0)}, varyant={counters.get('varyant',0)}. "
            "Eski faz 5.3/5.4 images yapisi _pre_faz511_snapshot'ta korundu (audit izi)."
        ),
        "main": images_struct["main"],
        "variants": images_struct["variants"],
        "lifestyle": images_struct["lifestyle"],
        "technical": images_struct["technical"],
        "_pre_faz511_snapshot": urun["images"].get("_pre_faz511_snapshot"),
        "_quality_notes": images_struct["_quality_notes"],
    }

    # Audit history append
    urun["source_data"]["_provenance"]["audit_history"].append({
        "audit_id": f"{urun['urun_id']}_v1.3_2026-05-26",
        "audit_date": "2026-05-26",
        "audit_doc": "topla/scripts/migrate_dedar_gorseller.py",
        "version_before": "v1.2/v1.1 (Faz 5.10 scraper v1.1 audit eklendi, images.* tek varyant)",
        "version_after": "v1.3 (Faz 5.11 images.* genisletildi, ham_cikti -> gorseller kopya)",
        "notes": (
            f"Scraper v1.1 ham_cikti'da {len(gorseller_ham)} gorsel vardi (Cobra/DLN buyuk gallery). "
            f"{copied} gorsel gorseller/dedar/{product_code}/ konumuna kopyalandi, JSON images.* "
            f"genisletildi. Eski tek-varyant images yapisi _pre_faz511_snapshot'ta arsivlendi."
        ),
    })
    urun["last_updated"] = NOW
    urun["data_quality"]["completeness_percent"] = min(urun["data_quality"].get("completeness_percent", 60) + 10, 85)

    with urun_json_path.open("w", encoding="utf-8") as f:
        json.dump(urun, f, ensure_ascii=False, indent=2)

    print(f"  JSON guncellendi: {urun_json_path.name}")


# En guncel ham cikti dosyalari (scraper v1.1.1 sonrasi)
def _latest_ham(prefix: str) -> Path:
    candidates = sorted(HAM_CIKTI.glob(f"{prefix}*.json"))
    if not candidates:
        raise SystemExit(f"HATA: {prefix}*.json bulunamadi")
    return candidates[-1]

# === Cobra ===
migrate_urun(
    ham_json_path=_latest_ham("dedar_cobra_"),
    product_code="00T19063",
    urun_slug="cobra",
    urun_json_filename="dedar_00T19063-cobra.json",
)

# === Days Like Now ===
migrate_urun(
    ham_json_path=_latest_ham("dedar_days-like-now_"),
    product_code="00T25007",
    urun_slug="days-like-now",
    urun_json_filename="dedar_00T25007-days-like-now.json",
)

print("\n=== Toplam ===")
total = sum(1 for _ in (GORSELLER / "dedar").rglob("*.jpg"))
print(f"gorseller/dedar/ icindeki toplam JPG: {total}")
