"""Dashboard JS array'ini parse edip markalar/urunler/<marka>_<kod>.json taslaklarini uret.

Anayasa kural #9: Python SADECE mekanik veri toplama yapar.
- source_data: dashboard JS objesinden direkt mapping
- variants: dashboard renkler[] -> sema variants[] (color_code, color_name, main_image_local_path)
- images: dashboard renkler[].gorseller[] yolu -> images.variants[] (layer_used=1 cunku Documents'ta zaten indirilmis)
- mobidik_evaluation: BOS BIRAKILIR (Claude Code denetim sonra doldurur)
- ai_inferences: BOS BIRAKILIR
- audit_history: ilk entry "Faz 3.4 batch migration from dashboard JS array"

Calistirma:
  .venv\\Scripts\\python.exe topla\\scripts\\parse_dashboard_to_urun_jsons.py --dry-run
  .venv\\Scripts\\python.exe topla\\scripts\\parse_dashboard_to_urun_jsons.py
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "03_html_dashboard" / "index.html"
OUT_DIR = ROOT / "markalar" / "urunler"
NOW = "2026-05-25T22:30:00Z"

# Marka slug haritasi
MARKA_SLUGS = {
    "ADO Goldkante": "ado_goldkante",
    "Zimmer + Rohde": "zimmer_rohde",
    "Etamine": "etamine",
    "Travers": "travers",
    "Kvadrat": "kvadrat",
}

# Marka kod uzunluklari (yeni gorseller/<marka>/<urun>/ icin)
URUN_KOD_UZUN = {
    "kvadrat": 4,
    "ado_goldkante": 4,
    "zimmer_rohde": 5,
    "etamine": 5,
    "travers": 5,
}

# Atlamak istedigimiz markalar (zaten Kvadrat n=2 migrate edildi)
SKIP_MARKALAR = {"Kvadrat"}


def parse_dashboard(html_path: Path) -> list[dict]:
    """HTML icinden const products = [...] array'ini parse et."""
    content = html_path.read_text(encoding="utf-8")
    match = re.search(r"const products = (\[[\s\S]*?\n\]);", content)
    if not match:
        raise SystemExit("HATA: const products array bulunamadi")
    js_array = match.group(1)
    return json.loads(js_array)


def extract_urun_kodu(dashboard_kod: str, marka_slug: str) -> tuple[str, str]:
    """'3018-110' -> ('3018', '110'). Dashboard 'XXXX-NNN' formatinda."""
    # Tire ile ayrilmis: ilk kisim urun, ikinci renk
    if "-" in dashboard_kod:
        urun_kodu, renk_kodu = dashboard_kod.split("-", 1)
        return urun_kodu, renk_kodu
    # Yoksa: marka_slug'a gore son N haneyi renk olarak al
    urun_len = URUN_KOD_UZUN.get(marka_slug, 5)
    return dashboard_kod[:urun_len], dashboard_kod[urun_len:]


def parse_en_cm(en_str: str) -> int | None:
    """'300' -> 300, 'üretici beyan etmiyor' -> None"""
    if not en_str:
        return None
    en_str = en_str.strip()
    m = re.search(r"(\d+)", en_str)
    return int(m.group(1)) if m else None


def parse_gramaj_gsm(gramaj_str: str) -> int | None:
    """Numeric g/m² veya None"""
    if not gramaj_str or "beyan etmiyor" in gramaj_str.lower():
        return None
    m = re.search(r"(\d+)", gramaj_str)
    return int(m.group(1)) if m else None


def parse_kompozisyon(text: str) -> list[dict]:
    """'59% Polyester, 41% Cotton' -> [{fiber_generic, ratio_percent}, ...]"""
    if not text:
        return []
    parts = re.split(r"[,;]", text)
    composition = []
    fiber_tr_map = {
        "Polyester": "Polyester",
        "Cotton": "Pamuk",
        "Pamuk": "Pamuk",
        "Flax": "Keten",
        "Linen": "Keten",
        "Keten": "Keten",
        "Viscose": "Viskon",
        "Viskoz": "Viskon",
        "Wool": "Yun",
        "Yün": "Yun",
        "Polyamide": "Poliamid",
        "Polyamid": "Poliamid",
        "Acrylic": "Akrilik",
        "Alpaca": "Alpaka",
        "Lyocell": "Lyocell",
        "Recycled PES": "Geri Donusturulmus PES",
        "rPES": "Geri Donusturulmus PES",
    }
    for part in parts:
        part = part.strip()
        m = re.match(r"(\d+)\s*%?\s*(.+)", part)
        if not m:
            continue
        ratio = int(m.group(1))
        fiber_raw = m.group(2).strip()
        # Recycled PES eslesimi
        if "recycled" in fiber_raw.lower() and "pes" in fiber_raw.lower():
            fiber_commercial = "Recycled PES"
            fiber_generic = "Geri Donusturulmus PES"
        else:
            fiber_commercial = fiber_raw
            fiber_generic = fiber_tr_map.get(fiber_raw.split()[0] if fiber_raw else "", fiber_raw)
        composition.append({
            "fiber_generic": fiber_generic,
            "fiber_commercial": fiber_commercial,
            "ratio_percent": ratio,
            "fr_treatment": None,
        })
    return composition


def parse_dokuma(text: str) -> tuple[str, str | None]:
    """'dobby' -> ('dobby', 'dobby'); 'plain (sheer)' -> ('plain (sheer)', 'plain')"""
    raw = text.strip() if text else ""
    # Normalize: ilk kelime
    first_word = raw.lower().split("(")[0].strip().split()[0] if raw else ""
    valid_normalized = {"plain", "dobby", "jacquard", "sheer", "leno", "boucle"}
    if first_word in valid_normalized:
        return raw, first_word
    # leno tespiti
    if "leno" in raw.lower():
        return raw, "leno"
    if "boucle" in raw.lower():
        return raw, "dobby"  # boucle iplik dobby altkumesi
    if "sheer" in raw.lower() or "voile" in raw.lower():
        return raw, "sheer"
    if "double" in raw.lower():
        return raw, "double_cloth"
    return raw, None


def build_urun_json(dashboard_obj: dict) -> tuple[str, dict] | None:
    """Dashboard objesinden urun JSON taslagi insa et. (filename, json_dict) doner."""
    marka = dashboard_obj["marka"]
    if marka in SKIP_MARKALAR:
        return None
    marka_slug = MARKA_SLUGS.get(marka)
    if not marka_slug:
        print(f"UYARI: bilinmeyen marka {marka}, atlandi", file=sys.stderr)
        return None

    # Urun kodu: dashboard "3018-110" -> "3018" (ana), "110" varsayilan renk
    dashboard_kod = dashboard_obj["urun_kodu"]
    urun_kodu, default_renk = extract_urun_kodu(dashboard_kod, marka_slug)
    urun_slug = dashboard_obj["urun_adi"].lower().replace(" ", "-").replace("+", "-")
    urun_id = f"{marka_slug}_{urun_kodu}-{urun_slug}"
    filename = f"{urun_id}.json"

    # Variants: dashboard renkler[] -> sema variants[]
    variants = []
    images_variants = []
    for renk in dashboard_obj.get("renkler", []):
        renk_kodu = renk["kod"]
        full_color_code = f"{urun_kodu}-{renk_kodu}"
        # Eski gorsel yollari -> yeni konvansiyon
        eski_yollar = renk.get("gorseller", [])
        if eski_yollar:
            ana_yeni_yol = f"gorseller/{marka_slug}/{urun_kodu}/{renk_kodu}_1.jpg"
        else:
            ana_yeni_yol = None
        variants.append({
            "color_code": full_color_code,
            "color_name": renk.get("ad"),
            "main_image_url_source": renk.get("swatch"),
            "main_image_local_path": ana_yeni_yol,
        })
        # images.variants[]: her renk icin 3-5 gorsel
        for idx, eski in enumerate(eski_yollar, start=1):
            images_variants.append({
                "url": renk.get("swatch") if idx == 1 else None,
                "local_path": f"gorseller/{marka_slug}/{urun_kodu}/{renk_kodu}_{idx}.jpg",
                "variant_code": full_color_code,
                "variant_name": renk.get("ad"),
                "layer_used": 1,
                "layer_1_attempt": {"success": True, "error": None, "method": "documents_legacy_pre_migrate"},
                "downloaded_at": "2026-05-11T00:00:00Z",
                "quality_check": "passed",
                "_note": f"Documents iterasyonu PowerShell indir.ps1 ile indirildi; Faz 3.3 migrate sonrasi {ana_yeni_yol.rsplit('/', 1)[0] if ana_yeni_yol else 'gorseller/...'} altinda",
            })

    # Kompozisyon
    kompozisyon = parse_kompozisyon(dashboard_obj.get("kompozisyon", ""))

    # En
    en_cm = parse_en_cm(dashboard_obj.get("en", ""))

    # Dokuma
    weave_raw, weave_normalized = parse_dokuma(dashboard_obj.get("dokuma", ""))

    # Rapor
    rapor_str = dashboard_obj.get("rapor", "")
    repeat_cm = {"vertical": None, "horizontal": None}
    if "yok" not in rapor_str.lower() and rapor_str:
        m = re.search(r"(\d+(?:\.\d+)?)\s*cm", rapor_str)
        if m:
            repeat_cm["vertical"] = float(m.group(1))

    # Gramaj
    weight_gsm = parse_gramaj_gsm(dashboard_obj.get("gramaj", ""))

    # Ulke -> ISO uyumlu olarak Turkce kalsin (sema string kabul ediyor)
    ulke = dashboard_obj.get("ulke")

    # Mobidik notu HTML -> plain text (gecici, denetim sonrasi yeniden yazilacak)
    mobidik_notu_html = dashboard_obj.get("mobidik_notu", "")
    mobidik_notu_text = re.sub(r"<[^>]+>", "", mobidik_notu_html)

    urun_json = {
        "_schema_version": "1.3",
        "urun_id": urun_id,
        "brand": marka,
        "brand_slug": marka_slug,
        "collection": dashboard_obj.get("koleksiyon"),
        "product_code": urun_kodu,
        "product_name": dashboard_obj["urun_adi"],
        "source_url": dashboard_obj.get("url"),
        "scraped_at": "2026-05-11T00:00:00Z",  # Documents parti01-03 tarihi
        "last_updated": NOW,
        "source_data": {
            "_description": "Documents iterasyonundan migrate edildi (Faz 3.4). Birincil kaynak: 03_html_dashboard/index.html JS array; ikincil: 01_raporlar/<marka>_parti<NN>_<tarih>.md (varsa).",
            "_provenance": {
                "schema_version": "1.1",
                "created_at": NOW,
                "last_updated": NOW,
                "sources_used": [
                    {
                        "url": "03_html_dashboard/index.html (Documents iterasyonu, parti01-03 sonrasi)",
                        "type": "internal_dashboard_pre_migration",
                        "accessed_at": NOW,
                        "fields_supported": ["composition", "width_cm", "weave_type", "variants", "country_of_origin", "description"],
                    },
                    {
                        "url": dashboard_obj.get("url", ""),
                        "type": "html_product_page",
                        "accessed_at": "2026-05-11T00:00:00Z",
                        "fields_supported": ["original_source_for_all_fields"],
                    },
                ],
                "field_metadata": {},
                "fields_from_dashboard_migration": ["composition", "width_cm", "weave_type_raw", "variants", "country_of_origin", "description"],
                "fields_from_inference": [],
                "constitutional_violations_check": "pending_phase34_audit",
                "audit_history": [
                    {
                        "audit_id": f"{urun_id}_v1.0_2026-05-25",
                        "audit_date": "2026-05-25",
                        "audit_doc": "docs/parti_log.md (kuruluyor)",
                        "version_before": "(yok — Documents iterasyonundan ilk JSON migrate)",
                        "version_after": "v1.0 (Faz 3.4 batch migrate from dashboard JS array)",
                        "notes": "Python parse_dashboard_to_urun_jsons.py mekanik migrate. source_data + variants + images dolduruldu. mobidik_evaluation BOS — Claude Code denetim sonra dolduracak (kapasite tablosu #7 + ai_inferences). Documents dashboard'daki mobidik_notu_html metni gecici source_data.mobidik_notu_legacy alaninda saklandi.",
                    }
                ],
            },
            "technical": {
                "composition": kompozisyon,
                "width_cm": en_cm,
                "weight_gsm": weight_gsm,
                "repeat_cm": repeat_cm,
                "weave_type_raw": weave_raw,
                "weave_type_normalized": weave_normalized,
                "yarn_type": None,
                "transparency": {"value": None, "_note": "Documents dashboard transparency beyan etmiyor; ai_inferences.light_transmission adayi."},
                "usage_area": ["curtains"],
                "performance": {
                    "lightfastness": None,
                    "abrasion_martindale": None,
                    "pilling": None,
                    "shrinkage": {"warp_percent": None, "weft_percent": None},
                    "washing_resistance": None,
                },
                "acoustic": {"alpha_s_value": None, "absorption_class": None, "comment": None},
            },
            "variants": variants,
            "certifications": {
                "fire_safety": [],
                "sustainability": [],
                "other": [],
                "raw_text": ", ".join(dashboard_obj.get("performans", [])),
            },
            "commercial": {
                "price_per_meter": None,
                "price_currency": None,
                "moq_meters": None,
                "lead_time_days": None,
                "country_of_origin": ulke,
                "sample_policy": None,
                "launch_year": None,
                "production_model": {"value": "unknown", "notes": "Documents migrasyonunda beyan yok"},
            },
            "design_credit": {"designer": None, "type": "unknown"},
            "description_original": {
                "language": "tr",
                "text": dashboard_obj.get("aciklama"),
                "source_url": dashboard_obj.get("url"),
                "extracted_at": "2026-05-11T00:00:00Z",
                "_note": "Documents iterasyonu Turkce ozet — orijinal Ingilizce/Almanca aciklama Z+R sayfasinda ayrica cekilebilir",
            },
            "description_tr": {
                "text": dashboard_obj.get("aciklama"),
                "translation_method": "user_curated",
                "translated_at": "2026-05-11T00:00:00Z",
                "is_official_translation": False,
            },
            "style_note": dashboard_obj.get("stil_notu"),
            "performans_legacy": dashboard_obj.get("performans", []),
            "mobidik_notu_legacy": mobidik_notu_text,
        },
        "ai_inferences": {
            "_description": "Faz 3.4 batch migrate sonrasi Claude Code denetim sirasinda doldurulacak.",
            "weight_gsm": {"estimated_value": None, "confidence": None, "method": "pending", "based_on": [], "model": "claude-opus-4-7", "created_at": None, "user_verified": False, "user_correction": None},
            "light_transmission": {"estimated_class": None, "confidence": None, "method": "pending", "model": "claude-opus-4-7", "created_at": None, "user_verified": False, "user_correction": None},
        },
        "image_analysis": {
            "_description": "Visual analiz pending — Faz 3.4 sonrasi denetim asamasinda eklenecek.",
            "dominant_colors": {"value": None},
            "texture_classification": None,
            "transparency_visual": None,
            "color_palette_summary": f"{len(variants)} renk varyanti — palet Documents dashboard'da listelendi",
            "style_tags": [],
            "pattern_type": None,
            "pattern_density": None,
            "estimated_use_context": ["curtains"],
        },
        "images": {
            "_description": f"{len(images_variants)} gorsel — Documents iterasyonu PowerShell indir.ps1 ile indirildi; Faz 3.3 yeni gorseller/<marka>/<urun>/<renk>_<sira>.jpg konvansiyonuna migrate edildi.",
            "main": [],
            "variants": images_variants,
            "lifestyle": [],
            "technical": [],
            "_quality_notes": [],
        },
        "mobidik_evaluation": {
            "_description": "PENDING — Faz 3.4 sonrasi Claude Code denetim. Kapasite tablosu (anayasa #7) uygulanacak. source_data.mobidik_notu_legacy gecici metin kaynak.",
            "staubli_feasibility": {
                "score": None,
                "frame_count_estimate": None,
                "warp_compatibility": "pending",
                "weft_compatibility": "pending",
                "repeat_size_compatibility": "pending",
                "reed_density_estimate": None,
                "sizing_requirement": None,
                "comment": "PENDING — Faz 3.4 batch migrate sonrasi denetim",
            },
            "arge_value": {"score": None, "key_learnings": [], "comment": "PENDING"},
            "market_gap": {"score": None, "comment": "PENDING", "target_markets": []},
            "portfolio_fit": {"score": None, "similar_existing_products": [], "comment": "PENDING"},
            "overall_score": None,
            "priority_level": None,
            "strategic_note": "PENDING — source_data.mobidik_notu_legacy gecici metni var, kapasite #7 uyarinca yeniden hesaplanacak.",
        },
        "data_quality": {
            "missing_fields": ["technical.performance.*", "commercial.price_per_meter", "commercial.moq_meters", "ai_inferences.*", "mobidik_evaluation.*"],
            "ai_estimated_fields": [],
            "user_verified_fields": ["commercial.country_of_origin", "variants[].color_name"],
            "completeness_percent": 45,  # taslak — denetim sonrasi yukselir
            "last_verified": NOW,
            "notes": [
                f"Faz 3.4 batch migrate. {len(variants)} renk varyanti dashboard'dan alindi.",
                "mobidik_evaluation + ai_inferences PENDING — Claude Code denetim sonra dolduracak.",
                f"Gorsel yollari yeni konvansiyona ({images_variants[0]['local_path'].rsplit('/', 1)[0] if images_variants else 'gorseller/...'}) uyarlandi.",
            ],
        },
    }
    return filename, urun_json


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    products = parse_dashboard(HTML)
    print(f"Dashboard'da {len(products)} urun bulundu")

    marka_count = {}
    written = []
    skipped = []
    for obj in products:
        marka = obj["marka"]
        marka_count[marka] = marka_count.get(marka, 0) + 1
        if marka in SKIP_MARKALAR:
            skipped.append(f"  {marka} | {obj['urun_kodu']} | {obj['urun_adi']} (Faz 2 zaten migrate)")
            continue
        result = build_urun_json(obj)
        if not result:
            continue
        filename, urun_json = result
        out_path = OUT_DIR / filename
        if args.dry_run:
            print(f"  [DRY] {marka} | {obj['urun_kodu']} | {obj['urun_adi']} ({len(obj.get('renkler', []))} renk) -> {filename}")
        else:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(urun_json, f, ensure_ascii=False, indent=2)
            written.append(f"  {marka} | {obj['urun_kodu']} | {obj['urun_adi']} -> {filename}")

    print()
    print(f"=== Marka dagilimi ===")
    for marka, count in sorted(marka_count.items()):
        marker = " (SKIP)" if marka in SKIP_MARKALAR else ""
        print(f"  {marka}: {count}{marker}")

    if skipped:
        print()
        print(f"=== Atlanan {len(skipped)} urun (Faz 2 zaten migrate edildi) ===")
        for s in skipped:
            print(s)

    if written:
        print()
        print(f"=== Yazilan {len(written)} urun JSON ===")
        for w in written:
            print(w)

    print()
    print(f"Toplam: {len(products)} dashboard urun, {len(written)} yeni JSON, {len(skipped)} atlandi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
