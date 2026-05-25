# Dedar Scraper v1.1 Sonuçları (Faz 5.10)

**Tarih:** 2026-05-25
**Test ürünleri:** Cobra (00T19063) + Days Like Now (00T25007)
**Scraper dosya:** `topla/scrapers/dedar.py` (v1.0 → v1.1)
**Sonuç dokümanı (referans):** `docs/scraper_sapmalari_cobra.md` (v1.0 öğrenilen 7 hata)

## Düzeltme tablosu — önce/sonra

| Alan | v1.0 (Cobra) | v1.0 (DLN) | v1.1 (Cobra) | v1.1 (DLN) | Sonuç |
|---|---|---|---|---|---|
| **width_cm** | None ❌ | None ❌ | **325** ✅ | **134** ✅ | DÜZELDİ |
| **weave_type** | "Single sheet" ❌ | "Single sheet" ❌ | **leno** ✅ | **plain** ✅ (shantung normalize) | DÜZELDİ |
| **description** | cookie banner ❌ | cookie banner ❌ | gerçek paragraf ✅ | gerçek paragraf ✅ | DÜZELDİ |
| **lightfastness** | None ❌ | None | **6** ✅ | (sayfada yok) | DÜZELDİ |
| **production_model** | unknown | unknown | **stock** ✅ | **stock** ✅ | DÜZELDİ |
| **variants_raw** | 2 dupe SKU ❌ | 2 dupe SKU ❌ | **002+004** ✅ | **001-008 (8 ton)** ✅ | DÜZELDİ |
| **görsel sayısı** | 1 ❌ | 3 ⚠️ | **36** ✅ | **74** ✅ | DÜZELDİ (36-74x artış) |
| composition | OK ✅ | OK ✅ | OK ✅ | OK ✅ | — |
| country | OK ✅ | OK ✅ | OK ✅ | OK ✅ | — |
| certifications | 6 sertifika ✅ | 3 sertifika ✅ | 6 ✅ | 3 ✅ | — |

**Skor:** 7/7 düzeltme **BAŞARILI** — body manual gerek YOK (Cobra+DLN için).

## Teknik notlar — düzeltmeler

### 1. width_cm

**Sorun (v1.0):** `_extract_label_value(text, "Width")` body'de ilk "Width" eşleşmesini alıyordu, bu Cobra'da SKU label'ından önce gelen başka bir "Width" idi (form alanı "TYPE\nSingle sheet\nDouble sheet\n Add window\nHeight\ncm\nWidth\ncm").

**Çözüm (v1.1):** `_extract_width_strict()` fonksiyonu:
```python
matches = re.findall(r"\bWidth\s*\n\s*(\d+)\s*cm\b", text)
return f"{matches[-1]} cm"  # son eşleşme (Specifications tablosu sayfanın altında)
```

Sayısal değer ZORUNLU — form alanı boş "cm" pattern ile eşleşmez.

### 2. weave_type

**Sorun (v1.0):** "Type" label "Single sheet/Double sheet" form alanından eşleşiyordu.

**Çözüm (v1.1):** `_extract_weave_dedar()`:
1. Önce "Type" label dene → ama `WEAVE_REJECT = ["single sheet", "double sheet", "transparency", ...]` reject listesi
2. Sonra body'de WEAVE_KEYWORDS (leno weave, jacquard, shantung, plain weave, ...) ara

`shantung` özel normalize: `plain` (slub iplik + plain dokuma).

### 3. description

**Sorun (v1.0):** İlk 80-800 karakter paragrafı alıyordu → cookie banner.

**Çözüm (v1.1):** `_extract_dedar_description()`:
1. Marka adıyla başlayan paragraf tercih (`Cobra is...`, `Days Like Now celebrates...`)
2. Cookie keyword filter (`"cookies", "social media features", "advertising"`)
3. 80-1000 karakter aralık

### 4. lightfastness

**Sorun (v1.0):** "Light fastness" label ve `≥ 6​` formatı (zero-width-space içerir) eşleşmiyordu.

**Çözüm (v1.1):**
```python
text_clean = re.sub(r"[​‌‍﻿]", "", text)  # zero-width karakterleri temizle
for label in ["Lightfastness", "Light fastness", "Light Fastness"]:
    m = re.search(rf"\b{label}\b\s*[:\n]\s*[≥≧>=\s]*(\d+)", text_clean)
```

### 5. galeri (BigCommerce CDN)

**Sorun (v1.0):** `extract_image_specs()` Kvadrat-spesifik selectors (`product-color-picker`) → Dedar BigCommerce stencil'de yetersiz.

**Çözüm (v1.1):** `_extract_dedar_gallery_images()`:
```python
re.finditer(
    r'https://cdn11\.bigcommerce\.com/s-td9auqdllx/[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
    html
)
# + connect.dedar.com lifestyle URL'leri
```

Sonuç: Cobra 36 görsel, DLN 74 görsel (önceki 1, 3).

### 6. variants_raw

**Sorun (v1.0):** Radio button regex `data-product-attribute-value` Dedar BigCommerce tema'da eşleşmedi.

**Çözüm (v1.1):** Body'den "Selected Colore is X" sonrası ardışık 3-haneli kodlar:
```python
m = re.search(r"Selected Colore[^\n]+\n([\d\n]+)", body_text)
# Cobra: "Selected Colore is 4 duna\n004\n002" → 002+004
# DLN:   "Selected Colore is 1 quarzo\n001\n002\n003\n004\n005\n006\n007\n008" → 001-008
```

### 7. production_model

**Sorun (v1.0):** Sadece "Article on request" → make_to_order kontrol vardı.

**Çözüm (v1.1):**
```python
if re.search(r"Article on request", body_text):
    "make_to_order"
elif re.search(r"Current Stock", body_text):
    "stock"
else:
    "unknown"
```

Cobra + DLN ikisinde de "Current Stock" var → stock. "Article on request" Dedar'ın bazı niş/MTO ürünlerinde olabilir.

## Açık iş (Faz 5.11)

### Görsel migrasyonu

Cobra ham_cikti'da **36 görsel**, DLN ham_cikti'da **74 görsel** indirildi (`topla/ham_cikti/gorseller/dedar/<urun-slug>/`). Bunları:
1. `gorseller/dedar/<urun_kodu>/` konvansiyon yolu altına kopyala
2. Her görsel için `images.variants[]` veya `images.lifestyle[]` veya `images.technical[]` listesine girdi ekle
3. Dashboard rebuild → kart başına 3-5 görsel görünür (lightbox carousel)

### Cobra için 002 varyantı

v1.1 002 SKU'yu tespit etti (variants_raw'da var) ama renk adı hâlâ bilinmiyor. 002 SKU URL'i `https://dedar.com/cobra/?sku=00T1906300002` çekilerek (varyant tıklayarak) renk adı alınabilir. Faz 5.11.

## Genel değer

Bu Faz 5.10 iyileştirmesi sonucu:
- **Yeni Dedar ürünleri için body manual gerek YOK** — scraper otomatik
- Diğer 4 yeni marka (Rubelli, Sahco, Nya Nordiska, Création Baumann) için **Dedar pattern'i şablon** (BigCommerce stencil + label-value + description + galeri CDN tarama)
- Anayasa #9 disiplini canlı doğrulandı: Python mekanik, Claude denetim — iki katman ayrı

Faz 5.5+ (yeni marka adaptörleri) Dedar v1.1 öğrenilenlerle başlayacak: BigCommerce/Magento/Shopify gibi platform tespit + CDN pattern + label-value + description filter.
