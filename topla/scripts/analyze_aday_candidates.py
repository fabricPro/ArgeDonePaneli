"""Faz 6.8: Aday URL'leri Mobidik kapasite filtresinden gecir.

Kapasite (kapasite/staubli_uretim_kapasitesi.md):
- TAM: dobby, leno, twill, pamuk/keten/viskon/polyester/yun, FR iplik
- Risk: outdoor (iplik), Trevira CS (tedarik), C2C/GRS (sertifika)
- YOK: jakar, metallic, max en > 360 cm

Slug'lardan ipucu cikarip kategorize et.
"""
import json
import re
import sys
from pathlib import Path

# Force UTF-8 stdout (Windows cp1254 cannot render emojis)
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Anahtar kelimeler
TAM = ["sheer", "twill", "leno", "linen", "lin", "wool", "alpaca", "cotton", "viscose", "silk"]
RISK = ["outdoor", "dim", "blackout"]
YOK = [
    "gold", "metallic", "metal", "lurex", "foil",
    "jacquard", "jakar", "velvet", "kadife",
]
# Mobidik ALTIN-ailesi (mevcut ALTIN urun benzerligi)
ALTIN_HINT = {
    "linen": "Anatolian Linen sub-brand (Air Line + Melange Linen + Nuri ailesi, 81-82 ALTIN)",
    "wool": "yun pazarinda Mobidik deneyimi var",
    "lin": "lin/keten",
    "sheer": "Air Line muadili, 81 ALTIN",
    "twill": "Pure White Pinstripe ailesi (81 ALTIN)",
    "leno": "Cobra ailesi (83 ALTIN, leno + FR sheer)",
    "outdoor": "ADO Capri Plus / Drift FR ailesi (87, 79 ALTIN)",
    "fire": "Cobra ailesi (83 ALTIN, FR sheer)",
    "fr": "Cobra ailesi (FR)",
    "stripe": "Pinstripe ailesi (81 ALTIN)",
    "pin": "Pinstripe ailesi",
    "color": "Color Fields sub-brand",
    "pure": "Pure White serisi (ADO ALTIN ailesi)",
    "alpaca": "Alpaca Leno ailesi (Kvadrat 73)",
    "air": "Air Line ailesi (81 ALTIN)",
}


def kategorize(slug: str) -> tuple[str, list[str]]:
    """Slug'i kategoriye sok."""
    s = slug.lower()
    reasons: list[str] = []
    risk_lvl = "ok"

    for kw in YOK:
        if kw in s:
            reasons.append(f"YOK: '{kw}'")
            risk_lvl = "yok"

    if risk_lvl != "yok":
        for kw in RISK:
            if kw in s:
                reasons.append(f"risk: '{kw}'")
                risk_lvl = "risk"

    for kw in TAM:
        if kw in s:
            reasons.append(f"TAM: '{kw}'")
            if risk_lvl == "ok":
                risk_lvl = "tam"

    # ALTIN hint
    for kw, hint in ALTIN_HINT.items():
        if kw in s:
            reasons.append(f"ALTIN benzer: {hint}")
            break

    return risk_lvl, reasons


def analyze(filepath: Path):
    d = json.loads(filepath.read_text(encoding="utf-8"))
    print(f"\n{'='*70}")
    print(f"  {filepath.name}")
    print(f"{'='*70}")
    for slug, r in d["marka_sonuclari"].items():
        if r.get("status") != "ok":
            continue
        print(f"\n--- {slug.upper()} ({r.get('display')}) — {r['yeni_aday_sayisi']} yeni ---\n")
        # Kategoriye gore grupla
        tam, risk, yok, diger = [], [], [], []
        for u in r["yeni_adaylar"]:
            risk_lvl, reasons = kategorize(u["slug"])
            row = {"slug": u["slug"], "key": u["key"], "url": u["url"], "reasons": reasons}
            if risk_lvl == "tam":
                tam.append(row)
            elif risk_lvl == "risk":
                risk.append(row)
            elif risk_lvl == "yok":
                yok.append(row)
            else:
                diger.append(row)

        if tam:
            print(f"  [TAM] TAM UYUM ({len(tam)} aday) — ALTIN benzer:")
            for row in tam:
                marker = ""
                hints = [r for r in row["reasons"] if "ALTIN benzer" in r]
                if hints:
                    marker = "  [ALTIN]"
                print(f"    {row['slug']}{marker}")
                for r in row["reasons"]:
                    print(f"      - {r}")

        if risk:
            print(f"\n  [RISK] RISK ({len(risk)} aday) — incelemeye deger:")
            for row in risk:
                print(f"    {row['slug']}")
                for r in row["reasons"]:
                    print(f"      - {r}")

        if yok:
            print(f"\n  [YOK] KAPASITE DISI ({len(yok)} aday) — atla:")
            for row in yok[:5]:
                print(f"    {row['slug']} ({', '.join(row['reasons'])})")
            if len(yok) > 5:
                print(f"    ... +{len(yok)-5} daha")

        if diger:
            print(f"\n  [?] ANAHTAR YOK ({len(diger)} aday) — slug'dan emin degil:")
            for row in diger[:10]:
                print(f"    {row['slug']}")
            if len(diger) > 10:
                print(f"    ... +{len(diger)-10} daha")


if __name__ == "__main__":
    for fp in sorted((PROJECT_ROOT / "topla" / "ham_cikti").glob("aday_*.json")):
        analyze(fp)
