# Scheduled Tasks — Mobidik ARGE

Faz 6.4 — Windows Task Scheduler entegrasyonu

## Kadans (CLAUDE.md)

| Gün | Saat | Görev | Markalar / İşlem |
|---|---|---|---|
| Pazartesi | 06:00 | `Batch_nordik` | Kvadrat, Sahco |
| Çarşamba | 06:00 | `Batch_italyan` | Dedar, Rubelli |
| Cuma | 06:00 | `Batch_alman` | Zimmer + Rohde, ADO Goldkante, Etamine, Travers, Nya Nordiska, Création Baumann |
| Cumartesi | 09:00 | `Weekly_Review` | `docs/haftalik_oz_degerlendirme_YYYY-MM-DD.md` üretir |

## Anayasa #6 disiplini

Batch çalıştırması SADECE ön izleme yapar:
- Marka kategori sayfasını çek
- Ürün URL'lerini extract et
- `markalar/urunler/*.json` ile diff'le
- Yeni adayları `topla/ham_cikti/aday_<bolge>_<tarih>.json` yaz

**Tam veri çekimi YAPILMAZ.** Kullanıcı `aday_*.json`'ı inceler, onayladığı URL'leri tek tek `python -m topla.cli <url>` ile çeker, Claude denetim sonrası `markalar/urunler/`'e geçer.

## Dosyalar

- `run_batch.ps1` — Tek bölge için batch wrapper (logging dahil)
- `run_weekly_review.ps1` — Haftalık öz-değerlendirme wrapper
- `register_tasks.ps1` — Tüm 4 görevi Task Scheduler'a kaydet
- `unregister_tasks.ps1` — Tüm görevleri sil

## Kurulum

### 1. .venv hazır olmalı

```powershell
cd C:\Users\PC\Documents\ARGE_Perdelik_Pazar_Arastirmasi
# .venv yoksa:
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\playwright install chromium
```

### 2. Manuel smoke test

Task Scheduler'a kaydetmeden önce manuel test (kullanıcı oturumunda):

```powershell
# Nordik bölge test
.\scheduled_tasks\run_batch.ps1 -Region nordik

# Çıktıyı kontrol et
Get-Content topla\ham_cikti\aday_nordik_*.json
Get-Content topla\logs\task_scheduler_nordik_*.log

# Weekly review test
.\scheduled_tasks\run_weekly_review.ps1
Get-Content docs\haftalik_oz_degerlendirme_*.md
```

### 3. Task Scheduler'a kaydet

```powershell
# Bu komut admin gerektirmez (kullanıcı oturumunda çalışır)
.\scheduled_tasks\register_tasks.ps1
```

### 4. Doğrulama

```powershell
Get-ScheduledTask -TaskPath "\Mobidik\ARGE_Pazar_Zekasi\*"
```

Beklenen 4 görev:
- `Batch_nordik` — Monday 06:00
- `Batch_italyan` — Wednesday 06:00
- `Batch_alman` — Friday 06:00
- `Weekly_Review` — Saturday 09:00

### 5. Manuel tetikleme (test için)

```powershell
Start-ScheduledTask -TaskPath "\Mobidik\ARGE_Pazar_Zekasi\" -TaskName "Batch_nordik"

# Sonuç kontrol
Get-ScheduledTaskInfo -TaskPath "\Mobidik\ARGE_Pazar_Zekasi\" -TaskName "Batch_nordik"
Get-Content topla\logs\task_scheduler_nordik_*.log -Tail 20
```

## Silme

```powershell
.\scheduled_tasks\unregister_tasks.ps1
```

## Logger

Her batch çalıştırması iki log oluşturur:

1. `topla/logs/task_scheduler_<bolge>_<tarih>.log` — Wrapper PS1 logu
2. `topla/logs/batch_<bolge>_<tarih>.log` — Python batch.py logu

Çıktı (JSON):
- `topla/ham_cikti/aday_<bolge>_<YYYYMMDD>.json` — yeni aday listesi
- `docs/haftalik_oz_degerlendirme_<YYYY-MM-DD>.md` — haftalık özet

## Marka Listesi (BRANDS registry)

`topla/batch.py` içinde tanımlı:

**Scraper'ı olan markalar (full pipeline çalışır):**
- Kvadrat (nordik)
- Dedar (italyan)
- Rubelli (italyan)
- Zimmer + Rohde (alman)
- ADO Goldkante (alman)
- Etamine (alman)
- Travers (alman)

**Sadece ön keşif (scraper bekleniyor):**
- Sahco (nordik) — Faz 7 hedef
- Nya Nordiska (alman) — Faz 7 hedef
- Création Baumann (alman) — Faz 7 hedef

3 yeni markanın URL pattern'leri keşfedilince `topla/batch.py` içindeki BRANDS dict'e eklenmeli.

## Troubleshooting

### "Bu görev şu sistemle çalıştırılamadı" (Result code 0x8007...)

- Görev kullanıcı oturumunda olmalı (`-LogonType Interactive`)
- Kullanıcı oturumda değilse görev tetiklenmez. "Run whether user is logged on or not" seçeneği şifre gerektirir — şimdi açık değil.

### Python .venv bulunamadı

- `register_tasks.ps1` çalıştırmadan önce `.venv` kurulmalı.
- Wrapper script kontrolü: `Test-Path .\.venv\Scripts\python.exe`

### Playwright timeout

- Kategori sayfası bazı markalarda yavaş (Kvadrat Vue.js). `topla/batch.py`'da `fetch_html_playwright(url, wait_ms=3500)` → gerekirse arttır.

### Z+R 429 rate-limit

- `topla/batch.py` requests-based + 5/10/20 sn backoff retry içeriyor.
- Beklenmedik 429 IP block: 30 dk bekle, manuel re-run.
