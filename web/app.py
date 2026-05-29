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
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # yereldeyse .env yukle

import os

from flask import (
    Flask, jsonify, redirect, render_template, request, session, url_for,
)
from PIL import Image, ImageOps

import store

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB

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
    return {
        "urun_id": d.get("urun_id"), "brand": d.get("brand"),
        "brand_slug": d.get("brand_slug"), "country": d.get("country"),
        "collection": d.get("collection"), "product_name": d.get("product_name"),
        "product_code": d.get("product_code"), "width_cm": d.get("width_cm"),
        "weave_type": d.get("weave_type"),
        "cover_image": store.public_url(cover_path(d)),
        "variant_count": len(d.get("images") or []),
        "updated_at": d.get("updated_at"),
    }


# ============================================================
# Auth
# ============================================================

@app.before_request
def require_login():
    if request.endpoint in ("login", "static", "health"):
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
    products = [product_summary(p) for p in store.get_all()]
    groups: dict[str, list] = {}
    for p in products:
        groups.setdefault(p.get("country") or "Belirtilmemiş", []).append(p)
    country_groups = sorted(
        groups.items(),
        key=lambda kv: (kv[0] == "Belirtilmemiş", -len(kv[1]), kv[0]),
    )
    brands = sorted({p["brand"] for p in products if p.get("brand")})
    return render_template(
        "index.html", country_groups=country_groups, total=len(products), brands=brands,
    )


@app.route("/ekle")
def ekle():
    return render_template(
        "ekle.html", tracked_brands=TRACKED_BRANDS,
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
    return render_template(
        "urun.html", product=d, urun_id=urun_id,
        cover_image=store.public_url(cover_path(d)),
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
    for key in ("width_cm", "repeat_vertical_cm", "repeat_horizontal_cm"):
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


@app.route("/api/urun/<urun_id>/sil", methods=["POST"])
def api_delete_product(urun_id: str):
    d = store.get(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404
    store.delete_images([im.get("path") for im in (d.get("images") or [])])
    store.delete(urun_id)
    return jsonify({"ok": True})


@app.route("/api/urunler")
def api_urunler():
    products = [product_summary(p) for p in store.get_all()]
    return jsonify({"count": len(products), "products": products})


@app.route("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(f"Mobidik Kumas Paneli — http://localhost:{port}")
    if not APP_PASSWORD:
        print("UYARI: APP_PASSWORD bos — panel sifresiz acik (yerel gelistirme).")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
