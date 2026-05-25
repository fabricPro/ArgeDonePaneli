# Kvadrat Adaptörü

**Adaptör versiyonu**: v1.0
**Son güncelleme**: 2026-05-12
**Bölge**: nordik
**Marka slug**: kvadrat

---

## Marka Profili Özeti

> **Denetim notu (2026-05-13)**: Bu özet kalibrasyon test #1 marka profili denetiminden sonra GÜNCELLENDİ. İddialar resmi `kvadrat.dk/en/about/our-company` ve Wikipedia kanıtlarıyla doğrulandı.

- **Ülke**: Danimarka (resmi: dogrulandi)
- **Merkez**: Ebeltoft, Danimarka (Wikipedia + LinkedIn: dogrulandi)
- **Kuruluş**: 1968 (kvadrat.dk + Wikipedia: dogrulandi)
- **Kurucular**: Poul Byriel, Erling Rasmussen (Wikipedia: dogrulandi)
- **CEO**: Anders Byriel (Wikipedia: dogrulandi)
- **Çalışan sayısı**: 691 (LinkedIn snippet, ~501-1000 aralık)
- **Karakter**: İskandinav design tradition — high-performance, design textiles + rugs + window covering + acoustic solutions (resmi sayfa). "Minimalist" yorumu adaptörün kendi gözlemi, resmi konumlandırma değil.
- **Veri disiplini**: HTML sayfalarında bazı alanlar Vue.js render gerektiriyor (width/weight/lightFastness/sertifika listesi/varyant kodları). PDF technical spec öncelikli kaynak (image-only Word export → OCR şart).
- **Bot dostluğu**: Yüksek — engelleyici sistem yok, normal user-agent yeterli
- **Dil**: İngilizce (kvadrat.dk/en kullan; .dk EN tercih)
- **Üretim modeli**: Kvadrat **kendi tezgah sahibi** İngiltere, Norveç, Hollanda'da (resmi sayfa). Air Line "Türkiye'de üretiliyor" → bu liste dışı; muhtemelen **fason üretim ortağı**. Stratejik istihbarat: hangi Türk tedarikçi?
- **Garanti**: Çoğu tekstilde 10 yıl garanti (resmi sayfa). Air Line 2 yıl — alt segment olabilir.
- **Sürdürülebilirlik**: ISO 14001 (1997'den beri), LCA + EPD EN15804 framework, EU Ecolabel "majority of woollen products". Bu yön resmi sayfada güçlü vurgu.
- **Tasarımcı işbirlikleri**: Patricia Urquiola, Ronan & Erwan Bouroullec, Margrethe Odgaard, Alfredo Häberli, Doshi Levien, Peter Saville, Olafur Eliasson, Raf Simons, Hella Jongerius vb. (resmi + Wikipedia)
- **Anıtsal projeler**: Gherkin, MoMA, Walt Disney Concert Hall, Reichstag, Guggenheim Bilbao, Foster & Partners, Oslo/Copenhagen Opera (Wikipedia)
- **Ortaklıklar**: Wooltex UK (49%, 2011), Really (52%, 2017 — circular/upcycle)
- **Showroomlar**: Kopenhag (flagship), Stockholm (flagship), New York, Los Angeles, Paris, Londra, Milano

> **Sertifika varsayımı yok** — Kvadrat'ın "her ürün B1/NFPA/OEKO-TEX sertifikalı" gibi bir genel kuralı YOKTUR. Air Line denetiminde bu kanıtlandı (yangın sertifikası YOK, OEKO-TEX YOK). Her ürün için sertifika listesi **ürünün kendi PDF/HTML kanıtından** alınır.

---

## URL Yapısı

```
https://www.kvadrat.dk/en/products/curtains/{kod}-{urun-slug}
```

Örnek:
```
https://www.kvadrat.dk/en/products/curtains/5539-air-line
```

**Renk varyantı URL pattern'i**: Aynı sayfada dropdown ile yönetilir. Varyant seçildiğinde URL hash değişebilir (`#variant=...`).

**Kategori sayfası** (tarama için):
```
https://www.kvadrat.dk/en/products/curtains
```

---

## Alan Eşleştirmesi

| Şema Alanı | Sitedeki Konum | Notlar |
|------------|----------------|--------|
| `product_code` | URL'deki başlangıç sayısı (örn. "5539") | |
| `product_name` | `<h1>` başlık | |
| `collection` | Genelde yok, ürün başlığıyla aynı | null |
| `composition` | "Composition" başlığı altı | "70% New Wool, 30% Polyester" formatında |
| `width_cm` | "Width" alanı | Cm cinsinden açık yazılı |
| `weight_gsm` | "Weight" alanı | Genelde var, "g/m²" birimi |
| `repeat_cm` | "Pattern repeat" | "Vertical / Horizontal" formatında veya "No repeat" |
| `weave_type_raw` | "Construction" alanı | |
| `usage_area` | "Use" alanı | |
| `certifications.fire_safety` | "Flame retardant" listesi | |
| `certifications.sustainability` | "Sustainability" sekmesi | EU Ecolabel, C2C, OEKO-TEX |
| `description` | İlk paragraf | |
| `style_note` | "Design" sekmesi (varsa) | |
| `acoustic.alpha_s_value` | "Acoustics" alanı (varsa) | Sayısal değer |

---

## Dokuma Yapısı Normalizasyonu

| Sitedeki ifade | Bizim normalize değerimiz |
|----------------|---------------------------|
| "Plain weave" | plain |
| "Twill" | dobby |
| "Jacquard" | jacquard |
| "Leno" | leno |
| "Voile" | sheer |
| "Sheer" | sheer |
| "Boucle" | dobby (özel notla) |

---

## Varyant Yönetimi

**Sunum şekli**: Aynı sayfada renk grid'i. Her renk için ayrı küçük görsel + renk kodu.

**Varyant verisi çekme stratejisi**:
```
1. Sayfayı yükle
2. ".color-variants" container'ındaki tüm öğeleri bul
3. Her variant için:
   - data-color-code attribute → color_code
   - aria-label veya tooltip → color_name
   - <img src> → main_image_url_source (küçük resim)
4. Her renge ardışık tıkla (JavaScript click event):
   - Modal/lightbox açılır → yüksek çözünürlüklü görsel
   - URL'i kaydet, modal'ı kapat, sonraki renge geç
```

Bu işlem Katman 2 (Claude in Chrome) gerektirir çünkü tıklama gerekiyor.

---

## Görsel Çekme Kuralları

**Ana ürün görseli**:
- Konum: Sayfa üst kısmı, büyük slider
- Yüksek çözünürlük: `srcset` içindeki en büyük URL veya zoom modal

**Varyant görselleri**:
- Konum: Renk seçici altında küçük kareler
- Çekme: Her renge tıkla → modal'daki yüksek çözünürlüklü URL

**Lifestyle görseller**:
- Konum: "Inspiration" sekmesi veya sayfanın alt kısmı
- Önemi: Yüksek — Kvadrat lifestyle çekimleri stil/bağlam analizinde değerli

**Close-up / teknik görseller**:
- Konum: Genelde ana slider'da 3-4. görsel olarak
- Notlar: Doku ve iplik analizi için ideal kalitede

**Önerilen indirme katmanı**: Katman 2 (Chrome) — varyant tıklamaları gerektiği için.

---

## Bilinen Eksiklikler

Kvadrat genel olarak veri zengini ama bazen şunlar yok:

- [ ] `price_per_meter` — Hiçbir zaman yayınlanmaz (B2B)
- [ ] `moq_meters` — Site'de değil, distribütörden öğrenilir
- [ ] `country_of_origin` — Bazen var, bazen yok
- [ ] `thread_density` — Hiç yayınlanmaz → AI tahmin edilebilir
- [ ] `acoustic` — Sadece akustik perdelerde dolu

---

## Site-Özel Kurallar

- Sayfa Vue.js ile render edilir → sayfa yüklemesinden sonra **2-3 saniye bekle** (DOM'un dolması için)
- "Add to favorites" gibi etkileşimleri tıklama — sadece veri çek
- Cookie banner çıkarsa "Accept" yerine "Reject all" tercih et (gizlilik için)
- Kvadrat'ın iki sitesi var: kvadrat.dk ve kvadrat.com. **Her zaman .dk EN versiyonunu kullan** — daha güncel ve tam.

---

## Bilinen Altyapı Host'ları

Kvadrat'ın ana site (`kvadrat.dk`) dışında veri/dosya sunduğu altyapı host'ları. Provenance set yönetimi ve fetch onayı için referans listesi.

| Host | Amaç | Onay durumu |
|------|------|-------------|
| `www.kvadrat.dk` | Ana ürün sayfaları (HTML) | **onaylı** — varsayılan |
| `kvadrat-downloadcenter.azurewebsites.net` | Technical specification PDF'leri, lightfastness sertifikaları, görsel arşiv (`/downloadimages/<kod>`) | **onaylı** — Kvadrat'ın resmi download center'ı |

**Kural**: Sadece yukarıda listelenen host'lar onaylıdır. Başka herhangi bir `*.azurewebsites.net` subdomain'i veya üçüncü taraf host **manuel kullanıcı onayı ister** — provenance set'e otomatik girmez.

**Pratik not**: `web_fetch` tool'u URL'leri yalnızca kullanıcı mesajı veya önceki fetch çıktısı içinden tanır. Anchor tag'ten URL keşfi otomatik provenance vermez — bu nedenle PDF gibi yan host'lar için kullanıcı URL'i mesajına **tek satır olarak** yapıştırmalı (satır kırığı parser'ı yanıltabilir).

---

## PDF Technical Spec

Kvadrat ürünlerinin önemli bir kısmında "Technical specifications" linkiyle erişilebilen bir PDF teknik şartname yayınlanır. Yapı:

```
https://kvadrat-downloadcenter.azurewebsites.net/api/downloadcenter/
  assets/<asset-id>/T_<urun_kodu>_stechnical-specification.pdf
```

**Genel kural**:
- **Varlığı garanti DEĞİL** — bazı ürünlerde link var, bazılarında yok.
- **Bulunduğunda öncelikli kaynaktır** — özellikle HTML sayfasının config-bağımlı (Vue.js render gerektiren) alanları için: `width_cm`, `weight_gsm`, sertifika listesi, abrasion, lightfastness sayısal değeri.
- **Bulunmadığında AI inference ile DOLDURULMAZ** — sertifikasyon, weight, width gibi PDF-tipik alanlar PDF yoksa `null` kalır ve `missing_fields`'a girer. Tahmin için sadece şu alanlar aday: `thread_density`, `light_transmission` (close-up görsel + composition+transparency kombinasyonu ile), `repeat_cm` (görsel ölçümle).

**Çekme stratejisi**:
1. HTML sayfasında "Downloads → Product information → Technical specifications" linki var mı kontrol et
2. Varsa: URL'i provenance set'e dahil et (üst host onaylı), PDF'i çek
3. PDF'ten çıkan her alan için kayıt formatı:
   ```json
   {
     "value": <değer>,
     "source": "technical_spec_pdf",
     "source_url": "<pdf url>",
     "page_number": <sayfa>,
     "extracted_at": "<ISO 8601>",
     "extraction_confidence": "exact" | "interpreted"
   }
   ```
   - `exact`: PDF'te birebir yazılı (örn. tablo hücresi "Width: 300 cm")
   - `interpreted`: PDF'te yorumlanmış olarak çıkıyor (örn. "European fire standards" gibi muğlak ifade — bu durumda alan **null bırakılır**, `extraction_notes` ile açıklanır)
4. PDF'te yoksa: `null` + `missing_fields`'a ekle. PDF'in **olmadığı** da bir bilgidir — `data_quality.notes`'a "PDF'te alan X bulunmadı" notu düş.

**Muğlak ifadeler ASLA source_data'ya yazılmaz**: "European fire standards", "Various certifications", "Suitable for contract use" gibi ifadeler kanıt değildir. Spesifik kod (B1, BS 5852, NFPA 701 vb.) yoksa `certifications` boş kalır.

---

## Kategori Tarama Stratejisi

**Tüm ürün listesi**:
```
1. https://www.kvadrat.dk/en/products/curtains adresine git
2. "Load more" butonuna basarak tüm ürünleri yükle (yaklaşık 80-120 ürün)
3. Her ürün kartı için href'i topla
4. Liste oluştur: [{url, product_name, product_code}, ...]
```

**Sayfalandırma**: Infinite scroll + "Load more" hibridi.

**Toplam tahmini ürün sayısı**: ~110 perdelik ürün

---

## Anormallik İmzaları

> **Denetim notu (2026-05-13)**: Bu bölümün "width_cm 320'den büyük veya 100'den küçük" eşiği **Kvadrat ürünlerinden gerçek aralık doğrulanması bekliyor**. Air Line denetiminde gerçek genişlik 315 cm çıktı (320 sınırına çok yakın); bu sınır küçük bir örneklemle ileri taşınabilir. Bilgi olarak korunuyor, mutlak güvenli eşik kabul edilmemeli — adaptör v1.2'de gerçek dağılım hesaplandığında güncellenecek.

- Eğer `width_cm` 320'den büyük veya 100'den küçük görünüyorsa → kontrol et (eşik provisional, daha çok kanıt gerek)
- Eğer composition yüzdeleri %100 toplamıyorsa → kontrol et (Kvadrat'ta nadir — bu gözlem Kvadrat'ın veri disiplininden geliyor, doğrulanmış varsayım değil)
- Eğer "Construction" alanı boşsa → bu garip, manuel inceleme önerilir

---

## Versiyon Geçmişi

- **v1.0** (2026-05-12): İlk sürüm
- **v1.1** (2026-05-13): Kalibrasyon testi #1 (Air Line) sonrası eklendi:
  - "Bilinen Altyapı Host'ları" bölümü — `kvadrat-downloadcenter.azurewebsites.net` onaylandı
  - "PDF Technical Spec" bölümü — varlığı garanti değil, bulunduğunda öncelikli, bulunmadığında AI inference yapılmaz
  - Vue.js render konusunda Katman 1 sınırı somut deneyimle doğrulandı: width_cm, weight_gsm, sertifika listesi, varyant kodları HTML fetch ile alınamadı; PDF veya Katman 2 gerekli
- **v1.2** (2026-05-13): Marka profili denetimi sonrası eklendi:
  - "Marka Profili Özeti" bölümü resmi kanıtlarla yeniden yazıldı (Ebeltoft, 1968, kurucular, CEO, mill ownership, designer roster, ortaklıklar, showroomlar, anıtsal projeler — hepsi kvadrat.dk/en/about/our-company + Wikipedia teyitli)
  - **Sertifika varsayımı KALDIRILDI** — "her üründe B1/NFPA/OEKO-TEX" gibi kategorik iddialar yasak; her ürün için sertifika listesi o ürünün kendi kanıtından alınır
  - "Anormallik İmzaları" bölümüne provisional eşik notu eklendi (320 cm sınırı Air Line'ın 315'iyle çok yakın — gerçek dağılım gerekiyor)
  - Üretim modeli netleştirildi: Kvadrat tezgahları İngiltere/Norveç/Hollanda'da, Air Line Türkiye üretimi muhtemelen fason ortak
  - Air Line 2-yıl garantisi resmi 10-yıl politikasıyla çelişiyor — Air Line alt segment olabilir notu
