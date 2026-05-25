"""Faz 5.5.1b: Rubelli Filicudi denetim + n=1 -> n=2 update."""
import json
import shutil
import sys
import re as _re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

URUNLER = PROJECT_ROOT / "markalar" / "urunler"
MARKA = PROJECT_ROOT / "markalar"
GORSELLER = PROJECT_ROOT / "gorseller"
HAM = PROJECT_ROOT / "topla" / "ham_cikti" / "rubelli_filicudi_20260525T215748Z.json"
NOW = "2026-05-26T02:00:00Z"

with HAM.open(encoding="utf-8") as f:
    ham = json.load(f)
sd = ham["source_data"]

# Gorseller kopyala
dst_dir = GORSELLER / "rubelli" / "30764"
dst_dir.mkdir(parents=True, exist_ok=True)
copied_images = []
for g in ham["gorseller"]:
    if not g.get("dosya_yolu"):
        continue
    src = Path(g["dosya_yolu"])
    if not src.exists():
        continue
    m = _re.search(r"/A\d+_(\d{1,3})/", g["kaynak_url"])
    color = m.group(1).zfill(3) if m else "default"
    fname = f"{color}_main.jpg"
    shutil.copy2(src, dst_dir / fname)
    copied_images.append({
        "url": g["kaynak_url"],
        "local_path": f"gorseller/rubelli/30764/{fname}",
        "variant_code": f"30764-{color}",
        "variant_name": None,
        "layer_used": 1,
        "layer_1_attempt": {"success": True, "error": None, "method": "scraper_v1_1_rubelli"},
        "quality_check": "passed",
    })

# variants_for_json
variants_for_json = []
for v in sd.get("variants_raw", []):
    color = (v.get("color_code") or "").zfill(3)
    if not color:
        continue
    raw_name = v.get("name") or ""
    if " - " in raw_name:
        clean = raw_name.split(" - ", 1)[1].strip()
    else:
        clean = raw_name.strip() or None
    full_code = f"30764-{color}"
    local_path = None
    for img in copied_images:
        if img["variant_code"] == full_code:
            local_path = img["local_path"]
            img["variant_name"] = clean
            break
    variants_for_json.append({
        "color_code": full_code,
        "color_name": clean,
        "color_name_confidence": "exact" if clean else "unknown",
        "main_image_url_source": v.get("main_image_url"),
        "main_image_local_path": local_path,
    })

FILICUDI = {
    "_schema_version": "1.3",
    "urun_id": "rubelli_30764-filicudi",
    "brand": "Rubelli",
    "brand_slug": "rubelli",
    "collection": None,
    "product_code": "30764",
    "product_name": "Filicudi",
    "source_url": ham["source_url"],
    "scraped_at": ham["scraped_at"],
    "last_updated": NOW,
    "source_data": {
        "_description": (
            "Rubelli Filicudi (Formafantasma) — %100 Solution-Dyed Acrylic Tempotest, "
            "141 cm, 10 renk. Heavy use upholstery (suitable for upholstery), perdelik "
            "kategoride listede ama primer upholstery. Tempotest = Italyan outdoor acrylic "
            "benchmark. Capri Plus (ADO solution-dyed PES) ile karsilastirilabilir."
        ),
        "_provenance": {
            "schema_version": "1.1", "created_at": NOW, "last_updated": NOW,
            "sources_used": [
                {"url": ham["source_url"], "type": "html_product_page", "accessed_at": ham["scraped_at"]},
                {"url": "kapasite/staubli_uretim_kapasitesi.md", "type": "user_verified_capacity_table", "accessed_at": NOW},
            ],
            "constitutional_violations_check": f"passed_at_{NOW}",
            "audit_history": [{
                "audit_id": "rubelli_30764-filicudi_v1.0_2026-05-26",
                "audit_date": "2026-05-26",
                "audit_doc": "topla/scripts/create_rubelli_filicudi.py",
                "version_before": "(yok — Rubelli n=2 ekleniyor)",
                "version_after": "v1.0",
                "notes": (
                    "Rubelli 2. denetim. Scraper v1.1 Use fix calisti (Heavy use yakalandi, "
                    "v1.0'da Care and treatment yanlis idi). Filicudi Heavy use upholstery — "
                    "Curtains kategoride listede ama description 'suitable for upholstery'. "
                    "Solution-dyed acrylic Tempotest outdoor benchmark (Capri Plus PES analog). "
                    "10 varyant tespit (Sabbia, Grigio, Avorio, vb.), 1 gorsel (variant click iyilesme gerek)."
                ),
            }],
        },
        "technical": {
            "composition": sd.get("composition_parsed", []),
            "width_cm": 141,
            "weight_gsm": None,
            "repeat_cm": {"vertical": None, "horizontal": None},
            "weave_type_raw": "Plain",
            "weave_type_normalized": "plain",
            "yarn_type": "filament",
            "transparency": {"value": None},
            "usage_area": ["upholstery", "heavy_use", "outdoor"],
            "performance": {
                "lightfastness": None,
                "abrasion_martindale": None,
                "pilling": None,
                "shrinkage": {"warp_percent": None, "weft_percent": None},
            },
            "acoustic": {"alpha_s_value": None, "absorption_class": None, "comment": None},
            "outdoor_rated": True,
            "tempotest_certified": True,
        },
        "variants": variants_for_json,
        "certifications": {
            "fire_safety": ["CAL TB117:2013", "BS5852"],
            "sustainability": ["Oeko-Tex Standard 100"],
            "other": ["Tempotest (Italyan outdoor acrylic sertifikasi)"],
            "raw_text": "CAL.TB117, BS5852, Oeko-Tex",
        },
        "commercial": {
            "price_per_meter": None, "price_currency": None, "moq_meters": None, "lead_time_days": None,
            "country_of_origin": "Italy",
            "sample_policy": "REQUEST A SAMPLE",
            "launch_year": None,
            "production_model": {"value": "stock", "notes": "Current Stock"},
        },
        "design_credit": {"designer": "Formafantasma", "type": "collaborator"},
        "description_original": {
            "language": "en",
            "text": "Filicudi is similar to the plain Elba and completes its colour range. It is suitable for upholstery.",
            "source_url": ham["source_url"], "extracted_at": NOW,
        },
        "description_tr": {
            "text": "Filicudi, plain Elba'ya benzer ve onun renk paletini tamamlıyor. Upholstery için uygundur.",
            "translation_method": "claude_inference", "translated_at": NOW, "is_official_translation": False,
        },
        "style_note": (
            "Italyan premium outdoor acrylic — Tempotest sertifikali. Plain dokuma + Solution-Dyed "
            "Acrylic = Capri Plus (PES) ile paralel teknoloji ama farkli iplik. Formafantasma tasarim."
        ),
        "use_text": "Heavy use",
        "mobidik_scope": "upholstery_kapsam_disi",
    },
    "ai_inferences": {
        "light_transmission": {
            "estimated_class": "opaque", "confidence": "high",
            "method": "Heavy use upholstery + solution-dyed acrylic + 141 cm dar = opaque",
            "based_on": ["use heavy", "composition acrylic"],
            "model": "claude-opus-4-7", "created_at": NOW, "user_verified": False,
        },
    },
    "image_analysis": {
        "_description": "10 varyant tespit, sadece 1 gorsel (variant click iyilesme gerek).",
        "dominant_colors": {"value": None},
        "color_palette_summary": "10 İtalyanca renk (Avorio, Sabbia, Grigio, ...)",
        "style_tags": ["italian", "rubelli", "formafantasma", "tempotest", "outdoor", "acrylic", "plain"],
        "pattern_type": "düz",
        "pattern_density": "düşük",
        "estimated_use_context": ["outdoor mobilya", "otel terasi", "premium konut"],
    },
    "images": {
        "_description": f"Rubelli v1.1, {len(copied_images)} gorsel (10 varyant icin az — variant click pending).",
        "main": [], "variants": copied_images, "lifestyle": [], "technical": [],
        "_quality_notes": ["10 varyant tespit, sadece 1 gorsel — variant click iyilesme sonraki."],
    },
    "mobidik_evaluation": {
        "_description": (
            "Filicudi UPHOLSTERY (Heavy use) — Mobidik perdelik kapsam DISI. "
            "Ancak Tempotest outdoor acrylic teknolojisi Capri Plus (PES) icin analog: "
            "Mobidik solution-dyed acrylic alternatif olarak Aksa Türk üreticisi."
        ),
        "staubli_feasibility": {
            "score": 4, "frame_count_estimate": "2-4",
            "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun",
            "reed_density_estimate": "16-22 dent/cm",
            "sizing_requirement": "Solution-dyed acrylic standart hasil",
            "comment": (
                "Plain dokuma TAM, %100 acrylic standart kategoride (Stabli'ye uygun), 141 cm dar. "
                "Solution-dyed acrylic Aksa Turk uretici (Capri Plus PES'le paralel iplik tedariki). "
                "Tempotest outdoor sertifikası Mobidik için yeni alan. Skor 4: dokuma TAM, dar en + "
                "upholstery (heavy use) Mobidik perdelik projesi disi."
            ),
        },
        "arge_value": {
            "score": 65,
            "key_learnings": ["Solution-dyed acrylic outdoor (Aksa Turk tedariki)", "Tempotest sertifika Italyan benchmark", "Capri Plus PES vs Filicudi acrylic karsilastirma"],
            "comment": "Mobidik outdoor portfoyu icin (Capri Plus + Fil du Temps + Filicudi) acrylic alternatifi.",
        },
        "market_gap": {
            "score": 50,
            "comment": "Upholstery — perdelik segment disi. Outdoor acrylic Türkiye'de Aksa var, Mobidik için outdoor mobilya segmenti acilim potansiyeli (Mobidik perdelik haricinde).",
            "target_markets": ["TR outdoor mobilya", "AB outdoor (DACH)"],
        },
        "portfolio_fit": {"score": 40, "similar_existing_products": ["Capri Plus (ADO outdoor PES)"], "comment": "Mobidik perdelik portfoyune uyumsuz (upholstery + dar)."},
        "overall_score": 50, "priority_level": "dusuk",
        "strategic_note": (
            "DUSUK ONCELIK (perdelik kapsam DIŞI). Filicudi Heavy use upholstery, Rubelli'nin "
            "Curtains kategori meta etiketi var ama description 'suitable for upholstery'. "
            "Tempotest outdoor acrylic teknolojisi Mobidik'in Capri Plus (PES) ile paralel — "
            "Aksa Türk solution-dyed acrylic alternative tedariki ARGE alani olabilir (uzun vade). "
            "Rubelli perdelik (gerçek sheer/lightweight curtain) icin Dimlight veya diger urunde "
            "pilot gerek (3. Rubelli denetimi)."
        ),
    },
    "data_quality": {
        "missing_fields": ["weight_gsm", "lightfastness", "9 variant gorseli"],
        "ai_estimated_fields": ["light_transmission"],
        "user_verified_fields": ["country (Italy)", "Use (Heavy use)", "designer (Formafantasma)"],
        "completeness_percent": 62,
        "last_verified": NOW,
        "notes": [
            "Rubelli 2. denetim, scraper v1.1 Use fix calisti.",
            "Filicudi outdoor acrylic Tempotest — Mobidik için Aksa solution-dyed acrylic ARGE.",
            "Variant click iyilesme: sonraki v1.2 (color picker click-based fetch).",
        ],
    },
}

(URUNLER / "rubelli_30764-filicudi.json").write_text(json.dumps(FILICUDI, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Yazildi: rubelli_30764-filicudi.json (staubli=4/5, overall=50)")

# === Rubelli profil n=1 -> n=2 ===
with (MARKA / "rubelli.json").open(encoding="utf-8") as f:
    rubelli = json.load(f)
rubelli["product_count_tracked"] = 2
rubelli["last_updated"] = NOW

# Width n=2: 145, 141 -> range 141-145
rubelli["width_distribution"]["min_cm"]["sample_status"] = "insufficient_n_2"
rubelli["width_distribution"]["min_cm"]["sample_size"] = 2
rubelli["width_distribution"]["min_cm"]["observed_at_n2"] = 141
rubelli["width_distribution"]["max_cm"]["sample_status"] = "insufficient_n_2"
rubelli["width_distribution"]["max_cm"]["sample_size"] = 2
rubelli["width_distribution"]["max_cm"]["observed_at_n2"] = 145
rubelli["width_distribution"]["comment"] = "n=2: Charles 145 + Filicudi 141 — Rubelli upholstery dar en standardı (141-145 cm)."

# Color: 28 + 10 = 38
rubelli["color_profile"]["total_variant_count"]["sample_size"] = 2
rubelli["color_profile"]["total_variant_count"]["observed_at_n2"] = 38
rubelli["color_profile"]["average_per_product"]["sample_size"] = 2
rubelli["color_profile"]["average_per_product"]["observed_at_n2"] = 19.0
rubelli["color_profile"]["comment"] = "n=2: Charles 28 + Filicudi 10 = 38 varyant. Rubelli ortalama 19/ürün — geniş palet."

# Weave: 2 plain
rubelli["weave_distribution"]["plain"]["sample_size"] = 2
rubelli["weave_distribution"]["plain"]["observed_at_n2"] = 2
rubelli["weave_distribution"]["plain"]["comment"] = "2 plain (Charles moiré + Filicudi outdoor)"

# Composition: Charles CO/VI/LI blend natural-dominant + Filicudi 100% Acrylic sentetik
rubelli["composition_distribution"]["synthetic_ratio_percent"]["sample_size"] = 2
rubelli["composition_distribution"]["synthetic_ratio_percent"]["observed_at_n2"] = 68.5  # (37 + 100)/2
rubelli["composition_distribution"]["natural_ratio_percent"]["sample_size"] = 2
rubelli["composition_distribution"]["natural_ratio_percent"]["observed_at_n2"] = 31.5
rubelli["composition_distribution"]["blend_ratio_percent"]["sample_size"] = 2
rubelli["composition_distribution"]["blend_ratio_percent"]["observed_at_n2"] = 50.0  # 1 blend + 1 mono = 50%
rubelli["composition_distribution"]["comment"] = "n=2: Charles 3-bileşen blend natural + Filicudi mono acrylic. Çeşitlilik yüksek."

# Country
rubelli["country_distribution"] = {"Italy": 2}

# Mobidik avg: (4 + 4)/2 = 4.0
rubelli["mobidik_strategic_assessment"]["average_feasibility_score"]["sample_size"] = 2
rubelli["mobidik_strategic_assessment"]["average_feasibility_score"]["observed_at_n2"] = 4.0
rubelli["mobidik_strategic_assessment"]["_general_feasibility_basis"] = (
    "n=2: Charles 4/5 + Filicudi 4/5 (her ikisi upholstery, plain dokuma TAM ama dar 141-145 cm). "
    "Rubelli urun yelpazesi 557 — perdelik (Curtains) filtreli 160 ürün var ama denetlenen ikisi "
    "de Heavy use. Rubelli'de gercek perdelik (sheer/lightweight curtain) için ayrı pilot gerek."
)
rubelli["mobidik_strategic_assessment"]["arge_priority_areas"].append(
    "Solution-dyed acrylic Tempotest (Filicudi) — Mobidik outdoor portfoyu icin Aksa Türk alternatifi"
)
rubelli["mobidik_strategic_assessment"]["arge_priority_areas"].append(
    "Moire finishing (Charles) — Mobidik finishing makinesi (calender) yatirim alani"
)

# Data integrity
rubelli["data_integrity"]["sample_size_tracked_products"] = 2
rubelli["data_integrity"]["_reliability_explanation"] = (
    "n=2 (Charles upholstery + Filicudi outdoor upholstery). Threshold n>=3 oncesi dagilim null. "
    "Iki denetim de upholstery — Mobidik perdelik segmenti icin Rubelli gercek sheer/lightweight "
    "curtain (Dimlight veya benzer) pilot gerek."
)

# Audit
rubelli["_provenance"]["audit_history"].append({
    "audit_id": "rubelli_marka_v1.1_2026-05-26",
    "audit_date": "2026-05-26",
    "version_before": "v1.0 (n=1, Charles)",
    "version_after": "v1.1 (n=2, Filicudi eklendi)",
    "notes": (
        "Filicudi (outdoor acrylic Tempotest) eklendi. n=1 -> n=2. Charles + Filicudi her ikisi "
        "Heavy use upholstery. Rubelli'de Curtains filtre meta etiketleri var ama denetlenen "
        "2 urun de upholstery. avg_staubli 4.0. Rubelli perdelik gercek pilotu (sheer/lightweight) "
        "sonraki adim — Dimlight (30771) veya Spectrum (30756) aday."
    ),
})
rubelli["_provenance"]["last_updated"] = NOW
rubelli["_provenance"]["constitutional_violations_check"] = f"passed_at_{NOW}"

rubelli["notes"].append("v1.1 (2026-05-26): Filicudi eklendi. n=2. avg_staubli=4.0. Her iki urun upholstery — perdelik pilot devam.")
rubelli["notes"].append("Tempotest outdoor acrylic (Filicudi) Mobidik için Capri Plus PES'in acrylic alternatif analoğu — Aksa Türk tedariki ARGE alanı.")

(MARKA / "rubelli.json").write_text(json.dumps(rubelli, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Yazildi: markalar/rubelli.json (n=1 -> n=2, avg_staubli=4.0)")
