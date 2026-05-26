"""Faz 7.3: Flask web app — Ön onay + ana dashboard + manuel tetik.

Routes:
- GET  /              → Ana dashboard (approved ürünler)
- GET  /pending       → Ön onay sayfası (pending ürünler)
- GET  /history       → Geçmiş kararlar (approved + rejected karma)
- POST /trigger       → Manuel tarama (form: bölge)
- POST /api/approve   → JSON: {urun_id, notes?}
- POST /api/reject    → JSON: {urun_id, reasons[], notes?}
- GET  /api/products  → Ana dashboard veri (JSON)
- GET  /api/pending   → Pending veri (JSON)
- GET  /gorsel/<path> → gorseller/ static serve

Kullanim:
    python web/app.py
    # Tarayici: http://localhost:5000
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from flask import (
    Flask, jsonify, render_template, request, send_from_directory,
    redirect, url_for, flash,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

URUNLER_DIR = PROJECT_ROOT / "markalar" / "urunler"
GORSELLER_DIR = PROJECT_ROOT / "gorseller"
HAM_CIKTI_DIR = PROJECT_ROOT / "topla" / "ham_cikti"
ML_DIR = PROJECT_ROOT / "ml"
FEEDBACK_LOG = ML_DIR / "feedback_log.jsonl"

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "mobidik_arge_dev"


# ============================================================
# Helpers
# ============================================================

def load_product(urun_id: str) -> dict | None:
    """Bir ürün JSON'unu yükle."""
    for jp in URUNLER_DIR.glob("*.json"):
        if jp.stem == urun_id:
            return json.loads(jp.read_text(encoding="utf-8"))
    return None


def save_product(urun_id: str, d: dict) -> bool:
    """Bir ürün JSON'u yaz."""
    jp = URUNLER_DIR / f"{urun_id}.json"
    if not jp.exists():
        return False
    jp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def load_products_by_status(status: str) -> list[dict]:
    """approval_status == status olan tüm ürünleri yükle (özet bilgilerle)."""
    products = []
    for jp in sorted(URUNLER_DIR.glob("*.json")):
        d = json.loads(jp.read_text(encoding="utf-8"))
        approval = d.get("approval_status", {})
        current = approval.get("value") if isinstance(approval, dict) else approval
        if current != status:
            continue
        products.append(_product_summary(d))
    return products


def _product_summary(d: dict) -> dict:
    """Dashboard için product card özeti."""
    sd = d.get("source_data", {})
    tech = sd.get("technical", {})
    me = d.get("mobidik_evaluation", {})
    images = d.get("images", {})
    variants = sd.get("variants", [])

    main_image = None
    if images.get("main"):
        main_image = images["main"][0].get("local_path")
    elif variants and variants[0].get("main_image_local_path"):
        main_image = variants[0]["main_image_local_path"]

    return {
        "urun_id": d.get("urun_id"),
        "brand": d.get("brand"),
        "brand_slug": d.get("brand_slug"),
        "product_code": d.get("product_code"),
        "product_name": d.get("product_name"),
        "collection": d.get("collection"),
        "source_url": d.get("source_url"),
        "width_cm": tech.get("width_cm"),
        "weave": tech.get("weave_type_normalized") or tech.get("weave_type_raw"),
        "country": sd.get("commercial", {}).get("country_of_origin"),
        "variant_count": len(variants),
        "color_names": [v.get("color_name") for v in variants[:8]],
        "overall_score": me.get("overall_score"),
        "staubli_score": (me.get("staubli_feasibility") or {}).get("score"),
        "priority_level": me.get("priority_level"),
        "strategic_note": me.get("strategic_note"),
        "approval_status": d.get("approval_status", {}).get("value") if isinstance(d.get("approval_status"), dict) else d.get("approval_status"),
        "admin_decision": d.get("admin_decision"),
        "ml_score": d.get("ml_score"),
        "main_image": main_image,
        "is_altin": (me.get("overall_score") or 0) >= 80,
    }


def append_feedback(entry: dict):
    """feedback_log.jsonl'e satır ekle."""
    ML_DIR.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ============================================================
# Routes — HTML pages
# ============================================================

@app.route("/")
def index():
    """Ana dashboard — approved ürünler."""
    products = load_products_by_status("approved")
    products.sort(key=lambda p: -(p.get("overall_score") or 0))
    pending_count = len(load_products_by_status("pending"))
    return render_template(
        "index.html",
        products=products,
        pending_count=pending_count,
    )


@app.route("/pending")
def pending():
    """Ön onay sayfası — pending ürünler."""
    products = load_products_by_status("pending")

    # ML score sort: yüksekten düşüğe
    def sort_key(p):
        ml = p.get("ml_score") or {}
        return -(ml.get("predicted_approval_prob") or 0)
    products.sort(key=sort_key)

    # AI stats
    high = sum(1 for p in products if (p.get("ml_score") or {}).get("predicted_approval_prob", 0) >= 0.75)
    med = sum(1 for p in products if 0.5 <= ((p.get("ml_score") or {}).get("predicted_approval_prob") or 0) < 0.75)
    low = sum(1 for p in products if ((p.get("ml_score") or {}).get("predicted_approval_prob") or 0) < 0.5)

    return render_template(
        "pending.html",
        products=products,
        ai_stats={"high": high, "med": med, "low": low, "total": len(products)},
    )


@app.route("/history")
def history():
    """Geçmiş kararlar."""
    approved = load_products_by_status("approved")
    rejected = load_products_by_status("rejected")

    # Decision date'e göre sırala (en yeni önce)
    def sort_key(p):
        ad = p.get("admin_decision") or {}
        return ad.get("decision_date") or ""
    approved.sort(key=sort_key, reverse=True)
    rejected.sort(key=sort_key, reverse=True)

    return render_template(
        "history.html",
        approved=approved,
        rejected=rejected,
    )


# ============================================================
# Routes — API endpoints
# ============================================================

@app.route("/api/approve", methods=["POST"])
def api_approve():
    data = request.get_json(force=True)
    urun_id = data.get("urun_id")
    notes = data.get("notes", "")

    d = load_product(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404

    now_iso = datetime.now(timezone.utc).isoformat()

    # Güncelle
    if not isinstance(d.get("approval_status"), dict):
        d["approval_status"] = {}
    d["approval_status"]["value"] = "approved"
    d["admin_decision"] = {
        "status": "approved",
        "decision_date": now_iso,
        "decision_by": "admin",
        "notes": notes,
        "rejection_reasons": [],
    }
    d["last_updated"] = now_iso

    # Audit history
    audit_hist = d.setdefault("source_data", {}).setdefault("_provenance", {}).setdefault("audit_history", [])
    audit_hist.append({
        "audit_id": f"{urun_id}_approve_{now_iso[:10]}",
        "audit_date": now_iso[:10],
        "version_before": "pending",
        "version_after": "approved (admin onay)",
        "notes": f"Web UI'dan admin onay: {notes[:200]}",
    })

    save_product(urun_id, d)

    # feedback_log
    append_feedback({
        "timestamp": now_iso,
        "urun_id": urun_id,
        "action": "approve",
        "notes": notes,
        "model_version": (d.get("ml_score") or {}).get("model_version"),
        "predicted_prob": (d.get("ml_score") or {}).get("predicted_approval_prob"),
    })

    return jsonify({"ok": True, "urun_id": urun_id, "new_status": "approved"})


@app.route("/api/reject", methods=["POST"])
def api_reject():
    data = request.get_json(force=True)
    urun_id = data.get("urun_id")
    reasons = data.get("reasons") or []
    notes = data.get("notes", "")

    d = load_product(urun_id)
    if not d:
        return jsonify({"ok": False, "error": "Ürün bulunamadı"}), 404

    now_iso = datetime.now(timezone.utc).isoformat()

    if not isinstance(d.get("approval_status"), dict):
        d["approval_status"] = {}
    d["approval_status"]["value"] = "rejected"
    d["admin_decision"] = {
        "status": "rejected",
        "decision_date": now_iso,
        "decision_by": "admin",
        "notes": notes,
        "rejection_reasons": reasons,
    }
    d["last_updated"] = now_iso

    audit_hist = d.setdefault("source_data", {}).setdefault("_provenance", {}).setdefault("audit_history", [])
    audit_hist.append({
        "audit_id": f"{urun_id}_reject_{now_iso[:10]}",
        "audit_date": now_iso[:10],
        "version_before": "pending",
        "version_after": f"rejected (sebep: {', '.join(reasons)})",
        "notes": f"Web UI'dan admin red: {notes[:200]}",
    })

    save_product(urun_id, d)

    append_feedback({
        "timestamp": now_iso,
        "urun_id": urun_id,
        "action": "reject",
        "reasons": reasons,
        "notes": notes,
        "model_version": (d.get("ml_score") or {}).get("model_version"),
        "predicted_prob": (d.get("ml_score") or {}).get("predicted_approval_prob"),
    })

    return jsonify({"ok": True, "urun_id": urun_id, "new_status": "rejected"})


@app.route("/api/products")
def api_products():
    """JSON: ana dashboard data."""
    products = load_products_by_status("approved")
    return jsonify({"count": len(products), "products": products})


@app.route("/api/pending")
def api_pending():
    products = load_products_by_status("pending")
    return jsonify({"count": len(products), "products": products})


@app.route("/trigger", methods=["POST"])
def trigger():
    """Manuel tarama: subprocess ile topla.cli --batch çağrı."""
    region = request.form.get("region", "nordik")
    if region not in ("nordik", "italyan", "alman", "all"):
        flash(f"Geçersiz bölge: {region}", "error")
        return redirect(url_for("pending"))

    regions = ["nordik", "italyan", "alman"] if region == "all" else [region]

    # Background tetikle (asenkron — kullanıcı beklemesin)
    for r in regions:
        subprocess.Popen(
            [str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"),
             "-m", "topla.cli", "--batch", r],
            cwd=str(PROJECT_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )

    flash(
        f"🔍 {region.upper()} tarama başladı (arka planda). 5-10 dk içinde "
        f"topla/ham_cikti/aday_*.json oluşur ve pending listesine düşer.",
        "info",
    )
    return redirect(url_for("pending"))


# ============================================================
# Static — görseller
# ============================================================

@app.route("/gorsel/<path:relpath>")
def serve_gorsel(relpath: str):
    """gorseller/ klasörü servis."""
    return send_from_directory(str(GORSELLER_DIR), relpath)


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Mobidik ARGE Pazar Zekası — Web UI")
    print("=" * 50)
    print(f"\nProje: {PROJECT_ROOT}")
    print(f"Ürün sayısı: {len(list(URUNLER_DIR.glob('*.json')))}")
    print(f"\nAna dashboard:  http://localhost:5000/")
    print(f"Ön onay:        http://localhost:5000/pending")
    print(f"Geçmiş:         http://localhost:5000/history")
    print(f"\nCTRL+C ile durdurabilirsiniz.\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
