# Dedar Scraping — Öğrenilen Dersler

**Son güncelleme:** 2026-05-26
**Kapsam:** Dedar BigCommerce platformu (cobra, days-like-now, wide-linen-*, twillman)

Bu doküman, Dedar ürün scrape + denetim sürecinde yapılan hatalar ve çözümlerinin **kalıcı kaydıdır**. Yeni oturum başlarken oku. Aynı hataları tekrar yaşama.

---

## 1. Ana akış: scrape → migrate → link → dashboard

Dedar ürün denetimi 4 aşamada tamamlanır:

```
1) python -m topla.cli https://dedar.com/<slug>/        # Scrape (Python mekanik)
2) topla/scripts/migrate_tier1_gorseller_v2.py          # ham_cikti → gorseller/dedar/<code>/
3) topla/scripts/link_variant_metadata.py               # variants[].color_name + main_image_local_path eşle
4) build_dashboard.py + build_altin_dashboard.py         # HTML rebuild
```

**HER aşama önemli.** Önceki gibi sadece scrape + migrate yaptıysan, dashboard'da varyantların içi BOŞ olur (color_name=null, image-color eşleştirmesi yok).

---

## 2. Scraper bug pattern'leri (v1.2 öncesi)

### 2.1 product_code = None (URL'de ?sku= yoksa)
- **Sorun:** Wide Linen / Twillman gibi `https://dedar.com/<slug>/` URL'lerinde query string yok
- **Sonuç:** product_code=None → _extract_dedar_variants SKU üretemez → _scrape_variant_pages variant page loop yapmaz → high-res variant images alınamaz
- **Düzeltme:** `topla/scrapers/dedar.py` line ~106-114: body_text'ten regex `(00T\d{10})` ile SKU çıkar, product_code = SKU[:8]
- **DİKKAT:** Regex `\d{11}` YANLIŞ — gerçek SKU "00T2204400006" = 00T + 10 digit (8 product + 5 variant - 3 overlap? No: 00T + 10 digit = 13 chars). `\d{10}` doğru.

### 2.2 Default variant variant page loop'ta işlenmiyor
- **Sorun:** URL `/wide-linen-baobab/` 006 senape varsayılana redirect olur. Variant page loop bu URL'i tekrar ziyaret etmez (sonsuz döngü önlemek için).
- **Sonuç:** 8 varyantın 7'sinin variant page main image var, 1'i (default) eksik.
- **Geçici çözüm:** link script default variant için "ana" image'ini fallback olarak atar.
- **Kalıcı çözüm (Faz 6.11+):** Variant page loop'a default variant URL'i de ekle (`?sku=<full_sku_of_first_variant>` ile dummy navigation).

### 2.3 Main page swatch'leri "varyant" tipinde extract ediliyor
- **Sorun:** Dedar BigCommerce main page'inde color picker'da küçük swatch resimleri var (1-5 KB). Scraper bunları `tip="varyant"` olarak yakalıyor.
- **Sonuç:** ham_cikti gorseller listesinde 9 swatch (varyant_adi=None) + N named variant (variant page loop'tan) karışık.
- **Düzeltme:** `link_variant_metadata.py` swatch'leri (`varyant_adi=None`) JSON'a koymaz. Dashboard'a temiz veri gider.

---

## 3. JSON variant metadata eşleştirme

### 3.1 ham_cikti variants_raw yapısı (v1.2)

```json
[
  {"sku": "00T2204400006", "color_suffix": "006", "name": "senape", "main_image_url": "https://cdn11.bigcommerce.com/...1280x1280..."},
  {"sku": "00T2204400001", "color_suffix": "001", "name": "bianco", "main_image_url": "..."},
  ...
]
```

### 3.2 Üst ürün JSON variants[] yapısı (sema v1.3)

```json
[
  {
    "color_code": "00T22044-006",   // <product_code>-<suffix>
    "color_name": "senape",          // <-- variants_raw[].name'den eşleşir
    "main_image_url_source": "https://cdn...1280x1280...",   // <-- variants_raw[].main_image_url
    "main_image_local_path": "gorseller/dedar/00T22044/varyant_NN.jpg"  // <-- disk file'a link
  }
]
```

### 3.3 images.variants[] yapısı

```json
[
  {
    "variant_code": "00T22044-006",
    "color_code": "006",
    "color_name": "senape",
    "url": "https://cdn...",
    "local_path": "gorseller/dedar/00T22044/varyant_10.jpg",
    "alt": "wide-linen-baobab - senape"
  }
]
```

**Eşleştirme algoritması:**
- `varyant_adi` (ham_cikti gorseller entry) → `name_to_suffix[varyant_adi]` → suffix → color_code

---

## 4. Italyan/Fransız renk adları (örnek mapping)

Dedar renk isimleri orijinal dilde kalır (Anayasa #1 conventional). Örnekler:

**Wide Linen Baobab (8):**
- 001 bianco (beyaz) · 002 avorio (fildişi) · 003 mastice (mastik)
- 004 perla (inci) · 005 taupe · 006 senape (hardal)
- 007 canyon · 008 bottiglia (şişe yeşili)

**Wide Linen Signor Darcy (11):**
- 001 bianco · 002 avorio · 003 ardoise (kayrak) · 004 sable (kum)
- 005 rose poudré (toz pembe) · 006 glacier · 007 jonc (kamış)
- 009 perle · 010 charbon (kömür) · 011 mastic · 012 daim (süet)

---

## 5. Görsel hiyerarşi (Dedar'da)

Bir Dedar ürün sayfasında:
1. **Moodboard büyük resim** (1 adet, 1280×1280+) — `tip="ana"`
2. **Moodboard thumbnail/lifestyle** (1-2 adet) — `tip="detay"` veya `tip="lifestyle"`
3. **Color picker swatches** (8-11 adet, 1-5 KB) — `tip="varyant"`, `varyant_adi=None` — **ATLA**
4. **Variant page main images** (8-11 adet, 100-500 KB, 1280×1280) — `tip="varyant"`, `varyant_adi="bianco"` vs.

Dashboard'da gösterilecek olan: 1 + 2 + 4 (NOT 3).

---

## 6. Çözülen "denetlenmiş çelişki" örnekleri

### Cobra (00T19063)
- **Çelişki:** Documents raporu "Stäubli leno yapamaz" diyordu
- **Doğru:** kapasite/staubli_uretim_kapasitesi.md → leno TAM (Stäubli aparat var)
- **Anayasa #7 uygulandı** → leno için 5/5 puan, ALTIN aday (83)

### Broken Twill Sheer (Kvadrat 8108)
- **Çelişki:** slug "broken-twill-sheer" → twill (Stäubli dobby YAPAR) izlenimi
- **Doğru:** HTML field "Construction: Jacquard", description "twill weave **interpretation**" → Kvadrat bunu **jakar tezgahta** dokuyor, twill efekti veriyor
- **Anayasa #7+#8 uygulandı** → 1/5 puan, Mobidik kapasite-dışı, denetime alınmadı

---

## 7. Sonraki oturum kontrol listesi

Bir yeni oturumda Dedar ürün denetlerken:

- [ ] `topla/scrapers/dedar.py` v1.2 olduğunu doğrula (body fallback `\d{10}` regex)
- [ ] `python -m topla.cli <url>` scrape sonrası `ham_cikti/.../variants_raw[].name` dolu mu kontrol et
- [ ] Migrate sonrası: `link_variant_metadata.py` ÇALIŞTIR (variants[].color_name doldur)
- [ ] Dashboard rebuild
- [ ] Tarayıcıda kontrol — varyant kartlarında renk adları görüldüğünü, her renge tıklayınca ona ait görselin açıldığını gör
- [ ] Görüntü kırık mı? Disk'te dosya var mı? `ls gorseller/dedar/<code>/`

---

## 8. Bekleyen iyileştirmeler (Faz 6.11+)

1. **Default variant variant page'i ziyaret et** — şu an 7/8 variant images, 1 eksik
2. **Variant page full gallery** — şu an variant başına 1 image, asıl sitede 2-3 var (kumaş + lifestyle perde foto)
3. **Swatch'ler kullanılabilir alternatif** — eğer variant page erişilemezse swatch'i gözden geçirilmiş low-res olarak göster
4. **Renk swatch'i hex çıkar** — image_analysis ile dominant_color hex (dashboard renk kutusu için)
