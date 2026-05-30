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
    return render_template(
        "urun.html", product=d, urun_id=urun_id,
        cover_image=store.public_url(cover_path(d)),
        display_items=display_items,
        pinned_items=pinned_items,
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


@app.route("/sw.js")
def service_worker():
    """Service worker root scope — sw.js /sw.js'ten servis edilmeli ki tüm site scope'una sahip olsun."""
    static_dir = Path(app.static_folder) if app.static_folder else Path(__file__).resolve().parent / "static"
    resp = send_from_directory(str(static_dir), "sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Content-Type"] = "application/javascript"
    return resp


@app.route("/manifest.json")
def web_manifest():
    """PWA manifest (kök yol için max uyumluluk)."""
    static_dir = Path(app.static_folder) if app.static_folder else Path(__file__).resolve().parent / "static"
    resp = send_from_directory(str(static_dir), "manifest.json")
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
    print(f"Mobidik Kumas Paneli — http://localhost:{port}")
    if not APP_PASSWORD:
        print("UYARI: APP_PASSWORD bos — panel sifresiz acik (yerel gelistirme).")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
