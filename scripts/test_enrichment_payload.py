"""OnCalisma-V2 (Problem 4a) — build_enrichment_payload + research_update strip-retry testleri.

Çalıştırma:  python scripts/test_enrichment_payload.py
DB GEREKTİRMEZ: build_enrichment_payload saf; strip-retry mock client ile test edilir
(PROD havuzuna YAZMA, login YOK).
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1254 konsol koruması
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web"))
import gemini_extract as gx  # noqa: E402
import store  # noqa: E402

fails = 0


def check(label, cond):
    global fails
    if not cond:
        fails += 1
    print(f"{'OK  ' if cond else 'FAIL'}  {label}")


# ---------------- build_enrichment_payload ----------------
RESULT = {
    "ok": True, "model_used": "gemini-2.5-flash",
    "suggestions": {
        "composition": {"value": "%100 Keten", "evidence": "Composition: 100% Linen"},
        "production_country": {"value": "İtalya", "evidence": "Made in Italy"},
        "reference_price": {"value": "140 EUR", "type": "from", "evidence": "from 140 EUR/m"},
        "weave_type": {"value": "dobby", "evidence": ""},      # evidence YOK -> atlanmalı (#3)
        "width_cm": {"value": "", "evidence": "width 140"},     # value YOK -> atlanmalı
        "brand": None,                                          # null -> atlanmalı
        # P4b — yeni alanlar (evidence'lı -> extracted_facts'e girer)
        "brand_country": {"value": "İsviçre", "evidence": "based in Switzerland"},
        "color_count": {"value": "21", "evidence": "21 colours"},
        # P5 — taxonomy (inference; vocab'a validate) + image_analysis (vision inference)
        "taxonomy": {"category": "TUL", "pattern": "cizgili", "color_family": "krem-bej",
                     "weave_tags": ["vual", "banana"], "style_tags": ["premium", "minimal", "premium", ""],
                     "confidence": "high", "reason": "tul sheer"},
        "image_analysis": {"dominant_colors": ["#EEE8D5", "#C9B79C"], "texture": "dokulu",
                           "transparency": "tül", "color_count": "21", "confidence": "medium", "note": "açık tonlar"},
        "arge_notu_taslak": {"value": "A" * 350, "evidence": "desc"},
    },
}

p = gx.build_enrichment_payload(RESULT)
ef = p["extracted_facts"]; ai = p["ai_summary"]
# (a) factual/inference ayrımı doğru (P6.2: brand_country artık ÇIKARIM → suggested, ef'te DEĞİL)
check("(a) factual kanıtlı 4 alan", sorted(ef.keys()) == ["color_count", "composition", "production_country", "reference_price"])
check("(P4b) color_count extracted_facts'te", ef.get("color_count", {}).get("value") == "21")
check("(P6.2) brand_country ÇIKARIM: suggested'da, ef'te DEĞİL", "brand_country" not in ef and (ai.get("suggested") or {}).get("brand_country") == "İsviçre")
check("(a) arge_notu ai_summary'de, extracted_facts'te DEĞİL", "arge_notu_taslak" not in ef and "arge_notu" in ai)
check("(a) production_country sadece extracted_facts'te", "production_country" in ef)
# (b) evidence/value'sız factual atlanıyor
check("(b) weave_type (evidence yok) atlandı", "weave_type" not in ef)
check("(b) width_cm (value yok) atlandı", "width_cm" not in ef)
check("(b) brand (null) atlandı", "brand" not in ef)
# price type taşınıyor + evidence korunuyor
check("price.type='from' taşındı", ef.get("reference_price", {}).get("type") == "from")
check("composition.evidence korundu", ef.get("composition", {}).get("evidence") == "Composition: 100% Linen")
# (c) arge ≤300
check("(c) arge_notu <= 300", len(ai.get("arge_notu", "")) == 300)
check("ai_summary model + generated_at var", bool(ai.get("model")) and bool(ai.get("generated_at")))
# P5 — taxonomy ÖNERİSİ ai_summary.suggested'da (extracted_facts'te DEĞİL), vocab'a temizlenmiş
_sug = ai.get("suggested") or {}
check("(P5) taxonomy extracted_facts'te DEĞİL", "taxonomy" not in ef and "image_analysis" not in ef)
check("(P5) suggested.category normalize (TUL->tul)", _sug.get("category") == "tul")
check("(P5) suggested.weave_tags banana süzüldü", _sug.get("weave_tags") == ["vual"])
check("(P6) suggested.style_tags trim+dedup", _sug.get("style_tags") == ["premium", "minimal"])
check("(P5) suggested.confidence taşındı", _sug.get("confidence") == "high")
# P5 — image_analysis ai_summary'de
_ia = ai.get("image_analysis") or {}
check("(P5) image_analysis dominant_colors + transparency", _ia.get("dominant_colors") == ["#EEE8D5", "#C9B79C"] and _ia.get("transparency") == "tül")

# ---------------- P6.1/P6.3 — kanıt doğrulama: şüpheli ATILMAZ, unverified:true ile işaretlenir ----------------
RESULT_V = {
    "ok": True, "model_used": "gemini-2.5-pro",
    "source_text": 'Material 100% polyester  Width / Height 315 cm / 124"  Colour variations 5',
    "suggestions": {
        "composition": {"value": "%100 polyester", "evidence": "Material 100% polyester"},   # kanıt VAR
        "width_cm": {"value": "315", "evidence": 'Width / Height 315 cm / 124"'},             # VAR
        "weight_gsm": {"value": "113", "evidence": "Weight 113 g/m²"},                         # YOK -> unverified
        "reference_price": {"value": "120 EUR", "type": "from", "evidence": "Price from 120 EUR / m"},  # YOK -> unverified
    },
}
pv = gx.build_enrichment_payload(RESULT_V)
efv = pv["extracted_facts"]
check("(P6.3) composition kaldı + verified", "composition" in efv and efv["composition"].get("unverified") is None)
check("(P6.3) width_cm kaldı + verified", "width_cm" in efv and efv["width_cm"].get("unverified") is None)
check("(P6.3) weight_gsm KALDI + unverified:true", efv.get("weight_gsm", {}).get("unverified") is True)
check("(P6.3) reference_price KALDI + unverified:true", efv.get("reference_price", {}).get("unverified") is True)
check("(P6.3) reference_price.type şüphelide de korundu", efv.get("reference_price", {}).get("type") == "from")
check("(P6.3) unverified_fields listesi doğru", sorted(pv.get("unverified_fields") or []) == ["reference_price", "weight_gsm"])
# source_text YOKSA doğrulama atlanır (geriye dönük uyum) — bayrak konmaz
_nosrc = gx.build_enrichment_payload({"ok": True, "suggestions": {"weave_type": {"value": "dobby", "evidence": "kanıtsız"}}})
check("(P6.3) source_text yoksa doğrulama atlanır", "weave_type" in _nosrc["extracted_facts"] and not _nosrc.get("unverified_fields"))
check("(P6.3) source_text yoksa unverified bayrağı konmaz", _nosrc["extracted_facts"]["weave_type"].get("unverified") is None)

# (d) error -> boş payload
pe = gx.build_enrichment_payload({"ok": False, "error": "http_404"})
check("(d) error -> boş payload + error", pe["extracted_facts"] == {} and pe["ai_summary"] == {} and pe.get("error") == "http_404")
pe2 = gx.build_enrichment_payload({"ok": True, "suggestions": None})
check("(d) suggestions None -> no_suggestions", pe2.get("error") == "no_suggestions")


# ---------------- research_update strip-retry (mock client) ----------------
class _Chain:
    def __init__(self, payload): self.payload = payload
    def eq(self, *a, **k): return self
    def execute(self):
        # Migration uygulanmamış gibi: enrichment kolonu varsa "column does not exist" fırlat
        if any(k in self.payload for k in ("extracted_facts", "ai_summary", "enrichment_status")):
            raise Exception('column "extracted_facts" of relation "research_pool" does not exist')
        return type("R", (), {"data": [dict(self.payload, id="RID")]})()


class _Table:
    def update(self, payload): return _Chain(payload)


class _Client:
    def table(self, name): return _Table()


_orig_client = store.client
_orig_get = store.research_get
store.client = lambda: _Client()
store.research_get = lambda rid: {"id": rid, "_noop": True}
try:
    res = store.research_update("RID", {
        "extracted_facts": {"composition": {"value": "x", "evidence": "y"}},
        "ai_summary": {"arge_notu": "n"},
        "enrichment_status": "enriched",
        "notes": "kept",   # whitelisted normal alan -> slim'de kalmalı
    })
    check("strip-retry ÇÖKMEDİ", res is not None)
    check("strip-retry: notes korundu", res.get("notes") == "kept")
    check("strip-retry: 3 enrichment kolonu düştü",
          all(k not in res for k in ("extracted_facts", "ai_summary", "enrichment_status")))
    # Yalnız enrichment kolonları -> slim boş -> research_get (no-op), çökme yok
    res2 = store.research_update("RID", {"enrichment_status": "verified"})
    check("strip-retry: yalnız-enrichment patch -> no-op, çökme yok", res2 is not None and res2.get("_noop"))
finally:
    store.client = _orig_client
    store.research_get = _orig_get


print("-" * 60)
print("SONUC:", "TUM TESTLER GECTI (PASS)" if fails == 0 else f"{fails} HATA (FAIL)")
sys.exit(1 if fails else 0)
