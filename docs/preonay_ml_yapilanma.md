# Ön Onay + ML + Web UI Yapılanması (Faz 7)

**Tarih:** 2026-05-26
**Versiyon:** 1.0

Bu doküman, Mobidik ARGE pazar zekası sisteminin Faz 7 sonrası yeni mimarisini açıklar. Önceki manuel akış (ham_cikti → Claude denetim → markalar/urunler/) artık **admin onay döngüsü ve ML öğrenmesi ile** çalışıyor.

---

## 1. Yeni Akış (4 aşamalı)

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. KEŞIF                                                              │
│  ─────────                                                             │
│  Scheduled task (Pzt/Çar/Cuma 06:00) veya manuel:                     │
│  • Web UI /pending → "🔍 Şimdi Tara" buton                            │
│  • Terminal: .\scheduled_tasks\run_batch.ps1 -Region nordik           │
│  • Terminal: .\scheduled_tasks\run_all_now.ps1 (3 bölge)              │
│                                                                        │
│  ↓ topla/batch.py: kategori sayfası tarar, yeni URL'leri keşfeder     │
│  → topla/ham_cikti/aday_<bolge>_<tarih>.json                          │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  2. SCRAPE                                                             │
│  ──────────                                                            │
│  Kullanıcı aday URL'i alır, manuel:                                   │
│  python -m topla.cli https://dedar.com/<slug>/                        │
│                                                                        │
│  ↓ topla/topla.py: HTML/PDF/görsel mekanik veri toplama                │
│  ↓ topla/scripts/migrate_*_gorseller_v2.py: ham → gorseller/          │
│  ↓ topla/scripts/link_variant_metadata.py: renk-görsel eşleştir        │
│  → markalar/urunler/<urun>.json (approval_status="pending")           │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  3. AI TAHMIN + ÖN ONAY                                                │
│  ──────────────────                                                    │
│  Otomatik:                                                             │
│  python topla/scripts/populate_ml_scores.py                           │
│  → ml_score doldurulur (predicted_approval_prob, similar_*)           │
│                                                                        │
│  Admin Web UI:                                                         │
│  http://localhost:5000/pending                                        │
│  → Her aday kart: AI öneri + benzer ürünler + onay/red butonu         │
│                                                                        │
│  ↓ /api/approve veya /api/reject                                       │
│  → markalar/urunler/<urun>.json (status değişir)                      │
│  → ml/feedback_log.jsonl (1 satır eklenir)                            │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  4. ÖĞRENME (Active Learning)                                          │
│  ────────────────────────────                                          │
│  Her N feedback'te (önerilen: 10):                                    │
│  python -m topla.ml.train --active                                    │
│                                                                        │
│  ↓ ml/model_v<N>.pkl yeni eğitilir                                     │
│  ↓ ml/metrics.json performans takibi                                   │
│  → Sonraki populate_ml_scores tahmin gelişir                          │
│  → Reddedilen pattern'ler benzer ürünleri filtreliyor                 │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Dosya Mimarisi

| Klasör | İçerik |
|---|---|
| `web/` | Flask app (app.py + templates + static) |
| `topla/ml/` | ML modülü (features, model, inference, train) |
| `ml/` | Model artifacts (model_v*.pkl gitignore, metrics+feedback commit) |
| `markalar/urunler/` | 27 ürün JSON v1.4 (approval_status + admin_decision + ml_score) |
| `topla/ham_cikti/` | Scrape ham çıktı + aday JSON (gitignore) |
| `_legacy/` | ALTIN sayfa + build_altin_dashboard.py (arşiv) |

---

## 3. Şema v1.4 — Yeni Alanlar

```jsonc
{
  "_schema_version": "1.4",
  // mevcut alanlar...

  "approval_status": {
    "value": "pending" | "approved" | "rejected"
  },
  "admin_decision": {
    "status": "approved" | "rejected" | null,
    "decision_date": "ISO 8601",
    "decision_by": "admin",
    "notes": "string",
    "rejection_reasons": ["jakar", "metallic", "en_sinir_disi", ...]
  },
  "ml_score": {
    "predicted_approval_prob": 0.0-1.0,
    "confidence": "high|medium|low",
    "similar_approved_products": ["urun_id_1", ...],
    "similar_rejected_products": [...],
    "model_version": "v1|v2|...",
    "predicted_at": "ISO 8601",
    "embedding_source": "tabular_only" | "dinov2_vitb14" (Faz 7.10+)
  }
}
```

---

## 4. ML Modeli (MVP)

**Tip:** sklearn RandomForestClassifier (binary: approved/rejected)
**Features (26):** width, weight, variant_count, certifications, staubli, overall, has_jakar, has_metallic, 6 fiber ratio, 4 weave flag, 4 country flag, 3 cert flag

**Cold start (v1):**
- 27 retroaktif approved + 27 synthetic negatives (jakar/metallic pattern)
- In-sample F1 = 1.0 (overfitting bekleniyor)

**Active learning (v2+):**
- Her admin red'i sonrası gerçek negatif örnek eklenir
- 5-10 feedback ile ilk anlamlı retrain
- ~20 feedback ile production-ready

**DINOv2 görsel embedding (Faz 7.10+):**
- Şu an MVP tabular yeterli
- Tekstil görsel benzerliği için DINOv2-ViT-B14 (sentence-transformers)
- 7GB disk + GPU önerilir

---

## 5. Web UI Kullanım

### Başlatma
```powershell
.\.venv\Scripts\python.exe web\app.py
# Tarayıcı: http://localhost:5000
```

### Ana Dashboard (`/`)
- 27 onaylı ürün (approved)
- Filter: arama + ALTIN-only checkbox
- ALTIN ürünler (skor ≥ 80) ⭐ rozetle

### Ön Onay (`/pending`)
- Pending ürünler (admin kararı bekleyen)
- Sol sidebar: AI stats + manuel tetik form
- Her kart: AI öneri renkli (yüksek/orta/düşük) + benzer ürünler
- Onay/Red butonları + Red modal (9 sebep checkbox)

### Geçmiş (`/history`)
- Tab: Approved + Rejected
- Tablo: karar tarihi + notlar + reddetme sebepleri

### Manuel Tetik
- Web UI dropdown: nordik / italyan / alman / all
- Terminal: `.\scheduled_tasks\run_all_now.ps1`

---

## 6. Admin Akışı (Pratik)

**Pazartesi sabah 06:00 → Scheduled task `Batch_nordik` çalıştı.**
1. Admin Web UI'a girer (`http://localhost:5000`)
2. Top nav'da "🔍 Onay Bekleyen (N)" sayacı görünür
3. Pending sayfasına gider
4. Her ürünü AI önerisi ile değerlendirir:
   - **Yeşil (≥75%)**: AI güveniyor — hızlı onay
   - **Sarı (50-75%)**: Belirsizlik — detayları incele
   - **Kırmızı (<50%)**: AI red öneriyor — sebep dikkat
5. Onay/Red kararı verir
   - Red: 1+ sebep seç (taxonomy)
6. Karar feedback_log'a yazılır + ML retrain için hazırlanır

**Cumartesi 09:00 → `Weekly_Review` çalıştı.**
- `docs/haftalik_oz_degerlendirme_<tarih>.md` üretildi
- Admin haftalık özet okur

---

## 7. ML Retrain Tetikleme

**Manuel:**
```powershell
.\.venv\Scripts\python.exe -m topla.ml.train --active
```

**Otomatik (önerilen):**
- Her 10 feedback sonrası background subprocess
- Eklenmesi gereken: `web/app.py` /api/reject sonunda counter kontrolü
- Şu an MVP — manuel retrain (Faz 7.6+ ileride)

**Model versiyonlama:**
- `ml/model_v1.pkl` (cold start)
- `ml/model_v2.pkl` (ilk gerçek retrain)
- `ml/metrics.json`: tüm versiyonların performansı kaydı

---

## 8. Bilinen Sınırlar

1. **Cold start overfitting**: İlk model 27 pozitif + synthetic'lerle eğitildi. Hepsi yüksek prob (0.95-1.0). Gerçek red'lerden sonra ayrışacak.
2. **DINOv2 entegre değil**: Şu an sadece tabular features. Görsel similarity (DINOv2) için Faz 7.10+ planı.
3. **Admin auth yok**: Tek kullanıcı varsayımı. Çok kullanıcılı olursa login eklenmeli.
4. **Web UI Flask dev mode**: Production için gunicorn/uvicorn gerekir (currently localhost-only).
5. **Active learning manuel**: Otomatik retrain tetik henüz yok (Faz 7.6+).

---

## 9. Migration Notları (Faz 7 öncesi sisteme dönüş)

- Schema v1.3 → v1.4: yeni alanlar opsiyonel (eski kod görmezden gelir)
- `_legacy/altin_urunler.html.legacy`: silinmedi, gerekirse geri taşınabilir
- `_legacy/build_altin_dashboard.py.legacy`: aynı şekilde
- ALTIN konsepti dashboard'da hala mevcut (overall ≥ 80 rozet)

---

## 10. Sonraki Adımlar

### Faz 7.6 — Otomatik retrain (kısa vadeli)
- Her 10 feedback sonrası `subprocess.Popen("python -m topla.ml.train --active")` /api/reject sonunda

### Faz 7.10 — DINOv2 entegrasyonu (uzun vadeli)
- `topla/ml/embeddings.py` — DINOv2-ViT-B14 cache
- `topla/ml/model.py` — fusion: concat(embedding 768d + tabular 26d) = 794d
- Re-train ile gelişmiş "benzer kumaş" arama

### Faz 7.20 — Production hardening
- Flask → uvicorn + reverse proxy
- Auth (single user login)
- Health endpoint + Sentry log
