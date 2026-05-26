"""Faz 6.1: Batch aday kesfi — kategori sayfalarinda yeni urun URL'lerini diff'le.

Anayasa #6 disiplini: Bu modul SADECE on izleme yapar (ad, URL, kod, slug).
TAM veri cekimi + AI yorum: kullanici onayi + Claude denetim sonrasi
`python -m topla.cli <url>` ile tek tek calistirilir.

Kullanim:
    from topla.batch import run_batch
    sonuc = run_batch("nordik")  # kvadrat + sahco
    # Output: topla/ham_cikti/aday_nordik_<YYYYMMDD>.json

CLI:
    python -m topla.cli --batch nordik
    python -m topla.cli --batch italyan
    python -m topla.cli --batch alman

Bolgeler ve markalar (CLAUDE.md kadansi):
- nordik    -> kvadrat, sahco
- italyan   -> dedar, rubelli
- alman     -> zimmer_rohde, ado_goldkante, etamine, travers,
               nya_nordiska, creation_baumann
"""
import json
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
URUNLER_DIR = PROJECT_ROOT / "markalar" / "urunler"
HAM_CIKTI_DIR = PROJECT_ROOT / "topla" / "ham_cikti"
LOGS_DIR = PROJECT_ROOT / "topla" / "logs"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# Marka kayit defteri — region + kategori URL + URL pattern + scraper varligi
#
# product_url_regex: href icinde aranan pattern. Onceden hrefler extract edilir
# (re.findall href="..."), sonra her href bu pattern'le test edilir.
# Domain filter: relatif href'ler ve domain'a uyan absolute href'ler dahil.
BRANDS: dict[str, dict] = {
    "kvadrat": {
        "region": "nordik",
        "display": "Kvadrat",
        "domain": "kvadrat.dk",
        "category_url": "https://www.kvadrat.dk/en/products/curtains",
        # /en/products/curtains/5539-air-line (4-6 hane kod)
        "product_url_regex": (
            r"^/en/products/curtains/"
            r"(?P<code>\d{4,6})-(?P<slug>[a-z][a-z0-9-]+?)"
            r"(?:[/?#]|$)"
        ),
        "use_playwright": True,
        "has_scraper": True,
    },
    "sahco": {
        "region": "nordik",
        "display": "Sahco",
        "domain": "sahco.com",
        "category_url": "https://www.sahco.com/en/products/curtain",
        "product_url_regex": None,  # TODO Faz 7.x: site keşfi gerek
        "use_playwright": True,
        "has_scraper": False,
    },
    "dedar": {
        "region": "italyan",
        "display": "Dedar",
        "domain": "dedar.com",
        # /products/ ana sayfasi kurumsal grid (urun listesi DEGIL).
        # Asil urunler alt-kategori sayfalarinda. Cobra = indoor-outdoor,
        # Days Like Now = curtain (silk sheer).
        "category_urls": [
            "https://dedar.com/products/curtain/",
            "https://dedar.com/products/sheer/",
            "https://dedar.com/products/indoor-outdoor/",
            "https://dedar.com/products/fire-retardant/",
            "https://dedar.com/products/jacquard/",
        ],
        # /cobra/ veya /days-like-now/ — slug-only, kod yok
        # Non-product slugs blacklist (kurumsal sayfalar)
        "product_url_regex": (
            r"^/"
            r"(?!products|account|cart|search|checkout|wishlist|contact"
            r"|about|blog|news|press|support|login|register|newsletter"
            r"|projects|inspiration|company|download|moodboards|history"
            r"|governance|responsibility|legal-notes|payments|careers"
            r"|sustainability|certifications|stories|magazine|catalogue"
            r"|catalogues|stores|store-locator|where-to-buy"
            r"|fr/|en/|it/|de/|es/|cookie|privacy|terms|wp-|static|assets"
            r"|img/|images/|api/|sitemap|category|categories|shop)"
            r"(?P<slug>[a-z][a-z0-9-]+)/"
            r"(?:\?sku=(?P<code>[A-Z0-9]+))?(?:[?#]|$)"
        ),
        "use_playwright": True,
        "has_scraper": True,
    },
    "rubelli": {
        "region": "italyan",
        "display": "Rubelli",
        "domain": "rubelli.com",
        # /en/textiles tum tekstilleri listeler (adaptorler/rubelli.md referans)
        "category_url": "https://www.rubelli.com/en/textiles",
        # /en/<slug>-<5haneli-kod>
        "product_url_regex": (
            r"^/en/"
            r"(?P<slug>[a-z][a-z0-9-]+?)-(?P<code>\d{5})(?!\d)"
        ),
        "use_playwright": True,
        "has_scraper": True,
    },
    "zimmer_rohde": {
        "region": "alman",
        "display": "Zimmer + Rohde",
        "domain": "zimmer-rohde.com",
        "category_url": (
            "https://www.zimmer-rohde.com/en/product-finder"
            "?brand=zimmer-rohde&category=curtains"
        ),
        # /en/product-finder/details/melange-linen-10969-980 (5-hane kod)
        "product_url_regex": (
            r"^/en/product-finder/details/"
            r"(?P<slug>[a-z0-9-]+?)-(?P<code>\d{5})(?!\d)(?:-\d{3})?"
        ),
        "use_playwright": False,
        "has_scraper": True,
    },
    "ado_goldkante": {
        "region": "alman",
        "display": "ADO Goldkante",
        "domain": "zimmer-rohde.com",
        "category_url": (
            "https://www.zimmer-rohde.com/en/product-finder"
            "?brand=ado-goldkante&category=curtains"
        ),
        # 4-haneli kod (Z+R 5-haneli ile karismaz)
        "product_url_regex": (
            r"^/en/product-finder/details/"
            r"(?P<slug>[a-z0-9-]+?)-(?P<code>\d{4})(?!\d)(?:-\d{3})?"
        ),
        "use_playwright": False,
        "has_scraper": True,
    },
    "etamine": {
        "region": "alman",
        "display": "Etamine",
        "domain": "zimmer-rohde.com",
        "category_url": (
            "https://www.zimmer-rohde.com/en/product-finder"
            "?brand=etamine&category=curtains"
        ),
        "product_url_regex": (
            r"^/en/product-finder/details/"
            r"(?P<slug>[a-z0-9-]+?)-(?P<code>\d{5})(?!\d)(?:-\d{3})?"
        ),
        "use_playwright": False,
        "has_scraper": True,
    },
    "travers": {
        "region": "alman",
        "display": "Travers",
        "domain": "zimmer-rohde.com",
        "category_url": (
            "https://www.zimmer-rohde.com/en/product-finder"
            "?brand=travers&category=curtains"
        ),
        "product_url_regex": (
            r"^/en/product-finder/details/"
            r"(?P<slug>[a-z0-9-]+?)-(?P<code>\d{5})(?!\d)(?:-\d{3})?"
        ),
        "use_playwright": False,
        "has_scraper": True,
    },
    "nya_nordiska": {
        "region": "alman",
        "display": "Nya Nordiska",
        "domain": "nya-nordiska.com",
        "category_url": "https://www.nya-nordiska.com/en/products/curtain",
        "product_url_regex": None,  # TODO
        "use_playwright": True,
        "has_scraper": False,
    },
    "creation_baumann": {
        "region": "alman",
        "display": "Creation Baumann",
        "domain": "creationbaumann.com",
        "category_url": "https://www.creationbaumann.com/en/products/curtain",
        "product_url_regex": None,  # TODO
        "use_playwright": True,
        "has_scraper": False,
    },
}


def existing_product_keys(brand_slug: str) -> set[str]:
    """`markalar/urunler/<brand>_<key>.json` dosyalarindan `<key>` set'i.

    Key formati: `<code>-<slug>` (orn. `5539-air-line`, `00T19063-cobra`).
    """
    keys: set[str] = set()
    if not URUNLER_DIR.exists():
        return keys
    for jp in URUNLER_DIR.glob(f"{brand_slug}_*.json"):
        stem = jp.stem  # kvadrat_5539-air-line
        prefix = brand_slug + "_"
        if stem.startswith(prefix):
            keys.add(stem[len(prefix):])
    return keys


def existing_slugs(brand_slug: str) -> set[str]:
    """Sadece slug kismini (Dedar gibi kategori sayfasinda kod yoksa kullanilir)."""
    slugs: set[str] = set()
    for key in existing_product_keys(brand_slug):
        # key = "code-slug" -> slug = key.split("-", 1)[1] but slug may contain "-"
        parts = key.split("-", 1)
        if len(parts) == 2:
            slugs.add(parts[1])
        else:
            slugs.add(parts[0])
    return slugs


def fetch_html_requests(url: str, timeout: int = 30) -> str | None:
    """requests ile HTML cek. 429 -> 5/10/20 sn backoff retry."""
    import time
    for backoff in [0, 5, 10, 20]:
        if backoff:
            time.sleep(backoff)
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            if r.status_code == 200:
                return r.text
            if r.status_code != 429:
                return None
        except Exception:
            return None
    return None


def fetch_html_playwright(url: str, wait_ms: int = 3500) -> str | None:
    """Playwright ile HTML cek (SPA siteleri icin)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=USER_AGENT)
            page = ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(wait_ms)
            html = page.content()
            browser.close()
            return html
    except Exception:
        return None


def _resolve_category_urls(brand_slug: str) -> list[str]:
    """Spec'ten kategori URL'lerini cek (tek 'category_url' veya liste 'category_urls')."""
    spec = BRANDS[brand_slug]
    if "category_urls" in spec:
        urls = spec["category_urls"]
        if isinstance(urls, list):
            return urls
    if "category_url" in spec:
        return [spec["category_url"]]
    return []


def fetch_category_html(brand_slug: str) -> str | None:
    """Tek kategori URL'i icin HTML. Birden fazla URL varsa hepsini birlestir."""
    urls = _resolve_category_urls(brand_slug)
    if not urls:
        return None
    spec = BRANDS[brand_slug]
    parts: list[str] = []
    for url in urls:
        html: str | None = None
        if spec["use_playwright"]:
            html = fetch_html_playwright(url)
        if not html:
            html = fetch_html_requests(url)
        if html:
            parts.append(html)
    return "\n".join(parts) if parts else None


def _normalize_to_path(href: str) -> str | None:
    """href'i path'e cevir (kendi domain'inden gelenler icin).

    Donus: '/en/products/...' veya None (cross-domain).
    """
    if href.startswith("//"):
        href = "https:" + href
    if href.startswith("http"):
        from urllib.parse import urlparse
        p = urlparse(href)
        return p.path + (("?" + p.query) if p.query else "")
    if href.startswith("/"):
        return href
    return None  # relative path veya javascript:, mailto: vs.


def _find_thumbnail_near_href(html: str, href: str) -> str | None:
    """HTML'de href'in yakınındaki img src'i bul (kategori card thumbnail)."""
    # Pattern: <a href="HREF"...><img src="THUMB"...>  veya tersi
    # Çok büyük HTML için sadece href'in etrafındaki 800 char penceresi ara
    idx = html.find(href)
    if idx < 0:
        return None

    window = html[max(0, idx - 800):idx + 800]
    # img src + data-src
    img_pats = [
        r'<img[^>]+(?:data-src|data-original|srcset)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
        r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
    ]
    for pat in img_pats:
        m = re.search(pat, window, re.IGNORECASE)
        if m:
            thumb = m.group(1)
            # srcset birden fazla URL içerir, ilkini al
            if "," in thumb:
                thumb = thumb.split(",")[0].strip().split(" ")[0]
            return thumb
    return None


def extract_product_urls(brand_slug: str, html: str) -> list[dict]:
    """HTML'den href'leri extract et, her birini brand pattern'i ile test et."""
    spec = BRANDS[brand_slug]
    pattern_str = spec.get("product_url_regex")
    if not pattern_str:
        return []

    pattern = re.compile(pattern_str, re.IGNORECASE)
    domain = spec.get("domain", "").lower()

    # Tum href= attribute'larini topla
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)

    # Ayrica raw text icinde gozuken URL'leri de yakala (Vue.js state vs.)
    # (data attribute, JSON-LD vs. icin)
    extras = re.findall(
        r'(?:["\']|>)((?:https?://[a-zA-Z0-9.-]+)?/[a-zA-Z0-9/_?=&#%-]+)(?=["\'<])',
        html,
    )
    all_candidates = list(hrefs) + list(extras)

    seen: set[str] = set()
    products: list[dict] = []
    for raw in all_candidates:
        # Cross-domain filter: absolute href'ler kendi domain'inde mi?
        if raw.startswith("http"):
            if domain and domain not in raw.lower():
                continue
        path = _normalize_to_path(raw)
        if path is None:
            continue

        m = pattern.search(path)
        if not m:
            continue
        d = m.groupdict()
        code = d.get("code") or ""
        slug = d.get("slug") or ""
        if not slug:
            continue
        key = f"{code}-{slug}" if code else slug
        if key in seen:
            continue
        seen.add(key)

        # Tam URL olarak normalize (ilk kategori URL'i base)
        base_urls = _resolve_category_urls(brand_slug)
        base = base_urls[0] if base_urls else f"https://{domain}"
        full_url = urljoin(base, path)

        # Thumbnail extract (kategori sayfasından)
        thumb = _find_thumbnail_near_href(html, raw)
        if thumb:
            if thumb.startswith("//"):
                thumb = "https:" + thumb
            elif thumb.startswith("/"):
                thumb = urljoin(base, thumb)

        products.append({
            "url": full_url,
            "code": code or None,
            "slug": slug,
            "key": key,
            "thumbnail": thumb,
        })
    return products


def diff_with_existing(brand_slug: str, discovered: list[dict]) -> dict:
    """Discovered URL listesi ile mevcut markalar/urunler/ dosyalarini kiyasla."""
    existing_keys = existing_product_keys(brand_slug)
    existing_slug_set = existing_slugs(brand_slug)

    yeni: list[dict] = []
    bilinen: list[dict] = []

    for prod in discovered:
        code = prod["code"]
        slug = prod["slug"]
        # Kod varsa code-slug ile eslestir (Kvadrat/Z+R/Rubelli)
        if code:
            key = f"{code}-{slug}"
            if key in existing_keys:
                bilinen.append({**prod, "match_type": "code-slug"})
                continue
        # Slug fallback (Dedar)
        if slug in existing_slug_set:
            bilinen.append({**prod, "match_type": "slug-only"})
            continue
        yeni.append(prod)

    return {
        "yeni": yeni,
        "bilinen": bilinen,
        "mevcut_dosya_sayisi": len(existing_keys),
    }


def discover_brand(brand_slug: str) -> dict:
    """Tek marka icin aday kesfi yap."""
    spec = BRANDS.get(brand_slug)
    if not spec:
        return {
            "brand_slug": brand_slug,
            "status": "unknown_brand",
            "error": f"BRANDS kaydinda yok: {brand_slug}",
        }

    category_urls = _resolve_category_urls(brand_slug)
    if not spec.get("product_url_regex"):
        return {
            "brand_slug": brand_slug,
            "status": "no_url_pattern",
            "category_urls": category_urls,
            "note": (
                f"{spec['display']} URL pattern'i henuz tanimli degil "
                "(Faz 7.x: site kesfi gerek)."
            ),
        }

    html = fetch_category_html(brand_slug)
    if not html:
        return {
            "brand_slug": brand_slug,
            "status": "fetch_failed",
            "category_urls": category_urls,
            "error": "Kategori sayfasi cekilemedi (requests + Playwright fallback)",
        }

    discovered = extract_product_urls(brand_slug, html)
    diff = diff_with_existing(brand_slug, discovered)

    return {
        "brand_slug": brand_slug,
        "display": spec["display"],
        "category_urls": category_urls,
        "status": "ok",
        "html_length": len(html),
        "toplam_kesfedilen": len(discovered),
        "yeni_aday_sayisi": len(diff["yeni"]),
        "bilinen_urun_sayisi": len(diff["bilinen"]),
        "mevcut_jsonn_sayisi": diff["mevcut_dosya_sayisi"],
        "yeni_adaylar": diff["yeni"],
        "bilinen_urunler": diff["bilinen"],
    }


def run_batch(region: str) -> dict:
    """Bir bolgenin tum markalari icin aday kesfi yap, ham_cikti'ya yaz."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    date_only = datetime.now(timezone.utc).strftime("%Y%m%d")
    HAM_CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    brands_in_region = [b for b, s in BRANDS.items() if s["region"] == region]
    if not brands_in_region:
        return {
            "region": region,
            "status": "unknown_region",
            "error": f"Bilinen bolgeler: {sorted({s['region'] for s in BRANDS.values()})}",
        }

    sonuclar: dict[str, dict] = {}
    toplam_yeni = 0
    toplam_bilinen = 0
    hata_sayisi = 0

    for brand_slug in brands_in_region:
        print(f"[batch] {brand_slug} kesif basliyor...", flush=True)
        try:
            sonuc = discover_brand(brand_slug)
        except Exception as e:
            sonuc = {
                "brand_slug": brand_slug,
                "status": "exception",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
        sonuclar[brand_slug] = sonuc

        if sonuc.get("status") == "ok":
            yeni_n = sonuc.get("yeni_aday_sayisi", 0)
            bilinen_n = sonuc.get("bilinen_urun_sayisi", 0)
            toplam_yeni += yeni_n
            toplam_bilinen += bilinen_n
            print(
                f"  -> {sonuc['display']}: {yeni_n} yeni aday, "
                f"{bilinen_n} bilinen, mevcut JSON: {sonuc['mevcut_jsonn_sayisi']}",
                flush=True,
            )
        else:
            hata_sayisi += 1
            print(
                f"  -> {brand_slug}: {sonuc.get('status')}"
                + (f" — {sonuc.get('error', '')}" if sonuc.get("error") else ""),
                flush=True,
            )

    rapor = {
        "region": region,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "marka_sayisi": len(brands_in_region),
        "toplam_yeni_aday": toplam_yeni,
        "toplam_bilinen": toplam_bilinen,
        "hata_sayisi": hata_sayisi,
        "marka_sonuclari": sonuclar,
    }

    out_path = HAM_CIKTI_DIR / f"aday_{region}_{date_only}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)

    # Log dosyasi
    log_path = LOGS_DIR / f"batch_{region}_{date_only}.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n=== {datetime.now(timezone.utc).isoformat()} ===\n")
        f.write(f"Bolge: {region}, Marka: {len(brands_in_region)}\n")
        f.write(f"Yeni aday: {toplam_yeni}, Bilinen: {toplam_bilinen}, Hata: {hata_sayisi}\n")
        f.write(f"Cikti: {out_path.name}\n")

    print(f"\n[batch] Tamamlandi: {out_path}")
    print(f"  Toplam yeni aday: {toplam_yeni}")
    print(f"  Toplam bilinen: {toplam_bilinen}")
    print(f"  Hata: {hata_sayisi}")

    return rapor


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanim: python -m topla.batch <bolge>", file=sys.stderr)
        print("Bolgeler: nordik, italyan, alman", file=sys.stderr)
        sys.exit(2)
    run_batch(sys.argv[1])
