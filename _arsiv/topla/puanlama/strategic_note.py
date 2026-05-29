"""Türkçe stratejik not şablonu.

Kural #9: Python AI inference yapmaz. Bu sadece template doldurma —
detaylı yorum Claude Code oturumunda gelir.
"""


def _fmt(value, fallback="bilinmiyor"):
    if value is None or value == "":
        return fallback
    return str(value)


def generate_strategic_note(source_data: dict, staubli: dict) -> str:
    brand = _fmt(source_data.get("brand"), "Marka bilinmiyor")
    product = _fmt(source_data.get("product_name"), "ürün")
    composition = _fmt(source_data.get("composition_text"), "kompozisyon bilinmiyor")
    weave = _fmt(source_data.get("weave_type"), "dokuma bilinmiyor")
    country_raw = source_data.get("country_of_origin")
    country_part = f"üretim {country_raw}" if country_raw else "üretim ülkesi sayfada belirtilmemiş"

    score = staubli["score"]
    reasons = staubli.get("reasons") or []
    reason_str = " ".join(reasons)

    return (
        f"{brand} {product}: {composition}, {weave} dokuma, {country_part}. "
        f"Stäubli yapılabilirlik {score}/5 — {reason_str} "
        f"Detaylı stratejik yorum Claude Code oturumunda yapılacak."
    )
