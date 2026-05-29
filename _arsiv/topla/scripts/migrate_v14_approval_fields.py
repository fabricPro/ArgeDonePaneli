"""Faz 7.1: Schema v1.3 → v1.4 migrate. 27 mevcut urun retroaktif 'approved'.

Mevcut urunler manuel denetim ile zaten admin tarafindan dogrulandi (Anayasa #6).
ML icin POZITIF training ornegi olarak ekle.

Yeni alanlar:
- approval_status.value = 'approved'
- admin_decision (date, by, notes, rejection_reasons[])
- ml_score (predicted_approval_prob=null cunku ML henuz eğitilmedi)

Kullanim:
    .venv\\Scripts\\python.exe topla\\scripts\\migrate_v14_approval_fields.py
"""
import json
import sys
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

URUNLER = PROJECT_ROOT / "markalar" / "urunler"
NOW = "2026-05-26T11:00:00Z"


def migrate_one(json_path: Path) -> bool:
    d = json.loads(json_path.read_text(encoding="utf-8"))
    if d.get("_schema_version") == "1.4" and "approval_status" in d:
        return False  # Zaten migrate edilmis

    d["_schema_version"] = "1.4"
    d["approval_status"] = {
        "value": "approved",
        "_history": "Faz 7.1 migrate (2026-05-26): Mevcut 27 urun retroaktif 'approved'. Anayasa #6 disiplini ile zaten manuel denetlendiler — ML icin pozitif training ornegi.",
    }
    d["admin_decision"] = {
        "status": "approved",
        "decision_date": NOW,
        "decision_by": "admin (retroaktif Faz 7.1 migrate)",
        "notes": (
            "Faz 7 oncesi denetim akisinda manuel Claude denetimi ile onaylandi. "
            "Web UI Faz 7.3 hazirlandiktan sonra yeni adaylar 'pending' olarak baslayacak."
        ),
        "rejection_reasons": [],
    }
    d["ml_score"] = {
        "predicted_approval_prob": None,
        "confidence": None,
        "similar_approved_products": [],
        "similar_rejected_products": [],
        "model_version": None,
        "predicted_at": None,
        "embedding_source": "dinov2_vitb14",
        "_note": "Faz 7.2'de DINOv2 embedding + sklearn ile doldurulacak. Su an placeholder.",
    }
    d["last_updated"] = NOW

    # audit_history entry
    audit_hist = d.setdefault("source_data", {}).setdefault("_provenance", {}).setdefault("audit_history", [])
    audit_hist.append({
        "audit_id": f"{d['urun_id']}_v14_schema_migrate_2026-05-26",
        "audit_date": "2026-05-26",
        "version_before": "v1.3 (approval_status alani yok)",
        "version_after": "v1.4 (approval_status=approved, ml_score placeholder)",
        "notes": "Faz 7.1 schema migration. Pozitif training ornegi olarak ML eğitiminde kullanilacak.",
    })

    json_path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def main():
    files = sorted(URUNLER.glob("*.json"))
    print(f"Migrate edilecek: {len(files)} urun")
    migrated = 0
    skipped = 0
    for fp in files:
        if migrate_one(fp):
            migrated += 1
            print(f"  ✓ {fp.name}")
        else:
            skipped += 1
            print(f"  - {fp.name} (zaten v1.4)")
    print(f"\nToplam: {migrated} migrate, {skipped} atlandi (zaten v1.4)")


if __name__ == "__main__":
    main()
