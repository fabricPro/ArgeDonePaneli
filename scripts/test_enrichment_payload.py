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
        "arge_notu_taslak": {"value": "A" * 350, "evidence": "desc"},
    },
}

p = gx.build_enrichment_payload(RESULT)
ef = p["extracted_facts"]; ai = p["ai_summary"]
# (a) factual/inference ayrımı doğru
check("(a) factual sadece kanıtlı 3 alan", sorted(ef.keys()) == ["composition", "production_country", "reference_price"])
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
