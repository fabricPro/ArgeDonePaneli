"""Dedar scraper. Adaptör v1.0 (`adaptorler/dedar.md`) mantığı.

Platform: BigCommerce stencil, görseller cdn11.bigcommerce.com/s-td9auqdllx/...
URL pattern: https://dedar.com/{urun-slug}/?sku={sku-kod}
  - product_code = SKU ilk 8 hane (örn. "00T19063" Cobra)
  - variant_code = SKU son 5 hane (örn. "00004" Linen,Beige)

Kural #9: Sadece mekanik veri toplama. AI inference YOK.
Kural #3: composition, width, certifications, country sayfadan birebir;
         yoksa null. Asla tahmin yapma.
Kural #8 (sertifika ürün bazli): Marka geneli sertifika varsayımı YASAK
         (eski v0 adaptör hatası). Her ürün için sayfadaki Certifications
         bölümünü birebir okuyup kaydet.
"""

import re
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

from topla.images import extract_image_specs

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def scrape_dedar(url: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Cookie banner — adaptör v1.0 kuralı: "necessary cookies only"
        for sel in [
            "button:has-text('Use necessary cookies only')",
            "button:has-text('Reject')",
            "button:has-text('Decline')",
            "button:has-text('Only necessary')",
        ]:
            try:
                page.click(sel, timeout=2000)
                break
            except Exception:
                continue

        # Cloudflare challenge varsa bekle
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(2000)

        # Specifications accordion'unu aç (varsa)
        for sel in [
            "button:has-text('Specifications')",
            "button:has-text('Certifications')",
            "button:has-text('Maintenance')",
            "summary:has-text('Specifications')",
            "summary:has-text('Certifications')",
        ]:
            try:
                btn = page.locator(sel).first
                if btn.is_visible():
                    btn.click(timeout=2000)
                    page.wait_for_timeout(400)
            except Exception:
                continue

        html = page.content()
        data: dict = {"brand": "Dedar"}

        # URL'den slug + SKU
        parsed = urlparse(url)
        slug_match = re.match(r"^/([a-z0-9-]+)/?$", parsed.path)
        data["product_slug"] = slug_match.group(1) if slug_match else "unknown"

        qs = parse_qs(parsed.query)
        sku = (qs.get("sku") or [""])[0]
        if sku and len(sku) >= 13:
            data["product_code"] = sku[:8]  # 00T19063
            data["variant_code"] = sku[8:]  # 00004
            data["sku_full"] = sku
        else:
            data["product_code"] = None
            data["variant_code"] = None
            data["sku_full"] = sku or None

        # Product name — h1 veya og:title
        try:
            data["product_name"] = page.locator("h1").first.inner_text(timeout=5000).strip()
        except Exception:
            data["product_name"] = None
        if not data["product_name"]:
            m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
            if m:
                data["product_name"] = m.group(1).strip()

        # Body text
        try:
            body_text = page.locator("body").inner_text(timeout=5000)
        except Exception:
            body_text = ""

        # Specifications tablosu — label/value paterni
        data["composition_text"] = _extract_label_value(body_text, "Composition")
        width_raw = _extract_label_value(body_text, "Width")
        data["width_raw"] = width_raw
        data["width_cm"] = _parse_width(width_raw)
        data["weight_raw"] = _extract_label_value(body_text, "Weight")
        data["repeat_raw"] = (
            _extract_label_value(body_text, "Pattern repeat")
            or _extract_label_value(body_text, "Rapporto")
            or _extract_label_value(body_text, "Repeat")
        )
        # Dedar bazen Type vermez; açıklamada leno/jacquard geçer
        weave_raw = (
            _extract_label_value(body_text, "Type")
            or _extract_label_value(body_text, "Construction")
            or _extract_label_value(body_text, "Weave")
            or _find_weave_in_description(body_text)
        )
        data["weave_type_raw"] = weave_raw
        data["weave_type"] = _normalize_weave(weave_raw)
        data["usage_text"] = _extract_label_value(body_text, "Usage")
        data["country_of_origin"] = (
            _extract_label_value(body_text, "Made in")
            or _extract_label_value(body_text, "Country of origin")
            or _extract_label_value(body_text, "Origin")
        )
        data["lightfastness_raw"] = _extract_label_value(body_text, "Light fastness")

        # Production model — "Article on request" varsa make_to_order
        if re.search(r"Article on request", body_text, re.IGNORECASE):
            data["production_model"] = "make_to_order"
        else:
            data["production_model"] = "unknown"

        # Lead time — "Production order lead time"
        lead_raw = _extract_label_value(body_text, "Production order lead time")
        if lead_raw:
            data["lead_time_raw"] = lead_raw
            m = re.search(r"(\d+)\s*week", lead_raw, re.IGNORECASE)
            if m:
                data["lead_time_days"] = int(m.group(1)) * 7
        else:
            data["lead_time_raw"] = None
            data["lead_time_days"] = None

        # Sertifika — adaptör kural: ürün bazlı, sayfada birebir
        data["certifications"] = _extract_dedar_certifications(body_text, html)

        # Açıklama — ilk paragraf (description_original)
        data["description_original"] = _extract_description(body_text)

        # Varyantlar (radio button SKU listesi) — Cobra'da 2 varyant tipik
        data["variants_raw"] = _extract_variants(html, body_text)

        # Body preview (debug)
        data["_body_text_preview"] = body_text[:2000] if body_text else None

        # Görseller (BigCommerce CDN'den)
        data["_image_specs"] = extract_image_specs(page)

        browser.close()
        return data


def _extract_label_value(text: str, label: str) -> str | None:
    """Kvadrat scraper ile aynı pattern."""
    if not text:
        return None
    m = re.search(rf"{re.escape(label)}\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    if m:
        v = m.group(1).strip()
        if v and len(v) < 500:
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


WEAVE_MAP = {
    "plain weave": "plain",
    "plain": "plain",
    "twill": "dobby",
    "jacquard": "jacquard",
    "leno": "leno",
    "voile": "sheer",
    "sheer": "sheer",
    "boucle": "dobby",
    "dobby": "dobby",
    "velvet": "dobby",
    "embroidery": "jacquard",
    "embroidered": "jacquard",
}


def _normalize_weave(raw: str | None) -> str | None:
    if not raw:
        return None
    low = raw.lower()
    for key, val in WEAVE_MAP.items():
        if key in low:
            return val
    return raw


def _find_weave_in_description(text: str) -> str | None:
    """Dedar açıklamada 'leno weave', 'jacquard', 'plain weave' geçebilir."""
    if not text:
        return None
    for kw in ["leno weave", "jacquard weave", "plain weave", "velvet", "boucle", "leno"]:
        if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
            return kw
    return None


# Dedar Cobra denetiminden gözlenmiş sertifika anahtar kelimeleri
DEDAR_CERT_KEYWORDS = [
    # Denizcilik
    "IMO MED",
    "IMO Part. 7",
    # Pazar-özel FR
    "Italy Class 1",
    "UNI 9176",
    "UNI 9177",
    "BS5867/2/B",
    "BS5867",
    "BS 5852",
    "NFPA 701",
    "NFPA701",
    "M1",
    "DIN 4102",
    # Sürdürülebilirlik
    "Oekotex",
    "Oeko-Tex",
    "OEKO-TEX",
    "GRS",
    "Cradle to Cradle",
    "C2C",
    "REACH",
    "EU Ecolabel",
]


def _extract_dedar_certifications(text: str, html: str) -> list:
    found = []
    source = (text or "") + " " + (html or "")
    for kw in DEDAR_CERT_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", source, re.IGNORECASE):
            if kw not in found:
                found.append(kw)
    return found


def _extract_description(text: str) -> str | None:
    """Dedar ürün açıklaması — sayfada büyük paragraf, hikaye odaklı."""
    if not text:
        return None
    # Cobra örneği: "Cobra is a fire-retardant outdoor sheer..."
    # Strateji: 200-800 karakterlik bir paragraf yakala
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if 80 <= len(line) <= 800 and not re.match(r"^[A-Z][a-z]+:", line):
            return line
    return None


def _extract_variants(html: str, text: str) -> list:
    """Radio button SKU listesi + isim. Strict değil — Claude denetim sonra refine eder."""
    variants = []
    # BigCommerce stencil: <input type="radio" ... value="..."> + label
    # Bu kalıp her temada farklı, basit regex deneyelim
    matches = re.findall(
        r'data-product-attribute-value="(\d+)"[^>]*data-sku="([^"]+)"',
        html,
    )
    for attr_id, sku in matches:
        variants.append({"sku": sku, "attribute_id": attr_id})
    if not variants:
        # Alternatif: text'ten "00T..." formatlı SKU'lar
        for m in re.finditer(r"\b(\d{2}[A-Z]\d{4,5}\d{5})\b", text or ""):
            variants.append({"sku": m.group(1), "attribute_id": None})
    return variants
