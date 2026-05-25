"""Mobidik genel puanı (0-100) baseline hesabı.

Demo'da arge_value/market_gap/portfolio_fit baseline 50 — gerçek değer
Claude Code oturumunda hesaplanır (kural #9: AI inference Claude'un işi).

Ağırlıklar:
- staubli: 0.40
- arge_value: 0.25
- market_gap: 0.20
- portfolio_fit: 0.15
"""


def compute_mobidik_score(source_data: dict, staubli: dict) -> dict:
    staubli_pct = (staubli["score"] / 5.0) * 100

    arge_value_baseline = 50
    market_gap_baseline = 50
    portfolio_fit_baseline = 50

    score = (
        staubli_pct * 0.40
        + arge_value_baseline * 0.25
        + market_gap_baseline * 0.20
        + portfolio_fit_baseline * 0.15
    )

    return {
        "score": round(score),
        "components": {
            "staubli_pct": round(staubli_pct),
            "arge_value": arge_value_baseline,
            "market_gap": market_gap_baseline,
            "portfolio_fit": portfolio_fit_baseline,
        },
    }
