#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
backfill_renk_id.py — İplik Kataloğu: nested renk objelerine KALICI renk_id backfill
(Senkron modülü önkoşulu). TEK SEFERLİK, NON-DESTRUCTIVE, IDEMPOTENT.

NEDEN
-----
Renk kimliği eskiden pozisyonel "numara" idi ve her kayıtta yeniden yazılıyordu →
demirleme (Senkron iplik havuzu) için kırılgan. Sayfa nasıl kalıcı sayfa_id taşıyorsa,
renk de kalıcı renk_id taşımalı. Sunucu artık her yazımda renk_id garanti ediyor
(store.upsert_kartela → store.ensure_renk_ids), ama renk_id eklenmeden ÖNCE
oluşturulmuş eski renkler hâlâ renk_id'siz olabilir. Bu script onları geriye dönük damgalar.

NE YAZAR / YAZMAZ
-----------------
- YALNIZCA renk_id EKSİK/boş olan nested renge yeni id (uuid hex[:12]) basar.
- Mevcut renk_id, numara, ad, hex, kod, rgb, lab, secim_noktasi, foto_path, sayfa_id —
  HİÇBİRİNE dokunmaz (store.ensure_renk_ids yalnız renk_id alanını ekler).
- renk_id'si ZATEN dolu renkleri ATLAR → idempotent (#3): ikinci çalıştırma 0 değişiklik.
- Damga gerektiren renk yoksa o kartela'yı upsert ETMEZ (gereksiz guncelleme_tarihi bump yok).

TEK KAYNAK (#1 ile aynı mantık)
-------------------------------
Damgalama store.ensure_renk_ids() ile yapılır (sunucu yazma yoluyla BİREBİR aynı fonksiyon;
kural kopyalanmaz). uuid formatı sunucudaki ile aynı: uuid4().hex[:12].

ÖNKOŞUL
-------
Yeni KOLON gerekmez (renk zaten sayfalar jsonb içinde nested). Şema değişmez.

KULLANIM
--------
    # Önizleme (yazma YOK — varsayılan):
    .venv/Scripts/python.exe scripts/backfill_renk_id.py
    # Gerçek yazma (yalnız sen çalıştır):
    .venv/Scripts/python.exe scripts/backfill_renk_id.py --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Windows cp1254 konsol koruması (Türkçe/sembol çıktıda UnicodeEncodeError olmasın)
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

# --- Env + store import (scripts/backfill_family_fields.py konvansiyonu) ----------
from dotenv import load_dotenv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "web"))

import store  # noqa: E402  (env yüklendikten SONRA import edilmeli)


def count_missing(sayfalar) -> tuple[int, int]:
    """(toplam_renk, renk_id_eksik) sayar — mutasyon YOK (dry-run için)."""
    total = missing = 0
    for s in (sayfalar or []):
        if not isinstance(s, dict):
            continue
        for r in (s.get("renkler") or []):
            if not isinstance(r, dict):
                continue
            total += 1
            if not str(r.get("renk_id") or "").strip():
                missing += 1
    return total, missing


def main() -> int:
    ap = argparse.ArgumentParser(
        description="iplik_kartelalari nested renkler[] için kalıcı renk_id backfill.",
    )
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--apply", action="store_true",
                   help="Gerçek yazma. Verilmezse DRY-RUN (hiçbir şey yazılmaz).")
    g.add_argument("--dry-run", action="store_true",
                   help="Açık dry-run (varsayılan davranış).")
    args = ap.parse_args()
    apply = bool(args.apply)

    print("=" * 64)
    print("BACKFILL renk_id — iplik_kartelalari  (%s MODU)"
          % ("APPLY / YAZMA" if apply else "DRY-RUN / ÖNİZLEME"))
    print("=" * 64)

    rows = store.list_kartelalar()
    print("Toplam kartela: %d" % len(rows))
    if not rows:
        print("Kartela yok — çıkılıyor.")
        return 0

    total_renk = 0
    total_missing = 0
    kartela_to_fix: list[dict] = []
    for k in rows:
        t, m = count_missing(k.get("sayfalar"))
        total_renk += t
        total_missing += m
        if m > 0:
            kartela_to_fix.append(k)
            print("  %s (%s): %d renk, %d eksik"
                  % (k.get("kartela_id"), (k.get("ad") or "")[:30], t, m))

    print("-" * 64)
    print("Toplam renk:            %d" % total_renk)
    print("renk_id eksik:          %d" % total_missing)
    print("Damga gereken kartela:  %d" % len(kartela_to_fix))

    if total_missing == 0:
        print("=" * 64)
        print("Tüm renkler zaten renk_id taşıyor — yapılacak iş yok (idempotent).")
        return 0

    print("=" * 64)
    if not apply:
        print("DRY-RUN — hiçbir şey yazılmadı. Gerçek uygulama için --apply ile çalıştırın.")
        return 0

    print("APPLY: %d kartela güncelleniyor..." % len(kartela_to_fix))
    stamped_total = 0
    updated = 0
    errors = 0
    for i, k in enumerate(kartela_to_fix, 1):
        # store.ensure_renk_ids: sunucu ile BİREBİR aynı damgalama (in-place, yalnız eksik).
        n = store.ensure_renk_ids(k.get("sayfalar"))
        try:
            store.upsert_kartela(k)   # upsert içinde de ensure çağrılır → no-op (zaten damgalı)
            stamped_total += n
            updated += 1
            print("  [%d/%d] %s -> %d renk damgalandı"
                  % (i, len(kartela_to_fix), k.get("kartela_id"), n))
        except Exception as e:  # noqa: BLE001
            errors += 1
            print("  [%d/%d] HATA %s: %s" % (i, len(kartela_to_fix), k.get("kartela_id"), e))

    print("-" * 64)
    print("Güncellenen kartela: %d   Damgalanan renk: %d   Hata: %d"
          % (updated, stamped_total, errors))
    print("Bitti. Tekrar çalıştırırsanız 0 değişiklik beklenir (idempotent).")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
