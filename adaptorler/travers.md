# Travers Adaptörü

**Adaptör versiyonu:** v1.0
**Son güncelleme:** 2026-05-25
**Bölge:** amerikan
**Marka slug:** travers
**Üst marka:** Zimmer + Rohde Group

---

## Marka Profili Özeti

- **Ülke:** ABD (tasarım) + üretim Avrupa (genellikle İtalya/Almanya)
- **Üst marka:** Z+R Group'un Amerikan kanat markası (1990'lar Z+R portföyüne katıldı)
- **Karakter:** "Wallpaper coordinates" — duvar kağıdı + perdelik birleşik koleksiyonlar. El-dokuma görünümlü slub iplik, vintage Amerikan dekoratif. Premium konut + butik otel segmentleri.
- **Üretim modeli:** Tasarım ABD (New York), üretim **çoğunlukla Avrupa** (Z+R Group altyapısı). Açık beyan varsa o ülke kullanılır.
- **Dil:** İngilizce (Amerikan)
- **Bot dostluğu:** Yüksek (Z+R TYPO3)

---

## URL Yapısı

```
https://www.zimmer-rohde.com/en/product-finder/details/<urun-slug>-<urun_kodu>?brand=travers
```

Örnek:
```
https://www.zimmer-rohde.com/en/product-finder/details/garden-stripe-44187-683
```

**Ürün kodu formatı:** 8 haneli, **44** veya **45** ile başlar (Travers prefix). Örn. `44187683`, `44187594`.

**Travers ürün kodları (indir.ps1'den, 02_gorseller/travers/'a indirilen):**
- 44187586 — Garden Stripe Deniz Mavisi
- 44187594 — Garden Stripe Yeşil
- 44187683 — Garden Stripe Pudra Somon (dashboard default)
- 44187844 — Garden Stripe Mercan
- 44187981 — Garden Stripe Açık Duman
- 44187987 — Garden Stripe Mor/Lila

**Önemli:** Bu 6 kod 6 ayrı ÜRÜN değil, 1 ürünün (Garden Stripe `44187`) 6 renk varyantı (son 3 hane renk kodu). Dashboard'da sadece 1 ürün olarak görünür (varyant 683 default).

---

## Görsel CDN — Z+R Group Ortak

```
https://www.zimmer-rohde.com/fileadmin/_processed_/{x}/{y}/csm_<urun_kodu>_<sira>_<hash>.jpg
```

Travers ürünlerinin her renk varyantı için **3 görsel** indirilmiş (parti03):
- `_1.jpg` — Yakın çekim doku
- `_2.jpg` — Düz arka plan (shared `_rb_` fallback olabilir)
- `_3.jpg` — Lifestyle / oda kurulumu (shared)

Toplam 6 renk × 3 görsel = 18 görsel `02_gorseller/travers/` altında.

---

## Alan Eşleştirmesi (Z+R + Travers-özel)

| Şema Alanı | Travers Notu |
|---|---|
| `product_code` | 44- veya 45- ile başlayan 8 haneli |
| `collection` | Genellikle Travers'in tematik koleksiyonları: **Garden Club** (Garden Stripe), **Hamptons**, **Manhattan**, vb. Doğa + Amerikan dekoratif temalı |
| `composition` | Karışım iplikler yoğun: pamuk-keten-viskon-PES (Garden Stripe %66 Cotton + %17 PES + %9 Linen + %8 Viscose) |
| `country_of_origin` | Açık beyan yoksa **ABD** default (Travers merkezi). Pratikte üretim Avrupa (İtalya/Almanya) — sayfa beyanı kritik |
| `style_note` | Amerikan dekoratif, vintage, sahil/garden estetik vurgusu |
| `weave_type_raw` | Genellikle stripe, plain, hand-loom-look |

---

## Travers Özel Dokuma Karakteri

| Sitedeki ifade | Normalize | Notlar |
|---|---|---|
| Hand-loom look stripe | plain (slub yarn) | Slub iplik el-dokuma görünümü; çerçeve 2-4 (basit pinstripe) |
| Railroaded curtain | plain | Yatay yön kullanım (dikey çizgi = vertical light pattern) |
| Brocade / Damask | jakar | Stäubli için YOK (replication dışı) |
| Multi-fiber sheer | sheer (multi-fiber) | 3-4 lif karışım sheer — iplik MOQ riski |

**Stäubli kapasitesi:** Garden Stripe gibi basit pinstripe sheer ürünler TAM (kolay 2-4 çerçeve). Asıl risk **çok-bileşenli iplik MOQ** (4-bileşen Cot/PES/Lin/Viscose karışımı el-dokuma görünümünde slub).

---

## Çekirdek Koleksiyonlar (referans)

| Koleksiyon | Tema | Önemli ürünler |
|---|---|---|
| **Garden Club** | Bahçe/sahil temalı stripe + plain | Garden Stripe |
| **Hamptons** | Klasik Amerikan kıyı | (varsayım) |
| **Manhattan** | Şehir/loft dekoratif | (varsayım) |

---

## Travers Özel Pazar Sinyalleri

1. **Garden Stripe pinstripe** — 4-lifli karışım sheer + 6 renk + railroaded uygulama. AB markette "wallpaper coordinates" konumlanması zor; Mobidik için "basit pinstripe sheer multi-fiber" segment.
2. **El-dokuma görünümlü slub iplik** — Türkiye'de spinner az (Polaron, Yünsa fason). MOQ ~500 kg.
3. **Travers'in ABD merkezi** + Avrupa üretim — bu hibrit model Mobidik için "Türk üretim, Türk marka" yerine "Türk üretim, Avrupa/Amerika tasarım" olası iş modeli sinyali.

---

## Migrasyon Önceliği (parti03 raporu YOK)

Travers Documents iterasyonunda parti03 raporu **yazılmadı** (README "⚠️ görseller var, rapor eksik"). Görseller `02_gorseller/travers/` altında, ama markdown analiz yok. **Faz 3 migrasyon stratejisi:**

1. **Dashboard JS objesini birincil kaynak yap** — Garden Stripe için dashboard'da temel spec'ler var (kompozisyon, en, ülke, 6 renk, mobidik_notu).
2. **6 renk varyantı için tek ürün JSON** yaz (`markalar/urunler/travers_44187-garden-stripe.json`), 6 varyant `variants[]` içinde.
3. **Mobidik Notu**'nu kapasite tablosuna göre yeniden değerlendir: pinstripe sheer = kolay; 4-bileşen iplik MOQ = orta zorluk.
4. **Marka profili** sadece 1 ürünlük (n=1) — Kvadrat parti01 ile aynı durumdan başlama; daha çok Travers ürünü partile sonra n yükseltilir.

---

## PDF Datasheet

Travers ürünleri için datasheet pattern (varsayım):
```
https://www.zimmer-rohde.com/fileadmin/user_upload/_datasheets_/TRA_<urun_kodu>_<lang>.pdf
```

Garden Stripe için PDF mevcudiyeti doğrulanmadı — Faz 3 sırasında Z+R sayfası kontrol edilir.

---

## Bilinen Eksiklikler

- [ ] `country_of_origin` — Z+R sayfasında her zaman görünmez (ABD default veya Avrupa üretim)
- [ ] `price_per_meter` — B2B-only
- [ ] `weight_gsm` — datasheet PDF'te
- [ ] Slub iplik tedarikçi listesi — Mobidik açık iş

---

## Versiyon Geçmişi

- **v1.0** (2026-05-25): İlk sürüm. Travers parti03 raporu eksik olduğu için dashboard JS objesi primary kaynak. 6 ürün kodu = 1 ürün × 6 renk varyantı (Garden Stripe). Slub iplik + 4-bileşen MOQ riskleri belgelendi.
