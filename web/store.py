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
BUCKET_KARTELALAR = "kartelalar"  # İplik Kataloğu Parça 1 (Parça 2'de kullanılacak)
TABLE = "products"
TABLE_RESEARCH = "research_pool"  # v4.0-part-2 Adim 8
TABLE_KARTELA = "iplik_kartelalari"  # İplik Kataloğu Parça 1
TABLE_LOOMS = "looms"  # Senkron Sprint 1
TABLE_LOOM_PRODUCTS = "loom_products"  # Senkron Sprint 1
TABLE_MATERIAL_STOCK = "material_stock"  # Senkron Sprint 2 — iplik havuzu
TABLE_WEFT_MAPPINGS = "weft_color_mappings"  # Senkron Sprint 3 — atkı renk eşleme
TABLE_WARPS = "warps"  # Senkron Sprint 4 — çözgü
TABLE_WARP_YARNS = "warp_yarns"  # Senkron Sprint 4 — çözgü iplikleri
TABLE_WARP_ALLOCATIONS = "warp_product_allocations"  # Senkron Sprint 4 — metre bütçesi

PRODUCT_COLUMNS = [
    "urun_id", "brand", "brand_slug", "country", "collection", "product_name",
    "product_code", "composition", "width_cm", "weight_gsm", "weave_type",
    "repeat_vertical_cm", "repeat_horizontal_cm", "arge_notu", "notes",
    "source_url", "images", "albums", "teknik", "dashboard_order",
    "pdfs", "notlar_html",  # v4.0-part-2 Adim 7
    "status", "country_code", "source_url_hash",  # v4.0-part-2 Adim 8
    # v4.0-part-2 Sprint 11.5 — country ayrimi + reference_price
    "brand_country", "brand_country_code",                # firma HQ (mevcut country = bunun alias'i)
    "production_country", "production_country_code",      # "Made in" — yalniz Gemini sayfadan
    "reference_price", "reference_price_type", "reference_price_evidence",
    "from_research_id",  # v4.0-part-2 Sprint 14 — Ön çalışma kaynağı (varsa)
    "plan",  # tasarim-v2 Plan Parça 1 — sürüm-bazlı planlama (surum_id ile anahtarlı jsonb)
    "todo",  # Faz 2 — ürün-bazlı To-Do listesi (jsonb: [{id,text,done,order}])
    # OnCalisma-V2 (Problem 2) — taksonomi (3 bağımsız eksen; controlled vocab + migration ile)
    "category", "pattern", "weave_tags", "style_tags", "color_family",
    # OnCalisma-V2 (Problem 4b) — renk sayısı (color_family yerine UI'da) + AI notu
    "color_count", "ai_notu",
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
    "albums",  # v4.0-part-2 Sprint 11 — ürün öncesi albüm + renk paleti
    "brand_country", "brand_country_code",  # v4.0-part-2 Sprint 11.5 — country = brand_country alias
    # OnCalisma-V2 (Problem 1) — ürün ailesi / varyant tespiti (sistem-türetimli; migration ile)
    "family_key", "base_code", "is_variant_candidate", "variant_of",
    # OnCalisma-V2 (Problem 2) — taksonomi (kullanıcı havuzda da girebilir; migration ile)
    "category", "pattern", "weave_tags", "style_tags", "color_family",
    # OnCalisma-V2 (Problem 4a) — Gemini zenginleştirme staging (iki katmanlı)
    "extracted_facts", "ai_summary", "enrichment_status",
    # OnCalisma-V2 (Problem 4b) — renk sayısı + AI notu
    "color_count", "ai_notu",
    # Sprint 12 — ürün taslağı (çekmecede düzenlenen ürün-öncesi alanlar; Ürün Oluştur'da taşınır)
    "product_draft",
]

# İplik Kataloğu Parça 1 — kartela kolonları (upsert whitelist)
KARTELA_COLUMNS = [
    "kartela_id", "ad", "tedarikci", "iplik_tipi", "iplik_numarasi", "kompozisyon",
    "fiyat_tutar", "fiyat_birim", "fiyat_per", "moq_kg", "moq_notu",
    "sayfalar",  # jsonb — Parça 2 doldurur
    "olusturma_tarihi", "guncelleme_tarihi",
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
    try:
        client().table(TABLE).upsert(row, on_conflict="urun_id").execute()
    except Exception as e:
        # OnCalisma-V2 (Problem 2) — taksonomi kolonları migration öncesi yoksa
        # onları düşür ve yeniden dene (research_insert deseni). Diğer hatalar aynen fırlar.
        msg = str(e).lower()
        if any(k in msg for k in _TAXONOMY_KEYS) or "todo" in msg or "schema cache" in msg or "column" in msg:
            # Migration-öncesi yoksa düşür (taksonomi + Faz 2 todo). DB'deki mevcut değerler korunur.
            _drop = set(_TAXONOMY_KEYS) | {"todo"}
            slim = {k: v for k, v in row.items() if k not in _drop}
            client().table(TABLE).upsert(slim, on_conflict="urun_id").execute()
        else:
            raise


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


def download_image_bytes(path: str) -> bytes:
    """v4.0-part-2 Sprint 10.5 — Storage'tan binary oku.
    Prefill kopyalama (_inbox → product folder) için kullanılır."""
    return client().storage.from_(BUCKET).download(path)


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
# İplik Kataloğu Parça 1 — iplik_kartelalari CRUD + kartelalar bucket
# (CRUD products pattern'iyle; storage helper'ları Parça 2 için hazır, Parça 1'de kullanılmaz)
# =================================================================

def list_kartelalar() -> list[dict]:
    res = client().table(TABLE_KARTELA).select("*").execute()
    return res.data or []


def get_kartela(kartela_id: str) -> dict | None:
    res = (client().table(TABLE_KARTELA).select("*")
           .eq("kartela_id", kartela_id).limit(1).execute())
    return res.data[0] if res.data else None


def ensure_renk_ids(sayfalar) -> int:
    """sayfalar[].renkler[] içindeki her renge KALICI renk_id (uuid hex[:12]) bas — yalnız
    EKSİK/boş olanlara. In-place; mevcut renk_id ASLA değişmez (Senkron demirleme önkoşulu).
    numara/ad/hex vb. alanlara dokunmaz. Damgalanan renk sayısını döndürür (idempotent)."""
    if not isinstance(sayfalar, list):
        return 0
    stamped = 0
    for s in sayfalar:
        if not isinstance(s, dict):
            continue
        renkler = s.get("renkler")
        if not isinstance(renkler, list):
            continue
        for r in renkler:
            if isinstance(r, dict) and not str(r.get("renk_id") or "").strip():
                r["renk_id"] = _uuid.uuid4().hex[:12]
                stamped += 1
    return stamped


def upsert_kartela(data: dict) -> None:
    # Sadece bilinen kolonlari gonder; guncelleme_tarihi her zaman tazelenir.
    # olusturma_tarihi payload'a EKLENMEZ: yeni kayitta DB default doldurur,
    # guncellemede dokunulmaz.
    # Sunucu garantisi (tek doğruluk noktası): client renk_id göndermese bile her renk
    # kalıcı renk_id taşır. In-place damga → endpoint'in response renkler'i de id'li döner.
    ensure_renk_ids(data.get("sayfalar"))
    row = {k: data.get(k) for k in KARTELA_COLUMNS if k in data}
    row["guncelleme_tarihi"] = _now_iso()
    row.pop("olusturma_tarihi", None)
    client().table(TABLE_KARTELA).upsert(row, on_conflict="kartela_id").execute()


def delete_kartela(kartela_id: str) -> None:
    client().table(TABLE_KARTELA).delete().eq("kartela_id", kartela_id).execute()


# ============================================================
# Senkron Sprint 1 — looms + loom_products (thin DB katmanı)
# Şema: scripts/supabase_schema_senkron_part1.sql (migration ile, runtime DDL yok).
# Read'ler migration uygulanmadan önce boş döner (sayfa çökmesin); write'lar hata verir.
# ============================================================
LOOM_COLUMNS = [
    "loom_id", "loom_no", "max_width_cm", "frame_count", "frame_purpose",
    "setup_name", "reed_no", "reed_report", "working_warp_width_cm",
    "status", "notes", "created_at", "updated_at",
]
LOOM_PRODUCT_COLUMNS = ["id", "loom_id", "urun_id", "sequence", "notes", "created_at"]


def _missing_table(e) -> bool:
    """Supabase 'tablo yok' hatası mı? (migration henüz uygulanmadıysa read boş dönsün)."""
    m = str(e).lower()
    return ("could not find the table" in m or "pgrst205" in m
            or "does not exist" in m or "42p01" in m)


def list_looms() -> list[dict]:
    try:
        res = client().table(TABLE_LOOMS).select("*").order("loom_no").execute()
        return res.data or []
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return []
        raise


def get_loom(loom_id: str) -> dict | None:
    try:
        res = (client().table(TABLE_LOOMS).select("*")
               .eq("loom_id", loom_id).limit(1).execute())
        return res.data[0] if res.data else None
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return None
        raise


def upsert_loom(data: dict) -> None:
    # Sadece bilinen kolonlar; updated_at her zaman tazelenir; created_at'e dokunma.
    row = {k: data.get(k) for k in LOOM_COLUMNS if k in data}
    row["updated_at"] = _now_iso()
    row.pop("created_at", None)
    client().table(TABLE_LOOMS).upsert(row, on_conflict="loom_id").execute()


def delete_loom(loom_id: str) -> None:
    # loom_products FK on delete cascade → bu tezgahın atamaları da silinir.
    client().table(TABLE_LOOMS).delete().eq("loom_id", loom_id).execute()


def loom_products_for(loom_id: str) -> list[dict]:
    try:
        res = (client().table(TABLE_LOOM_PRODUCTS).select("*")
               .eq("loom_id", loom_id).order("sequence").execute())
        return res.data or []
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return []
        raise


def loom_product_counts() -> dict:
    """{loom_id: atalı ürün sayısı} — liste ekranı rozet/özeti için."""
    try:
        res = client().table(TABLE_LOOM_PRODUCTS).select("loom_id").execute()
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return {}
        raise
    counts: dict = {}
    for r in (res.data or []):
        counts[r.get("loom_id")] = counts.get(r.get("loom_id"), 0) + 1
    return counts


def loom_product_exists(loom_id: str, urun_id: str) -> bool:
    res = (client().table(TABLE_LOOM_PRODUCTS).select("id")
           .eq("loom_id", loom_id).eq("urun_id", urun_id).limit(1).execute())
    return bool(res.data)


def loom_product_add(loom_id: str, urun_id: str, sequence: int = 0, notes=None) -> dict | None:
    """Atama ekle. unique(loom_id,urun_id): zaten varsa None döner (çift eklemez)."""
    if loom_product_exists(loom_id, urun_id):
        return None
    row = {
        "id": "lp_" + _uuid.uuid4().hex[:12],
        "loom_id": loom_id, "urun_id": urun_id,
        "sequence": int(sequence or 0), "notes": notes, "created_at": _now_iso(),
    }
    client().table(TABLE_LOOM_PRODUCTS).insert(row).execute()
    return row


def loom_product_remove(lp_id: str) -> None:
    client().table(TABLE_LOOM_PRODUCTS).delete().eq("id", lp_id).execute()


def loom_product_set_sequence(lp_id: str, sequence: int) -> None:
    client().table(TABLE_LOOM_PRODUCTS).update(
        {"sequence": int(sequence)}).eq("id", lp_id).execute()


# ============================================================
# Senkron Sprint 2 — material_stock (iplik havuzu / alım planı)
# Şema: scripts/supabase_schema_senkron_part2.sql. Read'ler migration öncesi boş döner.
# Havuz ASLA serbest-metin renk tutmaz; her zaman kanonik renk_id (kartela_has_renk doğrular).
# TÜKETİM/KALAN bu sprintte YOK.
# ============================================================
MATERIAL_STOCK_COLUMNS = [
    "id", "kartela_id", "renk_id", "planned_purchase_kg", "actual_purchase_kg",
    "notes", "created_at", "updated_at",
]


def kartela_has_renk(kartela_id: str, renk_id: str) -> bool:
    """renk_id verilen kartelanın sayfalar[].renkler[] içinde GERÇEKTEN var mı?
    Havuz kaydı öncesi uygulama-düzeyi tutarlılık doğrulaması (renk jsonb-nested, DB-FK yok)."""
    k = get_kartela(kartela_id)
    if not k:
        return False
    rid = str(renk_id or "").strip()
    if not rid:
        return False
    for s in (k.get("sayfalar") or []):
        for r in (s.get("renkler") or []):
            if isinstance(r, dict) and str(r.get("renk_id") or "") == rid:
                return True
    return False


def list_material_stock() -> list[dict]:
    try:
        res = client().table(TABLE_MATERIAL_STOCK).select("*").order("created_at").execute()
        return res.data or []
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return []
        raise


def get_material_stock(ms_id: str) -> dict | None:
    try:
        res = (client().table(TABLE_MATERIAL_STOCK).select("*")
               .eq("id", ms_id).limit(1).execute())
        return res.data[0] if res.data else None
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return None
        raise


def material_stock_exists(kartela_id: str, renk_id: str) -> bool:
    res = (client().table(TABLE_MATERIAL_STOCK).select("id")
           .eq("kartela_id", kartela_id).eq("renk_id", renk_id).limit(1).execute())
    return bool(res.data)


def material_stock_add(kartela_id: str, renk_id: str, planned_purchase_kg=None,
                       actual_purchase_kg=None, notes=None) -> dict | None:
    """Havuza (iplik+renk) satırı ekle. unique(kartela_id,renk_id): zaten varsa None döner."""
    if material_stock_exists(kartela_id, renk_id):
        return None
    now = _now_iso()
    row = {
        "id": "ms_" + _uuid.uuid4().hex[:10],
        "kartela_id": kartela_id, "renk_id": renk_id,
        "planned_purchase_kg": planned_purchase_kg, "actual_purchase_kg": actual_purchase_kg,
        "notes": notes, "created_at": now, "updated_at": now,
    }
    client().table(TABLE_MATERIAL_STOCK).insert(row).execute()
    return row


def material_stock_update(ms_id: str, patch: dict) -> None:
    allowed = {"planned_purchase_kg", "actual_purchase_kg", "notes"}
    upd = {k: v for k, v in patch.items() if k in allowed}
    upd["updated_at"] = _now_iso()
    client().table(TABLE_MATERIAL_STOCK).update(upd).eq("id", ms_id).execute()


def material_stock_remove(ms_id: str) -> None:
    client().table(TABLE_MATERIAL_STOCK).delete().eq("id", ms_id).execute()


# ============================================================
# Senkron Sprint 3 — weft_color_mappings (atkı renk eşleme)
# Şema: scripts/supabase_schema_senkron_part3.sql. Read'ler migration öncesi boş döner.
# Tüketim BU TABLODA TUTULMAZ — yalnız (atkı pozisyonu+renk → havuz kalemi) eşlemesi.
# ============================================================

def loom_product_get(lp_id: str) -> dict | None:
    try:
        res = (client().table(TABLE_LOOM_PRODUCTS).select("*")
               .eq("id", lp_id).limit(1).execute())
        return res.data[0] if res.data else None
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return None
        raise


def list_weft_mappings() -> list[dict]:
    try:
        res = client().table(TABLE_WEFT_MAPPINGS).select("*").execute()
        return res.data or []
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return []
        raise


def weft_mappings_for(loom_product_id: str, surum_id: str | None = None) -> list[dict]:
    try:
        q = client().table(TABLE_WEFT_MAPPINGS).select("*").eq("loom_product_id", loom_product_id)
        if surum_id is not None:
            q = q.eq("surum_id", surum_id)
        return q.execute().data or []
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return []
        raise


def weft_mapping_set(loom_product_id: str, surum_id: str, iplik_index: int,
                     cell_key: str, material_stock_id: str) -> dict:
    """Doğal anahtara (loom_product, surum, iplik_index, cell_key) eşleme yaz — varsa güncelle,
    yoksa ekle (upsert). material_stock_id'yi günceller."""
    existing = (client().table(TABLE_WEFT_MAPPINGS).select("id")
                .eq("loom_product_id", loom_product_id).eq("surum_id", surum_id)
                .eq("iplik_index", int(iplik_index)).eq("cell_key", cell_key)
                .limit(1).execute()).data
    if existing:
        wm_id = existing[0]["id"]
        client().table(TABLE_WEFT_MAPPINGS).update(
            {"material_stock_id": material_stock_id}).eq("id", wm_id).execute()
        return {"id": wm_id, "updated": True}
    row = {
        "id": "wm_" + _uuid.uuid4().hex[:10],
        "loom_product_id": loom_product_id, "surum_id": surum_id,
        "iplik_index": int(iplik_index), "cell_key": cell_key,
        "material_stock_id": material_stock_id, "created_at": _now_iso(),
    }
    client().table(TABLE_WEFT_MAPPINGS).insert(row).execute()
    return row


def weft_mapping_clear(loom_product_id: str, surum_id: str, iplik_index: int, cell_key: str) -> None:
    (client().table(TABLE_WEFT_MAPPINGS).delete()
     .eq("loom_product_id", loom_product_id).eq("surum_id", surum_id)
     .eq("iplik_index", int(iplik_index)).eq("cell_key", cell_key).execute())


# ============================================================
# Senkron Sprint 4 — warps + warp_yarns + warp_product_allocations (çözgü)
# Şema: scripts/supabase_schema_senkron_part4.sql. Read'ler migration öncesi boş döner.
# Tüketim/işbağ/metre bütçesi BU TABLOLARDA TUTULMAZ — canlı hesaplanır (app.py).
# ============================================================
WARP_COLUMNS = [
    "id", "loom_id", "name", "layer", "kind", "thread_count", "width_cm", "length_m",
    "consumed_kg_override", "tie_group_override", "source_product_id", "source_surum_id",
    "source_durum", "sequence", "notes", "created_at", "updated_at",
]
WARP_YARN_COLUMNS = [
    "id", "warp_id", "material_stock_id", "thread_count", "yarn_tip", "yarn_iplik",
    "seed_renk_ad", "seed_renk_hex", "notes", "created_at",
]
WARP_ALLOC_COLUMNS = ["id", "warp_id", "loom_product_id", "allocated_m", "notes", "created_at"]


def list_warps_for_loom(loom_id: str) -> list[dict]:
    try:
        return (client().table(TABLE_WARPS).select("*")
                .eq("loom_id", loom_id).order("sequence").execute()).data or []
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return []
        raise


def list_all_warps() -> list[dict]:
    try:
        return client().table(TABLE_WARPS).select("*").execute().data or []
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return []
        raise


def get_warp(warp_id: str) -> dict | None:
    try:
        res = client().table(TABLE_WARPS).select("*").eq("id", warp_id).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return None
        raise


def upsert_warp(data: dict) -> None:
    row = {k: data.get(k) for k in WARP_COLUMNS if k in data}
    row["updated_at"] = _now_iso()
    row.pop("created_at", None)
    client().table(TABLE_WARPS).upsert(row, on_conflict="id").execute()


def delete_warp(warp_id: str) -> None:
    # warp_yarns + warp_product_allocations FK on delete cascade → birlikte gider.
    client().table(TABLE_WARPS).delete().eq("id", warp_id).execute()


def warp_yarns_for(warp_id: str) -> list[dict]:
    try:
        return (client().table(TABLE_WARP_YARNS).select("*")
                .eq("warp_id", warp_id).order("created_at").execute()).data or []
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return []
        raise


def list_all_warp_yarns() -> list[dict]:
    try:
        return client().table(TABLE_WARP_YARNS).select("*").execute().data or []
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return []
        raise


def warp_yarn_add(data: dict) -> dict:
    row = {k: data.get(k) for k in WARP_YARN_COLUMNS if k in data}
    row["id"] = "wy_" + _uuid.uuid4().hex[:10]
    row["created_at"] = _now_iso()
    client().table(TABLE_WARP_YARNS).insert(row).execute()
    return row


def warp_yarn_update(wy_id: str, patch: dict) -> None:
    allowed = {"material_stock_id", "thread_count", "yarn_tip", "yarn_iplik",
               "seed_renk_ad", "seed_renk_hex", "notes"}
    upd = {k: v for k, v in patch.items() if k in allowed}
    if upd:
        client().table(TABLE_WARP_YARNS).update(upd).eq("id", wy_id).execute()


def warp_yarns_delete_for(warp_id: str) -> None:
    client().table(TABLE_WARP_YARNS).delete().eq("warp_id", warp_id).execute()


def allocations_for_warp(warp_id: str) -> list[dict]:
    try:
        return (client().table(TABLE_WARP_ALLOCATIONS).select("*")
                .eq("warp_id", warp_id).execute()).data or []
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return []
        raise


def list_all_allocations() -> list[dict]:
    try:
        return client().table(TABLE_WARP_ALLOCATIONS).select("*").execute().data or []
    except Exception as e:  # noqa: BLE001
        if _missing_table(e):
            return []
        raise


def allocation_set(warp_id: str, loom_product_id: str, allocated_m, notes=None) -> dict:
    """Doğal anahtara (warp, loom_product) dağıtım yaz — varsa güncelle, yoksa ekle."""
    existing = (client().table(TABLE_WARP_ALLOCATIONS).select("id")
                .eq("warp_id", warp_id).eq("loom_product_id", loom_product_id).limit(1).execute()).data
    if existing:
        aid = existing[0]["id"]
        client().table(TABLE_WARP_ALLOCATIONS).update(
            {"allocated_m": allocated_m, "notes": notes}).eq("id", aid).execute()
        return {"id": aid, "updated": True}
    row = {"id": "wa_" + _uuid.uuid4().hex[:10], "warp_id": warp_id,
           "loom_product_id": loom_product_id, "allocated_m": allocated_m,
           "notes": notes, "created_at": _now_iso()}
    client().table(TABLE_WARP_ALLOCATIONS).insert(row).execute()
    return row


def allocation_remove(alloc_id: str) -> None:
    client().table(TABLE_WARP_ALLOCATIONS).delete().eq("id", alloc_id).execute()


# ---- kartelalar Storage (Parça 2'de sayfa fotoğrafları için) ----

def public_url_kartela(path: str | None) -> str | None:
    if not path:
        return None
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_KARTELALAR}/{path}"


def upload_kartela(path: str, data: bytes, content_type: str = "image/jpeg") -> None:
    client().storage.from_(BUCKET_KARTELALAR).upload(
        path, data, {"content-type": content_type, "upsert": "true"}
    )


def delete_kartelalar(paths: list[str]) -> None:
    paths = [p for p in paths if p]
    if paths:
        try:
            client().storage.from_(BUCKET_KARTELALAR).remove(paths)
        except Exception:
            pass  # dosya yoksa sorun degil


def ensure_bucket_kartelalar() -> None:
    """kartelalar bucket yoksa olustur (service_role key ile her zaman yetkili)."""
    try:
        client().storage.create_bucket(
            BUCKET_KARTELALAR,
            options={"public": True, "file_size_limit": 25 * 1024 * 1024},
        )
    except Exception as e:
        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
            print(f"[ensure_bucket_kartelalar] uyarı: {e}")


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


# OnCalisma-V2 (Problem 1) — Ürün ailesi / varyant tespiti.
# normalize_url()'i DEĞİŞTİRMEZ (dedup aynen kalır); yalnız base_code + family_key türetir.
# Renk/tracking query'leri base'den düşülür ki aynı kumaşın renk varyantları tek aileye gelsin.
_COLOR_QUERY_KEYS = {"color", "colour", "variant", "renk", "c"}
_TRACKING_QUERY_KEYS = {"fbclid", "gclid", "ref", "mc_cid", "mc_eid"}


def derive_base_code(product_url: str | None, brand_slug: str | None) -> tuple[str, str]:
    """Üründen renk ekini soyup taban kod + family_key türet. SAF, exception fırlatmaz.
    family_key = '<brand_slug>:<base_code>'. Örnekler:
      .../p/CA1580/092 -> CA1580 ; .../p/JA7161-071 -> JA7161 ;
      .../fabric/aurora?color=red | ?color=blue -> aurora
    """
    bslug = (brand_slug or "").strip().lower()
    try:
        from urllib.parse import urlparse, parse_qsl
        p = urlparse((product_url or "").strip())
        segs = [s for s in p.path.split("/") if s]
        base = ""
        if segs:
            last = segs[-1]
            if re.fullmatch(r"\d{2,4}", last) and len(segs) >= 2:
                base = segs[-2]                              # /CA1580/092 -> CA1580 (slash+renk)
            else:
                m = re.match(r"^(.+?)-\d{2,4}$", last)
                if m and m.group(1):
                    base = m.group(1)                        # JA7161-071 -> JA7161 (tire+renk)
                else:
                    base = last                              # aurora (soyma yok)
        else:
            base = (p.netloc or "").lower()
        # Renk + tracking query'lerini at; kalan anlamlı query'yi kanonik ekle
        # (query-id'li sitelerde aşırı-gruplamayı önler; renk/tracking atılır ki varyant gruplanır).
        kept = []
        for k, v in parse_qsl(p.query, keep_blank_values=False):
            kl = (k or "").strip().lower()
            if kl in _COLOR_QUERY_KEYS or kl in _TRACKING_QUERY_KEYS or kl.startswith("utm_"):
                continue
            kept.append((kl, (v or "").strip().lower()))
        if kept:
            kept.sort()
            base = base + "?" + "&".join(f"{k}={v}" for k, v in kept)
        base = base.strip().lower()
        return base, f"{bslug}:{base}"
    except Exception:
        return "", f"{bslug}:"


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


def research_save(research_id: str, patch: dict) -> dict | None:
    """v4.0-part-2 Sprint 11 — research_pool satırına kısmi update (albums/images vb.).
    Generik yazıcı: rotalar research_get ile okur, mutasyona uğratır, buraya
    {"albums": [...], "images": [...]} gibi patch gönderir."""
    if not research_id or not patch:
        return None
    res = (client().table(TABLE_RESEARCH).update(patch)
           .eq("id", research_id).execute())
    return (res.data or [None])[0]


def product_find_by_url_hash(hash_: str) -> dict | None:
    """Aynı URL hash'li ürün var mı (research → product dedup)."""
    res = client().table(TABLE).select("urun_id,product_name,brand").eq("source_url_hash", hash_).limit(1).execute()
    return res.data[0] if res.data else None


def research_find_family_siblings(family_key: str | None) -> list[dict]:
    """OnCalisma-V2 (Problem 1) — Aynı family_key'e sahip pending kayıtlar (en eski önce).
    family_key boş veya ':' ile bitiyorsa (base_code türetilemedi) [] döner."""
    if not family_key or family_key.endswith(":"):
        return []
    try:
        res = (client().table(TABLE_RESEARCH)
               .select("id,added_at,variant_of")
               .eq("family_key", family_key)
               .eq("status", "pending")
               .order("added_at", desc=False)
               .execute())
        return res.data or []
    except Exception:
        # family_key kolonu yoksa (migration henüz uygulanmadı) → sessizce boş
        return []


def compute_family_fields(product_url: str | None, brand_slug: str | None) -> dict:
    """OnCalisma-V2 (Problem 1) — Ekleme öncesi family/varyant alanlarını hesapla.
    İŞARETLER, BİRLEŞTİRMEZ (Anayasa #6). Aynı aileden başka pending kayıt varsa
    is_variant_candidate=True + variant_of=<en eski sibling'in kökü>."""
    base, fk = derive_base_code(product_url, brand_slug)
    sibs = research_find_family_siblings(fk)
    if sibs:
        vof = sibs[0].get("variant_of") or sibs[0].get("id")
        cand = True
    else:
        vof = None
        cand = False
    return {
        "base_code": base or None,
        "family_key": fk,
        "is_variant_candidate": cand,
        "variant_of": vof,
    }


_FAMILY_KEYS = ("family_key", "base_code", "is_variant_candidate", "variant_of")


def research_insert(row: dict):
    """OnCalisma-V2 (Problem 1) — research_pool insert; migration uygulanmadıysa
    (family kolonları yoksa) family alanlarını düşürüp yeniden dener → 'ekle' bozulmaz.
    Diğer hataları (ör. UNIQUE duplicate) AYNEN yukarı fırlatır."""
    try:
        return client().table(TABLE_RESEARCH).insert(row).execute()
    except Exception as e:
        msg = str(e).lower()
        if any(k in msg for k in _FAMILY_KEYS) or "schema cache" in msg or "column" in msg:
            slim = {k: v for k, v in row.items() if k not in _FAMILY_KEYS}
            return client().table(TABLE_RESEARCH).insert(slim).execute()
        raise


# ---------------------------------------------------------------------------
# OnCalisma-V2 (Problem 2) — Taksonomi controlled vocabulary + doğrulama.
# TEK KAYNAK: backend doğrulaması ve frontend dropdown'u BUNDAN beslenir.
# Değerler Türkçe, sabit listeler. AI doldurma YOK (Problem 4); manuel/boş girilebilir.
# ---------------------------------------------------------------------------
VALID_CATEGORIES = ["tul", "dekoratif", "dosemelik", "outdoor", "karartma", "diger"]
VALID_WEAVE_TAGS = ["leno", "tabby", "jakar", "vual", "batist", "twill", "marquisette", "crash", "rep", "saten", "orme"]
VALID_PATTERNS = ["cizgili", "duz", "yari-duz", "desenli", "karma"]
VALID_COLOR_FAMILIES = ["beyaz", "krem-bej", "gri", "siyah", "mavi", "yesil", "sari", "turuncu", "kirmizi", "pembe", "mor", "kahve", "coklu"]
# Tek tabloda taksonomi kolonları (migration dayanıklılığı + whitelist için).
# P4b: color_count + ai_notu da migration-öncesi strip-retry ile düşürülebilsin diye burada.
_TAXONOMY_KEYS = ("category", "pattern", "weave_tags", "style_tags", "color_family", "color_count", "ai_notu")
# OnCalisma-V2 (Problem 4a) — Gemini zenginleştirme staging kolonları (migration ile)
_ENRICHMENT_KEYS = ("extracted_facts", "ai_summary", "enrichment_status")


def _norm_enum(v) -> str:
    """Enum değerini normalize et: strip + lower. None/boş → ''."""
    return ("" if v is None else str(v)).strip().lower()


def _validate_enum(v, allowed: list[str]) -> str | None:
    """Normalize edilen değer allowed içindeyse döndür, değilse None (sessiz temizle)."""
    nv = _norm_enum(v)
    return nv if nv in allowed else None


def validate_category(v) -> str | None:
    return _validate_enum(v, VALID_CATEGORIES)


def validate_pattern(v) -> str | None:
    return _validate_enum(v, VALID_PATTERNS)


def validate_color_family(v) -> str | None:
    return _validate_enum(v, VALID_COLOR_FAMILIES)


def validate_enum_list(vals, allowed: list[str]) -> list[str]:
    """weave_tags — listedeki geçerli (allowed) değerleri süz; tekrar/boş at, sıra korunur."""
    out: list[str] = []
    for v in (vals or []):
        nv = _norm_enum(v)
        if nv in allowed and nv not in out:
            out.append(nv)
    return out


def validate_str_list(vals) -> list[str]:
    """style_tags — serbest string listesi; trim, boş at, tekrar at (içerik doğrulanmaz)."""
    out: list[str] = []
    for v in (vals or []):
        s = ("" if v is None else str(v)).strip()
        if s and s not in out:
            out.append(s)
    return out


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

    # OnCalisma-V2 (Problem 1) — family/varyant işaretleri (tam-URL dedup AYNEN korunur)
    row.update(compute_family_fields(purl, row["brand_slug"]))

    res = research_insert(row)
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
    """Fiziksel silme (admin): DB satırı + storage görselleri (sızıntı bırakmadan)."""
    row = research_get(research_id)
    if row:
        paths: list[str] = []
        if row.get("image_storage_path"):
            paths.append(row["image_storage_path"])
        for im in (row.get("images") or []):
            sp = im.get("storage_path")
            if sp:
                paths.append(sp)
        if paths:
            try:
                delete_images(paths)   # gorseller bucket (_inbox/... research görselleri)
            except Exception:
                pass  # storage temizliği başarısızsa bile DB satırını sil
    client().table(TABLE_RESEARCH).delete().eq("id", research_id).execute()


# v4.0-part-2 Sprint 6 — Düzenleme + Favori

# Düzenlenebilir alanlar (whitelist) — diğer alanları PATCH eden istek atlanır.
RESEARCH_EDITABLE_FIELDS = {
    "master_url", "product_url", "product_url_hash",
    "brand", "brand_slug", "country", "country_code",
    "notes", "thumb_url", "is_favorite",
    # OnCalisma-V2 (Problem 1) — kullanıcı "bu aileye bağla/ayır" diyebilir.
    # family_key/base_code/is_variant_candidate sistem-türetimli; patch DIŞINDA.
    "variant_of",
    # OnCalisma-V2 (Problem 2) — taksonomi (kullanıcı havuzda elle sınıflandırabilir).
    "category", "pattern", "weave_tags", "style_tags", "color_family",
    # OnCalisma-V2 (Problem 4a) — Gemini staging (enrich/verify endpoint'leri yazar).
    "extracted_facts", "ai_summary", "enrichment_status",
    # OnCalisma-V2 (Problem 4b) — renk sayısı + AI notu (kullanıcı drawer'da düzenler).
    "color_count", "ai_notu",
    # Sprint 12 — ürün taslağı (çekmecedeki genişletilmiş ürün alanları, jsonb)
    "product_draft",
}


def research_update(research_id: str, patch: dict) -> dict | None:
    """Whitelist'li alanları güncelle. Boş patch hata değil — no-op."""
    safe = {k: v for k, v in patch.items() if k in RESEARCH_EDITABLE_FIELDS}
    if not safe:
        return research_get(research_id)
    try:
        res = client().table(TABLE_RESEARCH).update(safe).eq("id", research_id).execute()
    except Exception as e:
        # OnCalisma-V2 (P2 taksonomi + P4a enrichment) — opsiyonel kolonlar migration
        # öncesi yoksa onları düşür+retry. Diğer hatalar aynen fırlar.
        _opt = _TAXONOMY_KEYS + _ENRICHMENT_KEYS
        msg = str(e).lower()
        if any(k in msg for k in _opt) or "schema cache" in msg or "column" in msg:
            slim = {k: v for k, v in safe.items() if k not in _opt}
            if not slim:
                return research_get(research_id)
            res = client().table(TABLE_RESEARCH).update(slim).eq("id", research_id).execute()
        else:
            raise
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


def _workspace_doc() -> dict:
    """workspace_fabric_ids app_state dokümanı: {fabric_ids, scope_orders, updated_at}.
    Backfill (migration-siz): eski {fabric_ids:[...]} → scope_orders {} eklenir.
    fabric_ids = pin SETİ + KÖK (Tümü) sırası; scope_orders[albumId] = klasör kapsamı sırası."""
    state = get_app_state(WORKSPACE_KEY) or {}
    if not isinstance(state, dict):
        state = {}
    state.setdefault("fabric_ids", [])
    state.setdefault("scope_orders", {})
    return state


def _workspace_doc_save(doc: dict) -> None:
    doc["updated_at"] = _now_iso()
    set_app_state(WORKSPACE_KEY, doc)


def workspace_get_ids() -> list[str]:
    """Çalışma alanına pinlenmiş ürün id'leri (KÖK/Tümü sırası)."""
    return list(_workspace_doc().get("fabric_ids") or [])


def workspace_scope_orders() -> dict:
    """Kapsam (klasör albümü) → kaydedilmiş sıra map'i. Kök kapsam fabric_ids'tedir."""
    return dict(_workspace_doc().get("scope_orders") or {})


def workspace_add(urun_id: str) -> list[str]:
    """Bir ürünü workspace'e ekle (yoksa). KÖK sıranın SONUNA. scope_orders korunur."""
    doc = _workspace_doc()
    ids = list(doc.get("fabric_ids") or [])
    if urun_id and urun_id not in ids:
        ids.append(urun_id)
        doc["fabric_ids"] = ids
        _workspace_doc_save(doc)
    return ids


def workspace_remove(urun_id: str) -> list[str]:
    """Unpin: kök sıradan + TÜM kapsam sıralarından çıkar."""
    doc = _workspace_doc()
    doc["fabric_ids"] = [i for i in (doc.get("fabric_ids") or []) if i != urun_id]
    so = doc.get("scope_orders") or {}
    for k in list(so.keys()):
        so[k] = [i for i in so[k] if i != urun_id]
    doc["scope_orders"] = so
    _workspace_doc_save(doc)
    return doc["fabric_ids"]


def workspace_reorder(ids: list[str]) -> list[str]:
    """KÖK (Tümü) sırasını değiştir. Yalnız mevcut pinler korunur. scope_orders KORUNUR."""
    doc = _workspace_doc()
    current = set(doc.get("fabric_ids") or [])
    doc["fabric_ids"] = [i for i in ids if i in current]
    _workspace_doc_save(doc)
    return doc["fabric_ids"]


def workspace_reorder_scope(scope_id, ids: list[str]) -> list[str]:
    """Bir KAPSAMIN sırasını kaydet. scope_id boş → kök (workspace_reorder).
    Aksi halde scope_orders[scope_id] = [pinli id'ler]; fabric_ids + diğer kapsamlar DOKUNULMAZ."""
    scope_id = (scope_id or "").strip()
    if not scope_id:
        return workspace_reorder(ids)
    doc = _workspace_doc()
    current = set(doc.get("fabric_ids") or [])
    cleaned = [i for i in ids if i in current]
    so = doc.get("scope_orders") or {}
    so[scope_id] = cleaned
    doc["scope_orders"] = so
    _workspace_doc_save(doc)
    return cleaned


# =================================================================
# v4.0-part-2 Sprint 13 — Çalışma Alanı albümleri (workspace_data)
# =================================================================
# Mevcut workspace_fabric_ids (flat array) DOKUNULMAZ — backward compat.
# Yeni: workspace_data = {
#   "albums": [{"id": uuid, "name": "Yaz 2026", "color": "#abc", "created_at": ISO}],
#   "membership": {"urun_1": "<album_id>" | null, ...},
#   "updated_at": ISO
# }
# album_id None / yok → ürün "Tümü" tab'ında ama hiçbir albüme ait değil.

import uuid as _uuid

WORKSPACE_DATA_KEY = "workspace_data"


def workspace_data_get() -> dict:
    state = get_app_state(WORKSPACE_DATA_KEY) or {}
    if not isinstance(state, dict):
        return {"albums": [], "membership": {}, "updated_at": _now_iso()}
    state.setdefault("albums", [])
    state.setdefault("membership", {})
    return state


def _workspace_data_save(data: dict) -> dict:
    data["updated_at"] = _now_iso()
    set_app_state(WORKSPACE_DATA_KEY, data)
    return data


def workspace_album_create(name: str, color: str | None = None, parent_id: str | None = None) -> dict:
    """Yeni albüm/klasör yarat. Faz 3: parent_id ile sınırsız derinlik (None = kök).
    Aynı isimde birden fazla olabilir (UUID id'leriyle ayrılır)."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Albüm adı boş olamaz")
    data = workspace_data_get()
    parent_id = (parent_id or "").strip() or None
    if parent_id and parent_id not in {a.get("id") for a in data["albums"]}:
        raise ValueError("Üst klasör bulunamadı")
    album = {
        "id": _uuid.uuid4().hex,
        "name": name,
        "color": (color or "").strip() or None,
        "parent_id": parent_id,   # Faz 3 — ağaç
        "created_at": _now_iso(),
    }
    data["albums"].append(album)
    _workspace_data_save(data)
    return album


def workspace_album_delete(album_id: str) -> bool:
    """Klasörü sil. Faz 3: alt klasörler ve üye ürünler bir ÜST düzeye taşınır (promote) —
    veri kaybı yok. Silinen kök ise çocuklar/üyeler "Tümü"ye (None) düşer."""
    if not album_id:
        return False
    data = workspace_data_get()
    target = next((a for a in data["albums"] if a.get("id") == album_id), None)
    if not target:
        return False
    parent_id = target.get("parent_id") or None  # silinenin ebeveyni (kök ise None)
    # Çocukları bir üste taşı
    for a in data["albums"]:
        if (a.get("parent_id") or None) == album_id:
            a["parent_id"] = parent_id
    # Düğümü kaldır
    data["albums"] = [a for a in data["albums"] if a.get("id") != album_id]
    # Üye ürünleri ebeveyne taşı (None ise "Tümü")
    data["membership"] = {k: (parent_id if v == album_id else v) for k, v in (data["membership"] or {}).items()}
    _workspace_data_save(data)
    # Silinen klasörün kapsam sırasını da temizle (workspace_fabric_ids.scope_orders)
    try:
        doc = _workspace_doc()
        if album_id in (doc.get("scope_orders") or {}):
            doc["scope_orders"].pop(album_id, None)
            _workspace_doc_save(doc)
    except Exception:
        pass  # best-effort
    return True


def workspace_album_rename(album_id: str, new_name: str, color: str | None = None) -> bool:
    new_name = (new_name or "").strip()
    if not album_id or not new_name:
        return False
    data = workspace_data_get()
    for a in data["albums"]:
        if a.get("id") == album_id:
            a["name"] = new_name
            if color is not None:
                a["color"] = (color or "").strip() or None
            _workspace_data_save(data)
            return True
    return False


def workspace_set_album(urun_id: str, album_id: str | None) -> dict:
    """Bir ürünü belirli albüme taşı. album_id=None → "Tümü" (albümsüz)."""
    if not urun_id:
        return workspace_data_get()
    data = workspace_data_get()
    # album_id geçerli mi kontrol et (None hariç)
    if album_id:
        known_ids = {a.get("id") for a in data["albums"]}
        if album_id not in known_ids:
            raise ValueError("Albüm bulunamadı")
    membership = data.get("membership") or {}
    if album_id is None:
        membership.pop(urun_id, None)
    else:
        membership[urun_id] = album_id
    data["membership"] = membership
    _workspace_data_save(data)
    return data


# Workspace remove'ı extend et: membership'ten de temizle
_original_workspace_remove = workspace_remove


def workspace_remove(urun_id: str) -> list[str]:  # type: ignore[no-redef]
    """Sprint 13: workspace çıkış + membership temizliği."""
    ids = _original_workspace_remove(urun_id)
    try:
        data = workspace_data_get()
        if urun_id in (data.get("membership") or {}):
            data["membership"].pop(urun_id, None)
            _workspace_data_save(data)
    except Exception:
        pass  # best-effort
    return ids


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
