"""Faz 6.8c: Tier 1 gorsellerini ham_cikti/gorseller/dedar/<slug>/ -> gorseller/dedar/<code>/

Eski isim: <slug>_ana_01.jpg, <slug>_varyant_01.jpg, ...
Yeni isim: gorseller/dedar/<product_code>/main_01.jpg, variant_001_1.jpg, variant_002_1.jpg, ...

Anayasa #9: Mekanik (Python). Resimleri varyant numarasi/sirasi ile rename + JSON
images.* genislet.
"""
import json
import shutil
import sys
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HAM_GORSELLER = PROJECT_ROOT / "topla" / "ham_cikti" / "gorseller" / "dedar"
GORSELLER = PROJECT_ROOT / "gorseller" / "dedar"
URUNLER = PROJECT_ROOT / "markalar" / "urunler"
NOW = "2026-05-26T09:30:00Z"

# slug -> (product_code, variant_color_codes_in_order)
PRODUCTS = {
    "wide-linen-baobab": {
        "code": "00T22044",
        "variant_order": ["006", "001", "002", "003", "004", "005", "007", "008"],
    },
    "wide-linen-atelier-1930": {
        "code": "00T21015",
        "variant_order": ["001", "002", "003"],
    },
    "wide-linen-signor-darcy": {
        "code": "00T19031",
        "variant_order": ["009", "001", "002", "003", "004", "005", "006", "007", "008", "010", "011"],
    },
    "twillman": {
        "code": "00T23046",
        "variant_order": ["002", "001", "003"],
    },
}


def migrate_one(slug: str, info: dict) -> dict:
    code = info["code"]
    variant_order = info["variant_order"]
    src_dir = HAM_GORSELLER / slug
    dst_dir = GORSELLER / code
    dst_dir.mkdir(parents=True, exist_ok=True)

    if not src_dir.exists():
        print(f"  HATA: {src_dir} yok")
        return {}

    files = sorted(src_dir.iterdir())
    print(f"  {slug} -> {code}: {len(files)} dosya")

    # main: <slug>_ana_*.jpg -> main_NN.jpg
    # variants: <slug>_varyant_NN.jpg -> variant_<color>_<sira>.jpg
    images_meta = {
        "main": [],
        "technical": [],
        "lifestyle": [],
        "variants": [],
    }

    ana_count = 0
    for f in files:
        name = f.name
        if "_ana_" in name:
            ana_count += 1
            dst_name = f"main_{ana_count:02d}.jpg"
            shutil.copy2(f, dst_dir / dst_name)
            images_meta["main"].append({
                "url": None,  # ham JSON'da yok, ileride alinacak
                "local_path": f"gorseller/dedar/{code}/{dst_name}",
                "alt": f"{slug} - main {ana_count}",
            })
        elif "_varyant_" in name:
            # Sıra numarasını çıkar
            m = name.split("_varyant_")[1].split(".")[0]
            try:
                idx = int(m) - 1
            except ValueError:
                continue
            if idx < len(variant_order):
                color_code = variant_order[idx]
                full_variant_code = f"{code}-{color_code}"
                dst_name = f"variant_{color_code}_1.jpg"
                shutil.copy2(f, dst_dir / dst_name)
                images_meta["variants"].append({
                    "variant_code": full_variant_code,
                    "color_code": color_code,
                    "url": None,
                    "local_path": f"gorseller/dedar/{code}/{dst_name}",
                    "alt": f"{slug} - {color_code}",
                })
        elif "_detay_" in name:
            ana_count += 1
            dst_name = f"technical_{ana_count:02d}.jpg"
            shutil.copy2(f, dst_dir / dst_name)
            images_meta["technical"].append({
                "url": None,
                "local_path": f"gorseller/dedar/{code}/{dst_name}",
                "alt": f"{slug} - technical {ana_count}",
            })

    print(f"    main={len(images_meta['main'])}, variants={len(images_meta['variants'])}, technical={len(images_meta['technical'])}")
    return images_meta


def update_product_json(slug: str, code: str, images_meta: dict):
    """JSON'daki images.* alanini ve variants[].main_image_local_path'i guncelle."""
    json_path = URUNLER / f"dedar_{code}-{slug}.json"
    if not json_path.exists():
        print(f"    HATA: JSON yok: {json_path.name}")
        return

    d = json.loads(json_path.read_text(encoding="utf-8"))

    # images.* guncelle
    d["images"]["main"] = images_meta["main"]
    d["images"]["variants"] = images_meta["variants"]
    d["images"]["technical"] = images_meta["technical"]
    d["images"]["_note"] = "Faz 6.8c migrate edildi (ham_cikti/gorseller -> gorseller/dedar/<code>/)."

    # variants[].main_image_local_path eslestir
    variants = d["source_data"]["variants"]
    for v in variants:
        color = v["color_code"].split("-")[-1]
        # images_meta.variants'tan eslesen var mi?
        for img in images_meta["variants"]:
            if img["color_code"] == color:
                v["main_image_local_path"] = img["local_path"]
                break

    # last_updated + audit_history
    d["last_updated"] = NOW
    d["source_data"]["_provenance"]["audit_history"].append({
        "audit_id": f"{d['urun_id']}_v1.1_2026-05-26_image_migrate",
        "audit_date": "2026-05-26",
        "version_before": "v1.0: images bos, gorseller ham_cikti'da",
        "version_after": (
            f"v1.1: {len(images_meta['main'])} main + {len(images_meta['variants'])} variant + "
            f"{len(images_meta['technical'])} technical gorseli gorseller/dedar/{code}/'a kopyalandi."
        ),
        "notes": "Faz 6.8c gorsel migrasyonu (Python mekanik, Anayasa #9).",
    })

    # missing_fields'tan image_analysis disinda kalanlari kaldir
    mf = d["data_quality"]["missing_fields"]
    mf = [f for f in mf if "image" not in f.lower() or "image_analysis" in f.lower()]
    d["data_quality"]["missing_fields"] = mf

    json_path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"    JSON guncellendi: {json_path.name}")


def main():
    print(f"=== Tier 1 gorsel migrasyon ===\n")
    for slug, info in PRODUCTS.items():
        print(f"\n{slug}")
        images_meta = migrate_one(slug, info)
        if images_meta:
            update_product_json(slug, info["code"], images_meta)

    print(f"\n=== Tamamlandi ===")


if __name__ == "__main__":
    main()
