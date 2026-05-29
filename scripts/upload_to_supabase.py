"""Yerel urunler/*.json + gorseller/ -> Supabase (Postgres + Storage) tasima.

Tek seferlik (idempotent: tekrar calistirilirsa ustune yazar).
Once .env'i doldur (SUPABASE_URL, SUPABASE_SERVICE_KEY), sonra:
    .venv\\Scripts\\python.exe scripts\\upload_to_supabase.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "web"))

import store  # noqa: E402  (env yuklendikten sonra import edilmeli)

URUNLER = ROOT / "urunler"


def to_bucket_path(local_path: str | None) -> str | None:
    """'gorseller/kvadrat/5539/0101_1.jpg' -> 'kvadrat/5539/0101_1.jpg'."""
    if not local_path:
        return None
    return local_path.split("gorseller/", 1)[-1]


def main() -> int:
    if not store.SUPABASE_URL or not store.SUPABASE_SERVICE_KEY:
        print("HATA: .env icinde SUPABASE_URL / SUPABASE_SERVICE_KEY yok.")
        return 1
    if not URUNLER.exists():
        print(f"HATA: {URUNLER} yok.")
        return 1

    print("Bucket kontrol/olustur...")
    store.ensure_bucket()

    n_prod = n_img = n_missing = 0
    for jp in sorted(URUNLER.glob("*.json")):
        d = json.loads(jp.read_text(encoding="utf-8"))
        new_images = []
        for im in d.get("images", []):
            lp = im.get("local_path")
            bpath = to_bucket_path(lp)
            f = ROOT / lp if lp else None
            if not bpath or not f or not f.exists():
                n_missing += 1
                print(f"  EKSIK gorsel atlandi: {lp}")
                continue
            store.upload_image(bpath, f.read_bytes(), "image/jpeg")
            new_images.append({
                "path": bpath,
                "variant_label": im.get("variant_label"),
                "is_cover": bool(im.get("is_cover")),
                "order": im.get("order", len(new_images)),
            })
            n_img += 1
        # Kapak garanti: hicbiri is_cover degilse ilkini kapak yap
        if new_images and not any(i["is_cover"] for i in new_images):
            new_images[0]["is_cover"] = True

        row = {k: d.get(k) for k in store.PRODUCT_COLUMNS if k in d}
        row["images"] = new_images
        store.upsert(row)
        n_prod += 1
        print(f"  OK {d.get('urun_id')}: {len(new_images)} gorsel")

    print(f"\nTAMAM -> Supabase: {n_prod} urun, {n_img} gorsel, {n_missing} eksik atlandi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
