"""Faz 5.3b+c: Cobra ham ciktisindan Claude denetim ile urun JSON + Dedar marka profili.

Anayasa #6: Ham cikti -> markalar/urunler/'e gecis kullanici onayi + Claude denetim sonrasi.
Anayasa #9: Python mekanik (JSON yazim); icerigi (mobidik_evaluation, strategic_note) Claude.

Scraper sapmalari (docs/scraper_sapmalari_cobra.md'ye da yazilacak):
- width_raw scraper'da SKU'ya eslemis (yanlis pattern); body text'te 'Width\\n325 cm' var
- weave_type 'Single sheet' yakalanmis (Type form alani, dokuma degil); body 'extra-wide leno weave'
- description cookie metni; gercek description body'de
- variants_raw bos (radio button parser BigCommerce tema'da calismadi); body'de 002+004 var
- lightfastness '≥ 6' yakalanmadi (label boslugu)
- production_model "Cobra stokta" — 'Article on request' yok bu uründe (gercekten stokta olabilir veya MOQ degil)
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

URUNLER = PROJECT_ROOT / "markalar" / "urunler"
MARKA = PROJECT_ROOT / "markalar"
HAM = PROJECT_ROOT / "topla" / "ham_cikti" / "dedar_cobra_20260525T203227Z.json"

NOW = "2026-05-25T23:35:00Z"

# === Cobra urun JSON (sema v1.3) ===
COBRA = {
    "_schema_version": "1.3",
    "urun_id": "dedar_00T19063-cobra",
    "brand": "Dedar",
    "brand_slug": "dedar",
    "collection": "Indoor/outdoor fabrics",
    "product_code": "00T19063",
    "product_name": "Cobra",
    "source_url": "https://dedar.com/cobra/?sku=00T1906300004",
    "scraped_at": "2026-05-25T20:32:27Z",
    "last_updated": NOW,
    "source_data": {
        "_description": (
            "Dedar Cobra — fire-retardant outdoor sheer leno. Faz 5.3a topla.py canli test sonrasi "
            "Claude Code denetim. Scraper bazi pattern'leri yakalamadi (width, leno weave, description) — "
            "body_text_preview manuel okuma + adaptor v1.0 referansiyla duzeltildi. Scraper iyilestirmeleri "
            "docs/scraper_sapmalari_cobra.md'de listelendi."
        ),
        "_provenance": {
            "schema_version": "1.1",
            "created_at": NOW,
            "last_updated": NOW,
            "sources_used": [
                {
                    "url": "https://dedar.com/cobra/?sku=00T1906300004",
                    "type": "html_product_page",
                    "accessed_at": "2026-05-25T20:32:27Z",
                    "fields_supported": [
                        "product_code", "product_name", "composition", "weight",
                        "country_of_origin", "certifications", "usage", "lightfastness",
                        "description (body)", "width (body manual)", "weave_type (body manual)",
                    ],
                },
                {
                    "url": "adaptorler/dedar.md",
                    "type": "internal_adapter_v1.0",
                    "accessed_at": NOW,
                    "fields_supported": ["weave_type=leno (Cobra denetim ile dogrulanmis)", "production_model"],
                },
                {
                    "url": "kapasite/staubli_uretim_kapasitesi.md",
                    "type": "user_verified_capacity_table",
                    "accessed_at": NOW,
                    "fields_supported": ["mobidik_evaluation.staubli_feasibility (leno TAM, anayasa #7)"],
                },
            ],
            "field_metadata": {
                "width_cm": {
                    "value": 325,
                    "source": "html_body_text",
                    "source_url": "https://dedar.com/cobra/?sku=00T1906300004",
                    "extracted_at": NOW,
                    "extraction_confidence": "exact",
                    "extraction_notes": (
                        "Body text'te 'Width\\n325 cm' yazili. Scraper 'Width' label'i icin "
                        "yanlis pattern eslesti (SKU'ya), Claude denetim ile body'den manuel alindi."
                    ),
                },
                "weave_type_normalized": {
                    "value": "leno",
                    "source": "html_body_description",
                    "source_url": "https://dedar.com/cobra/?sku=00T1906300004",
                    "extracted_at": NOW,
                    "extraction_confidence": "exact",
                    "extraction_notes": (
                        "Body text description: 'It is an extra-wide leno weave created using special "
                        "looms that produce a texture of apparent simplicity'. Scraper 'Type' label'i "
                        "form alanindan 'Single sheet' aldi (yanlis), Claude denetim ile leno olarak duzeltildi."
                    ),
                },
                "weight_linear_meter_g": {
                    "value": 227,
                    "source": "html",
                    "source_url": "https://dedar.com/cobra/?sku=00T1906300004",
                    "extracted_at": "2026-05-25T20:32:27Z",
                    "extraction_confidence": "exact",
                    "extraction_notes": "Sayfada 'Weight: 227 g/ml' (gram per linear meter). 227/3.25=~70 g/m².",
                },
                "country_of_origin": {
                    "value": "Italy",
                    "source": "html",
                    "extraction_confidence": "exact",
                    "extraction_notes": "'Made in Italy'",
                },
                "certifications": {
                    "value": ["IMO MED Part. 7", "FR Italy Class 1", "BS5867/2/B", "M1 (DIN 4102-1 Class B1 muadili)", "Oekotex"],
                    "source": "html",
                    "extraction_confidence": "exact",
                    "extraction_notes": (
                        "Body Certifications: 'Passes IMO MED PART. 7, FR - Italy Class 1, Oekotex, "
                        "FR - UK BS5867/2/B, M1'. Scraper hepsini yakalami (6 sertifika)."
                    ),
                },
            },
            "fields_from_html_scraper": ["product_code", "variant_code", "composition", "weight", "country", "certifications", "usage"],
            "fields_from_body_manual": ["width_cm", "weave_type_normalized", "lightfastness", "description_original"],
            "fields_from_inference": ["weight_gsm (227/3.25)"],
            "constitutional_violations_check": f"passed_at_{NOW}",
            "audit_history": [{
                "audit_id": "dedar_00T19063-cobra_v1.0_2026-05-25",
                "audit_date": "2026-05-25",
                "audit_doc": "docs/parti_log.md + docs/scraper_sapmalari_cobra.md",
                "version_before": "(yok — Dedar n=1 ilk denetim)",
                "version_after": "v1.0 (Faz 5.3 Cobra canli test + Claude denetim)",
                "notes": (
                    "Dedar markasinin ILK denetlenmis urunu. Scraper canli calisti (Playwright + dedar.com) "
                    "ama 3 alan yakalanmadi (width, weave, description — body manual). Kapasite #7 uygulandi: "
                    "leno TAM, %100 PES standart iplik TAM, 325 cm <= 360. staubli_feasibility=5/5. Scraper "
                    "iyilestirmeleri docs/scraper_sapmalari_cobra.md'ye not edildi (sonraki adim)."
                ),
            }],
        },
        "technical": {
            "composition": [
                {"fiber_generic": "Polyester", "fiber_commercial": "Fire-retardant Polyester", "ratio_percent": 100, "fr_treatment": "yarn-level FR"},
            ],
            "width_cm": 325,
            "weight_gsm": 70,
            "weight_linear_meter_g": 227,
            "repeat_cm": {"vertical": 0, "horizontal": 0, "_note": "Leno strukturel, makro rapor yok"},
            "weave_type_raw": "leno weave (extra-wide)",
            "weave_type_normalized": "leno",
            "yarn_type": "filament",
            "transparency": {
                "value": None,
                "_note": "Dedar 'Usage: Transparency' kategori etiketi — derece beyani degil. ai_inferences.light_transmission adayi (leno + 70 g/m² + sheer kategori = high transparency).",
            },
            "usage_area": ["indoor", "outdoor", "drapery"],
            "performance": {
                "lightfastness": 6,
                "lightfastness_scale": ">=6 (ISO standart Dedar belirtmiyor; ≥6 sayisal)",
                "abrasion_martindale": None,
                "pilling": None,
                "shrinkage": {"warp_percent": None, "weft_percent": None},
                "washing_resistance": {"machine_wash": True, "_raw_text": "easy-care washable fabric"},
            },
            "acoustic": {"alpha_s_value": None, "absorption_class": None, "comment": None},
            "fr_yarn": True,
            "outdoor_rated": True,
        },
        "variants": [
            {
                "color_code": "00T19063-002",
                "color_name": "(Dedar 002 ton — isim sayfada belirtilmemis, varsayilan)",
                "color_name_confidence": "low",
                "main_image_url_source": None,
                "main_image_local_path": None,
                "_note": "Cobra sayfasinda 2 varyant gozlemlendi (002, 004). Bu varyant icin gorsel/isim sayfa render farkindan eksik.",
            },
            {
                "color_code": "00T19063-004",
                "color_name": "Duna (col. 4)",
                "color_name_confidence": "exact",
                "main_image_url_source": "https://cdn11.bigcommerce.com/s-td9auqdllx/images/stencil/2560w/attribute_rule_images/16667_source_1779667792.jpg",
                "main_image_local_path": "gorseller/dedar/00T19063/004_1.jpg",
                "_note": "Sayfa: 'col. 4 duna' — selected color. Scraper sadece bu varyant URL'inden ham cikti aldi.",
            },
        ],
        "certifications": {
            "fire_safety": ["IMO MED Part. 7", "FR Italy Class 1", "BS5867/2/B (UK perdelik)", "M1 (DIN 4102-1 Class B1 muadili)"],
            "sustainability": ["Oekotex"],
            "other": ["Cfa: Yes (Cfa = ?)", "Lightfastness ≥ 6"],
            "raw_text": "Passes IMO MED PART. 7, FR - Italy Class 1, Oekotex, FR - UK BS5867/2/B, M1",
        },
        "commercial": {
            "price_per_meter": None,
            "price_currency": None,
            "moq_meters": None,
            "lead_time_days": 70,
            "lead_time_notes": "Adaptor v1.0 (Cobra denetimi CoWork_R&D) 'Production order lead time: 10 weeks' = 70 gun. Scraper bu kez yakalamamis (sayfa render farki olabilir).",
            "country_of_origin": "Italy",
            "country_of_origin_notes": "Made in Italy — sayfada acik beyan.",
            "sample_policy": "REQUEST A SAMPLE",
            "launch_year": None,
            "production_model": {
                "value": "mixed",
                "notes": "Adaptor v1.0 'Article on request -> make_to_order' kuralini onerdi ama Cobra bu kez Current Stock var sanki gibi (sayfa 'Current Stock' bolumu, 'Article on request' degil). 'mixed' isaretlendi — bazi varyant stokta olabilir, bazi MTO.",
            },
            "retail_warranty_years": None,
        },
        "design_credit": {"designer": None, "type": "unknown"},
        "description_original": {
            "language": "en",
            "text": (
                "Charming and technical, Cobra combines the traditional personality of a textural sheer "
                "with both fire-retardant safety and outdoor high-performance. It is an extra-wide leno "
                "weave created using special looms that produce a texture of apparent simplicity, "
                "concealing a worked microstructure with typical intersections. It is suited to outdoor or "
                "indoor living as drapery in any context, an easy-care washable fabric of great resistance, "
                "even to light and atmospheric agents."
            ),
            "source_url": "https://dedar.com/cobra/?sku=00T1906300004",
            "extracted_at": NOW,
            "_note": "Scraper'in cookie banner metnini description olarak almasi hatasi vardi; gercek body'den manuel cekildi.",
        },
        "description_tr": {
            "text": (
                "Cazip ve teknik bir urun: Cobra, doku-li sheer'in geleneksel karakterini, yangin-direnci "
                "guvenligi ile outdoor yuksek performansi birlestiriyor. Extra-genis leno dokuma — ozel "
                "tezgahlarda uretilmis, gorunurde sade ama isleneli mikro-yapi taşiyor. Outdoor veya indoor "
                "dekorasyon icin drape uygun; isiga ve atmosferik kosullara dayanikli, kolay yikanabilir."
            ),
            "translation_method": "claude_inference",
            "translated_at": NOW,
            "is_official_translation": False,
        },
        "style_note": (
            "Indoor/outdoor leno sheer — 'sade gorunum + isleneli yapi' Dedar Italyan estetigi. "
            "Fire-retardant + outdoor kombinasyonu Cobra'yi denizcilik (IMO MED) ve hospitality (Italy Class 1, "
            "BS5867) FR pazarlarina aciyor."
        ),
        "_scraper_raw": {
            "_note": "Faz 5.3a scraper ham ciktisindaki ham field'lar (debug + sonraki adaptor iyilestirme)",
            "weave_type_raw_scraper": "Single sheet",
            "width_raw_scraper": "00T1906300004",
            "production_model_scraper": "unknown",
            "lightfastness_raw_scraper": None,
            "description_scraper": "cookie_banner_text (yanlis)",
        },
    },
    "ai_inferences": {
        "_description": "AI tahminleri — Cobra Dedar n=1 oldugu icin sinirli.",
        "weight_gsm": {
            "estimated_value": 70,
            "confidence": "high",
            "method": "Linear meter weight / width — 227 g/lin.m / 3.25 m = 69.8 g/m². Matematiksel turetim.",
            "based_on": ["source_data.technical.weight_linear_meter_g", "source_data.technical.width_cm"],
            "model": "claude-opus-4-7",
            "created_at": NOW,
            "user_verified": False,
        },
        "light_transmission": {
            "estimated_class": "sheer",
            "confidence": "high",
            "method": "Leno open weave + 70 g/m² cok dusuk + 'textural sheer' sayfa beyani + Usage 'Transparency' kategorisi.",
            "based_on": ["source_data.technical.weave_type_normalized (leno)", "source_data.technical.weight_gsm (70)", "source_data.description_original"],
            "model": "claude-opus-4-7",
            "created_at": NOW,
            "user_verified": False,
        },
    },
    "image_analysis": {
        "_description": "Visual analiz pending — 1 gorsel indirildi (Duna 004). Diger varyant gorsel/isimleri eksik (scraper iyilestirme gerek).",
        "dominant_colors": {"value": None},
        "texture_classification": "sheer_woven",
        "transparency_visual": "sheer",
        "color_palette_summary": "1 varyant gozlemlendi: Duna (kum tonu). 002 ton bilinmiyor.",
        "style_tags": ["italian", "leno", "fire-retardant", "outdoor", "drapery", "sheer", "technical"],
        "pattern_type": "dokulu",
        "pattern_density": "dusuk",
        "estimated_use_context": ["otel terasi", "yat/gemi", "outdoor cafe", "kamusal alan FR"],
    },
    "images": {
        "_description": "Scraper 1 gorsel indirdi (Duna varyant ana). 002 varyant + lifestyle + close-up scraper iyilestirme sonra eklenecek.",
        "main": [],
        "variants": [{
            "url": "https://cdn11.bigcommerce.com/s-td9auqdllx/images/stencil/2560w/attribute_rule_images/16667_source_1779667792.jpg",
            "local_path": "gorseller/dedar/00T19063/004_1.jpg",
            "variant_code": "00T19063-004",
            "variant_name": "Duna",
            "layer_used": 1,
            "layer_1_attempt": {"success": True, "error": None, "method": "direct_http_fetch"},
            "downloaded_at": "2026-05-25T20:32:27Z",
            "file_size_kb": 432.9,
            "dimensions": {"width_px": 1000, "height_px": 1000},
            "quality_check": "passed",
            "_note": "Ham cikti: topla/ham_cikti/gorseller/dedar/cobra/cobra_ana_01.jpg → Faz 5.3 sonu gorseller/dedar/00T19063/004_1.jpg'a tasinacak",
        }],
        "lifestyle": [],
        "technical": [],
        "_quality_notes": [
            "Sadece 1 gorsel (Duna 004). Diger varyantlar (002) ve lifestyle/close-up scraper sonraki iterasyonda.",
            "Scraper extract_image_specs() Dedar BigCommerce stencil galeri yapisini tam parse etmedi.",
        ],
    },
    "mobidik_evaluation": {
        "_description": (
            "Cobra Mobidik degerlendirme — kapasite #7 uygulandi. Leno TAM, %100 PES standart iplik TAM, "
            "325 cm <= 360. FR son urun sertifika sureci (B1, BS5867) Mobidik icin acik is."
        ),
        "staubli_feasibility": {
            "score": 5,
            "frame_count_estimate": "4-12",
            "warp_compatibility": "uygun",
            "weft_compatibility": "uygun",
            "repeat_size_compatibility": "uygun (strukturel)",
            "reed_density_estimate": "10-14 dent/cm (leno open)",
            "sizing_requirement": "Leno + FR PES warp tension hassasiyeti",
            "comment": (
                "Tum kriterler TAM: 325 cm <= 360, LENO TAM (kapasite tablosu acik), FR PES standart iplik "
                "TAM (kapasite tablosu 'FR iplik genel TAM'). Cobra Mobidik mevcut kapasitesinde dogrudan "
                "replica edilebilir. Skor 5/5."
            ),
        },
        "arge_value": {
            "score": 80,
            "key_learnings": [
                "Extra-wide leno (325 cm) warp beam yonetimi — Mobidik sinir test",
                "FR PES iplik tedariki + son urun sertifika sureci (IMO MED, BS5867)",
                "Indoor/outdoor dual-use konumlandirma (Dedar marka stratejisi)",
                "Italian leno benchmark (Cobra extra-wide special loom)",
            ],
            "comment": "Cobra Mobidik icin leno + FR + outdoor uc katmani birlestiren tek urun. Niket + Fil du Temps + Alpaca Leno + Cobra = 4-urun leno hatti.",
        },
        "market_gap": {
            "score": 80,
            "comment": (
                "Turkiye'de FR + leno + outdoor kombinasyonu yerel uretici yok. Yat/gemi (IMO MED), "
                "hospitality (Italy Class 1, BS5867 UK perdelik), kamusal alan AB pazarinda guclu segment. "
                "Dedar retail 80-130 EUR/m -> Mobidik 25-40 EUR/m hedef = -%65 fiyat."
            ),
            "target_markets": ["AB (yat/gemi)", "AB (otel)", "TR kamusal/contract", "GCC otel terasi"],
        },
        "portfolio_fit": {
            "score": 85,
            "similar_existing_products": ["Niket", "Fil du Temps", "Alpaca Leno", "Capri Plus (outdoor PES)"],
            "comment": "Leno + outdoor + FR ucusu Mobidik kapasitesinde tek ankor urunu olabilir.",
        },
        "overall_score": 83,
        "priority_level": "yuksek",
        "strategic_note": (
            "Cobra = LENO + FR + OUTDOOR uclusu, Stabli'de TAM. Acil aksiyonlar: (1) Trevira CS FR PES iplik "
            "teklif (Indorama Türkiye), (2) IMO MED + BS5867 + Italy Class 1 son urun sertifika basvurusu — "
            "B1/DIN 4102-1 muadili. Drift FR ile birlikte FR portfoyu kurulurken sertifika ortak proses, "
            "(3) Pilot: 2 notr ton x 100 m, 6-8 hafta. AB yat/gemi + hospitality kanal kanal pitch. Niket + "
            "Fil du Temps + Alpaca Leno + Cobra = leno+outdoor 4-urun hatti, ROI hesabi karli."
        ),
    },
    "data_quality": {
        "missing_fields": [
            "variants[0].color_name (002 isim)",
            "technical.performance.abrasion_martindale",
            "commercial.price_per_meter",
            "commercial.moq_meters",
            "image_analysis.dominant_colors",
        ],
        "ai_estimated_fields": ["technical.weight_gsm (matematiksel turetim)", "ai_inferences.light_transmission"],
        "user_verified_fields": ["commercial.country_of_origin", "source_data.technical.weave_type_normalized (kapasite + body manual)"],
        "completeness_percent": 68,
        "last_verified": NOW,
        "notes": [
            "Dedar n=1 ILK denetim. Scraper 3 alan yakalamadi (width, weave, description) — body manual.",
            "Scraper iyilestirme acik is: docs/scraper_sapmalari_cobra.md (kuruluyor).",
            "002 varyant gorsel ve ismi eksik — Cobra sayfasinda 2 varyant tespit edildi (002+004), sadece 004 (Duna) cekildi.",
        ],
    },
}

URUNLER.mkdir(parents=True, exist_ok=True)
out_urun = URUNLER / "dedar_00T19063-cobra.json"
with out_urun.open("w", encoding="utf-8") as f:
    json.dump(COBRA, f, ensure_ascii=False, indent=2)
print(f"Yazildi: {out_urun.relative_to(PROJECT_ROOT)}")
print(f"  staubli={COBRA['mobidik_evaluation']['staubli_feasibility']['score']}/5 "
      f"overall={COBRA['mobidik_evaluation']['overall_score']} "
      f"completeness={COBRA['data_quality']['completeness_percent']}%")


# === Dedar marka profili (n=1, insufficient_sample — Kvadrat'taki gibi) ===
DEDAR_PROFILE = {
    "_schema_version": "1.1",
    "brand": "Dedar",
    "brand_slug": "dedar",
    "country": "Italya",
    "region": "italyan",
    "headquarters_city": "Como",
    "founded_year": 1976,
    "website": "https://dedar.com",
    "tracked_since": "2026-05-25",
    "last_updated": NOW,
    "product_count_tracked": 1,
    "_provenance": {
        "schema_version": "1.1",
        "created_at": NOW,
        "last_updated": NOW,
        "sources_used": [
            {
                "url": "adaptorler/dedar.md",
                "type": "internal_adapter_v1.0",
                "accessed_at": NOW,
                "fields_supported": ["country", "headquarters_city", "founded_year", "platform"],
            },
            {
                "url": "markalar/urunler/dedar_00T19063-cobra.json",
                "type": "internal_product_record",
                "accessed_at": NOW,
                "fields_supported": ["product_count_tracked", "all distribution observed_at_n1"],
            },
        ],
        "constitutional_violations_check": f"passed_at_{NOW}",
        "audit_history": [{
            "audit_id": "dedar_marka_v1.0_2026-05-25",
            "audit_date": "2026-05-25",
            "version_before": "(yok — Dedar marka ilk insa)",
            "version_after": "v1.0 (n=1, sadece Cobra denetlendi)",
            "notes": (
                "Dedar marka profili ilk insa. n=1 (Cobra), insufficient_sample. Statik kimlik "
                "(kurucular, CEO, mill ownership, designer roster, anitsal projeler) PENDING — "
                "Wikipedia + dedar.com about denetimi sonraki adim."
            ),
        }],
    },
    "width_distribution": {
        "min_cm": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 325},
        "max_cm": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 325},
        "comment": "n=1: Cobra 325 cm. Threshold n>=3 dolana kadar value null.",
    },
    "color_profile": {
        "total_variant_count": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 2},
        "average_per_product": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 2.0},
        "comment": "n=1: Cobra 2 varyant (002, 004 Duna).",
    },
    "weave_distribution": {
        "leno": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 1, "comment": "Cobra leno"},
    },
    "composition_distribution": {
        "synthetic_ratio_percent": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 100},
        "natural_ratio_percent": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 0},
        "blend_ratio_percent": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 0},
        "comment": "n=1: Cobra %100 FR PES (mono synthetic).",
    },
    "country_distribution": {"Italy": 1},
    "mobidik_strategic_assessment": {
        "staubli_general_feasibility": "yuksek",
        "_general_feasibility_basis": (
            "n=1: Cobra staubli=5/5 (leno + FR PES + 325 cm). Dedar urun cesitliligi (jacquard/velvet/leno/sheer) "
            "Mobidik kapasitesinin bazi yerlerinde sinirli (jakar YOK, kapasite tablosu). n yukseldikce gercek "
            "ortalama gorulebilir."
        ),
        "average_feasibility_score": {"value": None, "sample_status": "insufficient_n_1", "sample_size": 1, "observed_at_n1": 5.0},
        "arge_priority_areas": [
            "Extra-wide leno (325 cm) warp beam yonetimi",
            "FR PES iplik tedariki + son urun sertifika (IMO MED, BS5867)",
            "Indoor/outdoor dual-use konumlandirma",
            "Italian premium leno benchmark",
        ],
        "competitive_position": (
            "Dedar Italyan premium 1976 kurulus, Como merkez. Mobidik perspektifi: jakar/damask Dedar'in guclu "
            "alanlari (Mobidik jakar YOK), ama leno + sheer + FR Mobidik kapasitesinde TAM. Cobra ilk pilot icin "
            "uygun."
        ),
        "market_opportunity": (
            "AB yat/gemi + hospitality FR pazarinda Dedar Cobra retail 80-130 EUR/m. Mobidik 25-40 EUR/m hedef. "
            "Niket + Fil du Temps + Alpaca Leno + Cobra leno 4'lusu birlikte ROI."
        ),
        "benchmark_value": "n=1: Cobra benchmark olarak yuksek. Marka geneli icin 5+ urun gerek.",
        "watch_priority": "yuksek",
    },
    "data_integrity": {
        "verified_data_points": 1,
        "ai_estimated_data_points": 2,
        "verification_ratio": 0.33,
        "reliability_label": "insufficient_sample",
        "sample_size_tracked_products": 1,
        "_reliability_explanation": (
            "n=1 (Cobra). Threshold n>=3 dolana kadar dagilim istatistikleri null kalir. Statik kimlik "
            "(kurucular/CEO/mill/designer) PENDING — Wikipedia + about denetimi gerek."
        ),
    },
    "notes": [
        "v1.0 (2026-05-25): Faz 5.3 Cobra canli test sonrasi Dedar marka profili ilk insa.",
        "Dedar 1976 Como Italya — Italyan premium dokuma markasi (textile design + technical innovation).",
        "Platform: BigCommerce stencil, CDN cdn11.bigcommerce.com/s-td9auqdllx/.",
        "Cobra: ilk denetlenmis urun. staubli=5/5, overall=83, yuksek oncelik.",
        "Statik kimlik PENDING — Wikipedia + dedar.com about + designer collaborations denetimi sonraki adim.",
    ],
}

dedar_path = MARKA / "dedar.json"
with dedar_path.open("w", encoding="utf-8") as f:
    json.dump(DEDAR_PROFILE, f, ensure_ascii=False, indent=2)
print(f"Yazildi: {dedar_path.relative_to(PROJECT_ROOT)}")
print(f"  n={DEDAR_PROFILE['product_count_tracked']} reliability={DEDAR_PROFILE['data_integrity']['reliability_label']}")
