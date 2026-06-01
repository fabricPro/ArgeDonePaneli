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
TABLE_RESEARCH = "research_pool"  # v4.0-part-2 Adim 8

PRODUCT_COLUMNS = [
    "urun_id", "brand", "brand_slug", "country", "collection", "product_name",
    "product_code", "composition", "width_cm", "weight_gsm", "weave_type",
    "repeat_vertical_cm", "repeat_horizontal_cm", "arge_notu", "notes",
    "source_url", "images", "albums", "teknik", "dashboard_order",
    "pdfs", "notlar_html",  # v4.0-part-2 Adim 7
    "status", "country_code", "source_url_hash",  # v4.0-part-2 Adim 8
    "created_at", "updated_at",
]

RESEARCH_COLUMNS = [
    "id", "master_url", "product_url", "product_url_hash",
    "brand", "brand_slug", "country", "country_code",
    "thumb_url", "status", "imported_product_id",
    "added_at", "imported_at", "notes",
    "is_favorite",  # v4.0-part-2 Sprint 6
    "image_sha256", "page_title", "image_storage_path",  # v4.0-part-2 Sprint 9 (eklenti yakalama)
    "images",  # v4.0-part-2 Sprint 10 — JSONB array (galeri mantığı)
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
    """pdfler bucket yoksa olustur (service_role key ile her zaman yetkili)."""
    try:
        # supabase-py 2.x: create_bucket(id, options={...})
        client().storage.create_bucket(
            BUCKET_PDFS,
            options={"public": True, "file_size_limit": 25 * 1024 * 1024},
        )
    except Exception as e:
        # 409 Conflict = zaten var, OK; başka hata varsa logla
        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
            print(f"[ensure_bucket_pdfs] uyarı: {e}")


# =================================================================
# v4.0-part-2 Adim 8 — URL normalize + research_pool + product status
# =================================================================

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen


def normalize_url(url: str | None) -> str:
    """Dedup için URL'i normalize et: scheme+host lowercase, www. drop,
    trailing slash drop, fragment drop, query KORUNUR."""
    if not url:
        return ""
    try:
        p = urlparse(url.strip())
        scheme = (p.scheme or "https").lower()
        host = (p.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        path = p.path.rstrip("/") or "/"
        return urlunparse((scheme, host, path, p.params, p.query, ""))
    except Exception:
        return url.strip().lower()


def url_hash(url: str | None) -> str | None:
    n = normalize_url(url)
    if not n:
        return None
    return hashlib.md5(n.encode("utf-8")).hexdigest()


def fetch_og_image(url: str, timeout: float = 5.0) -> str | None:
    """Sayfanın <meta property="og:image" content="..."> değerini döner.
    Yoksa veya hata olursa None. Hafif, sadece stdlib (requests yok)."""
    if not url:
        return None
    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; MobidikARGE/1.0; +research-pool)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(req, timeout=timeout) as resp:
            # İlk 200KB yeterli — og tagları head'da olur
            html = resp.read(200_000).decode("utf-8", errors="ignore")
    except Exception:
        return None

    # og:image (öncelikli)
    m = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if not m:
        # twitter:image fallback
        m = re.search(
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.IGNORECASE,
        )
    if not m:
        return None
    img = m.group(1).strip()
    # Relative → absolute
    if img.startswith("//"):
        img = "https:" + img
    elif img.startswith("/"):
        try:
            p = urlparse(url)
            img = f"{p.scheme}://{p.netloc}{img}"
        except Exception:
            return None
    return img


# ---- Products: status ----

def update_status(urun_id: str, status: str) -> None:
    """Ürün status'unu değiştir: 'active' veya 'archived'."""
    if status not in ("active", "archived"):
        raise ValueError(f"Geçersiz status: {status}")
    client().table(TABLE).update({"status": status}).eq("urun_id", urun_id).execute()


# ---- Research Pool CRUD ----

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def research_list(
    status: str | None = "pending",
    brand_slug: str | None = None,
    country_code: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """Ön çalışma havuzu listele (filtreli)."""
    q = client().table(TABLE_RESEARCH).select("*")
    if status:
        if status == "all":
            pass  # tümü
        else:
            q = q.eq("status", status)
    if brand_slug:
        q = q.eq("brand_slug", brand_slug)
    if country_code:
        q = q.eq("country_code", country_code)
    res = q.order("added_at", desc=True).limit(limit).execute()
    return res.data or []


def research_get(research_id: str) -> dict | None:
    res = client().table(TABLE_RESEARCH).select("*").eq("id", research_id).limit(1).execute()
    return res.data[0] if res.data else None


def research_find_by_hash(hash_: str) -> dict | None:
    res = client().table(TABLE_RESEARCH).select("*").eq("product_url_hash", hash_).limit(1).execute()
    return res.data[0] if res.data else None


def research_find_by_sha256(sha: str) -> dict | None:
    """v4.0-part-2 Sprint 9 — Aynı görsel (SHA-256) zaten yakalanmış mı?
    Mevcut tek-görsel kolonu için legacy lookup."""
    if not sha:
        return None
    res = (client().table(TABLE_RESEARCH).select("*")
           .eq("image_sha256", sha).limit(1).execute())
    return res.data[0] if res.data else None


def research_find_image_by_sha(sha: str) -> dict | None:
    """v4.0-part-2 Sprint 10 — JSONB images[] içinde sha256 ara.
    Hem yeni galeri içeriklerini hem legacy tek-görsel satırlarını yakalar
    (migration sonrası ikisi de images[]'de mevcut)."""
    if not sha:
        return None
    # PostgreSQL JSONB containment: images @> '[{"sha256": "..."}]'
    # postgrest-py .contains() dict kabul etmiyor → raw filter ile JSON string
    import json
    pattern = json.dumps([{"sha256": sha}])
    res = (client().table(TABLE_RESEARCH).select("*")
           .filter("images", "cs", pattern)
           .limit(1).execute())
    if res.data:
        return res.data[0]
    # Fallback: eski tek-görsel kolonu (migration koşmamış data için)
    return research_find_by_sha256(sha)


def research_get(research_id: str) -> dict | None:
    """Tek bir research_pool satırını getir."""
    if not research_id:
        return None
    res = (client().table(TABLE_RESEARCH).select("*")
           .eq("id", research_id).limit(1).execute())
    return res.data[0] if res.data else None


def research_append_image(research_id: str, image_meta: dict) -> dict | None:
    """v4.0-part-2 Sprint 10 — Mevcut entry'nin images[]'ine yeni görsel ekle.
    Read-modify-write (PostgREST JSONB concat operator yok).
    Race condition: SHA-256 dedup yukarı katmanda (research_find_image_by_sha) önler.
    image_meta: {sha256, storage_path, alt, source_image_url, added_at}.
    """
    if not research_id or not image_meta:
        return None
    row = research_get(research_id)
    if not row:
        return None
    images = row.get("images") or []
    # Aynı sha zaten array'de ise idempotent (insert atma)
    sha = image_meta.get("sha256")
    if sha and any((im or {}).get("sha256") == sha for im in images):
        return row
    images.append(image_meta)
    patch = {"images": images}
    # Geriye uyum: ilk görselse legacy kolonları da yaz
    if len(images) == 1:
        patch["image_sha256"] = sha
        patch["image_storage_path"] = image_meta.get("storage_path")
    res = (client().table(TABLE_RESEARCH).update(patch)
           .eq("id", research_id).execute())
    return (res.data or [None])[0]


def product_find_by_url_hash(hash_: str) -> dict | None:
    """Aynı URL hash'li ürün var mı (research → product dedup)."""
    res = client().table(TABLE).select("urun_id,product_name,brand").eq("source_url_hash", hash_).limit(1).execute()
    return res.data[0] if res.data else None


def research_add(payload: dict) -> dict:
    """Yeni ön çalışma satırı ekle. payload zorunlu alanları:
    master_url, product_url, brand, brand_slug, country.
    Otomatik: product_url_hash, country_code (varsa), thumb_url (best-effort)."""
    purl = (payload.get("product_url") or "").strip()
    if not purl:
        raise ValueError("product_url zorunlu")
    h = url_hash(purl)
    if not h:
        raise ValueError("product_url geçersiz")

    row = {
        "master_url": (payload.get("master_url") or "").strip(),
        "product_url": purl,
        "product_url_hash": h,
        "brand": (payload.get("brand") or "").strip(),
        "brand_slug": (payload.get("brand_slug") or "").strip().lower(),
        "country": (payload.get("country") or "").strip(),
        "country_code": (payload.get("country_code") or None),
        "thumb_url": payload.get("thumb_url"),
        "status": "pending",
        "notes": payload.get("notes") or None,
        "added_at": _now_iso(),
    }
    if not row["master_url"] or not row["brand"] or not row["country"]:
        raise ValueError("master_url + brand + country zorunlu")

    res = client().table(TABLE_RESEARCH).insert(row).execute()
    return (res.data or [row])[0]


def research_update_status(research_id: str, new_status: str, imported_product_id: str | None = None) -> dict | None:
    """Status değiştir: pending | imported | dismissed."""
    if new_status not in ("pending", "imported", "dismissed"):
        raise ValueError(f"Geçersiz status: {new_status}")
    patch: dict = {"status": new_status}
    if new_status == "imported":
        patch["imported_at"] = _now_iso()
        if imported_product_id:
            patch["imported_product_id"] = imported_product_id
    res = client().table(TABLE_RESEARCH).update(patch).eq("id", research_id).execute()
    return (res.data or [None])[0]


def research_delete(research_id: str) -> None:
    """Soft delete: status='dismissed'."""
    research_update_status(research_id, "dismissed")


def research_hard_delete(research_id: str) -> None:
    """Fiziksel silme (admin)."""
    client().table(TABLE_RESEARCH).delete().eq("id", research_id).execute()


# v4.0-part-2 Sprint 6 — Düzenleme + Favori

# Düzenlenebilir alanlar (whitelist) — diğer alanları PATCH eden istek atlanır.
RESEARCH_EDITABLE_FIELDS = {
    "master_url", "product_url", "product_url_hash",
    "brand", "brand_slug", "country", "country_code",
    "notes", "thumb_url", "is_favorite",
}


def research_update(research_id: str, patch: dict) -> dict | None:
    """Whitelist'li alanları güncelle. Boş patch hata değil — no-op."""
    safe = {k: v for k, v in patch.items() if k in RESEARCH_EDITABLE_FIELDS}
    if not safe:
        return research_get(research_id)
    res = client().table(TABLE_RESEARCH).update(safe).eq("id", research_id).execute()
    return (res.data or [None])[0]


def research_set_favorite(research_id: str, value: bool) -> dict | None:
    """Favori (yıldız) toggle."""
    return research_update(research_id, {"is_favorite": bool(value)})


def research_list_favorites(limit: int = 500) -> list[dict]:
    """Sadece favori (is_favorite=true) satırlar."""
    res = (client().table(TABLE_RESEARCH).select("*")
           .eq("is_favorite", True)
           .order("added_at", desc=True).limit(limit).execute())
    return res.data or []


# =================================================================
# v4.0-part-2 Sprint 8 — Çalışma Alanı (workspace) helper'ları
# =================================================================

WORKSPACE_KEY = "workspace_fabric_ids"


def workspace_get_ids() -> list[str]:
    """Çalışma alanına pinlenmiş ürün id'leri (sıraya bağlı)."""
    state = get_app_state(WORKSPACE_KEY) or {}
    if not isinstance(state, dict):
        return []
    return list(state.get("fabric_ids") or [])


def workspace_add(urun_id: str) -> list[str]:
    """Bir ürünü workspace'e ekle (yoksa). Mevcut sıra korunur."""
    ids = workspace_get_ids()
    if urun_id and urun_id not in ids:
        ids.append(urun_id)
        set_app_state(WORKSPACE_KEY, {"fabric_ids": ids, "updated_at": _now_iso()})
    return ids


def workspace_remove(urun_id: str) -> list[str]:
    """Bir ürünü workspace'ten çıkar."""
    ids = [i for i in workspace_get_ids() if i != urun_id]
    set_app_state(WORKSPACE_KEY, {"fabric_ids": ids, "updated_at": _now_iso()})
    return ids


def workspace_reorder(ids: list[str]) -> list[str]:
    """Workspace sırasını değiştir. Sadece mevcut id'ler korunur, ek id'ler atlanır."""
    current = set(workspace_get_ids())
    cleaned = [i for i in ids if i in current]
    set_app_state(WORKSPACE_KEY, {"fabric_ids": cleaned, "updated_at": _now_iso()})
    return cleaned


# ---- Product summary helpers (galeri kart indikatörleri) ----

def has_teknik_calisma(product: dict) -> bool:
    """En az bir sürümde iplikler/parametreler dolu mu?"""
    teknik = product.get("teknik") or {}
    for s in teknik.get("surumler") or []:
        iplikler = s.get("iplikler") or {}
        cozgu = iplikler.get("cozgu") or []
        atki = iplikler.get("atki") or []
        if cozgu or atki:
            return True
        # ya da parametrelerde dolu alan
        params = s.get("parametreler") or {}
        if any(params.get(k) for k in ("ham_en", "mamul_en", "atki_sikligi")):
            return True
    return False


def has_pdfs(product: dict) -> bool:
    return bool(product.get("pdfs"))


def has_notlar(product: dict) -> bool:
    """Ürün-seviyesi VEYA herhangi sürüm-seviyesi not dolu mu?"""
    if (product.get("notlar_html") or "").strip():
        return True
    teknik = product.get("teknik") or {}
    for s in teknik.get("surumler") or []:
        if (s.get("notlar_html") or "").strip():
            return True
    return False
