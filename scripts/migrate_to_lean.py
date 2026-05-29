"""Tek seferlik migrasyon: markalar/urunler/*.json (v1.4 agir sema)
-> urunler/*.json (v2.0-lean manuel kuratorluk semasi).

DROP edilen bloklar: source_data, ai_inferences, image_analysis,
mobidik_evaluation (yalniz strategic_note -> arge_notu), data_quality,
approval_status, admin_decision, ml_score, _provenance.

Gorseller yerinde kalir; sadece JSON yeniden yazilir.
ANA CHECKOUT'ta calistir (gorseller/ orada). Eski JSON'lara dokunmaz.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Eski denetlenmis JSON'lar _arsiv/'e tasindi (Faz v3.0 manuel panel gecisi).
SRC_DIR = PROJECT_ROOT / "_arsiv" / "markalar_urunler_eski"
OUT_DIR = PROJECT_ROOT / "urunler"
GORSELLER_DIR = PROJECT_ROOT / "gorseller"
REPORT = OUT_DIR / "migration_report.txt"

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


COUNTRY_MAP = {
    "italy": "İtalya", "italya": "İtalya", "ıtalya": "İtalya", "italia": "İtalya",
    "turkey": "Türkiye", "türkiye": "Türkiye", "turkiye": "Türkiye",
    "germany": "Almanya", "almanya": "Almanya", "deutschland": "Almanya",
    "france": "Fransa", "fransa": "Fransa",
    "belgium": "Belçika", "belçika": "Belçika", "belgique": "Belçika",
    "usa": "ABD", "us": "ABD", "united states": "ABD", "abd": "ABD",
    "denmark": "Danimarka", "danimarka": "Danimarka",
    "sweden": "İsveç", "switzerland": "İsviçre", "schweiz": "İsviçre",
    "netherlands": "Hollanda", "holland": "Hollanda",
    "uk": "İngiltere", "united kingdom": "İngiltere", "england": "İngiltere",
    "india": "Hindistan", "hindistan": "Hindistan",
    "austria": "Avusturya", "österreich": "Avusturya",
}


def norm_country(c):
    """Ulke adini Turkce kanonik forma cevir (Italy -> Italya). Bilinmeyen oldugu gibi."""
    if not c:
        return None
    return COUNTRY_MAP.get(c.strip().lower(), c.strip())


def intify(v):
    """27.0 -> 27, 6 -> 6, 0 -> 0, null/'x' -> None."""
    if v is None:
        return None
    try:
        f = float(v)
        return int(f) if f == int(f) else f
    except (TypeError, ValueError):
        return None


def compose_str(comp) -> str | None:
    """source_data.technical.composition[] -> '%100 Keten' / '%70 Keten, %30 Pamuk'."""
    if not isinstance(comp, list) or not comp:
        return None
    parts = []
    for c in comp:
        if not isinstance(c, dict):
            continue
        fiber = c.get("fiber_generic") or c.get("fiber_commercial")
        ratio = c.get("ratio_percent")
        if fiber and ratio is not None:
            parts.append(f"%{ratio} {fiber}")
        elif fiber:
            parts.append(str(fiber))
    return ", ".join(parts) if parts else None


IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def build_code_to_name(sd: dict) -> dict[str, str]:
    """source_data.variants[] -> {renk_kodu_son_token: renk_adi} (disk fallback etiketi)."""
    out: dict[str, str] = {}
    for v in sd.get("variants", []) or []:
        if not isinstance(v, dict):
            continue
        cc = str(v.get("color_code") or "")
        name = v.get("color_name")
        if cc and name:
            out[cc.split("-")[-1]] = name
    return out


def scan_disk_dir(d: dict, sd: dict) -> list[dict]:
    """JSON yollari coozulmediginde urunun disk klasorunu tara (Kvadrat gibi
    bayat yol durumu). product_code ve urun_id ekinden klasor adayi dener."""
    brand_slug = d.get("brand_slug") or ""
    candidates = []
    if d.get("product_code"):
        candidates.append(str(d["product_code"]))
    uid = d.get("urun_id") or ""
    if "_" in uid:
        candidates.append(uid.split("_", 1)[1])  # orn. 5539-air-line
    code_to_name = build_code_to_name(sd)
    for cand in candidates:
        dpath = GORSELLER_DIR / brand_slug / cand
        if not dpath.is_dir():
            continue
        files = sorted(p for p in dpath.iterdir()
                       if p.is_file() and p.suffix.lower() in IMG_EXT)
        if not files:
            continue
        out = []
        for i, p in enumerate(files):
            code = p.stem.split("_")[0]
            rel = f"gorseller/{p.relative_to(GORSELLER_DIR).as_posix()}"
            out.append({
                "local_path": rel,
                "variant_label": code_to_name.get(code),
                "is_cover": i == 0,
                "order": i,
            })
        return out
    return []


def collect_images(d: dict, sd: dict, missing: list[str]) -> list[dict]:
    """images.main + variants + lifestyle + technical -> tek dizi.
    Sadece local_path + variant_label; ilk gorsel kapak (is_cover).
    JSON yollari hic cozulmezse disk klasorunu tarar (fallback)."""
    images_block = d.get("images", {})
    ordered: list[dict] = []
    seen: set[str] = set()
    if isinstance(images_block, dict):
        for bucket in ("main", "variants", "lifestyle", "technical"):
            for im in images_block.get(bucket, []) or []:
                if not isinstance(im, dict):
                    continue
                lp = im.get("local_path")
                if not lp or lp in seen:
                    continue
                seen.add(lp)
                if not (PROJECT_ROOT / lp).exists():
                    missing.append(lp)
                    continue
                label = im.get("variant_name") or im.get("color_name")
                ordered.append({
                    "local_path": lp,
                    "variant_label": label,
                    "is_cover": False,
                    "order": len(ordered),
                })
    if not ordered:
        # JSON yollari bayat -> diski tara
        recovered = scan_disk_dir(d, sd)
        if recovered:
            missing.clear()  # bayat yollar kurtarildi, raporu kirletme
        return recovered
    ordered[0]["is_cover"] = True
    return ordered


def migrate_one(d: dict, missing: list[str]) -> dict:
    sd = d.get("source_data", {}) if isinstance(d.get("source_data"), dict) else {}
    tech = sd.get("technical", {}) if isinstance(sd.get("technical"), dict) else {}
    commercial = sd.get("commercial", {}) if isinstance(sd.get("commercial"), dict) else {}
    me = d.get("mobidik_evaluation", {}) if isinstance(d.get("mobidik_evaluation"), dict) else {}
    repeat = tech.get("repeat_cm") if isinstance(tech.get("repeat_cm"), dict) else {}

    return {
        "_schema_version": "2.0-lean",
        "urun_id": d.get("urun_id"),
        "brand": d.get("brand"),
        "brand_slug": d.get("brand_slug"),
        "country": norm_country(commercial.get("country_of_origin")),
        "collection": d.get("collection"),
        "product_name": d.get("product_name"),
        "product_code": d.get("product_code"),
        "composition": compose_str(tech.get("composition")),
        "width_cm": tech.get("width_cm"),
        "weave_type": tech.get("weave_type_normalized") or tech.get("weave_type_raw"),
        "repeat_vertical_cm": intify(repeat.get("vertical")),
        "repeat_horizontal_cm": intify(repeat.get("horizontal")),
        "arge_notu": me.get("strategic_note"),
        "notes": None,
        "source_url": d.get("source_url"),
        "created_at": d.get("scraped_at") or NOW,
        "updated_at": NOW,
        "images": collect_images(d, sd, missing),
    }


def main() -> int:
    if not GORSELLER_DIR.exists():
        print(f"HATA: gorseller/ bulunamadi: {GORSELLER_DIR}")
        print("Bu script gorsellerin oldugu checkout'ta calistirilmali.")
        return 1
    if not SRC_DIR.exists():
        print(f"HATA: kaynak yok: {SRC_DIR}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report_lines: list[str] = [f"Migration {NOW}", ""]
    n_prod = 0
    n_img = 0
    all_missing: list[str] = []

    for jp in sorted(SRC_DIR.glob("*.json")):
        d = json.loads(jp.read_text(encoding="utf-8"))
        missing: list[str] = []
        lean = migrate_one(d, missing)
        out = OUT_DIR / f"{lean['urun_id']}.json"
        out.write_text(json.dumps(lean, ensure_ascii=False, indent=2), encoding="utf-8")
        n_prod += 1
        n_img += len(lean["images"])
        all_missing.extend(missing)
        cover = next((im["local_path"] for im in lean["images"] if im["is_cover"]), "(YOK)")
        report_lines.append(
            f"{lean['urun_id']}: {len(lean['images'])} gorsel, kapak={cover}"
            + (f", EKSIK={len(missing)}" if missing else "")
        )

    report_lines += ["", f"TOPLAM: {n_prod} urun, {n_img} gorsel"]
    if all_missing:
        report_lines += ["", "EKSIK GORSELLER (JSON referans veriyor ama diskte yok):"]
        report_lines += [f"  - {m}" for m in all_missing]
    REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"OK: {n_prod} urun -> {OUT_DIR}")
    print(f"   {n_img} gorsel, {len(all_missing)} eksik")
    print(f"   Rapor: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
