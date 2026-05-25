"""Faz 4: markalar/urunler/*.json -> 03_html_dashboard/index.html dashboard inject.

Anayasa #9 disiplini: Python mekanik (JSON oku, HTML inject); icerik (mobidik_notu HTML markup,
strategic_note metinleri) Claude Code denetimi sonucu.

Strateji:
- 19 urun JSON DB'den okunur
- Her urun, eski dashboard JS array formatina donusturulur
- 03_html_dashboard/index.html icindeki 'const products = [...]' replace edilir
- Ilk kez: index.html -> index_pre_faz4_legacy.html yedek
- PENDING urunler icin: mobidik_notu_legacy gosterilir + uyari badge

Calistirma:
  .venv\\Scripts\\python.exe topla\\scripts\\build_dashboard.py
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URUNLER_DIR = ROOT / "markalar" / "urunler"
HTML_PATH = ROOT / "03_html_dashboard" / "index.html"
HTML_LEGACY = ROOT / "03_html_dashboard" / "index_pre_faz4_legacy.html"

SCALE_EMOJI = {5: "✅", 4: "✅", 3: "⚠️", 2: "⚠️", 1: "⛔"}


def build_renkler(d: dict) -> list[dict]:
    """sema variants[] + images.variants[] -> dashboard renkler[]"""
    renkler = []
    # Gorselleri renk koduna gore grupla
    images_by_variant: dict[str, list[str]] = {}
    for img in d.get("images", {}).get("variants", []):
        vc = img.get("variant_code")
        if not vc:
            continue
        images_by_variant.setdefault(vc, []).append("../" + img["local_path"])

    for var in d["source_data"]["variants"]:
        full_code = var["color_code"]
        # Son segment renk kodu (orn. "5539-0101" -> "0101", "3018-110" -> "110")
        renk_kodu = full_code.split("-")[-1] if "-" in full_code else full_code

        gorseller = images_by_variant.get(full_code, [])
        # Eger images.variants'ta yoksa main_image_local_path'i kullan
        if not gorseller and var.get("main_image_local_path"):
            gorseller = ["../" + var["main_image_local_path"]]

        renkler.append({
            "kod": renk_kodu,
            "ad": var.get("color_name") or "(isim yok)",
            "swatch": var.get("main_image_url_source") or "",
            "gorseller": gorseller,
        })
    return renkler


def build_mobidik_notu(d: dict) -> str:
    """mobidik_evaluation + source_data -> dashboard HTML markup."""
    me = d.get("mobidik_evaluation", {})
    sf = me.get("staubli_feasibility", {})
    score = sf.get("score")

    if score is not None:
        # Tam denetim
        emoji = SCALE_EMOJI.get(score, "")
        priority = me.get("priority_level", "?")
        frame = sf.get("frame_count_estimate", "N/A")
        comment = sf.get("comment", "")
        strategic = me.get("strategic_note", "")
        # Strategic note kisa tutalim (300 karakter)
        if len(strategic) > 350:
            strategic = strategic[:350] + "..."

        # Celiski tespiti: audit_history'de "CELISKI" gecer mi?
        audit_str = json.dumps(d["source_data"]["_provenance"]["audit_history"], ensure_ascii=False)
        celiski_badge = ""
        # ASCII (CELISKI) + Turkce (ÇELİŞKİ) variant kontrolu
        if any(t in audit_str for t in ("CELISKI", "celiski", "ÇELİŞKİ", "çelişki", "ÇELISKI")):
            celiski_badge = " <span style='background:#ffe066;padding:2px 6px;border-radius:3px;font-size:0.85em'>⚠️ Documents çelişkisi düzeltildi (anayasa #7)</span>"

        return (
            f"<b>Stäubli: {score}/5 {emoji}</b>{celiski_badge} · "
            f"Çerçeve: {frame}. {comment}<br>"
            f"<b>Strateji ({priority} öncelik):</b> {strategic}"
        )
    else:
        # PENDING
        legacy = d["source_data"].get("mobidik_notu_legacy", "")
        if len(legacy) > 450:
            legacy = legacy[:450] + "..."
        return (
            "<b>⏳ Stratejik yorum henüz tamamlanmadı</b> "
            "<span style='background:#ffcccc;padding:2px 6px;border-radius:3px;font-size:0.85em'>(Faz 3.4 denetim devamı)</span><br>"
            f"<em>Documents notu (geçici):</em> {legacy}"
        )


def build_kompozisyon(comp_list: list) -> str:
    """[{'fiber_commercial': 'Polyester', 'ratio_percent': 59}, ...] -> '59% Polyester, 41% Cotton'"""
    if not comp_list:
        return "üretici beyan etmiyor"
    parts = []
    for c in comp_list:
        ratio = c.get("ratio_percent")
        fiber = c.get("fiber_commercial") or c.get("fiber_generic") or "?"
        if ratio is not None:
            parts.append(f"{ratio}% {fiber}")
        else:
            parts.append(fiber)
    return ", ".join(parts)


def build_rapor(repeat_cm: dict, raw_text: str | None = None) -> str:
    v = repeat_cm.get("vertical")
    h = repeat_cm.get("horizontal")
    if v is None and h is None:
        return raw_text or "yok / strüktürel"
    if v and not h:
        return f"~{v} cm vertikal"
    if v and h:
        return f"~{v} × {h} cm"
    return raw_text or "—"


def build_dashboard_obj(d: dict) -> dict:
    sd = d["source_data"]
    tech = sd["technical"]

    return {
        "marka": d["brand"],
        "koleksiyon": d.get("collection") or "(belirtilmemiş)",
        "urun_kodu": d["product_code"],
        "urun_adi": d["product_name"],
        "ulke": sd.get("commercial", {}).get("country_of_origin") or "—",
        "kompozisyon": build_kompozisyon(tech.get("composition", [])),
        "en": str(tech["width_cm"]) if tech.get("width_cm") else "üretici beyan etmiyor",
        "gramaj": (
            f"{tech['weight_gsm']} g/m²" if tech.get("weight_gsm")
            else "üretici beyan etmiyor"
        ),
        "rapor": build_rapor(tech.get("repeat_cm", {}), None),
        "dokuma": tech.get("weave_type_normalized") or tech.get("weave_type_raw") or "—",
        "renkler": build_renkler(d),
        "performans": sd.get("performans_legacy") or sd.get("certifications", {}).get("other", []),
        "aciklama": (
            sd.get("description_tr", {}).get("text")
            or sd.get("description_original", {}).get("text")
            or ""
        ),
        "stil_notu": sd.get("style_note") or "",
        "url": d.get("source_url") or "",
        "mobidik_notu": build_mobidik_notu(d),
    }


def main() -> None:
    # 1) Yedek al (sadece ilk kez)
    if not HTML_LEGACY.exists():
        shutil.copy2(HTML_PATH, HTML_LEGACY)
        print(f"Yedek alindi: {HTML_LEGACY.name}")
    else:
        print(f"Yedek zaten var: {HTML_LEGACY.name} (skip)")

    # 2) JSON DB oku
    urun_files = sorted(URUNLER_DIR.glob("*.json"))
    products = []
    pending_count = 0
    audited_count = 0
    for jp in urun_files:
        with jp.open(encoding="utf-8") as f:
            d = json.load(f)
        obj = build_dashboard_obj(d)
        products.append(obj)
        if d["mobidik_evaluation"]["staubli_feasibility"]["score"] is None:
            pending_count += 1
        else:
            audited_count += 1

    print(f"JSON DB'den {len(products)} urun yuklendi (audited: {audited_count}, PENDING: {pending_count})")

    # 3) HTML icine inject
    html = HTML_PATH.read_text(encoding="utf-8")
    pattern = re.compile(r"const products = \[[\s\S]*?\n\];")
    if not pattern.search(html):
        raise SystemExit("HATA: const products = [...] bulunamadi")

    new_array_str = "const products = " + json.dumps(products, ensure_ascii=False, indent=2) + ";"
    new_html = pattern.sub(lambda m: new_array_str, html, count=1)
    HTML_PATH.write_text(new_html, encoding="utf-8")

    print(f"HTML dashboard guncellendi: {HTML_PATH}")
    print(f"  Eski: inline JS array (23 urun, eski schema, mobidik_notu hardcoded)")
    print(f"  Yeni: JSON DB'den toplanan ({len(products)} urun, sema v1.3, mobidik_evaluation tabanli)")

    # 4) Marka istatistigi
    by_marka = {}
    for p in products:
        by_marka.setdefault(p["marka"], 0)
        by_marka[p["marka"]] += 1
    print()
    print("Marka dagilimi:")
    for marka, count in sorted(by_marka.items()):
        print(f"  {marka}: {count}")


if __name__ == "__main__":
    main()
