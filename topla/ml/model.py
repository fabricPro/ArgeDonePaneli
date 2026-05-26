"""Faz 7.2: sklearn binary classifier wrapper.

Model: RandomForestClassifier (binary: approved/rejected).
Cold start: 27 retroaktif approved + synthetic negatives.
Active learning: her admin red kararı negatif örnek olarak eklenir.

Disk yapısı:
- ml/model_<version>.pkl — eğitilmiş Pipeline
- ml/metrics.json — performans takibi (precision/recall/f1)
- ml/feedback_log.jsonl — admin kararları (her satır 1 JSON)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ML_DIR = PROJECT_ROOT / "ml"
ML_DIR.mkdir(parents=True, exist_ok=True)


def build_pipeline() -> Pipeline:
    """sklearn Pipeline — Scaler + RandomForest."""
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=2,
            random_state=42,
            class_weight="balanced",  # az veri ile dengeli
        )),
    ])


def synthetic_negatives(n_samples: int, n_features: int, rng: np.random.Generator) -> np.ndarray:
    """Cold start için: kapasite-dışı pattern'leri rastgele üret.

    Strateji: jakar=1, metallic=1 olan + linen=0, dobby=0 olan rastgele örnekler.
    """
    negatives = []
    for _ in range(n_samples):
        # Pozitif vektörden farklı bir profil
        v = rng.random(n_features).astype(np.float32) * 0.3  # düşük değerler
        v[6] = float(rng.random() > 0.5)  # has_jakar (50% şans)
        v[7] = float(rng.random() > 0.7)  # has_metallic (30%)
        # weave hepsi düşük
        v[15:19] = rng.random(4) * 0.2
        # natural fibers düşük (synthetic ağırlıklı)
        v[8:14] = rng.random(6) * 0.1
        v[10] = 0.7 + rng.random() * 0.3  # polyester yüksek (sentetik)
        v[14] = v[10]  # synthetic_total
        negatives.append(v)
    return np.array(negatives)


def train_cold_start(X_pos: np.ndarray, n_synthetic: int = 30) -> tuple[Pipeline, dict]:
    """Cold start: pozitif örnekler + synthetic negatives ile eğit."""
    rng = np.random.default_rng(42)
    X_neg = synthetic_negatives(n_synthetic, X_pos.shape[1], rng)

    X = np.vstack([X_pos, X_neg])
    y = np.concatenate([np.ones(len(X_pos)), np.zeros(len(X_neg))])

    pipe = build_pipeline()
    pipe.fit(X, y)

    # In-sample metrics (cold start, gerçek test seti yok)
    y_pred = pipe.predict(X)
    metrics = {
        "training_mode": "cold_start_synthetic",
        "n_positive": int(len(X_pos)),
        "n_negative_synthetic": int(n_synthetic),
        "in_sample_precision": float(precision_score(y, y_pred, zero_division=0)),
        "in_sample_recall": float(recall_score(y, y_pred, zero_division=0)),
        "in_sample_f1": float(f1_score(y, y_pred, zero_division=0)),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    return pipe, metrics


def train_active(X_pos: np.ndarray, X_neg: np.ndarray) -> tuple[Pipeline, dict]:
    """Active learning: gerçek positive + negative örnekler (admin geribildirim)."""
    if len(X_neg) == 0:
        # Henüz red yok — synthetic ile devam
        return train_cold_start(X_pos)

    X = np.vstack([X_pos, X_neg])
    y = np.concatenate([np.ones(len(X_pos)), np.zeros(len(X_neg))])

    pipe = build_pipeline()
    pipe.fit(X, y)

    y_pred = pipe.predict(X)
    metrics = {
        "training_mode": "active_learning",
        "n_positive": int(len(X_pos)),
        "n_negative_real": int(len(X_neg)),
        "in_sample_precision": float(precision_score(y, y_pred, zero_division=0)),
        "in_sample_recall": float(recall_score(y, y_pred, zero_division=0)),
        "in_sample_f1": float(f1_score(y, y_pred, zero_division=0)),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    return pipe, metrics


def save_model(pipe: Pipeline, version: str, metrics: dict) -> tuple[Path, Path]:
    """Diskte sakla."""
    model_path = ML_DIR / f"model_{version}.pkl"
    metrics_path = ML_DIR / "metrics.json"

    joblib.dump(pipe, model_path)

    # Metrik geçmişi append
    existing = {}
    if metrics_path.exists():
        existing = json.loads(metrics_path.read_text(encoding="utf-8"))
    history = existing.get("history", [])
    history.append({"version": version, **metrics})
    existing = {"latest_version": version, "history": history}
    metrics_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    return model_path, metrics_path


def load_latest_model() -> tuple[Pipeline | None, str | None]:
    """Disk'teki en güncel modeli yükle."""
    metrics_path = ML_DIR / "metrics.json"
    if not metrics_path.exists():
        return None, None
    existing = json.loads(metrics_path.read_text(encoding="utf-8"))
    version = existing.get("latest_version")
    if not version:
        return None, None
    model_path = ML_DIR / f"model_{version}.pkl"
    if not model_path.exists():
        return None, None
    return joblib.load(model_path), version
