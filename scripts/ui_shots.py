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

        browser.close()
    print(f"\nÇıktı: {OUT}")


if __name__ == "__main__":
    sys.exit(main())
