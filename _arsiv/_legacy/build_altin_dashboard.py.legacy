"""Faz 5.14: ALTIN urunler sayfasi build (03_html_dashboard/altin_urunler.html).

Mobidik ARGE departmani icin: overall_score >= 80 olan 7 urun, detayli rapor
formatinda tek sayfada. Her kart: gorsel + spec + MOBIDIK AKSIYON bolumu
(Stabli yapilabilirlik + strategic_note + Turk fason + sertifika + sub-brand
+ pilot timeline). Plan tablolarindan hardcoded meta.

Calistirma:
  .venv\\Scripts\\python.exe topla\\scripts\\build_altin_dashboard.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URUNLER_DIR = ROOT / "markalar" / "urunler"
OUT_HTML = ROOT / "03_html_dashboard" / "altin_urunler.html"

ALTIN_THRESHOLD = 80

# Plan tablolarindan hardcoded meta (ALTIN urunler icin Mobidik aksiyon detaylari)
ALTIN_META = {
    "ado_goldkante_3150-capri-plus": {
        "sub_brand": "Mediterranean Outdoor",
        "iplik": "SASA / Korteks (solution-dyed PES)",
        "fason": "Bursa havzasi outdoor ureticisi",
        "sertifika": "OEKO-TEX (genel)",
        "pilot_baslangic": "Ay 3-4",
        "pilot_sure": "4-6 hafta",
        "pilot_miktar": "5 notr ton x 150 m",
        "icon": "☀️",
    },
    "ado_goldkante_3009-harry-re": {
        "sub_brand": "Surdurulebilirlik (GRS hatti)",
        "iplik": "SASA / Korteks GRS-sertifikali rPES",
        "fason": "Bursa havzasi recycled sertifikali",
        "sertifika": "GRS basvurusu ALTIN ANAHTAR (3-6 ay)",
        "pilot_baslangic": "Ay 3-4 (paralel)",
        "pilot_sure": "4-6 hafta uretim + GRS 3-6 ay",
        "pilot_miktar": "2 ton x 100 m",
        "icon": "♻️",
    },
    "dedar_00T19063-cobra": {
        "sub_brand": "Mediterranean Outdoor (FR + leno)",
        "iplik": "Indorama Turkiye (Trevira CS FR PES)",
        "fason": "Mobidik iceride (leno aparat kapasitede)",
        "sertifika": "B1 / DIN 4102-1 + BS5867 + IMO MED Part. 7 (paralel)",
        "pilot_baslangic": "Ay 5-6 (paralel)",
        "pilot_sure": "6-8 hafta uretim + sertifika 3-12 ay",
        "pilot_miktar": "2 notr ton x 100 m",
        "icon": "🔥",
    },
    "zimmer_rohde_11049-nuri": {
        "sub_brand": "Anatolian After Rain (core competency)",
        "iplik": "Bursa keten + Adana pamuk",
        "fason": "Mobidik iceride (keten/pamuk dobby)",
        "sertifika": "OEKO-TEX",
        "pilot_baslangic": "Ay 1-2 (paralel)",
        "pilot_sure": "4-6 hafta",
        "pilot_miktar": "3 ton (renk 883/990/991) x 120 m",
        "icon": "🌾",
    },
    "kvadrat_5539-air-line": {
        "sub_brand": "Anatolian Linen (BENCHMARK)",
        "iplik": "Linex / Linus / Dogu Akdeniz Iplik (Bursa)",
        "fason": "Akin / Erak / Ipekis / Karsu (sektor networking — Kvadrat zaten TR'de fason yaptiriyor)",
        "sertifika": "EU Flax + OEKO-TEX",
        "pilot_baslangic": "Ay 1-2",
        "pilot_sure": "4-6 hafta",
        "pilot_miktar": "3 notr ton (White Linen, Light Ash, Hazel) x 100 m",
        "icon": "🇹🇷",
    },
    "zimmer_rohde_10969-melange-linen": {
        "sub_brand": "Anatolian Linen",
        "iplik": "Bursa keten birligi",
        "fason": "Mobidik iceride (Anatolian Linen ankor urunu)",
        "sertifika": "EU Flax + Masters of Linen muadili (Anatolian soylem)",
        "pilot_baslangic": "Ay 7-9",
        "pilot_sure": "6-8 hafta",
        "pilot_miktar": "3 ton x 100 m",
        "icon": "🌿",
    },
    "ado_goldkante_3301-pure-white-pinstripe": {
        "sub_brand": "Color Fields (AB kurumsal kanal)",
        "iplik": "Yunsa / Korteks (slub iplik MOQ ~500 kg)",
        "fason": "Mobidik iceride (320 cm warp beam test)",
        "sertifika": "OEKO-TEX",
        "pilot_baslangic": "Ay 5-6",
        "pilot_sure": "4-5 hafta",
        "pilot_miktar": "2 ton x 150 m (Pure White Tape ile birlikte)",
        "icon": "⚪",
    },
}


def html_escape(s: str | None) -> str:
    if not s:
        return ""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def collect_images(d: dict) -> list[str]:
    """Tum gorseller — pool fallback mantigi build_dashboard.py'dan."""
    pool = []
    seen = set()
    for bucket in ("variants", "main", "technical", "lifestyle"):
        for img in d.get("images", {}).get(bucket, []):
            path = img.get("local_path")
            if path and path not in seen:
                seen.add(path)
                pool.append("../" + path)
    return pool


def build_kompozisyon(comp_list: list) -> str:
    if not comp_list:
        return "—"
    parts = []
    for c in comp_list:
        r = c.get("ratio_percent")
        f = c.get("fiber_commercial") or c.get("fiber_generic") or "?"
        parts.append(f"{r}% {f}" if r is not None else f)
    return ", ".join(parts)


def build_card(d: dict) -> str:
    """Tek ALTIN urun icin detayli kart HTML."""
    urun_id = d["urun_id"]
    me = d.get("mobidik_evaluation", {})
    sd = d.get("source_data", {})
    tech = sd.get("technical", {})
    sf = me.get("staubli_feasibility", {})
    overall = me.get("overall_score", 0)
    staubli = sf.get("score", "?")
    strategic = me.get("strategic_note", "—")
    sf_comment = sf.get("comment", "—")

    meta = ALTIN_META.get(urun_id, {})
    sub_brand = meta.get("sub_brand", "—")
    iplik = meta.get("iplik", "—")
    fason = meta.get("fason", "—")
    sertifika = meta.get("sertifika", "—")
    pilot_baslangic = meta.get("pilot_baslangic", "—")
    pilot_sure = meta.get("pilot_sure", "—")
    pilot_miktar = meta.get("pilot_miktar", "—")
    icon = meta.get("icon", "⭐")

    images = collect_images(d)
    img_html = ""
    if images:
        img_html = "".join(
            f'<img src="{html_escape(p)}" alt="" onclick="openLightbox(this)" '
            f'onerror="this.style.display=\'none\'">'
            for p in images[:6]
        )

    composition = build_kompozisyon(tech.get("composition", []))
    width = tech.get("width_cm")
    width_str = f"{width} cm" if width else "—"
    weight = tech.get("weight_gsm")
    weight_str = f"{weight} g/m²" if weight else "üretici beyan etmiyor"
    weave = tech.get("weave_type_normalized") or tech.get("weave_type_raw") or "—"
    country = sd.get("commercial", {}).get("country_of_origin") or "—"
    variant_count = len(sd.get("variants", []))
    designer = sd.get("design_credit", {}).get("designer") or "—"

    certs = sd.get("certifications", {})
    cert_list = (
        certs.get("fire_safety", [])
        + certs.get("sustainability", [])
        + certs.get("other", [])
    )
    cert_html = (
        "<br>".join(html_escape(c) for c in cert_list[:6]) if cert_list else "—"
    )

    return f"""
<section class="altin-kart">
  <div class="altin-baslik">
    <div class="rozet">
      <span class="rozet-icon">{icon}</span>
      ALTIN ÜRÜN — Mobidik pilot adayı
      <span class="skor">{overall}/100</span>
    </div>
    <h2>{html_escape(d.get("brand", ""))} · {html_escape(d.get("product_name", ""))} · {html_escape(d.get("product_code", ""))}</h2>
    <div class="sub-brand">🏷️ <strong>{html_escape(sub_brand)}</strong></div>
  </div>

  <div class="altin-icerik">
    <div class="gorsel-kolon">
      <div class="gorsel-grid">{img_html or '<div class="gorsel-yok">Görsel yükleniyor...</div>'}</div>
    </div>

    <div class="spec-kolon">
      <h3>📋 Teknik Özellikler</h3>
      <table class="spec-tablo">
        <tr><td>Stäubli</td><td><strong>{staubli}/5 ✅</strong></td></tr>
        <tr><td>Üretim ülkesi</td><td>{html_escape(country)}</td></tr>
        <tr><td>Kompozisyon</td><td>{html_escape(composition)}</td></tr>
        <tr><td>En</td><td>{html_escape(width_str)}</td></tr>
        <tr><td>Gramaj</td><td>{html_escape(weight_str)}</td></tr>
        <tr><td>Dokuma</td><td>{html_escape(weave)}</td></tr>
        <tr><td>Renk varyantı</td><td>{variant_count} renk</td></tr>
        <tr><td>Designer</td><td>{html_escape(designer)}</td></tr>
        <tr><td>Sertifikalar</td><td>{cert_html}</td></tr>
      </table>
    </div>
  </div>

  <div class="mobidik-aksiyon">
    <h3>🎯 MOBİDİK AKSİYON</h3>

    <div class="aksiyon-bolum">
      <h4>🔧 Stäubli Yapılabilirlik (Kapasite #7)</h4>
      <p>{html_escape(sf_comment)}</p>
    </div>

    <div class="aksiyon-bolum">
      <h4>📈 Stratejik Not</h4>
      <p>{html_escape(strategic)}</p>
    </div>

    <div class="aksiyon-grid">
      <div class="aksiyon-kutu">
        <h4>🧵 İplik Tedarikçi</h4>
        <p>{html_escape(iplik)}</p>
      </div>
      <div class="aksiyon-kutu">
        <h4>🏭 Fason Üretici</h4>
        <p>{html_escape(fason)}</p>
      </div>
      <div class="aksiyon-kutu">
        <h4>📜 Sertifika İhtiyacı</h4>
        <p>{html_escape(sertifika)}</p>
      </div>
      <div class="aksiyon-kutu">
        <h4>📅 Pilot Timeline</h4>
        <p><strong>{html_escape(pilot_baslangic)}</strong> · {html_escape(pilot_sure)}<br>
        Miktar: {html_escape(pilot_miktar)}</p>
      </div>
    </div>
  </div>
</section>
"""


# Stil + JS
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>🌟 ALTIN Ürünler — Mobidik ARGE Pilot Adayları</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0d1117; color: #e6edf3; line-height: 1.6; padding: 20px; }
  .navbar { position: sticky; top: 0; background: #161b22; padding: 15px 20px;
    margin: -20px -20px 30px -20px; border-bottom: 2px solid #FFA500;
    display: flex; justify-content: space-between; align-items: center; z-index: 100; }
  .navbar a { color: #FFD700; text-decoration: none; font-weight: 600;
    padding: 8px 16px; border: 1px solid #FFD700; border-radius: 4px;
    transition: background 0.2s; }
  .navbar a:hover { background: rgba(255,215,0,0.1); }
  .ust-banner { text-align: center; padding: 30px 20px; margin-bottom: 30px;
    background: linear-gradient(135deg, rgba(255,215,0,0.15), rgba(255,165,0,0.05));
    border-radius: 12px; border: 1px solid rgba(255,165,0,0.3); }
  .ust-banner h1 { font-size: 2.2em; margin-bottom: 10px;
    background: linear-gradient(135deg, #FFD700, #FFA500); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; background-clip: text; }
  .ust-banner p { color: #8b949e; font-size: 1.05em; }
  .ozet { display: flex; gap: 20px; justify-content: center; margin-top: 15px; flex-wrap: wrap; }
  .ozet-kutu { background: #161b22; padding: 10px 20px; border-radius: 6px;
    border: 1px solid #30363d; }
  .ozet-kutu strong { color: #FFD700; }
  .altin-kart { background: #161b22; border-radius: 12px; padding: 25px;
    margin-bottom: 30px; border: 2px solid rgba(255,165,0,0.3);
    box-shadow: 0 4px 12px rgba(255,165,0,0.1); }
  .altin-baslik { border-bottom: 1px solid #30363d; padding-bottom: 15px;
    margin-bottom: 20px; }
  .rozet { display: inline-flex; align-items: center; gap: 10px;
    background: linear-gradient(135deg, #FFD700, #FFA500);
    color: #1a1a1a; font-weight: 700; padding: 8px 16px;
    border-radius: 6px; margin-bottom: 10px;
    box-shadow: 0 3px 8px rgba(255,165,0,0.4); }
  .rozet-icon { font-size: 1.3em; }
  .skor { background: rgba(0,0,0,0.2); padding: 2px 10px; border-radius: 4px;
    margin-left: 8px; }
  .altin-baslik h2 { font-size: 1.6em; color: #f0f6fc; }
  .sub-brand { color: #8b949e; margin-top: 8px; font-size: 0.95em; }
  .altin-icerik { display: grid; grid-template-columns: 1fr 1fr; gap: 25px;
    margin-bottom: 25px; }
  @media (max-width: 900px) { .altin-icerik { grid-template-columns: 1fr; } }
  .gorsel-kolon h3, .spec-kolon h3 { color: #FFD700; margin-bottom: 12px;
    font-size: 1.1em; }
  .gorsel-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .gorsel-grid img { width: 100%; height: 140px; object-fit: cover;
    border-radius: 6px; cursor: pointer; transition: transform 0.2s; }
  .gorsel-grid img:hover { transform: scale(1.05); }
  .gorsel-yok { background: #21262d; height: 140px; display: flex;
    align-items: center; justify-content: center; border-radius: 6px;
    color: #8b949e; font-size: 0.9em; grid-column: 1/-1; }
  .spec-tablo { width: 100%; border-collapse: collapse; }
  .spec-tablo td { padding: 8px 10px; border-bottom: 1px solid #30363d;
    font-size: 0.95em; }
  .spec-tablo td:first-child { color: #8b949e; width: 40%; }
  .mobidik-aksiyon { background: rgba(255,215,0,0.05); padding: 20px;
    border-radius: 8px; border: 1px solid rgba(255,215,0,0.2); }
  .mobidik-aksiyon h3 { color: #FFA500; margin-bottom: 15px; font-size: 1.2em; }
  .aksiyon-bolum { margin-bottom: 15px; }
  .aksiyon-bolum h4 { color: #FFD700; font-size: 1em; margin-bottom: 6px; }
  .aksiyon-bolum p { color: #c9d1d9; font-size: 0.95em; }
  .aksiyon-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px;
    margin-top: 15px; }
  @media (max-width: 700px) { .aksiyon-grid { grid-template-columns: 1fr; } }
  .aksiyon-kutu { background: #0d1117; padding: 12px; border-radius: 6px;
    border-left: 3px solid #FFA500; }
  .aksiyon-kutu h4 { color: #FFD700; font-size: 0.9em; margin-bottom: 5px; }
  .aksiyon-kutu p { color: #c9d1d9; font-size: 0.9em; }
  .footer { text-align: center; color: #6e7681; padding: 30px 20px;
    margin-top: 30px; border-top: 1px solid #30363d; }
  .lightbox { display: none; position: fixed; top: 0; left: 0; width: 100%;
    height: 100%; background: rgba(0,0,0,0.95); z-index: 1000;
    cursor: pointer; }
  .lightbox img { max-width: 90vw; max-height: 90vh; position: absolute;
    top: 50%; left: 50%; transform: translate(-50%, -50%); }
</style>
</head>
<body>
  <nav class="navbar">
    <a href="index.html">← Tüm Dashboard'a Dön (23 ürün)</a>
    <span style="color:#8b949e;">Mobidik ARGE — ALTIN ürünler raporu</span>
  </nav>

  <header class="ust-banner">
    <h1>🌟 ALTIN ÜRÜNLER — Mobidik Pilot Adayları</h1>
    <p>Otomasyonun keşfettiği ALTIN ürünler — <strong>overall_score ≥ 80</strong></p>
    <div class="ozet">
      <div class="ozet-kutu"><strong>__TOPLAM__</strong> ALTIN ürün</div>
      <div class="ozet-kutu"><strong>__MARKA_SAYI__</strong> marka</div>
      <div class="ozet-kutu">Skor aralığı <strong>__MIN_SKOR__–__MAX_SKOR__</strong>/100</div>
    </div>
  </header>

  <main>
    __KARTLAR__
  </main>

  <footer class="footer">
    <p>📄 Detaylı plan: <code>docs/mobidik_arge_pilot_uretim_plani.md</code> · 📚 Rehber: <code>docs/altin_urunler_rehberi.md</code></p>
    <p>Sistem: 23 ürün audited · 7 marka kayıt · 16 commit · Faz 5.14</p>
  </footer>

  <div class="lightbox" id="lightbox" onclick="this.style.display='none'">
    <img id="lightbox-img" src="" alt="">
  </div>

  <script>
    function openLightbox(img) {
      document.getElementById('lightbox-img').src = img.src;
      document.getElementById('lightbox').style.display = 'block';
    }
  </script>
</body>
</html>
"""


def main():
    products = []
    for jp in sorted(URUNLER_DIR.glob("*.json")):
        with jp.open(encoding="utf-8") as f:
            d = json.load(f)
        score = d.get("mobidik_evaluation", {}).get("overall_score")
        if score is not None and score >= ALTIN_THRESHOLD:
            products.append(d)

    products.sort(
        key=lambda d: d.get("mobidik_evaluation", {}).get("overall_score", 0),
        reverse=True,
    )

    print(f"ALTIN urun sayisi: {len(products)} (overall >= {ALTIN_THRESHOLD})")
    for p in products:
        score = p["mobidik_evaluation"]["overall_score"]
        print(f"  {score}/100  {p['brand']} {p['product_name']} ({p['product_code']})")

    kartlar_html = "".join(build_card(p) for p in products)
    markalar = sorted(set(p["brand"] for p in products))
    skorlar = [p["mobidik_evaluation"]["overall_score"] for p in products]

    html = HTML_TEMPLATE
    html = html.replace("__TOPLAM__", str(len(products)))
    html = html.replace("__MARKA_SAYI__", str(len(markalar)))
    html = html.replace("__MIN_SKOR__", str(min(skorlar) if skorlar else 0))
    html = html.replace("__MAX_SKOR__", str(max(skorlar) if skorlar else 0))
    html = html.replace("__KARTLAR__", kartlar_html)

    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"\nYazildi: {OUT_HTML.relative_to(ROOT)} ({len(html):,} byte)")


if __name__ == "__main__":
    main()
