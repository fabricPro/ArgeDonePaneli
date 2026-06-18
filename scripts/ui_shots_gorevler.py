"""Faz 3 — Görevler panosu screenshot (Stüdyo). Dev-only.

Çalıştırma: Flask localhost:5000 açıkken
  .venv/Scripts/python.exe scripts/ui_shots_gorevler.py

Çıktı: ui-shots/30-gorevler-dashboard-v2.png (tam), 30b-gorevler-dashboard-680-v2.png (dar).
Demo görevleri geçici tohumlar (mevcut gerçek görevlere DOKUNMAZ) → screenshot → yalnız
tohumladığı ürünleri temizler.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import store  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = os.environ.get("FAS_BASE", "http://localhost:5000")
PW = os.environ.get("APP_PASSWORD", "Katyonik<312")
OUT = Path(__file__).resolve().parent.parent / "ui-shots"
OUT.mkdir(exist_ok=True)
KEEP = "ado_goldkante_3301-pure-white-pinstripe"  # mevcut gerçek görevli ürün — dokunma


def pick():
    """(surumlu_uid, sid, genel_uid) — KEEP ürününe dokunmadan."""
    prods = store.get_all()
    surumlu = sid = genel = None
    for p in prods:
        if p["urun_id"] == KEEP:
            continue
        sl = ((p.get("teknik") or {}).get("surumler")) or []
        if sl and not surumlu:
            surumlu, sid = p["urun_id"], sl[0]["id"]
        elif (p.get("images")) and not genel:
            genel = p["urun_id"]
        if surumlu and genel:
            break
    return surumlu, sid, genel


def main():
    surumlu, sid, genel = pick()
    print(f"[i] surumlu={surumlu}/{sid} genel={genel} (korunan={KEEP})")
    store.gorev_sync_items(surumlu, [
        {"id": "g1", "text": "Atkı sıklığını 22→24 dene", "durum": "yapiliyor", "oncelik": "yuksek", "surum_id": sid},
        {"id": "g2", "text": "Kenar tahar grubunu revize et", "durum": "acik", "oncelik": "dusuk", "surum_id": sid},
        {"id": "g3", "text": "Kartela renk eşlemesi tamamlansın", "durum": "acik", "oncelik": "orta", "surum_id": None},
    ])
    store.gorev_sync_items(genel, [
        {"id": "h1", "text": "Numune dokuma planı çıkar", "durum": "acik", "oncelik": "yuksek", "surum_id": None},
        {"id": "h2", "text": "Müşteri onayı bekleniyor", "durum": "yapiliyor", "oncelik": None, "surum_id": None},
        {"id": "h3", "text": "İlk parti arşivlendi", "durum": "tamamlandi", "oncelik": None, "surum_id": None},
    ])
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 980}, device_scale_factor=2)
            page = ctx.new_page()
            page.goto(f"{BASE}/login", wait_until="networkidle")
            page.fill('input[name="password"]', PW)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")

            page.goto(f"{BASE}/gorevler", wait_until="networkidle")
            page.wait_for_timeout(900)  # kapak görselleri
            page.screenshot(path=str(OUT / "30-gorevler-dashboard-v2.png"))
            print("[ok] 30-gorevler-dashboard-v2.png")

            page.set_viewport_size({"width": 680, "height": 1080})
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUT / "30b-gorevler-dashboard-680-v2.png"))
            print("[ok] 30b-gorevler-dashboard-680-v2.png")
            browser.close()
    finally:
        store.gorev_sync_items(surumlu, [])
        store.gorev_sync_items(genel, [])
        print("[ok] cleanup (yalnız demo ürünler; gerçek görevler korundu)")


if __name__ == "__main__":
    main()
