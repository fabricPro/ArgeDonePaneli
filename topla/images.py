"""Görsel tespit + indirme.

Kvadrat CDN: kvadrat-imageresizer.azureedge.net/iri/<UUID>?width=N&height=N&...
URL'deki width parametresi maks 2400'e çekilebilir (height düşür ki crop bozulmasın).

Selector ipuçları (Air Line sayfa inspection'ından):
- Varyant grid: img.product-color-picker__list-item-img — alt="<Brand> - <kod>"
- Lifestyle / Inspiration: .image-text-block__image
- Ana hero: galerideki ilk büyük (>=300px) img

Kural #3: tahmin yok — sınıflandırılamayan img atlanır.
"""

import os
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from PIL import Image, UnidentifiedImageError

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

MAX_BYTES = 20 * 1024 * 1024
TIMEOUT_SEC = 30
TARGET_WIDTH = 2400


def _pick_best_from_srcset(srcset):
    if not srcset:
        return None
    candidates = []
    for chunk in srcset.split(","):
        chunk = chunk.strip()
        m = re.match(r"(\S+)\s+(\d+)w", chunk)
        if m:
            candidates.append((int(m.group(2)), m.group(1)))
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[0])[1]


def _upgrade_kvadrat_url(url):
    if not url or "kvadrat-imageresizer" not in url:
        return url
    parts = urlsplit(url)
    qs = dict(parse_qsl(parts.query))
    if "width" in qs:
        qs["width"] = str(TARGET_WIDTH)
        # height + mode=crop birlikte aspect bozar — kaldır
        qs.pop("height", None)
        if qs.get("mode") == "crop":
            qs.pop("mode", None)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(qs), parts.fragment)
    )


def extract_image_specs(page):
    """Görsel inventory + lazy scroll tetikleme."""
    # Lazy-load için sayfayı 4 adımda scroll
    for i in range(1, 5):
        page.evaluate(
            f"window.scrollTo(0, document.body.scrollHeight * {i / 4})"
        )
        page.wait_for_timeout(800)
    page.wait_for_timeout(1500)
    # Geri yukarı scroll (galeri görselleri bazen yukarıda lazy-load olur)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)

    raw = page.evaluate(
        """
() => Array.from(document.querySelectorAll('img')).map(el => {
  const r = el.getBoundingClientRect();
  return {
    src: el.src || null,
    srcset: el.srcset || el.getAttribute('srcset') || null,
    dataSrc: el.getAttribute('data-src') || null,
    dataSrcset: el.getAttribute('data-srcset') || null,
    alt: el.alt || null,
    parentClass: el.parentElement ? el.parentElement.className : '',
    grandparentClass: el.parentElement && el.parentElement.parentElement ? el.parentElement.parentElement.className : '',
    width: Math.round(r.width),
    height: Math.round(r.height)
  };
})
"""
    )

    specs = []
    for el in raw:
        best = (
            _pick_best_from_srcset(el.get("srcset"))
            or _pick_best_from_srcset(el.get("dataSrcset"))
            or el.get("dataSrc")
            or el.get("src")
        )
        if not best:
            continue
        # Veri URI'leri at
        if best.startswith("data:"):
            continue
        best = _upgrade_kvadrat_url(best)

        pc = (el.get("parentClass") or "") + " " + (el.get("grandparentClass") or "")
        alt = el.get("alt") or None
        w = el.get("width") or 0

        if "product-color-picker" in pc:
            tip = "varyant"
        elif "image-text-block" in pc:
            tip = "lifestyle"
        elif w >= 300:
            tip = "ana"  # ilk büyük 'ana', sonrakileri 'detay' yapacağız
        elif w >= 100:
            tip = "detay"
        else:
            continue

        specs.append(
            {
                "tip": tip,
                "kaynak_url": best,
                "varyant_adi": alt if tip == "varyant" else None,
                "_observed_w": w,
            }
        )

    # İlk 'ana' kalsın, diğerleri 'detay'
    seen_ana = False
    for s in specs:
        if s["tip"] == "ana":
            if seen_ana:
                s["tip"] = "detay"
            else:
                seen_ana = True

    # Aynı URL iki kere olmasın
    seen_urls = set()
    deduped = []
    for s in specs:
        if s["kaynak_url"] in seen_urls:
            continue
        seen_urls.add(s["kaynak_url"])
        deduped.append(s)

    return deduped


def _ext_from_url(url):
    path = urlsplit(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    qs = dict(parse_qsl(urlsplit(url).query))
    fmt = qs.get("format", "").lower()
    if fmt in ("jpg", "jpeg"):
        return ".jpg"
    if fmt in ("png", "webp"):
        return f".{fmt}"
    return ".jpg"


def _read_dimensions(path: Path):
    try:
        with Image.open(path) as img:
            return img.width, img.height
    except (UnidentifiedImageError, OSError, Exception):
        return None, None


def _download_one(url, dst_path: Path):
    try:
        r = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            stream=True,
            timeout=TIMEOUT_SEC,
        )
        if r.status_code != 200:
            return {"indirme_durumu": f"atlandı:http_{r.status_code}"}

        content_len = r.headers.get("Content-Length")
        if content_len and int(content_len) > MAX_BYTES:
            return {"indirme_durumu": f"atlandı:too_large_{content_len}b"}

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = dst_path.with_suffix(dst_path.suffix + ".part")
        total = 0
        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                f.write(chunk)
                total += len(chunk)
                if total > MAX_BYTES:
                    f.close()
                    tmp_path.unlink(missing_ok=True)
                    return {"indirme_durumu": f"atlandı:exceeded_{total}b"}
        os.replace(tmp_path, dst_path)

        size_kb = round(total / 1024, 1)
        w, h = _read_dimensions(dst_path)
        return {
            "indirme_durumu": "indirildi",
            "dosya_boyutu_kb": size_kb,
            "genislik_px": w,
            "yukseklik_px": h,
        }
    except requests.RequestException as e:
        return {"indirme_durumu": f"atlandı:request_{type(e).__name__}"}
    except Exception as e:
        return {"indirme_durumu": f"atlandı:error_{type(e).__name__}"}


def download_all(specs, brand_slug, urun_slug, project_root: Path):
    if not specs:
        return []

    base_dir = (
        Path(project_root) / "topla" / "ham_cikti" / "gorseller" / brand_slug / urun_slug
    )
    base_dir.mkdir(parents=True, exist_ok=True)

    url_cache = set()
    result = []
    counters = {"ana": 0, "varyant": 0, "detay": 0, "lifestyle": 0}

    for spec in specs:
        tip = spec["tip"]
        url = spec["kaynak_url"]

        if url in url_cache:
            result.append(
                {
                    "tip": tip,
                    "kaynak_url": url,
                    "varyant_adi": spec.get("varyant_adi"),
                "_variant_code": spec.get("_variant_code"),
                "_variant_sku": spec.get("_variant_sku"),
                "_variant_image_idx": spec.get("_variant_image_idx"),
                "_variant_image_role": spec.get("_variant_image_role"),
                    "dosya_yolu": None,
                    "dosya_boyutu_kb": None,
                    "genislik_px": None,
                    "yukseklik_px": None,
                    "indirme_durumu": "atlandı:duplicate_url",
                }
            )
            continue

        counters[tip] += 1
        idx = counters[tip]
        ext = _ext_from_url(url)
        fname = f"{urun_slug}_{tip}_{idx:02d}{ext}"
        dst = base_dir / fname

        if dst.exists():
            url_cache.add(url)
            size_kb = round(dst.stat().st_size / 1024, 1)
            w, h = _read_dimensions(dst)
            result.append(
                {
                    "tip": tip,
                    "kaynak_url": url,
                    "varyant_adi": spec.get("varyant_adi"),
                "_variant_code": spec.get("_variant_code"),
                "_variant_sku": spec.get("_variant_sku"),
                "_variant_image_idx": spec.get("_variant_image_idx"),
                "_variant_image_role": spec.get("_variant_image_role"),
                    "dosya_yolu": str(dst).replace("\\", "/"),
                    "dosya_boyutu_kb": size_kb,
                    "genislik_px": w,
                    "yukseklik_px": h,
                    "indirme_durumu": "cached",
                }
            )
            continue

        dl = _download_one(url, dst)
        if dl["indirme_durumu"] in ("indirildi",):
            url_cache.add(url)
            dosya_yolu = str(dst).replace("\\", "/")
        else:
            dosya_yolu = None

        result.append(
            {
                "tip": tip,
                "kaynak_url": url,
                "varyant_adi": spec.get("varyant_adi"),
                "_variant_code": spec.get("_variant_code"),
                "_variant_sku": spec.get("_variant_sku"),
                "_variant_image_idx": spec.get("_variant_image_idx"),
                "_variant_image_role": spec.get("_variant_image_role"),
                "dosya_yolu": dosya_yolu,
                "dosya_boyutu_kb": dl.get("dosya_boyutu_kb"),
                "genislik_px": dl.get("genislik_px"),
                "yukseklik_px": dl.get("yukseklik_px"),
                "indirme_durumu": dl["indirme_durumu"],
            }
        )

    return result
