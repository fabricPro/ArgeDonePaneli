"""Faz 7.6: Mevcut tüm urunlere ML score doldur.

Inference modulunden predict_for_product cagir, urun JSON'larini guncelle.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from topla.ml.inference import predict_for_product

URUNLER = PROJECT_ROOT / "markalar" / "urunler"


def main():
    files = sorted(URUNLER.glob("*.json"))
    print(f"ML score doldurulacak: {len(files)} ürün\n")
    updated = 0
    for jp in files:
        d = json.loads(jp.read_text(encoding="utf-8"))
        score = predict_for_product(d)
        d["ml_score"] = score
        jp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        updated += 1
        prob = score.get("predicted_approval_prob")
        prob_str = f"{prob:.3f}" if prob is not None else "—"
        print(f"  ✓ {d['urun_id']:50s} prob={prob_str} conf={score.get('confidence', '—')}")

    print(f"\nToplam {updated} ürün ml_score güncellendi.")


if __name__ == "__main__":
    main()
