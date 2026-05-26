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
import os
import re
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
LOGS_DIR = PROJECT_ROOT / "topla" / "logs"
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
    """Ön onay sayfası — pending ürünler + yeni aday URL'ler."""
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

    # Aday URL'ler — henüz scrape edilmemiş
    with app.test_request_context():
        aday_res = api_aday()
    aday_data = aday_res.get_json() if hasattr(aday_res, "get_json") else json.loads(aday_res.data)

    return render_template(
        "pending.html",
        products=products,
        ai_stats={"high": high, "med": med, "low": low, "total": len(products)},
        adaylar=aday_data.get("adaylar", []),
        aday_count=aday_data.get("count", 0),
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


@app.route("/api/aday")
def api_aday():
    """Aday URL'leri listele (henüz scrape edilmedi).

    aday_*.json dosyalarındaki yeni_adaylar[] içeriğini topla.
    Zaten markalar/urunler/'de olanları + reddedilmişleri çıkar.
    """
    # Mevcut markalar/urunler/ slug/code listesi
    existing_keys: set[str] = set()
    rejected_urls: set[str] = set()
    for jp in URUNLER_DIR.glob("*.json"):
        d = json.loads(jp.read_text(encoding="utf-8"))
        # urun_id formatı: <brand>_<code>-<slug> veya <brand>_<slug>
        stem = jp.stem
        existing_keys.add(stem)
        approval = d.get("approval_status", {})
        status = approval.get("value") if isinstance(approval, dict) else approval
        if status == "rejected":
            url = d.get("source_url")
            if url:
                rejected_urls.add(url)

    # Aday-seviyesi hızlı red URL'leri
    rejected_urls_file = ML_DIR / "rejected_urls.jsonl"
    if rejected_urls_file.exists():
        for line in rejected_urls_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("url"):
                    rejected_urls.add(entry["url"])
            except Exception:
                continue

    # Aday JSON dosyalarından URL topla
    aday_urls: list[dict] = []
    seen_urls: set[str] = set()

    if HAM_CIKTI_DIR.exists():
        # Bugünün adaylarını öncelikle göster
        for aday_file in sorted(HAM_CIKTI_DIR.glob("aday_*.json"),
                                 key=lambda p: -p.stat().st_mtime):
            try:
                aday_data = json.loads(aday_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            region = aday_data.get("region")
            marka_sonuclari = aday_data.get("marka_sonuclari", {})
            for brand_slug, brand_data in marka_sonuclari.items():
                if brand_data.get("status") != "ok":
                    continue
                for prod in brand_data.get("yeni_adaylar") or []:
                    url = prod.get("url", "")
                    if not url or url in seen_urls or url in rejected_urls:
                        continue
                    # Var olanı atla — urun_id tahmini
                    key = prod.get("key", "")
                    estimated_urun_id = f"{brand_slug}_{key}"
                    if estimated_urun_id in existing_keys:
                        continue
                    seen_urls.add(url)
                    # Thumbnail upscale (250→500 daha kaliteli preview)
                    thumb = prod.get("thumbnail")
                    if thumb:
                        thumb = re.sub(r"width=\d+", "width=500", thumb)
                        thumb = re.sub(r"height=\d+", "height=500", thumb)
                        thumb = re.sub(r"/stencil/\d+w/", "/stencil/500w/", thumb)
                        thumb = re.sub(r"/stencil/\d+x\d+/", "/stencil/500x500/", thumb)
                    aday_urls.append({
                        "url": url,
                        "brand_slug": brand_slug,
                        "code": prod.get("code"),
                        "slug": prod.get("slug"),
                        "key": key,
                        "thumbnail": thumb,
                        "region": region,
                        "discovered_in": aday_file.name,
                    })

    return jsonify({"count": len(aday_urls), "adaylar": aday_urls})


SUPPORTED_SCRAPE_DOMAINS = {"kvadrat.dk", "dedar.com", "rubelli.com"}
UNSUPPORTED_BRANDS = {
    "zimmer-rohde.com": "Z+R Group (Z+R/ADO/Etamine/Travers) scraper henüz yazılmadı (Faz 7.11). Adaptör hazır — referans `adaptorler/zimmer_rohde.md`. Mevcut görsel indirme: `topla/scripts/download_zr_variants.py`.",
    "sahco.com": "Sahco scraper henüz yok (Faz 7.x).",
    "nya-nordiska.com": "Nya Nordiska scraper henüz yok (Faz 7.x).",
    "creationbaumann.com": "Création Baumann scraper henüz yok (Faz 7.x).",
}


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """Bir aday URL için detaylı scrape başlat (subprocess).

    Background olarak topla.cli <url> çalıştırır. stdout/stderr log dosyasına
    yönlenir (topla/logs/scrape_<timestamp>.log). Tamamlanınca
    markalar/urunler/<urun>.json oluşur (approval_status=pending).
    """
    data = request.get_json(force=True)
    url = data.get("url")
    if not url:
        return jsonify({"ok": False, "error": "url eksik"}), 400

    # Brand pre-check (subprocess başlatmadan önce)
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().replace("www.", "")
    if host in UNSUPPORTED_BRANDS:
        return jsonify({
            "ok": False,
            "error": f"Scraper yok: {host}",
            "message": UNSUPPORTED_BRANDS[host],
            "scraper_missing": True,
        }), 400
    if not any(d in host for d in SUPPORTED_SCRAPE_DOMAINS):
        return jsonify({
            "ok": False,
            "error": f"Bilinmeyen marka: {host}",
            "message": "Bu domain'e ait scraper yok. Mevcut: Kvadrat, Dedar, Rubelli.",
        }), 400

    # Log dosyası (terminale değil dosyaya yaz)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_slug = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0][:30]
    log_path = LOGS_DIR / f"scrape_{safe_slug}_{ts}.log"

    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        return jsonify({"ok": False, "error": f".venv yok: {python_exe}"}), 500

    # Playwright env — Flask context'inde LOCALAPPDATA eksik olabilir
    env = os.environ.copy()
    if "LOCALAPPDATA" not in env or "ms-playwright" not in (env.get("PLAYWRIGHT_BROWSERS_PATH", "")):
        # Explicit Windows user path
        user_localappdata = os.environ.get("LOCALAPPDATA") or f"C:\\Users\\{os.environ.get('USERNAME', 'PC')}\\AppData\\Local"
        env["LOCALAPPDATA"] = user_localappdata
        env["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(user_localappdata, "ms-playwright")

    try:
        log_f = log_path.open("w", encoding="utf-8")
        log_f.write(f"# Scrape başlangıç: {ts}\n# URL: {url}\n# CMD: python -m topla.cli {url}\n")
        log_f.write(f"# PLAYWRIGHT_BROWSERS_PATH: {env.get('PLAYWRIGHT_BROWSERS_PATH')}\n\n")
        log_f.flush()

        # Faz 7.10f fix: subprocess KALDIRILDI — sandbox context sorununa yol acti
        # (Playwright Chromium executable visible degil subprocess child'a)
        # Cozum: scrape_and_score'u Flask thread'inde DOGRUDAN cagir (ayni process,
        # ayni context). UX bloklamaz cunku daemon thread'inde.
        import threading
        def _run_inline():
            try:
                sys.path.insert(0, str(PROJECT_ROOT))
                from topla.topla import scrape_and_score
                result = scrape_and_score(url)
                log_f.write(f"\n=== SCRAPE TAMAM ===\n")
                log_f.write(json.dumps(result, ensure_ascii=False, indent=2))
                log_f.write("\n")
            except Exception as e:
                import traceback
                log_f.write(f"\n=== HATA ===\n")
                log_f.write(f"{type(e).__name__}: {e}\n")
                log_f.write(traceback.format_exc())
            finally:
                try:
                    log_f.close()
                except Exception:
                    pass
        t = threading.Thread(target=_run_inline, daemon=True)
        t.start()
        return jsonify({
            "ok": True,
            "message": f"Scrape başladı: {url}",
            "log_file": log_path.name,
            "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        })
    except Exception as e:
        import traceback
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()[:500]}), 500


@app.route("/api/quick-reject", methods=["POST"])
def api_quick_reject():
    """Aday seviyesinde hızlı red — URL'i feedback_log'a yaz, markalar/urunler/'e gitmesin.

    Kullanım: aday slug'ında "jacquard"/"metallic" gibi açıkça kötü pattern
    görüldüğünde, scrape etmeden direkt reddet.
    """
    data = request.get_json(force=True)
    url = data.get("url")
    reasons = data.get("reasons") or ["aday_seviyesinde_red"]
    notes = data.get("notes", "")

    if not url:
        return jsonify({"ok": False, "error": "url eksik"}), 400

    now_iso = datetime.now(timezone.utc).isoformat()
    append_feedback({
        "timestamp": now_iso,
        "action": "quick_reject",
        "url": url,
        "brand_slug": data.get("brand_slug"),
        "key": data.get("key"),
        "reasons": reasons,
        "notes": notes,
        "_note": "Aday seviyesinde red — scrape edilmedi. Tekrar aynı URL gelirse filtreyle.",
    })

    # Reddedilen URL'leri ayrı dosyada da tut (aday taramasında filtrelensin)
    rejected_urls_file = ML_DIR / "rejected_urls.jsonl"
    ML_DIR.mkdir(parents=True, exist_ok=True)
    with rejected_urls_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "url": url,
            "reasons": reasons,
            "timestamp": now_iso,
            "brand_slug": data.get("brand_slug"),
            "key": data.get("key"),
        }, ensure_ascii=False) + "\n")

    return jsonify({"ok": True, "url": url})


@app.route("/api/scan-status")
def api_scan_status():
    """Arka planda çalışan tarama durumu — son log dosyalarından çıkar.

    Bir tarama "aktif" sayılır eğer:
      - log dosyası son 5 dakikada modify edildi
      - log içinde "Batch run BASARILI" veya "HATA" görünmedi
    """
    import time

    now = time.time()
    active_threshold = 300  # 5 dk

    scans = []
    if LOGS_DIR.exists():
        for log_file in sorted(LOGS_DIR.glob("task_scheduler_*.log"), key=lambda p: -p.stat().st_mtime):
            # Sadece bugünün dosyaları
            today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
            if today_str not in log_file.name:
                continue

            mtime = log_file.stat().st_mtime
            age_sec = now - mtime

            # Region çıkar
            # task_scheduler_<region>_<date>.log
            parts = log_file.stem.split("_")
            region = parts[2] if len(parts) >= 3 else "unknown"

            # Log son 30 satır
            try:
                lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                last_lines = lines[-30:]
                tail = "\n".join(last_lines)
            except Exception:
                tail = ""

            # Durum: success / error / running
            success = "Batch run BASARILI" in tail or "Weekly review BASARILI" in tail
            error = "HATA:" in tail or "EXCEPTION:" in tail
            is_running = (age_sec < active_threshold) and not success and not error

            # Output JSON kompakt (son 10 satır)
            tail_short = "\n".join(last_lines[-10:])

            # Aday JSON oluştu mu?
            aday_path = HAM_CIKTI_DIR / f"aday_{region}_{today_str}.json"
            aday_count = None
            if aday_path.exists():
                try:
                    aday_data = json.loads(aday_path.read_text(encoding="utf-8"))
                    aday_count = aday_data.get("toplam_yeni_aday", 0)
                except Exception:
                    pass

            scans.append({
                "region": region,
                "log_file": log_file.name,
                "modified_at": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                "age_seconds": int(age_sec),
                "status": "running" if is_running else ("success" if success else ("error" if error else "stale")),
                "new_candidates": aday_count,
                "log_tail": tail_short,
            })

    active_count = sum(1 for s in scans if s["status"] == "running")
    return jsonify({"active_count": active_count, "scans": scans})


@app.route("/trigger", methods=["POST"])
def trigger():
    """Manuel tarama: subprocess ile topla.cli --batch çağrı."""
    region = request.form.get("region", "nordik")
    if region not in ("nordik", "italyan", "alman", "all"):
        flash(f"Geçersiz bölge: {region}", "error")
        return redirect(url_for("pending"))

    regions = ["nordik", "italyan", "alman"] if region == "all" else [region]

    # Background tetikle (asenkron — kullanıcı beklemesin)
    # Log dosyasına yaz, env=parent (Playwright PATH için)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    for r in regions:
        log_path = LOGS_DIR / f"task_scheduler_{r}_{today}.log"
        log_f = log_path.open("a", encoding="utf-8")
        log_f.write(f"\n[{datetime.now(timezone.utc).isoformat()}] === Web UI trigger ===\n")
        log_f.flush()
        subprocess.Popen(
            [str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"),
             "-m", "topla.cli", "--batch", r],
            cwd=str(PROJECT_ROOT),
            stdout=log_f,
            stderr=subprocess.STDOUT,
            env=os.environ.copy(),
            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0),
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
    # debug=False — auto-reload daemon thread'i oldurur, scrape yarida kalir
    # Code degisikligi sonrasi Flask manuel restart gerekir (Ctrl+C, yeniden basla)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
