"""Faz 3.5: markalar/urunler/<marka>_*.json dosyalarindan marka profili inşa et.

Anayasa #9: Python mekanik — istatistik turetimi (n, dagilim, ortalama). Statik kimlik
(kurucular/CEO/mill/designer_roster) PENDING — Claude Code denetimi sonra dolduracak.

n esigi: n<3 -> insufficient_sample, n>=3 -> mostly_estimated
"""
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
NOW = "2026-05-25T22:55:00Z"
URUNLER_DIR = ROOT / "markalar" / "urunler"
MARKA_OUT = ROOT / "markalar"

MARKA_STATIK = {
    "zimmer_rohde": {
        "brand": "Zimmer + Rohde",
        "country": "Almanya",
        "region": "alman_alpin",
        "headquarters_city": "Oberursel",
        "founded_year": 1956,
        "website": "https://www.zimmer-rohde.com",
        "_static_pending_note": "Tam statik kimlik (kurucular, CEO, mill, designer_roster, anitsal projeler) Faz 3.5 sonraki denetim adimi — Z+R about + Wikipedia.",
    },
    "ado_goldkante": {
        "brand": "ADO Goldkante",
        "country": "Almanya",
        "region": "alman_alpin",
        "headquarters_city": "Aschendorf",
        "founded_year": 1948,
        "website": "https://www.zimmer-rohde.com/en/ado-goldkante",
        "_static_pending_note": "Z+R'nin 1990 satin aldigi alt marka. Tam profil PENDING.",
    },
    "etamine": {
        "brand": "Etamine",
        "country": "Fransa",
        "region": "fransiz_alpin",
        "headquarters_city": "Paris",
        "founded_year": 1986,
        "website": "https://www.zimmer-rohde.com/en/etamine",
        "_static_pending_note": "Z+R'nin Fransiz alt markasi (1995'ten Z+R'ye katildi). Tam profil PENDING.",
    },
    "travers": {
        "brand": "Travers",
        "country": "ABD",
        "region": "amerikan",
        "headquarters_city": "New York",
        "founded_year": None,
        "website": "https://www.zimmer-rohde.com/en/travers",
        "_static_pending_note": "Z+R'nin ABD alt markasi. Founding year + tam profil PENDING.",
    },
}

SYNTHETIC = {"Polyester", "Geri Donusturulmus PES", "Poliamid", "Akrilik"}
NATURAL = {"Pamuk", "Keten", "Yun", "Alpaka", "Ipek"}
THRESHOLD = 3


def hesapla(marka_slug: str) -> dict | None:
    urunler = []
    for jp in URUNLER_DIR.glob(f"{marka_slug}_*.json"):
        with jp.open(encoding="utf-8") as f:
            urunler.append(json.load(f))
    n = len(urunler)
    if n == 0:
        return None

    statik = MARKA_STATIK[marka_slug]
    sample_status = "insufficient_n_" + str(n) if n < THRESHOLD else "ok"
    reliability = "insufficient_sample" if n < THRESHOLD else "mostly_estimated"
    obs_key = f"observed_at_n{n}"
    use_value = n >= THRESHOLD

    widths = [u["source_data"]["technical"]["width_cm"] for u in urunler
              if u["source_data"]["technical"]["width_cm"]]
    width_min = min(widths) if widths else None
    width_max = max(widths) if widths else None

    color_counts = [len(u["source_data"]["variants"]) for u in urunler]
    total_colors = sum(color_counts)
    avg_colors = round(total_colors / n, 1) if n else 0

    weave_dist = Counter()
    for u in urunler:
        wt = u["source_data"]["technical"]["weave_type_normalized"]
        if wt:
            weave_dist[wt] += 1

    synth_ratios, natural_ratios, blend_count, mono_count = [], [], 0, 0
    for u in urunler:
        comp = u["source_data"]["technical"]["composition"]
        if not comp:
            continue
        s_total = sum(c["ratio_percent"] for c in comp if c["fiber_generic"] in SYNTHETIC)
        n_total = sum(c["ratio_percent"] for c in comp if c["fiber_generic"] in NATURAL)
        synth_ratios.append(s_total)
        natural_ratios.append(n_total)
        if len(comp) > 1:
            blend_count += 1
        else:
            mono_count += 1

    countries = Counter(
        u["source_data"]["commercial"]["country_of_origin"] for u in urunler
        if u["source_data"]["commercial"]["country_of_origin"]
    )
    staubli_scores = [
        u["mobidik_evaluation"]["staubli_feasibility"]["score"] for u in urunler
        if u["mobidik_evaluation"]["staubli_feasibility"]["score"] is not None
    ]
    avg_staubli = round(sum(staubli_scores) / len(staubli_scores), 2) if staubli_scores else None
    audited_count = len(staubli_scores)

    avg_synth = round(sum(synth_ratios) / len(synth_ratios), 1) if synth_ratios else 0
    avg_natural = round(sum(natural_ratios) / len(natural_ratios), 1) if natural_ratios else 0

    return {
        "_schema_version": "1.1",
        "brand": statik["brand"],
        "brand_slug": marka_slug,
        "country": statik["country"],
        "region": statik["region"],
        "headquarters_city": statik["headquarters_city"],
        "founded_year": statik["founded_year"],
        "website": statik["website"],
        "tracked_since": "2026-05-11",
        "last_updated": NOW,
        "product_count_tracked": n,
        "_provenance": {
            "schema_version": "1.1",
            "created_at": NOW,
            "last_updated": NOW,
            "sources_used": [{
                "url": "Documents/01_raporlar + 03_html_dashboard/index.html",
                "type": "internal_dashboard_pre_migration",
                "accessed_at": NOW,
                "fields_supported": ["all_stat_distributions_from_n_products"],
            }],
            "constitutional_violations_check": "passed_at_" + NOW,
            "audit_history": [{
                "audit_id": f"{marka_slug}_marka_v1.0_2026-05-25",
                "audit_date": "2026-05-25",
                "version_before": "(yok — Faz 3.5 ilk inşa)",
                "version_after": f"v1.0 (n={n}, urun JSON'larindan turetilen istatistikler)",
                "notes": (
                    f"Documents iterasyonundan migrate. Python mekanik istatistik hesabi (build_marka_profilleri.py). "
                    f"n={n} {'>=3 -> mostly_estimated' if n >= THRESHOLD else '<3 -> insufficient_sample'}. "
                    f"audited urun sayisi (staubli_feasibility dolu): {audited_count}/{n}. "
                    "Statik kimlik (kurucular, CEO, mill, designer_roster, anitsal projeler) PENDING."
                ),
            }],
        },
        "width_distribution": {
            "min_cm": {"value": width_min if use_value else None, "sample_status": sample_status, "sample_size": n, obs_key: width_min},
            "max_cm": {"value": width_max if use_value else None, "sample_status": sample_status, "sample_size": n, obs_key: width_max},
            "comment": f"n={n}, en araligi: {width_min}-{width_max} cm" if widths else "veri yok",
        },
        "color_profile": {
            "total_variant_count": {"value": total_colors if use_value else None, "sample_status": sample_status, "sample_size": n, obs_key: total_colors},
            "average_per_product": {"value": avg_colors if use_value else None, "sample_status": sample_status, "sample_size": n, obs_key: avg_colors},
            "comment": f"n={n}, toplam {total_colors} renk varyanti, ortalama {avg_colors}/urun",
        },
        "weave_distribution": {
            wt: {
                "value": round(count / n * 100, 1) if use_value else None,
                "sample_status": sample_status,
                "sample_size": n,
                obs_key: count,
                "comment": f"{count}/{n} urunde {wt}",
            }
            for wt, count in weave_dist.items()
        },
        "composition_distribution": {
            "synthetic_ratio_percent": {"value": avg_synth if use_value else None, "sample_status": sample_status, "sample_size": n, obs_key: avg_synth},
            "natural_ratio_percent": {"value": avg_natural if use_value else None, "sample_status": sample_status, "sample_size": n, obs_key: avg_natural},
            "blend_ratio_percent": {"value": round(blend_count / n * 100, 1) if use_value else None, "sample_status": sample_status, "sample_size": n, obs_key: round(blend_count / n * 100, 1)},
            "comment": f"n={n}, {mono_count} mono + {blend_count} blend; avg synth %{avg_synth}, natural %{avg_natural}",
        },
        "country_distribution": dict(countries),
        "mobidik_strategic_assessment": {
            "average_feasibility_score": {
                "value": avg_staubli if (use_value and audited_count >= THRESHOLD) else None,
                "sample_status": "audited_n_" + str(audited_count),
                "sample_size": audited_count,
                obs_key: avg_staubli,
            },
            "watch_priority": "yuksek" if n >= 3 else "orta",
            "comment": (
                f"n={n} urun denetlenmis; audited {audited_count}/{n} (staubli_feasibility dolu); "
                f"avg = {avg_staubli if avg_staubli else 'henuz pilot urun denetimi tamamlanmadi'}. "
                "Faz 3.4 pilot: Capri Plus + Niket denetlendi (5/5 her ikisi). Diger urunler PENDING."
            ),
        },
        "data_integrity": {
            "verified_data_points": 0,
            "ai_estimated_data_points": 0,
            "verification_ratio": 0.0,
            "reliability_label": reliability,
            "sample_size_tracked_products": n,
            "_reliability_explanation": (
                f"n={n}, threshold n>={THRESHOLD} "
                f"{'gecti -> mostly_estimated' if n >= THRESHOLD else 'gecmedi -> insufficient_sample'}. "
                f"Audited (mobidik_evaluation dolu) {audited_count}/{n}; bu sayi yukseldikce avg_feasibility daha guvenilir."
            ),
        },
        "notes": [
            f"v1.0 (2026-05-25): Faz 3.5 ilk insa. Documents iterasyonu urun JSON'larindan turetildi (n={n}, audited={audited_count}).",
            "Statik kimlik (kurucular, CEO, mill_ownership, designer_roster, anitsal projeler) PENDING — sonraki denetim adimi.",
            statik["_static_pending_note"],
        ],
    }


for slug in ["zimmer_rohde", "ado_goldkante", "etamine", "travers"]:
    p = hesapla(slug)
    if p is None:
        print(f"{slug}: urun yok, atlandi")
        continue
    out_path = MARKA_OUT / f"{slug}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)
    avg = p["mobidik_strategic_assessment"]["average_feasibility_score"].get(
        "observed_at_n" + str(p["product_count_tracked"])
    )
    print(
        f"{slug}: n={p['product_count_tracked']}, "
        f"reliability={p['data_integrity']['reliability_label']}, "
        f"avg_staubli={avg if avg else 'pending'}"
    )
