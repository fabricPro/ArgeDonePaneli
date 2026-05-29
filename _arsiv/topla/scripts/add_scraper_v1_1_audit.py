"""Faz 5.10b: Cobra + DLN ürün JSON'larına scraper v1.1 audit entry ekle.

Anayasa #2: Veri bütünlüğü mutlak — audit_history append-only.
Anayasa #9: Python mekanik JSON modify; içerik (audit notları) Claude.

scraper v1.1 sonuçları (canlı doğrulanmış):
- Cobra: width 325, weave leno, gorsel 1 -> 36 (BigCommerce CDN + connect.dedar)
- DLN:   width 134, weave plain, gorsel 3 -> 74
- Her iki uründe de body manual gerek YOK (artik scraper otomatik)

Görsel kopyalama Faz 5.11 ayrı adım — bu commit sadece audit + scraper kayıt.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URUNLER = ROOT / "markalar" / "urunler"
NOW = "2026-05-26T00:00:00Z"

# === Cobra audit v1.2 ===
cobra_path = URUNLER / "dedar_00T19063-cobra.json"
with cobra_path.open(encoding="utf-8") as f:
    cobra = json.load(f)

cobra["source_data"]["_provenance"]["audit_history"].append({
    "audit_id": "dedar_00T19063-cobra_v1.2_2026-05-26",
    "audit_date": "2026-05-26",
    "audit_doc": "docs/scraper_v1_1_sonuclari.md",
    "version_before": "v1.1 (Faz 5.3 Claude denetim, body manual: width=325, weave=leno, description, lightfastness)",
    "version_after": "v1.2 (Faz 5.10 scraper v1.1 yeniden cekildi, body manual gerek YOK)",
    "notes": (
        "Scraper v1.1 ile Cobra yeniden cekildi (test_cobra.py run 20260525T205810Z). "
        "Otomatik yakalananlar: width=325.0 cm (onceki None), weave=leno (onceki 'Single sheet'), "
        "lightfastness=6 (onceki None), description (cookie banner filtrelendi), "
        "production_model=stock (Current Stock tespit, onceki unknown), "
        "variants_raw=2 (002+004, onceki bos). Gorsel: 1 -> 36 (BigCommerce CDN + connect.dedar.com). "
        "Anayasa #9 disiplini canli dogrulandi: scraper mekanik, Claude denetim ayri. "
        "Bu rebuild sonrasi 'body manual' notlari source_data._provenance.field_metadata'da hala "
        "korunur (kanit zinciri tarihcesi), ama yeni alimlar scraper kaynakli sayilir."
    ),
})
cobra["source_data"]["_provenance"]["constitutional_violations_check"] = f"passed_at_{NOW}"
cobra["last_updated"] = NOW

with cobra_path.open("w", encoding="utf-8") as f:
    json.dump(cobra, f, ensure_ascii=False, indent=2)
print(f"Cobra audit v1.2 eklendi -> {cobra_path.name}")

# === DLN audit v1.1 ===
dln_path = URUNLER / "dedar_00T25007-days-like-now.json"
with dln_path.open(encoding="utf-8") as f:
    dln = json.load(f)

dln["source_data"]["_provenance"]["audit_history"].append({
    "audit_id": "dedar_00T25007-days-like-now_v1.1_2026-05-26",
    "audit_date": "2026-05-26",
    "audit_doc": "docs/scraper_v1_1_sonuclari.md",
    "version_before": "v1.0 (Faz 5.4 Claude denetim, body manual: width=134, weave=plain, description, 8 varyant)",
    "version_after": "v1.1 (Faz 5.10 scraper v1.1 yeniden cekildi, body manual gerek YOK)",
    "notes": (
        "Scraper v1.1 ile DLN yeniden cekildi (test_days_like_now.py run 20260525T205940Z). "
        "Otomatik yakalananlar: width=134.0 cm, weave=plain (shantung normalize), "
        "production_model=stock (Current Stock), 8 varyant body'den (001-008). "
        "Gorsel: 3 -> 74 (BigCommerce CDN + connect.dedar.com lifestyle). "
        "Sadece eksik: lightfastness (DLN sayfasinda yok — DLN'de bu alan beyan edilmemis, "
        "Cobra'da var; bu uretici kararı, scraper hatasi degil)."
    ),
})
dln["source_data"]["_provenance"]["constitutional_violations_check"] = f"passed_at_{NOW}"
dln["last_updated"] = NOW

with dln_path.open("w", encoding="utf-8") as f:
    json.dump(dln, f, ensure_ascii=False, indent=2)
print(f"DLN audit v1.1 eklendi -> {dln_path.name}")
