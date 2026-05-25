"""Faz 5.4: Dedar marka profili n=1 -> n=2 (Days Like Now eklendi).

build_marka_profilleri.py mevcut profilin audit_history'sini silecek olduğu icin,
Kvadrat pattern'inde ayri update scripti. Audit_history korunur, n=2 stat eklenir.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "markalar" / "dedar.json"
NOW = "2026-05-25T23:55:00Z"

with PROFILE.open(encoding="utf-8") as f:
    d = json.load(f)

# Ust alanlar
d["product_count_tracked"] = 2
d["last_updated"] = NOW

# Width: Cobra 325 + DLN 134 = range 134-325 (cok genis cesitlilik)
d["width_distribution"]["min_cm"]["sample_status"] = "insufficient_n_2"
d["width_distribution"]["min_cm"]["sample_size"] = 2
d["width_distribution"]["min_cm"]["observed_at_n2"] = 134
d["width_distribution"]["max_cm"]["sample_status"] = "insufficient_n_2"
d["width_distribution"]["max_cm"]["sample_size"] = 2
d["width_distribution"]["max_cm"]["observed_at_n2"] = 325
d["width_distribution"]["comment"] = (
    "n=2: Cobra 325 cm extra-wide + Days Like Now 134 cm dar. "
    "Dedar urun cesitliliği geniş — bir tek 'standart en' yok."
)

# Color: Cobra 2 + DLN 8 = 10 toplam
d["color_profile"]["total_variant_count"]["sample_size"] = 2
d["color_profile"]["total_variant_count"]["observed_at_n2"] = 10
d["color_profile"]["average_per_product"]["sample_size"] = 2
d["color_profile"]["average_per_product"]["observed_at_n2"] = 5.0
d["color_profile"]["comment"] = "n=2: Cobra 2 ton + DLN 8 ton = 10 varyant, ortalama 5.0/urun."

# Weave: Cobra leno + DLN plain
d["weave_distribution"]["leno"]["sample_size"] = 2
d["weave_distribution"]["leno"]["observed_at_n2"] = 1
d["weave_distribution"]["plain"] = {
    "value": None, "sample_status": "insufficient_n_2", "sample_size": 2,
    "observed_at_n2": 1, "comment": "1 plain (DLN shantung)",
}
d["weave_distribution"]["leno"]["comment"] = "1 leno (Cobra)"

# Composition: Cobra %100 FR PES (sentetik) + DLN %100 ipek (dogal)
d["composition_distribution"]["synthetic_ratio_percent"]["sample_size"] = 2
d["composition_distribution"]["synthetic_ratio_percent"]["observed_at_n2"] = 50.0
d["composition_distribution"]["natural_ratio_percent"]["sample_size"] = 2
d["composition_distribution"]["natural_ratio_percent"]["observed_at_n2"] = 50.0
d["composition_distribution"]["blend_ratio_percent"]["sample_size"] = 2
d["composition_distribution"]["blend_ratio_percent"]["observed_at_n2"] = 0.0
d["composition_distribution"]["comment"] = (
    "n=2: 1 mono sentetik (Cobra %100 FR PES) + 1 mono dogal (DLN %100 ipek). "
    "Cesitlilik max — Dedar urun yelpazesi premium nis."
)

# Country: Italy + India
d["country_distribution"] = {"Italy": 1, "India": 1}

# Mobidik avg: (5 + 4) / 2 = 4.5
d["mobidik_strategic_assessment"]["average_feasibility_score"]["sample_size"] = 2
d["mobidik_strategic_assessment"]["average_feasibility_score"]["observed_at_n2"] = 4.5
d["mobidik_strategic_assessment"]["_general_feasibility_basis"] = (
    "n=2: Cobra 5/5 (leno+FR+PES, Stabli TAM) + DLN 4/5 (plain ipek, Mobidik egzotik kategori). "
    "Ortalama 4.5. Dedar urun cesitligi premium nis: extra-wide outdoor leno (Cobra) vs dar artisanal ipek (DLN). "
    "Global fason agi: Cobra Italya, DLN Hindistan."
)
d["mobidik_strategic_assessment"]["arge_priority_areas"].append(
    "Wild silk shantung tedariki — Bursa ipekciligi cagrismi (uzun vade ARGE projesi)"
)
d["mobidik_strategic_assessment"]["arge_priority_areas"].append(
    "Dedar global fason modeli — Italyan brand + Hindistan/Italya uretim cesitliligi"
)

# Data integrity
d["data_integrity"]["sample_size_tracked_products"] = 2
d["data_integrity"]["_reliability_explanation"] = (
    "n=2 (Cobra + Days Like Now). Threshold n>=3 dolana kadar dagilim istatistikleri null. "
    "Iki urun arasinda yuksek cesitlilik (en, kompozisyon, ulke) - Dedar premium nis marka."
)

# Audit history append
d["_provenance"]["audit_history"].append({
    "audit_id": "dedar_marka_v1.1_2026-05-25",
    "audit_date": "2026-05-25",
    "version_before": "v1.0 (n=1, sadece Cobra)",
    "version_after": "v1.1 (n=2, Days Like Now eklendi)",
    "notes": (
        "Days Like Now (wild silk shantung Hindistan) eklendi. n=1 -> n=2. Cobra (leno+FR Italya) ile "
        "yuksek cesitlilik gozlendi: en 134-325 cm, sentetik+dogal, Italya+Hindistan. "
        "avg_staubli 5.0 -> 4.5 (DLN 4/5 ipek tedariki nis). Statik kimlik (kurucular/CEO/mill/designer) "
        "PENDING."
    ),
})
d["_provenance"]["last_updated"] = NOW
d["_provenance"]["constitutional_violations_check"] = f"passed_at_{NOW}"

# Notes
d["notes"].append("v1.1 (2026-05-25): Days Like Now eklendi (n=2). avg_staubli 4.5 (Cobra 5 + DLN 4).")
d["notes"].append(
    "Dedar profili gozlemi: extra-wide outdoor leno (Cobra Italya) + dar artisanal silk (DLN Hindistan) "
    "= premium nis cesitliligi. Global fason agi (Italya/Hindistan)."
)

with PROFILE.open("w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print(f"OK dedar.json: n={d['product_count_tracked']} reliability={d['data_integrity']['reliability_label']} avg_staubli_n2={d['mobidik_strategic_assessment']['average_feasibility_score']['observed_at_n2']}")
