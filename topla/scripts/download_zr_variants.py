"""Faz 5.13: Z+R Group urunleri icin tum renk varyanti gorsellerini indir.

Sorun: Documents iterasyonunda indir.ps1 her urun icin sadece 1-2 renk URL'i
hardcoded — gercekte 5-17 renk var, gorseller eksik. JSON DB'de variant entry
hepsi var ama disk'te dosya yok.

Cozum: Z+R sayfalarinda her rengin ayri URL'i var
(/en/product-finder/details/<slug>-<urun>-<renk>). Her renk URL'sine Playwright
ile git, csm_<urun><renk>_<sira>_<hash>.jpg pattern'lerini regex ile cek,
requests ile gorseller/<marka>/<urun>/<renk>_<sira>.jpg'a indir, JSON guncelle.

Kullanim:
  .venv\\Scripts\\python.exe topla\\scripts\\download_zr_variants.py \\
      ado_goldkante 3150 capri-plus

Veya tum eksik Z+R Group urunlerini (default):
  .venv\\Scripts\\python.exe topla\\scripts\\download_zr_variants.py
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

GORSELLER = PROJECT_ROOT / "gorseller"
URUNLER = PROJECT_ROOT / "markalar" / "urunler"
NOW = "2026-05-26T03:00:00Z"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

BASE = "https://www.zimmer-rohde.com"


_cookie_handled = {"done": False}


def fetch_variant_images(page, urun_slug: str, urun_kodu: str, renk_kodu: str, debug: bool = False) -> list[str]:
    """Tek bir renk URL'sine git, csm CDN URL'lerini topla."""
    url = f"{BASE}/en/product-finder/details/{urun_slug}-{urun_kodu}-{renk_kodu}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"    HATA: {renk_kodu} sayfa yuklenmedi: {e}")
        return []

    # Cookie banner — ilk sayfada bir kez
    if not _cookie_handled["done"]:
        for sel in [
            "button:has-text('Accept all')",
            "button:has-text('Accept')",
            "button:has-text('Akzeptieren')",
            "button:has-text('Reject')",
            "button:has-text('Only necessary')",
        ]:
            try:
                page.click(sel, timeout=2000)
                _cookie_handled["done"] = True
                print(f"    Cookie banner kapatildi: {sel}")
                break
            except Exception:
                continue
        _cookie_handled["done"] = True  # bir daha denenmesin

    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    page.wait_for_timeout(1500)  # Vue render icin bekle

    html = page.content()

    if debug:
        debug_path = Path("debug_zr_html.html")
        debug_path.write_text(html, encoding="utf-8")
        print(f"    DEBUG: HTML yazildi -> {debug_path}")
        # csm geciyor mu?
        csm_count = len(re.findall(r"csm_", html))
        print(f"    DEBUG: html'de 'csm_' sayisi: {csm_count}")
        # ilk 3 csm URL'i (full pattern)
        for m in re.finditer(r"csm_[^\s\"'<>]+\.jpg", html)[:3] if csm_count else []:
            print(f"      ornek: {m.group(0)[:100]}")

    # csm_<urun><renk>_<X>_<hash>.jpg pattern — daha esnek
    full_code = urun_kodu + renk_kodu
    pattern = (
        rf"https://www\.zimmer-rohde\.com/fileadmin/_processed_/[^/]+/[^/]+/"
        rf"csm_{full_code}[_a-zA-Z0-9]*\.jpg"
    )
    urls = []
    seen = set()
    for m in re.finditer(pattern, html, re.IGNORECASE):
        u = m.group(0)
        if u not in seen:
            seen.add(u)
            urls.append(u)
    return urls


def download_image(url: str, dst: Path) -> bool:
    """Tek bir gorseli indir."""
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30, stream=True)
        if r.status_code != 200:
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open("wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"    HATA: indirme: {e}")
        return False


def process_urun(
    page,
    brand_slug: str,
    urun_kodu: str,
    urun_slug: str,
    variant_codes: list[str],
    dry_run: bool = False,
) -> dict:
    """Bir urun icin tum renk varyantlarini isle."""
    dst_dir = GORSELLER / brand_slug / urun_kodu
    dst_dir.mkdir(parents=True, exist_ok=True)

    stats = {"renk_basina": {}, "toplam_indirilen": 0, "toplam_atlanan": 0}

    is_first = True
    for renk in variant_codes:
        renk_clean = renk.split("-")[-1] if "-" in renk else renk
        # Mevcut dosya var mi (atla)
        existing = list(dst_dir.glob(f"{renk_clean}_*.jpg"))
        if len(existing) >= 3:
            print(f"    {renk_clean}: {len(existing)} dosya zaten var, atlandi")
            stats["toplam_atlanan"] += len(existing)
            stats["renk_basina"][renk_clean] = {"durum": "cached", "sayi": len(existing)}
            is_first = False
            continue

        print(f"    {renk_clean}: sayfa cekiliyor...", end=" ", flush=True)
        urls = fetch_variant_images(page, urun_slug, urun_kodu, renk_clean, debug=is_first)
        is_first = False
        print(f"{len(urls)} URL bulundu")

        if dry_run:
            stats["renk_basina"][renk_clean] = {"durum": "dry-run", "sayi": len(urls)}
            continue

        indirilen = 0
        for idx, url in enumerate(urls, start=1):
            dst = dst_dir / f"{renk_clean}_{idx}.jpg"
            if dst.exists():
                continue
            if download_image(url, dst):
                indirilen += 1
                stats["toplam_indirilen"] += 1
                time.sleep(0.2)  # nazik ol
        stats["renk_basina"][renk_clean] = {"durum": "indirildi", "sayi": indirilen}

    return stats


def update_json_for_urun(json_path: Path, brand_slug: str, urun_kodu: str, stats: dict):
    """Indirme sonrasi JSON images.variants entry'lerinde local_path'leri dogrula."""
    with json_path.open(encoding="utf-8") as f:
        d = json.load(f)

    dst_dir = GORSELLER / brand_slug / urun_kodu
    images_variants = d.get("images", {}).get("variants", [])

    yeni_count = 0
    for img in images_variants:
        local_path = img.get("local_path", "")
        if not local_path:
            continue
        fname = Path(local_path).name
        if (dst_dir / fname).exists():
            yeni_count += 1

    # audit_history entry
    d["source_data"]["_provenance"]["audit_history"].append({
        "audit_id": f"{d['urun_id']}_v_zr_download_{NOW[:10]}",
        "audit_date": NOW[:10],
        "version_before": "(eski indir.ps1 sadece 1 renk)",
        "version_after": f"Z+R Group downloader — {yeni_count}/{len(images_variants)} renk gorsel disk'te",
        "notes": (
            f"Faz 5.13 Z+R Group otomatik renk gorsel indirme. "
            f"Indirilen renkler: {stats['toplam_indirilen']}, cached: {stats['toplam_atlanan']}. "
            f"Renk basina detay: {dict(list(stats['renk_basina'].items())[:5])}..."
        ),
    })
    d["last_updated"] = NOW

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"    JSON guncellendi: {json_path.name}")


def main():
    # Hangi urunler isleneck?
    if len(sys.argv) >= 4:
        targets = [(sys.argv[1], sys.argv[2], sys.argv[3])]
    else:
        # Default: tum Z+R Group urunleri (eksik gorselle olanlar)
        targets = []
        for jp in sorted(URUNLER.glob("*.json")):
            with jp.open(encoding="utf-8") as f:
                d = json.load(f)
            brand_slug = d.get("brand_slug")
            if brand_slug not in ("zimmer_rohde", "ado_goldkante", "etamine", "travers"):
                continue
            urun_kodu = d.get("product_code", "")
            urun_slug = (d.get("product_name", "") or "").lower().replace(" ", "-")
            if not urun_slug or not urun_kodu:
                continue
            targets.append((brand_slug, urun_kodu, urun_slug))

    print(f"Hedef: {len(targets)} urun islenecek")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        for brand_slug, urun_kodu, urun_slug in targets:
            # JSON'dan variant_codes oku
            json_files = list(URUNLER.glob(f"{brand_slug}_{urun_kodu}-*.json"))
            if not json_files:
                print(f"  ATLANDI: {brand_slug}/{urun_kodu} JSON yok")
                continue
            json_path = json_files[0]
            with json_path.open(encoding="utf-8") as f:
                d = json.load(f)
            variants = d.get("source_data", {}).get("variants", [])
            variant_codes = [v["color_code"] for v in variants]

            print(f"\n=== {brand_slug} / {urun_kodu} {urun_slug} ({len(variant_codes)} renk) ===")
            stats = process_urun(page, brand_slug, urun_kodu, urun_slug, variant_codes)
            print(f"  Indirilen: {stats['toplam_indirilen']}, Cached: {stats['toplam_atlanan']}")

            update_json_for_urun(json_path, brand_slug, urun_kodu, stats)

        browser.close()


if __name__ == "__main__":
    main()
