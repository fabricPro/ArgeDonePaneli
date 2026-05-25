# Dedar Cobra Scraper Sapmaları (2026-05-25 canlı test)

**Test URL:** `https://dedar.com/cobra/?sku=00T1906300004`
**Ham çıktı:** `topla/ham_cikti/dedar_cobra_20260525T203227Z.json`
**Scraper versiyon:** `topla/scrapers/dedar.py` v1.0 (ilk canlı test)
**Sonuç:** scraper çalıştı, 6/10 alan doğru yakalandı; 4 alan body manual gerektirdi.

## ✅ Scraper başarıyla yakaladı (6 alan)

- `product_code` (00T19063) + `variant_code` (00004) — URL parse
- `composition_text` (100% Fire-retardant Polyester) — Specifications label
- `weight_raw` (227 g/ml) — Specifications label
- `country_of_origin` (Italy) — Specifications "Made in"
- `certifications` (6 sertifika: IMO MED, Italy Class 1, BS5867/2/B, BS5867, M1, Oekotex) — regex set
- 1 ana görsel indirildi (Layer 1 başarılı, BigCommerce CDN)

## ❌ Scraper yakalayamadı (4 alan) — Claude denetim manuel düzeltti

### 1. `width_cm` → None (gerçek: 325 cm)

**Sorun:** `width_raw` SKU değerini almış (`"00T1906300004"`).

**Sebep:** `_extract_label_value(text, "Width")` ilk pattern `"Width: value"` SKU label'ından önce yakaladı. Sayfada body text'inde:
```
Code
00T1906300004
...
Width
325 cm
```
Pattern `"Width\nvalue"` (yeni satır ayraçlı) çalışması beklenir ama önceki "Width" kelimesi başka yerde olabilir.

**Düzeltme önerisi (scraper v1.1):**
- Width için **sayısal pattern** ara: `re.search(r"Width\s*\n\s*(\d+)\s*cm", text)`
- Veya: `width_raw`'da SKU formatı varsa (`^\d+[A-Z]\d+$`) reject et, alternative pattern dene.

### 2. `weave_type` → "Single sheet" (gerçek: "leno")

**Sorun:** Scraper "Type" label'ı altında "Single sheet" buldu.

**Sebep:** Sayfada "TYPE\nSingle sheet\nDouble sheet" — bu form alanı (perde paneli sayısı seçimi), **dokuma tipi değil**. Adaptör v1.0 "Type" label'ı diyordu ama yanılmış.

**Gerçek konum:** Description paragrafı içinde:
> "It is an extra-wide **leno weave** created using special looms..."

**Düzeltme önerisi (scraper v1.1):**
- "Type" label'ından "Single sheet"/"Double sheet" gibi form değerleri **reject** et (weave_map'te yok).
- `_find_weave_in_description(body_text)` zaten var; öncelikle description'da ara.
- Adaptör `dedar.md`'de "Type alanı dokuma değil, form alanı olabilir" notu ekle.

### 3. `description_original` → cookie banner metni (gerçek: ürün açıklaması)

**Sorun:** `_extract_description()` ilk 80-800 karakter paragrafı aldı, cookie banner ("We use cookies to personalise...") yakalandı.

**Düzeltme önerisi:**
- Cookie banner keyword'larını filtrele ("cookie", "personalise content", "social media features").
- "Charming and technical, Cobra..." gibi marka adıyla başlayan paragrafı tercih et.
- Veya: `<meta name="description" content="...">` tag'ini de dene.

### 4. `lightfastness_raw` → None (gerçek: ≥ 6)

**Sorun:** Body text'inde "Lightfastness\n≥ 6​" var (özel `​` karakter — zero-width-space içerebilir).

**Düzeltme önerisi:**
- Label normalize: "Light fastness" + "Lightfastness" + "Light Fastness" hepsini dene.
- Value'da `≥ 6` formatını strip et (`re.sub(r"[^\d.]", "", val)`).

## ⚠️ Kısmi sorunlar

### 5. `variants_raw` boş

**Sorun:** Radio button regex `data-product-attribute-value` Dedar BigCommerce temada eşleşmedi.

**Düzeltme önerisi:**
- BigCommerce stencil tema farklılığı — alternatif selector dene: `input[name="attribute"]`, `[data-sku]`, `.product-attribute__value`.
- Veya Playwright `page.locator()` ile DOM gez.

### 6. `production_model` "unknown" (gerçek: "mixed" veya stokta)

**Sorun:** Cobra'da "Article on request" yok. Sayfada "Current Stock" var (stok bilgisi). Adaptör v1.0 Cobra denetiminde "make_to_order" demişti — bu sefer farklı çıktı (sayfa güncellenmiş olabilir, ya da varyant farklı).

**Düzeltme önerisi:**
- "Article on request" YOK + "Current Stock: X" VAR → `production_model = "stock"`.
- Adaptör'de production_model tespit tablosu güncellenmeli.

### 7. Görsel sayısı 1 (galeri eksik)

**Sorun:** `extract_image_specs()` sayfada sadece 1 ana görsel buldu. Gallery + varyant görseller eksik.

**Düzeltme önerisi:**
- BigCommerce stencil: `.productView-image img`, `.productView-thumbnail img`, swiper galeri parse.
- Adaptör notu: "Çok görsel için galeri scroll + thumbnail click yap" (Katman 2 Chrome MCP).

## Sonraki adımlar (Faz 5 devamı)

1. **Scraper v1.1**: 4 hata düzeltmesi (`width`, `weave`, `description`, `lightfastness`). Tahmini efor: 1-2 saat.
2. **Days Like Now testi**: Scraper v1.1'i ikinci üründe doğrula → Dedar n=2.
3. **Galeri scraper geliştirme**: BigCommerce stencil için tüm görselleri çekme. Tahmini efor: 1 saat.

## Adaptör güncelleme (`adaptorler/dedar.md`)

Yapılacak değişiklik:
- "Type" label'ı için uyarı: "Single sheet/Double sheet form değeri, dokuma değil"
- Description için: "İlk paragraf cookie banner olabilir, marka adıyla başlayan paragrafı tercih"
- Lightfastness: "Value'da `≥` ve zero-width-space karakterleri olabilir"
- production_model: "Current Stock varsa stock, Article on request varsa make_to_order"

Bu sapmalar Cobra ürün JSON'unda `source_data._provenance.field_metadata`'da kaynak işaretiyle korundu (`source: "html_body_manual"` veya `source: "html_body_description"`). Anayasa kural #2 (kanıt zinciri) ihlal edilmedi.
