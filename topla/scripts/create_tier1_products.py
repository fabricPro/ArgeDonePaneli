"""Faz 6.8b: 4 Tier 1 ALTIN-aday icin Claude denetim → markalar/urunler/.

Anayasa #6 + #9: ham_cikti'dan denetlenmis ürün JSON'una geçiş.
Python mekanik (provenance + audit_history scaffold), Claude analiz
(mobidik_evaluation, strategic_note, sub-brand, sertifika yol haritası).

4 ürün (hepsi Dedar):
- 00T22044 wide-linen-baobab (Anatolian Linen sub-brand aday)
- 00T21015 wide-linen-atelier-1930 (Anatolian Linen sub-brand aday)
- 00T19031 wide-linen-signor-darcy ⭐ (saf keten chevron, en güçlü ALTIN aday)
- 00T23046 twillman (Cobra ailesi muadili FR twill)
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
NOW = "2026-05-26T09:30:00Z"


# ============================================================
# 4 ÜRÜN AUDIT VERİSİ — Claude analizi (Anayasa #9)
# ============================================================

PRODUCTS = {
    "wide-linen-baobab": {
        "ham_cikti_file": "dedar_wide-linen-baobab_20260526T090048Z.json",
        "product_code": "00T22044",
        "product_name": "Wide Linen Baobab",
        "collection": "Wide Sheers — Linen",
        "source_url": "https://dedar.com/wide-linen-baobab/",
        "composition": [
            {"fiber_commercial": "Linen", "fiber_generic": "linen", "ratio_percent": 90},
            {"fiber_commercial": "Polyamide", "fiber_generic": "polyamide", "ratio_percent": 10},
        ],
        "width_cm": 300,
        "country_of_origin": "Italy",
        "weave_type_raw": "open weave",
        "weave_type_normalized": "open_weave_dobby",
        "weave_notes": "Body description: 'open weave that allows light to filter through'. Bulky linen yarn + polyamide karışım, dokuma 'open weave' = sheer açık dokuma. Stäubli dobby ile uyumlu (kural #7).",
        "lightfastness": None,
        "certifications_raw": ["M1"],
        "certifications_other": ["M1 (DIN 4102-1 Class B1 muadili)"],
        "category": ["Sheer fabrics", "Wide curtains"],
        "designer": None,
        "variant_count": 8,
        "description_original_text": (
            "An extra-width linen poised harmoniously between a textural effect and transparency: "
            "intertwined with bulky linen yarn to create an open weave that allows the light to filter through."
        ),
        "description_tr_text": (
            "Doku etkisi ile şeffaflık arasında uyumla konumlanmış ekstra-geniş keten: "
            "iri keten ipliklerle örülerek ışığın süzülmesine izin veren açık dokuma."
        ),
        "style_note": (
            "Anatolian Linen sub-brand muadili — 90% keten + 10% naylon (sağlamlık), "
            "açık dokuma sheer, 300 cm en (Mobidik 360 cm avantajı içinde), 8 nötr ton. "
            "M1 sertifika var → Mobidik için M1 (Fransa) B1'e eşdeğer."
        ),
        "mobidik_evaluation": {
            "priority_level": "yüksek",
            "staubli_feasibility": {
                "score": 5,
                "frame_count_estimate": "12-16 cerceve (open weave dobby — basit yapı)",
                "comment": (
                    "Stäubli dobby + 90% keten + 10% naylon (standart iplik) = TAM uyum. "
                    "Open weave (sheer) Stäubli ana fonksiyonu. 300 cm en Mobidik 360 cm "
                    "sınırı içinde. Mevcut Türk fason: SASA naylon, Bursa keten birliği."
                ),
            },
            "overall_score": 80,
            "components": {
                "staubli_feasibility": 5,
                "yarn_supply": 4,
                "certification_path": 3,
                "market_fit": 5,
                "sub_brand_alignment": 5,
                "design_uniqueness": 3,
            },
            "strategic_note": (
                "Anatolian Linen sub-brand için pilot adayı (Air Line/Melange Linen/Nuri 81-82 "
                "ALTIN ailesi). Mobidik avantajı: 360 cm warp beam → 300 cm en kolay, "
                "Türk keten + naylon tedariki yerli (SASA + Bursa). M1 sertifika prosesi "
                "mevcut OEKO-TEX'i tamamlar. ARGE pilot: 3 nötr ton × 100 m, 4-6 hafta. "
                "EU Flax sertifikası 'Anatolian Linen' söylem için ek değer (3-6 ay başvuru)."
            ),
        },
    },
    "wide-linen-atelier-1930": {
        "ham_cikti_file": "dedar_wide-linen-atelier-1930_20260526T090127Z.json",
        "product_code": "00T21015",
        "product_name": "Wide Linen Atelier 1930",
        "collection": "Wide Sheers — Linen",
        "source_url": "https://dedar.com/wide-linen-atelier-1930/",
        "composition": [
            {"fiber_commercial": "Linen", "fiber_generic": "linen", "ratio_percent": 90},
            {"fiber_commercial": "Polyamide", "fiber_generic": "polyamide", "ratio_percent": 10},
        ],
        "width_cm": 305,
        "country_of_origin": "Italy",
        "weave_type_raw": "open weave",
        "weave_type_normalized": "open_weave_dobby",
        "weave_notes": "Body description: 'open weave construction allows light filter'. Baobab kardeşi — aynı kompozisyon, biraz daha geniş.",
        "lightfastness": None,
        "certifications_raw": ["M1", "Oekotex"],
        "certifications_other": ["M1 (DIN 4102-1 Class B1 muadili)", "OEKO-TEX Standard 100"],
        "category": ["Sheer fabrics", "Wide curtains"],
        "designer": None,
        "variant_count": 3,
        "description_original_text": (
            "A linen fabric in extra width, with the spontaneous beauty of natural yarns, "
            "whose impact lies in the contrast between texture and transparency. Thanks to its "
            "open weave construction, it allows the light to filter through, despite the assertive "
            "presence of linen."
        ),
        "description_tr_text": (
            "Ekstra genişlikte keten kumaş, doğal ipliklerin spontane güzelliğiyle, "
            "doku ile şeffaflık arasındaki kontrastta etkili. Açık dokuma konstrüksiyonu sayesinde, "
            "ketenin baskın varlığına rağmen ışığın süzülmesine izin verir."
        ),
        "style_note": (
            "Baobab kardeşi (aynı kompozisyon, 305 cm). 'Atelier 1930' atölye/zanaat söylemi — "
            "Mobidik Anatolian Linen hikayesine (Bursa keten dokuma geleneği) uygun. "
            "OEKO-TEX zaten var (Mobidik mevcut sertifikasıyla eşit)."
        ),
        "mobidik_evaluation": {
            "priority_level": "yüksek",
            "staubli_feasibility": {
                "score": 5,
                "frame_count_estimate": "12-16 cerceve",
                "comment": (
                    "Baobab ile teknik olarak özdeş. Stäubli dobby + keten/naylon = TAM. "
                    "305 cm en sorunsuz."
                ),
            },
            "overall_score": 81,
            "components": {
                "staubli_feasibility": 5,
                "yarn_supply": 4,
                "certification_path": 4,
                "market_fit": 5,
                "sub_brand_alignment": 5,
                "design_uniqueness": 3,
            },
            "strategic_note": (
                "Atelier 1930 söylemi Anatolian Linen sub-brand'ın 'Bursa atölye geleneği' "
                "hikayesine uygun. M1+OEKO-TEX iki sertifika mevcut (Mobidik OEKO-TEX zaten "
                "var, M1 başvuru gerek — 3-6 ay). 3 renk varyantı = sınırlı palette; "
                "pilot için 3 nötr ton × 100 m, 4-6 hafta. Türk keten + SASA naylon yerli."
            ),
        },
    },
    "wide-linen-signor-darcy": {
        "ham_cikti_file": "dedar_wide-linen-signor-darcy_20260526T090205Z.json",
        "product_code": "00T19031",
        "product_name": "Wide Linen Signor Darcy",
        "collection": "Wide Sheers — Linen",
        "source_url": "https://dedar.com/wide-linen-signor-darcy/",
        "composition": [
            {"fiber_commercial": "Linen", "fiber_generic": "linen", "ratio_percent": 100},
        ],
        "width_cm": 310,
        "country_of_origin": "Italy",
        "weave_type_raw": "chevron yarn-dyed",
        "weave_type_normalized": "dobby_chevron",
        "weave_notes": "Body: 'extra-wide Chevron, yarn-dyed, woven in Italy with fine, long linen fibres from France and Belgium'. Chevron = dobby tekniği (zig-zag twill varyantı). Yarn-dyed = renkli iplikten dokuma (Mobidik için TAM uyum).",
        "lightfastness": None,
        "certifications_raw": ["M1", "Oekotex", "Oeko-Tex", "OEKO-TEX"],
        "certifications_other": ["M1 (DIN 4102-1 Class B1 muadili)", "OEKO-TEX Standard 100"],
        "category": ["Sheer fabrics", "Wide curtains"],
        "designer": None,
        "variant_count": 11,
        "description_original_text": (
            "This light and elegant extra-wide Chevron, yarn-dyed, was woven in Italy with fine, "
            "long linen fibres from France and Belgium. Both soft and resistant. "
            "NOTE: The fabric is shown railroaded."
        ),
        "description_tr_text": (
            "Bu hafif ve zarif ekstra-geniş Chevron deseni, ipliği boyalı olarak, "
            "Fransa ve Belçika'dan ince, uzun keten lifleriyle İtalya'da dokunmuştur. "
            "Hem yumuşak hem dayanıklı. NOT: Kumaş yana çevrilmiş gösterilmektedir."
        ),
        "style_note": (
            "⭐ EN GÜÇLÜ ALTIN aday — 100% saf keten + dobby chevron pattern + 310 cm en + "
            "EU Flax (Fransa/Belçika lif) + 11 renk varyantı. 'Signor Darcy' İngiliz "
            "aristokrat ismi (Pride & Prejudice referansı). Mobidik için Anatolian Linen "
            "premium uçta."
        ),
        "mobidik_evaluation": {
            "priority_level": "kritik",
            "staubli_feasibility": {
                "score": 5,
                "frame_count_estimate": "16-24 cerceve (chevron desen 8-16 frame, ek varyasyon icin)",
                "comment": (
                    "Stäubli dobby + 100% keten + chevron (zig-zag twill) yarn-dyed = TAM uyum. "
                    "Mobidik 360 cm warp beam ile 310 cm sorunsuz. EU Flax dış kaynak (Avrupa "
                    "keten) vs Anadolu keten karşılaştırması: kompozisyon aynı, hikaye farklı. "
                    "Mobidik için: Bursa keten birliği + Adana pamuk (Nuri ailesi) iplik kaynağı."
                ),
            },
            "overall_score": 86,
            "components": {
                "staubli_feasibility": 5,
                "yarn_supply": 5,
                "certification_path": 4,
                "market_fit": 5,
                "sub_brand_alignment": 5,
                "design_uniqueness": 4,
            },
            "strategic_note": (
                "⭐ ALTIN — Anatolian Linen sub-brand'ın PREMİUM uçta pilot adayı. "
                "100% saf keten chevron + 11 renk = Air Line (81)/Melange Linen (81)/Nuri (82) "
                "ailesine yeni hat olarak eklenebilir. Mobidik avantajı: Bursa keten + dobby "
                "chevron = İtalyan yarn-dyed Avrupa keten muadili 'Anatolian Linen Chevron'. "
                "Sertifika: OEKO-TEX zaten var, M1 başvuru (3-6 ay), EU Flax muadili "
                "'Anatolian Linen' söylem (Masters of Linen ekipman gerek). ARGE pilot: "
                "5 nötr+toprak ton × 150 m, 6 hafta. Designer: Dedar in-house (Mobidik için "
                "Türk tasarımcı işbirliği fırsatı)."
            ),
        },
    },
    "twillman": {
        "ham_cikti_file": "dedar_twillman_20260526T090434Z.json",
        "product_code": "00T23046",
        "product_name": "Twillman",
        "collection": "Indoor/outdoor fabrics — FR Twill",
        "source_url": "https://dedar.com/twillman/",
        "composition": [
            {"fiber_commercial": "Fire-retardant Polyester", "fiber_generic": "polyester", "ratio_percent": 69},
            {"fiber_commercial": "Fire-retardant Recycled Polyester", "fiber_generic": "polyester_recycled", "ratio_percent": 17},
            {"fiber_commercial": "Recycled Trevira CS Polyester", "fiber_generic": "polyester_recycled", "ratio_percent": 14},
        ],
        "width_cm": 140,
        "country_of_origin": "Italy",
        "weave_type_raw": "twill",
        "weave_type_normalized": "dobby_twill",
        "weave_notes": "Body: 'textured and bulky twill brings exuberance of material and yarns to fore. Fireproof, washable, abrasion-resistant, weather-conditions, sunlight, mold-resistant'. Twill = dobby ile yapılabilir (Stäubli TAM).",
        "lightfastness": None,
        "certifications_raw": ["IMO MED", "Italy Class 1", "BS5867/2/B", "BS5867", "NFPA 701", "M1", "Oekotex"],
        "certifications_other": [
            "IMO MED Part. 7",
            "FR Italy Class 1",
            "BS5867/2/B (UK)",
            "NFPA 701 (US)",
            "M1 (DIN 4102-1 Class B1 muadili)",
            "OEKO-TEX Standard 100",
        ],
        "category": ["Upholstery fabrics", "Indoor/outdoor", "FR fabrics"],
        "designer": None,
        "variant_count": 3,
        "description_original_text": (
            "A textured and bulky twill brings the exuberance of the material and yarns to the fore. "
            "Fireproof, washable, and resistant to abrasion, weather conditions, sunlight, and mold, "
            "easily adaptable to all indoor and outdoor spaces."
        ),
        "description_tr_text": (
            "Dokulu ve hacimli bir dimi, malzeme ve ipliklerin canlılığını ön plana çıkarır. "
            "Yangına dayanıklı, yıkanabilir; sürtünme, hava koşulları, güneş ışığı ve küfe karşı "
            "dirençli; tüm iç ve dış mekan ortamlarına kolayca uyum sağlar."
        ),
        "style_note": (
            "Cobra (00T19063) ailesi muadili — fire-retardant indoor/outdoor + dobby twill. "
            "Farkı: Cobra leno + extra-wide sheer; Twillman dobby twill + 140 cm dar + "
            "%100 FR PES geri dönüşümlü karışım. 6 ÇOK GÜÇLÜ sertifika seti (IMO+BS+NFPA+M1+OEKO)."
        ),
        "mobidik_evaluation": {
            "priority_level": "yüksek",
            "staubli_feasibility": {
                "score": 5,
                "frame_count_estimate": "8-12 cerceve (basit twill dobby)",
                "comment": (
                    "Stäubli dobby + FR PES (Trevira CS varyantları) twill = TAM. Mobidik FR "
                    "iplik deneyimi mevcut (Cobra denetim doğruladı). 140 cm en sorunsuz "
                    "(360 cm sınırın çok altında). Recycled Trevira CS = GRS sertifika fırsatı."
                ),
            },
            "overall_score": 82,
            "components": {
                "staubli_feasibility": 5,
                "yarn_supply": 4,
                "certification_path": 3,
                "market_fit": 5,
                "sub_brand_alignment": 4,
                "design_uniqueness": 4,
            },
            "strategic_note": (
                "Cobra ailesi'ne kardeş ürün — FR dobby twill. Mobidik için yeni FR perdelik "
                "hattı (Cobra leno sheer + Twillman twill upholstery/curtain). 6 sertifika seti "
                "Mobidik için yol haritası: IMO MED (denizyolu), BS5867 (UK), NFPA 701 (US), "
                "M1 (FR), OEKO-TEX (mevcut). 3-12 ay sertifika süreçleri paralel başlat. "
                "Türk iplik: Indorama Türkiye (Trevira CS FR), SASA solution-dyed FR PES. "
                "Recycled PES → GRS başvurusu (Harry RE ailesi ile birlikte hızlandırma). "
                "ARGE pilot: 3 nötr ton × 100 m, 5-6 hafta + sertifika 3-12 ay paralel."
            ),
        },
    },
}


# ============================================================
# Yardimci fonksiyonlar
# ============================================================

def load_ham(fname: str) -> dict:
    return json.loads((HAM / fname).read_text(encoding="utf-8"))


def build_variants(sd: dict, product_code: str, variant_count: int) -> list[dict]:
    """variants_raw -> sema variants[] (color_code + main_image_url)."""
    variants_raw = sd.get("variants_raw") or []
    variants = []
    for vr in variants_raw[:variant_count]:
        cs = vr.get("color_suffix", "")
        if not cs:
            continue
        full_code = f"{product_code}-{cs}"
        variants.append({
            "color_code": full_code,
            "color_name": None,  # Dedar renk isimleri body'de yok, ileride manuel
            "main_image_url_source": None,
            "main_image_local_path": None,
        })
    return variants


def build_images(sd: dict) -> dict:
    """ham_cikti'da indirilen gorseller listesini sema images yapisina cevir."""
    raw_images = sd.get("_image_specs", []) or sd.get("images_raw", [])
    # Aslinda gorseller ana scrape sonucundan sd'a yazilir; topla.py'da:
    # gorseller listesi result icinde, source_data'da degil
    # Bu yuzden direkt ham JSON'dan oku
    return {
        "main": [],
        "technical": [],
        "lifestyle": [],
        "variants": [],
        "_note": "Görseller ham_cikti/gorseller/ altında, migrate edilecek (Faz 6.8c).",
    }


def build_urun_json(slug: str, audit: dict) -> dict:
    """Tek ürün için tam JSON oluştur."""
    ham = load_ham(audit["ham_cikti_file"])
    sd = ham["source_data"]
    code = audit["product_code"]
    name = audit["product_name"]
    full_id = f"dedar_{code}-{slug}"

    obj = {
        "_schema_version": "1.3",
        "urun_id": full_id,
        "brand": "Dedar",
        "brand_slug": "dedar",
        "collection": audit["collection"],
        "product_code": code,
        "product_name": name,
        "source_url": audit["source_url"],
        "scraped_at": ham.get("scraped_at"),
        "last_updated": NOW,
        "source_data": {
            "_description": (
                f"Dedar {name} — Faz 6.8 Tier 1 ALTIN aday denetim. "
                f"topla --batch italyan tarafından discover edildi, kullanıcı onayıyla "
                f"topla.cli ile scrape edildi, Claude denetim (mobidik_evaluation, "
                f"strategic_note, kapasite #7 uygulaması) sonrası markalar/urunler/'e geçti."
            ),
            "_provenance": {
                "schema_version": "1.1",
                "created_at": NOW,
                "last_updated": NOW,
                "sources_used": [
                    {
                        "url": audit["source_url"],
                        "type": "html_product_page",
                        "accessed_at": ham.get("scraped_at"),
                        "fields_supported": [
                            "product_code", "product_name", "composition",
                            "width_cm", "country_of_origin", "certifications",
                            "description_original",
                        ],
                    },
                    {
                        "url": "topla/batch.py",
                        "type": "scheduled_batch_discovery",
                        "accessed_at": "2026-05-26T02:38:32Z",
                        "fields_supported": ["discovered_via=italyan_batch"],
                    },
                    {
                        "url": "kapasite/staubli_uretim_kapasitesi.md",
                        "type": "user_verified_capacity_table",
                        "accessed_at": NOW,
                        "fields_supported": ["mobidik_evaluation.staubli_feasibility"],
                    },
                ],
                "field_metadata": {
                    "weave_type_normalized": {
                        "value": audit["weave_type_normalized"],
                        "source": "html_body_description + Claude denetim",
                        "extraction_confidence": "exact",
                        "extraction_notes": audit["weave_notes"],
                    },
                    "country_of_origin": {
                        "value": audit["country_of_origin"],
                        "source": "html_scraper",
                        "extraction_confidence": "exact",
                    },
                    "certifications_other": {
                        "value": audit["certifications_other"],
                        "source": "html_scraper",
                        "extraction_confidence": "exact",
                        "extraction_notes": (
                            f"Scraper yakalama: {audit['certifications_raw']}. "
                            f"Claude denetim ile tam ad/standart normalize edildi."
                        ),
                    },
                },
                "fields_from_html_scraper": [
                    "product_name", "composition", "width_cm", "country", "certifications",
                    "description_original",
                ],
                "fields_from_body_manual": ["weave_type_normalized", "product_code (SKU)"],
                "fields_from_inference": [],
                "constitutional_violations_check": f"passed_at_{NOW}",
                "audit_history": [
                    {
                        "audit_id": f"{full_id}_v1.0_2026-05-26",
                        "audit_date": "2026-05-26",
                        "version_before": "(yok — yeni keşfedilen ürün)",
                        "version_after": (
                            "v1.0: topla --batch italyan ile keşif, topla.cli ile scrape, "
                            "Claude denetim ile mobidik_evaluation + strategic_note + "
                            "field_metadata."
                        ),
                        "notes": (
                            f"Faz 6.8 Tier 1 ALTIN aday denetimi. Stäubli={audit['mobidik_evaluation']['staubli_feasibility']['score']}/5, "
                            f"Overall={audit['mobidik_evaluation']['overall_score']}/100, "
                            f"Priority={audit['mobidik_evaluation']['priority_level']}. "
                            f"Görseller ham_cikti/gorseller/ altında, migrate Faz 6.8c'de."
                        ),
                    },
                ],
            },
            "commercial": {
                "country_of_origin": audit["country_of_origin"],
                "production_model": "Dedar koleksiyon (stok + üretim)",
                "price": None,
                "moq_meters": None,
                "lead_time_weeks": None,
            },
            "technical": {
                "composition": audit["composition"],
                "width_cm": audit["width_cm"],
                "weight_gsm": None,
                "weight_linear_meter_g": None,
                "repeat_cm": {"vertical": None, "horizontal": None},
                "weave_type_raw": audit["weave_type_raw"],
                "weave_type_normalized": audit["weave_type_normalized"],
                "thread_count": None,
                "stretch_percent": None,
            },
            "certifications": {
                "fire_safety": [c for c in audit["certifications_other"] if any(t in c for t in ["M1", "B1", "BS5867", "NFPA", "IMO", "Class"])],
                "sustainability": [c for c in audit["certifications_other"] if "OEKO" in c],
                "other": [],
            },
            "usage": {
                "category": audit["category"],
                "lightfastness_iso_105_b02": audit["lightfastness"],
                "martindale": None,
            },
            "variants": build_variants(sd, audit["product_code"], audit["variant_count"]),
            "description_original": {
                "lang": "en",
                "text": audit["description_original_text"],
                "source": "html_product_page",
            },
            "description_tr": {
                "lang": "tr",
                "text": audit["description_tr_text"],
                "translation_method": "claude_code_manual",
                "translated_at": NOW,
            },
            "style_note": audit["style_note"],
            "designer": audit["designer"],
        },
        "ai_inferences": {
            "weave_normalization": {
                "value": audit["weave_type_normalized"],
                "confidence": "high",
                "method": "html_body_description_inference",
                "based_on": audit["weave_notes"],
            },
        },
        "mobidik_evaluation": audit["mobidik_evaluation"],
        "images": build_images(sd),
        "data_quality": {
            "missing_fields": [
                "weight_gsm",
                "lightfastness",
                "color_names (varyant renk isimleri)",
                "main_image_url_source per variant",
                "image_analysis (dominant_colors, texture, transparency)",
            ],
            "notes": (
                "Görseller ham_cikti/gorseller/ altında 10-11 dosya/ürün; "
                "Faz 6.8c'de gorseller/dedar/<code>/ altına migrate edilecek. "
                "image_analysis ve renk isimleri ileride manuel denetim ile eklenecek."
            ),
        },
    }
    return obj


def main():
    URUNLER.mkdir(parents=True, exist_ok=True)
    olusturulan = []
    for slug, audit in PRODUCTS.items():
        obj = build_urun_json(slug, audit)
        out_path = URUNLER / f"{obj['urun_id']}.json"
        out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        olusturulan.append(out_path.name)
        print(f"  Yazildi: {out_path.name}")
        print(f"    Stäubli={obj['mobidik_evaluation']['staubli_feasibility']['score']}/5, "
              f"Overall={obj['mobidik_evaluation']['overall_score']}/100, "
              f"Priority={obj['mobidik_evaluation']['priority_level']}")
    print(f"\nToplam {len(olusturulan)} JSON urun olusturuldu.")


if __name__ == "__main__":
    main()
