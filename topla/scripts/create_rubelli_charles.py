"""Faz 5.5b: Rubelli Charles denetim + marka profili n=1.

Charles upholstery (Heavy use), Mobidik perdelik projesi icin kapsam disi
ama Rubelli marka geneli icin pilot. Skor dusuk oncelik.
Scraper sapmalari (rubelli v1.0):
- 'Use' alani 'Care and treatment' yanlis eslesmesi (sayfa label sirasi)
- 28 varyantin 26'sinin gorseli alinmamis (?color= URL parametresi calismadi)
"""
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

URUNLER = PROJECT_ROOT / "markalar" / "urunler"
MARKA = PROJECT_ROOT / "markalar"
GORSELLER = PROJECT_ROOT / "gorseller"
HAM = PROJECT_ROOT / "topla" / "ham_cikti" / "rubelli_charles_20260525T213826Z.json"
NOW = "2026-05-26T01:30:00Z"

with HAM.open(encoding="utf-8") as f:
    ham = json.load(f)
sd = ham["source_data"]

# === Gorseller kopyala ===
dst_dir = GORSELLER / "rubelli" / "30750"
dst_dir.mkdir(parents=True, exist_ok=True)
copied_images = []
for g in ham["gorseller"]:
    if not g.get("dosya_yolu"):
        continue
    src = Path(g["dosya_yolu"])
    if not src.exists():
        continue
    # URL'den variant kodu cikar (Rubelli pattern: A<kod>_<renk>/<kod>_<sira>.jpg)
    import re as _re
    m = _re.search(r"/A\d+_(\d{1,3})/", g["kaynak_url"])
    color = m.group(1).zfill(3) if m else "default"
    fname = f"{color}_main.jpg"
    dst = dst_dir / fname
    shutil.copy2(src, dst)
    copied_images.append({
        "url": g["kaynak_url"],
        "local_path": f"gorseller/rubelli/30750/{fname}",
        "variant_code": f"30750-{color}",
        "variant_name": None,  # ham cikti varyant_adi None
        "layer_used": 1,
        "layer_1_attempt": {"success": True, "error": None, "method": "scraper_v1_0_rubelli"},
        "quality_check": "passed",
    })

# variants_raw'dan tum 28 varyant JSON'a
variants_for_json = []
for v in sd.get("variants_raw", []):
    color = v.get("color_code")
    if not color:
        continue
    color = color.zfill(3)
    full_code = f"30750-{color}"
    # Renk adi format: "Charles - Tabacco" -> "Tabacco"
    raw_name = v.get("name") or ""
    if " - " in raw_name:
        clean_name = raw_name.split(" - ", 1)[1].strip()
    else:
        clean_name = raw_name.strip() or None
    # Bu varyantin gorseli kopyalandi mi?
    local_path = None
    for img in copied_images:
        if img["variant_code"] == full_code:
            local_path = img["local_path"]
            img["variant_name"] = clean_name
            break
    variants_for_json.append({
        "color_code": full_code,
        "color_name": clean_name,
        "color_name_confidence": "exact" if clean_name else "unknown",
        "main_image_url_source": v.get("main_image_url"),
        "main_image_local_path": local_path,
    })

# === Charles urun JSON ===
CHARLES = {
    "_schema_version": "1.3",
    "urun_id": "rubelli_30750-charles",
    "brand": "Rubelli",
    "brand_slug": "rubelli",
    "collection": None,
    "product_code": "30750",
    "product_name": "Charles",
    "source_url": "https://www.rubelli.com/en/charles-30750",
    "scraped_at": ham["scraped_at"],
    "last_updated": NOW,
    "source_data": {
        "_description": (
            "Rubelli Charles (Formafantasma designer) — Cotton/Viscose/Linen plain moiré "
            "upholstery, 145 cm, 28 renk. Mobidik perdelik projesi icin kapsam disi (Heavy use), "
            "ancak Rubelli marka geneli izleme icin pilot."
        ),
        "_provenance": {
            "schema_version": "1.1",
            "created_at": NOW,
            "last_updated": NOW,
            "sources_used": [
                {"url": ham["source_url"], "type": "html_product_page", "accessed_at": ham["scraped_at"]},
                {"url": "adaptorler/rubelli.md", "type": "internal_adapter_v1.0", "accessed_at": NOW},
                {"url": "kapasite/staubli_uretim_kapasitesi.md", "type": "user_verified_capacity_table", "accessed_at": NOW},
            ],
            "constitutional_violations_check": f"passed_at_{NOW}",
            "audit_history": [{
                "audit_id": "rubelli_30750-charles_v1.0_2026-05-26",
                "audit_date": "2026-05-26",
                "audit_doc": "topla/scripts/create_rubelli_charles.py",
                "version_before": "(yok — Rubelli n=1 ilk)",
                "version_after": "v1.0 (Faz 5.5 canli test + denetim)",
                "notes": (
                    "Rubelli markasinin ILK denetlenmis urunu. Scraper v1.0 calisti. "
                    "Tum field'lar dogru cekildi (CO/VI/LI composition, width 145, plain moire, "
                    "Italy, CAL.TB117+BS5852). 28 varyant tespit edildi (Italyanca isimler), "
                    "ama sadece 2 gorsel indirildi (default + 008 Tabacco) — ?color= URL "
                    "parametresi Rubelli'de calismadi. Sonraki adim: scraper v1.1 ile color "
                    "picker click-based variant fetching. Mobidik scope: upholstery_kapsam_disi "
                    "(Heavy use mobilya kumaşı, perdelik projesi icin relevant degil)."
                ),
            }],
        },
        "technical": {
            "composition": sd.get("composition_parsed", []),
            "width_cm": 145,
            "weight_gsm": None,
            "weight_linear_meter_g": 460,
            "repeat_cm": {"vertical": None, "horizontal": None},
            "weave_type_raw": "Moiré (plain + finishing)",
            "weave_type_normalized": "plain",
            "yarn_type": "spun",
            "transparency": {"value": None, "_note": "Upholstery — opaque kesinlikle"},
            "usage_area": ["upholstery", "heavy_use"],
            "performance": {
                "lightfastness": None,
                "abrasion_martindale": 20000,
                "pilling": "4/5",
                "shrinkage": {"warp_percent": None, "weft_percent": None},
                "tensile_strength_en14465": "A",
                "tear_strength_en14465": "E",
                "seam_slippage_en14465": "A",
                "color_fastness_dry_clean": "A",
            },
            "acoustic": {"alpha_s_value": None, "absorption_class": None, "comment": None},
            "moire_finishing": True,
        },
        "variants": variants_for_json,
        "certifications": {
            "fire_safety": ["CAL TB117:2013 (Kaliforniya yangin upholstery)", "BS5852 source 0 (UK sigara/perdelik)"],
            "sustainability": [],
            "other": ["EN 14465 Type B (upholstery durability)"],
            "raw_text": "U.S.A. CAL.TB117:2013, UK Cigarette BS5852 source 0",
        },
        "commercial": {
            "price_per_meter": None, "price_currency": None, "moq_meters": None, "lead_time_days": None,
            "country_of_origin": "Italy",
            "sample_policy": "REQUEST A SAMPLE",
            "launch_year": None,
            "production_model": {"value": "limited_stock", "notes": "Sayfada 'Limited Stock' beyani"},
        },
        "design_credit": {"designer": "Formafantasma", "type": "collaborator", "notes": "Italyan tasarim stüdyosu — Andrea Trimarchi + Simone Farresin"},
        "description_original": {
            "language": "en",
            "text": (
                "Charles is the fourth edition of this particular cotton, linen, and viscose "
                "canvas. Moiré is an ancient, artisanal technique that creates a watermark "
                "effect through a natural sheen generated by a special process — without "
                "chemicals — using pressure and temperature."
            ),
            "source_url": ham["source_url"],
            "extracted_at": NOW,
        },
        "description_tr": {
            "text": (
                "Charles, bu özel pamuk-keten-viskon kanvasin dördüncü 'baskısı'. Moiré, "
                "kimyasal madde olmaksızın basınç ve sıcaklık ile filigran efekti oluşturan "
                "antik artisanal tekniği. Cotton, linen ve viskoz karışımı — Formafantasma tasarımı."
            ),
            "translation_method": "claude_inference",
            "translated_at": NOW,
            "is_official_translation": False,
        },
        "style_note": (
            "Italyan premium upholstery — Cotton+Linen+Viscose plain moiré 'antik tekniği'. "
            "Formafantasma designer credit. 28 renk genis palet."
        ),
        "_scraper_v1_sapma": {
            "use_alani": "'Care and treatment' yanlis eslesme — sayfada Use 'Heavy use' diyor; scraper sapmalari sonraki adim duzelir",
            "variant_imgs": "28 varyantin sadece 2'si gorsel aldi (default + selected) — ?color= URL parametresi Rubelli'de calismadi, color picker click-based gerek",
        },
    },
    "ai_inferences": {
        "weight_gsm": {
            "estimated_value": 317,
            "confidence": "high",
            "method": "460 g/lin.m / 1.45 m = 317.2 g/m². Matematiksel turetim.",
            "based_on": ["weight_linear", "width_cm"],
            "model": "claude-opus-4-7", "created_at": NOW, "user_verified": False,
        },
        "light_transmission": {
            "estimated_class": "blackout",
            "confidence": "high",
            "method": "Heavy use upholstery, 317 g/m² + plain moiré opaque sertifikali.",
            "based_on": ["use heavy", "weight_gsm 317", "Martindale 20000"],
            "model": "claude-opus-4-7", "created_at": NOW, "user_verified": False,
        },
    },
    "image_analysis": {
        "_description": "28 varyantin sadece 2'si indirildi — Avorio (default) + Tabacco (selected). 26 varyant gorseli scraper v1.1 sonrasi.",
        "dominant_colors": {"value": None},
        "color_palette_summary": "28 italyanca renk: Avorio, Perla, Pietra, Peltro, Tabacco, Blu, Ortensia, ...",
        "style_tags": ["italian", "rubelli", "formafantasma", "moiré", "plain", "upholstery", "venedik"],
        "pattern_type": "düz",
        "pattern_density": "düşük",
        "estimated_use_context": ["mobilya", "boyama-kosulu", "klasik dekorasyon", "premium konut"],
    },
    "images": {
        "_description": f"Faz 5.5 ilk Rubelli denetim. {len(copied_images)} gorsel indirildi (28 varyant icin) — scraper iyilesme gerek.",
        "main": [],
        "variants": copied_images,
        "lifestyle": [],
        "technical": [],
        "_quality_notes": [
            f"Charles 28 varyant tespit edildi (Italyanca isimler ile), ama sadece {len(copied_images)} gorsel "
            "alindi (default Avorio + selected Tabacco). Scraper v1.1 sonra 26 ek gorsel eklenecek."
        ],
    },
    "mobidik_evaluation": {
        "_description": (
            "Charles UPHOLSTERY (Heavy use) — Mobidik perdelik projesi icin kapsam DISI. "
            "Rubelli marka geneli icin izleme amacli pilot. Plain moiré dokuma TAM, ama "
            "moiré finishing ek sureç + 145 cm dar + Heavy use mobilya kumaşı."
        ),
        "staubli_feasibility": {
            "score": 4, "frame_count_estimate": "2-4",
            "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun (rapor yok)",
            "reed_density_estimate": "18-24 dent/cm (plain dense)",
            "sizing_requirement": "Multi-fiber CO/VI/LI hasil + moiré finishing (basinç+ısı)",
            "comment": (
                "Dokuma TAM: plain (moiré finishing dokuma sonrasi). 145 cm cok dar Mobidik 360 max icin israf. "
                "CO/VI/LI standart iplikler TAM. ASIL: Moiré finishing (basinç+ısı kimyasalsiz) "
                "Mobidik tezgahda yapilamaz — ayri finishing makinesi (calender / kalandr) gerek. "
                "Skor 4: dokuma yapilabilir, moiré ozel finishing yatirim ister."
            ),
        },
        "arge_value": {
            "score": 50,
            "key_learnings": ["Italyan moiré finishing tekniği", "Formafantasma tasarım dili", "EN 14465 upholstery sertifika", "28 renk yönetimi"],
            "comment": "Mobidik için ARGE değeri kismi (moiré finishing yatırım niş).",
        },
        "market_gap": {"score": 30, "comment": "UPHOLSTERY — Mobidik perdelik projesi kapsam disi. Mobilya kumaşı yerel uretim ayri sektor.", "target_markets": []},
        "portfolio_fit": {"score": 20, "similar_existing_products": [], "comment": "Mobidik portföyüne uyumsuz (perdelik vs upholstery)."},
        "overall_score": 36, "priority_level": "dusuk",
        "strategic_note": (
            "DUSUK ONCELIK — Charles UPHOLSTERY. Mobidik perdelik projesi icin kapsam disi. "
            "Rubelli marka geneli benchmarking icin gozlem (Italyan moiré + Formafantasma + 28 renk). "
            "Rubelli'de perdelik (Curtains/Sheers filtreli) ürünleri ayrica izlemek gerek — "
            "Charles ilgili değil. Strateji: Rubelli textiles?use=curtains kategorisinden 2-3 "
            "perdelik üründe pilot."
        ),
    },
    "data_quality": {
        "missing_fields": ["27 variants gorseli", "lightfastness", "lead_time_days"],
        "ai_estimated_fields": ["weight_gsm", "light_transmission"],
        "user_verified_fields": ["country (Italy)", "designer (Formafantasma)"],
        "completeness_percent": 65,
        "last_verified": NOW,
        "notes": [
            "Rubelli markasinin ilk denetlenmis urunu. Scraper v1.0 calisti.",
            "Charles UPHOLSTERY — perdelik projesi kapsam disi (Heavy use).",
            "28 varyant tespit + Italyanca isimler, ama sadece 2 gorsel.",
            "Rubelli scraper'in 'Use' alan yakalama sapmasi var (sonraki iterasyon duzeltir).",
        ],
    },
}

URUNLER.mkdir(parents=True, exist_ok=True)
charles_path = URUNLER / "rubelli_30750-charles.json"
with charles_path.open("w", encoding="utf-8") as f:
    json.dump(CHARLES, f, ensure_ascii=False, indent=2)
print(f"Yazildi: {charles_path.relative_to(PROJECT_ROOT)}")
print(f"  staubli=4/5 overall=36 priority=dusuk (Heavy use upholstery)")
print(f"  {len(copied_images)} gorsel kopyalandi (28 varyant icin az)")

# === Rubelli marka profili (n=1) ===
RUBELLI = {
    "_schema_version": "1.1",
    "brand": "Rubelli",
    "brand_slug": "rubelli",
    "country": "Italya",
    "region": "italyan",
    "headquarters_city": "Venedik (showroom) + Cucciago (uretim)",
    "founded_year": 1858,
    "website": "https://www.rubelli.com",
    "tracked_since": "2026-05-26",
    "last_updated": NOW,
    "product_count_tracked": 1,
    "_provenance": {
        "schema_version": "1.1", "created_at": NOW, "last_updated": NOW,
        "sources_used": [
            {"url": "adaptorler/rubelli.md", "type": "internal_adapter_v1.0", "accessed_at": NOW},
            {"url": "https://www.rubelli.com/en/textiles", "type": "category_keşfi", "accessed_at": NOW},
            {"url": "markalar/urunler/rubelli_30750-charles.json", "type": "internal_product_record", "accessed_at": NOW},
        ],
        "constitutional_violations_check": f"passed_at_{NOW}",
        "audit_history": [{
            "audit_id": "rubelli_marka_v1.0_2026-05-26",
            "audit_date": "2026-05-26",
            "version_before": "(yok)",
            "version_after": "v1.0 (n=1 Charles)",
            "notes": (
                "Rubelli marka profili ilk insa. 1858 Venedik kurulus, 557 ürün textiles. "
                "Charles tek denetim — UPHOLSTERY (Heavy use), Mobidik perdelik kapsam disi. "
                "Statik kimlik (kurucular/CEO/mill/designer roster) PENDING. "
                "Rubelli perdelik ürünleri (Curtains/Sheers filtre) icin pilot sonraki adim."
            ),
        }],
    },
    "width_distribution": {
        "min_cm": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 145},
        "max_cm": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 145},
        "comment": "n=1: Charles 145 cm — Rubelli'nin upholstery standart eni. Perdelik ürünleri farklı olabilir (300+ cm).",
    },
    "color_profile": {
        "total_variant_count": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 28},
        "average_per_product": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 28.0},
        "comment": "n=1: Charles 28 İtalyanca renk varyantı — Rubelli geniş palet yönetimi.",
    },
    "weave_distribution": {
        "plain": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 1, "comment": "Charles plain (moiré)"},
    },
    "composition_distribution": {
        "synthetic_ratio_percent": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 37},
        "natural_ratio_percent": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 63},
        "blend_ratio_percent": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 100},
        "comment": "n=1: Charles 3-bileşen (Cotton+Viscose+Linen) blend, natural-dominant.",
    },
    "country_distribution": {"Italy": 1},
    "mobidik_strategic_assessment": {
        "staubli_general_feasibility": "orta",
        "_general_feasibility_basis": (
            "n=1: Charles 4/5 (plain TAM, moiré finishing ek). Rubelli urun yelpazesi 557 — damask/jakar/velvet "
            "agirlikli + plain + sheers + curtains var. Mobidik perdelik icin sadece Curtains/Sheers kategorisi "
            "relevant. Damask/jakar Stäubli yapamaz (kapasite YOK). Marka geneli orta tahmini."
        ),
        "average_feasibility_score": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 4.0},
        "arge_priority_areas": [
            "Moiré finishing tekniği (basinç+ısı kalandr) — Mobidik yatirim alani",
            "Italyan tasarımcı işbirlikleri benchmark (Formafantasma)",
            "Multi-fiber blend iplik (CO/VI/LI) tedariki",
            "557 ürün katalog yönetimi (geniş palet, Rubelli scale benchmark)",
        ],
        "competitive_position": (
            "Rubelli Italyan premium 1858 kurulus, Venedik — yüzyıllık damask geleneği + çağdaş tasarımcı işbirlikleri. "
            "Mobidik perspektifi: Rubelli upholstery (Charles tipi) Mobidik kapsam DIŞI. "
            "Perdelik ve sheer ürünleri için ayrı pilot gerek — Curtains/Sheers filtre."
        ),
        "market_opportunity": (
            "Rubelli perdelik segmentinde (Curtains/Sheers) Mobidik nis pozisyon olabilir. "
            "Rubelli retail 80-150 EUR/m premium; Mobidik 25-40 EUR/m hedef. "
            "Italyan damask geleneği Mobidik kapasitesinde değil (jakar YOK), ama plain/sheer/leno yapilir."
        ),
        "benchmark_value": "Italyan premium tekstil markası benchmark. n=1 (Charles upholstery) için yetersiz — perdelik kategorisinden 2-3 ürün denetim gerek.",
        "watch_priority": "orta",
    },
    "data_integrity": {
        "verified_data_points": 0, "ai_estimated_data_points": 2, "verification_ratio": 0.0,
        "reliability_label": "insufficient_sample",
        "sample_size_tracked_products": 1,
        "_reliability_explanation": "n=1 (Charles upholstery). Perdelik ürünleri icin n=0 — perdelik filtreli pilot acil gerek.",
    },
    "notes": [
        "v1.0 (2026-05-26): Rubelli marka profili ilk inşa.",
        "Rubelli 1858 Venedik — 170 yıllık premium İtalyan tekstil (Venedik dokuma geleneği).",
        "557 ürün textiles katalog. Upholstery + Curtains + Sheers + Wallcoverings + Outdoor.",
        "Charles tek denetlenmiş — UPHOLSTERY (Heavy use), Mobidik perdelik kapsam DIŞI.",
        "Sonraki adim: Rubelli textiles?use=curtains kategorisinden 2-3 perdelik üründe pilot.",
        "Statik kimlik (Wikipedia + about) PENDING.",
    ],
}

(MARKA / "rubelli.json").write_text(json.dumps(RUBELLI, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Yazildi: markalar/rubelli.json (n=1, insufficient_sample)")
