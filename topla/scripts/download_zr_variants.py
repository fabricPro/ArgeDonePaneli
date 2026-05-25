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

import requests

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


def fetch_variant_images(urun_slug: str, urun_kodu: str, renk_kodu: str) -> list[str]:
    """Tek bir renk URL'sine requests ile git, csm CDN URL'lerini topla.

    429 rate-limit retry: 5/10/20 sn backoff.
    """
    url = f"{BASE}/en/product-finder/details/{urun_slug}-{urun_kodu}-{renk_kodu}"
    html = None
    for attempt, backoff in enumerate([0, 5, 10, 20]):
        if backoff:
            print(f" [429 backoff {backoff}s]", end="", flush=True)
            time.sleep(backoff)
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        except Exception as e:
            print(f" [HATA: {e}]", end="")
            return []
        if r.status_code == 200:
            html = r.text
            break
        if r.status_code != 429:
            print(f" [status {r.status_code}]", end="")
            return []
    if html is None:
        print(" [hala 429]", end="")
        return []

    # csm_<urun><renk>_<X>_<hash>.jpg pattern — goreli URL (HTML'de prefix yok)
    full_code = urun_kodu + renk_kodu
    pattern = (
        rf"/?fileadmin/_processed_/[a-zA-Z0-9]+/[a-zA-Z0-9]+/"
        rf"csm_{full_code}[_a-zA-Z0-9]*\.jpg"
    )
    urls = []
    seen = set()
    for m in re.finditer(pattern, html, re.IGNORECASE):
        path = m.group(0)
        full_url = BASE + ("/" + path.lstrip("/"))
        if full_url not in seen:
            seen.add(full_url)
            urls.append(full_url)
    # Rate-limit yumusatici
    time.sleep(1.5)
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
    brand_slug: str,
    urun_kodu: str,
    urun_slug: str,
    variant_codes: list[str],
    dry_run: bool = False,
) -> dict:
    """Bir urun icin tum renk varyantlarini isle (requests-based)."""
    dst_dir = GORSELLER / brand_slug / urun_kodu
    dst_dir.mkdir(parents=True, exist_ok=True)

    stats = {"renk_basina": {}, "toplam_indirilen": 0, "toplam_atlanan": 0}

    for renk in variant_codes:
        renk_clean = renk.split("-")[-1] if "-" in renk else renk
        existing = list(dst_dir.glob(f"{renk_clean}_*.jpg"))
        if len(existing) >= 3:
            print(f"    {renk_clean}: {len(existing)} cached, atlandi")
            stats["toplam_atlanan"] += len(existing)
            stats["renk_basina"][renk_clean] = {"durum": "cached", "sayi": len(existing)}
            continue

        urls = fetch_variant_images(urun_slug, urun_kodu, renk_clean)
        print(f"    {renk_clean}: {len(urls)} URL", end="", flush=True)

        if dry_run:
            print(" (dry-run)")
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
                time.sleep(0.15)
        print(f" -> {indirilen} indirildi")
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

    for brand_slug, urun_kodu, urun_slug in targets:
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
        stats = process_urun(brand_slug, urun_kodu, urun_slug, variant_codes)
        print(f"  Toplam indirilen: {stats['toplam_indirilen']}, Cached: {stats['toplam_atlanan']}")

        update_json_for_urun(json_path, brand_slug, urun_kodu, stats)


if __name__ == "__main__":
    main()
