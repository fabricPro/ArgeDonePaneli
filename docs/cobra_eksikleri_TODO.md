# Cobra Düzeltme TODO (Days Like Now sonrası)

**Tarih:** 2026-05-25 (Faz 5.3 sonrası)
**Hedef:** Cobra için eksik veri + görselleri tamamla.
**Kullanıcı kararı (2026-05-25):** Days Like Now'a önce geç, Cobra düzeltmesi sonra.

## Eksikler

### 1. Görseller (8-10 adet bekleniyor, 1 var)

**Şu an mevcut:** `gorseller/dedar/00T19063/004_1.jpg` (sadece Duna varyantı ana görseli)

**Eksik:**
- `002_1.jpg` — 002 varyantı (ismi de bilinmiyor)
- `004_2.jpg`, `004_3.jpg` — Duna detay/close-up
- `lifestyle_01.jpg` — Mood/oda çekimi
- Galerideki diğer açılar (3-5 görsel daha)

### 2. 002 varyant adı

Şu an `markalar/urunler/dedar_00T19063-cobra.json` `variants[0]` için `color_name: "(Dedar 002 ton — isim sayfada belirtilmemiş, varsayılan)"` — gerçek isim alınmadı.

### 3. Production model belirsizliği

Adaptör v1.0 "Article on request → make_to_order" diyor. Cobra sayfasında "Article on request" yok, "Current Stock" var. Şu an `production_model: "mixed"` işaretli — net değil.

### 4. Lead time eksik

Adaptör v1.0 "10 weeks = 70 gün" diyordu, scraper bu kez yakalamadı. JSON'da `lead_time_days: 70` manuel olarak adaptör referansından yazıldı, ama Cobra sayfasında "Production order lead time" Cobra için var mı doğrulanmadı (stokta görünüyorsa lead time uygulanmaz).

## Çözüm seçenekleri

### Seçenek A: Scraper v1.1 sonrası Cobra rebuild (önerilen, sürdürülebilir)

Scraper v1.1 ile şunlar otomatik gelir:
- Galeri tüm görselleri parse → 8-10 görsel
- 002 varyant adı + görseli
- width/weave/description otomatik (body manual gerekmez)
- Production model + lead time net

Sonra Cobra JSON'unu yeniden üret:
```powershell
.\.venv\Scripts\python.exe topla\scripts\test_cobra.py  # scraper v1.1 ile
.\.venv\Scripts\python.exe topla\scripts\create_dedar_cobra.py  # yeniden patch
.\.venv\Scripts\python.exe topla\scripts\build_dashboard.py
```

audit_history'ye v1.2 entry'si: "scraper v1.1 sonrası galeri + 002 varyant + gerçek production_model eklendi".

### Seçenek B: Manuel görsel indirme (~10 dakika)

Chrome'da dedar.com/cobra/?sku=00T1906300002 ve 00T1906300004 sayfalarını aç, her görseli sağ tık → kaydet → `gorseller/dedar/00T19063/<renk>_<sira>.jpg`. JSON'u manuel güncelle.

Hızlı ama scraper iyileştirme sağlanmaz.

### Seçenek C: Manuel + Scraper v1.1 her ikisi

Days Like Now'a geç → Dedar n=2 → 4 yeni marka adaptör + scraper yaz → scraper v1.1 hazır olunca **Cobra'yı yeniden çek**.

## Karar

**Şimdilik C** (Days Like Now önce → 4 yeni marka adaptör → scraper iyileştirme paralel öğrenilir → Cobra v1.2 rebuild). Çünkü:
- Cobra zaten dashboard'da görünüyor (1 görsel, mobidik_evaluation tam)
- Days Like Now n=2'ye yükseltir, marka profili güçlenir
- 4 yeni marka adaptör + scraper geliştirme sırasında BigCommerce/Vue/diğer platform parse pattern'leri öğreneceğim — Dedar scraper iyileştirmesi paralel ilerler
- En sonunda **TÜM Dedar ürünlerini scraper v1.1 ile yeniden çek**

## Faz 5 yol haritası (güncel)

1. ✅ Faz 5.3: Cobra n=1 (bu oturum)
2. ⏳ Faz 5.4: Days Like Now n=2
3. ⏳ Faz 5.5-5.8: Rubelli, Sahco, Nya Nordiska, Création Baumann (sıra)
4. ⏳ Faz 5.9: Scraper v1.1 (Cobra + Dedar sapmaları + 4 yeni markanın öğrenilmiş hataları)
5. ⏳ Faz 5.10: **Cobra rebuild + Days Like Now rebuild** (scraper v1.1 ile tüm Dedar n=2 verisi temiz)
6. Faz 5 SONU: 7 marka × ~30-50 ürün audited, tüm görseller tam

## Kontrol noktası

Faz 5.10'da bu dosya kontrol edilir. Eğer Cobra hâlâ 1 görselle duruyorsa Faz 5.9 scraper v1.1 tamamlandıktan sonra rebuild zorunlu.

Audit_history'de iz: `dedar_00T19063-cobra_v1.2_<tarih>` "scraper v1.1 rebuild + galeri tam + 002 varyant".
