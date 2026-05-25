"""Stäubli yapılabilirlik (1-5) deterministik puanlama.

Kapasite tablosu kuralları (kapasite/staubli_uretim_kapasitesi.md):
- En > 360 cm → 0-2 (fiziksel sınır)
- Jakar yapı → 0-1 (Stäubli armür, jakar değil)
- Metallic/lurex iplik → max 2 (yetkinlik yok)
- Trevira CS spesifik → tam ama tedarik notu
- Outdoor/UV → max 3 (doğrulanmadı)

Kural #7: kapasite md'sindeki KESİN ve TAM değerler bağlayıcı.
Kural #9: Python AI inference yapmaz — bu deterministik kural uygulaması.
"""

MAX_WIDTH_CM = 360


def compute_staubli_feasibility(source_data: dict) -> dict:
    width = source_data.get("width_cm")
    weave = (source_data.get("weave_type") or "").lower()
    composition = (source_data.get("composition_text") or "").lower()
    usage = (source_data.get("usage_text") or "").lower()

    score = 5
    reasons = []

    # En kontrolü
    if width and width > MAX_WIDTH_CM:
        score = min(score, 2)
        reasons.append(
            f"Bitmiş ürün eni {int(width)} cm Mobidik'in {MAX_WIDTH_CM} cm sınırını aşıyor"
        )

    # Dokuma kontrolü
    if weave == "jacquard":
        score = min(score, 1)
        reasons.append("Jakar dokuma — Stäubli armür tezgahı jakar değil")

    # İplik kontrolü
    if "metallic" in composition or "lurex" in composition or "lurex" in composition:
        score = min(score, 2)
        reasons.append("Metallic/lurex iplik yetkinliği yok, geliştirme gerekli")

    if "trevira cs" in composition:
        reasons.append("Trevira CS tedariki gerekli (deneyim FR kategoride var)")

    if "outdoor" in usage or "uv" in composition:
        score = min(score, 3)
        reasons.append("Outdoor/UV iplik tedarik kapasitesi doğrulanmadı")

    if not reasons:
        reasons.append("Standart dokuma + standart iplik; en sınır dahilinde")

    return {"score": score, "reasons": reasons}
