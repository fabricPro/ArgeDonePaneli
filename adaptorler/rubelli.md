# Rubelli Adaptörü

**Adaptör versiyonu:** v1.0 (Charles canlı testinden önce, taslak)
**Son güncelleme:** 2026-05-26
**Bölge:** italyan
**Marka slug:** rubelli
**Test ürünü (planlı):** Charles (30750) — Cotton/Viscose/Linen moiré upholstery

> ℹ️ **Denetim durumu:** Adaptör taslağı (v1.0). WebFetch ile rubelli.com keşfedildi, Charles 30750 yapısı analiz edildi ama henüz **Playwright canlı test yapılmadı**. İlk test sonrası v1.1'e güncellenir (Dedar pattern'i).

---

## Marka Profili Özeti

- **Ülke:** İtalya (Cucciago / Venedik)
- **Kuruluş:** 1858 (Venedik) — **170 yıllık** premium tekstil markası
- **Karakter:** Damask, jakar, brokar, moiré, velvet — klasik Venedik dokuma geleneği + çağdaş tasarımcı işbirlikleri (Formafantasma, vb.)
- **Üretim:** Cucciago (İtalya, Como bölgesi yakını)
- **Toplam ürün:** **557 ürün** (textiles kategorisi, perdelik + upholstery + wallcoverings)
- **Kapsam:** Upholstery (heavy use ağırlıklı), Curtains, Sheers, Wallcoverings, Outdoor

> ⚠️ **Mobidik kapsamı uyarısı:** Rubelli ürünlerinin çoğu **upholstery** (mobilya kumaşı, "Use: Heavy use"). Mobidik perdelik projesi için sadece **Curtains + Sheers** filtreli ürünler relevant. Adaptör notu: "Use" alanı her ürün için kontrol; Heavy/medium/light use ürünleri perdelik değil, ayrı not düşülür.

> ⚠️ **Kapasite uyarısı:** Rubelli **jakar + damask** ağırlıklı — Mobidik kapasite tablosu **jakar YOK** (Stäubli armür). Replication kısmi olur (damask jakar üretilemez, ama plain/moiré yapılabilir).

---

## URL Yapısı

```
https://www.rubelli.com/en/<urun-slug>-<urun_kodu>
```

Örnekler:
```
https://www.rubelli.com/en/charles-30750
https://www.rubelli.com/en/aurora-30751
https://www.rubelli.com/en/fabgold-30753
https://www.rubelli.com/en/elba-30763
https://www.rubelli.com/en/filicudi-30764
```

**Ürün kodu formatı:** 5 haneli numerik (örn. `30750`). Bu Rubelli internal product ID.

**Renk varyantı format:** `<urun_kodu>_<renk_kodu>` (örn. `30750_001`, `30750_008`). 1-3 haneli renk kodu (genelde 3 hane: 001-999).

**Kategori sayfası:**
```
https://www.rubelli.com/en/textiles
```

**Filtreler (URL parameter):**
- Use: `?use=curtains`, `?use=sheers`, `?use=upholstery-heavy`, vb.
- Design Type, Type, Composition, Technical specs (FR, IMO, Outdoor)

**Toplam textiles:** **557 ürün**

---

## Platform Altyapısı

- **E-ticaret:** **Magento 2** (cart URL'leri `___store/` parametreleri)
- **Görsel CDN:** `cdn.rubelli.com` (kendi CDN — Akamai veya Cloudfront altında muhtemelen)
- **Render:** Server-side HTML + JavaScript hibrit
- **Dil:** İngilizce (`/en/`), İtalyanca (default), Fransızca

---

## Görsel CDN Pattern

```
https://cdn.rubelli.com/A<urun_kodu>_<renk_kodu>/<urun_kodu>_<sira>.<boyut>.jpg
```

**Boyut versiyonları:**
- `.30x30c.jpg` — thumbnail
- `.84x84c.jpg` — küçük (renk grid)
- `.300x300c.jpg` — orta
- `.840x840c.jpg` — büyük (modal görseli)
- `.x516.jpg` — galeri (yükseklik 516px)

**Yüksek çözünürlüklü versiyonlar:** `1280` veya `2048` ile değiştirilebilir (test gerek).

Örnek:
```
https://cdn.rubelli.com/A30750_001/30750_1.30x30c.jpg
https://cdn.rubelli.com/A30750_008/30750_8.840x840c.jpg
```

---

## Bilinen Altyapı Host'ları

| Host | Amaç | Onay durumu |
|---|---|---|
| `www.rubelli.com` | Ana ürün sayfaları (HTML) | **onaylı** — varsayılan |
| `cdn.rubelli.com` | Görsel CDN (tek host) | **onaylı (2026-05-26 taslak — Charles testinden sonra v1.1)** |

Başka Rubelli subdomain'i çıkarsa **manuel onay gerekir** (Kvadrat/Dedar disiplini).

---

## Alan Eşleştirmesi

| Şema Alanı | Sitedeki Konum | Notlar |
|---|---|---|
| `product_code` | URL son numarası (örn. `30750`) | 5 haneli internal ID |
| `product_name` | `<h1>` veya og:title | Örn. "Charles" |
| `collection` | Belirsiz — Rubelli koleksiyon adları ürün adında ya da ayrı | Sayfa kontrolü gerek |
| `composition` | Specifications "Composition" | **Format: kısaltma** (CO=Cotton, VI=Viscose, LI=Linen, SE=Silk, WO=Wool, PL=Polyester, PA=Polyamide) — normalize gerek |
| `width_cm` | Specifications "Width" | "145 cm / 57 in" — strip et |
| `weight_gsm` | Specifications "Weight" | **"g / lbs" formatında** — Rubelli birim belirsiz, kontrol gerek (lin.m mi m² mi?) |
| `repeat_cm` | Specifications "Pattern repeat" | Var-yok karışık |
| `weave_type_raw` | Specifications "Type" veya description | Damask, Jacquard, Velvet, Plain, Moiré, Boucle, Canvas |
| `usage_area` | Specifications "Use" | Heavy use / Medium use / Light use / Curtains / Sheers |
| `country_of_origin` | "Made in" | Genelde İtalya (Made in Italy) |
| `certifications.fire_safety` | Certifications bölümü | CAL TB117, BS5852, B1, IMO MED, NFPA — ürün bazlı |
| `description` | Üst paragraf | Hikaye odaklı, koleksiyon temasını anlatır |
| `style_note` | Description + designer credit | Designer adı önemli (Formafantasma, vb.) |

---

## Kompozisyon Kısaltma Normalize Tablosu

| Kısaltma | Açılım | Türkçe |
|---|---|---|
| CO | Cotton | Pamuk |
| VI | Viscose | Viskon |
| LI | Linen | Keten |
| SE | Silk | İpek |
| WO | Wool | Yün |
| PL | Polyester | Polyester |
| PA | Polyamide | Poliamid |
| AC | Acrylic | Akrilik |
| AL | Alpaca | Alpaka |
| LY | Lyocell | Lyocell |

---

## Dokuma Yapısı Normalize

| Sitedeki | Normalize | Stäubli notu |
|---|---|---|
| Plain | plain | TAM |
| Moiré | plain (özel finishing) | TAM (moiré ek finishing) |
| Damask | jacquard | **YOK** (kapasite jakar YOK) |
| Jacquard | jacquard | YOK |
| Velvet | dobby | TAM (boucle/pile) |
| Boucle | dobby | TAM (boucle iplik) |
| Canvas | plain | TAM |
| Chenille | dobby (chenille iplik) | TAM ama özel iplik |
| Voile | sheer | TAM |
| Leno | leno | TAM (kapasite #2 leno) |
| Embroidered | jacquard (genelde) | YOK |

---

## Varyant Yönetimi

**Sunum:** 84x84 px thumbnail grid (Charles'ta 28 renk). Her renge tıklayınca URL **muhtemelen değişmez** (Magento default tek SKU + galeri swap) veya `?color=` parametresi olabilir — test gerek.

**Strateji (Dedar v1.1.2 pattern'i):**
1. Ana sayfa çek → renk grid SKU'larını topla (`<urun_kodu>_<renk_kodu>` format)
2. Her renge tıklayıp (veya her renk için ayrı URL) ana görsel + renk adı al
3. Renk adı: Italyanca (Avorio, Perla, Tabacco, Blu, Ortensia)

**Önemli:** Charles 28 renk! Days Like Now 8'di. **Rubelli ürünleri çok renk** — scraper döngüsü 28 sayfa demek (28 × 5 sn = 140 sn). Optimize gerek olabilir.

---

## Sertifika Yaklaşımı

Sertifikalar **ürün bazlı**. Charles'ta sadece:
- CAL.TB117:2013 (Kaliforniya yangın)
- BS5852 source 0 (UK sigara/perdelik FR)

Rubelli ürünlerinin geneli yangın sertifikalı **değil** (premium upholstery). FR sertifikalı olanlar ayrı koleksiyonlarda.

---

## Bilinen Eksiklikler

- [ ] `price_per_meter` — Yayınlanmaz (B2B premium)
- [ ] `moq_meters` — Yayınlanmaz
- [ ] `acoustic` — Sadece acoustic paneller
- [ ] PDF technical spec — varlığı belirsiz, ilk Charles testinde kontrol edilecek
- [ ] Lead time — "Limited Stock" sinyali var ama gün sayısı yok
- [ ] Yarn type (spun/filament) — belirtilmez

---

## Kategori Tarama Stratejisi

```
1. https://www.rubelli.com/en/textiles
2. Filtre: ?use=curtains veya ?use=sheers (Mobidik için relevant)
3. Pagination — 557 ürün, muhtemelen sayfa başına 50-100
4. Her ürün kartı için: <a href> → /en/<slug>-<kod> URL
5. SKU ilk 5 hanesiyle dedupe
```

**Mobidik için öncelikli kategoriler:**
- `?use=curtains` (perdelik)
- `?use=sheers` (şeffaf perdelik)
- `?technical=outdoor` (outdoor perde)
- `?technical=flame-retardant` (FR perde)

---

## Anormallik İmzaları (Charles testinden sonra eklenir)

- Use "Heavy use" → upholstery, Mobidik perdelik projesi için kapsam dışı (mobidik_evaluation: priority=düşük, scope=upholstery)
- Damask/Jacquard → Stäubli yapamaz (kapasite jakar YOK), replication kısmi
- Composition "100% Silk" → Mobidik egzotik kategori (Days Like Now pattern)
- 28+ renk → Charles örneği, Rubelli ürünlerinin renk paleti zengin

---

## Versiyon Geçmişi

- **v1.0 (TASLAK, 2026-05-26):** İlk sürüm. WebFetch + Charles 30750 analizi. Magento + cdn.rubelli.com pattern + Specifications şeması. **Charles canlı test sonrası v1.1 düzeltmesi gerekecek** (Dedar pattern'i: width/weave/description/lightfastness/galeri/variants/production_model). Compoition kısaltma normalize tablosu (CO/VI/LI/SE/WO/PL/PA/AL/LY).
