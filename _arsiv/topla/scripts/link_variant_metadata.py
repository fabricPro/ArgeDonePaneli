"""Faz 6.10: Variant metadata (renk adi + gorsel) JSON'lara aktar — v2.

Dedar scraper v1.2 gorseller listesinde 2 tip 'varyant' var:
1. Main page swatch'leri (tip='varyant', varyant_adi=None, KUCUK 1-5 KB)
   — Color picker'dan gelir, low-res, dashboard'da gosterilmemeli.
2. Variant page main image'lari (tip='varyant', varyant_adi='bianco' gibi,
   YUKSEK CHOZ 100-500 KB) — Bu kullanicinin gormek istedigi gercek renkler.

Algoritma:
- variants_raw'dan name -> suffix mapping olustur
- Disk'teki varyant_NN.jpg dosyalarini ham_cikti gorseller sirasiyla eslestir
- Sadece varyant_adi (color name) olan'lari images.variants[]'e ekle
  (swatch'leri JSON'a koyma — dashboard kalabalik olmasin)
- variants[].main_image_local_path = matched named variant image
- Default variant (variant page loop'ta islenmeyen ilk renk):
  source_data.variants[0]'a ana image atanir (urunun MOODBOARD'dan gelen big shot)

HAFIZA NOTU (gelecek oturum):
- Bu link script'i HER yeni Dedar urun scrape'inden sonra calistirilmali
- Cobra/DLN/Wide-Linen/Twillman ayni pattern: 9 swatch + N named variant images
- Ham_cikti varyant_adi=None olanlar SWATCH (atla), name'li olanlar gercek renk
"""
import json
import sys
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

URUNLER = PROJECT_ROOT / "markalar" / "urunler"
HAM = PROJECT_ROOT / "topla" / "ham_cikti"
GORSELLER = PROJECT_ROOT / "gorseller" / "dedar"
NOW = "2026-05-26T10:45:00Z"

PRODUCTS = [
    ("00T22044", "wide-linen-baobab"),
    ("00T21015", "wide-linen-atelier-1930"),
    ("00T19031", "wide-linen-signor-darcy"),
    ("00T23046", "twillman"),
    ("00T19063", "cobra"),
    ("00T25007", "days-like-now"),
]


def latest_ham(prefix: str) -> Path | None:
    candidates = sorted(HAM.glob(f"{prefix}*.json"))
    return candidates[-1] if candidates else None


def link_one(code: str, slug: str):
    json_path = URUNLER / f"dedar_{code}-{slug}.json"
    if not json_path.exists():
        print(f"  ATLA: {json_path.name} yok")
        return

    ham_path = latest_ham(f"dedar_{slug}_")
    if not ham_path:
        print(f"  ATLA: ham_cikti dedar_{slug}_*.json yok")
        return

    print(f"\n=== {code} / {slug} ===")
    print(f"  Ham: {ham_path.name}")

    ham = json.loads(ham_path.read_text(encoding="utf-8"))
    sd_ham = ham["source_data"]
    gorseller_ham = ham.get("gorseller") or []

    # 1) variants_raw'dan name -> suffix mapping
    variants_raw = sd_ham.get("variants_raw") or []
    name_to_suffix: dict[str, str] = {}
    suffix_meta: dict[str, dict] = {}
    for v in variants_raw:
        cs = v.get("color_suffix")
        nm = v.get("name")
        if cs:
            suffix_meta[cs] = {
                "name": nm,
                "sku": v.get("sku"),
                "main_image_url": v.get("main_image_url"),
            }
            if nm:
                name_to_suffix[nm] = cs

    print(f"  variants_raw: {len(variants_raw)} (named: {len(name_to_suffix)})")

    # 2) Disk dosyalari (varyant_NN.jpg + ana_01.jpg)
    dst_dir = GORSELLER / code
    disk_varyant = sorted(dst_dir.glob("varyant_*.jpg"))
    disk_ana = sorted(dst_dir.glob("ana_*.jpg"))
    print(f"  disk: varyant={len(disk_varyant)}, ana={len(disk_ana)}")

    # 3) ham_cikti varyant sirasinda her dosyaya varyant_adi ata
    # Dosya naming: varyant_NN.jpg <=> ham_cikti varyant_imgs[NN-1]
    varyant_imgs_ham = [g for g in gorseller_ham if g.get("tip") == "varyant"]
    swatch_count = 0
    named_count = 0
    new_image_variants = []
    for fpath in disk_varyant:
        # Filename: varyant_NN.jpg -> idx
        try:
            idx = int(fpath.stem.split("_")[1])
        except (IndexError, ValueError):
            continue
        if idx - 1 >= len(varyant_imgs_ham):
            continue
        ham_entry = varyant_imgs_ham[idx - 1]
        varyant_adi = ham_entry.get("varyant_adi")
        if not varyant_adi:
            # Swatch — atla, JSON'a koyma
            swatch_count += 1
            continue
        suffix = name_to_suffix.get(varyant_adi)
        if not suffix:
            # Bilinmeyen renk adi
            continue
        full_variant_code = f"{code}-{suffix}"
        meta = suffix_meta.get(suffix, {})
        new_image_variants.append({
            "variant_code": full_variant_code,
            "color_code": suffix,
            "color_name": varyant_adi,
            "url": ham_entry.get("kaynak_url") or meta.get("main_image_url"),
            "local_path": f"gorseller/dedar/{code}/{fpath.name}",
            "alt": f"{slug} - {varyant_adi}",
        })
        named_count += 1

    print(f"  matched named: {named_count}, swatch atlandi: {swatch_count}")

    # 4) JSON load + variants[] color_name guncelle
    d = json.loads(json_path.read_text(encoding="utf-8"))

    variants = d["source_data"]["variants"]
    name_updates = 0
    for v in variants:
        suffix = v["color_code"].split("-")[-1]
        if suffix in suffix_meta and suffix_meta[suffix]["name"]:
            v["color_name"] = suffix_meta[suffix]["name"]
            name_updates += 1
        # main_image_url_source
        if suffix in suffix_meta and suffix_meta[suffix]["main_image_url"]:
            v["main_image_url_source"] = suffix_meta[suffix]["main_image_url"]
    print(f"  variants[].color_name guncellendi: {name_updates}")

    # 5) Variants[].main_image_local_path eslestir
    suffix_to_local = {iv["color_code"]: iv["local_path"] for iv in new_image_variants}
    img_link_count = 0
    for v in variants:
        suffix = v["color_code"].split("-")[-1]
        if suffix in suffix_to_local:
            v["main_image_local_path"] = suffix_to_local[suffix]
            img_link_count += 1
        else:
            # Variant page loop'ta islenmeyen (default) variant — ana image kullan
            if disk_ana and len(disk_ana) >= 1:
                v["main_image_local_path"] = f"gorseller/dedar/{code}/{disk_ana[0].name}"
    print(f"  variants[].main_image_local_path linked: {img_link_count} (default ana fallback)")

    # 6) images.variants[] yeni hali
    d["images"]["variants"] = new_image_variants

    # 7) images.main: ana_01.jpg
    if disk_ana:
        d["images"]["main"] = [{
            "url": None,
            "local_path": f"gorseller/dedar/{code}/{disk_ana[0].name}",
            "alt": f"{slug} - main (default variant: {variants_raw[0].get('color_suffix') if variants_raw else '?'} {variants_raw[0].get('name') if variants_raw else '?'})",
        }]

    # 8) Audit history
    d["last_updated"] = NOW
    d["source_data"]["_provenance"]["audit_history"].append({
        "audit_id": f"{d['urun_id']}_v1.3_2026-05-26_color_link",
        "audit_date": "2026-05-26",
        "version_before": "v1.2: variants[].color_name=null, swatch+named karisik",
        "version_after": (
            f"v1.3: {name_updates} renk adi (Italyan/Fransiz) eslestirildi, "
            f"{named_count} variant gorseli renge link'lendi, "
            f"{swatch_count} main-page swatch atlandi (low-res)."
        ),
        "notes": (
            "Faz 6.10 (kullanici talep 2026-05-26): Dashboard variant cards renk basina "
            "high-res gorsel + renk adi. Swatch'ler (varyant_adi=None) JSON'a girmedi."
        ),
    })

    # 9) Yaz
    json_path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  JSON guncellendi: {json_path.name}")


def main():
    for code, slug in PRODUCTS:
        try:
            link_one(code, slug)
        except Exception as e:
            print(f"  HATA {code}/{slug}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
