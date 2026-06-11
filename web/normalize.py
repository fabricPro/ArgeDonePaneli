"""v4.0-part-2 Adım 8 — AI doldurma için birim çevirisi + elyaf kısaltma normalize.

Linkten-doldur akışında (Gemini API) yabancı sitelerden gelen:
  - "60 inch" → 152 (cm)
  - "8 oz/yd²" → 271 (g/m²)
  - "%50 PES, %50 CO" → "%50 Polyester, %50 Pamuk"

dönüşümlerini yapan saf Python helper'lar. Hem `app.py` (genel kullanım) hem
`gemini_extract.py` (linkten-doldur post-process) tarafından import edilir.
"""
from __future__ import annotations

import re


# ============================================================
# Elyaf kısaltma sözlüğü (ISO 1419 + yaygın varyantlar)
# ============================================================

FIBER_ABBR_TR: dict[str, str] = {
    # Sentetik
    "PES": "Polyester", "PL": "Polyester", "PET": "Polyester", "POL": "Polyester",
    "PA": "Poliamid", "NY": "Naylon", "PA6": "Poliamid", "PA66": "Poliamid",
    "AC": "Akrilik", "PAN": "Akrilik",
    "EA": "Elastan", "EL": "Elastan", "SP": "Elastan",
    "PP": "Polipropilen",
    # Doğal — bitkisel
    "CO": "Pamuk", "COT": "Pamuk",
    "LI": "Keten", "FL": "Keten", "LIN": "Keten",
    "RAM": "Rami",
    "JU": "Jüt", "JUT": "Jüt",
    "HE": "Kenevir", "HEM": "Kenevir",
    "BA": "Bambu", "BMB": "Bambu",
    # Doğal — hayvansal
    "WO": "Yün", "WV": "Yün", "WL": "Yün",
    "SI": "İpek", "SE": "İpek", "SLK": "İpek",
    "KA": "Kaşmir", "WS": "Kaşmir", "CSM": "Kaşmir",
    "MO": "Tiftik", "MHR": "Tiftik",  # Mohair
    "AL": "Alpaka", "ALP": "Alpaka",
    "AG": "Angora",
    # Yarı-sentetik (rejenere selüloz)
    "VI": "Viskon", "CV": "Viskon", "VIS": "Viskon", "RY": "Viskon",
    "CMD": "Modal", "MD": "Modal", "MAC": "Modal",
    "TEN": "Tencel",
    "LY": "Liyosel", "LYC": "Liyosel",
    "CA": "Asetat", "AC2": "Asetat",
    "CU": "Cupro",
    "RA": "Rejenere Selüloz",
}

# Tam İngilizce isimler — AI bazen kısaltma değil tam adı verir
FIBER_FULL_TR: dict[str, str] = {
    "polyester": "Polyester", "polyamide": "Poliamid", "polyamid": "Poliamid",
    "nylon": "Naylon", "acrylic": "Akrilik",
    "elastane": "Elastan", "spandex": "Elastan", "lycra": "Elastan",
    "polypropylene": "Polipropilen",
    "cotton": "Pamuk", "wool": "Yün", "silk": "İpek",
    "linen": "Keten", "flax": "Keten",
    "cashmere": "Kaşmir", "mohair": "Tiftik",
    "alpaca": "Alpaka", "angora": "Angora",
    "ramie": "Rami", "jute": "Jüt", "hemp": "Kenevir",
    "bamboo": "Bambu",
    "viscose": "Viskon", "rayon": "Viskon",
    "modal": "Modal", "tencel": "Tencel",
    "lyocell": "Liyosel", "acetate": "Asetat",
    "cupro": "Cupro",
    # Türkçe tam isimler — idempotent garanti (zaten Türkçe ise dokunma)
    "pamuk": "Pamuk", "yün": "Yün", "yun": "Yün",
    "ipek": "İpek", "i̇pek": "İpek",
    "keten": "Keten", "viskon": "Viskon",
    "polyester": "Polyester", "poliamid": "Poliamid",
    "akrilik": "Akrilik", "elastan": "Elastan",
    "kaşmir": "Kaşmir", "kasmir": "Kaşmir",
    "tiftik": "Tiftik", "alpaka": "Alpaka", "angora": "Angora",
    "kenevir": "Kenevir", "bambu": "Bambu", "modal": "Modal",
    "asetat": "Asetat", "polipropilen": "Polipropilen",
    "naylon": "Naylon",
}

# "Recycled X" / "rX" / "GRS X" → "Geri Dönüştürülmüş X"
# Uzun prefix'ler önce eşleştirilir; tek-harf "R" + kısaltma kombosu (rPES, rCO)
# _normalize_fiber_name içinde özel ele alınır.
RECYCLED_PREFIXES: tuple[str, ...] = (
    "GERİ DÖNÜŞTÜRÜLMÜŞ",
    "RECYCLED ", "RECYCLED-", "RECYCLED",
    "GRS ", "GRS-",
    "REC ", "REC-",
    "R-", "R ",
)


# ============================================================
# Genişlik birim çevirisi
# ============================================================

_WIDTH_RE = re.compile(
    r"(?P<num>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>cms?|mm|m\b|in\b|inch|inches|'|\"|″|′|mts?|meters?|metres?|metre)?",
    re.IGNORECASE,
)


def parse_width_cm(v) -> int | None:
    """Genişlik string'ini cm cinsinden int'e çevir.

    Örnekler:
        '60 inch'   → 152
        '60"'       → 152
        '1.5 m'     → 150
        '1500 mm'   → 150
        '152 cm'    → 152
        '152'       → 152  (birim yoksa cm varsayar)

    Range veya parse edilemezse None.
    """
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    # Range tespiti: "300-310 cm" gibi → null bırak (belirsizlik)
    if re.search(r"\d\s*[-–]\s*\d", s):
        return None
    m = _WIDTH_RE.search(s)
    if not m:
        return None
    try:
        num = float(m.group("num").replace(",", "."))
    except (ValueError, TypeError):
        return None
    unit = (m.group("unit") or "").lower().strip()
    if unit in ("in", "inch", "inches", '"', "''", "″"):
        num *= 2.54
    elif unit in ("m", "mt", "mts", "meter", "meters", "metre", "metres"):
        num *= 100
    elif unit == "mm":
        num /= 10
    # cm / cms / boş → as-is
    return int(round(num))


# ============================================================
# Gramaj birim çevirisi
# ============================================================

_GSM_RE = re.compile(
    r"(?P<num>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>g\s*/?\s*m[2²]?|gsm|gr/?m[2²]?|oz\s*/?\s*yd[2²]?|oz|kg\s*/?\s*m[2²]?)?",
    re.IGNORECASE,
)


def parse_weight_gsm(v) -> int | None:
    """Gramaj string'ini g/m² cinsinden int'e çevir.

    Örnekler:
        '8 oz/yd²'   → 271       (1 oz/yd² = 33.906 g/m²)
        '8oz/yd2'    → 271
        '180 g/m²'   → 180
        '180 gsm'    → 180
        '0.18 kg/m²' → 180
        '180'        → 180       (birim yoksa g/m² varsayar)

    Parse edilemezse None.
    """
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    # Range
    if re.search(r"\d\s*[-–]\s*\d", s):
        return None
    m = _GSM_RE.search(s)
    if not m:
        return None
    try:
        num = float(m.group("num").replace(",", "."))
    except (ValueError, TypeError):
        return None
    unit = (m.group("unit") or "").lower().replace(" ", "")
    if "oz" in unit:
        num *= 33.906  # oz/yd² → g/m²
    elif unit.startswith("kg"):
        num *= 1000
    # g/m² / gsm / boş → as-is
    return int(round(num))


# ============================================================
# Kompozisyon normalize (kısaltma → tam isim)
# ============================================================

# Tek bir parçada yüzde+elyaf eşleşmesi.
# Önce sırayı yakalar: "%50 PES" veya "50% PES" veya "PES 50%" veya "Cotton 60%"
# Dönüş: (pct_pre, fiber_pre, fiber_post, pct_post)
_COMPOSITION_FINDALL_RE = re.compile(
    r"(?:"
    r"%\s*(?P<pct_pre1>\d{1,3}(?:[.,]\d+)?)\s+(?P<fiber_a>[A-Za-zÇĞİıÖŞÜçğöşü][A-Za-zÇĞİıÖŞÜçğöşü\-]*)"
    r"|"
    r"(?P<pct_pre2>\d{1,3}(?:[.,]\d+)?)\s*%\s+(?P<fiber_b>[A-Za-zÇĞİıÖŞÜçğöşü][A-Za-zÇĞİıÖŞÜçğöşü\-]*)"
    r"|"
    r"(?P<fiber_c>[A-Za-zÇĞİıÖŞÜçğöşü][A-Za-zÇĞİıÖŞÜçğöşü\-]*)\s+(?P<pct_post>\d{1,3}(?:[.,]\d+)?)\s*%"
    r")",
    re.IGNORECASE,
)


def _normalize_fiber_name(name: str) -> str:
    """'PES' → 'Polyester'; 'cotton' → 'Pamuk'; 'rPES' → 'Geri Dönüştürülmüş Polyester'.

    Tanımadığı isimleri Title case bırakır (kullanıcı evidence'tan görebilir).
    """
    if not name:
        return ""
    s_orig = name.strip(" -.,")
    s = s_orig.upper()
    recycled = False
    # 1. Uzun recycled prefix'leri dene (en uzun önce gelsin)
    for pre in sorted(RECYCLED_PREFIXES, key=len, reverse=True):
        if s.startswith(pre):
            recycled = True
            s = s[len(pre):].strip(" -")
            break
    # 2. Uzun prefix yoksa, tek-harf "R" + kısaltma kombosunu dene (rPES, rCO, rPA...)
    if not recycled and len(s) >= 3 and s.startswith("R") and s[1:] in FIBER_ABBR_TR:
        recycled = True
        s = s[1:]
    # 3. Sözlükten ara
    if s in FIBER_ABBR_TR:
        result = FIBER_ABBR_TR[s]
    elif s.lower() in FIBER_FULL_TR:
        result = FIBER_FULL_TR[s.lower()]
    else:
        # Tanımadı → Title case (orijinal isim korunur)
        result = s_orig.title() if not recycled else s.title()
    if recycled:
        result = f"Geri Dönüştürülmüş {result}"
    return result


def normalize_composition(v) -> str | None:
    """Kompozisyon string'ini Türkçe tam isimli formatta normalize et.

    Örnekler:
        '%50 PES, %50 CO'          → '%50 Polyester, %50 Pamuk'
        '50% PES + 50% CO'         → '%50 Polyester, %50 Pamuk'
        '%100 LI'                  → '%100 Keten'
        '%80 rPES, %20 EA'         → '%80 Geri Dönüştürülmüş Polyester, %20 Elastan'
        '100% Wool'                → '%100 Yün'
        'Cotton 60% Linen 40%'     → '%60 Pamuk, %40 Keten'

    findall ile tüm (yüzde, elyaf) çiftlerini yakalar — ayraç gerekmez.
    Hiç eşleşme yoksa orijinali döner (data kaybı önler). Boş/None → None.
    """
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    out: list[str] = []
    seen: set[tuple[int, str]] = set()  # aynı (pct, fiber) çiftini bir kez ekle
    for m in _COMPOSITION_FINDALL_RE.finditer(s):
        pct = m.group("pct_pre1") or m.group("pct_pre2") or m.group("pct_post")
        fiber_raw = (m.group("fiber_a") or m.group("fiber_b") or m.group("fiber_c") or "").strip()
        if not pct or not fiber_raw:
            continue
        try:
            pct_val = int(round(float(pct.replace(",", "."))))
        except (ValueError, TypeError):
            continue
        fiber_norm = _normalize_fiber_name(fiber_raw)
        if not fiber_norm:
            continue
        key = (pct_val, fiber_norm)
        if key in seen:
            continue
        seen.add(key)
        out.append(f"%{pct_val} {fiber_norm}")
    if not out:
        return s  # Hiç parse edemediysek orijinali döndür
    return ", ".join(out)
