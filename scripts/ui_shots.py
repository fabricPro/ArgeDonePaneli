"""tasarim-v2 — UI screenshot aracı (Playwright). Dev-only, requirements'a girmez.

Çalıştırma: Flask localhost:5000'de açıkken
  .venv/Scripts/python.exe scripts/ui_shots.py

Çıktı: ui-shots/01-galeri-v2.png, 02-galeri-liste-v2.png, 10-ayarlar-v2.png
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("FAS_BASE", "http://localhost:5000")
PW = os.environ.get("APP_PASSWORD", "Katyonik<312")
# tasarim-v2 Faz 2 — örnek ürün (detay kabuğu screenshot'ı için)
URUN = os.environ.get("FAS_URUN", "zimmer_rohde_11047-ishari")
# tasarim-v2 Faz 3 — teknik verisi (sürüm) olan örnek ürün
TEKNIK = os.environ.get("FAS_TEKNIK", "ado_goldkante_3301-pure-white-pinstripe")
OUT = Path(__file__).resolve().parent.parent / "ui-shots"
OUT.mkdir(exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 860},
                                  device_scale_factor=2)
        page = ctx.new_page()

        # Giriş
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.fill('input[name="password"]', PW)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        # 01 — Galeri grid
        page.goto(f"{BASE}/", wait_until="networkidle")
        page.wait_for_timeout(1200)  # görseller
        page.screenshot(path=str(OUT / "01-galeri-v2.png"))
        print("[ok] 01-galeri-v2.png")

        # 02 — Galeri liste
        page.click('.view-btn[data-mode="list"]')
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / "02-galeri-liste-v2.png"))
        print("[ok] 02-galeri-liste-v2.png")
        # geri grid'e al (localStorage kalmasın)
        page.click('.view-btn[data-mode="grid"]')

        # 10 — Ayarlar
        page.goto(f"{BASE}/ayarlar", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "10-ayarlar-v2.png"))
        print("[ok] 10-ayarlar-v2.png")

        # 11 — Ürün detay (Galeri sekmesi) — Faz 2 kabuğu, üst görünüm
        page.goto(f"{BASE}/urun/{URUN}", wait_until="networkidle")
        page.wait_for_timeout(1500)  # hero + palet + grid görselleri yüklensin
        page.screenshot(path=str(OUT / "11-urun-galeri-v2.png"))
        print("[ok] 11-urun-galeri-v2.png")

        # 17 — Ürün detay — tam sayfa (hero → künye → palet → görsel grid)
        page.screenshot(path=str(OUT / "17-urun-detay-v2.png"), full_page=True)
        print("[ok] 17-urun-detay-v2.png")

        # === Teknik Analiz modülü (Faz 3) — teknik verisi olan üründe ===
        page.goto(f"{BASE}/urun/{TEKNIK}", wait_until="networkidle")
        page.wait_for_timeout(800)
        page.click('.utab-btn[data-tab="teknik"]')
        page.wait_for_timeout(700)
        tek = page.locator('section[data-tab="teknik"]')

        # 12 — Gramaj & Maliyet (analiz alt sekmesi)
        page.click('.numune-tab[data-numune-tab="analiz"]')
        page.wait_for_timeout(900)
        tek.screenshot(path=str(OUT / "12-teknik-gramaj-v2.png"))
        print("[ok] 12-teknik-gramaj-v2.png")

        # 13 — Desen & Tahar alt sekmesi (Faz 4)
        page.click('.numune-tab[data-numune-tab="desen"]')
        page.wait_for_timeout(800)
        tek.screenshot(path=str(OUT / "13-teknik-desen-v2.png"))
        print("[ok] 13-teknik-desen-v2.png")

        # 14 — Tarak alt sekmesi
        page.click('.numune-tab[data-numune-tab="tarak"]')
        page.wait_for_timeout(700)
        tek.screenshot(path=str(OUT / "14-teknik-tarak-v2.png"))
        print("[ok] 14-teknik-tarak-v2.png")

        # 16 — Notlar alt sekmesi
        page.click('.numune-tab[data-numune-tab="notlar"]')
        page.wait_for_timeout(600)
        tek.screenshot(path=str(OUT / "16-teknik-notlar-v2.png"))
        print("[ok] 16-teknik-notlar-v2.png")

        # 15 — Plan alt sekmesi (Faz 5)
        page.click('.numune-tab[data-numune-tab="plan"]')
        page.wait_for_timeout(800)
        tek.screenshot(path=str(OUT / "15-teknik-plan-v2.png"))
        print("[ok] 15-teknik-plan-v2.png")

        browser.close()
    print(f"\nÇıktı: {OUT}")


if __name__ == "__main__":
    sys.exit(main())
