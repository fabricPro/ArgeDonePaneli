"""Dedar scraper v1.1 — Cobra + Days Like Now denetiminden öğrenilen 7 düzeltme.

v1.0 → v1.1 değişiklikleri (2026-05-25):
1. width: Specifications tablosundan strict pattern (`Width\\nNNN cm`), SKU yanlış eşleşmesi giderildi
2. weave: 'Single sheet'/'Double sheet' form alanı reject; description'da leno/shantung/jacquard ara
3. description: cookie banner filtre + 80-1000 karakter aralık
4. lightfastness: ≥ ve zero-width-space karakterlerini handle et, "Lightfastness" + "Light fastness" alternatifleri
5. galeri: BigCommerce CDN pattern (cdn11.bigcommerce.com/s-td9auqdllx) + connect.dedar.com lifestyle ek toplama
6. variants_raw: body'den SKU son hane listesi (001, 002, ...) + DOM selectors
7. production_model: 'Current Stock' → stock, 'Article on request' → make_to_order

Kural #9: Mekanik veri toplama. AI inference YOK.
Kural #3: composition, width, certifications, country birebir; yoksa null.
Kural #8: sertifika ürün bazlı (marka geneli varsayım YASAK).
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

        # Cookie banner — adaptör v1.0 kuralı
        for sel in [
            "button:has-text('Use necessary cookies only')",
            "button:has-text('Reject')",
            "button:has-text('Decline')",
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
        page.wait_for_timeout(2000)

        # Specifications + Certifications accordion'ları aç
        for sel in [
            "button:has-text('Specifications')",
            "button:has-text('Certifications')",
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
            data["product_code"] = sku[:8]
            data["variant_code"] = sku[8:]
            data["sku_full"] = sku
        else:
            data["product_code"] = None
            data["variant_code"] = None
            data["sku_full"] = sku or None

        # Product name — h1 / og:title
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

        # Specifications — composition, country, usage (standart label-value)
        data["composition_text"] = _extract_label_value(body_text, "Composition")
        data["weight_raw"] = _extract_label_value(body_text, "Weight")
        data["repeat_raw"] = (
            _extract_label_value(body_text, "Pattern repeat")
            or _extract_label_value(body_text, "Rapporto")
        )
        data["usage_text"] = _extract_label_value(body_text, "Usage")
        data["country_of_origin"] = (
            _extract_label_value(body_text, "Made in")
            or _extract_label_value(body_text, "Country of origin")
        )

        # === Düzeltme 1: width — strict pattern (form alanı reject) ===
        data["width_raw"] = _extract_width_strict(body_text)
        data["width_cm"] = _parse_width(data["width_raw"])

        # === Düzeltme 2: weave — description'dan, form alanı reject ===
        weave_raw = _extract_weave_dedar(body_text)
        data["weave_type_raw"] = weave_raw
        data["weave_type"] = _normalize_weave(weave_raw)

        # === Düzeltme 3: description — cookie filter ===
        data["description_original"] = _extract_dedar_description(body_text, data.get("product_name"))

        # === Düzeltme 4: lightfastness — ≥ + zero-width-space ===
        data["lightfastness_raw"] = _extract_lightfastness(body_text)

        # === Düzeltme 7: production_model ===
        if re.search(r"Article on request", body_text, re.IGNORECASE):
            data["production_model"] = "make_to_order"
        elif re.search(r"Current Stock", body_text, re.IGNORECASE):
            data["production_model"] = "stock"
        else:
            data["production_model"] = "unknown"

        # Lead time
        lead_raw = _extract_label_value(body_text, "Production order lead time")
        if lead_raw:
            data["lead_time_raw"] = lead_raw
            m = re.search(r"(\d+)\s*week", lead_raw, re.IGNORECASE)
            if m:
                data["lead_time_days"] = int(m.group(1)) * 7
        else:
            data["lead_time_raw"] = None
            data["lead_time_days"] = None

        # Sertifika — ürün bazlı
        data["certifications"] = _extract_dedar_certifications(body_text, html)

        # === Düzeltme 6: variants_raw — body SKU listesi ===
        data["variants_raw"] = _extract_dedar_variants(html, body_text, data.get("product_code"))

        # Body preview (debug)
        data["_body_text_preview"] = body_text[:2000] if body_text else None

        # === Düzeltme 5: galeri — extract_image_specs + ek BigCommerce/connect.dedar ===
        base_images = extract_image_specs(page)
        extra_images = _extract_dedar_gallery_images(html)
        # Dedupe by URL
        seen_urls = {img["kaynak_url"] for img in base_images}
        for img in extra_images:
            if img["kaynak_url"] not in seen_urls:
                base_images.append(img)
                seen_urls.add(img["kaynak_url"])
        data["_image_specs"] = base_images

        browser.close()
        return data


# === Yardımcı fonksiyonlar ===


def _extract_label_value(text: str, label: str) -> str | None:
    """Generic label-value. Edge case: SKU eşleşmemesi için sayısal kontrol."""
    if not text:
        return None
    # 'Label: value'
    m = re.search(rf"{re.escape(label)}\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    if m:
        v = m.group(1).strip()
        if v and len(v) < 500 and v.lower() != label.lower():
            return v
    # 'Label\nvalue'
    m = re.search(rf"\b{re.escape(label)}\b\s*\n\s*([^\n]+)", text, re.IGNORECASE)
    if m:
        v = m.group(1).strip()
        if v and len(v) < 500 and v.lower() != label.lower():
            return v
    return None


def _extract_width_strict(text: str) -> str | None:
    """Width: Specifications tablosundan strict pattern.

    Form alanı 'TYPE\nSingle sheet\nDouble sheet\n Add window\nPROCEED' var Dedar'da;
    bu blok içindeki 'Width\ncm' tuzaktan kaçınılır.
    """
    if not text:
        return None
    # Pattern 1: 'Width\n<sayı> cm' — sayısal değer ZORUNLU
    matches = re.findall(r"\bWidth\s*\n\s*(\d+)\s*cm\b", text, re.IGNORECASE)
    if matches:
        # En son eşleşmeyi al (Specifications tablosu sayfanın altında)
        return f"{matches[-1]} cm"
    # Pattern 2: 'Width: <sayı> cm'
    m = re.search(r"\bWidth\s*[:\-]\s*(\d+)\s*cm\b", text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} cm"
    return None


def _parse_width(raw: str | None) -> float | None:
    if not raw:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*cm", raw, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


WEAVE_KEYWORDS = [
    # Specific dokuma adları (öncelik)
    ("leno weave", "leno"),
    ("leno", "leno"),
    ("jacquard weave", "jacquard"),
    ("jacquard", "jacquard"),
    ("shantung", "plain"),  # shantung = plain + slub iplik
    ("plain weave", "plain"),
    ("voile", "sheer"),
    ("velvet", "dobby"),
    ("boucle", "dobby"),
    ("embroidered", "jacquard"),
    ("embroidery", "jacquard"),
    ("twill", "dobby"),
    ("dobby", "dobby"),
    ("damask", "jacquard"),
]


# Form alanı değerleri — weave OLARAK reject
WEAVE_REJECT = ["single sheet", "double sheet", "transparency", "curtain", "fabric"]


def _extract_weave_dedar(text: str) -> str | None:
    """Description + Type alanı (ama form değerlerini reject)."""
    if not text:
        return None
    # 1) Önce Type label'ı bul, ama form alanı değil mi kontrol et
    type_val = _extract_label_value(text, "Type")
    if type_val and type_val.lower().strip() not in WEAVE_REJECT:
        return type_val
    # 2) Description (geniş paragraf) içinde dokuma keyword
    for kw, _ in WEAVE_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
            return kw
    return None


def _normalize_weave(raw: str | None) -> str | None:
    if not raw:
        return None
    low = raw.lower()
    for kw, norm in WEAVE_KEYWORDS:
        if kw in low:
            return norm
    if low in WEAVE_REJECT:
        return None
    return raw


def _extract_dedar_description(text: str, product_name: str | None) -> str | None:
    """Cookie banner filtre + marka adı/açıklama paragrafı."""
    if not text:
        return None

    cookie_kw = ["cookies", "social media features", "advertising", "analytics partners",
                 "personalise content", "this website uses"]

    # 1) Marka adıyla başlayan paragraf (en güvenilir)
    if product_name:
        # Sayfada "Cobra is a fire-retardant..." veya "Days Like Now celebrates..."
        # Product name kısa: "Cobra", "Days Like Now"
        first_word = product_name.split()[0] if product_name else ""
        if first_word:
            m = re.search(
                rf"\b{re.escape(first_word)}\s+(?:is|combines|celebrates|has|features|offers)[^\n]{{60,1000}}",
                text,
                re.IGNORECASE,
            )
            if m:
                full = m.group(0).strip()
                if not any(k in full.lower() for k in cookie_kw):
                    return full

    # 2) Fallback: 80-1000 karakter paragraf, cookie filter
    for line in text.split("\n"):
        line = line.strip()
        if 80 <= len(line) <= 1000 and not any(k in line.lower() for k in cookie_kw):
            return line

    return None


def _extract_lightfastness(text: str) -> str | None:
    """≥, ≧, > karakterleri + zero-width-space normalize."""
    if not text:
        return None
    # Zero-width-space + diğer görünmez karakterleri temizle
    text_clean = re.sub(r"[​‌‍﻿]", "", text)
    for label in ["Lightfastness", "Light fastness", "Light Fastness"]:
        # Label\n≥ N veya Label: ≥ N
        m = re.search(
            rf"\b{re.escape(label)}\b\s*[:\n]\s*[≥≧>=\s]*(\d+)",
            text_clean,
            re.IGNORECASE,
        )
        if m:
            return m.group(1)
    return None


DEDAR_CERT_KEYWORDS = [
    "IMO MED",
    "IMO Part. 7",
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


def _extract_dedar_gallery_images(html: str) -> list:
    """BigCommerce CDN + connect.dedar.com görselleri çek."""
    extra = []
    seen = set()

    # BigCommerce stencil CDN (Dedar): cdn11.bigcommerce.com/s-td9auqdllx/...
    for m in re.finditer(
        r'https://cdn11\.bigcommerce\.com/s-td9auqdllx/[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
        html,
        re.IGNORECASE,
    ):
        url = m.group(0)
        if url in seen:
            continue
        seen.add(url)
        # Boyut tahmin: URL'de stencil/1280x veya 2560w varsa "ana"
        if re.search(r"stencil/(\d{3,5})", url) and int(re.search(r"stencil/(\d{3,5})", url).group(1)) >= 800:
            tip = "detay"  # büyük resim ama varsayılan detay
        else:
            tip = "detay"
        extra.append({"tip": tip, "kaynak_url": url, "varyant_adi": None})

    # connect.dedar.com (lifestyle/inspiration)
    for m in re.finditer(
        r'https://connect\.dedar\.com/[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
        html,
        re.IGNORECASE,
    ):
        url = m.group(0)
        if url in seen:
            continue
        seen.add(url)
        extra.append({"tip": "lifestyle", "kaynak_url": url, "varyant_adi": None})

    return extra


def _extract_dedar_variants(html: str, body_text: str, product_code: str | None) -> list:
    """Body'den SKU son hane listesi (001, 002, ...) + DOM selectors."""
    variants = []
    seen_codes = set()

    # 1) DOM-based: data-product-attribute-value (Cobra'da boştu ama deneriz)
    for m in re.finditer(
        r'data-product-attribute-value="(\d+)"[^>]*data-sku="([^"]+)"', html
    ):
        attr_id, sku = m.group(1), m.group(2)
        if sku in seen_codes:
            continue
        seen_codes.add(sku)
        variants.append({"sku": sku, "attribute_id": attr_id, "color_suffix": sku[8:] if len(sku) >= 13 else None})

    # 2) Body'den ardışık ürün varyant kodları
    # Pattern Cobra: "Selected Colore is 4 duna\n004\n002"
    # Pattern DLN: "Selected Colore is 1 quarzo\n001\n002\n003\n004\n005\n006\n007\n008"
    # Stratejı: "Selected Colore" sonrası 1-2 satır boş, sonra ardışık 3-haneli kodlar
    m = re.search(r"Selected Colore[^\n]+\n([\d\n]+)", body_text or "")
    if m:
        codes_block = m.group(1).strip()
        for code_line in codes_block.split("\n"):
            code = code_line.strip()
            if not code.isdigit():
                continue
            # 1-3 haneli ürün varyant kodu (max 100 mantıklı sınır)
            if 0 < int(code) <= 999:
                code_padded = code.zfill(3)
                # Full SKU oluştur
                full_sku = (product_code or "") + "00" + code_padded if product_code else None
                if code_padded not in seen_codes:
                    seen_codes.add(code_padded)
                    variants.append({
                        "sku": full_sku,
                        "color_suffix": code_padded,
                        "attribute_id": None,
                    })

    return variants
