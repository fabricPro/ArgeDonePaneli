"""Faz 6.3: Haftalik oz-degerlendirme — son 7 gunluk ozet rapor.

CLAUDE.md kadansi: Cumartesi 09:00'da scheduled task tarafindan calistirilir.
Cikti: docs/haftalik_oz_degerlendirme_<YYYY-MM-DD>.md

Script SADECE mekanik veri toplar (Anayasa #9):
- markalar/urunler/*.json -> son 7 gunde mtime degisenler
- audit_history -> son 7 gunde yazilan kayitlar
- gorseller/ -> son 7 gunde yeni dosyalar
- git log --since='7 days ago' -> commit aktivitesi
- topla/ham_cikti/aday_*.json -> son 7 gun bulunan adaylar

Yorum / oneri / strategic plan: Claude oturumunda doldurulur.
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
URUNLER_DIR = PROJECT_ROOT / "markalar" / "urunler"
MARKALAR_DIR = PROJECT_ROOT / "markalar"
GORSELLER_DIR = PROJECT_ROOT / "gorseller"
HAM_CIKTI_DIR = PROJECT_ROOT / "topla" / "ham_cikti"
DOCS_DIR = PROJECT_ROOT / "docs"

DAYS = 7


def son_n_gun_iso(n: int = DAYS) -> str:
    threshold = datetime.now(timezone.utc) - timedelta(days=n)
    return threshold.isoformat()


def son_n_gun_unix(n: int = DAYS) -> float:
    return (datetime.now(timezone.utc) - timedelta(days=n)).timestamp()


def degisen_urunler() -> list[dict]:
    """Son 7 gunde mtime degisen markalar/urunler/*.json'lar."""
    cutoff = son_n_gun_unix()
    sonuc = []
    for jp in sorted(URUNLER_DIR.glob("*.json")):
        mtime = jp.stat().st_mtime
        if mtime < cutoff:
            continue
        with jp.open(encoding="utf-8") as f:
            d = json.load(f)
        sonuc.append({
            "urun_id": d.get("urun_id"),
            "brand": d.get("brand"),
            "product_name": d.get("product_name"),
            "overall_score": (d.get("mobidik_evaluation") or {}).get("overall_score"),
            "last_updated": d.get("last_updated"),
            "mtime_iso": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
            "dosya": str(jp.relative_to(PROJECT_ROOT)),
        })
    return sonuc


def son_audit_kayitlari() -> list[dict]:
    """Audit_history'de son 7 gunde audit_date'i olan kayitlar."""
    cutoff_iso = son_n_gun_iso()
    cutoff_date = cutoff_iso[:10]  # YYYY-MM-DD
    sonuc = []
    for jp in sorted(URUNLER_DIR.glob("*.json")):
        with jp.open(encoding="utf-8") as f:
            d = json.load(f)
        audit_hist = (
            d.get("source_data", {})
             .get("_provenance", {})
             .get("audit_history", [])
        )
        for entry in audit_hist:
            audit_date = entry.get("audit_date", "")
            if audit_date >= cutoff_date:
                sonuc.append({
                    "urun_id": d.get("urun_id"),
                    "audit_id": entry.get("audit_id"),
                    "audit_date": audit_date,
                    "notes": (entry.get("notes") or "")[:200],
                })
    return sorted(sonuc, key=lambda x: x["audit_date"], reverse=True)


def yeni_gorseller_sayisi() -> dict[str, int]:
    """Marka basina son 7 gunde olusturulan/degisen gorsel sayisi."""
    cutoff = son_n_gun_unix()
    sayim: dict[str, int] = {}
    if not GORSELLER_DIR.exists():
        return sayim
    for brand_dir in GORSELLER_DIR.iterdir():
        if not brand_dir.is_dir():
            continue
        n = 0
        for img in brand_dir.rglob("*.jpg"):
            if img.stat().st_mtime >= cutoff:
                n += 1
        if n > 0:
            sayim[brand_dir.name] = n
    return sayim


def git_log_son_7_gun() -> list[str]:
    """git log --since='7 days ago' --oneline"""
    try:
        r = subprocess.run(
            ["git", "log", f"--since={DAYS} days ago", "--oneline", "--no-decorate"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0:
            return [f"(git log hata: {r.stderr.strip()[:120]})"]
        lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
        return lines
    except FileNotFoundError:
        return ["(git CLI bulunamadi)"]
    except Exception as e:
        return [f"(hata: {e})"]


def son_aday_taramalari() -> list[dict]:
    """ham_cikti/aday_*.json son 7 gunde olusturulanlar."""
    cutoff = son_n_gun_unix()
    if not HAM_CIKTI_DIR.exists():
        return []
    sonuc = []
    for jp in sorted(HAM_CIKTI_DIR.glob("aday_*.json")):
        if jp.stat().st_mtime < cutoff:
            continue
        try:
            with jp.open(encoding="utf-8") as f:
                d = json.load(f)
            sonuc.append({
                "dosya": jp.name,
                "region": d.get("region"),
                "timestamp": d.get("timestamp"),
                "toplam_yeni_aday": d.get("toplam_yeni_aday", 0),
                "toplam_bilinen": d.get("toplam_bilinen", 0),
                "hata_sayisi": d.get("hata_sayisi", 0),
            })
        except Exception:
            continue
    return sorted(sonuc, key=lambda x: x.get("timestamp") or "", reverse=True)


def yazi_olustur() -> str:
    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bugun_iso = datetime.now(timezone.utc).isoformat()

    degisen = degisen_urunler()
    auditler = son_audit_kayitlari()
    gorsel = yeni_gorseller_sayisi()
    git_lines = git_log_son_7_gun()
    aday_taramalari = son_aday_taramalari()

    md = []
    md.append(f"# Haftalik Oz-Degerlendirme — {bugun}")
    md.append("")
    md.append(f"**Olusturuldu:** {bugun_iso}")
    md.append(f"**Kapsama:** son {DAYS} gun")
    md.append("")
    md.append("> ⓘ Bu rapor `topla/scripts/weekly_review.py` tarafindan otomatik olusturulur.")
    md.append("> Sadece mekanik veri toplar (Anayasa #9). Yorum + onerileri Claude oturumunda doldur.")
    md.append("")
    md.append("---")
    md.append("")

    # 1. Degisen urunler
    md.append("## 1. Degisen Urunler")
    md.append("")
    if degisen:
        md.append(f"Son {DAYS} gunde {len(degisen)} urun JSON dosyasi guncellendi:")
        md.append("")
        md.append("| Urun ID | Marka | Urun Adi | Skor | Son Guncelleme |")
        md.append("|---|---|---|---|---|")
        for u in degisen:
            md.append(
                f"| {u['urun_id']} | {u['brand']} | {u['product_name']} | "
                f"{u['overall_score']} | {u['last_updated']} |"
            )
    else:
        md.append(f"Son {DAYS} gunde markalar/urunler/ altinda degisiklik yok.")
    md.append("")

    # 2. Audit kayitlari
    md.append("## 2. Yeni Audit Kayitlari")
    md.append("")
    if auditler:
        md.append(f"Son {DAYS} gunde {len(auditler)} audit_history entry kaydedildi:")
        md.append("")
        for a in auditler:
            md.append(f"- **{a['audit_date']}** `{a['urun_id']}` ({a['audit_id']})")
            if a["notes"]:
                md.append(f"  - {a['notes']}")
    else:
        md.append("Yeni audit kaydi yok.")
    md.append("")

    # 3. Gorsel degisiklikleri
    md.append("## 3. Gorsel Degisiklikleri")
    md.append("")
    if gorsel:
        toplam = sum(gorsel.values())
        md.append(f"Son {DAYS} gunde {toplam} yeni/degisen gorsel:")
        md.append("")
        for marka, n in sorted(gorsel.items(), key=lambda x: -x[1]):
            md.append(f"- **{marka}**: {n} dosya")
    else:
        md.append("Yeni gorsel yok.")
    md.append("")

    # 4. Git aktivite
    md.append("## 4. Git Aktivite")
    md.append("")
    if git_lines:
        md.append(f"Son {DAYS} gunluk commitler ({len(git_lines)} adet):")
        md.append("")
        md.append("```")
        for ln in git_lines[:30]:
            md.append(ln)
        if len(git_lines) > 30:
            md.append(f"... +{len(git_lines) - 30} commit daha")
        md.append("```")
    else:
        md.append("Commit yok.")
    md.append("")

    # 5. Aday tarama
    md.append("## 5. Aday Tarama Sonuclari (topla --batch)")
    md.append("")
    if aday_taramalari:
        md.append(f"Son {DAYS} gunde {len(aday_taramalari)} batch tarama calistirildi:")
        md.append("")
        md.append("| Tarih | Bolge | Yeni Aday | Bilinen | Hata |")
        md.append("|---|---|---|---|---|")
        for a in aday_taramalari:
            md.append(
                f"| {(a.get('timestamp') or '')[:10]} | {a['region']} | "
                f"{a['toplam_yeni_aday']} | {a['toplam_bilinen']} | {a['hata_sayisi']} |"
            )
    else:
        md.append("Bu hafta batch tarama yok.")
    md.append("")

    # 6. Claude doldursun
    md.append("---")
    md.append("")
    md.append("## 6. Yorum & Sonraki Adimlar — Claude Doldurmali")
    md.append("")
    md.append("> Bu bolum Claude Code oturumunda elle doldurulur.")
    md.append("> Sorular:")
    md.append("> - Bu hafta hangi konuya en cok zaman ayrildi?")
    md.append("> - Hangi bulgular stratejik onem tasiyor?")
    md.append("> - Sonraki hafta icin oncelik ne?")
    md.append("> - Anayasa ihlali / celiski yakalandi mi?")
    md.append("")
    md.append("(boş — Claude oturumunda doldur)")
    md.append("")
    md.append("---")
    md.append("")
    md.append(f"_Rapor sonu — {bugun_iso}_")
    md.append("")

    return "\n".join(md)


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = DOCS_DIR / f"haftalik_oz_degerlendirme_{bugun}.md"
    text = yazi_olustur()
    out_path.write_text(text, encoding="utf-8")
    print(f"Yazildi: {out_path.relative_to(PROJECT_ROOT)}")
    print(f"Boyut: {len(text)} kar")


if __name__ == "__main__":
    main()
