# ADO Goldkante Adaptörü

**Adaptör versiyonu:** v1.0
**Son güncelleme:** 2026-05-25
**Bölge:** alman_alpin
**Marka slug:** ado_goldkante
**Üst marka:** Zimmer + Rohde Group

---

## Marka Profili Özeti

- **Ülke:** Almanya (Aschendorf merkez)
- **Üst marka:** Z+R Group alt markası (1948 kurulan ADO 1990'da Z+R'ye katıldı)
- **Karakter:** Z+R'nin geniş erişim + orta-üst premium markası. Daha ölçek odaklı, PES-dominant (Z+R'nin keten/yün premium odağına karşılık).
- **Üretim modeli:** Z+R Group altyapısı (Almanya)
- **Dil:** İngilizce + Almanca
- **Bot dostluğu:** Yüksek (Z+R TYPO3 ile aynı)
- **Karakter sinyali:** Outdoor + sustainability + FR koleksiyonları (Capri Plus, Harry RE, Drift FR). Color Fields koleksiyonu sade premium (Pure White serisi).

---

## URL Yapısı

```
https://www.zimmer-rohde.com/en/product-finder/details/<urun-slug>-<urun_kodu>?brand=ado-goldkante
```

Örnekler:
```
https://www.zimmer-rohde.com/en/product-finder/details/ora-3018-914
https://www.zimmer-rohde.com/en/product-finder/details/harry-re-3009-110
https://www.zimmer-rohde.com/en/product-finder/details/capri-plus-3150-332
https://www.zimmer-rohde.com/en/product-finder/details/pure-white-pinstripe-3301-110
https://www.zimmer-rohde.com/en/product-finder/details/drift-fr-3610-110
```

**Ürün kodu formatı:** **7 haneli** (Z+R'den farklı, 8 değil). Örn. `3018914`, `3150332`. Sayfada `XXXX-NNN` formatında (`3150-332`).

**Kategori sayfası:**
```
https://www.zimmer-rohde.com/en/product-finder?brand=ado-goldkante&category=curtains
```

---

## Görsel CDN — Z+R Ortak Pattern

ADO görselleri Z+R'nin TYPO3 instance'ında:

```
https://www.zimmer-rohde.com/fileadmin/_processed_/{x}/{y}/csm_<urun_kodu>_<sira>_<hash>.jpg
```

**Capri Plus ile ilgili dikkat:** 17 renk varyantı var ama dashboard'da yalnızca default 332 görseli yüklü olabilir; PowerShell `02_gorseller/indir.ps1` döngüsü kontrol edilmeli. Faz 3.3 görsel migrasyonu sırasında eksikler tespit edilir.

**Renk varyantı pattern'i:** `csm_<7_haneli_kod>_<sira>_<hash>.jpg` (Z+R 8-hane → ADO 7-hane fark).

---

## Alan Eşleştirmesi

Z+R Adaptörüyle aynı şablon, ek olarak ADO-özel:

| Şema Alanı | Sitedeki Konum | ADO-özel notu |
|---|---|---|
| `product_code` | URL + `<h1>` | **7 haneli** (Z+R 8-haneli) |
| `collection` | "Collection" | ADO koleksiyonları: F23 (Spring 2023), H22 (Fall 2022), Color Fields, Snapshot, Collaboration |
| `composition` | "Composition" | ADO PES-dominant (%59-%100), bazen %100 PES (Capri Plus, Drift FR), bazen rPES (Harry RE) |
| `weight_gsm` | Datasheet PDF | Genellikle 150-280 g/m² (Z+R orta segment) |
| `fire_performance` | Datasheet PDF "FR" | Drift FR koleksiyonu B1 + DIN 4102-1 sertifikası ZORUNLU; diğer koleksiyonlarda opsiyonel |
| `country_of_origin` | "Made in Germany" | Çoğunlukla Almanya (Aschendorf fabrika) |

---

## Dokuma Yapısı Normalizasyonu

ADO ürünleri genellikle daha sade dokuma profili:

| Sitedeki ifade | Normalize | Notlar |
|---|---|---|
| Dobby | dobby | ORA, çoğu jakar-olmayan |
| Plain weave | plain | Color Fields pinstripe |
| Open latticework | dobby (open) | Capri Plus — gözenekli kafes |
| Sheer / Voile | sheer | Harry RE rPES |
| Boucle / Loop / Slub | dobby + special_yarn | Pure White Tape/Pinstripe |
| Stripe | dobby (stripe pattern) | Drift FR |
| Jacquard | jacquard | Stäubli için YOK — düşük öncelik |

**Çelişki uyarısı:** ADO ürünlerinin çoğu Stäubli kapasitesinde TAM — leno problemi yok. Boucle ve slub iplik tedariki MOQ riski olabilir, ama dokuma kendisi sorunsuz.

---

## Çekirdek Koleksiyonlar

| Koleksiyon | Tema | Önemli ürünler | Mobidik öncelik |
|---|---|---|---|
| **F23 / H22** | Klasik dama/dokulu | ORA (mélange dobby check) | Orta — kolay replica |
| **Color Fields** | Sade premium pinstripe | Pure White Tape (boucle stripe), Pure White Pinstripe (slub) | Yüksek — AB kurumsal kanal |
| **Snapshot / Drift FR** | FR + outdoor | Drift FR (B1 sertifikalı) | Orta — FR son ürün sertifika süreci |
| **Collaboration** | Outdoor + sürdürülebilirlik | Capri Plus (open latticework, 17 renk!) | **EN YÜKSEK** — outdoor segment AB'de %25/yıl büyüyor |
| **Recycled / Heritage** | rPES + circular design | Harry RE (54% rPES) | **YÜKSEK** — GRS sertifika başvurusu acil |

---

## ADO Özel Pazar Sinyalleri

1. **Capri Plus 17-renk paleti** — open latticework outdoor PES; Mobidik için ALTIN ürün. R+T Stuttgart 2027 hedefi.
2. **Harry RE rPES** — %54 recycled PES + %46 standart PES. Türkiye'de SASA + Korteks GRS-sertifikalı rPES üretiyor — tedarik kolay.
3. **Pure White Pinstripe slub iplik** — özel sipariş MOQ ~500 kg; Yünsa veya Korteks fason.
4. **Drift FR** — B1 sertifika gerekliliği. Mobidik FR iplik kategorisi TAM ama son ürün sertifika süreci AÇIK İŞ.

---

## PDF Datasheet — ADO'ya Özel

ADO datasheet PDF'leri Z+R Group standart pattern'inde:

```
https://www.zimmer-rohde.com/fileadmin/user_upload/_datasheets_/ADO_<urun_kodu>_<lang>.pdf
```

Capri Plus için (17 renk) datasheet'te tüm renk kodları + Martindale + ışık haslığı listelidir — bu kritik bir kaynak.

---

## Bilinen Eksiklikler

- [ ] `price_per_meter` — B2B-only
- [ ] `moq_meters` — Distribütör
- [ ] `weight_gsm` HTML'de YOK — PDF zorunlu
- [ ] `thread_density` — AI inference adayı

---

## Versiyon Geçmişi

- **v1.0** (2026-05-25): İlk sürüm — Z+R Group ortak CDN'i + ADO özel farklar (7-hane kod, F23/H22 koleksiyonları, FR + rPES + outdoor sinyalleri).
