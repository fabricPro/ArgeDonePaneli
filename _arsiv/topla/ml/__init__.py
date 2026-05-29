"""Faz 7.2: ML modülü — admin onay/red kararlarından öğrenen sınıflandırıcı.

Mimari:
- features.py: tabular feature encoder (kompozisyon, dokuma, en, sertifika...)
- embeddings.py: DINOv2 görsel embedding (lazy, opsiyonel)
- model.py: sklearn Pipeline (StandardScaler + RandomForestClassifier)
- inference.py: yeni aday için ml_score hesapla + benzer ürün bul
- train.py: feedback_log'tan retrain

Anayasa #9: Bu modul sadece mekanik MODEL operasyonu (eğitim, tahmin).
Yorum/anlamlandırma Claude tarafından (Anayasa #6 — kullanıcı onayı).
"""

__version__ = "1.0"
