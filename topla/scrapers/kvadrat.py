"""Kvadrat scraper. Adaptör v1.2 mantığı.

Kural #9: Sadece mekanik veri toplama. AI inference YOK.
Kural #3: composition, width, certifications, country sayfadan birebir
         alınır; yoksa null. Asla tahmin yapma.
"""

import re
from playwright.sync_api import sync_playwright

from topla.images import extract_image_specs

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def scrape_kvadrat(url: str) -> dict:
    from topla.scrapers._browser import launch_chromium
    with sync_playwright() as p:
        browser = launch_chromium(p, headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Cookie banner — "Reject all" (adaptör v1.2 kuralı)
        for sel in [
            "button:has-text('Reject all')",
            "button:has-text('Reject')",
            "button:has-text('Decline')",
        ]:
            try:
                page.click(sel, timeout=2000)
                break
            except Exception:
                continue

        # Vue.js render bekle
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(2500)

        # Accordion'ları aç — sertifika/sustainability bölümleri için
        for sel in [
            "button:has-text('Certificates and manuals')",
            "button:has-text('Sustainability')",
            "button:has-text('Performance')",
            "button:has-text('Show more')",
        ]:
            try:
                btn = page.locator(sel).first
                if btn.is_visible():
                    btn.click(timeout=2000)
                    page.wait_for_timeout(500)
            except Exception:
                continue

        html = page.content()
        data = {}

        # URL'den kod + slug
        m = re.search(r"/curtains/(\d{4,5})-([a-z0-9-]+)", url)
        if m:
            data["product_code"] = m.group(1)
            data["product_slug"] = m.group(2)
        else:
            data["product_slug"] = "unknown"

        data["brand"] = "Kvadrat"

        # Product name — h1
        try:
            data["product_name"] = page.locator("h1").first.inner_text(timeout=5000).strip()
        except Exception:
            data["product_name"] = None

        # Plain text içeriği (etiketleri arıyoruz)
        try:
            body_text = page.locator("body").inner_text(timeout=5000)
        except Exception:
            body_text = ""

        data["composition_text"] = _extract_label_value(body_text, "Composition")
        width_raw = _extract_label_value(body_text, "Width")
        data["width_raw"] = width_raw
        data["width_cm"] = _parse_width(width_raw)
        data["weight_raw"] = _extract_label_value(body_text, "Weight")
        weave_raw = (
            _extract_label_value(body_text, "Binding")
            or _extract_label_value(body_text, "Construction")
            or _extract_label_value(body_text, "Weave")
        )
        data["weave_type_raw"] = weave_raw
        data["weave_type"] = _normalize_weave(weave_raw)
        data["usage_text"] = _extract_label_value(body_text, "Use")
        data["country_of_origin"] = (
            _extract_label_value(body_text, "Made in")
            or _extract_label_value(body_text, "Country of origin")
            or _extract_label_value(body_text, "Origin")
        )

        # Sertifika — adaptör v1.2 kuralı: marka geneli varsayım YASAK,
        # sayfada birebir bulunanı al.
        data["certifications"] = _extract_certifications(body_text, html)

        # Sayfa metnini de sakla (debug için)
        data["_body_text_preview"] = body_text[:2000] if body_text else None

        # Görsel inventarı (browser kapanmadan önce — sayfayı scroll edip topla)
        data["_image_specs"] = extract_image_specs(page)

        browser.close()
        return data


def _extract_label_value(text: str, label: str) -> str | None:
    """'Label: value' veya 'Label\\nvalue' paterni ara."""
    if not text:
        return None
    # 'Label: value' formatı
    m = re.search(
        rf"{re.escape(label)}\s*[:\-]\s*([^\n]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        value = m.group(1).strip()
        if value and len(value) < 500:
            return value
    # 'Label\nvalue' formatı (yeni satır ayraçlı tablo)
    m = re.search(
        rf"\b{re.escape(label)}\b\s*\n\s*([^\n]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        value = m.group(1).strip()
        if value and len(value) < 500 and value.lower() != label.lower():
            return value
    return None


def _parse_width(width_raw: str | None) -> float | None:
    if not width_raw:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*cm", width_raw, re.IGNORECASE)
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
}


def _normalize_weave(raw: str | None) -> str | None:
    if not raw:
        return None
    low = raw.lower()
    for key, val in WEAVE_MAP.items():
        if key in low:
            return val
    return raw


CERT_KEYWORDS = [
    "EU Ecolabel",
    "OEKO-TEX",
    "Oeko-Tex",
    "Cradle to Cradle",
    "GRS",
    "BS 5852",
    "BS5867",
    "NFPA 701",
    "NFPA701",
    "IMO MED",
    "Italy Class 1",
    "PFAS-free",
    "PFAS free",
    "REACH",
    "Prop 65",
    "LBC Red List",
    "Living Building Challenge",
]


def _extract_certifications(text: str, html: str) -> list:
    found = []
    source = (text or "") + " " + (html or "")
    for kw in CERT_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", source, re.IGNORECASE):
            if kw not in found:
                found.append(kw)
    return found
