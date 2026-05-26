"""Faz 7.2: ML inference — yeni aday için tahmin + benzer ürün.

Kullanim:
    from topla.ml.inference import predict_for_product
    score = predict_for_product(urun_json_dict)
    # score = {
    #   "predicted_approval_prob": 0.78,
    #   "confidence": "medium",
    #   "similar_approved_products": ["dedar_00T19031-...", ...],
    #   "model_version": "v2"
    # }
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from topla.ml.features import extract_features, extract_features_from_path
from topla.ml.model import load_latest_model

PROJECT_ROOT = Path(__file__).resolve().parents[2]
URUNLER_DIR = PROJECT_ROOT / "markalar" / "urunler"


def _confidence_from_prob(prob: float) -> str:
    """Olasılığa göre belirsizlik etiketi."""
    distance_from_0_5 = abs(prob - 0.5)
    if distance_from_0_5 > 0.35:
        return "high"
    if distance_from_0_5 > 0.15:
        return "medium"
    return "low"


def _build_feature_index() -> tuple[list[str], np.ndarray, list[str]]:
    """Mevcut ürünlerin (approved + rejected) feature matrisi."""
    approved_ids: list[str] = []
    rejected_ids: list[str] = []
    rows: list[np.ndarray] = []
    statuses: list[str] = []

    for jp in sorted(URUNLER_DIR.glob("*.json")):
        d = json.loads(jp.read_text(encoding="utf-8"))
        approval = d.get("approval_status", {})
        status = approval.get("value") if isinstance(approval, dict) else approval
        if status not in ("approved", "rejected"):
            continue
        urun_id = d["urun_id"]
        feats = extract_features(d)
        rows.append(feats)
        statuses.append(status)
        if status == "approved":
            approved_ids.append(urun_id)
        else:
            rejected_ids.append(urun_id)

    if not rows:
        return [], np.empty((0, 26)), []

    return approved_ids + rejected_ids, np.array(rows), statuses


def find_similar(query_feats: np.ndarray, top_n: int = 3) -> dict:
    """Cosine similarity ile en yakın N approved + N rejected ürün bul."""
    ids, matrix, statuses = _build_feature_index()
    if len(ids) == 0:
        return {"approved": [], "rejected": []}

    # Cosine similarity
    qn = np.linalg.norm(query_feats)
    if qn == 0:
        return {"approved": [], "rejected": []}
    mn = np.linalg.norm(matrix, axis=1)
    mn[mn == 0] = 1e-9  # zero-division önle
    sims = (matrix @ query_feats) / (mn * qn)

    # Approved + Rejected ayrı top-N
    pairs = list(zip(ids, sims, statuses))
    approved = sorted(
        [(i, s) for i, s, st in pairs if st == "approved"],
        key=lambda x: -x[1],
    )[:top_n]
    rejected = sorted(
        [(i, s) for i, s, st in pairs if st == "rejected"],
        key=lambda x: -x[1],
    )[:top_n]

    return {
        "approved": [{"urun_id": i, "similarity": float(s)} for i, s in approved],
        "rejected": [{"urun_id": i, "similarity": float(s)} for i, s in rejected],
    }


def predict_for_product(d: dict) -> dict:
    """Bir ürün JSON dict için ml_score yapısı döndür."""
    feats = extract_features(d)
    pipe, version = load_latest_model()

    if pipe is None:
        # Henüz model yok — sadece similarity döndür
        sim = find_similar(feats)
        return {
            "predicted_approval_prob": None,
            "confidence": "low",
            "similar_approved_products": [s["urun_id"] for s in sim["approved"]],
            "similar_rejected_products": [s["urun_id"] for s in sim["rejected"]],
            "model_version": None,
            "predicted_at": datetime.now(timezone.utc).isoformat(),
            "embedding_source": "tabular_only",
            "_note": "Model henüz eğitilmedi. python -m topla.ml.train ile cold start eğitim yap.",
        }

    # Tahmin
    prob = float(pipe.predict_proba(feats.reshape(1, -1))[0][1])  # P(approved)
    sim = find_similar(feats)
    return {
        "predicted_approval_prob": prob,
        "confidence": _confidence_from_prob(prob),
        "similar_approved_products": [s["urun_id"] for s in sim["approved"]],
        "similar_rejected_products": [s["urun_id"] for s in sim["rejected"]],
        "model_version": version,
        "predicted_at": datetime.now(timezone.utc).isoformat(),
        "embedding_source": "tabular_only",
    }


def predict_for_json_file(json_path: Path) -> dict:
    d = json.loads(Path(json_path).read_text(encoding="utf-8"))
    return predict_for_product(d)
