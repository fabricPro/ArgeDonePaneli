# ARGE Perdelik Pazar Zekası — Anayasa v2.0

Bu dosya her oturumda okunur. Sistemin operasyonel kurallarını içerir.

---

## BAĞLAM

Kullanıcı: Mobidik ARGE departmanı.
İş tanımı: Stäubli armür makinesi ile **armür (dobby) perdelik kumaş** üretimi. Türk pazarı + ihracat odaklı.

Bu projenin amacı: Premium perdelik üreticilerini sistematik izleyerek rakip/referans analizi yapmak, ARGE öncelikleri belirlemek, pazar fırsatlarını tespit etmek.

İzlenen markalar (7): Kvadrat, Dedar, Rubelli, Sahco, Nya Nordiska, Création Baumann, Zimmer + Rohde.

---

## MİMARİ — İŞ BÖLÜMÜ

İki katman var, kanıt zinciri için kesin sınırlı:

**Python script (`topla/topla.py`)** — sadece MEKANİK veri toplama:
- HTML çekme (Playwright)
- PDF indirme + metin çıkarma
- Görsel binary indirme
- Field parsing (adaptör eşleştirmesine göre)
- Ham JSON çıktı: `topla/ham_cikti/<marka>_<urun>_<timestamp>.json`

**Claude Code (sen)** — sadece DENETİM / YORUM / STRATEJİ:
- Anayasa kontrol
- `ai_inferences` doldur (sadece izinli alanlar)
- Türkçe çeviri (`description_tr`)
- `mobidik_evaluation` puanlama
- `strategic_note` (Türkçe)
- `image_analysis` (renk, doku, şeffaflık)
- Final JSON yazımı (`markalar/urunler/<marka>_<urun>.json`)
- `_provenance.audit_history` kaydı

İki katman karışmaz. Detayı: Altın Kural #9.

---

## ALTIN KURALLAR

### 1. Şema Değişmez
Her ürün `sema/urun.json`, her marka profili `sema/marka_profili.json` yapısına UYGUN olmak zorunda. Yeni alan ekleme. Mevcut alanı atlamak yerine `null` yaz. Eksik veriyi `data_quality.missing_fields` listesine ekle.

### 2. Veri Bütünlüğü Mutlak
Site/PDF kaynaklı veri `source_data` bloğunda durur. AI tahminleri `ai_inferences` bloğunda durur. **Asla karıştırma.** Her `source_data` alanı `_provenance.field_metadata`'da kaynağıyla (HTML / PDF / manual_sample) işaretlenir.

### 3. Asla Tahmin Edilmeyecek Alanlar
Fiyat, MOQ, sertifikasyonlar, üretim ülkesi, teslim süresi, kompozisyon, fr_treatment. Bu alanlar ya kaynaktan birebir gelir ya da `null` kalır. Bu alanları `ai_inferences` bloğuna **yazma**.

### 4. Görseller Mutlaka İndirilir
Python script (`topla.py`) görselleri Katman 1 (direct HTTP — `requests`) ile indirir; başarısız olursa Katman 2 (Chrome MCP) fallback. Cowork iterasyonundaki binary fetch engeli artık YOK — Python `requests` doğrudan binary indiriyor.

URL bırakma. İstisna: hiçbir katman başarılı olmazsa stub bırak:

```json
{
  "url": "...",
  "local_path": null,
  "status": "pending_manual_download",
  "layer_attempts_history": [...]
}
```

`pending_manual_download` istisna durumdur, varsayılan değil.

### 5. Kullanıcı Notu Birinci Sınıf Veridir
Türkçe doğal dil notları, yapılandırılmış puandan **öncelikli**. Kullanıcı bir alanı doğrularsa `user_verified: true` işaretle; düzeltme verirse `user_correction` doldur, `user_correction_source` kaynağı işaretle. Her tarama öncesi son 30 günün notlarını oku, örüntü çıkarımı yap.

### 6. Onay Olmadan Tam Veri Çekme
`topla.py` batch tarama yapar, çıktıyı `topla/ham_cikti/`'ya yazar. Claude Code denetim yapmadan **`markalar/urunler/`'e geçmez**.

"**Tam veri çekme**" = "ham_cikti'dan markalar/urunler/'e geçiş" anlamında. Bu adım kullanıcı onayı + Claude denetimi gerektirir.

Aday taramasında (`topla.py --batch`) sadece ön izleme: ad, URL, 1 thumbnail, temel özet. Tam veri + görsel detayı + AI yorum **sadece kullanıcı onayladıktan sonra**.

### 7. Stäubli Kapasite Bağlayıcıdır
`mobidik_evaluation.staubli_feasibility` puanlanırken `kapasite/staubli_uretim_kapasitesi.md` dosyası referans alınır. Bu dosya işletmenin BUGÜNKÜ gerçek kapasitesini yansıtır, teorik makine kapasitesini değil. AI inference ile puanlama yapılırken kapasite tablosundaki KESİN ve TAM değerler bağlayıcıdır.

### 8. Denetlenmiş Veri Önceliği — YENİ (v2.0)
Bir ürün/marka için spesifik kod, isim, sayısal değer veya tarihsel iddia kullanılırken, MEVCUT DOĞRULANMIŞ JSON dosyalarından kaynak alınır:
- `markalar/<marka>.json` (marka profili — denetlenmiş)
- `markalar/urunler/<marka>_<urun>.json` (ürün kayıtları — denetlenmiş)
- `kapasite/staubli_uretim_kapasitesi.md` (kapasite — kullanıcı doğrulamalı)

Hafızadan, karantinadaki referanslardan veya "genelde böyle olur" kalıbından alıntı **YASAKTIR**.

Karantinadaki veriler "neyin yanlış olduğunu" göstermek için saklanır; "neyin doğru olduğunu" söylemek için **KULLANILAMAZ**.

Bu kural Claude Code'a, herhangi bir Claude oturumuna ve Python script'inin parser mantığına uygulanır.

**Gerekçe**: Cowork iterasyonunun son evresinde ana sohbet Claude'u karantina verisinden alıntı yaptı ("0143 White Sand" hayaletti, gerçek "0101 White Linen"). Cowork yakaladı. Bu olay disiplinin sadece tek oturumla sınırlı olmadığını gösterdi — anayasa olarak sabitlenmesi gerekiyor.

### 9. Veri Toplama vs Denetim İş Bölümü — YENİ (v2.0)
Python script (`topla.py`) sadece MEKANİK veri toplama yapar: HTML çekme, PDF/görsel indirme, field parsing (adaptör eşleştirmesine göre).

**Python script ASLA yapmaz:**
- AI inference YAPMAZ
- Türkçe çeviri YAPMAZ
- `mobidik_evaluation` YAPMAZ
- Stratejik yorum YAPMAZ
- Anayasa denetimi YAPMAZ

**Claude Code (veya başka Claude oturumu) sadece DENETİM / YORUM / STRATEJİ yapar:**
- Anayasa kontrol
- `ai_inferences` doldur (sadece izinli alanlar)
- Türkçe çeviri (`description_tr`)
- `mobidik_evaluation` puanlama
- `strategic_note` (Türkçe)
- `image_analysis` (görseli okuyup hex renk, doku, şeffaflık)
- Final JSON yazımı (`markalar/urunler/` altına)
- `audit_history` kaydı

Bu iş bölümü değişmez. Hangi tarafın hangi adımı yapacağı karışırsa, sistem hibridleşir ve kanıt zinciri kırılır.

---

## DİL & KONVANSİYONLAR

- **Klasör adları**: İngilizce, sade (örn. `kapasite`, `sema`, `adaptorler`, `markalar`, `gorseller`, `pdfler`, `topla`, `docs`)
- **Dosya adları**: İngilizce, snake_case (örn. `staubli_uretim_kapasitesi.md`, `marka_profili.json`)
- **JSON alan isimleri**: İngilizce, snake_case (örn. `weight_gsm`, `weave_type`)
- **JSON değerleri ve raporlar**: Türkçe (örn. `"comment": "Standart dobby ile uyumlu..."`)
- **Marka/ürün adları**: Orijinal dilinde, değiştirilmez
- **Numerik değerler**: Metrik birim (cm, gsm), birim alan adında belirtilir
- **Tarih formatı**: ISO 8601 UTC (`2026-05-14T10:30:00Z`)

---

## MASTER İŞ AKIŞI — PARTİ LİNK GELDİĞİNDE

Kullanıcı bir veya birden fazla link verdiğinde:

1. **Marka tespiti**: URL'den marka çıkar.
2. **Adaptör yükle**: `adaptorler/<marka-slug>.md` oku. Yoksa kullanıcıya sor, birlikte oluştur.
3. **Python `topla.py` çalıştır** (kullanıcı veya scheduled task):
   - Adaptör kurallarına göre HTML / PDF / görsel çek
   - `source_data` + `_provenance.field_metadata` + `images.layer_*_attempt` kayıtları doldur
   - `ai_inferences`, `mobidik_evaluation`, `description_tr`, `image_analysis` BOŞ bırakılır
   - Ham çıktı: `topla/ham_cikti/<marka>_<urun>_<timestamp>.json`
4. **Claude Code denetim** (sen — bu sohbette):
   - Anayasa kontrol (kural 1-9)
   - `ai_inferences` doldur (izinli alanlar — güven seviyesi + method + based_on zorunlu)
   - `description_tr` çeviri (translation_method işareti)
   - `mobidik_evaluation` puanla (kapasite tablosu bağlayıcı — kural #7)
   - `image_analysis` (görseli oku — dominant_colors hex, texture, transparency)
   - `_provenance.audit_history` kaydı + `constitutional_violations_check: passed_at_<ISO>`
   - Final JSON: `markalar/urunler/<marka>_<urun>.json`
5. **Marka profili güncellemesi**:
   - `markalar/<marka>.json` yeniden hesapla
   - n eşiği kuralı: n<3 → `value: null` + `sample_status: "insufficient_n_X"` + `observed_at_n1`/`n2` ile gözlem korunur
   - `data_integrity.reliability_label` güncelle (insufficient_sample / mostly_estimated / mixed / high_verified)
6. **Log**:
   - `docs/parti_log.md`'ye parti notu (yoksa oluştur)
   - Eksiklikler `data_quality.missing_fields`'a düşmüş olmalı (kural #1)

---

## SCHEDULED TASK — ZAMANLANMIŞ ADAY KEŞFİ

Henüz kurulmadı. Pilot Air Line + Cobra denetiminden sonra aktive edilecek. Hedef kadans (Windows Task Scheduler ile `topla.py --batch <bölge>` çağrısı):

- **Pazartesi 06:00** → `kvadrat,sahco` (Nordik bölgesi)
- **Çarşamba 06:00** → `dedar,rubelli` (İtalyan bölgesi)
- **Cuma 06:00** → `nya-nordiska,creation-baumann,zimmer-rohde` (Alman / Alpin bölgesi)
- **Cumartesi 09:00** → Haftalık öz-değerlendirme (Claude Code oturumu — `markalar/`'daki son 7 günü tara)

`topla.py --batch` çalıştığında:
- Kategori sayfalarını tarar; ön izleme verisi çeker (ad, URL, 1 thumbnail, temel özet)
- `topla/ham_cikti/aday_<bolge>_<tarih>.json` yazar
- Kullanıcı arayüzde (gelecekte) inceleyip onaylayınca `topla.py --detail <urun-id>` ile tam veri çeker
- Claude Code denetim → `markalar/urunler/`'e yazar

---

## REHBERLERİ NE ZAMAN YÜKLEMELİSİN

CLAUDE.md kısa tutulmuştur. Detay gerektiğinde:

- **Stäubli kapasitesi (`staubli_feasibility` için bağlayıcı)**: `kapasite/staubli_uretim_kapasitesi.md`
- **Marka adaptörleri**: `adaptorler/<marka>.md` (denetlenmiş: `kvadrat.md` v1.2, `dedar.md` v1.0)
- **Mimari geçiş tarihçesi**: `docs/mimari_gecis_2026-05-14.md`
- **Cowork engelinin tarihçesi (neden Python)**: `docs/neden_python_script.md`
- **Şema referansı**: `sema/urun.json` (v1.3) + `sema/marka_profili.json` (v1.1)
- **Referans marka profili (n=1 örneği)**: `markalar/kvadrat.json`
- **⭐ Dedar scraping öğrenilen dersler (HER YENİ DEDAR ÜRÜN DENETİMİNDE OKU)**: `docs/dedar_scraping_lessons_learned.md` — 4-aşamalı akış (scrape → migrate → link → dashboard), swatch vs named variant ayrımı, v1.2 product_code fallback, çözülen çelişki örnekleri

---

## VERİ KAYDETME DİSİPLİNİ

### Asla
- Bir alanı sessizce atlama → `null` yaz + `missing_fields`'a ekle
- AI tahminini `source_data`'ya yazma
- Bir alanın değerini "muhtemelen" gibi muğlak yapma
- Veriyi başka bir alanda göstermek için duplicate etme
- Önceki kayıt varsa üzerine yazma — `last_updated` güncelle, `audit_history` tut

### Her zaman
- Her JSON kaydında `last_updated` (ISO 8601 UTC) güncelle
- Her AI çıkarımına güven seviyesi (`high | medium | low`) + method ekle
- Kullanıcı doğrularsa `user_verified: true` işaretle
- Adaptör artık çalışmıyorsa `docs/adaptor_sapmalari.md`'ye not düş (yoksa oluştur)

---

## HATA DURUMLARI

### Site erişilemiyor (403, timeout, vb.)
- `topla.py` Katman 1 başarısız → Katman 2 (Chrome MCP) fallback
- Hepsi başarısızsa → o ürünü atla, `data_quality.notes`'a düş, `docs/erisim_hatalari.md`'ye yaz (yoksa oluştur)
- ASLA "muhtemelen X olmalı" tahmin yapma

### Adaptör güncel değil (site yapısı değişmiş)
- Kullanıcıyı uyar
- `docs/adaptor_sapmalari.md`'ye yaz: hangi alanlar bulunamadı, hangi yeni alanlar görüldü
- Adaptör güncellemesi için kullanıcıdan onay iste

### Şüpheli / anormal veri
- Yazma, kullanıcıya sor
- Örn: bir Kvadrat ürününde 5000 cm en görüyorsan, bu yazılı hata olabilir — atla, raporda not düş

---

## SUPABASE / POSTGRESQL UYUMLULUK (uzun vade)

Tüm JSON yapıları PostgreSQL `jsonb` sütunlarına olduğu gibi mapleneceği şekilde tasarlanmıştır. Bu uyumluluğu bozmamak için:

- ID konvansiyonu: `urun_id = <marka_slug>_<urun_kodu>` (string, tek anahtar)
- Dosya yolları: `gorseller/<marka_slug>/<urun_kodu>/<dosya>.jpg` (Supabase Storage path uyumlu)
- Tarih formatı: ISO 8601 UTC (`2026-05-14T10:30:00Z`)

---

## VERSİYON

**Anayasa v2.0** — 2026-05-14

Değişiklikler v1.0'dan:
- Mimari yenilendi: Cowork → Python (`topla.py`) + Claude Code
- Kural #4 güncellendi: 3 katmanlı strateji yerine "Python Katman 1 + Chrome MCP fallback"
- Kural #6 güncellendi: tarama gate'i `topla/ham_cikti/` → `markalar/urunler/`
- **Kural #8 EKLENDİ**: Denetlenmiş veri önceliği (karantina/hafıza alıntısı yasak)
- **Kural #9 EKLENDİ**: Veri toplama vs denetim iş bölümü (Python ↔ Claude)
- Klasör adları sadeleşti: `_kapasite/` → `kapasite/`, `_sema/` → `sema/`, `_adaptorler/` → `adaptorler/`, `01_veri/marka_profilleri/` → `markalar/`, `01_veri/urunler_per_marka/` → `markalar/urunler/`, `02_gorseller/` → `gorseller/`, `99_kalite_kontrol/` (Cowork-spesifik) → `docs/` (sade dokümantasyon)
- Cowork referansları temizlendi
- v1.0'dan çıkarılanlar (henüz uygulanmıyor — gerektiğinde v2.x ile gelir): "Kullanıcı Kararı Sonrası" akışı, "Aylık Marka Keşfi", "Haftalık Öz-Değerlendirme", "Arayüz Üretimi", "Karar Diyaloğu Protokolü"
