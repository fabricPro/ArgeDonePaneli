"""Mobidik ARGE — Manuel Kumas Gorsel Kuratorluk Paneli (v3.1 — bulut).

Veri: Supabase Postgres (products tablosu) · Gorseller: Supabase Storage (gorseller bucket)
Erisim: tek sifreli giris (APP_PASSWORD). Her yerden (mobil dahil) kullanilir.

Env: SUPABASE_URL, SUPABASE_SERVICE_KEY, APP_PASSWORD, SECRET_KEY
Calistirma (yerel):  python web/app.py     |  Bulut (Render): gunicorn --chdir web app:app
"""
from __future__ import annotations

import io
import re
import unicodedata
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # yereldeyse .env yukle

import os

import math
from flask import (
    Flask, abort, jsonify, make_response, redirect, render_template, request, session, url_for,
)
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

import hashlib
import hmac
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen
import xml.etree.ElementTree as ET  # tasarim-v2 Plan Parça 1 — TCMB kur XML parse

import requests  # tasarim-v2 Plan Parça 1 — TCMB kur fetch (requirements.txt'te mevcut)

import store

# v4.0-part-2 Sprint 11 — Gemini destekli "Linkten Doldur" özelliği.
# SDK opsiyonel; modülün kendisi yoksa veya GEMINI_API_KEY tanımsızsa route 503 döner.
try:
    import gemini_extract as gx
    _GEMINI_AVAILABLE = True
except ImportError:
    gx = None  # type: ignore
    _GEMINI_AVAILABLE = False


# v4.0-part-2 Adım 7 — Sade Notlar HTML sanitize (regex tabanlı, bleach'siz)
#
# Tek-kullanıcılı admin paneli (APP_PASSWORD ile korumalı) — XSS risk düşük.
# Asıl risk: yapıştırılan içerikten gelen <script>, <iframe>, on* event handler'lar.
# Bunları regex ile temizliyoruz (whitelist yerine blocklist — daha esnek + tag'leri tutar).
_DANGEROUS_TAGS = re.compile(
    r"</?(?:script|iframe|object|embed|form|input|button|link|style|meta|svg|math|base|frame|frameset)\b[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
# Tüm event handler attribute'ları (onload, onclick, onerror, vb.)
_EVENT_HANDLERS = re.compile(
    r"""\s+on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""",
    re.IGNORECASE,
)
# javascript: ve data: URL'leri (data:image hariç)
_JS_URLS = re.compile(
    r"""(href|src)\s*=\s*(?:"\s*javascript:[^"]*"|'\s*javascript:[^']*'|"\s*data:(?!image/)[^"]*"|'\s*data:(?!image/)[^']*')""",
    re.IGNORECASE,
)


def _sanitize_notlar_html(html: str) -> str:
    """Tehlikeli HTML elemanlarını temizle (script, iframe, event handlers, js: URLs).
    Tag whitelist YOK — admin kullanıcının yazdığı her şey kabul edilir, sadece
    XSS vektörleri silinir."""
    if not html:
        return ""
    s = _DANGEROUS_TAGS.sub("", html)
    s = _EVENT_HANDLERS.sub("", s)
    s = _JS_URLS.sub(r"\1=''", s)
    return s


# v4.0-part-2 Adım 7 — PDF upload limitleri
PDF_MAX_BYTES = 25 * 1024 * 1024  # 25 MB

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB
# Sablon onbellegini kapat — her istekte disk mtime kontrolu (hem yerel hem Render)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
# v4.0-part-2 Sprint 9 — Tarayıcı eklentisi yakalama endpoint'i için token
MOBIDIK_API_TOKEN = os.environ.get("MOBIDIK_API_TOKEN", "")
EXTENSION_MAX_BYTES = 25 * 1024 * 1024  # 25 MB


# OnCalisma-V2 — çalışılan git branch'ini bir kez tespit et (deneme branch'lerinde UI rozeti için).
def _detect_git_branch() -> str:
    env_b = os.environ.get("APP_GIT_BRANCH", "").strip()
    if env_b:
        return env_b
    try:
        import subprocess
        root = str(Path(__file__).resolve().parent.parent)
        out = subprocess.run(
            ["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3,
        )
        return (out.stdout or "").strip() if out.returncode == 0 else ""
    except Exception:
        return ""


APP_GIT_BRANCH = _detect_git_branch()


@app.context_processor
def inject_git_branch():
    # Rozet yalnız deneme branch'lerinde görünür; main/master (üretim) ve tespit edilemezse gizli.
    b = APP_GIT_BRANCH
    return {"git_branch": b, "git_branch_show": bool(b) and b not in ("main", "master")}

TRACKED_BRANDS = [
    ("Kvadrat", "kvadrat"), ("Dedar", "dedar"), ("Rubelli", "rubelli"),
    ("Sahco", "sahco"), ("Nya Nordiska", "nya_nordiska"),
    ("Création Baumann", "creation_baumann"), ("Zimmer + Rohde", "zimmer_rohde"),
    ("ADO Goldkante", "ado_goldkante"), ("Etamine", "etamine"), ("Travers", "travers"),
]
COUNTRY_SUGGESTIONS = [
    "Türkiye", "Danimarka", "İtalya", "Almanya", "Fransa", "Belçika",
    "ABD", "İsveç", "İsviçre", "Hollanda", "İngiltere", "Avusturya",
]
WEAVE_SUGGESTIONS = ["dobby", "jacquard", "plain", "leno", "sheer", "bouclé", "saten", "twill"]

# v4.0-part-2 Sprint 11.7 / P4a-2 — Gemini model override whitelist (TEK KAYNAK).
# UI dropdown'larından gelen değer burada doğrulanır; dışındaki/boş → None (server default).
# Hem /api/urun/linkten-doldur hem /api/arastirma/<id>/enrich kullanır.
GEMINI_MODEL_WHITELIST = {
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-pro-latest",
}

COUNTRY_MAP = {
    "italy": "İtalya", "italya": "İtalya", "italia": "İtalya",
    "turkey": "Türkiye", "turkiye": "Türkiye", "germany": "Almanya", "deutschland": "Almanya",
    "france": "Fransa", "belgium": "Belçika", "belgique": "Belçika",
    "usa": "ABD", "us": "ABD", "united states": "ABD", "denmark": "Danimarka",
    "sweden": "İsveç", "switzerland": "İsviçre", "netherlands": "Hollanda",
    "uk": "İngiltere", "united kingdom": "İngiltere", "india": "Hindistan", "austria": "Avusturya",
}


# ============================================================
# Helpers
# ============================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = text.translate(str.maketrans("çğıİöşü", "cgiiosu"))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "urun"


def brand_slugify(text: str) -> str:
    s = slugify(text).replace("-", "_")
    return re.sub(r"[^a-z0-9_]", "_", s) or "diger"


def norm_country(c: str | None) -> str | None:
    if not c:
        return None
    c = c.strip()
    return COUNTRY_MAP.get(c.lower(), c)


def parse_int(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def clean(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def country_list() -> list[str]:
    """COUNTRY_SUGGESTIONS + data'dan unique ulkeleri alfabetik."""
    cs: set[str] = set(COUNTRY_SUGGESTIONS)
    try:
        for p in store.get_all():
            c = p.get("country")
            if c:
                cs.add(c)
    except Exception:
        pass
    return sorted(cs, key=lambda s: s.lower())


# ============================================================
# v4.0-part-2 Adım 6 — Firma Kütüphanesi (brands_registry)
# ============================================================

# v4.0-part-2 Sprint 11.5: Bu map artik kesinlikle BRAND HQ (firma merkezi).
# brand_registry.country alanini seed eder; UI tarafi bu degeri "Firma Ulkesi" alanina basar.
# Uretim ulkesi (production_country) AYRI bir alan — yalniz Gemini sayfadan cikarir.
BRAND_COUNTRY_HINT = {
    "kvadrat": "Danimarka", "dedar": "İtalya", "rubelli": "İtalya",
    "sahco": "İsveç", "nya_nordiska": "Almanya",
    "creation_baumann": "İsviçre", "zimmer_rohde": "Almanya",
    "ado_goldkante": "Almanya", "etamine": "Fransa", "travers": "ABD",
}

BRANDS_REGISTRY_KEY = "brands_registry"
BRANDS_REGISTRY_VERSION = "v4.0-part-2-adim6"


def _unique_brand_slug(name: str, existing: set[str]) -> str:
    """brand_slugify'dan unique slug üretir (-2, -3 suffix gerekirse)."""
    base = brand_slugify(name) or "diger"
    if base not in existing:
        return base
    i = 2
    while f"{base}-{i}" in existing:
        i += 1
    return f"{base}-{i}"


def save_brands_registry(brands: list[dict]) -> None:
    """Registry'yi app_state'e yazar."""
    try:
        store.set_app_state(BRANDS_REGISTRY_KEY, {
            "_seed_version": BRANDS_REGISTRY_VERSION,
            "_seeded_at": now_iso(),
            "brands": brands,
        })
    except Exception:
        pass


def seed_brands_registry() -> list[dict]:
    """İlk açılışta TRACKED_BRANDS + ürün brand'lerinden otomatik seed.
    Ülke tahmini: TRACKED için BRAND_COUNTRY_HINT, ürünlerden gelenler için
    Counter most_common ülke (majority vote)."""
    seen: set[str] = set()
    brands: list[dict] = []
    ts = now_iso()
    # 1. TRACKED_BRANDS — sabit liste (ülke MAP'ten)
    for name, slug in TRACKED_BRANDS:
        brands.append({
            "slug": slug, "name": name,
            "country": BRAND_COUNTRY_HINT.get(slug),
            "website": None,
            "created_at": ts, "updated_at": ts,
        })
        seen.add(slug)
    # 2. Ürünlerden ek markalar (slug bazında dedup, ülke majority vote)
    try:
        products = store.get_all()
    except Exception:
        products = []
    by_slug: dict[str, dict] = {}
    for p in products:
        s = p.get("brand_slug")
        if not s or s in seen:
            continue
        info = by_slug.setdefault(s, {"names": [], "countries": []})
        if p.get("brand"):
            info["names"].append(p["brand"])
        if p.get("country"):
            info["countries"].append(p["country"])
    for slug, info in by_slug.items():
        name_winner = Counter(info["names"]).most_common(1)[0][0] if info["names"] else slug
        country_winner = Counter(info["countries"]).most_common(1)[0][0] if info["countries"] else None
        brands.append({
            "slug": slug, "name": name_winner,
            "country": country_winner, "website": None,
            "created_at": ts, "updated_at": ts,
        })
    save_brands_registry(brands)
    return brands


def get_brands_registry() -> list[dict]:
    """Registry'den firmaları döner; boşsa otomatik seed çalıştırır."""
    try:
        reg = store.get_app_state(BRANDS_REGISTRY_KEY) or {}
    except Exception:
        reg = {}
    brands = reg.get("brands") if isinstance(reg, dict) else None
    if not brands:
        return seed_brands_registry()
    return brands


def get_brand_product_counts() -> dict[str, int]:
    """settings.html'de 'Ürün #' kolonu için: her brand_slug için ürün sayısı."""
    try:
        products = store.get_all()
    except Exception:
        return {}
    return dict(Counter(p.get("brand_slug") for p in products if p.get("brand_slug")))


def save_image(file_storage, dest_prefix: str, order: int) -> str:
    """Gorseli jpg'e normalize edip Supabase Storage'a yukle. Bucket-yolu doner."""
    img = Image.open(file_storage.stream)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((2000, 2000))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    path = f"{dest_prefix}/{order}_{uuid.uuid4().hex[:8]}.jpg"
    store.upload_image(path, buf.getvalue(), "image/jpeg")
    return path


def infer_prefix(d: dict) -> str:
    images = d.get("images") or []
    if images and images[0].get("path") and "/" in images[0]["path"]:
        return images[0]["path"].rsplit("/", 1)[0]
    bs = d.get("brand_slug") or "diger"
    code = slugify(d.get("product_code") or d.get("urun_id") or "urun")
    return f"{bs}/{code}"


def cover_path(d: dict) -> str | None:
    images = d.get("images") or []
    cover = next((im for im in images if im.get("is_cover")), None)
    if cover is None and images:
        cover = sorted(images, key=lambda x: x.get("order", 0))[0]
    return cover.get("path") if cover else None


def _palette_completed(d: dict, color_album_slug: str | None) -> bool:
    """v4.0-part-2 Sprint 13: Renkler albumundeki TUM gorsellere en az 1 rol
    atanmis mi? Tek bir gorsel rolsuzse False. Hicbir Renkler gorseli yoksa False.
    Sprint 12 normalize ile array (weft/warp) ve obje (mix) farkini saklar."""
    if not color_album_slug:
        return False
    color_images = [
        im for im in (d.get("images") or [])
        if color_album_slug in (im.get("albums") or [])
    ]
    if not color_images:
        return False
    for im in color_images:
        c = _normalize_role_colors(im.get("colors") or {})
        if not (c.get("weft") or c.get("warp") or c.get("mix")):
            return False
    return True


def product_summary(d: dict) -> dict:
    # "Renkler" adında veya slug'ında albüm var mı? (v3.6+)
    has_color_album = False
    color_album_slug = None
    color_album_image_count = 0
    for a in (d.get("albums") or []):
        a_slug = (a.get("slug") or "").lower()
        a_name = (a.get("name") or "").strip().lower()
        if a_slug == "renkler" or a_name == "renkler":
            color_album_slug = a.get("slug")
            break
    if color_album_slug:
        # Albüme atanmış görsel sayısı (varyantlar = bu albümdeki swatch sayısı)
        for im in (d.get("images") or []):
            if color_album_slug in (im.get("albums") or []):
                color_album_image_count += 1
        has_color_album = color_album_image_count > 0
    # Renk paleti sayısı (auto-derived — kaç renk Atkı/Çözgü/Toplam ile atanmış)
    # v4.0-part-2 Sprint 12: weft/warp ARRAY, mix obje — _derive_color_palette zaten
    # normalize edip hex bazlı dedup ediyor; tek-renkli eski kayıtlar da uyumlu.
    palette_size = len(_derive_color_palette(d.get("images") or []))
    # v4.0-part-2 Sprint 13: palette tamamlandi mi? (galeri kart ikonu parıltısı)
    palette_completed = _palette_completed(d, color_album_slug)
    return {
        "urun_id": d.get("urun_id"), "brand": d.get("brand"),
        "brand_slug": d.get("brand_slug"), "country": d.get("country"),
        "collection": d.get("collection"), "product_name": d.get("product_name"),
        "product_code": d.get("product_code"), "width_cm": d.get("width_cm"),
        "weave_type": d.get("weave_type"),
        "cover_image": store.public_url(cover_path(d)),
        "variant_count": len(d.get("images") or []),
        "updated_at": d.get("updated_at"),
        "has_color_album": has_color_album,
        "color_album_image_count": color_album_image_count,
        "palette_size": palette_size,
        "palette_completed": palette_completed,  # v4.0-part-2 Sprint 13
        # v4.0-part-2 Sprint 14 — Favori sayımı
        "favorite_count": sum(1 for im in (d.get("images") or []) if im.get("is_favorite")),
        # v4.0-part-2 Adım 8 — Galeri filtre + kart indikatörleri
        "status": d.get("status") or "active",
        "country_code": d.get("country_code"),
        # v4.0-part-2 Sprint 11.5 — country ayrimi (yeni alanlar; country = brand_country alias)
        "brand_country": d.get("brand_country") or d.get("country"),
        "brand_country_code": d.get("brand_country_code") or d.get("country_code"),
        "production_country": d.get("production_country"),
        "production_country_code": d.get("production_country_code"),
        "reference_price": d.get("reference_price"),
        "reference_price_type": d.get("reference_price_type"),
        "has_teknik": store.has_teknik_calisma(d),
        "has_pdf": store.has_pdfs(d),
        "has_notlar": store.has_notlar(d),
        # tasarim-v2 Sprint 18 — tooltip için sayılar (v{N} sürüm, {N} PDF)
        "teknik_surum_count": len(((d.get("teknik") or {}).get("surumler")) or []),
        "pdf_count": len(d.get("pdfs") or []),
        # Ön çalışmadan taşınan sınıflandırma (kart/rail chip'leri — F5)
        "category": d.get("category"),
        "pattern": d.get("pattern"),
        "color_family": d.get("color_family"),
        "color_count": d.get("color_count"),
        "weave_tags": d.get("weave_tags") or [],
        "style_tags": d.get("style_tags") or [],
        # Faz 2 — To-Do ilerleme rozeti (galeri/çalışma kartı)
        "todo_total": len(d.get("todo") or []),
        "todo_done": sum(1 for t in (d.get("todo") or []) if isinstance(t, dict) and t.get("done")),
    }


# ============================================================
# Auth
# ============================================================

@app.before_request
def require_login():
    if request.endpoint in (
        "login", "static", "health", "service_worker", "web_manifest",
        "api_arastirma_yakala",            # v4.0-part-2 Sprint 9 — token ile korunur
        "api_arastirma_entries_summary",   # v4.0-part-2 Sprint 10 — eklenti modal listesi
    ):
        return
    if not APP_PASSWORD:
        return  # sifre tanimli degil -> acik (yerel gelistirme)
    if not session.get("auth"):
        return redirect(url_for("login", next=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if APP_PASSWORD and request.form.get("password") == APP_PASSWORD:
            session["auth"] = True
            session.permanent = True
            return redirect(request.args.get("next") or url_for("index"))
        return render_template("login.html", error="Yanlış şifre"), 401
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ============================================================
# Sayfalar
# ============================================================

@app.route("/")
def index():
    raw = store.get_all()
    products = [product_summary(p) for p in raw]
    # dashboard_order'i ozetlere ekle (siralama icin)
    order_map = {p.get("urun_id"): p.get("dashboard_order") for p in raw}
    # v4.0-part-2 Sprint 8 — workspace pin durumu (galeri kartlarında ikon için)
    workspace_ids = set(store.workspace_get_ids())
    for s in products:
        s["dashboard_order"] = order_map.get(s["urun_id"])
        s["in_workspace"] = s.get("urun_id") in workspace_ids
    # Ulkelere grupla
    groups: dict[str, list] = {}
    for p in products:
        groups.setdefault(p.get("country") or "Belirtilmemiş", []).append(p)
    # Grup ici siralama: dashboard_order ASC NULLS LAST, sonra updated_at DESC
    for items in groups.values():
        items.sort(key=lambda p: p.get("updated_at") or "", reverse=True)
        items.sort(key=lambda p: p.get("dashboard_order") if p.get("dashboard_order") is not None else 10**9)
    # Grup sirasi: app_state.country_order varsa o; yoksa default (count desc, Belirtilmemis son)
    saved_order = store.get_app_state("country_order") or []
    if saved_order:
        ordered: list = []
        used: set = set()
        for c in saved_order:
            if c in groups:
                ordered.append((c, groups[c]))
                used.add(c)
        for c, items in groups.items():
            if c not in used:
                ordered.append((c, items))
        country_groups = ordered
    else:
        country_groups = sorted(
            groups.items(),
            key=lambda kv: (kv[0] == "Belirtilmemiş", -len(kv[1]), kv[0]),
        )
    brands = sorted({p["brand"] for p in products if p.get("brand")})
    return render_template(
        "index.html", country_groups=country_groups, total=len(products), brands=brands,
    )


@app.route("/api/sirala-dashboard", methods=["POST"])
def api_reorder_dashboard():
    """Dashboard siralamasini kaydet.
    Body: {country_order: [ulke...], product_orders: [urun_id...]} (urun_id sirasiyla dashboard_order).
    """
    data = request.get_json(force=True) or {}
    country_order = data.get("country_order") or []
    product_orders = data.get("product_orders") or []
    # Ulke sirasi kaydi
    store.set_app_state("country_order", country_order)
    # Her urune dashboard_order ata
    for idx, urun_id in enumerate(product_orders):
        d = store.get(urun_id)
        if not d:
            continue
        d["dashboard_order"] = idx
        d["updated_at"] = d.get("updated_at") or now_iso()  # zaman bozma
        store.upsert(d)
    return jsonify({"ok": True, "saved_countries": len(country_order), "saved_products": len(product_orders)})


@app.route("/ekle")
def ekle():
    # v4.0-part-2 Adım 8 — Ön Çalışmadan prefill (URL ?from_research=<id>)
    prefill = None
    from_research_id = request.args.get("from_research")
    if from_research_id:
        try:
            prefill = store.research_get(from_research_id)
        except Exception:
            prefill = None
    # v4.0-part-2 Sprint 10.5 — research entry'sinin galerisi → önizleme listesi
    # v4.0-part-2 Sprint 11 — albüm + renk paleti bağlamı (canlı düzenleme)
    prefill_images_with_urls = []
    research_ctx = None
    if prefill and prefill.get("images"):
        research_ctx = _research_album_ctx(prefill)
        for im in research_ctx["images_with_urls"]:
            if im.get("storage_path"):
                prefill_images_with_urls.append({
                    "path": im["storage_path"],
                    "url": im.get("url"),
                    "alt": im.get("alt") or "",
                    "albums": im.get("albums") or [],
                    "colors": im.get("colors") or {},
                })
    # Sağ panel için: tüm pending research'leri grupla (ülke → firma)
    try:
        research_rows = store.research_list(status="pending", limit=200)
    except Exception:
        research_rows = []
    # OnCalisma-V2 (Problem 4c) — Ürüne çevir ön-doldurma: YALNIZ alan-alan KABUL edilenler (Anayasa #6)
    ai_prefill: dict = {}
    if prefill:
        ef = prefill.get("extracted_facts") or {}
        for _k, _f in ef.items():
            if isinstance(_f, dict) and _f.get("accepted") and _f.get("value"):
                ai_prefill[_k] = _f["value"]
        # color_count / ai_notu: manuel onaylı research kolonları (varsa) öncelikli
        if prefill.get("color_count") not in (None, "") and "color_count" not in ai_prefill:
            ai_prefill["color_count"] = prefill.get("color_count")
        if (prefill.get("ai_notu") or "").strip():
            ai_prefill["ai_notu"] = prefill.get("ai_notu")
    return render_template(
        "ekle.html", tracked_brands=TRACKED_BRANDS,
        brands_registry=get_brands_registry(),
        countries=country_list(),
        country_suggestions=COUNTRY_SUGGESTIONS, weave_suggestions=WEAVE_SUGGESTIONS,
        prefill=prefill,
        ai_prefill=ai_prefill,   # OnCalisma-V2 (Problem 4b) — verified AI verisi (ürüne çevir ön-doldurma)
        prefill_images_with_urls=prefill_images_with_urls,
        research_rows=research_rows,
        research_id=from_research_id if research_ctx else None,
        albums=(research_ctx["albums"] if research_ctx else []),
        album_counts=(research_ctx["album_counts"] if research_ctx else {}),
        color_palette=(research_ctx["palette"] if research_ctx else []),
        color_album_slug=(research_ctx["color_album_slug"] if research_ctx else None),
        color_picker_images=(research_ctx["color_picker_images"] if research_ctx else []),
        image_color_map=(research_ctx["image_color_map"] if research_ctx else {}),
        # OnCalisma-V2 (Problem 2) — taksonomi sözlükleri (tek kaynak store.py; JS'e kopyalanmaz)
        category_vocab=store.VALID_CATEGORIES,
        pattern_vocab=store.VALID_PATTERNS,
        weave_tags_vocab=store.VALID_WEAVE_TAGS,
        color_family_vocab=store.VALID_COLOR_FAMILIES,
    )


@app.route("/urun/<urun_id>")
def urun_detail(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return render_template("urun.html", product=None, urun_id=urun_id), 404
    images = sorted(d.get("images") or [], key=lambda x: x.get("order", 0))
    for im in images:
        im["url"] = store.public_url(im.get("path"))
    d["images"] = images
    # v4.0-part-2 Adım 7: PDF'lere public URL ekle
    pdfs = d.get("pdfs") or []
    for p in pdfs:
        p["url"] = store.public_url_pdf(p.get("path"))
    d["pdfs"] = pdfs
    # Gorselleri varyant etiketine gore grupla (ayni varyantlar bitisik).
    # Grup sirasi: ilk gorulus sirasi (orders korur), grup ici sirasi: order.
    groups: dict[str, list[dict]] = {}
    for im in images:
        groups.setdefault(im.get("variant_label") or "", []).append(im)
    display_items: list[dict] = []
    multi_group = len(groups) > 1
    for label, imgs in groups.items():
        if multi_group:
            display_items.append({"type": "header", "label": label or "Genel", "count": len(imgs)})
        for im in imgs:
            display_items.append({"type": "image", **im})
    pinned_items = [im for im in images if im.get("is_pinned")]
    # Hero carousel için image-only, order'a göre sıralanmış, kapak ilk
    display_images = list(images)
    cover_idx = next((i for i, im in enumerate(display_images) if im.get("is_cover")), 0)
    if cover_idx > 0:
        display_images = [display_images[cover_idx]] + display_images[:cover_idx] + display_images[cover_idx+1:]
    # Albümler
    albums = d.get("albums") or []
    album_counts = {a.get("slug"): sum(1 for im in images if a.get("slug") in (im.get("albums") or [])) for a in albums}
    # v3.6: Renk paleti (auto-derived, açıktan koyuya — LAB L desc)
    color_palette = _derive_color_palette(images)
    # v3.6+: Renk çözümleme yalnız "Renkler" albümündeki görsellerden
    color_album_slug = None
    for a in albums:
        a_slug = (a.get("slug") or "").lower()
        a_name = (a.get("name") or "").strip().lower()
        if a_slug == "renkler" or a_name == "renkler":
            color_album_slug = a.get("slug")
            break
    if color_album_slug:
        color_picker_images = [im for im in images if color_album_slug in (im.get("albums") or [])]
    else:
        color_picker_images = []
    # v4.0-part-2 Sprint 8.8 + 12 — görsel-bazlı renk paleti (kolaj + rol filtreleri)
    # Sadece "Renkler" albümündeki + en az bir rol atanmış görseller
    # Sprint 12: çoklu atkı + çoklu çözgü → adaptive layout hesabı:
    #   total renk = (1 if mix else 0) + len(weft) + len(warp)
    #   layout: solid (1) | duo (2) | quad (3 ve 1+1+1) | bands (4+ veya 2 weft / 3 warp gibi)
    image_color_map = {}
    for im in color_picker_images:
        norm = _normalize_role_colors(im.get("colors") or {})
        if not norm:
            continue
        weft_n = len(norm.get("weft", []))
        warp_n = len(norm.get("warp", []))
        has_mix = bool(norm.get("mix"))
        total = (1 if has_mix else 0) + weft_n + warp_n
        if total == 0:
            continue
        if total == 1:
            layout = "solid"
        elif total == 2:
            layout = "duo"
        elif total == 3 and weft_n == 1 and warp_n == 1 and has_mix:
            layout = "quad"  # Sprint 8.8 mevcut 4-quadrant (1+1+1)
        else:
            layout = "bands"
        image_color_map[im["path"]] = {
            "label": im.get("variant_label") or "",
            "order": im.get("order", 0),
            "url": im.get("url"),
            "colors": norm,
            "weft_count": weft_n,
            "warp_count": warp_n,
            "has_mix": has_mix,
            "total_count": total,
            "layout": layout,
        }
    # v3.8: Teknik çalışma sekme verisi + mobile UA detect
    teknik = d.get("teknik") or {}
    is_mobile_ua = _is_mobile_ua(request)
    # v4.0-part-2 Sprint 8 — Embed modu (Çalışma Alanı iframe'lerinden)
    embed = (request.args.get("embed") or "").strip().lower() or None
    if embed not in {"calisma", "calisma-left", "calisma-right"}:
        embed = None
    # In-workspace flag (header pin butonu durumu için)
    in_workspace = urun_id in set(store.workspace_get_ids())
    # v4.0-part-2 Sprint 14 — Favoriler sentinel albümü
    has_favorites = any(im.get("is_favorite") for im in (d.get("images") or []))
    favorite_count = sum(1 for im in (d.get("images") or []) if im.get("is_favorite"))
    # v4.0-part-2 Sprint 14 — Ön çalışma kaynağı (from_research_id varsa)
    from_research_row = None
    fr_id = d.get("from_research_id")
    if fr_id:
        try:
            from_research_row = store.research_get(fr_id)
        except Exception:
            from_research_row = None
        # Ön Çalışma sekmesi görselleri: ham research_get .url içermez → storage_path'ten
        # public_url üret (arastirma_detail ile aynı; yoksa template kırık https://host/storage'a düşer).
        if from_research_row and from_research_row.get("images"):
            for _im in from_research_row["images"]:
                if isinstance(_im, dict) and not _im.get("url") and _im.get("storage_path"):
                    _im["url"] = store.public_url(_im["storage_path"])
    return render_template(
        "urun.html", product=d, urun_id=urun_id,
        cover_image=store.public_url(cover_path(d)),
        display_items=display_items,
        display_images=display_images,
        color_palette=color_palette,
        color_picker_images=color_picker_images,
        color_album_slug=color_album_slug,
        image_color_map=image_color_map,
        teknik=teknik,
        is_mobile_ua=is_mobile_ua,
        pinned_items=pinned_items,
        albums=albums,
        album_counts=album_counts,
        countries=country_list(),
        brands_registry=get_brands_registry(),
        country_suggestions=COUNTRY_SUGGESTIONS, weave_suggestions=WEAVE_SUGGESTIONS,
        embed=embed,
        in_workspace=in_workspace,
        # v4.0-part-2 Sprint 14
        has_favorites=has_favorites,
        favorite_count=favorite_count,
        from_research_row=from_research_row,
    )


# ============================================================
# v4.0-part-2 Adım 6 — Ayarlar sayfası + Firma CRUD API
# ============================================================

@app.route("/ayarlar")
def ayarlar():
    brands = get_brands_registry()
    return render_template(
        "settings.html",
        brands=brands,
        brand_product_counts=get_brand_product_counts(),
        countries=country_list(),
    )


# =================================================================
# İplik Kataloğu — Parça 1 (veri modeli + CRUD + liste + meta düzenleme)
# =================================================================

def _kartela_tedarikciler() -> list[str]:
    """Mevcut kartelalardan distinct tedarikçi listesi (datalist önerisi için)."""
    return sorted({
        (k.get("tedarikci") or "").strip()
        for k in store.list_kartelalar()
        if (k.get("tedarikci") or "").strip()
    })


@app.route("/iplik-katalogu")
def iplik_katalog_list():
    items = store.list_kartelalar()
    items.sort(key=lambda k: (k.get("ad") or "").lower())
    tedarikciler = sorted({
        (k.get("tedarikci") or "").strip() for k in items if (k.get("tedarikci") or "").strip()
    })
    tipler = sorted({
        (k.get("iplik_tipi") or "").strip() for k in items if (k.get("iplik_tipi") or "").strip()
    })
    # İplik Kataloğu Parça 2-A — kart kapak görseli + toplam renk rozeti (server-side)
    for it in items:
        sayfalar = it.get("sayfalar") or []
        ilk = sayfalar[0] if sayfalar else None
        it["kapak_url"] = store.public_url_kartela(ilk.get("foto_path")) if (ilk and ilk.get("foto_path")) else None
        it["toplam_renk"] = sum(len(s.get("renkler") or []) for s in sayfalar)
    return render_template(
        "iplik_katalogu.html", items=items, tedarikciler=tedarikciler, tipler=tipler,
    )


@app.route("/iplik-katalogu/yeni")
def iplik_katalog_yeni():
    return render_template(
        "iplik_katalogu_detay.html", kartela=None, tedarikciler=_kartela_tedarikciler(),
    )


@app.route("/iplik-katalogu/<kartela_id>")
def iplik_katalog_detay(kartela_id: str):
    k = store.get_kartela(kartela_id)
    if not k:
        abort(404)
    # İplik Kataloğu Parça 2-A — sayfalara foto_url enjekte et (yalnız render için; DB'ye sızmaz).
    k = dict(k)
    k["sayfalar"] = [
        {**s, "foto_url": store.public_url_kartela(s.get("foto_path"))}
        for s in (k.get("sayfalar") or [])
    ]
    return render_template(
        "iplik_katalogu_detay.html", kartela=k, tedarikciler=_kartela_tedarikciler(),
    )


@app.route("/iplik-katalogu/<kartela_id>", methods=["POST"])
def iplik_katalog_kaydet(kartela_id: str):
    """Auto-save: JSON gövde al, upsert, {ok, kartela_id} döndür. Yeni için id='yeni' gelir."""
    body = request.get_json(force=True) or {}
    ad = (body.get("ad") or "").strip()
    if not ad:
        return jsonify({"ok": False, "error": "Kartela adı zorunlu"}), 400
    if kartela_id == "yeni":
        kartela_id = uuid.uuid4().hex
    body["kartela_id"] = kartela_id
    store.upsert_kartela(body)
    return jsonify({"ok": True, "kartela_id": kartela_id})


@app.route("/iplik-katalogu/<kartela_id>/sil", methods=["POST"])
def iplik_katalog_sil(kartela_id: str):
    store.delete_kartela(kartela_id)
    return redirect(url_for("iplik_katalog_list"))


# ---- İplik Kataloğu Parça 2-A — sayfa fotoğrafı yükleme / silme ----

def save_kartela_sayfa(file_storage, kartela_id: str, sayfa_id: str) -> str:
    """Sayfa fotoğrafını JPEG'e normalize edip kartelalar bucket'a yükle. Bucket-yolu döner.
    save_image() PIL pipeline'ının kartela-bucket varyantı (sabit path + bucket-not-found fallback)."""
    img = Image.open(file_storage.stream)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((2000, 2000))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    path = f"{kartela_id}/{sayfa_id}.jpg"
    try:
        store.upload_kartela(path, buf.getvalue(), "image/jpeg")
    except Exception as e:
        m = str(e).lower()
        if "bucket not found" in m or "404" in m or "not_found" in m:
            store.ensure_bucket_kartelalar()
            store.upload_kartela(path, buf.getvalue(), "image/jpeg")
        else:
            raise
    return path


@app.route("/iplik-katalogu/<kartela_id>/sayfa/yukle", methods=["POST"])
def iplik_katalog_sayfa_yukle(kartela_id: str):
    k = store.get_kartela(kartela_id)
    if not k:
        return jsonify({"ok": False, "error": "Kartela bulunamadı"}), 404
    fs = request.files.get("foto")
    if not fs or not fs.filename:
        return jsonify({"ok": False, "error": "Dosya yok"}), 400
    store.ensure_bucket_kartelalar()
    sayfa_id = uuid.uuid4().hex[:12]
    try:
        path = save_kartela_sayfa(fs, kartela_id, sayfa_id)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Sayfa yüklenemedi: {e}"}), 400
    sayfalar = k.get("sayfalar") or []
    sayfa = {"sayfa_id": sayfa_id, "sira": len(sayfalar) + 1, "foto_path": path, "renkler": []}
    sayfalar.append(sayfa)
    k["sayfalar"] = sayfalar
    store.upsert_kartela(k)
    return jsonify({"ok": True, "sayfa": sayfa, "public_url": store.public_url_kartela(path)})


@app.route("/iplik-katalogu/<kartela_id>/sayfa/<sayfa_id>/sil", methods=["POST"])
def iplik_katalog_sayfa_sil(kartela_id: str, sayfa_id: str):
    k = store.get_kartela(kartela_id)
    if not k:
        return jsonify({"ok": False, "error": "Kartela bulunamadı"}), 404
    sayfalar = k.get("sayfalar") or []
    hedef = next((s for s in sayfalar if s.get("sayfa_id") == sayfa_id), None)
    if not hedef:
        return jsonify({"ok": False, "error": "Sayfa bulunamadı"}), 404
    foto_path = hedef.get("foto_path")
    if foto_path:
        try:
            store.delete_kartelalar([foto_path])
        except Exception as e:
            print(f"[iplik_katalog_sayfa_sil] storage temizleme uyarısı: {e}")
    kalan = [s for s in sayfalar if s.get("sayfa_id") != sayfa_id]
    for i, s in enumerate(kalan):
        s["sira"] = i + 1
    k["sayfalar"] = kalan
    store.upsert_kartela(k)
    return jsonify({"ok": True})


@app.route("/iplik-katalogu/<kartela_id>/sayfa/<sayfa_id>/renkler", methods=["POST"])
def iplik_katalog_sayfa_renkler(kartela_id: str, sayfa_id: str):
    """İplik Kataloğu Parça 2-B — sayfanın renk listesini idempotent değiştir (ekle/sil/güncelle)."""
    k = store.get_kartela(kartela_id)
    if not k:
        return jsonify({"ok": False, "error": "Kartela bulunamadı"}), 404
    sayfalar = k.get("sayfalar") or []
    hedef = next((s for s in sayfalar if s.get("sayfa_id") == sayfa_id), None)
    if not hedef:
        return jsonify({"ok": False, "error": "Sayfa bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    renkler = body.get("renkler")
    if not isinstance(renkler, list):
        renkler = []
    for i, r in enumerate(renkler):
        if isinstance(r, dict):
            r["numara"] = i + 1   # server-side renumber güvencesi
    hedef["renkler"] = renkler
    k["sayfalar"] = sayfalar
    store.upsert_kartela(k)
    return jsonify({"ok": True, "renkler": renkler})


@app.route("/api/brands", methods=["GET"])
def api_brands_list():
    return jsonify({"ok": True, "brands": get_brands_registry()})


@app.route("/api/brands", methods=["POST"])
def api_brands_create():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Ad zorunlu"}), 400
    country = norm_country(body.get("country"))
    website = (body.get("website") or "").strip() or None
    brands = get_brands_registry()
    existing_slugs = {b.get("slug") for b in brands}
    new_slug = _unique_brand_slug(name, existing_slugs)
    ts = now_iso()
    new_brand = {
        "slug": new_slug, "name": name,
        "country": country, "website": website,
        "created_at": ts, "updated_at": ts,
    }
    brands.append(new_brand)
    save_brands_registry(brands)
    return jsonify({"ok": True, "brand": new_brand})


@app.route("/api/brands/<slug>", methods=["POST"])
def api_brands_update(slug: str):
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Ad zorunlu"}), 400
    country = norm_country(body.get("country"))
    website = (body.get("website") or "").strip() or None
    brands = get_brands_registry()
    match = next((b for b in brands if b.get("slug") == slug), None)
    if not match:
        return jsonify({"ok": False, "error": "Firma bulunamadı"}), 404
    match["name"] = name
    match["country"] = country
    match["website"] = website
    match["updated_at"] = now_iso()
    save_brands_registry(brands)
    return jsonify({"ok": True, "brand": match})


@app.route("/api/brands/<slug>", methods=["DELETE"])
def api_brands_delete(slug: str):
    brands = get_brands_registry()
    before = len(brands)
    brands = [b for b in brands if b.get("slug") != slug]
    if len(brands) == before:
        return jsonify({"ok": False, "error": "Firma bulunamadı"}), 404
    save_brands_registry(brands)
    return jsonify({"ok": True, "removed": True})


@app.route("/api/brands/reseed", methods=["POST"])
def api_brands_reseed():
    """Registry'yi sıfırla + TRACKED_BRANDS + ürün markalarından tekrar tara."""
    brands = seed_brands_registry()
    return jsonify({"ok": True, "count": len(brands)})


# ============================================================
# API
# ============================================================

def _normalize_brand_slug(brand: str, brand_slug: str | None = None) -> str:
    bs = clean(brand_slug) or brand_slugify(brand)
    return re.sub(r"[^a-z0-9_]", "_", bs.lower()) or "diger"


def _new_product_id(brand_slug: str, product_code: str, product_name: str):
    """(urun_id, folder_code, dest_prefix) üret. Çakışma varsa timestamp suffix."""
    code_slug = slugify(product_code or product_name)
    urun_id = f"{brand_slug}_{code_slug}"
    folder_code = code_slug
    if store.get(urun_id):
        suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        folder_code = f"{code_slug}-{suffix}"
        urun_id = f"{brand_slug}_{folder_code}"
    return urun_id, folder_code, f"{brand_slug}/{folder_code}"


def _copy_research_images(research_row: dict | None, prefill_paths, prefill_alts, dest_prefix, images):
    """Ön çalışma görsellerini ürün klasörüne kopyala (albüm+renk taşır).
    images listesine ekler; kullanılan albüm slug set'ini döner."""
    used_album_slugs: set[str] = set()
    by_path = {}
    if research_row:
        for im in (research_row.get("images") or []):
            if isinstance(im, dict) and im.get("storage_path"):
                by_path[im["storage_path"]] = im
    for i, src_path in enumerate(prefill_paths):
        if not src_path:
            continue
        try:
            data = store.download_image_bytes(src_path)
            dst_path = f"{dest_prefix}/{len(images)}_{uuid.uuid4().hex[:8]}.jpg"
            store.upload_image(dst_path, data, "image/jpeg")
            alt = prefill_alts[i].strip() if i < len(prefill_alts) and prefill_alts[i].strip() else None
            img_obj = {"path": dst_path, "variant_label": alt, "is_cover": False, "order": len(images)}
            r_im = by_path.get(src_path)
            if r_im:
                r_albums = [s for s in (r_im.get("albums") or []) if s]
                if r_albums:
                    img_obj["albums"] = sorted(set(r_albums))
                    used_album_slugs.update(r_albums)
                r_colors = r_im.get("colors") or {}
                if r_colors:
                    img_obj["colors"] = r_colors
            images.append(img_obj)
        except Exception as e:
            print(f"[Sprint 10.5] Prefill görsel kopyalanamadı ({src_path}): {e}")
    return used_album_slugs


def _assemble_and_save_product(*, urun_id, folder_code, fields: dict, images: list,
                               research_row=None, used_album_slugs=None,
                               pdfs_meta=None, from_research_id=None):
    """Ürün dict'ini kur + albüm tohumla + 'Renkler' garanti + upsert + research'i imported işaretle.
    fields: çözümlenmiş skaler değerler (brand, brand_slug, product_name, taksonomi, ülke, fiyat...).
    Hem /ekle (form) hem araştırma→ürün (JSON) bunu kullanır. urun_id döner."""
    used_album_slugs = used_album_slugs or set()
    if images:
        ci = fields.get("cover_index")
        ci = ci if isinstance(ci, int) and 0 <= ci < len(images) else 0
        images[ci]["is_cover"] = True

    brand_country = norm_country(fields.get("brand_country") or fields.get("country"))
    production_country = norm_country(fields.get("production_country"))
    ref_price = clean(fields.get("reference_price")) or None
    ref_price_type = fields.get("reference_price_type")
    if ref_price_type not in ("exact", "from"):
        ref_price_type = None
    if not ref_price:
        ref_price_type = None
    ref_price_evidence = clean(fields.get("reference_price_evidence")) if ref_price else None
    source_url = clean(fields.get("source_url"))

    now = now_iso()
    d = {
        "urun_id": urun_id, "brand": fields["brand"], "brand_slug": fields["brand_slug"],
        "country": brand_country, "brand_country": brand_country,
        "brand_country_code": _country_iso(brand_country),
        "production_country": production_country,
        "production_country_code": _country_iso(production_country),
        "reference_price": ref_price, "reference_price_type": ref_price_type,
        "reference_price_evidence": ref_price_evidence,
        "collection": clean(fields.get("collection")), "product_name": fields["product_name"],
        "product_code": clean(fields.get("product_code")) or folder_code,
        "composition": clean(fields.get("composition")), "width_cm": parse_int(fields.get("width_cm")),
        "weight_gsm": parse_int(fields.get("weight_gsm")),
        "weave_type": clean(fields.get("weave_type")),
        "repeat_vertical_cm": parse_int(fields.get("repeat_vertical_cm")),
        "repeat_horizontal_cm": parse_int(fields.get("repeat_horizontal_cm")),
        "arge_notu": clean(fields.get("arge_notu")), "notes": clean(fields.get("notes")),
        "source_url": source_url,
        "source_url_hash": store.url_hash(source_url) if source_url else None,
        "status": "active", "country_code": _country_iso(brand_country),
        "created_at": now, "updated_at": now, "images": images,
    }
    # Albüm tohumla (sadece kullanılan slug'lar) + "Renkler" garanti
    if research_row and used_album_slugs:
        d["albums"] = [
            a for a in (research_row.get("albums") or [])
            if isinstance(a, dict) and a.get("slug") in used_album_slugs
        ]
    existing_albums = d.get("albums") or []
    has_renkler = any(
        ((a.get("slug") or "").lower() == "renkler" or (a.get("name") or "").strip().lower() == "renkler")
        for a in existing_albums if isinstance(a, dict)
    )
    if not has_renkler:
        d["albums"] = existing_albums + [{"slug": "renkler", "name": "Renkler"}]
    if pdfs_meta:
        d["pdfs"] = pdfs_meta
    if from_research_id:
        d["from_research_id"] = from_research_id
    # Taksonomi (controlled vocab; geçersiz → temizlenir)
    d["category"] = store.validate_category(fields.get("category"))
    d["pattern"] = store.validate_pattern(fields.get("pattern"))
    d["color_family"] = store.validate_color_family(fields.get("color_family"))
    d["weave_tags"] = store.validate_enum_list(fields.get("weave_tags") or [], store.VALID_WEAVE_TAGS)
    st = fields.get("style_tags")
    if isinstance(st, str):
        st = st.split(",")
    d["style_tags"] = store.validate_str_list(st or [])
    d["color_count"] = parse_int(fields.get("color_count"))
    d["ai_notu"] = clean(fields.get("ai_notu"))
    store.upsert(d)

    if from_research_id:
        try:
            store.research_update_status(from_research_id, "imported", imported_product_id=urun_id)
        except Exception:
            pass  # best-effort, ürün yine de oluştu
    return urun_id


@app.route("/api/urun", methods=["POST"])
def api_create_urun():
    f = request.form
    brand = clean(f.get("brand"))
    product_name = clean(f.get("product_name"))
    if not brand:
        return jsonify({"ok": False, "error": "Marka zorunlu"}), 400
    if not product_name:
        return jsonify({"ok": False, "error": "Ürün adı zorunlu"}), 400

    brand_slug = _normalize_brand_slug(brand, f.get("brand_slug"))
    product_code = clean(f.get("product_code"))
    urun_id, folder_code, dest_prefix = _new_product_id(brand_slug, product_code, product_name)

    files = [x for x in request.files.getlist("files") if x and x.filename]
    labels = request.form.getlist("variant_labels")
    cover_index = parse_int(f.get("cover_index")) or 0

    images = []
    # Ön Çalışmadan gelen görseller (prefill) — albüm + renk taşır
    from_research_id = clean(f.get("from_research_id"))
    research_row = store.research_get(from_research_id) if from_research_id else None
    used_album_slugs = _copy_research_images(
        research_row, request.form.getlist("prefill_image_paths"),
        request.form.getlist("prefill_image_alts"), dest_prefix, images,
    )
    # Yeni upload'lar (file-input'tan)
    for i, fs in enumerate(files):
        try:
            path = save_image(fs, dest_prefix, len(images))
        except Exception as e:
            return jsonify({"ok": False, "error": f"Görsel yüklenemedi ({fs.filename}): {e}"}), 400
        label = labels[i].strip() if i < len(labels) and labels[i].strip() else None
        images.append({"path": path, "variant_label": label, "is_cover": False, "order": len(images)})

    # PDF dosyaları (opsiyonel)
    pdfs_meta: list[dict] = []
    for fs in [x for x in request.files.getlist("pdf_files") if x and x.filename]:
        try:
            pdfs_meta.append(save_pdf(fs, urun_id))
        except Exception as e:
            return jsonify({"ok": False, "error": f"PDF yüklenemedi ({fs.filename}): {e}"}), 400

    fields = {
        "brand": brand, "brand_slug": brand_slug, "product_name": product_name,
        "product_code": product_code, "collection": f.get("collection"),
        "composition": f.get("composition"), "width_cm": f.get("width_cm"),
        "weight_gsm": f.get("weight_gsm"), "weave_type": f.get("weave_type"),
        "repeat_vertical_cm": f.get("repeat_vertical_cm"),
        "repeat_horizontal_cm": f.get("repeat_horizontal_cm"),
        "arge_notu": f.get("arge_notu"), "notes": f.get("notes"),
        "source_url": f.get("source_url"),
        "brand_country": f.get("brand_country"), "country": f.get("country"),
        "production_country": f.get("production_country"),
        "reference_price": f.get("reference_price"),
        "reference_price_type": f.get("reference_price_type"),
        "reference_price_evidence": f.get("reference_price_evidence"),
        "category": f.get("category"), "pattern": f.get("pattern"),
        "color_family": f.get("color_family"),
        "weave_tags": f.getlist("weave_tags"), "style_tags": f.get("style_tags") or "",
        "color_count": f.get("color_count"), "ai_notu": f.get("ai_notu"),
        "cover_index": cover_index,
    }
    _assemble_and_save_product(
        urun_id=urun_id, folder_code=folder_code, fields=fields, images=images,
        research_row=research_row, used_album_slugs=used_album_slugs,
        pdfs_meta=pdfs_meta, from_research_id=from_research_id,
    )
    return jsonify({"ok": True, "urun_id": urun_id, "redirect": url_for("urun_detail", urun_id=urun_id)})


# v4.0-part-2 Sprint 11 — Gemini destekli "Linkten Doldur"
# Bir kumaş ürün linkinden form alanları için ÖNERİ üretir.
# Form'a hiçbir şey otomatik yazılmaz; UI önerileri gösterir,
# kullanıcı tek tek veya toplu "Kabul" ile form'a basar.
# Anayasa kural #2/#3/#8 uyumu: SADECE sayfada açıkça yazan
# bilgiler döndürülür; her alan için sayfadan alıntı (evidence) zorunludur.
@app.route("/api/urun/linkten-doldur", methods=["POST"])
def api_urun_linkten_doldur():
    if not _GEMINI_AVAILABLE:
        return jsonify({
            "ok": False,
            "error": "gemini_module_missing",
            "message": "gemini_extract modülü yüklenemedi (google-generativeai kurulu mu?)",
        }), 503

    if not os.environ.get("GEMINI_API_KEY"):
        return jsonify({
            "ok": False,
            "error": "no_api_key",
            "message": "GEMINI_API_KEY tanımsız — endpoint pasif",
        }), 503

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"ok": False, "error": "missing_url", "message": "url zorunlu"}), 400
    if not url.startswith(("http://", "https://")):
        return jsonify({
            "ok": False, "error": "bad_url",
            "message": "url http:// veya https:// ile başlamalı",
        }), 400

    # v4.0-part-2 Sprint 11.7 — Model override (UI dropdown'dan); whitelist modül seviyesinde (tek kaynak).
    requested_model = (data.get("model") or "").strip() or None
    model_override = requested_model if requested_model in GEMINI_MODEL_WHITELIST else None

    # Tek-çağrı sarmalayıcı: fetch + extract.
    # Başarısızlık koşullarını `linkten_doldur` ok=False olarak döndürür.
    try:
        result = gx.linkten_doldur(url, model=model_override)
    except Exception as e:
        return jsonify({
            "ok": False, "error": "unexpected",
            "message": f"Beklenmeyen hata: {e}",
        }), 500

    if not result.get("ok"):
        # fetch / extract hatası — kullanıcıya 200 ile bilgi mesajı dön
        # (UI hata kartını gösterir, form girişi engellenmez)
        return jsonify({
            "ok": False,
            "stage": result.get("stage"),
            "error": result.get("error"),
            "message": result.get("message") or "Bilinmeyen hata",
            "model": result.get("model_used") or gx.MODEL_NAME,
            "requested_model": requested_model,
            "model_invalid": bool(requested_model and not model_override),
        }), 200

    return jsonify({
        "ok": True,
        "suggestions": result.get("suggestions") or {},
        "title": result.get("title") or "",
        "truncated": bool(result.get("truncated")),
        "model": result.get("model_used") or gx.MODEL_NAME,
        "requested_model": requested_model,
        "model_invalid": bool(requested_model and not model_override),
    }), 200


@app.route("/api/urun/<urun_id>/meta", methods=["POST"])
def api_update_meta(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    data = request.get_json(force=True)
    # v4.0-part-2 Adım 7: collection + product_code UI'dan kaldırıldı —
    # whitelist'te yok artık (eski jsonb verisi DB'de kalır, sadece düzenlenmez).
    for key in ("brand", "product_name",
                "composition", "weave_type", "arge_notu", "notes", "source_url"):
        if key in data:
            d[key] = clean(data[key])
    # v4.0-part-2 Sprint 11.5 — country = brand_country alias (geriye uyum)
    if "country" in data or "brand_country" in data:
        bc_raw = clean(data.get("brand_country") or data.get("country"))
        bc = norm_country(bc_raw)
        d["country"] = bc
        d["brand_country"] = bc
        d["brand_country_code"] = _country_iso(bc)
    if "production_country" in data:
        pc = norm_country(clean(data["production_country"]))
        d["production_country"] = pc
        d["production_country_code"] = _country_iso(pc)
    if "reference_price" in data:
        rp = clean(data["reference_price"]) or None
        rpt = clean(data.get("reference_price_type"))
        if rpt not in ("exact", "from"):
            rpt = None
        if not rp:
            rpt = None
        d["reference_price"] = rp
        d["reference_price_type"] = rpt
        d["reference_price_evidence"] = clean(data.get("reference_price_evidence")) if rp else None
    for key in ("width_cm", "weight_gsm", "repeat_vertical_cm", "repeat_horizontal_cm"):
        if key in data:
            d[key] = parse_int(data[key])
    # OnCalisma-V2 (Problem 2) — taksonomi (JSON gövde; listeler dizi gelir)
    if "category" in data:
        d["category"] = store.validate_category(data["category"])
    if "pattern" in data:
        d["pattern"] = store.validate_pattern(data["pattern"])
    if "color_family" in data:
        d["color_family"] = store.validate_color_family(data["color_family"])
    if "weave_tags" in data:
        d["weave_tags"] = store.validate_enum_list(data.get("weave_tags") or [], store.VALID_WEAVE_TAGS)
    if "style_tags" in data:
        d["style_tags"] = store.validate_str_list(data.get("style_tags") or [])
    # OnCalisma-V2 (Problem 4b) — renk sayısı + AI notu
    if "color_count" in data:
        d["color_count"] = parse_int(data["color_count"])
    if "ai_notu" in data:
        d["ai_notu"] = clean(data["ai_notu"])
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True})


@app.route("/api/urun/<urun_id>/gorsel-ekle", methods=["POST"])
def api_add_images(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    images = d.get("images") or []
    max_order = max((im.get("order", 0) for im in images), default=-1)
    prefix = infer_prefix(d)
    files = [x for x in request.files.getlist("files") if x and x.filename]
    labels = request.form.getlist("variant_labels")
    added = 0
    for i, fs in enumerate(files):
        order = max_order + 1 + i
        try:
            path = save_image(fs, prefix, order)
        except Exception as e:
            return jsonify({"ok": False, "error": f"Görsel yüklenemedi ({fs.filename}): {e}"}), 400
        label = labels[i].strip() if i < len(labels) and labels[i].strip() else None
        images.append({"path": path, "variant_label": label, "is_cover": False, "order": order})
        added += 1
    if images and not any(im.get("is_cover") for im in images):
        images[0]["is_cover"] = True
    d["images"] = images
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True, "added": added})


@app.route("/api/urun/<urun_id>/sirala", methods=["POST"])
def api_reorder(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    order_list = (request.get_json(force=True) or {}).get("order") or []
    pos = {p: i for i, p in enumerate(order_list)}
    images = d.get("images") or []
    images.sort(key=lambda im: pos.get(im.get("path"), len(order_list)))
    for i, im in enumerate(images):
        im["order"] = i
    d["images"] = images
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True})


@app.route("/api/urun/<urun_id>/gorsel-etiket", methods=["POST"])
def api_set_label(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    data = request.get_json(force=True) or {}
    target = data.get("path")
    found = False
    for im in d.get("images") or []:
        if im.get("path") == target:
            im["variant_label"] = clean(data.get("variant_label"))
            found = True
            break
    if not found:
        return jsonify({"ok": False, "error": "Görsel bulunamadı"}), 400
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True})


@app.route("/api/urun/<urun_id>/sabitle", methods=["POST"])
def api_set_pin(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    data = request.get_json(force=True) or {}
    target = data.get("path")
    pin = bool(data.get("pin"))
    found = False
    for im in d.get("images") or []:
        if im.get("path") == target:
            im["is_pinned"] = pin
            found = True
            break
    if not found:
        return jsonify({"ok": False, "error": "Görsel bulunamadı"}), 400
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True})


@app.route("/api/urun/<urun_id>/kapak", methods=["POST"])
def api_set_cover(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    target = (request.get_json(force=True) or {}).get("path")
    found = False
    for im in d.get("images") or []:
        im["is_cover"] = (im.get("path") == target)
        if im.get("path") == target:
            found = True
    if not found:
        return jsonify({"ok": False, "error": "Görsel bulunamadı"}), 400
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True})


# v4.0-part-2 Sprint 14 — Görsel favorileme
@app.route("/api/urun/<urun_id>/favori-toggle", methods=["POST"])
def api_favori_toggle(urun_id: str):
    """Body: {path} — görselin is_favorite flag'ini toggle eder."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    target = (request.get_json(silent=True) or {}).get("path", "")
    for im in (d.get("images") or []):
        if im.get("path") == target:
            im["is_favorite"] = not im.get("is_favorite", False)
            d["updated_at"] = now_iso()
            store.upsert(d)
            fav_count = sum(1 for x in (d.get("images") or []) if x.get("is_favorite"))
            return jsonify({"ok": True, "is_favorite": im["is_favorite"],
                            "favorite_count": fav_count})
    return jsonify({"ok": False, "error": "Görsel bulunamadı"}), 400


# ============================================================
# tasarim-v2 Plan Parça 1 — Kur altyapısı + Plan kaydı
# ============================================================

KUR_CACHE_KEY = "kur_tcmb_daily"
TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"


@app.route("/api/kur", methods=["GET"])
def api_kur():
    """TCMB günlük kuru (USD/EUR ForexSelling). app_state'te günlük cache.
    Hata → son cache (stale) veya null; ASLA 500 (frontend manuel kura düşer)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cached = store.get_app_state(KUR_CACHE_KEY) or {}
    # Aynı gün + dolu değer → cache döndür (TCMB hafta sonu güncellenmez, son değer geçerli)
    if cached.get("date") == today and cached.get("usd_try") and cached.get("eur_try"):
        return jsonify({"ok": True, "cached": True, **cached})
    try:
        resp = requests.get(TCMB_URL, timeout=8)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        def _rate(code):
            node = root.find(f".//Currency[@Kod='{code}']")
            if node is None:
                return None
            raw = (node.findtext("ForexSelling") or node.findtext("BanknoteSelling") or "").strip()
            raw = raw.replace(",", ".")
            return float(raw) if raw else None

        usd, eur = _rate("USD"), _rate("EUR")
        if usd is None and eur is None:
            raise ValueError("TCMB XML'inde USD/EUR bulunamadı")
        result = {"usd_try": usd, "eur_try": eur, "fetched_at": now_iso(), "date": today}
        store.set_app_state(KUR_CACHE_KEY, result)
        return jsonify({"ok": True, "cached": False, **result})
    except Exception:
        # Erişilemezse son cache'i (stale) ver; o da yoksa null — 500 ATMA
        if cached:
            return jsonify({"ok": True, "cached": True, "stale": True, **cached})
        return jsonify({"ok": False, "error": "TCMB erişilemedi",
                        "usd_try": None, "eur_try": None, "fetched_at": None})


@app.route("/api/urun/<urun_id>/plan", methods=["POST"])
def api_plan_update(urun_id: str):
    """Body: {surum_id, plan:{...}} — aktif teknik sürümün plan dilimini yazar.
    plan kolonu surum_id ile anahtarlı sözlük; yalnız ilgili dilim güncellenir."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    surum_id = body.get("surum_id")
    plan_data = body.get("plan")
    if not surum_id or not isinstance(plan_data, dict):
        return jsonify({"ok": False, "error": "surum_id ve plan zorunlu"}), 400
    plan_map = d.get("plan")
    if not isinstance(plan_map, dict):
        plan_map = {}
    plan_data["surum_id"] = surum_id
    plan_data["guncelleme_tarihi"] = now_iso()
    plan_map[surum_id] = plan_data
    d["plan"] = plan_map
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True, "plan": plan_data})


@app.route("/api/urun/<urun_id>/gorsel-sil", methods=["POST"])
def api_delete_image(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    target = (request.get_json(force=True) or {}).get("path")
    images = d.get("images") or []
    match = next((im for im in images if im.get("path") == target), None)
    if not match:
        return jsonify({"ok": False, "error": "Görsel bulunamadı"}), 400
    was_cover = match.get("is_cover")
    store.delete_images([target])
    images = [im for im in images if im.get("path") != target]
    if was_cover and images:
        images[0]["is_cover"] = True
    for i, im in enumerate(images):
        im["order"] = i
    d["images"] = images
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True, "remaining": len(images)})


def _is_mobile_ua(req) -> bool:
    """Basit UA kontrol — telefon mu? (tablet false döner)."""
    ua = (req.headers.get("User-Agent") or "").lower()
    if "ipad" in ua or "tablet" in ua:
        return False
    return any(k in ua for k in ("iphone", "android", "mobile", "windows phone"))


def _delete_product_atomic(uid: str) -> bool:
    """Bir ürünü ve tüm görsellerini + PDF'lerini atomik olarak siler. Yoksa False döner."""
    d = store.get(uid)
    if not d:
        return False
    paths = [im.get("path") for im in (d.get("images") or []) if im.get("path")]
    if paths:
        store.delete_images(paths)
    # v4.0-part-2 Adım 7: PDF cascade
    pdf_paths = [p.get("path") for p in (d.get("pdfs") or []) if p.get("path")]
    if pdf_paths:
        store.delete_pdfs(pdf_paths)
    store.delete(uid)
    return True


# v4.0-part-2 Sprint 12 — Çoklu atkı + çoklu çözgü renk atama
# Veri modeli: colors.weft = [{hex,...}, ...] (array), colors.warp = [...] (array),
# colors.mix = {hex,...} (tek obje). Mevcut görsellerin eski formatı (weft = {hex})
# bu helper ile şeffaf şekilde array'e normalize edilir.
def _normalize_role_colors(colors) -> dict:
    """Eski {weft: {hex...}} → {weft: [{hex...}]} normalize. mix tek obje kalır.
    Hem read path'lerinde hem API yazımında kullanılır."""
    if not isinstance(colors, dict):
        return {}
    out: dict = {}
    for role in ("weft", "warp"):
        v = colors.get(role)
        if v is None or v == {} or v == []:
            continue
        if isinstance(v, list):
            cleaned = [c for c in v if isinstance(c, dict) and c.get("hex")]
            if cleaned:
                out[role] = cleaned
        elif isinstance(v, dict) and v.get("hex"):
            out[role] = [v]   # eski tek-renk → array'e wrap
    mix = colors.get("mix")
    if isinstance(mix, dict) and mix.get("hex"):
        out["mix"] = mix
    return out


def _derive_color_palette(images: list[dict]) -> list[dict]:
    """images[i].colors -> dedup hex palette, açıktan koyuya (LAB L desc).
    v4.0-part-2 Sprint 12: weft/warp array iterasyonu (geriye uyumlu)."""
    items = []
    for im in images:
        colors = _normalize_role_colors(im.get("colors") or {})
        # Atkı + çözgü: array içinden her renk
        for role in ("weft", "warp"):
            for c in colors.get(role, []):
                if not c.get("hex"):
                    continue
                items.append({
                    "hex": c["hex"].upper(),
                    "name": c.get("name") or c.get("nearest") or "—",
                    "lab": c.get("lab") or [50, 0, 0],
                    "role": role,
                    "image_path": im.get("path") or im.get("storage_path"),  # research_pool fallback
                })
        # Mix: tek obje (varsa)
        mix = colors.get("mix")
        if mix and mix.get("hex"):
            items.append({
                "hex": mix["hex"].upper(),
                "name": mix.get("name") or mix.get("nearest") or "—",
                "lab": mix.get("lab") or [50, 0, 0],
                "role": "mix",
                "image_path": im.get("path") or im.get("storage_path"),  # research_pool fallback
            })
    by_hex: dict[str, list[dict]] = {}
    for it in items:
        by_hex.setdefault(it["hex"], []).append(it)
    palette = []
    for hex_, srcs in by_hex.items():
        s0 = srcs[0]
        palette.append({
            "hex": hex_,
            "name": s0["name"],
            "lab": s0["lab"],
            "roles": sorted({s["role"] for s in srcs}),
            "image_paths": sorted({s["image_path"] for s in srcs if s.get("image_path")}),
            "count": len(srcs),
        })
    # Açıktan koyuya — LAB L değeri azalan
    palette.sort(key=lambda p: -(p["lab"][0] if isinstance(p.get("lab"), list) and p["lab"] else 0))
    return palette


@app.route("/api/urun/<urun_id>/sil", methods=["POST"])
def api_delete_product(urun_id: str):
    if not _delete_product_atomic(urun_id):
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    return jsonify({"ok": True})


@app.route("/api/urun/toplu-sil", methods=["POST"])
def api_bulk_delete():
    """Toplu ürün silme. Body: {urun_ids: [str]}. Bulunmayanlar sessiz atlanır."""
    body = request.get_json(silent=True) or {}
    ids = body.get("urun_ids") or []
    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
        return jsonify({"ok": False, "error": "urun_ids string listesi olmalı"}), 400
    deleted = [uid for uid in ids if _delete_product_atomic(uid)]
    return jsonify({"ok": True, "deleted": deleted, "count": len(deleted)})


# ============================================================
# Teknik çalışma (multi-sürüm) — v3.8 Faz 1
# ============================================================

def _next_surum_id(existing_ids: list[str]) -> str:
    """v1, v2, v3 ... şeklinde benzersiz id üret."""
    nums = []
    for sid in existing_ids:
        m = re.match(r"^v(\d+)$", sid or "")
        if m:
            nums.append(int(m.group(1)))
    next_n = (max(nums) + 1) if nums else 1
    return f"v{next_n}"


def _ensure_teknik(d: dict) -> dict:
    t = d.get("teknik")
    if not isinstance(t, dict):
        t = {}
    t.setdefault("active_surum_id", None)
    t.setdefault("surumler", [])
    d["teknik"] = t
    return t


def _find_surum(teknik: dict, surum_id: str) -> dict | None:
    for s in (teknik.get("surumler") or []):
        if s.get("id") == surum_id:
            return s
    return None


@app.route("/api/urun/<urun_id>/teknik/surum", methods=["POST"])
def api_teknik_surum_create(urun_id: str):
    """Yeni teknik sürüm oluştur.
    Body: {ad, source_surum_id?}

    v4.0-part-2 Adım 8 — Eğer source_surum_id verilirse, o sürümdeki
    1·Analiz (kunye + parametreler + iplikler) + 2·Desen (desen) tablar
    KOPYALANIR. 3·Tarak (tahar_grid, tarak_raporu, tarak) ve notlar her
    zaman BOŞ başlar.
    """
    import copy
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    ad = clean(body.get("ad")) or "Yeni Sürüm"
    source_id = clean(body.get("source_surum_id"))

    teknik = _ensure_teknik(d)
    new_id = _next_surum_id([s.get("id") for s in teknik["surumler"]])
    now = now_iso()

    source = _find_surum(teknik, source_id) if source_id else None
    if source:
        # Miras alma: Analiz + Desen kopyalanır, Tarak + notlar boş.
        kunye_copy = copy.deepcopy(source.get("kunye") or {})
        # Tarih taze: yeni çalışma bugün başlıyor
        kunye_copy["tarih"] = now[:10]
        surum = {
            "id": new_id,
            "ad": ad,
            "olusturma_tarihi": now,
            "guncelleme_tarihi": now,
            "kunye": kunye_copy,
            "parametreler": copy.deepcopy(source.get("parametreler") or {}),
            "iplikler": copy.deepcopy(source.get("iplikler") or {"cozgu": [], "atki": []}),
            "desen": copy.deepcopy(source.get("desen") or {}),
            # 3·Tarak boş başlar
            "tahar_grid": {},
            "tarak_raporu": {},
            "tarak": {},
            # Notlar boş başlar (sürüm-spesifik)
            "notlar": "",
            "notlar_html": "",
            # Mirastan geldiği info (audit + UI badge için)
            "inherited_from": source_id,
        }
    else:
        surum = {
            "id": new_id,
            "ad": ad,
            "olusturma_tarihi": now,
            "guncelleme_tarihi": now,
            "kunye": {
                # v4.0-part-2 Adım 2.4 — ürün metadata'sından auto-fill
                "ad": d.get("product_code") or d.get("product_name") or "",
                "musteri": d.get("brand") or "",
                "tarih": now[:10],   # YYYY-MM-DD (ISO)
            },
            "parametreler": {
                "cozgu_sikligi": None,
                "atki_sikligi": None,
                "ham_en_cm": None,
                "mamul_en_cm": d.get("width_cm"),     # mevcut metadata'dan default
                "gramaj_gsm": d.get("weight_gsm"),
                # v4.0-part-2 Adım 2.5 — üretim & finisaj parametreleri default'ları
                "tezgah_devri": 280,
                "randiman": 85,
                "terbiye_fiyat": 1,
                "genel_fire": 5,
                "kursun_sabit": 0.25,
                "ek_malzeme": None,
            },
            "iplikler": {"cozgu": [], "atki": []},
            "tahar_grid": {},
            "tarak_raporu": {},
            # v4.0-part-2 Adım 3 — Desen modülü (tahar+armür+iro+döngü+rapor)
            "desen": {},
            # v4.0-part-2 Adım 4 — Tarak modülü (sıklık+rapor+dentThreads)
            "tarak": {},
            "notlar": "",
            "notlar_html": "",
        }
    teknik["surumler"].append(surum)
    # İlk sürüm otomatik aktif (veya miras alındıysa onu da aktif yap — kullanıcı yeniyi düzenleyecek)
    teknik["active_surum_id"] = new_id
    d["updated_at"] = now
    store.upsert(d)
    return jsonify({"ok": True, "surum": surum, "active_surum_id": teknik["active_surum_id"]})


@app.route("/api/urun/<urun_id>/teknik/<surum_id>", methods=["POST"])
def api_teknik_surum_update(urun_id: str, surum_id: str):
    """Sürüm verisini güncelle. Body: {parametreler?, iplikler?, tahar_grid?, tarak_raporu?, notlar?}."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    teknik = _ensure_teknik(d)
    surum = _find_surum(teknik, surum_id)
    if not surum:
        return jsonify({"ok": False, "error": "Sürüm bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    # Künye (Numune Master — ad/müşteri/tarih)
    if "kunye" in body and isinstance(body["kunye"], dict):
        cur_kunye = surum.get("kunye") or {}
        for key in ("ad", "musteri", "tarih"):
            if key in body["kunye"]:
                v = body["kunye"][key]
                cur_kunye[key] = clean(v) if isinstance(v, str) else ""
        surum["kunye"] = cur_kunye
    # Parametreler
    if "parametreler" in body and isinstance(body["parametreler"], dict):
        cur_param = surum.get("parametreler") or {}
        # v4.0-part-2 Adım 2.4 — üretim & finisaj parametreleri eklendi
        for key in ("cozgu_sikligi", "atki_sikligi", "ham_en_cm", "mamul_en_cm", "gramaj_gsm",
                    "tezgah_devri", "randiman", "terbiye_fiyat", "genel_fire",
                    "kursun_sabit", "ek_malzeme"):
            if key in body["parametreler"]:
                v = body["parametreler"][key]
                if v is None or v == "":
                    cur_param[key] = None
                else:
                    try:
                        cur_param[key] = float(str(v).replace(",", "."))
                    except (TypeError, ValueError):
                        cur_param[key] = None
        surum["parametreler"] = cur_param
    # İplikler (max 8 per yön)
    if "iplikler" in body and isinstance(body["iplikler"], dict):
        cur_ipl = surum.get("iplikler") or {"cozgu": [], "atki": []}
        for yon in ("cozgu", "atki"):
            if yon in body["iplikler"]:
                lst = body["iplikler"][yon]
                if isinstance(lst, list):
                    cur_ipl[yon] = lst[:8]
        surum["iplikler"] = cur_ipl
    # Tahar grid + tarak raporu + desen + tarak (jsonb passthrough)
    for k in ("tahar_grid", "tarak_raporu", "desen", "tarak"):
        if k in body:
            surum[k] = body[k] if isinstance(body[k], (dict, list)) else {}
    # Notlar
    if "notlar" in body:
        surum["notlar"] = clean(body["notlar"]) or ""
    surum["guncelleme_tarihi"] = now_iso()
    d["updated_at"] = surum["guncelleme_tarihi"]
    store.upsert(d)
    return jsonify({"ok": True, "surum": surum})


@app.route("/api/urun/<urun_id>/teknik/<surum_id>/ad", methods=["POST"])
def api_teknik_surum_rename(urun_id: str, surum_id: str):
    """Sürüm yeniden adlandır. Body: {yeni_ad}."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    teknik = _ensure_teknik(d)
    surum = _find_surum(teknik, surum_id)
    if not surum:
        return jsonify({"ok": False, "error": "Sürüm bulunamadı"}), 404
    yeni_ad = clean((request.get_json(force=True) or {}).get("yeni_ad"))
    if not yeni_ad:
        return jsonify({"ok": False, "error": "yeni_ad zorunlu"}), 400
    surum["ad"] = yeni_ad
    surum["guncelleme_tarihi"] = now_iso()
    d["updated_at"] = surum["guncelleme_tarihi"]
    store.upsert(d)
    return jsonify({"ok": True, "ad": yeni_ad})


@app.route("/api/urun/<urun_id>/teknik/<surum_id>", methods=["DELETE"])
def api_teknik_surum_delete(urun_id: str, surum_id: str):
    """Sürümü sil. Aktifse ilk sürüme geç."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    teknik = _ensure_teknik(d)
    before = len(teknik["surumler"])
    teknik["surumler"] = [s for s in teknik["surumler"] if s.get("id") != surum_id]
    if len(teknik["surumler"]) == before:
        return jsonify({"ok": False, "error": "Sürüm bulunamadı"}), 404
    # Aktif kontrolü
    if teknik.get("active_surum_id") == surum_id:
        teknik["active_surum_id"] = (teknik["surumler"][0]["id"] if teknik["surumler"] else None)
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True, "active_surum_id": teknik["active_surum_id"]})


@app.route("/api/urun/<urun_id>/teknik/aktif", methods=["POST"])
def api_teknik_set_active(urun_id: str):
    """Aktif sürümü değiştir. Body: {surum_id}."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    teknik = _ensure_teknik(d)
    surum_id = (request.get_json(force=True) or {}).get("surum_id")
    if not _find_surum(teknik, surum_id):
        return jsonify({"ok": False, "error": "Sürüm bulunamadı"}), 404
    teknik["active_surum_id"] = surum_id
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True, "active_surum_id": surum_id})


# ============================================================
# v4.0-part-2 Adım 5 Faz 1 — Teknik PDF (client-side print)
# ============================================================

def _num_or_none(v):
    """Güvenli sayısal parse. Boş/geçersizse None."""
    if v is None or v == "":
        return None
    try:
        n = float(str(v).replace(",", "."))
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def _parse_iplik(raw, tip):
    """JS parseIplikValue port — kat tip-aware.
    * / × / x → her zaman kat. / → NM/NE'de kat, DENYE/DTEX'te filament (kat=1).
    """
    if raw is None or raw == "":
        return {"value": None, "kat": 1}
    s = str(raw).strip()
    m = re.match(r"^\s*([0-9]+(?:[.,][0-9]+)?)\s*[\*xX×]\s*([0-9]+)\s*$", s)
    if m:
        val = float(m.group(1).replace(",", "."))
        kat = int(m.group(2)) or 1
        return {"value": val if math.isfinite(val) else None, "kat": kat}
    m = re.match(r"^\s*([0-9]+(?:[.,][0-9]+)?)\s*\/\s*([0-9]+)\s*$", s)
    if m:
        val = float(m.group(1).replace(",", "."))
        kat = int(m.group(2)) or 1
        if tip in ("NM", "NE"):
            return {"value": val if math.isfinite(val) else None, "kat": kat}
        return {"value": val if math.isfinite(val) else None, "kat": 1}
    try:
        n = float(s.replace(",", "."))
        return {"value": n if math.isfinite(n) else None, "kat": 1}
    except (ValueError, TypeError):
        return {"value": None, "kat": 1}


def _nm_eq(tip, val):
    """JS nmEquivalent port — DENYE/DTEX/NM/NE → m/g."""
    if val is None or val <= 0:
        return None
    if tip == "DENYE":
        return 9000 / val
    if tip == "DTEX":
        return 10000 / val
    if tip == "NM":
        return val
    if tip == "NE":
        return val * 1.693
    return None


def _g_per_mt_row(row):
    """Bir iplik satırı için g/m (kat dahil) — tek tel ağırlığı."""
    tip = row.get("tip", "DENYE")
    parsed = _parse_iplik(row.get("iplik"), tip)
    nm = _nm_eq(tip, parsed["value"])
    if nm is None or nm <= 0:
        return None, parsed
    return parsed["kat"] / nm, parsed


def _calc_teknik_summary(surum):
    """Sürümün tüm hesaplanan değerlerini döner — JS calc karşılığı."""
    params = surum.get("parametreler") or {}
    iplikler = surum.get("iplikler") or {}
    cozgu = iplikler.get("cozgu") or []
    atki = iplikler.get("atki") or []

    ham_en = _num_or_none(params.get("ham_en_cm"))
    mamul_en = _num_or_none(params.get("mamul_en_cm"))
    atki_sikligi = _num_or_none(params.get("atki_sikligi"))

    # Çözgü/Atkı satırları için chip değerleri (g/mt, $/mt)
    def satir_summary(r, yon):
        g, parsed = _g_per_mt_row(r)
        f = _num_or_none(r.get("fiyat"))
        s = _num_or_none(r.get("siklik"))
        g_mt = None
        if g and s and ham_en and ham_en > 0:
            g_mt = s * ham_en * g if yon == "cozgu" else s * (ham_en / 100) * g
        d_mt = (g_mt * f) / 1000 if g_mt is not None and f and f > 0 else None
        return {
            "tip": r.get("tip", "DENYE"),
            "iplik": r.get("iplik", ""),
            "kat": parsed["kat"],
            "siklik": s,
            "fiyat": f,
            "g_per_mt": g_mt,
            "dollar_per_mt": d_mt,
            "icerikler": ((r.get("olcum") or {}).get("icerikler")) or [],
            "bilgi": r.get("bilgi") or {},
            "renk_ad": r.get("renk_ad", ""),
            "renk_hex": r.get("renk_hex", ""),
        }

    cozgu_s = [satir_summary(r, "cozgu") for r in cozgu]
    atki_s = [satir_summary(r, "atki") for r in atki]

    cozgu_g_mt = sum(s["g_per_mt"] for s in cozgu_s if s["g_per_mt"])
    atki_g_mt = sum(s["g_per_mt"] for s in atki_s if s["g_per_mt"])
    toplam_g_mt = cozgu_g_mt + atki_g_mt

    cekme = {"factor": 1.0, "pct": 0.0}
    if ham_en and mamul_en and ham_en > 0 and mamul_en > 0:
        cekme = {"factor": ham_en / mamul_en, "pct": ((ham_en - mamul_en) / ham_en) * 100}

    iplik_cozgu = sum(s["dollar_per_mt"] for s in cozgu_s if s["dollar_per_mt"])
    iplik_atki = sum(s["dollar_per_mt"] for s in atki_s if s["dollar_per_mt"])
    iplik_total = iplik_cozgu + iplik_atki

    # Kapasite
    rpm = _num_or_none(params.get("tezgah_devri"))
    randiman = _num_or_none(params.get("randiman"))
    kapasite_mt_saat = None
    kapasite_mt_ay = None
    if rpm and randiman and atki_sikligi and rpm > 0 and randiman > 0 and atki_sikligi > 0:
        mt_dk = (rpm * (randiman / 100)) / (atki_sikligi * 100)
        kapasite_mt_saat = mt_dk * 60
        kapasite_mt_ay = kapasite_mt_saat * 24 * 30

    # İşçilik (saat ücreti 30 $/saat sabit varsayım + 1.18 KDV)
    iscilik = (30 / kapasite_mt_saat) * 1.18 if kapasite_mt_saat and kapasite_mt_saat > 0 else 0

    # Terbiye
    terbiye_fiyat = _num_or_none(params.get("terbiye_fiyat")) or 0
    terbiye = (toplam_g_mt / 1000) * terbiye_fiyat if toplam_g_mt > 0 else 0

    # Fire
    fire_pct = _num_or_none(params.get("genel_fire")) or 0
    fire = (iplik_total + iscilik + terbiye) * (fire_pct / 100) if fire_pct > 0 else 0

    # Kurşum
    kursun = (_num_or_none(params.get("kursun_sabit")) or 0) + (_num_or_none(params.get("ek_malzeme")) or 0)

    maliyet_total = iplik_total + iscilik + terbiye + fire + kursun

    # Kumaş içeriği — elyaf bazlı g/mt dağılımı
    icerikler_map = {}
    def add_satir_icerigi(rows, satir_sums):
        for r, s_dat in zip(rows, satir_sums):
            g_contrib = s_dat["g_per_mt"]
            if not g_contrib or g_contrib <= 0:
                continue
            ics = ((r.get("olcum") or {}).get("icerikler")) or []
            if not ics:
                icerikler_map["Belirsiz"] = icerikler_map.get("Belirsiz", 0) + g_contrib
                continue
            for it in ics:
                if not it or not it.get("elyaf"):
                    continue
                oran = _num_or_none(it.get("oran_yuzde"))
                if not oran or oran <= 0:
                    continue
                key = it["elyaf"].strip().upper()
                icerikler_map[key] = icerikler_map.get(key, 0) + g_contrib * (oran / 100)
    add_satir_icerigi(cozgu, cozgu_s)
    add_satir_icerigi(atki, atki_s)
    icerikler = sorted(
        ({"name": k, "gram_per_mt": v, "percent": (v / toplam_g_mt * 100) if toplam_g_mt > 0 else 0}
         for k, v in icerikler_map.items()),
        key=lambda x: -x["percent"]
    )

    return {
        "ham_en": ham_en, "mamul_en": mamul_en, "atki_sikligi": atki_sikligi,
        "cozgu_g_mt": cozgu_g_mt, "atki_g_mt": atki_g_mt, "toplam_g_mt": toplam_g_mt,
        "cekme": cekme,
        "iplik_cozgu": iplik_cozgu, "iplik_atki": iplik_atki, "iplik_total": iplik_total,
        "iscilik": iscilik, "terbiye": terbiye, "fire": fire, "kursun": kursun,
        "maliyet_total": maliyet_total,
        "kapasite_mt_saat": kapasite_mt_saat, "kapasite_mt_ay": kapasite_mt_ay,
        "kumas_icerigi": icerikler,
        "cozgu_satir": cozgu_s, "atki_satir": atki_s,
        "params": params,
    }


def _desen_compute(desen):
    """JS computeDesen + expandPicks port — print için sadece okuma."""
    if not desen or not isinstance(desen, dict):
        return None
    tahar = desen.get("tahar") or []
    armur = desen.get("armur") or []
    weft = desen.get("weftCount") or 0
    warp = desen.get("warpCount") or 0
    if weft <= 0 or warp <= 0:
        return None
    matrix = []
    for w in range(warp):
        f = tahar[w] if w < len(tahar) else None
        src = armur[f] if (f is not None and 0 <= f < len(armur)) else None
        row = [bool(src[p]) if (src and p < len(src)) else False for p in range(weft)]
        matrix.append(row)
    loops = desen.get("loops") or []
    start_map = {l.get("startPick"): l for l in loops if "startPick" in l}
    expanded = []
    p = 0
    while p < weft:
        loop = start_map.get(p)
        if loop:
            for _ in range(loop.get("count", 2)):
                for q in range(loop.get("startPick", p) + 1, loop.get("endPick", p)):
                    expanded.append(q)
            p = loop.get("endPick", p) + 1
        else:
            expanded.append(p)
            p += 1
    # Marker map (DO/NEXT işaretleri): pick → {kind, count?}
    marker_map = {}
    for l in loops:
        sp = l.get("startPick")
        ep = l.get("endPick")
        if sp is not None and 0 <= sp < weft:
            marker_map[sp] = {"kind": "DO", "count": l.get("count", 2)}
        if ep is not None and 0 <= ep < weft:
            marker_map[ep] = {"kind": "NEXT"}
    return {"matrix": matrix, "expanded_picks": expanded, "marker_map": marker_map}


def _tarak_rle(tarak):
    """tarak.js rle() port — diş gruplarını döner."""
    if not tarak or not isinstance(tarak, dict):
        return []
    threads = tarak.get("dentThreads") or []
    if not threads:
        return []
    groups = []
    cur_tel, cur_count, cur_start = threads[0], 1, 0
    for i in range(1, len(threads)):
        if threads[i] == cur_tel:
            cur_count += 1
        else:
            groups.append({"dis": cur_count, "tel": cur_tel, "start": cur_start})
            cur_tel, cur_count, cur_start = threads[i], 1, i
    groups.append({"dis": cur_count, "tel": cur_tel, "start": cur_start})
    return groups


def _tarak_summary(tarak):
    """tarak.js calcTarakSummary port."""
    if not tarak or not isinstance(tarak, dict):
        return None
    siklik = _num_or_none(tarak.get("siklik"))
    threads = tarak.get("dentThreads") or []
    dis = len(threads)
    toplam_tel = sum(int(t) for t in threads if isinstance(t, (int, float)) and t > 0)
    ort_tel_dis = (toplam_tel / dis) if dis > 0 else 0
    cozgu_siklik = (siklik or 0) * ort_tel_dis
    rapor_cm = (dis / siklik) if (siklik and siklik > 0) else 0
    return {
        "siklik": siklik or 0, "dis": dis, "toplam_tel": toplam_tel,
        "ort_tel_dis": ort_tel_dis, "cozgu_siklik": cozgu_siklik, "rapor_cm": rapor_cm
    }


@app.route("/urun/<urun_id>/teknik/<surum_id>/print", methods=["GET"])
def teknik_print(urun_id, surum_id):
    """Print-friendly HTML — Ctrl+P / window.print() ile PDF'e dökülür.
    Yeni sekmede açılır, otomatik print diyaloğu tetiklenir.
    """
    d = store.get(urun_id)
    if not d:
        abort(404)
    teknik = d.get("teknik") or {}
    surumler = teknik.get("surumler") or []
    surum = next((s for s in surumler if s.get("id") == surum_id), None)
    if not surum:
        abort(404)
    summary = _calc_teknik_summary(surum)
    desen_data = surum.get("desen") or {}
    tarak_data = surum.get("tarak") or {}
    desen_computed = _desen_compute(desen_data)
    tarak_groups = _tarak_rle(tarak_data)
    tarak_sum = _tarak_summary(tarak_data)
    return render_template(
        "teknik_print.html",
        product=d,
        surum=surum,
        summary=summary,
        desen=desen_data,
        desen_computed=desen_computed,
        tarak=tarak_data,
        tarak_groups=tarak_groups,
        tarak_sum=tarak_sum,
        cover_image=store.public_url(cover_path(d)),
        now_iso=now_iso(),
    )


@app.route("/api/urun/<urun_id>/teknik/<surum_id>/pdf", methods=["GET"])
def api_teknik_pdf(urun_id: str, surum_id: str):
    """v4.0-part-2 Adım 5 Faz 1 — print sayfasına redirect (eski URL backward-compat).
    Faz 2'de WeasyPrint binary PDF dönecek."""
    return redirect(url_for("teknik_print", urun_id=urun_id, surum_id=surum_id))


# tasarim-v2 Plan Parça 4 — Plan raporu print sayfası (window.print() + @media print, kütüphane yok)
@app.template_filter("money")
def _money(n):
    """Türkçe para formatı: 1234.5 → '1.234,50'. Plan PDF + raporlarda kullanılır."""
    try:
        s = f"{float(n):,.2f}"                                        # 1,234.50
        return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")  # 1.234,50
    except (TypeError, ValueError):
        return "—"


@app.route("/urun/<urun_id>/plan/<surum_id>/print", methods=["GET"])
def plan_print(urun_id, surum_id):
    """Plan raporu — yeni sekmede açılır, window.print() ile PDF'e dökülür.
    Tüm veri kayıtlı plan dilimi + sürüm + üründen okunur (hesap plan.js'te yapıldı)."""
    d = store.get(urun_id)
    if not d:
        abort(404)
    surumler = (d.get("teknik") or {}).get("surumler") or []
    surum = next((s for s in surumler if s.get("id") == surum_id), None)
    if not surum:
        abort(404)
    plan = (d.get("plan") or {}).get(surum_id) or {}
    return render_template(
        "plan_print.html",
        product=d, surum=surum, plan=plan,
        cover_image=store.public_url(cover_path(d)),
        now_iso=now_iso(),
    )


@app.route("/api/urun/<urun_id>/plan/<surum_id>/pdf", methods=["GET"])
def api_plan_pdf(urun_id: str, surum_id: str):
    """Plan print sayfasına redirect (teknik /pdf ile simetri)."""
    return redirect(url_for("plan_print", urun_id=urun_id, surum_id=surum_id))


# ============================================================
# Albümler (etiket-tabanlı, çoklu üyelik)
# ============================================================

def _album_slugify(name: str) -> str:
    s = (name or "").strip().lower()
    s = s.translate(str.maketrans("çğıİöşü", "cgiiosu"))
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "album"


def _unique_album_slug(base: str, existing: list[str]) -> str:
    if base not in existing:
        return base
    i = 2
    while f"{base}-{i}" in existing:
        i += 1
    return f"{base}-{i}"


# ------------------------------------------------------------
# v4.0-part-2 Sprint 11 — Generik albüm/renk mutasyon yardımcıları
# `d` herhangi bir kayıt: {images: [...], albums: [...]}.
# key_field görsel anahtar alanı: ürün="path", araştırma="storage_path".
# Hatalar ValueError ile yükselir; rotalar 400'e çevirir.
# ------------------------------------------------------------

def _albums_create(d: dict, name: str) -> str:
    albums = d.get("albums") or []
    existing = [a.get("slug") for a in albums if isinstance(a, dict)]
    slug = _unique_album_slug(_album_slugify(name), existing)
    albums.append({"slug": slug, "name": name})
    d["albums"] = albums
    return slug


def _albums_delete(d: dict, slug: str) -> None:
    d["albums"] = [a for a in (d.get("albums") or []) if a.get("slug") != slug]
    for im in (d.get("images") or []):
        tags = im.get("albums") or []
        if slug in tags:
            im["albums"] = [s for s in tags if s != slug]


def _albums_rename(d: dict, slug: str, new_name: str) -> bool:
    for a in (d.get("albums") or []):
        if a.get("slug") == slug:
            a["name"] = new_name
            return True
    return False


def _albums_assign(d: dict, slug: str, keys: list[str], add: bool, key_field: str = "path") -> int:
    if add:
        known = [a.get("slug") for a in (d.get("albums") or [])]
        if slug not in known:
            raise ValueError("Albüm tanımlı değil")
    key_set = set(keys)
    affected = 0
    for im in (d.get("images") or []):
        if im.get(key_field) not in key_set:
            continue
        tags = set(im.get("albums") or [])
        if add:
            if slug not in tags:
                tags.add(slug); affected += 1
        else:
            if slug in tags:
                tags.discard(slug); affected += 1
        im["albums"] = sorted(tags)
    return affected


def _image_set_colors(d: dict, key: str, payload: dict, key_field: str = "path") -> dict:
    """Bir görselin atkı/çözgü/toplam renk atamasını günceller (kısmi).
    v4.0-part-2 Sprint 12: weft/warp ARRAY (çoklu renk), mix TEK obje.
    - null/{}/[] -> o rol silinir
    - weft/warp için tek obje gelirse array'e wrap (legacy istemci uyumu)
    - mix sadece obje veya null kabul eder
    Güncellenmiş colors dict'ini döner."""
    images = d.get("images") or []
    match = next((im for im in images if im.get(key_field) == key), None)
    if not match:
        raise ValueError("Görsel bulunamadı")
    # Mevcut colors'u önce normalize et (eski tek-renk formatı varsa array'e çevir)
    cur = _normalize_role_colors(match.get("colors") or {})
    ts = now_iso()

    # weft + warp: array tutulur
    for role in ("weft", "warp"):
        if role not in payload:
            continue
        v = payload[role]
        if v is None or v == [] or v == {}:
            cur.pop(role, None)
            continue
        # Tek obje gelirse array'e wrap (legacy istemci uyumu)
        if isinstance(v, dict):
            v = [v]
        if not isinstance(v, list):
            raise ValueError(f"{role} için array (veya obje) bekleniyor")
        cleaned = []
        for i, item in enumerate(v):
            if not isinstance(item, dict) or not item.get("hex"):
                raise ValueError(f"{role}[{i}] için hex zorunlu")
            item["hex"] = str(item["hex"]).upper()
            item["name"] = (str(item.get("name") or "")).strip() or "—"
            item["picked_at"] = ts
            cleaned.append(item)
        if cleaned:
            cur[role] = cleaned
        else:
            cur.pop(role, None)

    # mix: tek obje
    if "mix" in payload:
        v = payload["mix"]
        if v is None or v == {} or v == []:
            cur.pop("mix", None)
        elif isinstance(v, dict) and v.get("hex"):
            v["hex"] = str(v["hex"]).upper()
            v["name"] = (str(v.get("name") or "")).strip() or "—"
            v["picked_at"] = ts
            cur["mix"] = v
        else:
            raise ValueError("mix için hex zorunlu")

    if cur:
        match["colors"] = cur
    else:
        match.pop("colors", None)
    return cur


@app.route("/api/urun/<urun_id>/album-ekle", methods=["POST"])
def api_album_create(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    name = clean((request.get_json(force=True) or {}).get("name"))
    if not name:
        return jsonify({"ok": False, "error": "Albüm adı zorunlu"}), 400
    slug = _albums_create(d, name)
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True, "slug": slug, "name": name})


@app.route("/api/urun/<urun_id>/album-sil", methods=["POST"])
def api_album_delete(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    slug = (request.get_json(force=True) or {}).get("slug")
    if not slug:
        return jsonify({"ok": False, "error": "slug zorunlu"}), 400
    _albums_delete(d, slug)
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True})


@app.route("/api/urun/<urun_id>/album-yeniden-adlandir", methods=["POST"])
def api_album_rename(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    slug = body.get("slug")
    new_name = clean(body.get("new_name"))
    if not slug or not new_name:
        return jsonify({"ok": False, "error": "slug ve new_name zorunlu"}), 400
    if not _albums_rename(d, slug, new_name):
        return jsonify({"ok": False, "error": "Albüm bulunamadı"}), 404
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True})


@app.route("/api/urun/<urun_id>/gorsel-renk", methods=["POST"])
def api_set_image_colors(urun_id: str):
    """Bir görselin atkı/çözgü/toplam renk atamasını günceller.
    v4.0-part-2 Sprint 12: weft/warp ARRAY (çoklu renk), mix TEK obje.
    Body:
        {path: str, colors: {
            weft: [{hex, rgb, lab, name, delta_e, points}, ...]  ya da {hex,...} (legacy),
            warp: [{...}, ...]  ya da {hex,...} (legacy),
            mix:  {hex,...} | null | {}
        }}
    - weft/warp için: None/{}/[] → o rol silinir; array → tümü kayıt; tek obje → [obje]'ye normalize
    - mix için: None/{} → silinir; obje → kaydedilir
    - Sadece gönderilen rol(ler) güncellenir (kısmi update)
    """
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    target = body.get("path")
    payload = body.get("colors") or {}
    if not target or not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "path ve colors zorunlu"}), 400
    try:
        cur = _image_set_colors(d, target, payload, key_field="path")
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({
        "ok": True,
        "palette": _derive_color_palette(d.get("images") or []),
        "image_colors": cur,
    })


def _image_set_ai_colors(d: dict, key: str, ai_data: dict, key_field: str = "path") -> dict:
    """P6 — Bir ürün görselinin ai_colors (vision renk analizi) alanını yazar.
    Manuel 'colors' (Atkı/Çözgü/Toplam) alanına DOKUNMAZ (Anayasa #2)."""
    images = d.get("images") or []
    match = next((im for im in images if im.get(key_field) == key), None)
    if not match:
        raise ValueError("Görsel bulunamadı")
    data = dict(ai_data or {})
    data["analyzed_at"] = now_iso()
    match["ai_colors"] = data
    return data


@app.route("/api/urun/<urun_id>/gorsel-vision", methods=["POST"])
def api_urun_gorsel_vision(urun_id: str):
    """P6 — Bir ürün VARYANT görselini AI (vision) ile analiz et → baskın renkler/doku/şeffaflık.
    images[i].ai_colors'a yazar; manuel renk (Atkı/Çözgü/Toplam) DOKUNULMAZ (#2). Role atamayı
    kullanıcı 'uygula' ile /gorsel-renk üzerinden yapar (#6)."""
    if not _GEMINI_AVAILABLE:
        return jsonify({"ok": False, "error": "gemini modülü yok"}), 503
    if not os.environ.get("GEMINI_API_KEY"):
        return jsonify({"ok": False, "error": "no_api_key", "message": "GEMINI_API_KEY tanımsız"}), 503
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    body = request.get_json(silent=True) or {}
    path = (body.get("path") or "").strip()
    if not path:
        return jsonify({"ok": False, "error": "path zorunlu"}), 400
    if not any(im.get("path") == path for im in (d.get("images") or [])):
        return jsonify({"ok": False, "error": "Görsel bulunamadı"}), 404
    requested_model = (body.get("model") or "").strip() or None
    model_override = requested_model if requested_model in GEMINI_MODEL_WHITELIST else None
    try:
        img_bytes = store.download_image_bytes(path)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Görsel indirilemedi: {e}"}), 502
    ai = gx.analyze_fabric_image(img_bytes, model=model_override)
    if ai.get("error"):
        return jsonify({"ok": False, "error": ai["error"]}), 200   # DB'ye yazma
    saved = _image_set_ai_colors(d, path, ai, key_field="path")
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True, "path": path, "ai_colors": saved})


@app.route("/api/urun/<urun_id>/album-atama", methods=["POST"])
def api_album_assign(urun_id: str):
    """Toplu görsel ↔ albüm atama. Body: {slug, paths: [str], add: bool}.
    add=True → albums listesine slug ekle (set semantiği); add=False → çıkar."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    slug = body.get("slug")
    paths = body.get("paths") or []
    add = bool(body.get("add", True))
    if not slug or not isinstance(paths, list):
        return jsonify({"ok": False, "error": "slug ve paths zorunlu"}), 400
    try:
        affected = _albums_assign(d, slug, paths, add, key_field="path")
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    if affected:
        d["updated_at"] = now_iso()
        store.upsert(d)
    return jsonify({"ok": True, "affected": affected})


# ============================================================
# v4.0-part-2 Adım 7 — PDF Dokümanlar + Rich-Text Notlar
# ============================================================

def save_pdf(file_storage, urun_id: str) -> dict:
    """PDF'i pdfler bucket'a yükle ve metadata dict'i döndür.
    Path: <urun_id>/<uuid8>_<güvenli_ad>.pdf
    Bucket yoksa otomatik oluşturmaya çalışır (Supabase 'Bucket not found' fallback)."""
    raw_name = file_storage.filename or "doc.pdf"
    safe_name = secure_filename(raw_name) or "doc.pdf"
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    uid8 = uuid.uuid4().hex[:8]
    path = f"{urun_id}/{uid8}_{safe_name}"
    data = file_storage.read()
    if not data:
        raise ValueError("Dosya boş")
    if len(data) > PDF_MAX_BYTES:
        raise ValueError(f"Dosya çok büyük (max {PDF_MAX_BYTES // (1024*1024)} MB)")
    # MIME ipucu — magic header %PDF
    if not data.startswith(b"%PDF"):
        raise ValueError("Geçerli bir PDF dosyası değil")
    try:
        store.upload_pdf(path, data)
    except Exception as e:
        msg = str(e).lower()
        if "bucket not found" in msg or "404" in msg or "not_found" in msg:
            # v4.0-part-2 Adım 7 hotfix: bucket yoksa otomatik oluştur + yeniden dene
            store.ensure_bucket_pdfs()
            store.upload_pdf(path, data)
        else:
            raise
    return {
        "path": path,
        "name": raw_name,  # orijinal ad (görüntülemek için)
        "size": len(data),
        "uploaded_at": now_iso(),
    }


@app.route("/api/urun/<urun_id>/pdf-ekle", methods=["POST"])
def api_pdf_ekle(urun_id: str):
    """Bir veya daha fazla PDF yükle. Multipart: files=PDF[]"""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    files = [x for x in request.files.getlist("files") if x and x.filename]
    if not files:
        return jsonify({"ok": False, "error": "Dosya yok"}), 400
    pdfs = d.get("pdfs") or []
    added = []
    for fs in files:
        try:
            meta = save_pdf(fs, urun_id)
        except Exception as e:
            return jsonify({"ok": False, "error": f"{fs.filename}: {e}"}), 400
        pdfs.append(meta)
        meta_with_url = dict(meta)
        meta_with_url["url"] = store.public_url_pdf(meta["path"])
        added.append(meta_with_url)
    d["pdfs"] = pdfs
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True, "added": added, "count": len(pdfs)})


@app.route("/api/urun/<urun_id>/pdf-sil", methods=["POST"])
def api_pdf_sil(urun_id: str):
    """Tek PDF sil. Body: {path}"""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    target = body.get("path")
    if not target:
        return jsonify({"ok": False, "error": "path zorunlu"}), 400
    # Path traversal koruması: silinecek path mutlaka <urun_id>/ ile başlamalı
    if not target.startswith(f"{urun_id}/"):
        return jsonify({"ok": False, "error": "Geçersiz path"}), 400
    pdfs = d.get("pdfs") or []
    before = len(pdfs)
    pdfs = [p for p in pdfs if p.get("path") != target]
    if len(pdfs) == before:
        return jsonify({"ok": False, "error": "PDF bulunamadı"}), 404
    # Storage'tan da sil
    try:
        store.delete_pdfs([target])
    except Exception:
        pass  # liste'den çıkardık, Storage'ta yoksa OK
    d["pdfs"] = pdfs
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True, "count": len(pdfs)})


@app.route("/api/urun/<urun_id>/notlar", methods=["POST"])
def api_notlar(urun_id: str):
    """Rich-text notlar kaydet (ürün-seviyesi, fallback / geriye uyum).
    v4.0-part-2 Adım 8: sürüm-spesifik notlar için
    POST /api/urun/<urun_id>/teknik/<surum_id>/notlar kullanılmalı."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    raw_html = body.get("html") or ""
    if len(raw_html) > 200_000:  # 200 KB pratik üst sınır
        return jsonify({"ok": False, "error": "Not içeriği çok büyük"}), 400
    clean_html = _sanitize_notlar_html(raw_html)
    d["notlar_html"] = clean_html
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True, "html": clean_html})


@app.route("/api/urun/<urun_id>/teknik/<surum_id>/notlar", methods=["POST"])
def api_teknik_surum_notlar(urun_id: str, surum_id: str):
    """v4.0-part-2 Adım 8 — Sürüm-spesifik notlar kaydet.
    Body: {html}. Aktif sürümün `notlar_html` alanına yazılır."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    teknik = _ensure_teknik(d)
    surum = _find_surum(teknik, surum_id)
    if not surum:
        return jsonify({"ok": False, "error": "Sürüm bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    raw_html = body.get("html") or ""
    if len(raw_html) > 200_000:
        return jsonify({"ok": False, "error": "Not içeriği çok büyük"}), 400
    clean_html = _sanitize_notlar_html(raw_html)
    surum["notlar_html"] = clean_html
    surum["guncelleme_tarihi"] = now_iso()
    d["updated_at"] = surum["guncelleme_tarihi"]
    store.upsert(d)
    return jsonify({"ok": True, "html": clean_html, "surum_id": surum_id})


@app.route("/api/urun/<urun_id>/todo", methods=["POST"])
def api_todo(urun_id: str):
    """Faz 2 — ürün-bazlı To-Do listesi kaydet. Body: {todo: [{id,text,done,order}]}.
    Tüm liste tek seferde gönderilir (notlar deseni gibi: client durumu otorite)."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    raw = body.get("todo")
    if not isinstance(raw, list):
        return jsonify({"ok": False, "error": "todo bir liste olmalı"}), 400
    if len(raw) > 500:
        return jsonify({"ok": False, "error": "Çok fazla adım (en fazla 500)"}), 400
    clean = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        text = str(it.get("text") or "").strip()[:500]
        if not text:
            continue  # boş adımları atla
        clean.append({
            "id": str(it.get("id") or "")[:40] or f"t{len(clean)}",
            "text": text,
            "done": bool(it.get("done")),
            "order": len(clean),  # temiz liste içinde sıralı (0,1,2…)
        })
    d["todo"] = clean
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({"ok": True, "todo": clean})


@app.route("/api/urun/<urun_id>/teknik/<surum_id>/notlar", methods=["GET"])
def api_teknik_surum_notlar_get(urun_id: str, surum_id: str):
    """Aktif sürümün notlar_html'ini döner (fallback: product.notlar_html)."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    teknik = _ensure_teknik(d)
    surum = _find_surum(teknik, surum_id)
    if not surum:
        return jsonify({"ok": False, "error": "Sürüm bulunamadı"}), 404
    html = surum.get("notlar_html") or ""
    fallback_used = False
    if not html.strip():
        html = d.get("notlar_html") or ""
        if html.strip():
            fallback_used = True
    return jsonify({"ok": True, "html": html, "surum_id": surum_id, "fallback": fallback_used})


@app.route("/api/urunler")
def api_urunler():
    products = [product_summary(p) for p in store.get_all()]
    return jsonify({"count": len(products), "products": products})


@app.route("/health")
def health():
    return jsonify({"ok": True})


@app.route("/sw.js")
def service_worker():
    """Service worker root scope — sw.js /sw.js'ten servis edilmeli ki tüm site scope'una sahip olsun."""
    resp = app.send_static_file("sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Content-Type"] = "application/javascript"
    return resp


@app.route("/manifest.json")
def web_manifest():
    """PWA manifest (kök yol için max uyumluluk)."""
    resp = app.send_static_file("manifest.json")
    resp.headers["Content-Type"] = "application/manifest+json"
    return resp


# ============================================================
# Analiz
# ============================================================

def _compute_stats() -> dict:
    products = store.get_all()
    total_products = len(products)
    all_labels: set = set()
    total_images = 0
    for p in products:
        for im in p.get("images") or []:
            lab = (im.get("variant_label") or "").strip().lower()
            if lab:
                all_labels.add(lab)
            total_images += 1

    by_country: dict[str, list] = {}
    for p in products:
        c = p.get("country") or "Belirtilmemiş"
        by_country.setdefault(c, []).append(p)

    country_stats: list[dict] = []
    for country, items in by_country.items():
        widths = [p["width_cm"] for p in items if p.get("width_cm")]
        weights = [p["weight_gsm"] for p in items if p.get("weight_gsm")]
        weave = Counter(p.get("weave_type") for p in items if p.get("weave_type"))
        comp = Counter(p.get("composition") for p in items if p.get("composition"))
        variant_counts = [len(p.get("images") or []) for p in items]
        labels: set = set()
        for p in items:
            for im in p.get("images") or []:
                lab = (im.get("variant_label") or "").strip().lower()
                if lab:
                    labels.add(lab)
        country_stats.append({
            "country": country,
            "count": len(items),
            "avg_width": (sum(widths) / len(widths)) if widths else None,
            "avg_weight": (sum(weights) / len(weights)) if weights else None,
            "weave_dist": weave.most_common(),
            "top_compositions": comp.most_common(3),
            "avg_variants": (sum(variant_counts) / len(variant_counts)) if variant_counts else 0.0,
            "distinct_labels": len(labels),
        })
    country_stats.sort(key=lambda s: -s["count"])

    return {
        "total_products": total_products,
        "total_countries": len(by_country),
        "total_distinct_labels": len(all_labels),
        "total_images": total_images,
        "by_country": country_stats,
    }


def _generate_insight(s: dict) -> str:
    parts = [f"<strong>{s['country']}</strong>: {s['count']} ürün"]
    if s["avg_width"]:
        parts.append(f"ortalama {int(round(s['avg_width']))} cm en")
    if s["avg_weight"]:
        parts.append(f"~{int(round(s['avg_weight']))} g/m² gramaj")
    if s["weave_dist"]:
        parts.append(f"ağırlıklı {s['weave_dist'][0][0]} dokuma")
    if s["top_compositions"]:
        parts.append(f"yaygın kompozisyon: {s['top_compositions'][0][0]}")
    parts.append(f"ortalama {s['avg_variants']:.1f} görsel/varyant")
    if s["distinct_labels"]:
        parts.append(f"{s['distinct_labels']} farklı renk")
    return ", ".join(parts) + "."


@app.route("/analiz")
def analiz():
    stats = _compute_stats()
    for s in stats["by_country"]:
        s["insight"] = _generate_insight(s)
    return render_template("analiz.html", stats=stats)


# ============================================================
# v4.0-part-2 Adım 8 — Ön Çalışma Alanı (research_pool)
# ============================================================

# Marka slug → ISO-2 ülke kodu çıkarımı (registry için)
COUNTRY_TO_ISO = {
    "türkiye": "TR", "turkey": "TR",
    "italya": "IT", "italy": "IT",
    "danimarka": "DK", "denmark": "DK",
    "almanya": "DE", "germany": "DE",
    "fransa": "FR", "france": "FR",
    "belçika": "BE", "belgium": "BE",
    "abd": "US", "usa": "US",
    "isveç": "SE", "sweden": "SE",
    "isviçre": "CH", "switzerland": "CH",
    "hollanda": "NL", "netherlands": "NL",
    "ingiltere": "GB", "uk": "GB",
    "avusturya": "AT", "austria": "AT",
    "hindistan": "IN", "india": "IN",
    "ispanya": "ES", "spain": "ES",
    "portekiz": "PT", "portugal": "PT",
}


def _country_iso(country: str | None) -> str | None:
    if not country:
        return None
    return COUNTRY_TO_ISO.get(country.strip().lower())


def _favicon_url(product_url: str | None, size: int = 64) -> str | None:
    """v4.0-part-2 Sprint 5 — Google s2 favicon URL'i client-side fetch için.
    Server-side hiçbir HTTP isteği yapmaz, sadece URL'i hesaplar."""
    if not product_url:
        return None
    try:
        from urllib.parse import urlparse, quote
        p = urlparse(product_url.strip())
        domain = (p.netloc or "").lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if not domain:
            return None
        return f"https://www.google.com/s2/favicons?domain={quote(domain)}&sz={size}"
    except Exception:
        return None


# Jinja global olarak kaydet — template'lerde {{ favicon_url(r.product_url) }} ile kullanılır
app.jinja_env.globals["favicon_url"] = _favicon_url


def _research_cover_url(row: dict) -> str | None:
    """OnCalisma-V2 (Problem 3) — havuz kapak URL'si (SALT-OKUMA, DB'ye yazmaz).
    Öncelik: (kapak/favori işaretli) yakalanan görsel → ilk yakalanan görsel →
    legacy tek görsel → og:image (thumb_url) → None (JS favicon/placeholder'a düşer).
    Tek kaynak: hem _enrich_research_row hem eklenti listesi bunu kullanır."""
    if not row:
        return None
    images = row.get("images") or []
    if isinstance(images, list) and images:
        chosen = next((im for im in images
                       if isinstance(im, dict) and (im.get("is_cover") or im.get("is_favorite"))
                       and im.get("storage_path")), None)
        if not chosen:
            chosen = next((im for im in images
                           if isinstance(im, dict) and im.get("storage_path")), None)
        if chosen:
            return store.public_url(chosen.get("storage_path"))
    if row.get("image_storage_path"):          # legacy tek görsel
        return store.public_url(row.get("image_storage_path"))
    if row.get("thumb_url"):                    # og:image
        return row.get("thumb_url")
    return None


def _enrich_research_row(row: dict) -> dict:
    """v4.0-part-2 Sprint 10 — Row'a galeri özellikleri ekle: images_count, cover_url.
    Mevcut field'lar korunur, sadece read-only ek alanlar yazılır."""
    if not row:
        return row
    images = row.get("images") or []
    row["images_count"] = len(images) if isinstance(images, list) else 0
    # OnCalisma-V2 (Problem 3) — kapak önceliği tek helper'da (yakalanan görsel → og:image → ...)
    row["cover_url"] = _research_cover_url(row)
    # OnCalisma-V2 (Problem 1) — family/varyant alanları (migration öncesi/eski satırda yoksa default)
    for _k, _d in (("family_key", None), ("base_code", None), ("is_variant_candidate", False), ("variant_of", None)):
        row.setdefault(_k, _d)
    # OnCalisma-V2 (Problem 2) — taksonomi (migration öncesi/eski satırda yoksa default)
    for _k, _d in (("category", None), ("pattern", None), ("color_family", None), ("weave_tags", []), ("style_tags", [])):
        row.setdefault(_k, _d)
    # OnCalisma-V2 (Problem 4a) — Gemini staging (migration öncesi/eski satırda yoksa default)
    for _k, _d in (("extracted_facts", {}), ("ai_summary", {}), ("enrichment_status", "raw")):
        row.setdefault(_k, _d)
    # OnCalisma-V2 (Problem 4b) — renk sayısı + AI notu
    for _k, _d in (("color_count", None), ("ai_notu", None)):
        row.setdefault(_k, _d)
    return row


@app.route("/arastirma")
def arastirma_page():
    """Ön Çalışma ana sayfa: ekleme paneli + filtreli liste."""
    brands = get_brands_registry()
    rows = store.research_list(status="pending")
    rows = [_enrich_research_row(r) for r in rows]
    return render_template(
        "arastirma.html",
        brands=brands,
        country_suggestions=COUNTRY_SUGGESTIONS,
        weave_suggestions=WEAVE_SUGGESTIONS,   # Sprint 12 — çekmecedeki Dokuma alanı datalist'i
        rows=rows,
        # OnCalisma-V2 (Problem 2) — taksonomi sözlükleri (tek kaynak store.py; JS'e kopyalanmaz)
        category_vocab=store.VALID_CATEGORIES,
        pattern_vocab=store.VALID_PATTERNS,
        weave_tags_vocab=store.VALID_WEAVE_TAGS,
        color_family_vocab=store.VALID_COLOR_FAMILIES,
    )


def _research_album_ctx(entry: dict) -> dict:
    """v4.0-part-2 Sprint 11 — Araştırma kaydının albüm + renk paleti bağlamı.
    Ürün detayındaki (product_summary/urun_detail) mantığı aynalar; görsel
    anahtarı storage_path. arastirma_detail + ekle (Ürüne Çevir) paylaşır."""
    images = entry.get("images") or []
    images_with_urls = []
    for im in images:
        if not isinstance(im, dict):
            continue
        path = im.get("storage_path")
        images_with_urls.append({
            **im,
            "url": store.public_url(path) if path else None,
        })
    albums = entry.get("albums") or []
    album_counts = {
        a.get("slug"): sum(1 for im in images_with_urls if a.get("slug") in (im.get("albums") or []))
        for a in albums
    }
    palette = _derive_color_palette(images_with_urls)
    # "Renkler" albümü tespiti — renk seçici sadece bu albümdeki görsellerden
    color_album_slug = None
    for a in albums:
        a_slug = (a.get("slug") or "").lower()
        a_name = (a.get("name") or "").strip().lower()
        if a_slug == "renkler" or a_name == "renkler":
            color_album_slug = a.get("slug")
            break
    if color_album_slug:
        color_picker_images = [im for im in images_with_urls if color_album_slug in (im.get("albums") or [])]
    else:
        color_picker_images = []
    image_color_map = {
        im["storage_path"]: {
            "label": im.get("alt") or "",
            "url": im.get("url"),
            "colors": im.get("colors") or {},
        }
        for im in color_picker_images
        if im.get("storage_path") and im.get("colors")
        and any((im.get("colors") or {}).get(k) for k in ("weft", "warp", "mix"))
    }
    return {
        "images_with_urls": images_with_urls,
        "albums": albums,
        "album_counts": album_counts,
        "palette": palette,
        "color_album_slug": color_album_slug,
        "color_picker_images": color_picker_images,
        "image_color_map": image_color_map,
    }


@app.route("/arastirma/<research_id>")
def arastirma_detail(research_id: str):
    """v4.0-part-2 Sprint 10 — Detay sayfası: bir entry'nin galerisi + meta."""
    entry = store.research_get(research_id)
    if not entry:
        return render_template("arastirma_detail.html", entry=None, research_id=research_id), 404
    entry = _enrich_research_row(entry)
    ctx = _research_album_ctx(entry)
    return render_template(
        "arastirma_detail.html",
        entry=entry,
        images=ctx["images_with_urls"],
        research_id=research_id,
        albums=ctx["albums"],
        album_counts=ctx["album_counts"],
        color_palette=ctx["palette"],
        color_album_slug=ctx["color_album_slug"],
        color_picker_images=ctx["color_picker_images"],
        image_color_map=ctx["image_color_map"],
    )


# ============================================================
# v4.0-part-2 Sprint 11 — Araştırma-kapsamlı albüm + renk rotaları
# (ürün rotalarını aynalar; görsel anahtarı storage_path)
# ============================================================

def _research_or_404(research_id: str):
    entry = store.research_get(research_id)
    if not entry:
        return None
    if entry.get("albums") is None:
        entry["albums"] = []
    if entry.get("images") is None:
        entry["images"] = []
    return entry


@app.route("/api/arastirma/<research_id>/album-ekle", methods=["POST"])
def api_research_album_create(research_id: str):
    entry = _research_or_404(research_id)
    if not entry:
        return jsonify({"ok": False, "error": "Araştırma bulunamadı"}), 404
    name = clean((request.get_json(force=True) or {}).get("name"))
    if not name:
        return jsonify({"ok": False, "error": "Albüm adı zorunlu"}), 400
    slug = _albums_create(entry, name)
    store.research_save(research_id, {"albums": entry["albums"]})
    return jsonify({"ok": True, "slug": slug, "name": name})


@app.route("/api/arastirma/<research_id>/album-sil", methods=["POST"])
def api_research_album_delete(research_id: str):
    entry = _research_or_404(research_id)
    if not entry:
        return jsonify({"ok": False, "error": "Araştırma bulunamadı"}), 404
    slug = (request.get_json(force=True) or {}).get("slug")
    if not slug:
        return jsonify({"ok": False, "error": "slug zorunlu"}), 400
    _albums_delete(entry, slug)
    store.research_save(research_id, {"albums": entry["albums"], "images": entry["images"]})
    return jsonify({"ok": True})


@app.route("/api/arastirma/<research_id>/album-yeniden-adlandir", methods=["POST"])
def api_research_album_rename(research_id: str):
    entry = _research_or_404(research_id)
    if not entry:
        return jsonify({"ok": False, "error": "Araştırma bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    slug = body.get("slug")
    new_name = clean(body.get("new_name"))
    if not slug or not new_name:
        return jsonify({"ok": False, "error": "slug ve new_name zorunlu"}), 400
    if not _albums_rename(entry, slug, new_name):
        return jsonify({"ok": False, "error": "Albüm bulunamadı"}), 404
    store.research_save(research_id, {"albums": entry["albums"]})
    return jsonify({"ok": True})


@app.route("/api/arastirma/<research_id>/album-atama", methods=["POST"])
def api_research_album_assign(research_id: str):
    """Toplu görsel ↔ albüm atama. Body: {slug, paths: [storage_path], add: bool}."""
    entry = _research_or_404(research_id)
    if not entry:
        return jsonify({"ok": False, "error": "Araştırma bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    slug = body.get("slug")
    paths = body.get("paths") or []
    add = bool(body.get("add", True))
    if not slug or not isinstance(paths, list):
        return jsonify({"ok": False, "error": "slug ve paths zorunlu"}), 400
    try:
        affected = _albums_assign(entry, slug, paths, add, key_field="storage_path")
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    if affected:
        store.research_save(research_id, {"images": entry["images"]})
    return jsonify({"ok": True, "affected": affected})


@app.route("/api/arastirma/<research_id>/gorsel-renk", methods=["POST"])
def api_research_set_image_colors(research_id: str):
    """Bir araştırma görselinin atkı/çözgü/toplam renk atamasını günceller.
    Body: {path: storage_path, colors: {weft|warp|mix: {...}|null|{}}}"""
    entry = _research_or_404(research_id)
    if not entry:
        return jsonify({"ok": False, "error": "Araştırma bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    target = body.get("path")
    payload = body.get("colors") or {}
    if not target or not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "path ve colors zorunlu"}), 400
    try:
        cur = _image_set_colors(entry, target, payload, key_field="storage_path")
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    store.research_save(research_id, {"images": entry["images"]})
    return jsonify({
        "ok": True,
        "palette": _derive_color_palette(entry.get("images") or []),
        "image_colors": cur,
    })


@app.route("/api/arastirma/list")
def api_arastirma_list():
    """Filtreli ön çalışma listesi.
    Query params: status (pending|imported|dismissed|all), brand_slug, country_code"""
    status = request.args.get("status", "pending")
    brand_slug = request.args.get("brand_slug") or None
    country_code = request.args.get("country_code") or None
    rows = store.research_list(status=status, brand_slug=brand_slug, country_code=country_code)
    rows = [_enrich_research_row(r) for r in rows]
    return jsonify({"ok": True, "rows": rows, "count": len(rows)})


@app.route("/api/arastirma/ekle", methods=["POST"])
def api_arastirma_ekle():
    """Yeni ön çalışma satırı ekle.
    Body (JSON): {master_url, product_url, brand_slug? | brand+country, notes?}

    Dedup: aynı URL hash daha önce eklenmişse:
      - status='pending' veya 'imported' ise hata
      - status='dismissed' ise "geri açayım mı?" hint
    products tablosunda aynı URL hash varsa "zaten ürün olarak kayıtlı" hatası.
    """
    data = request.get_json(silent=True) or {}
    purl = (data.get("product_url") or "").strip()
    if not purl:
        return jsonify({"ok": False, "error": "product_url zorunlu"}), 400

    h = store.url_hash(purl)
    if not h:
        return jsonify({"ok": False, "error": "product_url geçersiz"}), 400

    # 1) Aynı URL daha önce ürün olmuş mu?
    existing_prod = store.product_find_by_url_hash(h)
    if existing_prod:
        return jsonify({
            "ok": False, "error": "duplicate_product",
            "message": f"Bu URL zaten ürün olarak kayıtlı: {existing_prod.get('product_name') or existing_prod.get('urun_id')}",
            "urun_id": existing_prod.get("urun_id"),
        }), 409

    # 2) Aynı URL ön çalışmada var mı?
    existing_res = store.research_find_by_hash(h)
    if existing_res:
        if existing_res["status"] == "dismissed":
            return jsonify({
                "ok": False, "error": "previously_dismissed",
                "message": "Bu URL daha önce reddedilmişti. Geri açmak ister misin?",
                "research_id": existing_res["id"],
            }), 409
        return jsonify({
            "ok": False, "error": "duplicate_research",
            "message": f"Bu URL zaten ön çalışmada: {existing_res.get('brand')} / {existing_res.get('country')}",
            "research_id": existing_res["id"],
        }), 409

    # 3) Firma + ülke çözümle
    brand_slug = (data.get("brand_slug") or "").strip().lower()
    brand_name = (data.get("brand") or "").strip()
    country = (data.get("country") or "").strip()

    if brand_slug:
        # Registry'den firma bilgisi
        reg_brand = next((b for b in get_brands_registry() if b.get("slug") == brand_slug), None)
        if reg_brand:
            brand_name = brand_name or reg_brand.get("name") or brand_slug
            country = country or reg_brand.get("country") or ""
    elif brand_name:
        # Yeni firma — slug üret
        existing_slugs = {b.get("slug") for b in get_brands_registry()}
        brand_slug = _unique_brand_slug(brand_name, existing_slugs)

    if not brand_name or not country:
        return jsonify({"ok": False, "error": "brand + country zorunlu"}), 400

    country_normalized = norm_country(country)

    # 4) v4.0-part-2 Sprint 5 — Server-side og:image fetch artık yapılmaz.
    # Client-side favicon URL'i hesaplar (her sitenin Google s2 servisi favicon'u).
    # thumb_url alanı ileride manuel görsel override için boş bırakılır.
    # v4.0-part-2 Sprint 11.5 — research_pool da brand_country (HQ) alias'i kullanir
    cc = _country_iso(country_normalized)
    payload = {
        "master_url": (data.get("master_url") or "").strip(),
        "product_url": purl,
        "brand": brand_name,
        "brand_slug": brand_slug,
        "country": country_normalized,                 # geriye uyum
        "country_code": cc,
        "brand_country": country_normalized,           # YENI - HQ
        "brand_country_code": cc,
        "thumb_url": None,
        "notes": (data.get("notes") or "").strip() or None,
    }

    try:
        row = store.research_add(payload)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"DB hatası: {e}"}), 500

    return jsonify({"ok": True, "row": row})


@app.route("/api/arastirma/<research_id>/status", methods=["POST"])
def api_arastirma_status(research_id: str):
    """Status değiştir: pending | dismissed (geri aç). 'imported' otomatik (import flow)."""
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip()
    if new_status not in ("pending", "dismissed"):
        return jsonify({"ok": False, "error": "Geçersiz status (pending|dismissed)"}), 400
    row = store.research_update_status(research_id, new_status)
    if not row:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404
    return jsonify({"ok": True, "row": row})


def _run_enrich(row: dict, requested_model: str | None):
    """gx.linkten_doldur + build_enrichment_payload + firma ülkesi (brand_country) fallback.
    Dönüş: (payload, meta). payload['error'] doluysa başarısız. enrich + enrich-apply paylaşır.
    Sprint 12.1 — VISION KALDIRILDI: enrich artık SALT-METİN (görsel renk analizi ayrı yapılıyor,
    /gorsel-renk + analyze_fabric_image). Bu, AI doldurmayı belirgin hızlandırır."""
    url = (row.get("product_url") or "").strip()
    model_override = requested_model if requested_model in GEMINI_MODEL_WHITELIST else None
    result = gx.linkten_doldur(url, model=model_override)   # görsel gönderilmez (salt-metin)
    payload = gx.build_enrichment_payload(result)
    if not payload.get("error"):
        ai_sum = payload.get("ai_summary") or {}
        sug = ai_sum.get("suggested") or {}
        bc = sug.get("brand_country")
        if not bc:
            reg = next((b for b in get_brands_registry() if b.get("slug") == (row.get("brand_slug") or "")), None)
            if reg and reg.get("country"):
                bc = reg.get("country")
        if bc and str(bc).strip():
            sug["brand_country"] = norm_country(bc)
            ai_sum["suggested"] = sug
            payload["ai_summary"] = ai_sum
    meta = {
        "model": result.get("model_used") or gx.MODEL_NAME,
        "requested_model": requested_model,
        "model_invalid": bool(requested_model and not model_override),
        "vision": False,
        "result": result,
    }
    return payload, meta


def _accepted_fact(row: dict, key: str):
    """Kabul edilmiş bir extracted_facts değerini döner (yoksa None)."""
    f = (row.get("extracted_facts") or {}).get(key)
    if isinstance(f, dict) and f.get("accepted") and f.get("value") not in (None, ""):
        return f.get("value")
    return None


# OnCalisma-V2 (Problem 4a) — "Linkten Doldur" motorunu havuza taşı: text-only zenginleştirme.
# Çıktı İKİ KATMANLI staging'e yazılır (extracted_facts + ai_summary); gerçek kolonlara
# OTOMATİK yazım YOK. Yalnız research_update (whitelist + strip-retry) kullanılır.
@app.route("/api/arastirma/<research_id>/enrich", methods=["POST"])
def api_arastirma_enrich(research_id: str):
    row = store.research_get(research_id)
    if not row:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404
    if not (row.get("product_url") or "").strip():
        return jsonify({"ok": False, "error": "Bu kayıtta product_url yok"}), 400

    data = request.get_json(silent=True) or {}
    requested_model = (data.get("model") or "").strip() or None
    payload, meta = _run_enrich(row, requested_model)
    if payload.get("error"):
        return jsonify({
            "ok": False, "error": payload["error"],
            "message": meta["result"].get("message") or "Zenginleştirme başarısız",
            "model": meta["model"], "requested_model": requested_model,
            "model_invalid": meta["model_invalid"],
        }), 200

    # SADECE staging alanlarını yaz (research_update; insert/save KULLANMA).
    store.research_update(research_id, {
        "extracted_facts": payload["extracted_facts"],
        "ai_summary": payload["ai_summary"],
        "enrichment_status": "enriched",
    })
    return jsonify({
        "ok": True, "enrichment_status": "enriched",
        "extracted_facts": payload["extracted_facts"],
        "ai_summary": payload["ai_summary"],
        "suggestions": meta["result"].get("suggestions") or {},
        "model": meta["model"], "requested_model": requested_model,
        "model_invalid": meta["model_invalid"], "vision": meta["vision"],
        "unverified_fields": payload.get("unverified_fields") or [],  # P6.3 — sayfada doğrulanamayan (⚠ Şüpheli) alanlar
    })


# Sprint 12 — "AI Doldur + üzerine yaz" (tek tık): enrich + sonuçları kolonlara/product_draft'a UYGULA.
# Anayasa #6: açık, kullanıcı-tetikli "uygula" eylemi (otomatik arka plan yazımı değil).
@app.route("/api/arastirma/<research_id>/enrich-apply", methods=["POST"])
def api_arastirma_enrich_apply(research_id: str):
    row = store.research_get(research_id)
    if not row:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404
    if not (row.get("product_url") or "").strip():
        return jsonify({"ok": False, "error": "Bu kayıtta product_url yok"}), 400
    data = request.get_json(silent=True) or {}
    requested_model = (data.get("model") or "").strip() or None
    payload, meta = _run_enrich(row, requested_model)
    if payload.get("error"):
        return jsonify({
            "ok": False, "error": payload["error"],
            "message": meta["result"].get("message") or "Zenginleştirme başarısız",
            "model": meta["model"], "requested_model": requested_model,
            "model_invalid": meta["model_invalid"],
        }), 200

    ef = payload["extracted_facts"]
    ai_sum = payload["ai_summary"]
    sug = ai_sum.get("suggested") or {}

    def efv(k):
        v = (ef.get(k) or {}).get("value") if isinstance(ef.get(k), dict) else None
        return v if v not in (None, "") else None

    # 1) Staging + research kolonları (overwrite)
    patch = {
        "extracted_facts": ef, "ai_summary": ai_sum, "enrichment_status": "enriched",
    }
    if efv("brand"):
        patch["brand"] = efv("brand")
        patch["brand_slug"] = _normalize_brand_slug(efv("brand"), row.get("brand_slug"))
    bc = sug.get("brand_country")
    if bc and str(bc).strip():
        bcn = norm_country(bc)
        patch["country"] = bcn
        patch["country_code"] = _country_iso(bcn)
        patch["brand_country"] = bcn
        patch["brand_country_code"] = _country_iso(bcn)
    cat = store.validate_category(sug.get("category"))
    if cat: patch["category"] = cat
    pat = store.validate_pattern(sug.get("pattern"))
    if pat: patch["pattern"] = pat
    cf = store.validate_color_family(sug.get("color_family"))
    if cf: patch["color_family"] = cf
    wt = store.validate_enum_list(sug.get("weave_tags") or [], store.VALID_WEAVE_TAGS)
    if wt: patch["weave_tags"] = wt
    st = store.validate_str_list(sug.get("style_tags") or [])
    if st: patch["style_tags"] = st
    cc = parse_int(efv("color_count"))
    if cc is not None: patch["color_count"] = cc
    if ai_sum.get("arge_notu"):
        patch["ai_notu"] = ai_sum["arge_notu"]

    # 2) product_draft (overwrite — ürün-öncesi alanlar)
    draft = dict(row.get("product_draft") or {})
    for k in ("product_name", "product_code", "collection", "composition",
              "width_cm", "weight_gsm", "weave_type",
              "repeat_vertical_cm", "repeat_horizontal_cm", "production_country"):
        v = efv(k)
        if v is not None:
            draft[k] = v
    rp = ef.get("reference_price")
    if isinstance(rp, dict) and rp.get("value"):
        draft["reference_price"] = rp.get("value")
        draft["reference_price_type"] = rp.get("type")
        draft["reference_price_evidence"] = rp.get("evidence")
    patch["product_draft"] = draft

    store.research_update(research_id, patch)
    return jsonify({
        "ok": True, "row": store.research_get(research_id),
        "model": meta["model"], "requested_model": requested_model,
        "model_invalid": meta["model_invalid"], "vision": meta["vision"],
        "unverified_fields": payload.get("unverified_fields") or [],
    })


# Sprint 12 — Ön Çalışmadan DOĞRUDAN ürün oluştur (Galeriye Gönder); /ekle formuna gerek yok.
@app.route("/api/arastirma/<research_id>/to-product", methods=["POST"])
def api_arastirma_to_product(research_id: str):
    row = store.research_get(research_id)
    if not row:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404
    draft = row.get("product_draft") or {}

    def pick(k):
        v = draft.get(k)
        if v not in (None, ""):
            return v
        return _accepted_fact(row, k)

    brand = clean(row.get("brand"))
    product_name = clean(pick("product_name"))
    if not brand:
        return jsonify({"ok": False, "error": "Marka boş — önce markayı doldur"}), 400
    if not product_name:
        return jsonify({"ok": False, "error": "Ürün adı boş — AI Doldur ile getir veya elle yaz"}), 400

    brand_slug = _normalize_brand_slug(brand, row.get("brand_slug"))
    product_code = clean(pick("product_code"))
    urun_id, folder_code, dest_prefix = _new_product_id(brand_slug, product_code, product_name)

    images: list = []
    research_imgs = [im for im in (row.get("images") or []) if isinstance(im, dict) and im.get("storage_path")]
    prefill_paths = [im["storage_path"] for im in research_imgs]
    prefill_alts = [im.get("alt") or "" for im in research_imgs]
    used_album_slugs = _copy_research_images(row, prefill_paths, prefill_alts, dest_prefix, images)

    # reference_price tip/evidence: draft önce, yoksa kabul edilmiş fact
    ref_type = draft.get("reference_price_type")
    ref_ev = draft.get("reference_price_evidence")
    if not ref_type:
        ef_rp = (row.get("extracted_facts") or {}).get("reference_price")
        if isinstance(ef_rp, dict) and ef_rp.get("accepted"):
            ref_type = ef_rp.get("type")
            ref_ev = ref_ev or ef_rp.get("evidence")

    fields = {
        "brand": brand, "brand_slug": brand_slug, "product_name": product_name,
        "product_code": product_code, "collection": pick("collection"),
        "composition": pick("composition"), "width_cm": pick("width_cm"),
        "weight_gsm": pick("weight_gsm"), "weave_type": pick("weave_type"),
        "repeat_vertical_cm": pick("repeat_vertical_cm"),
        "repeat_horizontal_cm": pick("repeat_horizontal_cm"),
        "arge_notu": draft.get("arge_notu"), "notes": row.get("notes"),
        "source_url": row.get("product_url"),
        "brand_country": row.get("country"), "production_country": pick("production_country"),
        "reference_price": pick("reference_price"), "reference_price_type": ref_type,
        "reference_price_evidence": ref_ev,
        "category": row.get("category"), "pattern": row.get("pattern"),
        "color_family": row.get("color_family"),
        "weave_tags": row.get("weave_tags") or [], "style_tags": row.get("style_tags") or [],
        "color_count": row.get("color_count"), "ai_notu": row.get("ai_notu"),
        "cover_index": 0,
    }
    _assemble_and_save_product(
        urun_id=urun_id, folder_code=folder_code, fields=fields, images=images,
        research_row=row, used_album_slugs=used_album_slugs, from_research_id=research_id,
    )
    return jsonify({"ok": True, "urun_id": urun_id, "redirect": url_for("urun_detail", urun_id=urun_id)})


@app.route("/api/arastirma/<research_id>/verify", methods=["POST"])
def api_arastirma_verify(research_id: str):
    """Onayla: enrichment_status='verified' + AI verisinden BOŞ olan kalıcı havuz alanlarını
    promote et (ai_notu ← ai_summary.arge_notu; color_count ← extracted_facts.color_count).
    Kullanıcı düzenlemesini EZMEZ (yalnız boşsa). Gerçek ÜRÜN kolonlarına YAZMAZ — onlar yalnız
    'Ürüne çevir' formu + insan onayıyla yazılır (Anayasa #6)."""
    row = store.research_get(research_id)
    if not row:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404
    patch = {"enrichment_status": "verified"}
    ai_summary = row.get("ai_summary") or {}
    extracted = row.get("extracted_facts") or {}
    if not (row.get("ai_notu") or "").strip() and ai_summary.get("arge_notu"):
        patch["ai_notu"] = ai_summary.get("arge_notu")
    if row.get("color_count") in (None, "") and isinstance(extracted.get("color_count"), dict):
        cc = parse_int(extracted["color_count"].get("value"))
        if cc is not None:
            patch["color_count"] = cc
    updated = store.research_update(research_id, patch) or {}
    return jsonify({
        "ok": True,
        "enrichment_status": "verified",
        "ai_notu": updated.get("ai_notu") or patch.get("ai_notu"),
        "color_count": updated.get("color_count") if updated.get("color_count") is not None else patch.get("color_count"),
    })


@app.route("/api/arastirma/<research_id>/accept-fact", methods=["POST"])
def api_arastirma_accept_fact(research_id: str):
    """OnCalisma-V2 (Problem 4c) — AI çıkarımını ALAN-ALAN kabul/geri-al (ANLIK).
    extracted_facts[field].accepted bayrağını yazar. Ürüne çevir YALNIZ accepted alanları
    doldurur. Gerçek ÜRÜN kolonuna YAZMAZ (Anayasa #6 — yalnız 'Ürüne çevir' + insan onayı)."""
    data = request.get_json(silent=True) or {}
    field = (data.get("field") or "").strip()
    accepted = bool(data.get("accepted"))
    if not field:
        return jsonify({"ok": False, "error": "field zorunlu"}), 400
    row = store.research_get(research_id)
    if not row:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404
    ef = row.get("extracted_facts") or {}
    if not isinstance(ef.get(field), dict):
        return jsonify({"ok": False, "error": "Alan extracted_facts'te yok"}), 400
    ef[field]["accepted"] = accepted
    patch = {"extracted_facts": ef}
    new_status = row.get("enrichment_status")
    if accepted and new_status != "verified":   # en az bir kabul → rozet sinyali
        new_status = "verified"
        patch["enrichment_status"] = "verified"
    store.research_save(research_id, patch)
    return jsonify({"ok": True, "field": field, "accepted": accepted, "enrichment_status": new_status})


@app.route("/api/arastirma/<research_id>/accept-suggestion", methods=["POST"])
def api_arastirma_accept_suggestion(research_id: str):
    """P5/P6 — AI ÖNERİSİNİ alan-alan kabul/geri-al.
    Taksonomi (category/pattern/weave_tags/color_family/style_tags) kaynağı ai_summary.suggested,
    validate edilip kolona yazılır. P6: ai_notu kaynağı ai_summary.arge_notu (düz metin).
    Geri-al → kolon temizlenir. Gerçek ÜRÜN kolonuna YAZMAZ (yalnız havuz; ürüne çevir = insan onayı, #6)."""
    data = request.get_json(silent=True) or {}
    field = (data.get("field") or "").strip()
    accepted = bool(data.get("accepted"))
    if field not in ("category", "pattern", "weave_tags", "color_family", "style_tags", "ai_notu", "brand_country"):
        return jsonify({"ok": False, "error": "Geçersiz alan"}), 400
    row = store.research_get(research_id)
    if not row:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404
    if accepted:
        if field == "ai_notu":
            # P6 — ai_notu kaynağı suggested DEĞİL → ai_summary.arge_notu (düz metin, validator yok)
            value = ((row.get("ai_summary") or {}).get("arge_notu") or "").strip() or None
        elif field == "brand_country":
            # P6.2 — firma HQ ülkesi (ÇIKARIM); suggested.brand_country zaten normalize edilmiş
            raw = ((row.get("ai_summary") or {}).get("suggested") or {}).get("brand_country")
            value = norm_country(raw) if (raw and str(raw).strip()) else None
        else:
            raw = ((row.get("ai_summary") or {}).get("suggested") or {}).get(field)
            if field == "weave_tags":
                value = store.validate_enum_list(raw or [], store.VALID_WEAVE_TAGS)
            elif field == "style_tags":
                value = store.validate_str_list(raw or [])   # serbest (vocab yok)
            elif field == "category":
                value = store.validate_category(raw)
            elif field == "pattern":
                value = store.validate_pattern(raw)
            else:  # color_family
                value = store.validate_color_family(raw)
        if not value:
            return jsonify({"ok": False, "error": "Geçerli öneri yok"}), 400
    else:
        value = [] if field in ("weave_tags", "style_tags") else None
    if field == "brand_country":
        # firma HQ → görünen country + brand_country alias + ISO kodları (tek geri-al/kabul'de hepsi)
        cc = _country_iso(value) if value else None
        store.research_update(research_id, {
            "brand_country": value, "brand_country_code": cc,
            "country": value, "country_code": cc,
        })
    else:
        store.research_update(research_id, {field: value})
    return jsonify({"ok": True, "field": field, "accepted": accepted, "value": value})


@app.route("/api/arastirma/<research_id>/accept-all", methods=["POST"])
def api_arastirma_accept_all(research_id: str):
    """P6 — AI panelindeki HER ŞEYİ tek istekte kabul/geri-al (toggle, body {accepted: bool}).
    Kabul: tüm extracted_facts[*].accepted=true + tüm suggested taksonomi (validate) research
    kolonlarına + ai_notu ← ai_summary.arge_notu. Geri-al: ef flag'leri false + AI'nın önerdiği
    kolonlar boş. Gerçek ÜRÜN kolonuna YAZMAZ (#6). image_analysis color_count DAHİL DEĞİL (manuel)."""
    data = request.get_json(silent=True) or {}
    accepted = bool(data.get("accepted"))
    row = store.research_get(research_id)
    if not row:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404
    ai_summary = row.get("ai_summary") or {}
    suggested = ai_summary.get("suggested") or {}

    # 1) Factual: extracted_facts[*].accepted (yalnız değerli alanlar) → research_save (whitelist'siz)
    ef = row.get("extracted_facts") or {}
    enrichment_status = row.get("enrichment_status")
    for _k, _f in ef.items():
        # P6.3 — "Tümünü Kabul" ŞÜPHELİ (unverified) alanlara DOKUNMAZ; onlar yalnız elle kabul/geri-al
        if isinstance(_f, dict) and _f.get("value") and not _f.get("unverified"):
            _f["accepted"] = accepted
    save_patch = {"extracted_facts": ef}
    if accepted and enrichment_status != "verified":
        enrichment_status = "verified"
        save_patch["enrichment_status"] = "verified"
    store.research_save(research_id, save_patch)

    # 2) Taksonomi + ai_notu → research kolonları (whitelist + strip-retry)
    cols: dict = {}
    if accepted:
        cat = store.validate_category(suggested.get("category"))
        pat = store.validate_pattern(suggested.get("pattern"))
        cf = store.validate_color_family(suggested.get("color_family"))
        wt = store.validate_enum_list(suggested.get("weave_tags") or [], store.VALID_WEAVE_TAGS)
        st = store.validate_str_list(suggested.get("style_tags") or [])
        an = (ai_summary.get("arge_notu") or "").strip() or None
        if cat: cols["category"] = cat
        if pat: cols["pattern"] = pat
        if cf: cols["color_family"] = cf
        if wt: cols["weave_tags"] = wt
        if st: cols["style_tags"] = st
        if an: cols["ai_notu"] = an
        # P6.2 — firma ülkesi (ÇIKARIM) → country + brand_country + ISO kodları
        bc = norm_country(suggested.get("brand_country")) if (suggested.get("brand_country") and str(suggested.get("brand_country")).strip()) else None
        if bc:
            _cc = _country_iso(bc)
            cols["brand_country"] = bc; cols["brand_country_code"] = _cc
            cols["country"] = bc; cols["country_code"] = _cc
    else:
        # Geri-al: yalnız AI'nın önerdiği alanları temizle (kullanıcının elle girdiğine dokunma)
        if suggested.get("category"): cols["category"] = None
        if suggested.get("pattern"): cols["pattern"] = None
        if suggested.get("color_family"): cols["color_family"] = None
        if suggested.get("weave_tags"): cols["weave_tags"] = []
        if suggested.get("style_tags"): cols["style_tags"] = []
        if ai_summary.get("arge_notu"): cols["ai_notu"] = None
        if suggested.get("brand_country"):
            cols["brand_country"] = None; cols["brand_country_code"] = None
            cols["country"] = None; cols["country_code"] = None
    if cols:
        store.research_update(research_id, cols)

    def _out(key):
        return cols[key] if key in cols else row.get(key)
    return jsonify({
        "ok": True, "accepted": accepted,
        "extracted_facts": ef, "enrichment_status": enrichment_status,
        "category": _out("category"), "pattern": _out("pattern"),
        "color_family": _out("color_family"), "weave_tags": _out("weave_tags"),
        "style_tags": _out("style_tags"), "ai_notu": _out("ai_notu"),
        "brand_country": _out("brand_country"), "country": _out("country"),
    })


@app.route("/api/arastirma/<research_id>", methods=["DELETE"])
def api_arastirma_delete(research_id: str):
    """Soft delete (status='dismissed'). Hard delete için ?hard=1."""
    if request.args.get("hard") == "1":
        store.research_hard_delete(research_id)
        return jsonify({"ok": True, "hard": True})
    store.research_delete(research_id)
    return jsonify({"ok": True, "hard": False})


@app.route("/api/arastirma/<research_id>", methods=["POST"])
def api_arastirma_update(research_id: str):
    """v4.0-part-2 Sprint 6 — Düzenleme.
    Body (JSON): {master_url?, product_url?, brand?, brand_slug?, country?, notes?}

    Marka değişirse brand_slug otomatik türetilir (override edilebilir).
    URL değişirse hash yeniden hesaplanır; aynı hash'te başka satır varsa 409.
    """
    data = request.get_json(silent=True) or {}
    row = store.research_get(research_id)
    if not row:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404

    patch: dict = {}

    if "product_url" in data:
        new_purl = (data.get("product_url") or "").strip()
        if not new_purl:
            return jsonify({"ok": False, "error": "product_url boş olamaz"}), 400
        new_hash = store.url_hash(new_purl)
        if new_hash and new_hash != row.get("product_url_hash"):
            # Çakışma kontrol — başka bir satırda bu hash var mı
            other = store.research_find_by_hash(new_hash)
            if other and other.get("id") != research_id:
                return jsonify({
                    "ok": False, "error": "duplicate_research",
                    "message": "Bu URL zaten başka bir satırda kayıtlı.",
                    "research_id": other.get("id"),
                }), 409
            # Ürünlerde de var mı?
            existing_prod = store.product_find_by_url_hash(new_hash)
            if existing_prod:
                return jsonify({
                    "ok": False, "error": "duplicate_product",
                    "message": f"Bu URL zaten ürün olarak kayıtlı: {existing_prod.get('product_name') or existing_prod.get('urun_id')}",
                    "urun_id": existing_prod.get("urun_id"),
                }), 409
            patch["product_url_hash"] = new_hash
        patch["product_url"] = new_purl

    if "master_url" in data:
        patch["master_url"] = (data.get("master_url") or "").strip()

    if "notes" in data:
        patch["notes"] = (data.get("notes") or "").strip() or None

    # Brand + country: kullanıcı brand_slug verirse registry'den, vermezse text+otomatik slug
    if "brand_slug" in data and data.get("brand_slug"):
        new_slug = (data.get("brand_slug") or "").strip().lower()
        reg_brand = next((b for b in get_brands_registry() if b.get("slug") == new_slug), None)
        if reg_brand:
            patch["brand_slug"] = new_slug
            patch["brand"] = data.get("brand") or reg_brand.get("name") or new_slug
            country_raw = data.get("country") or reg_brand.get("country")
            if country_raw:
                country_norm = norm_country(country_raw)
                cc = _country_iso(country_norm)
                patch["country"] = country_norm
                patch["country_code"] = cc
                patch["brand_country"] = country_norm  # v4.0-part-2 Sprint 11.5 alias
                patch["brand_country_code"] = cc
    elif "brand" in data and data.get("brand"):
        # Marka artık düz metin (input+datalist). Mevcut bir firmayla (slug VEYA ad) eşleşirse
        # onun slug'ını KORU (yeni kopya/-2 yaratma); değilse yeni unique slug üret.
        brand_name = (data.get("brand") or "").strip()
        reg = get_brands_registry()
        base = brand_slugify(brand_name)
        match = next((b for b in reg
                      if b.get("slug") == base
                      or (b.get("name") or "").strip().casefold() == brand_name.casefold()), None)
        patch["brand"] = brand_name
        if match:
            patch["brand_slug"] = match.get("slug")
            # Ülke verilmediyse bilinen firmadan otomatik doldur (eski 'change' autofill yerine)
            if not (data.get("country") or "").strip() and match.get("country"):
                cn = norm_country(match.get("country"))
                cc = _country_iso(cn)
                patch["country"] = cn
                patch["country_code"] = cc
                patch["brand_country"] = cn
                patch["brand_country_code"] = cc
        else:
            existing_slugs = {b.get("slug") for b in reg}
            patch["brand_slug"] = _unique_brand_slug(brand_name, existing_slugs)

    if "country" in data and data.get("country") and "country" not in patch:
        country_norm = norm_country((data.get("country") or "").strip())
        cc = _country_iso(country_norm)
        patch["country"] = country_norm
        patch["country_code"] = cc
        patch["brand_country"] = country_norm           # v4.0-part-2 Sprint 11.5 alias
        patch["brand_country_code"] = cc

    # OnCalisma-V2 (Problem 2) — taksonomi (havuzda elle sınıflandırma; doğrulanıp patch'e)
    if "category" in data:
        patch["category"] = store.validate_category(data["category"])
    if "pattern" in data:
        patch["pattern"] = store.validate_pattern(data["pattern"])
    if "color_family" in data:
        patch["color_family"] = store.validate_color_family(data["color_family"])
    if "weave_tags" in data:
        patch["weave_tags"] = store.validate_enum_list(data.get("weave_tags") or [], store.VALID_WEAVE_TAGS)
    if "style_tags" in data:
        patch["style_tags"] = store.validate_str_list(data.get("style_tags") or [])
    # OnCalisma-V2 (Problem 4b) — renk sayısı + AI notu (havuzda elle düzenleme)
    if "color_count" in data:
        patch["color_count"] = parse_int(data["color_count"])
    if "ai_notu" in data:
        patch["ai_notu"] = clean(data["ai_notu"])

    # Sprint 12 — product_draft (çekmecedeki genişletilmiş ürün alanları, jsonb)
    if "product_draft" in data and isinstance(data.get("product_draft"), dict):
        draft = dict(row.get("product_draft") or {})
        NUM = {"width_cm", "weight_gsm", "repeat_vertical_cm", "repeat_horizontal_cm"}
        for k, v in data["product_draft"].items():
            if k in NUM:
                iv = parse_int(v)
                draft.pop(k, None) if iv is None else draft.__setitem__(k, iv)
            elif k == "reference_price_type":
                draft["reference_price_type"] = v if v in ("exact", "from") else None
            else:
                cv = clean(v) if isinstance(v, str) else v
                draft.pop(k, None) if cv in (None, "") else draft.__setitem__(k, cv)
        patch["product_draft"] = draft

    if not patch:
        return jsonify({"ok": True, "row": row, "noop": True})

    try:
        updated = store.research_update(research_id, patch)
    except Exception as e:
        return jsonify({"ok": False, "error": f"DB hatası: {e}"}), 500

    return jsonify({"ok": True, "row": updated})


# ============================================================
# v4.0-part-2 Sprint 9 — Tarayıcı eklentisi: görsel yakalama
# ============================================================

def _download_image_bytes(url: str, timeout: float = 10.0) -> bytes:
    """Eklentiden gelen imageUrl'i sunucu tarafında indir.
    Boyut sınırı: EXTENSION_MAX_BYTES. Hata durumunda exception fırlatır."""
    req = UrlRequest(url, headers={
        "User-Agent": "Mozilla/5.0 (MobidikARGE Extension Capture)",
        "Accept": "image/*,*/*;q=0.8",
    })
    with urlopen(req, timeout=timeout) as resp:
        cl = resp.headers.get("Content-Length")
        if cl:
            try:
                if int(cl) > EXTENSION_MAX_BYTES:
                    raise ValueError(f"Görsel çok büyük: Content-Length={cl}")
            except ValueError:
                pass  # malformed Content-Length — yine de okuruz, +1 byte ile yakalarız
        data = resp.read(EXTENSION_MAX_BYTES + 1)
        if not data:
            raise ValueError("Boş response")
        if len(data) > EXTENSION_MAX_BYTES:
            raise ValueError(f"Görsel çok büyük: > {EXTENSION_MAX_BYTES} byte")
        return data


def _extension_token_ok(req) -> bool:
    """X-Mobidik-Token header'ını sabit-zamanlı karşılaştır.
    Token tanımlı değilse False (yanlışlıkla open kalmasın)."""
    if not MOBIDIK_API_TOKEN:
        return False
    sent = req.headers.get("X-Mobidik-Token", "") or ""
    return hmac.compare_digest(sent, MOBIDIK_API_TOKEN)


def _extension_cors_headers() -> dict:
    """Eklentiden gelen istekler için CORS header'ları.
    Origin '*' — token zaten koruma sağlıyor."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Mobidik-Token",
        "Access-Control-Max-Age": "86400",
    }


def _ext_response(payload: dict, status_code: int = 200):
    """jsonify + CORS header'larını birlikte set eden yardımcı."""
    resp = make_response(jsonify(payload), status_code)
    for k, v in _extension_cors_headers().items():
        resp.headers[k] = v
    return resp


def _resolve_brand_from_input(brand_in: str) -> tuple[str, str, str, str, str | None]:
    """Marka girdisini registry ile karşılaştırıp standart 5'liyi döndür.
    Returns: (brand_name, brand_slug, default_master_url|"", country, country_code)
    """
    brand_slug = brand_slugify(brand_in) if brand_in else "diger"
    reg = get_brands_registry()
    reg_brand = next((b for b in reg if b.get("slug") == brand_slug), None)
    if reg_brand:
        brand_name = reg_brand.get("name") or brand_in or brand_slug
        default_master = reg_brand.get("default_master_url") or ""
        country = reg_brand.get("country") or "Bilinmiyor"
        country_code = _country_iso(country)
    else:
        brand_name = brand_in or brand_slug
        default_master = ""
        country = "Bilinmiyor"
        country_code = None
    return brand_name, brand_slug, default_master, country, country_code


@app.route("/api/arastirma/entries-summary", methods=["GET", "OPTIONS"])
def api_arastirma_entries_summary():
    """v4.0-part-2 Sprint 10 — Eklenti modal'ı için hafif entry listesi.
    Query: ?host=<page-host> veya ?brand_slug=<slug> ile marka-filtreli.
    Token zorunlu (eklenti çağırır).
    Response: { ok, entries: [{id, brand, brand_slug, country, master_url,
                                product_url, page_title, label,
                                images_count, cover_url, added_at}, ...] }
    label = okunabilir ürün etiketi (AI ürün adı → page_title → product_url).
    """
    # CORS preflight
    if request.method == "OPTIONS":
        resp = make_response("", 204)
        for k, v in _extension_cors_headers().items():
            resp.headers[k] = v
        return resp

    if not MOBIDIK_API_TOKEN:
        return _ext_response({"ok": False, "error": "MOBIDIK_API_TOKEN tanımsız"}, 503)
    if not _extension_token_ok(request):
        return _ext_response({"ok": False, "error": "unauthorized"}, 401)

    brand_slug = (request.args.get("brand_slug") or "").strip().lower() or None
    host = (request.args.get("host") or "").strip().lower() or None
    show_all = (request.args.get("all") or "").lower() in ("1", "true", "yes")

    # host verilmişse → registry'den brand_slug çöz
    if host and not brand_slug:
        clean_host = host.replace("www.", "").lstrip(".")
        # 1. denek: default_master_url'in domain'ine bak
        for b in get_brands_registry():
            dm = (b.get("default_master_url") or "").lower()
            if not dm:
                continue
            try:
                from urllib.parse import urlparse
                p = urlparse(dm)
                d = (p.netloc or "").replace("www.", "")
                if d == clean_host or clean_host.endswith("." + d):
                    brand_slug = b.get("slug")
                    break
            except Exception:
                pass

        # 2. denek: host'un ilk parçası registry slug'ına eşit mi?
        # (ör. dedar.com → "dedar" → brand_slug="dedar" eşleşmesi)
        if not brand_slug:
            host_first = clean_host.split(".")[0]
            for b in get_brands_registry():
                if (b.get("slug") or "").lower() == host_first:
                    brand_slug = b.get("slug")
                    break

    rows = store.research_list(status="pending", brand_slug=(None if show_all else brand_slug))

    entries = []
    for r in rows:
        images = r.get("images") or []
        # OnCalisma-V2 (Problem 4d) — eklenti modal'ı ürünü ayırt edebilsin: okunabilir etiket
        # Öncelik: AI ürün adı → sayfa başlığı (page_title) → ürün URL (son çare).
        ef = r.get("extracted_facts") or {}
        _pn = ef.get("product_name") if isinstance(ef, dict) else None
        label = ((_pn.get("value") if isinstance(_pn, dict) else None)
                 or r.get("page_title") or r.get("product_url"))
        entries.append({
            "id": r.get("id"),
            "brand": r.get("brand"),
            "brand_slug": r.get("brand_slug"),
            "country": r.get("country"),
            "master_url": r.get("master_url"),
            "product_url": r.get("product_url"),   # P4d — ürün linki (ayırt etme için)
            "page_title": r.get("page_title"),      # P4d — sayfa başlığı (okunabilir)
            "label": label,                         # P4d — modal'da gösterilecek ürün etiketi
            "images_count": len(images),
            # OnCalisma-V2 (Problem 3) — kapak önceliği tek helper'da (DRY)
            "cover_url": _research_cover_url(r),
            "added_at": r.get("added_at"),
        })

    return _ext_response({
        "ok": True,
        "entries": entries,
        "filter": {"brand_slug": brand_slug, "host": host, "show_all": show_all},
    }, 200)


@app.route("/api/arastirma/yakala", methods=["POST", "OPTIONS"])
def api_arastirma_yakala():
    """v4.0-part-2 Sprint 10 — Tarayıcı eklentisinden görsel yakalama (revize).
    Body: { imageUrl, pageUrl, pageTitle, brand, alt,
            target_id?, create_new?, master_url?, country? }
    Header: X-Mobidik-Token (zorunlu)

    Akış:
      - target_id verildi → mevcut entry'nin images[]'ine ekle (status: "added")
      - target_id yok ve create_new=true → yeni satır (status: "created")
      - İkisi de yok → 400
      - SHA-256 dedup tüm rows'ta önce kontrol → varsa o entry (status: "duplicate")
    """
    # 1) CORS preflight
    if request.method == "OPTIONS":
        resp = make_response("", 204)
        for k, v in _extension_cors_headers().items():
            resp.headers[k] = v
        return resp

    # 2) Token env tanımsızsa endpoint kapalı
    if not MOBIDIK_API_TOKEN:
        return _ext_response({
            "ok": False,
            "error": "MOBIDIK_API_TOKEN tanımsız — endpoint pasif",
        }, 503)

    # 3) Auth
    if not _extension_token_ok(request):
        return _ext_response({"ok": False, "error": "unauthorized"}, 401)

    # 4) Body parse
    data = request.get_json(silent=True) or {}
    image_url = (data.get("imageUrl") or "").strip()
    page_url = (data.get("pageUrl") or "").strip()
    page_title = (data.get("pageTitle") or "").strip() or None
    brand_in = (data.get("brand") or "").strip()
    alt = (data.get("alt") or "").strip() or None
    target_id = (data.get("target_id") or "").strip() or None
    create_new = bool(data.get("create_new"))
    body_master_url = (data.get("master_url") or "").strip() or None
    body_country = (data.get("country") or "").strip() or None

    if not image_url or not page_url:
        return _ext_response({"ok": False, "error": "imageUrl ve pageUrl zorunlu"}, 400)

    if not target_id and not create_new:
        return _ext_response({
            "ok": False,
            "error": "target_id veya create_new=true gerekli"
        }, 400)

    # 5) URL hash
    product_url_hash = store.url_hash(page_url)
    if not product_url_hash:
        return _ext_response({"ok": False, "error": "pageUrl geçersiz"}, 400)

    # 6) Görseli indir (SHA-256 orijinal bytes üzerinden)
    try:
        original_bytes = _download_image_bytes(image_url, timeout=10.0)
    except HTTPError as e:
        return _ext_response({
            "ok": False, "error": f"Görsel indirilemedi (HTTP {e.code}): {e.reason}",
        }, 502)
    except URLError as e:
        return _ext_response({"ok": False, "error": f"Görsel indirilemedi: {e.reason}"}, 502)
    except Exception as e:
        return _ext_response({"ok": False, "error": f"Görsel indirilemedi: {e}"}, 502)

    sha = hashlib.sha256(original_bytes).hexdigest()
    sha8 = sha[:8]

    # 7) Dedup: tüm rows'ta JSONB ile sha lookup
    existing = store.research_find_image_by_sha(sha)
    if existing:
        return _ext_response({
            "ok": True, "status": "duplicate",
            "row": existing, "target_id": existing.get("id"),
            "message": f"Bu görsel zaten yakalandı: {existing.get('brand', '?')}",
        }, 200)

    # 8) Marka standart 5'lisini çöz
    brand_name, brand_slug, default_master, country_reg, country_code_reg = \
        _resolve_brand_from_input(brand_in)

    # 9) target_id verildi → mevcut entry'ye ekle
    if target_id:
        target_row = store.research_get(target_id)
        if not target_row:
            return _ext_response({"ok": False, "error": "target_id geçersiz (entry bulunamadı)"}, 404)
        # Target'ın brand_slug'ını kullan (sayfa markasıyla farklı olabilir — kullanıcı bilinçli seçti)
        target_brand_slug = target_row.get("brand_slug") or brand_slug

        # 9a) Storage upload
        try:
            img = Image.open(io.BytesIO(original_bytes))
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((2000, 2000))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=85, optimize=True)
            jpeg_bytes = buf.getvalue()
        except Exception as e:
            return _ext_response({"ok": False, "error": f"Görsel işlenemedi: {e}"}, 422)

        storage_path = f"_inbox/{target_brand_slug}/{sha8}.jpg"
        try:
            store.upload_image(storage_path, jpeg_bytes, "image/jpeg")
        except Exception as e:
            return _ext_response({"ok": False, "error": f"Storage upload hatası: {e}"}, 500)

        image_meta = {
            "sha256": sha,
            "storage_path": storage_path,
            "alt": alt,
            "source_image_url": image_url,
            "added_at": store._now_iso(),
        }
        try:
            updated = store.research_append_image(target_id, image_meta)
        except Exception as e:
            return _ext_response({"ok": False, "error": f"DB append hatası: {e}"}, 500)

        return _ext_response({
            "ok": True, "status": "added",
            "row": updated, "target_id": target_id,
            "message": f"Eklendi: {target_row.get('brand', '?')}",
        }, 200)

    # 10) create_new=true → yeni satır
    # Master URL öncelik sırası: body.master_url → registry default → page_url
    master_url = body_master_url or default_master or page_url
    country = body_country or country_reg
    country_code = _country_iso(country) if body_country else country_code_reg

    # 10a) Storage upload
    try:
        img = Image.open(io.BytesIO(original_bytes))
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((2000, 2000))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85, optimize=True)
        jpeg_bytes = buf.getvalue()
    except Exception as e:
        return _ext_response({"ok": False, "error": f"Görsel işlenemedi: {e}"}, 422)

    storage_path = f"_inbox/{brand_slug}/{sha8}.jpg"
    try:
        store.upload_image(storage_path, jpeg_bytes, "image/jpeg")
    except Exception as e:
        return _ext_response({"ok": False, "error": f"Storage upload hatası: {e}"}, 500)

    image_meta = {
        "sha256": sha,
        "storage_path": storage_path,
        "alt": alt,
        "source_image_url": image_url,
        "added_at": store._now_iso(),
    }
    row = {
        "master_url": master_url,
        "product_url": page_url,
        "product_url_hash": product_url_hash,
        "brand": brand_name,
        "brand_slug": brand_slug,
        "country": country,
        "country_code": country_code,
        "brand_country": country,                 # v4.0-part-2 Sprint 11.5 — HQ alias
        "brand_country_code": country_code,
        "thumb_url": None,
        "status": "pending",
        "notes": alt,
        "is_favorite": False,
        # Legacy tek-görsel (ilk eklenen) — geriye uyum için yazılır
        "image_sha256": sha,
        "page_title": page_title,
        "image_storage_path": storage_path,
        # Yeni JSONB array
        "images": [image_meta],
        "added_at": store._now_iso(),
    }
    # OnCalisma-V2 (Problem 1) — eklenti yakalamada da family/varyant işaretle (havuz kalabalığı asıl burada)
    row.update(store.compute_family_fields(page_url, brand_slug))
    try:
        res = store.research_insert(row)   # migration yoksa family alanlarını düşürüp yine ekler
        inserted = (res.data or [row])[0]
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            existing = store.research_find_image_by_sha(sha)
            if existing:
                return _ext_response({
                    "ok": True, "status": "duplicate",
                    "row": existing, "target_id": existing.get("id"),
                }, 200)
        return _ext_response({"ok": False, "error": f"DB insert hatası: {e}"}, 500)

    return _ext_response({
        "ok": True, "status": "created",
        "row": inserted, "target_id": inserted.get("id"),
    }, 201)


@app.route("/api/arastirma/<research_id>/favorite", methods=["POST"])
def api_arastirma_favorite(research_id: str):
    """v4.0-part-2 Sprint 6 — Favori toggle.
    Body: {value: true|false}. Eksikse mevcut değer terslenir."""
    row = store.research_get(research_id)
    if not row:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404
    data = request.get_json(silent=True) or {}
    if "value" in data:
        new_val = bool(data.get("value"))
    else:
        new_val = not bool(row.get("is_favorite"))
    updated = store.research_set_favorite(research_id, new_val)
    return jsonify({"ok": True, "row": updated, "is_favorite": new_val})


@app.route("/api/arastirma/<research_id>/import", methods=["POST"])
def api_arastirma_import_mark(research_id: str):
    """Bu satırı 'imported' olarak işaretle. Ürün oluşturma akışı sonunda çağrılır.
    Body: {urun_id: '...'}"""
    data = request.get_json(silent=True) or {}
    urun_id = (data.get("urun_id") or "").strip()
    if not urun_id:
        return jsonify({"ok": False, "error": "urun_id zorunlu"}), 400
    row = store.research_update_status(research_id, "imported", imported_product_id=urun_id)
    if not row:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404
    return jsonify({"ok": True, "row": row})


# ============================================================
# v4.0-part-2 Adım 8 — Ürün status toggle (active/archived)
# ============================================================

@app.route("/api/urun/<urun_id>/status", methods=["POST"])
def api_urun_status(urun_id: str):
    """Ürünü 'archived' (çalışma yapıldı) veya 'active' yap.
    Body: {status: 'active' | 'archived'}"""
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip()
    if status not in ("active", "archived"):
        return jsonify({"ok": False, "error": "status active|archived olmalı"}), 400
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    try:
        store.update_status(urun_id, status)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "status": status})


# ============================================================
# v4.0-part-2 Sprint 8 — Çalışma Alanı (workspace)
# ============================================================

def _workspace_summary_list() -> list[dict]:
    """Workspace'deki ürünleri sıraya uygun olarak özetle döndür."""
    ids = store.workspace_get_ids()
    if not ids:
        return []
    all_products = store.get_all()
    by_id = {p["urun_id"]: p for p in all_products}
    items = []
    for uid in ids:
        if uid in by_id:
            items.append(product_summary(by_id[uid]))
    return items


def _workspace_albums_with_counts() -> list[dict]:
    """v4.0-part-2 Sprint 13: albüm listesi + her albümde kaç ürün var (workspace içinde)."""
    data = store.workspace_data_get()
    workspace_ids = set(store.workspace_get_ids())
    membership = data.get("membership") or {}
    counts: dict[str, int] = {}
    for urun_id, alb in membership.items():
        if urun_id not in workspace_ids or not alb:
            continue
        counts[alb] = counts.get(alb, 0) + 1
    out = []
    for a in (data.get("albums") or []):
        out.append({
            "id": a.get("id"),
            "name": a.get("name"),
            "color": a.get("color"),
            "count": counts.get(a.get("id"), 0),
            "created_at": a.get("created_at"),
        })
    return out


@app.route("/calisma")
def calisma_page():
    """Çalışma Alanı ana sayfa. Pinli kumaşlar grid'i + split-screen + albüm tabları."""
    items = _workspace_summary_list()
    # Sprint 13: her item'a album_id ekle
    data = store.workspace_data_get()
    membership = data.get("membership") or {}
    for it in items:
        it["album_id"] = membership.get(it.get("urun_id")) or None
    return render_template("calisma.html", items=items, total=len(items),
                           workspace_albums=_workspace_albums_with_counts())


@app.route("/api/calisma/list")
def api_calisma_list():
    """Workspace listesi (JSON) — Sprint 13: albümler + her item'da album_id."""
    items = _workspace_summary_list()
    data = store.workspace_data_get()
    membership = data.get("membership") or {}
    for it in items:
        it["album_id"] = membership.get(it.get("urun_id")) or None
    return jsonify({
        "ok": True, "items": items, "count": len(items),
        "albums": _workspace_albums_with_counts(),
    })


@app.route("/api/calisma/ekle", methods=["POST"])
def api_calisma_ekle():
    """Body: {urun_id} — workspace'e ekle."""
    data = request.get_json(silent=True) or {}
    urun_id = (data.get("urun_id") or "").strip()
    if not urun_id:
        return jsonify({"ok": False, "error": "urun_id zorunlu"}), 400
    if not store.get(urun_id):
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    ids = store.workspace_add(urun_id)
    return jsonify({"ok": True, "ids": ids, "count": len(ids)})


@app.route("/api/calisma/cikar", methods=["POST"])
def api_calisma_cikar():
    """Body: {urun_id} — workspace'ten çıkar."""
    data = request.get_json(silent=True) or {}
    urun_id = (data.get("urun_id") or "").strip()
    if not urun_id:
        return jsonify({"ok": False, "error": "urun_id zorunlu"}), 400
    ids = store.workspace_remove(urun_id)
    return jsonify({"ok": True, "ids": ids, "count": len(ids)})


@app.route("/api/calisma/sirala", methods=["POST"])
def api_calisma_sirala():
    """Body: {urun_ids: [str]} — workspace sırasını güncelle."""
    data = request.get_json(silent=True) or {}
    ids = data.get("urun_ids") or []
    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
        return jsonify({"ok": False, "error": "urun_ids string listesi olmalı"}), 400
    new_ids = store.workspace_reorder(ids)
    return jsonify({"ok": True, "ids": new_ids, "count": len(new_ids)})


# ============================================================
# v4.0-part-2 Sprint 13 — Çalışma Alanı albümleri
# ============================================================

@app.route("/api/calisma/album/ekle", methods=["POST"])
def api_calisma_album_ekle():
    """Body: {name, color?} → yeni albüm objesi."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    color = (data.get("color") or "").strip() or None
    if not name:
        return jsonify({"ok": False, "error": "name zorunlu"}), 400
    try:
        album = store.workspace_album_create(name, color)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True, "album": album, "albums": _workspace_albums_with_counts()})


@app.route("/api/calisma/album/<album_id>/sil", methods=["POST"])
def api_calisma_album_sil(album_id: str):
    """Albümü sil. İçindeki ürünler workspace'te kalır (membership None'a düşer)."""
    if not store.workspace_album_delete(album_id):
        return jsonify({"ok": False, "error": "Albüm bulunamadı"}), 404
    return jsonify({"ok": True, "albums": _workspace_albums_with_counts()})


@app.route("/api/calisma/album/<album_id>/yeniden-adlandir", methods=["POST"])
def api_calisma_album_rename(album_id: str):
    """Body: {name, color?}"""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    color = data.get("color")  # None ya da string
    if not name:
        return jsonify({"ok": False, "error": "name zorunlu"}), 400
    if not store.workspace_album_rename(album_id, name, color):
        return jsonify({"ok": False, "error": "Albüm bulunamadı"}), 404
    return jsonify({"ok": True, "albums": _workspace_albums_with_counts()})


@app.route("/api/calisma/urun-albume-tasi", methods=["POST"])
def api_calisma_urun_albume_tasi():
    """Body: {urun_id, album_id | null} → ürünü belirli albüme taşı (null = Tümü)."""
    body = request.get_json(silent=True) or {}
    urun_id = (body.get("urun_id") or "").strip()
    album_id = body.get("album_id")
    if not urun_id:
        return jsonify({"ok": False, "error": "urun_id zorunlu"}), 400
    if album_id == "":
        album_id = None
    if urun_id not in set(store.workspace_get_ids()):
        return jsonify({"ok": False, "error": "Ürün workspace'te yok"}), 400
    try:
        store.workspace_set_album(urun_id, album_id)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True, "urun_id": urun_id, "album_id": album_id,
                    "albums": _workspace_albums_with_counts()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    # FLASK_ENV=production -> debug kapali (Render asagidaki main'i kullanmaz, gunicorn calistirir)
    # Yerel calistirmada debug=True: kod degisikliklerinde otomatik reload + sablon refresh.
    debug = os.environ.get("FLASK_ENV", "").lower() != "production"
    print(f"Fabric Agent System — http://localhost:{port}  (debug={debug})")
    if not APP_PASSWORD:
        print("UYARI: APP_PASSWORD bos — panel sifresiz acik (yerel gelistirme).")
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True, use_reloader=debug)
