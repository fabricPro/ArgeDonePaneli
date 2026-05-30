"""v3.6.1 — Renk isimlerini meodai (EN) → renkler.json (TR) ile değiştir.

Idempotent: HEX/RGB/LAB sabit kalır, sadece images[i].colors[role].name
yeniden hesaplanır. Aynı RGB → aynı Türkçe ad.

Kullanım (ana checkout'tan):
    .venv\\Scripts\\python.exe scripts\\migrate_color_names_to_tr.py

İlk çalıştırmada Drift FR'deki 8 İngilizce ad ('Mocha Latte', vs) Türkçe
karşılıklarına dönüşür ('Sütlü Kahve', vs). HEX değerleri sabit.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# Repo kökünden çağrılır → web/ klasörünü modül path'ine ekle
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import store


RENKLER_PATH = ROOT / "web" / "static" / "data" / "renkler.json"


# ============================================================
# Renk motoru — color-picker.js'in JavaScript karşılığı (birebir)
# ============================================================

def rgb_to_lab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """sRGB (0-255) → LAB (D65). color-picker.js rgbToLab birebir karşılığı."""
    r /= 255.0; g /= 255.0; b /= 255.0
    r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
    g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
    b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722)
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    def f(t: float) -> float:
        return t ** (1.0 / 3.0) if t > 0.008856 else (7.787 * t + 16.0 / 116.0)
    x = f(x); y = f(y); z = f(z)
    return (116.0 * y - 16.0, 500.0 * (x - y), 200.0 * (y - z))


def delta_e00(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    """CIEDE2000. color-picker.js deltaE00 birebir karşılığı."""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    avg_L = (L1 + L2) / 2.0
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    avg_C = (C1 + C2) / 2.0
    G = 0.5 * (1 - math.sqrt(avg_C**7 / (avg_C**7 + 25.0**7)))
    a1p = a1 * (1 + G); a2p = a2 * (1 + G)
    C1p = math.hypot(a1p, b1); C2p = math.hypot(a2p, b2)
    avg_Cp = (C1p + C2p) / 2.0

    def hue(x: float, y: float) -> float:
        hp = math.degrees(math.atan2(y, x))
        return hp + 360.0 if hp < 0 else hp

    h1p = hue(a1p, b1); h2p = hue(a2p, b2)
    dLp = L2 - L1
    dCp = C2p - C1p

    if C1p * C2p == 0:
        dhp = 0.0
    else:
        diff = h2p - h1p
        if abs(diff) <= 180:
            dhp = diff
        elif diff > 180:
            dhp = diff - 360
        else:
            dhp = diff + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2.0))

    if C1p * C2p == 0:
        avg_Hp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        avg_Hp = (h1p + h2p) / 2.0
    elif h1p + h2p < 360:
        avg_Hp = (h1p + h2p + 360) / 2.0
    else:
        avg_Hp = (h1p + h2p - 360) / 2.0

    T = (1
         - 0.17 * math.cos(math.radians(avg_Hp - 30))
         + 0.24 * math.cos(math.radians(2 * avg_Hp))
         + 0.32 * math.cos(math.radians(3 * avg_Hp + 6))
         - 0.20 * math.cos(math.radians(4 * avg_Hp - 63)))
    dRo = 30 * math.exp(-((avg_Hp - 275) / 25.0) ** 2)
    Rc = 2 * math.sqrt(avg_Cp**7 / (avg_Cp**7 + 25.0**7))
    Sl = 1 + (0.015 * (avg_L - 50) ** 2) / math.sqrt(20 + (avg_L - 50) ** 2)
    Sc = 1 + 0.045 * avg_Cp
    Sh = 1 + 0.015 * avg_Cp * T
    Rt = -math.sin(math.radians(2 * dRo)) * Rc

    return math.sqrt(
        (dLp / Sl) ** 2
        + (dCp / Sc) ** 2
        + (dHp / Sh) ** 2
        + Rt * (dCp / Sc) * (dHp / Sh)
    )


def load_dictionary() -> list[tuple[str, str, tuple[float, float, float]]]:
    """renkler.json → [(ad, hex, lab), ...]. LAB önhesap."""
    data = json.loads(RENKLER_PATH.read_text(encoding="utf-8"))
    out = []
    for c in data:
        ad = c.get("ad") or c.get("name") or "—"
        hex_ = (c.get("hex") or "").upper()
        rgb = c.get("rgb")
        if not rgb and hex_:
            s = hex_.lstrip("#")
            rgb = [int(s[i:i+2], 16) for i in (0, 2, 4)]
        if not rgb:
            continue
        out.append((ad, hex_, rgb_to_lab(*rgb)))
    return out


def nearest_tr(rgb: list[int], dict_lab: list) -> tuple[str, float]:
    """En yakın Türkçe renk adı + ΔE."""
    target = rgb_to_lab(*rgb)
    best_name, best_de = "—", float("inf")
    for ad, _hex, lab in dict_lab:
        de = delta_e00(target, lab)
        if de < best_de:
            best_de = de
            best_name = ad
    return best_name, best_de


# ============================================================
# Migration
# ============================================================

def main() -> int:
    print("v3.6.1 — Renk adlarını Türkçeleştir")
    print("=" * 50)

    if not RENKLER_PATH.exists():
        print(f"HATA: {RENKLER_PATH} bulunamadı")
        return 1

    dict_lab = load_dictionary()
    print(f"  Sözlük: {len(dict_lab)} renk yüklendi")

    products = store.get_all()
    print(f"  Ürün: {len(products)} tarama başlıyor\n")

    updated_count = 0
    color_count = 0

    for d in products:
        urun_id = d.get("urun_id") or "?"
        changed = False
        per_product_changes = 0
        for im in (d.get("images") or []):
            colors = im.get("colors") or {}
            if not isinstance(colors, dict):
                continue
            for role in ("weft", "warp", "mix"):
                c = colors.get(role)
                if not isinstance(c, dict):
                    continue
                rgb = c.get("rgb")
                if not isinstance(rgb, list) or len(rgb) != 3:
                    continue
                old_name = c.get("name") or c.get("nearest") or ""
                new_name, new_de = nearest_tr(rgb, dict_lab)
                if new_name != old_name:
                    c["name"] = new_name
                    # delta_e de yeniden hesaplandı (sözlük değişti)
                    c["delta_e"] = round(new_de, 2)
                    changed = True
                    per_product_changes += 1
                    color_count += 1
        if changed:
            store.upsert(d)
            updated_count += 1
            print(f"  ✓ {urun_id}: {per_product_changes} renk güncellendi")

    print("\n" + "=" * 50)
    print(f"Toplam: {updated_count} ürün, {color_count} renk Türkçeleştirildi")
    print("Idempotent — tekrar çalıştırılabilir, değişiklik olmaz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
