#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
backfill_family_fields.py — Ön Çalışma Havuzu: mevcut kayıtlar için family_key backfill
(Problem 1 — OnCalisma-V2). TEK SEFERLİK, NON-DESTRUCTIVE, IDEMPOTENT.

NEDEN
-----
Varyant tespiti (family_key/base_code/is_variant_candidate/variant_of) yalnız YENİ
ekleme akışına bağlıydı (compute_family_fields → research_add / api_arastirma_yakala).
Migration ÖNCESİ eklenmiş kayıtlarda kolon yoktu → research_insert _FAMILY_KEYS'i
strip ediyordu → bu 4 alan NULL kaldı. Bu script o eski kayıtları geriye dönük tarar
ve "tek tek eklenmiş gibi" sonuç verecek şekilde işaretler.

NE YAZAR / YAZMAZ
-----------------
- YALNIZCA 4 alanı yazar: family_key, base_code, is_variant_candidate, variant_of.
  (store.research_save — whitelist'siz generik yazıcı; başka alana DOKUNMAZ → Anayasa /
  görev #1 non-destructive doğal olarak sağlanır.)
- family_key'i ZATEN DOLU kayıtları ATLAR (migration sonrası doğru eklenmiş yeni
  kayıtları bozmaz → idempotent, #2). İki kez çalışsa da aynı sonuç.

TÜRETME MANTIĞI (#4 — tek kaynak)
---------------------------------
base_code / family_key türetimi MUTLAKA mevcut store.derive_base_code() ile yapılır
(kural kopyalanmaz). Varyant FLAG'i (kök vs aday) ise compute_family_fields /
research_find_family_siblings'in PENDING-SIBLING mantığının bellekte birebir
replikasıdır. compute_family_fields() per-row ÇAĞRILMAZ; çünkü o canlı DB'den pending
sibling sorgular, backfill sırasında family_key DB'de henüz NULL olduğundan herkesi
"kök" işaretlerdi. Toplu/bellek-içi gruplama, tek-tek eklemeyle AYNI sonucu verir.

STATUS (#5)
-----------
Tüm statüler (pending/imported/dismissed) taranır; family_key+base_code hepsine yazılır.
Varyant FLAG'i yalnız PENDING grubundan türetilir (research_find_family_siblings'in
.eq("status","pending") davranışıyla birebir). imported/dismissed kayıtlar gruplamaya
katılmaz → is_variant_candidate=False, variant_of=None (ama family_key/base_code dolar).

ÖNKOŞUL
-------
scripts/migrate_add_family_fields.sql Supabase'de UYGULANMIŞ olmalı (kolonlar var olmalı).
Uygulanmadıysa --apply net mesajla durur; --dry-run NULL kabul edip yine de önizleme basar.

KULLANIM
--------
    # Önizleme (yazma YOK — varsayılan):
    .venv/Scripts/python.exe scripts/backfill_family_fields.py
    # Gerçek yazma (yalnız sen çalıştır):
    .venv/Scripts/python.exe scripts/backfill_family_fields.py --apply
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

# Windows cp1254 konsol koruması (Türkçe/sembol çıktıda UnicodeEncodeError olmasın)
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

# --- Env + store import (scripts/upload_to_supabase.py konvansiyonu) -------------
from dotenv import load_dotenv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "web"))

import store  # noqa: E402  (env yüklendikten SONRA import edilmeli)

FAMILY_FIELDS = ("family_key", "base_code", "is_variant_candidate", "variant_of")


def _added_at_key(row: dict) -> str:
    """ISO string → kronolojik sıralama anahtarı (None/boş en başa)."""
    return row.get("added_at") or ""


def main() -> int:
    ap = argparse.ArgumentParser(
        description="research_pool mevcut kayıtları için family_key/base_code/variant backfill.",
    )
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--apply", action="store_true",
                   help="Gerçek yazma. Verilmezse DRY-RUN (hiçbir şey yazılmaz).")
    g.add_argument("--dry-run", action="store_true",
                   help="Açık dry-run (varsayılan davranış).")
    args = ap.parse_args()
    apply = bool(args.apply)  # --apply yoksa daima dry-run

    print("=" * 64)
    print("BACKFILL family_key — research_pool  (%s MODU)"
          % ("APPLY / YAZMA" if apply else "DRY-RUN / ÖNİZLEME"))
    print("=" * 64)

    # 1) Tüm kayıtları çek (tüm statüler) — research_list(select *), added_at DESC
    rows = store.research_list(status="all", limit=100000)
    total = len(rows)
    print("Toplam kayıt: %d" % total)
    if total == 0:
        print("Kayıt yok — çıkılıyor.")
        return 0

    # 2) Kolon kontrolü: hiçbir satırda family_key anahtarı yoksa migration uygulanmamış olabilir
    column_present = any("family_key" in r for r in rows)
    if not column_present:
        msg = ("UYARI: Satırlarda 'family_key' kolonu görünmüyor — migration "
               "(scripts/migrate_add_family_fields.sql) muhtemelen UYGULANMAMIŞ.")
        print(msg)
        if apply:
            print("APPLY DURDURULDU: Önce migration'ı Supabase'de uygula, sonra --apply.")
            return 2
        print("(DRY-RUN: tüm family_key'leri NULL kabul edip önizlemeye devam ediliyor.)")

    # 3) Partition + türetme
    to_process: list[dict] = []        # {id, added_at, status, base_code, family_key}
    skipped_already_filled = 0
    skipped_missing_data = 0
    skipped_no_base_code = 0

    # Gruplama havuzu: TÜM pending satırlar (family_key'i olan) — kök tespiti için.
    # (Zaten dolu pending satırlar OKUMA amaçlı katılır; ASLA yeniden yazılmaz.)
    pending_pool: list[dict] = []

    for r in rows:
        rid = r.get("id")
        status = r.get("status")
        existing_fk = (r.get("family_key") or "").strip()

        # Zaten dolu → atla (idempotent). Ama pending ise gruplama havuzuna OKUMA için ekle.
        if existing_fk:
            skipped_already_filled += 1
            if status == "pending":
                pending_pool.append({
                    "id": rid,
                    "added_at": r.get("added_at"),
                    "family_key": existing_fk,
                    "variant_of": r.get("variant_of"),
                })
            continue

        product_url = (r.get("product_url") or "").strip()
        brand_slug = (r.get("brand_slug") or "").strip()
        if not product_url or not brand_slug:
            skipped_missing_data += 1
            print("  ATLA (eksik veri): id=%s url=%r brand=%r"
                  % (rid, product_url[:60], brand_slug))
            continue

        base, fk = store.derive_base_code(product_url, brand_slug)
        if not fk or fk.endswith(":"):
            # base_code türetilemedi → gruplanamaz (research_find_family_siblings de yok sayar)
            skipped_no_base_code += 1
            print("  ATLA (base_code yok): id=%s url=%r" % (rid, product_url[:60]))
            continue

        item = {
            "id": rid,
            "added_at": r.get("added_at"),
            "status": status,
            "base_code": base or None,
            "family_key": fk,
        }
        to_process.append(item)
        if status == "pending":
            pending_pool.append({
                "id": rid,
                "added_at": r.get("added_at"),
                "family_key": fk,
                "variant_of": None,  # bu satır henüz yazılmadı
            })

    # 4) Pending grupları → kök tespiti (en eski = kök)
    groups: dict[str, list[dict]] = defaultdict(list)
    for m in pending_pool:
        groups[m["family_key"]].append(m)
    roots: dict[str, dict] = {}
    for fk, members in groups.items():
        members.sort(key=_added_at_key)  # en eski önce
        roots[fk] = members[0]

    # 5) to_process satırlarına varyant flag ata
    n_root = 0
    n_variant = 0
    n_nonpending = 0
    for item in to_process:
        if item["status"] != "pending":
            # imported/dismissed → gruplamaya katılmaz (canlı pending-only kuralı)
            item["is_variant_candidate"] = False
            item["variant_of"] = None
            n_nonpending += 1
            continue
        root = roots.get(item["family_key"])
        if root and root["id"] == item["id"]:
            item["is_variant_candidate"] = False
            item["variant_of"] = None
            n_root += 1
        elif root:
            item["is_variant_candidate"] = True
            item["variant_of"] = root.get("variant_of") or root["id"]
            n_variant += 1
        else:
            # teorik: pending ama gruba düşmedi (olmamalı) → kök gibi davran
            item["is_variant_candidate"] = False
            item["variant_of"] = None
            n_root += 1

    # 6) Özet
    print("-" * 64)
    print("İşlenecek (boş family_key):        %d" % len(to_process))
    print("  ├─ pending kök                   %d" % n_root)
    print("  ├─ pending varyant adayı         %d" % n_variant)
    print("  └─ imported/dismissed (flag yok) %d" % n_nonpending)
    print("Atlanan (zaten dolu):              %d" % skipped_already_filled)
    print("Atlanan (eksik url/brand):         %d" % skipped_missing_data)
    print("Atlanan (base_code türetilemedi):  %d" % skipped_no_base_code)

    distinct_families = {it["family_key"] for it in to_process}
    print("İşlenecek satırlardaki farklı aile: %d" % len(distinct_families))

    # Birden fazla pending üyesi olan aileler (gruplama havuzundan)
    multi = {fk: ms for fk, ms in groups.items() if len(ms) > 1}
    print("-" * 64)
    print(">1 pending üyeli aileler: %d" % len(multi))
    # base_code örneği için to_process'ten family_key→base_code haritası
    base_by_fk: dict[str, str] = {}
    for it in to_process:
        base_by_fk.setdefault(it["family_key"], it.get("base_code") or "?")
    for fk in sorted(multi, key=lambda k: -len(multi[k])):
        n = len(multi[fk])
        base_ex = base_by_fk.get(fk, fk.split(":", 1)[-1] or "?")
        print("  %s -> %d kayıt (1 kök + %d varyant adayı)  [base: %s]"
              % (fk, n, n - 1, base_ex))

    # 7) Yazma / dry-run
    print("=" * 64)
    if not apply:
        print("DRY-RUN — hiçbir şey yazılmadı. Gerçek uygulama için --apply ile çalıştırın.")
        print("NOT: base_code heuristiği JAB/Carlucci kalıpları (/NNN, -NNN) dışında")
        print("     yanlış-pozitif aile birleşmesi üretebilir. Non-destructive: kullanıcı")
        print("     sonradan variant_of ile ayırabilir. Önce dry-run çıktısını gözden geçirin.")
        return 0

    print("APPLY: %d satır güncelleniyor..." % len(to_process))
    updated = 0
    errors = 0
    for i, item in enumerate(to_process, 1):
        patch = {
            "family_key": item["family_key"],
            "base_code": item.get("base_code"),
            "is_variant_candidate": item["is_variant_candidate"],
            "variant_of": item["variant_of"],
        }
        tag = "VARYANT" if item["is_variant_candidate"] else "KOK"
        try:
            store.research_save(item["id"], patch)
            updated += 1
            print("  [%d/%d] %s -> %s [%s]"
                  % (i, len(to_process), item["id"], item["family_key"], tag))
        except Exception as e:  # noqa: BLE001
            errors += 1
            print("  [%d/%d] HATA id=%s: %s" % (i, len(to_process), item["id"], e))

    print("-" * 64)
    print("Güncellenen: %d   Hata: %d" % (updated, errors))
    print("Bitti. NOT: base_code heuristiği yanlış-pozitif üretebilir; gerekirse")
    print("variant_of ile elle ayırın (non-destructive).")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
