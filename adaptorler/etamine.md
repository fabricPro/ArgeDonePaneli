# Etamine Adaptörü

**Adaptör versiyonu:** v1.0
**Son güncelleme:** 2026-05-25
**Bölge:** fransiz_alpin
**Marka slug:** etamine
**Üst marka:** Zimmer + Rohde Group

---

## Marka Profili Özeti

- **Ülke:** Fransa (Paris merkez, Lyon stüdyo)
- **Üst marka:** Z+R Group'un Fransız alt markası — 1986 kuruluş; 1995 Z+R Group'a katıldı
- **Karakter:** Z+R Group içinde **en lüks/artisanal** kanat. İtalyan + Fransız zanaatkar atölyelere fason, küçük partiler, "couture textile" konumlandırması. Maltinto el-boyama, digital pigment baskı, linen knit gibi özel teknikler.
- **Üretim ülkeleri:** Fransa (Heure Bleue, Fil du Temps), **İtalya** (Andria, Blanc de Lin) — açık beyan varsa o, yoksa Fransa default (anayasa ülke atama kuralı)
- **Dil:** İngilizce + Fransızca (Z+R sitesi /en path)
- **Bot dostluğu:** Yüksek (Z+R TYPO3)

---

## URL Yapısı

```
https://www.zimmer-rohde.com/en/product-finder/details/<urun-slug>-<urun_kodu>?brand=etamine
```

Örnekler:
```
https://www.zimmer-rohde.com/en/product-finder/details/andria-19621-883
https://www.zimmer-rohde.com/en/product-finder/details/heure-bleue-19650-882
https://www.zimmer-rohde.com/en/product-finder/details/blanc-de-lin-re-19635-880
https://www.zimmer-rohde.com/en/product-finder/details/fil-du-temps-19649-883
```

**Ürün kodu formatı:** 8 haneli, **19**'la başlar (Etamine prefix). Örn. `19621883`, `19650882`. Sayfada `XXXXX-NNN` formatında.

---

## Görsel CDN — Z+R Group Ortak

```
https://www.zimmer-rohde.com/fileadmin/_processed_/{x}/{y}/csm_<urun_kodu>_<sira>_<hash>.jpg
```

Etamine ürünleri 3-6 renk varyantı + 4-6 görsel/ürün. Lifestyle çekimleri **artisanal stüdyo atmosfer** ağırlıklı (Z+R'nin daha mimari çekimlerinden farklı).

---

## Alan Eşleştirmesi (Z+R + Etamine-özel ek)

| Şema Alanı | Etamine Notu |
|---|---|
| `product_code` | 19-ile başlayan 8 haneli |
| `collection` | Fransızca koleksiyon adları: **Ailleurs** (Maltinto artisan), **Songe d'Ete** (Akdeniz manzaraları), **Vents d'été** (sürdürülebilir keten), **Maltinto** (el-boyama özel) |
| `composition` | Yüksek doğal lif oranı: keten (Flax), pamuk, viskon. Andria 4-bileşenli (Cot+Lin+Vis+PES) |
| `country_of_origin` | İtalya (Andria, Blanc de Lin) veya Fransa (Heure Bleue, Fil du Temps) — sayfa açık beyanı yoksa marka merkezi Fransa default |
| `style_note` | Akdeniz, gün batımı, vintage, artisanal vurgusu — koleksiyon adından + description'dan çıkar |
| `certifications.sustainability` | European Flax + OEKO-TEX (özellikle Vents d'été RE serisi) |
| `production_model` | Çoğunlukla **make_to_order** (artisanal) — lead time uzun (4-8 hafta) |

---

## Dokuma Yapısı + Özel Teknikler

| Sitedeki ifade | Normalize | Stäubli kapasitesi |
|---|---|---|
| Plain linen voile | sheer / plain | TAM (Heure Bleue) |
| Broad-striped woven + Maltinto | dobby + special_finishing | Dokuma TAM, ama **Maltinto el-boyama dokumam değil finishing** (Andria) |
| Linen knit / crochet | knit | **ATÖLYE DIŞI** — Stäubli armür örme yapamaz (Blanc de Lin RE) |
| Crochet-inspired gauzy weave | leno (open) | TAM kapasitede leno var (Fil du Temps); ama outdoor acrylic iplik tedariki niş |

**Önemli çelişki uyarısı:** Documents iterasyonu Etamine ürünlerinin bazılarını "Stäubli yapamaz" sınıfladı. Kapasite tablosuna göre:
- **Andria:** Dokuma TAM ama Maltinto el-boyama replication dışı → plain version (Maltinto'suz) pilot yapılabilir, "artisanal patina yok" notu ile.
- **Blanc de Lin RE:** Stäubli **örme yapamaz** (kapasite tablosu: jakar YOK, ÖRME zaten kategori dışı). Replication hedefi DEĞİL — pazar gözlemi olarak rapor edilir.
- **Fil du Temps:** Leno TAM (kapasite #2), ama solution-dyed acrylic + outdoor finishing iplik tedariki Türkiye'de niş (Aksa). 3-ürün leno portföyü (Niket + Fil du Temps + Kvadrat Alpaca Leno) ROI hesabında kritik.

---

## PDF Datasheet

Etamine datasheet'leri Z+R Group standartında:
```
https://www.zimmer-rohde.com/fileadmin/user_upload/_datasheets_/ETA_<urun_kodu>_<lang>.pdf
```

PDF'te artisanal teknik detaylar (Maltinto boyama süreci, Crochet stitch repeat) açıklamalı olabilir — `style_note` için kaynak.

---

## Çekirdek Koleksiyonlar

| Koleksiyon | Tema | Ürünler | Mobidik strateji |
|---|---|---|---|
| **Ailleurs** | Akdeniz/Doğu seyahatleri, artisanal | Andria (Maltinto el-boyama) | ZOR — plain version pilot, Maltinto fason aday tespiti |
| **Songe d'Ete** | Yaz hayalleri, gradient print + outdoor | Heure Bleue (digital print), Fil du Temps (crochet outdoor) | Orta-Zor — digital printer yatırımı veya fason; outdoor finishing fason |
| **Vents d'été** | Sürdürülebilir keten RE | Blanc de Lin RE (knit) | ATÖLYE DIŞI — örme makinesi yatırım gerekir, replication hedefi değil |

---

## Etamine Özel Notlar

1. **Üretim ülkesi her ürün için farklı olabilir** — Z+R Group sitesinde "Made in" satırı dikkatli okunmalı. Default "Fransa" (marka merkezi), ama Andria/Blanc de Lin açık "Italy" beyanı.
2. **Artisanal "couture textile" konumlandırma** — premium fiyat seviyesi (Kvadrat üstü olabilir). Mobidik için "Kvadrat-tarzı Türk üretimi" söylemi Etamine için **işe yaramaz** — fiyat aralığı erişilemez segment.
3. **Replication zorluğu**: 4 üründen 2'si replication dışı (Blanc de Lin örme, Andria Maltinto), 1'i niş yatırım (Fil du Temps outdoor), sadece 1'i (Heure Bleue) "olası pilot" — ama o da digital baskı fason gerek.

---

## Bilinen Eksiklikler

- [ ] `country_of_origin` her ürün için ayrı kontrol gerek
- [ ] `price_per_meter` — B2B + makers' segment, hiç publike değil
- [ ] `weight_gsm` — PDF'te
- [ ] Artisanal teknik açıklaması (Maltinto, knit gauge) — sayfa açıklamasında özetli, derinlemesine yok

---

## Versiyon Geçmişi

- **v1.0** (2026-05-25): İlk sürüm. Z+R Group ortak şablon + Etamine artisanal teknikler (Maltinto/knit/crochet) için kapasite çelişkisi notları. 4 üründen 2'si replication dışı; ayrım net.
