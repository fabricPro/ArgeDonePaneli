# renkler.json — Türkçe Tekstil Ticari Renk Sözlüğü

**152 renk** · Elle küratörlenmiş · Mobidik ARGE projesi

## Format

```json
[
  { "ad": "Vizon", "hex": "#A98E73", "rgb": [169, 142, 115] },
  ...
]
```

Her entry üç alandan oluşur:

- `ad` — Türkçe ticari renk adı (piyasa terimi). Pantone/RAL standardı **DEĞİLDİR**.
- `hex` — 6-haneli HEX, büyük harf, `#` prefix dahil.
- `rgb` — `[r, g, b]` 0–255 array; `hex` ile redundant ama hızlı erişim için tutulur.

## Kapsam

Türk tekstil sektöründe (perdelik, döşemelik, giyim) yaygın kullanılan ticari renk adları:

- **Bej/Krem/Toprak** ailesi (24): Krem, Vanilya, Ekru, Kemik, Şampanya, Bej, Vizon, Taş, Greige, Köstebek, Toprak, Vizon, Kahve, Tarçın...
- **Gri ailesi** (16): İnci Grisi, Sis Grisi, Duman Grisi, Antrasit, Köşür, Demir Grisi...
- **Mavi ailesi** (17): Buz Mavisi, Gök Mavisi, Çini Mavisi, Kobalt, Safir, Lacivert, Petrol...
- **Yeşil ailesi** (17): Mint, Çağla, Adaçayı, Zeytin, Haki, Çam Yeşili, Petrol Yeşili...
- **Sarı/Turuncu/Pas** (16): Limon, Hardal, Bal, Kavun, Turuncu, Mandalina, Pas, Kiremit...
- **Pembe/Kırmızı** (16): Pudra, Gül Kurusu, Toz Pembe, Fuşya, Bordo, Vişne, Şarap...
- **Mor/Leylak** (10): Lila, Lavanta, Orkide, Mor, Erguvan, Mürdüm, Patlıcan...
- **Beyaz/Siyah uçları** (8): Beyaz, Kar Beyazı, Optik Beyaz, Kırık Beyaz... → Antrasit, Kömür, İs Siyahı, Siyah

## Kullanım

Frontend (`web/static/js/color-picker.js`):
```js
fetch('/static/data/renkler.json')
  .then(r => r.json())
  .then(list => {
    COLOR_LAB = list.map(c => ({
      name: c.ad, hex: c.hex.toUpperCase(),
      rgb: c.rgb, lab: rgbToLab(...c.rgb),
    }));
  });
```

Backend göç scripti (`scripts/migrate_color_names_to_tr.py`) aynı JSON'u okuyup `nearestColorName` ile mevcut `images[i].colors[role].name`'leri günceller.

## Genişletme

Kendi onaylı kartelandaki adlar + ölçülmüş HEX'leriyle bu JSON'u **manuel olarak** genişletebilirsin. Format ile uyumlu yeni entry ekle, kaydet, commit + push. ΔE eşleşme yakınlığı sıkılaşır.

Önerilenler:
- Mobidik markalı tonlar (örn. "Mobidik Antrasit", "Mobidik Vizon") — kartela laboratuvar HEX'leriyle
- Müşteri-spesifik özel tonlar (örn. "Otel A Krem", "Otel B Bordosu")

## Lisans

Bu dosya **public domain** muamelesi görür (kullanıcının kendi projesi için elle küratörlenmiş). Pantone/RAL gibi marka renk standartları **değildir**. Pantone karşılığı isteyenler ayrı bir Pantone sözlüğüne bakmalıdır.

## Versiyon geçmişi

- **2026-05-30** — v1.0 — 152 renk başlangıç sözlüğü (v3.6.1 commit)
