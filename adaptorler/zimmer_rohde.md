# Zimmer + Rohde Adaptörü

**Adaptör versiyonu:** v1.0
**Son güncelleme:** 2026-05-25
**Bölge:** alman_alpin
**Marka slug:** zimmer_rohde

---

## Marka Profili Özeti

- **Ülke:** Almanya (Oberursel/Frankfurt merkez)
- **Karakter:** Almanya'nın en büyük yüksek-segment perdelik üreticisi. Z+R Group ana çatı (ADO Goldkante + Etamine + Travers alt markalar). 1956 kuruluş.
- **Üretim modeli:** Z+R Group kendi tezgah parkına sahip Almanya + Belçika (keten için). Vertically integrated.
- **Dil:** İngilizce (kvadrat.dk benzeri /en path), Almanca paralel
- **Bot dostluğu:** Yüksek — TYPO3 CMS, standart user-agent yeterli
- **Veri disiplini:** Ürün sayfasında temel spec'ler statik HTML; technical datasheet PDF ekstra detay (en, gramaj, çekme, abrasion, FR sertifika kodları)
- **Sertifika varsayımı yok:** Her ürünün sertifika seti **kendi datasheet PDF'inden** alınır. Marka geneli "B1/NFPA hepsinde var" iddiası YASAK.

---

## URL Yapısı

```
https://www.zimmer-rohde.com/en/product-finder/details/<urun-slug>-<urun_kodu>
```

Örnekler:
```
https://www.zimmer-rohde.com/en/product-finder/details/melange-linen-10969-980
https://www.zimmer-rohde.com/en/product-finder/details/niket-11051-812
https://www.zimmer-rohde.com/en/product-finder/details/softgrid-10918-694
```

**Ürün kodu formatı:** 8 haneli (örn. `10969980`, `11051812`). Sayfada `XXXXX-NNN` formatında gösterilir (`10969-980`); URL'de tireli + URL-encoded slug.

**Kategori sayfası (tarama için):**
```
https://www.zimmer-rohde.com/en/product-finder?brand=zimmer-rohde&category=curtains
```

---

## Görsel CDN — Z+R Group Ortak

Tüm Z+R Group markaları (Z+R, ADO, Etamine, Travers) aynı TYPO3 instance'ı kullanıyor:

```
https://www.zimmer-rohde.com/fileadmin/_processed_/{x}/{y}/csm_<urun_kodu>_<sira>_<hash>.jpg
```

- `{x}/{y}`: 2 karakterli hash routing (örn. `0/7`, `e/0`)
- `<hash>`: 8 karakterli hex ImageMagick imzası
- `<sira>`: 1-5 arası varyant numarası (renkler veya açılar)
- Renk varyantı pattern'i: `csm_<urun_kodu>_<renk_kodu>_<sira>_<hash>.jpg` veya `csm_<full_kod_with_color>_<sira>_<hash>.jpg`

**Shared fallback:** Bazı renkler için ortak roomshot görseli kullanılır:
```
csm_<base_kod>_rb_<sira>_<hash>.jpg
```

Örn. `11051812_4` → `csm_11051_rb_1_29bee0338f.jpg` (Niket'in 4. görseli markalar koleksiyon roomshot'u).

---

## Alan Eşleştirmesi

| Şema Alanı | Sitedeki Konum | Notlar |
|---|---|---|
| `product_code` | URL son numarası + sayfa `<h1>` altındaki kod | 8 haneli, renk son 3 hane |
| `product_name` | `<h1>` başlık | İngilizce orijinal ad |
| `collection` | "Collection" alanı | Örn. "Abstract", "After The Rain", "SKETCHBOOK" |
| `composition` | "Composition" alanı | "%X Material, %Y Material" formatı; bazen 4+ bileşen |
| `width_cm` | "Width" alanı | cm cinsinden; "Width" sayısal değer + birim |
| `weight_gsm` | Datasheet PDF içinde | HTML sayfada genellikle YOK; PDF'te "Weight: NNN g/m²" |
| `repeat_cm` | "Pattern repeat" / "Repeat" | Vertical + Horizontal cm; sıklıkla "No repeat" |
| `weave_type_raw` | "Construction" veya "Material" alanı | "Plain", "Dobby", "Leno", "Double-layer", "Boucle" |
| `usage_area` | "Use" tag listesi | "Room high", "Curtains", "Drapes" |
| `country_of_origin` | "Made in" veya "Country of origin" | Almanya çoğunluk; Belçika (Belgian Linen), İtalya (Etamine alt markası) |
| `certifications.fire_safety` | Datasheet PDF "Fire performance" | B1, BS 5852, NFPA 701, IMO MED — PDF'te kod listesi |
| `certifications.sustainability` | "Sustainability" sekmesi | European Flax / Belgian Linen / Masters of Linen, OEKO-TEX 100 |
| `description` | "Product description" paragrafı | 2-4 cümle |
| `style_note` | "Design" alt sekmesi (varsa) | Koleksiyon tematik notu |
| `acoustic.alpha_s_value` | "Acoustic" alanı (sadece akustik ürünlerde) | αs değer |

---

## Dokuma Yapısı Normalizasyonu

| Sitedeki ifade | Normalize değer | Stäubli notu |
|---|---|---|
| Plain | plain | TAM |
| Dobby | dobby | TAM (ana fonksiyon) |
| Jacquard | jacquard | YOK (Stäubli armür, jakar değil) |
| Leno / Gauze / Grid leno | leno | TAM (kapasite tablosu: aparat var + aktif üretim) |
| Boucle | dobby (boucle iplikli) | TAM ama özel iplik tedariki |
| Double-cloth / Double-layer | double_cloth | Kontrol gerek — 8-12 çerçeve, programlama karmaşık |
| Sheer / Voile / Curtain weave | sheer | TAM (plain altkümesi) |
| Crepe / Crepe-effect | crepe | TAM (Stäubli için orta) |

**Çelişki uyarısı:** Documents iterasyonunun eski raporlarında "Stäubli leno yapamaz" iddiası VAR — ancak kapasite/staubli_uretim_kapasitesi.md (kullanıcı doğrulamalı): "Leno (giz) | TAM | Aparat var + aktif üretim var". Anayasa kural #7'ye göre **kapasite kazanır**. Niket (11051-812) gibi leno ürünler için staubli_feasibility=4-5/5 olmalı, 1/5 değil.

---

## Varyant Yönetimi

**Sunum şekli:** Ürün sayfasında renk grid'i, her renk için ürün kodu varyantı (örn. `10969-980` = ürün `10969`, renk `980`).

**Görsel adlandırma kuralı (eski 02_gorseller/):**
```
<urun_kodu><renk_kodu>_<sira>.jpg
```
Örn. `10969980_1.jpg`, `10969980_2.jpg` ... `10969980_5.jpg`

**Yeni konvansiyon (gorseller/):**
```
gorseller/zimmer_rohde/<urun_kodu>/<renk_kodu>_<sira>.jpg
```
Örn. `gorseller/zimmer_rohde/10969/980_1.jpg`

**Renk varyantı sayısı:** Genellikle 3-12 renk. Melange Linen 10 ton, Softgrid 12 ton, Loops 3 ton.

---

## Görsel Çekme Kuralları

**Görsel sıralaması (genelde):**
1. `_1.jpg` — Ana ürün görseli (yakın çekim, doku)
2. `_2.jpg` — Düz arka plan, ölçü hissi
3. `_3.jpg` — Detay/close-up
4. `_4.jpg` — Lifestyle (oda kurulumu) — bazen shared `_rb_`
5. `_5.jpg` — Alternatif lifestyle veya teknik

**Çekme katmanı:** Layer 1 (direct HTTP fetch) — `requests` yeterli, Vue.js render gerek yok. Hash-based URL'ler resolve edilebilir.

---

## PDF Technical Datasheet — Önemli Kaynak

Z+R her ürün için "Technical specifications" altında PDF datasheet yayınlar. Pattern:

```
https://www.zimmer-rohde.com/fileadmin/user_upload/_datasheets_/Z+R_<urun_kodu>_<lang>.pdf
```

**PDF'te genellikle bulunan (HTML'de YOK):**
- Tam `weight_gsm` (g/m²)
- `abrasion_martindale` (devir sayısı)
- `pilling` (ISO sınıfı)
- `shrinkage` warp/weft % değerleri
- `fire_performance` sertifika kodları (B1, BS 5852, NFPA 701, IMO MED)
- `lightfastness` ISO 105-B02 skoru
- Tam `composition` (% breakdown)

**Strateji:** HTML sayfasından temel veri + PDF'ten teknik tamamlama. Her alan için `_provenance.field_metadata.source = "html" | "technical_spec_pdf" | "html_and_pdf_consistent"`.

---

## Bilinen Eksiklikler

- [ ] `price_per_meter` — Hiç publike değil (B2B-only)
- [ ] `moq_meters` — Distribütörden sorulur
- [ ] `country_of_origin` — Genellikle var (Almanya/Belçika); bazen yok
- [ ] `thread_density` — Hiç publike değil → AI inference adayı
- [ ] `acoustic` — Sadece akustik ürünlerde dolu

---

## Çekirdek Koleksiyonlar (referans)

| Koleksiyon | Tema | Tipik ürünler |
|---|---|---|
| **Abstract** | Mélange + boucle premium | Melange Linen, Loops |
| **After The Rain** | Polyester drape, teknik | Niket (leno), Ishari (double), Nuri (crosshatch) |
| **SKETCHBOOK** | Karışım iplik tasarım | Softgrid |
| **Heritage** | Klasik desen jakar | (yer almıyor) |

---

## Kategori Tarama Stratejisi

```
1. https://www.zimmer-rohde.com/en/product-finder?brand=zimmer-rohde
2. "Load more" / pagination ile tüm ürün kartlarını yükle
3. Her kart için: <a href> → product detay URL + thumbnail
4. Liste: [{url, product_name, product_code, thumbnail}, ...]
```

**Toplam Z+R curtain ürünü tahmini:** ~60-80 aktif

---

## Anormallik İmzaları

- Eğer `width_cm` 320'den büyük → kontrol et (Mobidik kapasitesi max 360 cm)
- Eğer composition yüzdeleri %100 toplamıyorsa → kontrol et
- "Construction" alanı boşsa → PDF datasheet zorunlu
- Yangın sertifikası HTML'de "European fire standards" gibi muğlak ifade → spesifik kod (B1, BS, NFPA) yoksa `certifications.fire_safety` BOŞ kalır (kural #3)

---

## Versiyon Geçmişi

- **v1.0** (2026-05-25): İlk sürüm — Documents iterasyonundan migrasyon sırasında inşa edildi. Kvadrat adaptör v1.2 şablon. Z+R Group ortak CDN pattern'i + marka-özel farklar (ADO 7-hane kod, Etamine Fransızca koleksiyon adları, Travers Amerikan tematik) belgelendi. Kapasite çelişki uyarısı (leno + double-cloth) eklendi.
