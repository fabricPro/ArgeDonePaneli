"""Supabase veri (Postgres) + gorsel (Storage) erisim katmani.

Env:
  SUPABASE_URL          — proje URL'i (https://xxxx.supabase.co)
  SUPABASE_SERVICE_KEY  — service_role gizli anahtar (sadece sunucuda)

products tablosu: scalar kolonlar + images jsonb.
gorseller bucket: herkese acik okuma (CDN). Yol: <brand_slug>/<kod>/<dosya>.jpg
"""
from __future__ import annotations

import os
from functools import lru_cache

from supabase import Client, create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
BUCKET = "gorseller"
BUCKET_PDFS = "pdfler"  # v4.0-part-2 Adim 7
TABLE = "products"

PRODUCT_COLUMNS = [
    "urun_id", "brand", "brand_slug", "country", "collection", "product_name",
    "product_code", "composition", "width_cm", "weight_gsm", "weave_type",
    "repeat_vertical_cm", "repeat_horizontal_cm", "arge_notu", "notes",
    "source_url", "images", "albums", "teknik", "dashboard_order",
    "pdfs", "notlar_html",  # v4.0-part-2 Adim 7
    "created_at", "updated_at",
]


@lru_cache(maxsize=1)
def client() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SERVICE_KEY env tanimli degil. "
            ".env dosyasini veya Render env degiskenlerini kontrol et."
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def public_url(path: str | None) -> str | None:
    """Bucket icindeki yoldan herkese acik CDN URL'i."""
    if not path:
        return None
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"


def public_url_pdf(path: str | None) -> str | None:
    """v4.0-part-2 Adim 7 — pdfler bucket'i icin acik URL."""
    if not path:
        return None
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_PDFS}/{path}"


# ---- Products ----

def get_all() -> list[dict]:
    res = client().table(TABLE).select("*").execute()
    return res.data or []


def get(urun_id: str) -> dict | None:
    res = client().table(TABLE).select("*").eq("urun_id", urun_id).limit(1).execute()
    return res.data[0] if res.data else None


def upsert(product: dict) -> None:
    # Sadece bilinen kolonlari gonder (fazlalik kolonlar postgrest hatasi verir)
    row = {k: product.get(k) for k in PRODUCT_COLUMNS if k in product}
    client().table(TABLE).upsert(row, on_conflict="urun_id").execute()


def delete(urun_id: str) -> None:
    client().table(TABLE).delete().eq("urun_id", urun_id).execute()


# ---- app_state (kullanici tercihleri: country_order, vb.) ----

def get_app_state(key: str, default=None):
    try:
        res = client().table("app_state").select("value").eq("key", key).limit(1).execute()
        if res.data:
            return res.data[0].get("value", default)
    except Exception:
        pass
    return default


def set_app_state(key: str, value) -> None:
    try:
        client().table("app_state").upsert(
            {"key": key, "value": value}, on_conflict="key"
        ).execute()
    except Exception:
        pass


# ---- Storage ----

def upload_image(path: str, data: bytes, content_type: str = "image/jpeg") -> None:
    client().storage.from_(BUCKET).upload(
        path, data, {"content-type": content_type, "upsert": "true"}
    )


def delete_images(paths: list[str]) -> None:
    paths = [p for p in paths if p]
    if paths:
        try:
            client().storage.from_(BUCKET).remove(paths)
        except Exception:
            pass  # dosya zaten yoksa sorun degil


def ensure_bucket() -> None:
    """gorseller bucket yoksa herkese acik olarak olustur."""
    try:
        client().storage.create_bucket(BUCKET, options={"public": "true"})
    except Exception:
        pass  # zaten var


# ---- v4.0-part-2 Adim 7: PDF Storage ----

def upload_pdf(path: str, data: bytes) -> None:
    """PDF'i pdfler bucket'a yukle."""
    client().storage.from_(BUCKET_PDFS).upload(
        path, data, {"content-type": "application/pdf", "upsert": "true"}
    )


def delete_pdfs(paths: list[str]) -> None:
    paths = [p for p in paths if p]
    if paths:
        try:
            client().storage.from_(BUCKET_PDFS).remove(paths)
        except Exception:
            pass  # dosya yoksa sorun degil


def download_pdf(path: str) -> bytes:
    """PDF'i bytes olarak indir (proxy serve icin)."""
    return client().storage.from_(BUCKET_PDFS).download(path)


def ensure_bucket_pdfs() -> None:
    """pdfler bucket yoksa olustur (manuel kurulum tercih edilir — Dashboard'dan)."""
    try:
        client().storage.create_bucket(BUCKET_PDFS, options={"public": "true"})
    except Exception:
        pass  # zaten var veya yetki yok
