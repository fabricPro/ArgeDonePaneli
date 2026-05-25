# Cowork Araç Kısıtlamaları — Görsel İndirme Engeli

## Tespit Edilen Engel

**Tarih**: 2026-05-13
**Test bağlamı**: ARGE Perdelik Pazar Araştırması, Görsel Katman Testi v1.3
**Detay rapor**: `99_kalite_kontrol/gorsel_indirme_test_raporu.md`

Cowork'ün mevcut araç setiyle görsel binary dosyaları workspace'e otomatik kaydetme **imkansız**:

| Araç | Engel | Kanıt |
|------|-------|-------|
| `web_fetch` | binary save desteği yok | Air Line PDF testinde kanıtlandı (kullanıcı manuel indirdi) |
| Chrome MCP `javascript_tool` | binary fetch + base64 → `[BLOCKED: Cookie/query string data]` | 2026-05-13 Cobra cdn11.bigcommerce.com image fetch denemesi |
| Chrome MCP doğrudan download tool'u | YOK (envanterli) | `file_upload`/`upload_image`/`gif_creator` var, image_download yok |
| bash `curl`/`wget`/`lynx` | web content restrictions YASAK | CLAUDE.md/sistem prompt'u |
| bash Python `urllib`/`requests`/`httpx`/`aiohttp` | YASAK | aynı |
| Diğer programlama dilleri HTTP fetch | YASAK | aynı |

**Sonuç**: Görsel indirme her ürün için **manuel müdahale** gerektiriyor.

---

## Etki — Mevcut Sistem

| Senaryo | Etki |
|---------|------|
| Tek ürün testleri (kullanıcı manuel hazır) | İşliyor — kullanıcı 1-2 dakika manuel indirme, sonra Cowork analiz yapar |
| Scheduled task (haftada 3 kez 7 marka taraması — CLAUDE.md'de tanımlı) | **KIRILIR** — manuel müdahale otomasyon ile uyumsuz |
| Master zincir görsel doldurma (`02_gorseller/<marka>/<urun>/`) | **Yarı manuel kalır** — ürünler tek tek manuel yüklenir |
| `image_analysis` bloğu otomatik üretimi | Bağımlı — görsel olmadan boş kalır |
| Dashboard görsel galeri (`04_html_dashboard/`) | Görselsiz başlatılır, dolduruldukça zenginleşir |

---

## Geçici Çözüm (şu an uygulanan)

- Test bazında manuel görsel indirme (kullanıcı tarayıcıdan)
- Pipeline'ın geri kalanı (kayıt, image_analysis, JSON entegrasyonu) otomatik
- Diğer ürünlerin görselleri için `images` array stub'ları **pending_manual_download** durumunda kalır
- Şema v1.3 stub yapısı: `{url, local_path: null, status: "pending_manual_download", layer_attempts_history: [...]}`

---

## Önerilen Uzun Vade Çözümler

### Çözüm 1 — Anthropic Cowork Update'i Bekleme (en pasif)

- `web_fetch`'e binary save modu eklenirse problem çözülür (örn. `web_fetch(url, save_to: "<workspace_path>")`)
- Chrome MCP'ye binary fetch izni verilirse (`[BLOCKED]` filtresi gevşetilirse) javascript_tool trick'i çalışır
- Veya doğrudan `mcp__Claude_in_Chrome__download_resource(url, save_to)` benzeri bir tool eklenirse

**Aksiyon**: Anthropic'e geri bildirim — feedback hub veya support kanalıyla bu kısıtlama bildirilebilir. Pasif bekleme.

### Çözüm 2 — Lokal Python Script (otonom, en sağlam)

```python
# pseudo
- JSON dosyalarını tara (01_veri/urunler_per_marka/*.json)
- images array'lerinde status == "pending_manual_download" stub'larını topla
- requests.get(stub.url) → binary → workspace/02_gorseller/{marka}/{urun}/{filename}
- Stub'ı tamamlanmış kayıt olarak güncelle (downloaded_at, file_size_kb, dimensions, layer_used: "local_script")
- Cowork bir sonraki run'da bu kayıtları görür, image_analysis tetikler
```

- Scheduled task ile periyodik çalışır (`cron` veya Windows Task Scheduler)
- Cowork'ten **bağımsız** — Cowork sınırlamalarına takılmaz
- Tek yatırım: ~50-100 satır Python + temel dependency (`requests`, `Pillow`)
- Bakım kolaylığı yüksek

**Aksiyon**: Master zincire geçmeden önce **kurulmalı**. Mobidik ARGE ekibi (veya kullanıcı) Python script'i bir kez yazıp scheduled task olarak ekler.

### Çözüm 3 — Lokal bash wrapper (Cowork başlatır, kullanıcı bilgisayarı çalıştırır)

- Cowork bir "indirilmesi gereken görseller" listesi üretir (`99_kalite_kontrol/indirilecek_gorseller.txt`)
- Kullanıcı bir komut çalıştırır (örn. `./indir_eksik_gorseller.sh`)
- Script tüm pending görselleri toplu indirir (curl tabanlı)
- Cowork bir sonraki run'da kayıtları görür

**Avantaj**: Çözüm 2'den daha basit; Python kurulu olmasa bile çalışır.
**Dezavantaj**: Manuel tetikleme — scheduled task otomasyonu Cowork tarafı için zayıf kalır.

### Çözüm 4 — Browser Extension (kullanıcı tıklar) — kısa vade

- Bir Chrome extension yazılır (~200 satır JS)
- Kullanıcı ürün sayfalarında bir tıkla görsel paketi indirir (Kvadrat downloadcenter linki veya BigCommerce stencil 1280x1280 versiyonu)
- İndirme klasörü `02_gorseller/<marka>/<urun>/` otomatik routing

**Avantaj**: Kullanıcı yine de browser kullanıyor; UI üzerinden tıklama doğal akışta.
**Dezavantaj**: Yine manuel (her ürün için bir tıklama).

---

## Tavsiye

**Şu an**: **Çözüm 2 (Lokal Python script)** en sağlam uzun vadeli yol. Scheduled task ile haftada 3 kez Cowork'ün tarama çıktısını okur, eksik görselleri otomatik toplar. Cowork bir sonraki run'da görsel olarak hazır verilerle çalışır.

**Master zincire geçmeden önce**: Çözüm 2 kurulmalı, aksi takdirde sistem yarı manuel kalır.

**Geçici** (Çözüm 2 hazırlanana kadar): Manuel indirme — test ürünleri için OK.

---

## CLAUDE.md Kalıcı Not

Bu engel CLAUDE.md'ye kalıcı uyarı olarak eklendi (Altın Kural #4'ün altına): görsel indirme her zaman manuel veya lokal script gerektirir; Cowork web_fetch tek başına yeterli değil.

---

## Versiyon

- **v1.0** (2026-05-13): İlk tespit. Görsel Katman Testi v1.3 sırasında çıktı.
