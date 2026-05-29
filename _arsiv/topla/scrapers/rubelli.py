"""Rubelli scraper v1.0 — Magento + cdn.rubelli.com pattern.

Dedar v1.1.2'den öğrenilen pattern'ler:
- Specifications label-value (Composition, Width, Weight, Made in, Use)
- Description (cookie filter + marka adı paragraf)
- Variants page loop (her renk için ayrı page.goto)
- URL filter darlığı (cdn.rubelli.com/A<kod>_<renk>/ path mecburi)

Rubelli'ye özgü:
- Composition kısaltma (CO=Cotton, VI=Viscose, LI=Linen, SE=Silk, WO=Wool, vb.)
- Use alanı (Heavy use / Medium use / Curtains / Sheers — Mobidik için critical)
- 28+ renk varyantı çok yaygın (Charles örneği) — scraper sayısını sınırla (max 10 varyant)

Kural #9: Mekanik. Kural #3: tahmin yok.
"""

import re
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from topla.images import extract_image_specs

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Rubelli composition kısaltma → tam isim
COMP_MAP = {
    "CO": ("Cotton", "Pamuk"),
    "VI": ("Viscose", "Viskon"),
    "LI": ("Linen", "Keten"),
    "SE": ("Silk", "Ipek"),
    "WO": ("Wool", "Yun"),
    "PL": ("Polyester", "Polyester"),
    "PES": ("Polyester", "Polyester"),
    "PA": ("Polyamide", "Poliamid"),
    "AC": ("Acrylic", "Akrilik"),
    "AL": ("Alpaca", "Alpaka"),
    "LY": ("Lyocell", "Lyocell"),
    "ME": ("Metallic", "Metallic"),
}

WEAVE_KEYWORDS = [
    ("damask", "jacquard"),
    ("jacquard", "jacquard"),
    ("moiré", "plain"),
    ("moire", "plain"),
    ("velvet", "dobby"),
    ("boucle", "dobby"),
    ("canvas", "plain"),
    ("chenille", "dobby"),
    ("voile", "sheer"),
    ("leno", "leno"),
    ("plain", "plain"),
    ("embroidered", "jacquard"),
    ("embroidery", "jacquard"),
]


def scrape_rubelli(url: str) -> dict:
    from topla.scrapers._browser import launch_chromium
    with sync_playwright() as p:
        browser = launch_chromium(p, headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Cookie banner — Magento + Italyan site
        for sel in [
            "button:has-text('Accept')",
            "button:has-text('Reject')",
            "button:has-text('Only necessary')",
            "button:has-text('Use necessary')",
        ]:
            try:
                page.click(sel, timeout=2000)
                break
            except Exception:
                continue

        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(2500)

        html = page.content()
        data: dict = {"brand": "Rubelli"}

        # URL'den slug + kod (/en/charles-30750)
        parsed = urlparse(url)
        m = re.match(r"^/en/([a-z0-9-]+?)-(\d{5,6})/?$", parsed.path)
        if m:
            data["product_slug"] = m.group(1)
            data["product_code"] = m.group(2)
        else:
            data["product_slug"] = "unknown"
            data["product_code"] = None

        # Product name — h1
        try:
            data["product_name"] = page.locator("h1").first.inner_text(timeout=5000).strip()
        except Exception:
            data["product_name"] = None
        if not data["product_name"]:
            m_og = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
            if m_og:
                data["product_name"] = m_og.group(1).strip()

        # Body
        try:
            body_text = page.locator("body").inner_text(timeout=5000)
        except Exception:
            body_text = ""

        # Specifications
        data["composition_text"] = _extract_label_value(body_text, "Composition")
        data["composition_parsed"] = _parse_rubelli_composition(data["composition_text"])
        width_raw = _extract_label_value(body_text, "Width")
        data["width_raw"] = width_raw
        data["width_cm"] = _parse_width(width_raw)
        data["weight_raw"] = _extract_label_value(body_text, "Weight")
        data["weight_g_per_lm"] = _parse_weight(data["weight_raw"])
        data["repeat_raw"] = (
            _extract_label_value(body_text, "Pattern repeat")
            or _extract_label_value(body_text, "Repeat")
        )
        data["use_text"] = _extract_use_value(body_text)
        data["country_of_origin"] = (
            _extract_label_value(body_text, "Made in")
            or _extract_label_value(body_text, "Country of origin")
        )
        data["martindale"] = _extract_label_value(body_text, "Abrasion test") or _extract_label_value(body_text, "Martindale")
        data["pilling"] = _extract_label_value(body_text, "Pilling")
        data["designer"] = _extract_label_value(body_text, "Designer")

        # Weave (description'da damask/moire/velvet/plain ara)
        weave_raw = _extract_weave_rubelli(body_text)
        data["weave_type_raw"] = weave_raw
        data["weave_type"] = _normalize_weave(weave_raw)

        # Use'a göre Mobidik kapsam tespit
        use_low = (data.get("use_text") or "").lower()
        if "curtain" in use_low or "sheer" in use_low:
            data["mobidik_scope"] = "perdelik"
        elif "heavy" in use_low or "medium" in use_low or "light" in use_low:
            data["mobidik_scope"] = "upholstery_kapsam_disi"
        else:
            data["mobidik_scope"] = "unknown"

        # Stock
        stock_text = body_text.lower()
        if "limited stock" in stock_text:
            data["production_model"] = "limited_stock"
        elif "out of stock" in stock_text:
            data["production_model"] = "out_of_stock"
        elif "made to order" in stock_text or "article on request" in stock_text:
            data["production_model"] = "make_to_order"
        else:
            data["production_model"] = "stock"

        # Description
        data["description_original"] = _extract_rubelli_description(body_text, data.get("product_name"))

        # Sertifika
        data["certifications"] = _extract_rubelli_certifications(body_text, html)

        # Variants
        data["variants_raw"] = _extract_rubelli_variants(html, body_text, data.get("product_code"))

        # Body preview
        data["_body_text_preview"] = body_text[:2000] if body_text else None

        # Görseller — cdn.rubelli.com darlığı + 840x840c yüksek çözünürlük
        base_images = extract_image_specs(page)
        # Filtre: cdn.rubelli.com olmayan veya A<kod>_<renk> path'i olmayanları at
        base_images = [
            img for img in base_images
            if "cdn.rubelli.com" in (img.get("kaynak_url") or "")
            and re.search(r"/A\d{5,6}_\d{1,3}/", img.get("kaynak_url") or "")
        ]
        extra_images = _extract_rubelli_gallery_images(html, data.get("product_code"))
        # Variants page loop
        variants_enriched = _scrape_variant_pages(page, url, data["variants_raw"][:10])  # max 10
        data["variants_raw"] = variants_enriched + data["variants_raw"][10:]
        for v in variants_enriched:
            if v.get("main_image_url"):
                extra_images.append({
                    "tip": "varyant",
                    "kaynak_url": v["main_image_url"],
                    "varyant_adi": v.get("name") or v.get("color_code"),
                    "_variant_code": v.get("color_code"),
                })

        seen_urls = {img["kaynak_url"] for img in base_images}
        for img in extra_images:
            if img["kaynak_url"] not in seen_urls:
                base_images.append(img)
                seen_urls.add(img["kaynak_url"])
        data["_image_specs"] = base_images

        browser.close()
        return data


USE_KEYWORDS = [
    "Heavy use", "Medium use", "Light use",
    "Curtains", "Sheers",
    "Outdoor", "Indoor/Outdoor",
    "Wallcovering", "Upholstery",
]


def _extract_use_value(body_text: str) -> str | None:
    """v1.1: Rubelli Use alani — kategorik keyword ara (genel 'Use' label cakismasini onler)."""
    if not body_text:
        return None
    # Önce 'Use\n' label ile kategorik değer
    for kw in USE_KEYWORDS:
        m = re.search(rf"\bUse\s*\n\s*{re.escape(kw)}\b", body_text, re.IGNORECASE)
        if m:
            return kw
    # Fallback: body'de hangi USE keyword'i geciyor
    for kw in USE_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", body_text, re.IGNORECASE):
            return kw
    return None


def _extract_label_value(text: str, label: str) -> str | None:
    if not text:
        return None
    m = re.search(rf"{re.escape(label)}\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    if m:
        v = m.group(1).strip()
        if v and len(v) < 500 and v.lower() != label.lower():
            return v
    m = re.search(rf"\b{re.escape(label)}\b\s*\n\s*([^\n]+)", text, re.IGNORECASE)
    if m:
        v = m.group(1).strip()
        if v and len(v) < 500 and v.lower() != label.lower():
            return v
    return None


def _parse_width(raw: str | None) -> float | None:
    if not raw:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*cm", raw, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def _parse_weight(raw: str | None) -> int | None:
    if not raw:
        return None
    m = re.search(r"(\d+)\s*g", raw, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _parse_rubelli_composition(text: str | None) -> list[dict]:
    """48%CO 37%VI 15%LI → [{generic, commercial, ratio}, ...]"""
    if not text:
        return []
    parts = []
    for m in re.finditer(r"(\d+)\s*%?\s*([A-Z]{2,4})", text):
        ratio = int(m.group(1))
        code = m.group(2)
        if code in COMP_MAP:
            commercial, generic = COMP_MAP[code]
            parts.append({
                "fiber_generic": generic,
                "fiber_commercial": commercial,
                "ratio_percent": ratio,
                "fr_treatment": None,
                "_rubelli_code": code,
            })
        else:
            parts.append({
                "fiber_generic": code,
                "fiber_commercial": code,
                "ratio_percent": ratio,
                "fr_treatment": None,
                "_rubelli_code": code,
            })
    return parts


def _extract_weave_rubelli(text: str) -> str | None:
    if not text:
        return None
    # Type label
    type_val = _extract_label_value(text, "Type")
    if type_val and type_val.lower().strip() not in ("plain weave",):
        # Reject form alanı değerlerini de (Rubelli'de bilinmiyor henüz)
        first = type_val.lower().split()[0] if type_val else ""
        if first in [k for k, _ in WEAVE_KEYWORDS]:
            return type_val
    # Description'dan keyword ara
    for kw, _ in WEAVE_KEYWORDS:
        if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
            return kw
    return None


def _normalize_weave(raw: str | None) -> str | None:
    if not raw:
        return None
    low = raw.lower()
    for kw, norm in WEAVE_KEYWORDS:
        if kw in low:
            return norm
    return raw


def _extract_rubelli_description(text: str, product_name: str | None) -> str | None:
    if not text:
        return None
    cookie_kw = ["cookies", "social media features", "advertising"]
    if product_name:
        first_word = product_name.split()[0] if product_name else ""
        if first_word:
            m = re.search(
                rf"\b{re.escape(first_word)}\s+(?:is|combines|celebrates|has|features|offers|brings)[^\n]{{60,1000}}",
                text,
                re.IGNORECASE,
            )
            if m:
                full = m.group(0).strip()
                if not any(k in full.lower() for k in cookie_kw):
                    return full
    for line in text.split("\n"):
        line = line.strip()
        if 80 <= len(line) <= 1000 and not any(k in line.lower() for k in cookie_kw):
            return line
    return None


RUBELLI_CERT_KEYWORDS = [
    "CAL.TB117", "CAL TB117", "TB 117",
    "BS5852", "BS 5852", "BS5867",
    "M1", "M2", "DIN 4102",
    "NFPA 701", "NFPA701",
    "IMO MED", "IMO Part",
    "Italy Class 1", "UNI 9176", "UNI 9177",
    "Oekotex", "Oeko-Tex", "OEKO-TEX",
    "GRS", "Cradle to Cradle", "C2C",
    "REACH", "EU Ecolabel",
]


def _extract_rubelli_certifications(text: str, html: str) -> list:
    found = []
    source = (text or "") + " " + (html or "")
    for kw in RUBELLI_CERT_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", source, re.IGNORECASE):
            if kw not in found:
                found.append(kw)
    return found


def _extract_rubelli_gallery_images(html: str, product_code: str | None) -> list:
    """cdn.rubelli.com/A<kod>_<renk>/ pattern (yüksek çözünürlük)."""
    extra = []
    seen = set()
    # 840x840c versiyonlarını tercih et (modal/galeri büyük)
    pattern = rf"https://cdn\.rubelli\.com/A\d{{5,6}}_\d{{1,3}}/\d{{5,6}}_\d+\.(?:840x840c|x516|300x300c)\.jpg"
    for m in re.finditer(pattern, html, re.IGNORECASE):
        url = m.group(0)
        if url in seen:
            continue
        seen.add(url)
        # variant_code çıkar
        vm = re.search(r"/A(\d{5,6})_(\d{1,3})/", url)
        variant_code = f"{vm.group(1)}-{vm.group(2)}" if vm else None
        extra.append({
            "tip": "varyant" if variant_code else "detay",
            "kaynak_url": url,
            "varyant_adi": None,
            "_variant_code": variant_code,
        })
    return extra


def _extract_rubelli_variants(html: str, body_text: str, product_code: str | None) -> list:
    """Renk grid'inden SKU listesi."""
    variants = []
    if not product_code:
        return variants
    # HTML'de A<urun_kodu>_<renk_kodu> path'inden tüm renk kodlarını yakala
    seen = set()
    for m in re.finditer(rf"/A{product_code}_(\d{{1,3}})/", html):
        renk = m.group(1).zfill(3)
        if renk in seen:
            continue
        seen.add(renk)
        variants.append({
            "color_code": renk,
            "sku": f"{product_code}_{renk}",
            "name": None,
            "main_image_url": None,
        })
    return variants


def _scrape_variant_pages(page, base_url: str, variants_raw: list) -> list:
    """Rubelli her varyant aynı URL'de — color picker ile değişir; URL'de ?color=NNN dene."""
    if not variants_raw:
        return []
    enriched = []
    for v in variants_raw:
        renk = v.get("color_code")
        if not renk:
            enriched.append(v)
            continue
        # Rubelli URL'inde renk parametresi denemesi (?color=NNN)
        # Eğer çalışmazsa default sayfa hâlâ tüm renk URL'lerini içerir
        variant_url = f"{base_url}{'&' if '?' in base_url else '?'}color={renk}"
        try:
            page.goto(variant_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(500)
            vhtml = page.content()
            # Bu renk için yüksek çözünürlüklü ana görsel
            m = re.search(
                rf"https://cdn\.rubelli\.com/A\d{{5,6}}_{renk}/\d{{5,6}}_\d+\.(?:840x840c|x516)\.jpg",
                vhtml,
                re.IGNORECASE,
            )
            main_image = m.group(0) if m else None
            # Renk adı: Magento'da color picker alt text'inde olabilir
            mname = re.search(rf'data-color-name="([^"]+)"[^>]*A\d{{5,6}}_{renk}', vhtml)
            if not mname:
                mname = re.search(rf'A\d{{5,6}}_{renk}[^>]*alt="([^"]+)"', vhtml)
            name = mname.group(1) if mname else None

            enriched.append({
                "color_code": renk,
                "sku": v.get("sku"),
                "name": name,
                "main_image_url": main_image,
                "url": variant_url,
            })
        except Exception as e:
            enriched.append({**v, "_error": str(e)[:200]})
    return enriched
