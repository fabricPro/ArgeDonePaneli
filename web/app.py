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
    Flask, abort, jsonify, redirect, render_template, request, session, url_for,
)
from PIL import Image, ImageOps

import store

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB
# Sablon onbellegini kapat — her istekte disk mtime kontrolu (hem yerel hem Render)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")

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
    palette_size = len({
        c["hex"].upper()
        for im in (d.get("images") or [])
        for c in (im.get("colors") or {}).values()
        if c and c.get("hex")
    })
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
    }


# ============================================================
# Auth
# ============================================================

@app.before_request
def require_login():
    if request.endpoint in ("login", "static", "health", "service_worker", "web_manifest"):
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
    for s in products:
        s["dashboard_order"] = order_map.get(s["urun_id"])
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
    return render_template(
        "ekle.html", tracked_brands=TRACKED_BRANDS,
        countries=country_list(),
        country_suggestions=COUNTRY_SUGGESTIONS, weave_suggestions=WEAVE_SUGGESTIONS,
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
    # v3.8: Teknik çalışma sekme verisi + mobile UA detect
    teknik = d.get("teknik") or {}
    is_mobile_ua = _is_mobile_ua(request)
    return render_template(
        "urun.html", product=d, urun_id=urun_id,
        cover_image=store.public_url(cover_path(d)),
        display_items=display_items,
        display_images=display_images,
        color_palette=color_palette,
        color_picker_images=color_picker_images,
        color_album_slug=color_album_slug,
        teknik=teknik,
        is_mobile_ua=is_mobile_ua,
        pinned_items=pinned_items,
        albums=albums,
        album_counts=album_counts,
        countries=country_list(),
        country_suggestions=COUNTRY_SUGGESTIONS, weave_suggestions=WEAVE_SUGGESTIONS,
    )


# ============================================================
# API
# ============================================================

@app.route("/api/urun", methods=["POST"])
def api_create_urun():
    f = request.form
    brand = clean(f.get("brand"))
    product_name = clean(f.get("product_name"))
    if not brand:
        return jsonify({"ok": False, "error": "Marka zorunlu"}), 400
    if not product_name:
        return jsonify({"ok": False, "error": "Ürün adı zorunlu"}), 400

    brand_slug = clean(f.get("brand_slug")) or brand_slugify(brand)
    brand_slug = re.sub(r"[^a-z0-9_]", "_", brand_slug.lower()) or "diger"
    product_code = clean(f.get("product_code"))
    code_slug = slugify(product_code or product_name)

    urun_id = f"{brand_slug}_{code_slug}"
    folder_code = code_slug
    if store.get(urun_id):
        suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        folder_code = f"{code_slug}-{suffix}"
        urun_id = f"{brand_slug}_{folder_code}"
    dest_prefix = f"{brand_slug}/{folder_code}"

    files = [x for x in request.files.getlist("files") if x and x.filename]
    labels = request.form.getlist("variant_labels")
    cover_index = parse_int(f.get("cover_index")) or 0

    images = []
    for i, fs in enumerate(files):
        try:
            path = save_image(fs, dest_prefix, i)
        except Exception as e:
            return jsonify({"ok": False, "error": f"Görsel yüklenemedi ({fs.filename}): {e}"}), 400
        label = labels[i].strip() if i < len(labels) and labels[i].strip() else None
        images.append({"path": path, "variant_label": label, "is_cover": False, "order": i})
    if images:
        ci = cover_index if 0 <= cover_index < len(images) else 0
        images[ci]["is_cover"] = True

    now = now_iso()
    d = {
        "urun_id": urun_id, "brand": brand, "brand_slug": brand_slug,
        "country": norm_country(clean(f.get("country"))),
        "collection": clean(f.get("collection")), "product_name": product_name,
        "product_code": product_code or folder_code,
        "composition": clean(f.get("composition")), "width_cm": parse_int(f.get("width_cm")),
        "weight_gsm": parse_int(f.get("weight_gsm")),
        "weave_type": clean(f.get("weave_type")),
        "repeat_vertical_cm": parse_int(f.get("repeat_vertical_cm")),
        "repeat_horizontal_cm": parse_int(f.get("repeat_horizontal_cm")),
        "arge_notu": clean(f.get("arge_notu")), "notes": clean(f.get("notes")),
        "source_url": clean(f.get("source_url")),
        "created_at": now, "updated_at": now, "images": images,
    }
    store.upsert(d)
    return jsonify({"ok": True, "urun_id": urun_id, "redirect": url_for("urun_detail", urun_id=urun_id)})


@app.route("/api/urun/<urun_id>/meta", methods=["POST"])
def api_update_meta(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    data = request.get_json(force=True)
    for key in ("brand", "collection", "product_name", "product_code",
                "composition", "weave_type", "arge_notu", "notes", "source_url"):
        if key in data:
            d[key] = clean(data[key])
    if "country" in data:
        d["country"] = norm_country(clean(data["country"]))
    for key in ("width_cm", "weight_gsm", "repeat_vertical_cm", "repeat_horizontal_cm"):
        if key in data:
            d[key] = parse_int(data[key])
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
    """Bir ürünü ve tüm görsellerini atomik olarak siler. Yoksa False döner."""
    d = store.get(uid)
    if not d:
        return False
    paths = [im.get("path") for im in (d.get("images") or []) if im.get("path")]
    if paths:
        store.delete_images(paths)
    store.delete(uid)
    return True


def _derive_color_palette(images: list[dict]) -> list[dict]:
    """images[i].colors -> dedup hex palette, açıktan koyuya (LAB L desc)."""
    items = []
    for im in images:
        for role, c in (im.get("colors") or {}).items():
            if not c or not c.get("hex"):
                continue
            items.append({
                "hex": c["hex"].upper(),
                "name": c.get("name") or c.get("nearest") or "—",
                "lab": c.get("lab") or [50, 0, 0],
                "role": role,
                "image_path": im.get("path"),
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
    """Yeni teknik sürüm oluştur. Body: {ad}."""
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    ad = clean(body.get("ad")) or "Yeni Sürüm"
    teknik = _ensure_teknik(d)
    new_id = _next_surum_id([s.get("id") for s in teknik["surumler"]])
    now = now_iso()
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
    }
    teknik["surumler"].append(surum)
    # İlk sürüm otomatik aktif
    if not teknik.get("active_surum_id"):
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
    return {"matrix": matrix, "expanded_picks": expanded}


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
@require_login
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


@app.route("/api/urun/<urun_id>/album-ekle", methods=["POST"])
def api_album_create(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    name = clean((request.get_json(force=True) or {}).get("name"))
    if not name:
        return jsonify({"ok": False, "error": "Albüm adı zorunlu"}), 400
    albums = d.get("albums") or []
    existing = [a.get("slug") for a in albums if isinstance(a, dict)]
    slug = _unique_album_slug(_album_slugify(name), existing)
    albums.append({"slug": slug, "name": name})
    d["albums"] = albums
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
    albums = [a for a in (d.get("albums") or []) if a.get("slug") != slug]
    # Tüm images'tan slug'ı temizle
    for im in (d.get("images") or []):
        tags = im.get("albums") or []
        if slug in tags:
            im["albums"] = [s for s in tags if s != slug]
    d["albums"] = albums
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
    for a in (d.get("albums") or []):
        if a.get("slug") == slug:
            a["name"] = new_name
            d["updated_at"] = now_iso()
            store.upsert(d)
            return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Albüm bulunamadı"}), 404


@app.route("/api/urun/<urun_id>/gorsel-renk", methods=["POST"])
def api_set_image_colors(urun_id: str):
    """Bir görselin atkı/çözgü/toplam renk atamasını günceller.
    Body: {path: str, colors: {weft|warp|mix: {hex, rgb, lab, name, delta_e, points} | null | {}}}
    - null veya {} -> o rol silinir
    - Sadece gönderilen role'ler güncellenir (kısmi update)
    """
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    body = request.get_json(force=True) or {}
    target = body.get("path")
    payload = body.get("colors") or {}
    if not target or not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "path ve colors zorunlu"}), 400
    images = d.get("images") or []
    match = next((im for im in images if im.get("path") == target), None)
    if not match:
        return jsonify({"ok": False, "error": "Görsel bulunamadı"}), 400
    cur = match.get("colors") or {}
    for role in ("weft", "warp", "mix"):
        if role not in payload:
            continue
        v = payload[role]
        if v is None or v == {}:
            cur.pop(role, None)
            continue
        if not isinstance(v, dict) or not v.get("hex"):
            return jsonify({"ok": False, "error": f"{role} için hex zorunlu"}), 400
        # Server-side normalize
        v["hex"] = str(v["hex"]).upper()
        v["name"] = (str(v.get("name") or "")).strip() or "—"
        v["picked_at"] = now_iso()
        cur[role] = v
    if cur:
        match["colors"] = cur
    else:
        match.pop("colors", None)
    d["updated_at"] = now_iso()
    store.upsert(d)
    return jsonify({
        "ok": True,
        "palette": _derive_color_palette(images),
        "image_colors": cur,
    })


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
    # Slug ürünün albüm listesinde olmalı (add iken)
    if add:
        known = [a.get("slug") for a in (d.get("albums") or [])]
        if slug not in known:
            return jsonify({"ok": False, "error": "Albüm tanımlı değil"}), 400
    path_set = set(paths)
    affected = 0
    for im in (d.get("images") or []):
        if im.get("path") not in path_set:
            continue
        tags = set(im.get("albums") or [])
        if add:
            if slug not in tags:
                tags.add(slug); affected += 1
        else:
            if slug in tags:
                tags.discard(slug); affected += 1
        im["albums"] = sorted(tags)
    if affected:
        d["updated_at"] = now_iso()
        store.upsert(d)
    return jsonify({"ok": True, "affected": affected})


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    # FLASK_ENV=production -> debug kapali (Render asagidaki main'i kullanmaz, gunicorn calistirir)
    # Yerel calistirmada debug=True: kod degisikliklerinde otomatik reload + sablon refresh.
    debug = os.environ.get("FLASK_ENV", "").lower() != "production"
    print(f"Fabric Agent System — http://localhost:{port}  (debug={debug})")
    if not APP_PASSWORD:
        print("UYARI: APP_PASSWORD bos — panel sifresiz acik (yerel gelistirme).")
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True, use_reloader=debug)
