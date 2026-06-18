"""Faz 2 — To-Do paneli screenshot (Stüdyo). Dev-only.

Çalıştırma: Flask localhost:5000 açıkken
  .venv/Scripts/python.exe scripts/ui_shots_todo.py

Çıktı: ui-shots/20-todo-panel-v2.png (tam genişlik), 20b-todo-panel-680-v2.png (split ≤680px).
Örnek görevleri geçici tohumlar → screenshot → temizler (net-sıfır; DB'de iz bırakmaz).
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


def pick_product():
    """Sürümü olan bir ürün seç (env FAS_TEKNIK öncelikli)."""
    pref = os.environ.get("FAS_TEKNIK", "ado_goldkante_3301-pure-white-pinstripe")
    p = store.get(pref)
    if p and ((p.get("teknik") or {}).get("surumler")):
        sl = p["teknik"]["surumler"]
        return p["urun_id"], sl[0]["id"], sl[0].get("ad")
    for p in store.get_all():
        sl = ((p.get("teknik") or {}).get("surumler")) or []
        if sl:
            return p["urun_id"], sl[0]["id"], sl[0].get("ad")
    raise SystemExit("Sürümü olan ürün bulunamadı")


def seed(uid, sid):
    store.gorev_sync_items(uid, [
        {"id": "s1", "text": "Kartela renk eşlemesi tamamlansın", "durum": "acik", "oncelik": None, "surum_id": None},
        {"id": "s2", "text": "Numune dokuma planı çıkar", "durum": "yapiliyor", "oncelik": "orta", "surum_id": None},
        {"id": "s3", "text": "Müşteri brief'i arşivle", "durum": "tamamlandi", "oncelik": None, "surum_id": None},
        {"id": "s4", "text": "Atkı sıklığını 22→24 dene", "durum": "yapiliyor", "oncelik": "yuksek", "surum_id": sid},
        {"id": "s5", "text": "Kenar tahar grubunu revize et", "durum": "acik", "oncelik": "dusuk", "surum_id": sid},
    ])


def open_todo(page):
    """Teknik sekmesi → To-Do alt sekmesi (full sayfa veya embed)."""
    try:
        page.click('.utab-btn[data-tab="teknik"]', timeout=2500)
        page.wait_for_timeout(500)
    except Exception:
        pass  # embed modunda utab yok
    page.click('.numune-tab[data-numune-tab="todo"]', timeout=8000)
    page.wait_for_selector('.numune-section[data-numune-section="todo"]:not([hidden])', timeout=8000)
    page.wait_for_timeout(500)


def main():
    uid, sid, sad = pick_product()
    print(f"[i] ürün={uid} sürüm={sid} ({sad})")
    seed(uid, sid)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
            page = ctx.new_page()
            # giriş
            page.goto(f"{BASE}/login", wait_until="networkidle")
            page.fill('input[name="password"]', PW)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")

            # 20 — tam genişlik (teknik modülü)
            page.goto(f"{BASE}/urun/{uid}", wait_until="networkidle")
            page.wait_for_timeout(700)
            open_todo(page)
            page.locator('section[data-tab="teknik"]').screenshot(path=str(OUT / "20-todo-panel-v2.png"))
            print("[ok] 20-todo-panel-v2.png")

            # 20b — split (≤680px): embed=calisma-right, dar viewport → container query
            page.set_viewport_size({"width": 720, "height": 980})
            page.goto(f"{BASE}/urun/{uid}?embed=calisma-right", wait_until="networkidle")
            page.wait_for_timeout(700)
            open_todo(page)
            page.screenshot(path=str(OUT / "20b-todo-panel-680-v2.png"))
            print("[ok] 20b-todo-panel-680-v2.png")
            browser.close()
    finally:
        store.gorev_sync_items(uid, [])  # cleanup — net-sıfır
        print("[ok] cleanup (gorevler boşaltıldı)")


if __name__ == "__main__":
    main()
