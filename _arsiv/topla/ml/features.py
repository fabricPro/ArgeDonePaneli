"""Faz 7.2: Tabular feature encoder.

Ürün JSON'undan ML için sayısal feature vektörü çıkar.

Feature sırası (sabit, model versiyonu ile bağlı):
  0: width_cm (float, 0-360 normalize)
  1: weight_gsm (float, 0-500 normalize, null=0)
  2: variant_count (int, 1-20 normalize)
  3: certification_count (int)
  4: staubli_score (1-5)
  5: overall_score (0-100 normalize)
  6: has_jakar (0/1) — kapasite dışı
  7: has_metallic (0/1) — kapasite dışı
  8: linen_ratio (0-1)
  9: cotton_ratio (0-1)
 10: polyester_ratio (0-1)
 11: wool_ratio (0-1)
 12: silk_ratio (0-1)
 13: viscose_ratio (0-1)
 14: synthetic_ratio (0-1) — toplam sentetik
 15: weave_dobby (0/1)
 16: weave_leno (0/1)
 17: weave_twill (0/1)
 18: weave_plain (0/1)
 19: country_italy (0/1)
 20: country_germany (0/1)
 21: country_denmark (0/1)
 22: country_turkey (0/1)
 23: has_fr_cert (0/1) — IMO MED, BS5867, NFPA, M1
 24: has_oekotex (0/1)
 25: has_grs (0/1)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

FEATURE_NAMES: list[str] = [
    "width_cm_norm", "weight_gsm_norm", "variant_count_norm", "certification_count",
    "staubli_score", "overall_score_norm",
    "has_jakar", "has_metallic",
    "linen_ratio", "cotton_ratio", "polyester_ratio", "wool_ratio", "silk_ratio", "viscose_ratio",
    "synthetic_ratio_total",
    "weave_dobby", "weave_leno", "weave_twill", "weave_plain",
    "country_italy", "country_germany", "country_denmark", "country_turkey",
    "has_fr_cert", "has_oekotex", "has_grs",
]
N_FEATURES = len(FEATURE_NAMES)


SYNTHETIC_FIBERS = {"polyester", "polyester_recycled", "polyamide", "acrylic", "nylon"}
NATURAL_FIBERS = {"linen", "cotton", "wool", "silk", "viscose", "alpaca", "hemp"}


def _fiber_ratios(composition: list[dict]) -> dict[str, float]:
    """Kompozisyondan fiber bazlı oran çıkar (0-1 normalize)."""
    totals: dict[str, float] = {
        "linen": 0.0, "cotton": 0.0, "polyester": 0.0, "wool": 0.0,
        "silk": 0.0, "viscose": 0.0, "synthetic_total": 0.0,
    }
    for c in composition or []:
        fiber = (c.get("fiber_generic") or "").lower()
        ratio = c.get("ratio_percent") or 0
        ratio_norm = ratio / 100.0

        if fiber == "linen":
            totals["linen"] += ratio_norm
        elif fiber == "cotton":
            totals["cotton"] += ratio_norm
        elif fiber in ("polyester", "polyester_recycled"):
            totals["polyester"] += ratio_norm
        elif fiber == "wool":
            totals["wool"] += ratio_norm
        elif fiber == "silk":
            totals["silk"] += ratio_norm
        elif fiber == "viscose":
            totals["viscose"] += ratio_norm

        if fiber in SYNTHETIC_FIBERS:
            totals["synthetic_total"] += ratio_norm

    return totals


def _weave_flags(weave: str | None) -> dict[str, int]:
    w = (weave or "").lower()
    return {
        "weave_dobby": 1 if "dobby" in w else 0,
        "weave_leno": 1 if "leno" in w else 0,
        "weave_twill": 1 if "twill" in w else 0,
        "weave_plain": 1 if w == "plain" or "plain" in w else 0,
    }


def _country_flags(country: str | None) -> dict[str, int]:
    c = (country or "").lower()
    return {
        "country_italy": 1 if c == "italy" else 0,
        "country_germany": 1 if c == "germany" else 0,
        "country_denmark": 1 if c == "denmark" else 0,
        "country_turkey": 1 if c == "turkey" else 0,
    }


def _certification_flags(certifications: dict) -> dict[str, int]:
    """certifications dict'inden flag çıkar."""
    fire = certifications.get("fire_safety") or []
    sust = certifications.get("sustainability") or []
    other = certifications.get("other") or []
    all_certs = " ".join(fire + sust + other).lower()

    return {
        "has_fr_cert": 1 if any(t in all_certs for t in ("imo", "bs5867", "nfpa", "m1", "b1", "class 1")) else 0,
        "has_oekotex": 1 if "oeko" in all_certs else 0,
        "has_grs": 1 if "grs" in all_certs else 0,
    }


def _has_blacklist_pattern(d: dict) -> dict[str, int]:
    """Slug/composition/weave'de jakar/metallic gibi kapasite-dışı pattern var mı?"""
    slug = (d.get("urun_id") or "").lower()
    weave = (d.get("source_data", {}).get("technical", {}).get("weave_type_raw") or "").lower()
    weave_norm = (d.get("source_data", {}).get("technical", {}).get("weave_type_normalized") or "").lower()
    composition = d.get("source_data", {}).get("technical", {}).get("composition") or []
    comp_str = " ".join((c.get("fiber_commercial") or "").lower() for c in composition)

    has_jakar = 1 if any(t in (slug + weave + weave_norm) for t in ("jacquard", "jakar")) else 0
    has_metallic = 1 if any(t in (slug + comp_str + weave_norm) for t in ("metallic", "metal", "lurex", "foil", "gold")) else 0

    return {"has_jakar": has_jakar, "has_metallic": has_metallic}


def extract_features(d: dict) -> np.ndarray:
    """Ürün JSON dict'inden N_FEATURES boyutlu vektör çıkar."""
    sd = d.get("source_data", {})
    tech = sd.get("technical", {})
    commercial = sd.get("commercial", {})
    me = d.get("mobidik_evaluation", {})

    # Sayısal
    width = (tech.get("width_cm") or 0) / 360.0  # Mobidik max
    weight = (tech.get("weight_gsm") or 0) / 500.0
    variant_count = min(len(sd.get("variants") or []), 20) / 20.0
    cert_obj = sd.get("certifications", {}) or {}
    cert_count = sum(len(cert_obj.get(k) or []) for k in ("fire_safety", "sustainability", "other"))
    staubli = (me.get("staubli_feasibility", {}) or {}).get("score") or 0
    overall = (me.get("overall_score") or 0) / 100.0

    # Pattern flags
    bl = _has_blacklist_pattern(d)

    # Fiber ratios
    fr = _fiber_ratios(tech.get("composition") or [])

    # Weave flags
    weave_norm = tech.get("weave_type_normalized") or tech.get("weave_type_raw")
    wf = _weave_flags(weave_norm)

    # Country flags
    cf = _country_flags(commercial.get("country_of_origin"))

    # Cert flags
    cef = _certification_flags(cert_obj)

    features = [
        width, weight, variant_count, cert_count,
        staubli, overall,
        bl["has_jakar"], bl["has_metallic"],
        fr["linen"], fr["cotton"], fr["polyester"], fr["wool"], fr["silk"], fr["viscose"],
        fr["synthetic_total"],
        wf["weave_dobby"], wf["weave_leno"], wf["weave_twill"], wf["weave_plain"],
        cf["country_italy"], cf["country_germany"], cf["country_denmark"], cf["country_turkey"],
        cef["has_fr_cert"], cef["has_oekotex"], cef["has_grs"],
    ]

    return np.array(features, dtype=np.float32)


def extract_features_from_path(json_path: Path) -> tuple[str, np.ndarray]:
    """JSON dosya yolu → (urun_id, features)."""
    d = json.loads(Path(json_path).read_text(encoding="utf-8"))
    return d["urun_id"], extract_features(d)
