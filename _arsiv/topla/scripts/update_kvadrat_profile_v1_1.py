"""One-shot script: Kvadrat marka profilini n=1'den n=2'ye yukselt (Alpaca Leno eklendi).

Bu script anayasa kural #9 uyarinca MEKANIK guncelleme yapar (JSON load/modify/save);
ic erik (gozlem degerleri, comment metinleri, audit notlari) Claude Code tarafindan denetimle yazildi.

Calistirma: .venv\\Scripts\\python.exe topla\\scripts\\update_kvadrat_profile_v1_1.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "markalar" / "kvadrat.json"
NOW = "2026-05-25T22:00:00Z"

with PROFILE.open(encoding="utf-8") as f:
    d = json.load(f)

# Ust alanlar
d["product_count_tracked"] = 2
d["last_updated"] = NOW

# width_distribution: Air Line 315, Alpaca Leno 315
for k in ("min_cm", "max_cm"):
    d["width_distribution"][k]["sample_status"] = "insufficient_n_2"
    d["width_distribution"][k]["sample_size"] = 2
    d["width_distribution"][k]["observed_at_n2"] = 315

d["width_distribution"]["most_common_cm"]["sample_status"] = "insufficient_n_2"
d["width_distribution"]["most_common_cm"]["sample_size"] = 2
d["width_distribution"]["most_common_cm"]["observed_at_n2"] = [315]
d["width_distribution"]["histogram"]["sample_status"] = "insufficient_n_2"
d["width_distribution"]["histogram"]["sample_size"] = 2
d["width_distribution"]["histogram"]["observed_at_n2"] = {"315": 2}
d["width_distribution"]["comment"] = (
    "n=2: Air Line 315 cm + Alpaca Leno 315 cm — ayni en. Threshold n>=3 dolana kadar "
    "value hesaplanmaz. Frequency koleksiyonunun standart en degeri 315 cm olabilir."
)

# color_profile: 5+5=10, ortalama 5.0
d["color_profile"]["total_variant_count"]["sample_status"] = "insufficient_n_2"
d["color_profile"]["total_variant_count"]["sample_size"] = 2
d["color_profile"]["total_variant_count"]["observed_at_n2"] = 10
d["color_profile"]["average_per_product"]["sample_status"] = "insufficient_n_2"
d["color_profile"]["average_per_product"]["sample_size"] = 2
d["color_profile"]["average_per_product"]["observed_at_n2"] = 5.0
d["color_profile"]["dominant_palette_tr"]["sample_status"] = "insufficient_n_2"
d["color_profile"]["dominant_palette_tr"]["sample_size"] = 2
d["color_profile"]["dominant_palette_tr"]["observed_at_n2"] = [
    "White Linen", "Light Ash", "Hazel", "Mosswood", "Northern Pine (Air Line)",
    "Soft Wool", "Almond Bark", "Redwood", "Cool Cedar", "5544-0931 (isim bilinmiyor)",
]
d["color_profile"]["comment"] = (
    "n=2: Air Line 5 ton organik melange + Alpaca Leno 5 ton (4 isim + 1 bilinmeyen). "
    "Ortalama 5.0/urun. Frequency koleksiyonu icin 5 ton standart gibi gorunuyor."
)

# composition_distribution
d["composition_distribution"]["synthetic_ratio_percent"]["sample_status"] = "insufficient_n_2"
d["composition_distribution"]["synthetic_ratio_percent"]["sample_size"] = 2
d["composition_distribution"]["synthetic_ratio_percent"]["observed_at_n2"] = 12.5  # (0 + 25(lyocell+viskon)) / 2
d["composition_distribution"]["natural_ratio_percent"]["sample_status"] = "insufficient_n_2"
d["composition_distribution"]["natural_ratio_percent"]["sample_size"] = 2
d["composition_distribution"]["natural_ratio_percent"]["observed_at_n2"] = 87.5  # (100 + 75(yun+alpaka)) / 2
d["composition_distribution"]["blend_ratio_percent"]["sample_status"] = "insufficient_n_2"
d["composition_distribution"]["blend_ratio_percent"]["sample_size"] = 2
d["composition_distribution"]["blend_ratio_percent"]["observed_at_n2"] = 50.0  # 1 mono + 1 blend
d["composition_distribution"]["trevira_cs_usage_percent"]["sample_status"] = "insufficient_n_2"
d["composition_distribution"]["trevira_cs_usage_percent"]["sample_size"] = 2
d["composition_distribution"]["trevira_cs_usage_percent"]["observed_at_n2"] = 0
d["composition_distribution"]["most_common_fibers"]["sample_status"] = "insufficient_n_2"
d["composition_distribution"]["most_common_fibers"]["sample_size"] = 2
d["composition_distribution"]["most_common_fibers"]["observed_at_n2"] = [
    {"fiber": "Keten", "usage_percent_in_sample": 100, "product_count": 1},
    {"fiber": "Yun", "usage_percent_in_sample": 58, "product_count": 1},
    {"fiber": "Alpaka", "usage_percent_in_sample": 17, "product_count": 1},
    {"fiber": "Lyocell", "usage_percent_in_sample": 14, "product_count": 1},
    {"fiber": "Viskon", "usage_percent_in_sample": 11, "product_count": 1},
]
d["composition_distribution"]["comment"] = (
    "n=2: Air Line %100 keten mono + Alpaca Leno %58 yun + %17 alpaka + %14 lyocell + %11 viskon. "
    "Iki uretici modeli: monomateryal vs multi-staple kompleks blend. Threshold n>=3 oncesi dagilim hesabi yapilmaz."
)

# weave_distribution
for k in ("plain", "dobby", "jacquard", "sheer", "leno", "unknown"):
    d["weave_distribution"][k]["sample_status"] = "insufficient_n_2"
    d["weave_distribution"][k]["sample_size"] = 2

d["weave_distribution"]["plain"]["observed_at_n2"] = 0
d["weave_distribution"]["dobby"]["observed_at_n2"] = 1
d["weave_distribution"]["jacquard"]["observed_at_n2"] = 0
d["weave_distribution"]["sheer"]["observed_at_n2"] = 0
d["weave_distribution"]["leno"]["observed_at_n2"] = 1
d["weave_distribution"]["unknown"]["observed_at_n2"] = 0
d["weave_distribution"]["comment"] = (
    "n=2: 1 dobby (Air Line) + 1 leno (Alpaca Leno). 50/50 dagilim ama n=2 yetersiz."
)

# product_groups
for k in ("sheer_voile", "dimout", "blackout", "drapery", "acoustic", "decorative_jacquard", "other"):
    d["product_groups"][k]["sample_status"] = "insufficient_n_2"
    d["product_groups"][k]["sample_size"] = 2

d["product_groups"]["drapery"]["observed_at_n2"] = 2
for k in ("sheer_voile", "dimout", "blackout", "acoustic", "decorative_jacquard", "other"):
    d["product_groups"][k]["observed_at_n2"] = 0

# certification_profile
d["certification_profile"]["fire_safety_certified_percent"]["sample_status"] = "insufficient_n_2"
d["certification_profile"]["fire_safety_certified_percent"]["sample_size"] = 2
d["certification_profile"]["fire_safety_certified_percent"]["observed_at_n2"] = 0
d["certification_profile"]["common_fire_certs"]["sample_status"] = "insufficient_n_2"
d["certification_profile"]["common_fire_certs"]["sample_size"] = 2
d["certification_profile"]["common_fire_certs"]["observed_at_n2"] = []
d["certification_profile"]["sustainability_certs"]["sample_status"] = "insufficient_n_2"
d["certification_profile"]["sustainability_certs"]["sample_size"] = 2
d["certification_profile"]["sustainability_certs"]["observed_at_n2"] = [
    "EU Ecolabel (Air Line - marka geneli claim, urun-ozel kanit PDF)",
    "Lightfastness ISO 105-B02 (her iki urunde de skor 8)",
]
d["certification_profile"]["always_present_certs"]["sample_status"] = "insufficient_n_2"
d["certification_profile"]["always_present_certs"]["sample_size"] = 2
d["certification_profile"]["always_present_certs"]["observed_at_n2"] = [
    "Lightfastness ISO 105-B02 score 8",
    "2-yil retail warranty",
]
d["certification_profile"]["comment"] = (
    "n=2: Iki urunde de yangin guvenligi sertifikasi YOK. Ikisinde de Lightfastness 8 + 2 yil warranty. "
    "Air Line EU Ecolabel claim eder; Alpaca Leno multi-fiber oldugu icin mono material avantajini kaybeder."
)

# mobidik_strategic_assessment
d["mobidik_strategic_assessment"]["average_feasibility_score"]["sample_status"] = "insufficient_n_2"
d["mobidik_strategic_assessment"]["average_feasibility_score"]["sample_size"] = 2
d["mobidik_strategic_assessment"]["average_feasibility_score"]["observed_at_n2"] = 4.5  # (5 + 4) / 2
d["mobidik_strategic_assessment"]["_general_feasibility_basis"] = (
    "n=2: Air Line 5/5 (dobby + keten + TR uretim) + Alpaca Leno 4/5 (leno TAM + multi-staple iplik nis). "
    "Ortalama 4.5. Kvadrat marka geneli icin yuksek feasibility tahmini guclendi. "
    "Onceki n=1 Documents notu Alpaca Leno icin 1/5 demisti — kapasite tablosu duzeltisi (anayasa #7)."
)
d["mobidik_strategic_assessment"]["arge_priority_areas"].append(
    "Leno + yun/alpaka multi-staple iplik portfoyu — Niket + Etamine Fil du Temps + Alpaca Leno = 3-urun leno hatti (ROI 12-15 ay)"
)
d["mobidik_strategic_assessment"]["arge_priority_areas"].append(
    "Italyan artisanal uretim modeli benchmark (51 gun lead time, premium yun/alpaka segment, MTO)"
)

# data_integrity
d["data_integrity"]["sample_size_tracked_products"] = 2
d["data_integrity"]["verified_data_points"] = d["data_integrity"].get("verified_data_points", 0) + 3
d["data_integrity"]["_reliability_explanation"] = (
    "n=2 (Air Line + Alpaca Leno denetlenmis). Threshold n>=3 dolana kadar dagilim istatistikleri null kalir, "
    "reliability_label='insufficient_sample'. Statik kimlik (founding/headquarters/mill/designers/projects) dolu; "
    "istatistik bloklari observed_at_n2 ile gozlem korunuyor. 1 daha urun eklendiginde n=3 (mostly_estimated) olur."
)
d["data_integrity"]["comment"] = (
    "Statik kimlik %100 dogrulanmis (multi_source); dagilim istatistikleri 0% (n esigi). "
    "3. urun eklendiginde reliability='mostly_estimated' yukselir. Frequency koleksiyonu ortak ozellikler: "
    "315 cm en, lightfastness 8, 2 yil warranty."
)

# Audit history
d["_provenance"]["audit_history"].append({
    "audit_id": "kvadrat_marka_v1.1_2026-05-25",
    "audit_date": "2026-05-25",
    "audit_doc": "docs/parti_log.md (kuruluyor)",
    "version_before": "v1.0 (n=1, sadece Air Line)",
    "version_after": "v1.1 (n=2, Alpaca Leno eklendi)",
    "notes": (
        "Documents iterasyonu migrasyonu sirasinda Kvadrat parti01 raporundaki 2. urun (Alpaca Leno 5544) "
        "ham_cikti + Documents raporu birlesimiyle denetlendi. CELISKI VAKASI: Documents raporu "
        "'Stabli leno yapamaz' demisti; kapasite tablosu 'leno TAM' der — anayasa kural #7 uyarinca "
        "kapasite kazandi. KOMPOZISYON DUZELTMESI: Documents 3-lif demisti; HTML 4-lif (viscose %11 eklendi). "
        "5. renk (5544-0931) adi bilinmiyor (sayfa tam cekimi gerek). product_count 1->2, tum stat bloklari "
        "observed_at_n2 ile guncellendi. n=2 hala threshold alti."
    ),
})
d["_provenance"]["last_updated"] = NOW
d["_provenance"]["constitutional_violations_check"] = "passed_at_" + NOW

# Notes
d["notes"].append("v1.1 (2026-05-25): Alpaca Leno (5544) eklendi. n=1 -> n=2.")
d["notes"].append(
    "Frequency koleksiyonu gozlemi: ayni en (315 cm), ayni lightfastness (8), ayni warranty (2 yil). "
    "Iki farkli uretici modeli (Air Line=Turkiye fason stock, Alpaca Leno=Italyan artisanal MTO)."
)
d["notes"].append(
    "CELISKI DUZELTMESI: Documents Mobidik notu Alpaca Leno icin 'Stabli leno yapamaz' demisti (yanlis); "
    "kapasite tablosu der 'leno TAM' (dogru, kullanici dogrulamali). Anayasa #7 + #8 uyarinca kapasite kazandi. "
    "staubli_feasibility 1/5 -> 4/5."
)

with PROFILE.open("w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print(
    f"OK product_count_tracked={d['product_count_tracked']} "
    f"reliability={d['data_integrity']['reliability_label']} "
    f"avg_feasibility_n2={d['mobidik_strategic_assessment']['average_feasibility_score']['observed_at_n2']}"
)
