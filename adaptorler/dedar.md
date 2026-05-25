# Dedar Adaptörü

**Adaptör versiyonu**: v1.0 (denetlenmiş)
**Son güncelleme**: 2026-05-13
**Bölge**: italyan
**Marka slug**: dedar
**Denetim raporu**: `99_kalite_kontrol/referans_denetimi_dedar_cobra.md`
**Test ürünü**: Cobra (00T19063) — Fire-retardant outdoor sheer

> ⓘ **Denetim durumu**: Bu adaptör Cobra ürün testiyle (2026-05-13) doğrulandı. Sertifika tahmini ve "Width 137-140 cm standart" gibi kanıtsız iddialar SİLİNDİ. Mevcut bilgi 1 ürün üzerinde test edildi; daha fazla ürün eklendikçe genişler.

---

## URL Yapısı

```
https://dedar.com/{urun-slug}/?sku={sku-kod}
```

Örnek:
```
https://dedar.com/cobra/?sku=00T1906300004
https://dedar.com/days-like-now/?sku=00T2500700001
```

**Renk varyantı**: URL'deki `?sku=` parametresi değişir. Ürün sayfası varsayılan açıldığında ilk varyantın SKU'suna otomatik redirect yapar (örn. `/cobra/` → `/cobra/?sku=00T1906300004`). Radio button ile varyant değiştirilirse URL yenilenir.

**Kategori sayfaları**:
```
https://dedar.com/products/                  (tüm ürünler)
https://dedar.com/products/curtain/          (perdelik)
https://dedar.com/products/sheer/            (sheer)
https://dedar.com/products/indoor-outdoor/   (indoor/outdoor)
https://dedar.com/products/fire-retardant/   (FR)
https://dedar.com/products/jacquard/         (jakar)
https://dedar.com/products/velvet/           (kadife)
```

Filtreli arama: `https://dedar.com/products/?_bc_fsnf=1&families=...` veya `?_bc_fsnf=1&typologies=...`

**Önemli düzeltme**: Eski adaptör `/curtains/` ve `/sheers/` URL'leri veriyordu — gerçek paterni `/products/{kategori}/`. Eski URL'ler çalışmaz.

---

## Platform Altyapısı

- **E-ticaret platformu**: BigCommerce stencil
- **Görsel CDN**: `cdn11.bigcommerce.com/s-td9auqdllx/...` (tüm Dedar görselleri)
- **Görsel boyut paterni**: `.../images/{img_id}/1__{hash}.{timestamp}.{w}.{h}.jpg` — yüksek çözünürlük için 1280x1280 versiyonu: `.../images/stencil/1280x1280/products/{prod_id}/{img_id}/...`

---

## Bilinen Altyapı Host'ları

Dedar'ın resmi domain dışında veri/dosya sunduğu altyapı host'ları.

| Host | Amaç | Onay durumu |
|------|------|-------------|
| `dedar.com` | Ana ürün sayfaları (HTML), kategori sayfaları, FR filtreli aramalar | **onaylı** — varsayılan |
| `cdn11.bigcommerce.com` | Görsel CDN (BigCommerce e-ticaret altyapısı). Dedar resmi `dedar.com` sayfalarından anchor olarak link ediliyor → provenance otomatik kabul edilir | **onaylı (2026-05-13 onayı, Cobra denetimi sonrası)** |

**Önemli kural**: Sadece `cdn11.bigcommerce.com` subdomain'i onaylı. Başka BigCommerce subdomain'i (`cdn3`, `cdn5`, `cdn12`, vb.) çıkarsa **manuel kullanıcı onayı gerektirir** — provenance set'e otomatik girmez. Bu politika Kvadrat `kvadrat-downloadcenter.azurewebsites.net` host'uyla aynı disiplin.

**Pratik not**: BigCommerce stencil platformu genelde tek CDN subdomain'i kullanır (mağaza başına `s-{store_id}` parametre değişiklği). Dedar için `s-td9auqdllx` mağaza ID'si — değişirse adaptör güncellenir.

---

## Sayfa Davranışı

- **Cloudflare**: Sayfa Cloudflare arkasında — cookies ve fingerprint kontrolü var. Cobra testinde **bot challenge çıkmadı**, web_fetch normal user-agent ile doğrudan başarılı oldu. Yine de challenge gelirse Chrome MCP (Katman 2) ile aşılır.
- **JS render**: Sayfanın çoğu Specifications, Certifications, açıklama, Maintenance dahil **HTML render** (web_fetch'te tam içerik var). "Download" accordion içeriği muhtemelen JS-render (varsa Chrome MCP gerek).
- **Cookie banner**: "Use necessary cookies only" tercih et (privacy için).

---

## Alan Eşleştirmesi

| Şema Alanı | Sitedeki Konum | Notlar |
|------------|----------------|--------|
| `product_code` | SKU'nun ilk 8 hanesi (örn. "00T19063") | Son 5 hane (örn. "00004") varyant kodu |
| `product_name` | `<h1>` veya `og:title` veya breadcrumb | Cobra: og:title="Cobra" |
| `collection` | Sayfa başlığı / breadcrumb | Belirsizlik olabilir — koleksiyon mu, ürün ailesi mi, kategori mi? Cobra: "Enjoyable Indoors / Enjoyable Outdoors" hem koleksiyon başlığı hem kategori gibi gözüküyor. Şema önerisi: collection array olabilmeli (dual-listing) |
| `composition` | Specifications tablosu | "100% Fire-retardant Polyester" gibi metin. Spesifik marka adı (Trevira CS vb.) genelde verilmez — fiber_commercial null |
| `width_cm` | Specifications tablosu "Width: X cm" | Cobra: 325 cm. Dedar'da geniş ürün çeşitliliği var — standart aralık varsayma |
| `weight_gsm` | Specifications "Weight" | Genelde **boş** — Dedar bu alanı yayınlamayabilir (Cobra'da boş) |
| `repeat_cm` | Specifications "Pattern repeat" / "Rapporto" | Cobra leno yapı, makro rapor yok |
| `weave_type_raw` | **Spec tablosu olabilir VEYA açıklamada** | Cobra: Specifications'ta "Type" alanı yok, açıklamada "leno weave" |
| `transparency` | Yarısı kategori (sheer altında listeli), yarısı açıklama | Dedar explicit transparency derece (semitransparent vb.) beyan etmiyor — usage etiketi "Transparency" var ama bu kategori, derece değil. AI light_transmission inference olabilir |
| `usage_area` | Specifications "Usage" + breadcrumb kategori | Cobra: "Transparency" usage + "indoor-outdoor" kategori |
| `performance.lightfastness` | Specifications | Cobra: "≥ 6" — ISO standart adı genelde verilmez |
| `certifications.fire_safety` | "Certifications" bölümü | **Sertifikalar ÜRÜN bazlıdır**, marka geneli varsayım yapılmaz. Cobra: IMO MED Part. 7, FR Italy Class 1, BS5867/2/B |
| `certifications.sustainability` | "Certifications" bölümü | Cobra: "Oekotex" — tam program adı (Standard 100 mu, Made in Green mi) genelde verilmez; interpreted |
| `commercial.country_of_origin` | Specifications "Made in" | Cobra: Italy |
| `commercial.lead_time_days` | "Stock check" → "Production order lead time" | Cobra: 10 weeks = 70 gün. NOT: `commercial.production_model` ile birlikte değerlendir (make_to_order ise lead time uzun) |
| `commercial.production_model` | "Article on request" etiketi varsa make_to_order | Cobra: "Article on request" — make_to_order |
| `description_original` | Üst paragraf | Genelde EN, hikaye odaklı tek paragraf |
| `style_note` | Tek bölüm değil, dağınık | Specifications + bakım + üretim notlarından toplanır |

---

## Dokuma Yapısı Normalizasyonu

| Sitedeki ifade | Normalize | Notlar |
|----------------|-----------|--------|
| Plain | plain | |
| Jacquard | jacquard | |
| **Leno** | leno | Cobra'da test edildi — explicit "leno weave" |
| Embroidery | jacquard | "embroidered curtain" notu eklenir; Stäubli'de doğrudan yapılamaz (ayrı nakış süreci) |
| Sheer | sheer | Kategori etiketi olarak; dokuma değil — gerçek weave farklı olabilir (örn. Cobra "sheer kategori altında ama dokuma leno") |
| Velvet | dobby | "velvet pile" notu |
| Boucle | dobby | |

---

## PDF Technical Spec — Politika

> **Cobra denetiminde fark edildi**: Dedar her ürün için PDF technical spec **YAYINLAMIYOR**. Cobra'da Download accordion'unda PDF linki yok.

**Kural**:
- **Varlığı garanti DEĞİL** (Kvadrat'tan farklı — Kvadrat çoğu üründe PDF verir).
- Bulunduğunda öncelikli kaynaktır (HTML render eksikliklerini kapatır).
- Bulunmadığında HTML zaten zengin (Dedar HTML render disiplini iyi — Specifications tablosu, Certifications, açıklama hepsi web_fetch'te erişilebilir).
- **Bulunmadığında AI inference yapılmaz** — width, sertifika, weight gibi alanlar yoksa null + missing_fields'a eklenir.

---

## Varyant Yönetimi

**Sunum**: Ürün sayfasında radio button grid (Cobra'da 2 varyant: 002 White, 004 Linen,Beige). Her renk için SKU + isim listeli, click → URL yenilenir.

**Strateji**:
1. Ana sayfayı çek (varsayılan SKU'ya redirect)
2. Radio button listesinden tüm SKU'ları + isimleri topla
3. Her varyant URL'sini ayrı sayfa olarak işle (color_code = SKU son 5 hane, color_name = etiket)
4. Master `product_code` = SKU ilk 8 hanesi

**Önemli**: Dedar varyantları **ayrı URL** olarak görüldüğü için aynı ürünün varyantları "yeni ürün" gibi algılanmamalı. Dedupe SKU ilk 8 hanesiyle.

---

## Görsel Çekme Kuralları

**Ana ürün görseli**:
- Konum: Sayfa üstündeki büyük görsel
- CDN: `cdn11.bigcommerce.com/s-td9auqdllx/...`
- Yüksek çözünürlük: URL'deki `stencil/634x750/` veya `386.513` yerine `stencil/1280x1280/` ile değiştir

**Varyant görselleri**:
- Her varyant SKU'sunun kendi görseli var

**Lifestyle görseller**:
- "Inspiration" bölümü (Cobra'da bu bölüm var ama içerik test edilmedi)
- Önemi: Yüksek — Dedar mood çekimleriyle ünlü

**Close-up**:
- Ürün galerisinde 2-3. görsel
- Çok yüksek çözünürlüklü

**Önerilen indirme katmanı**: Katman 1 (direkt CDN) — BigCommerce CDN doğrudan erişilebilir, modal tıklama gerekmiyor.

---

## Bilinen Eksiklikler

- [ ] `price_per_meter` — Hiç yayınlanmaz (B2B; "Price on request")
- [ ] `thread_density` — Yayınlanmaz
- [ ] `acoustic.alpha_s_value` — Sadece akustik özel ürünlerde (test edilmedi)
- [ ] `weight_gsm` — Bazı ürünlerde boş (Cobra: boş)
- [ ] `yarn_type` — Genelde belirtilmez (Cobra: yok)
- [ ] `launch_year` — Sayfada belirtilmez (Cobra: yok)
- [ ] `design_credit.designer` — Bazı ürünlerde belirtilmez (Cobra: yok)
- [ ] PDF technical spec — bazı ürünlerde yok (Cobra: yok)
- [ ] Sertifika test report numbers — sayfada yok

---

## Sertifika Yaklaşımı (denetim kazanımı)

> **Önemli**: Sertifikalar **ÜRÜN bazlıdır, marka geneli varsayım yapılmaz**. Eski adaptör "çoğunlukla M1, BS 5852" diyordu — Cobra'da bunların **hiçbiri yok** (Italy Class 1, BS5867/2/B var). Eski iddia SİLİNDİ.

Dedar ürünlerinde gözlenmiş sertifika kategorileri (Cobra örneğinden):

- **Denizcilik FR**: IMO MED Part. 7 (yat/gemi)
- **Pazar-özel FR**: Italy Class 1 (UNI 9176/9177 muhtemel), UK BS5867/2/B (perde özel)
- **Sürdürülebilirlik**: "Oekotex" (tam program adı genelde verilmez)

Her ürün için sayfa "Certifications" bölümü birebir okunur; standart adları **birebir** kaydedilir (M1 ≠ Italy Class 1, BS 5852 ≠ BS5867 — bu standartlar farklıdır).

---

## Kategori Tarama Stratejisi

```
1. https://dedar.com/products/sheer/  (veya başka alt kategori)
2. Lazy load — sayfa sonuna scroll
3. Her ürün kartı için ana ürün href'ini topla
4. SKU ilk 8 hanesi ile dedupe
5. Toplam: ~150-200 perdelik ürün (akustik dahil — kullanıcının verdiği tahmin, doğrulanmadı)
```

---

## Anormallik İmzaları (denetim sonrası temizlendi)

> Eski "Width 137-140 cm standart" iddiası SİLİNDİ — Cobra 325 cm extra-wide ile yanlışlandı. Dedar'da geniş ürün çeşitliliği var.

- Composition'da "Various" yazıyorsa → kompozisyon paylaşılmıyor, manuel kontrol gerekir
- "Embroidered" ürünlerde Stäubli yapılabilirlik düşük puanlanır (nakış ayrı süreç)
- Certifications bölümü tamamen boşsa → kontrol et (Cobra zengin set verdi, beklemiyorsa şüphe)

---

## Versiyon Geçmişi

- **v0** (2026-05-12): İlk sürüm (denetlenmedi — karantinada: `99_kalite_kontrol/karantina/_adaptorler_v0_denetlenmedi/dedar.md`)
- **v1.0** (2026-05-13): Cobra denetimi sonrası temizlenmiş. Cold storage bayrağı çıkarıldı. Değişiklikler:
  - SİLİNEN: "Çoğunlukla M1, BS 5852" (sertifika tahmini — anayasa #3 ihlali, kanıtlanmış)
  - SİLİNEN: "Width 137-140 cm standart" (kategori silen genelleme — yeni türde ihlal, kanıtlanmış)
  - SİLİNEN: Marka profili özeti (denetlenmedi; marka profili inşası ayrı süreç, adaptörde olmaz)
  - DÜZELTİLEN: Kategori URL'leri `/curtains/` → `/products/curtain/`
  - DÜZELTİLEN: Dokuma normalize tablosuna "Leno" satırı eklendi
  - EKLENEN: "PDF Technical Spec — Politika" bölümü (Cobra'da yok, varlık garanti değil)
  - EKLENEN: "Platform Altyapısı" bölümü (BigCommerce + CDN)
  - EKLENEN: "Sertifika Yaklaşımı" bölümü (ürün bazlı, marka geneli varsayım yasak)
  - EKLENEN: `commercial.production_model` alanı (Cobra make_to_order)
  - EKLENEN: Dual-listing belirsizliği uyarısı (collection alanı için)
