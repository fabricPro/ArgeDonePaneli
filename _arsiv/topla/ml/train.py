"""Faz 7.2: ML model eğitimi — cold start + active learning retrain.

Kullanim:
    python -m topla.ml.train          # cold start (varsayılan)
    python -m topla.ml.train --active # feedback_log'tan retrain
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from topla.ml.features import extract_features
from topla.ml.model import (
    ML_DIR, load_latest_model, save_model, train_active, train_cold_start,
)

URUNLER_DIR = PROJECT_ROOT / "markalar" / "urunler"
FEEDBACK_LOG = ML_DIR / "feedback_log.jsonl"


def load_positives() -> tuple[list[str], np.ndarray]:
    """Approved ürünlerin feature matrisi."""
    ids: list[str] = []
    rows: list[np.ndarray] = []
    for jp in sorted(URUNLER_DIR.glob("*.json")):
        d = json.loads(jp.read_text(encoding="utf-8"))
        approval = d.get("approval_status", {})
        status = approval.get("value") if isinstance(approval, dict) else approval
        if status != "approved":
            continue
        ids.append(d["urun_id"])
        rows.append(extract_features(d))
    return ids, np.array(rows) if rows else np.empty((0, 26))


def load_negatives() -> tuple[list[str], np.ndarray]:
    """Rejected ürünlerin feature matrisi."""
    ids: list[str] = []
    rows: list[np.ndarray] = []
    for jp in sorted(URUNLER_DIR.glob("*.json")):
        d = json.loads(jp.read_text(encoding="utf-8"))
        approval = d.get("approval_status", {})
        status = approval.get("value") if isinstance(approval, dict) else approval
        if status != "rejected":
            continue
        ids.append(d["urun_id"])
        rows.append(extract_features(d))
    return ids, np.array(rows) if rows else np.empty((0, 26))


def next_version() -> str:
    """En son model versiyonundan bir sonraki."""
    pipe, latest = load_latest_model()
    if not latest:
        return "v1"
    # latest "v3" → 4
    try:
        n = int(latest.lstrip("v")) + 1
        return f"v{n}"
    except Exception:
        return "v1"


def train_and_save(mode: str = "cold_start") -> dict:
    pos_ids, X_pos = load_positives()
    neg_ids, X_neg = load_negatives()

    print(f"Pozitif (approved): {len(pos_ids)}")
    print(f"Negatif (rejected): {len(neg_ids)}")

    if len(pos_ids) == 0:
        print("HATA: Hiç approved ürün yok. Önce migrate çalıştır.")
        return {}

    if mode == "cold_start" or len(neg_ids) == 0:
        print(f"Mod: cold_start (synthetic negatives)")
        pipe, metrics = train_cold_start(X_pos, n_synthetic=max(20, len(X_pos)))
    else:
        print(f"Mod: active_learning ({len(neg_ids)} gerçek red)")
        pipe, metrics = train_active(X_pos, X_neg)

    version = next_version()
    metrics["positive_product_ids"] = pos_ids
    metrics["negative_product_ids"] = neg_ids if mode == "active_learning" else []

    model_path, metrics_path = save_model(pipe, version, metrics)
    print(f"\nKaydedildi:")
    print(f"  {model_path.relative_to(PROJECT_ROOT)}")
    print(f"  {metrics_path.relative_to(PROJECT_ROOT)}")
    print(f"\nMetrikler:")
    print(f"  Precision (in-sample): {metrics['in_sample_precision']:.3f}")
    print(f"  Recall (in-sample):    {metrics['in_sample_recall']:.3f}")
    print(f"  F1 (in-sample):        {metrics['in_sample_f1']:.3f}")

    return metrics


def main():
    mode = "cold_start"
    if "--active" in sys.argv:
        mode = "active_learning"
    train_and_save(mode)


if __name__ == "__main__":
    main()
