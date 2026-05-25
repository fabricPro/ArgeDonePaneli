# Scheduled Task Otomasyon Kurulumu

Faz 6 — Mobidik ARGE pazar zekası haftalık otomasyon

## Hedef

Kullanıcı her hafta manuel olarak `python -m topla.cli <url>` yapmak yerine, Windows Task Scheduler 7 markayı periyodik olarak tarayıp yeni aday URL'lerini `topla/ham_cikti/aday_*.json`'a düşürür. Kullanıcı incelediği adayları onaylayıp tek tek detay çekimine alır.

**Anayasa #6 disiplini:** Otomasyon SADECE ön keşif yapar. Tam veri + AI yorum kullanıcı onayı sonrası manuel akış (`python -m topla.cli <url>`).

## Kadans (CLAUDE.md sabit)

| Gün | Saat (yerel) | Bölge | Markalar |
|---|---|---|---|
| Pazartesi | 06:00 | nordik | Kvadrat, Sahco |
| Çarşamba | 06:00 | italyan | Dedar, Rubelli |
| Cuma | 06:00 | alman | Z+R Group (4) + Nya + CB |
| Cumartesi | 09:00 | — | Haftalık öz-değerlendirme |

## Mimari

```
Task Scheduler
   ↓ tetikler
scheduled_tasks/run_batch.ps1 -Region <bolge>
   ↓ wrapper (loglar)
.venv\Scripts\python.exe -m topla.cli --batch <bolge>
   ↓ cli.py
topla/batch.py run_batch(<bolge>)
   ↓ her marka için
fetch_category_html (requests veya Playwright)
   ↓
extract_product_urls (regex)
   ↓
diff_with_existing (markalar/urunler/*.json ile karşılaştır)
   ↓
topla/ham_cikti/aday_<bolge>_<YYYYMMDD>.json
+ topla/logs/batch_<bolge>_<YYYYMMDD>.log
```

## Kurulum Adımları

### Önkoşul: .venv

```powershell
cd C:\Users\PC\Documents\ARGE_Perdelik_Pazar_Arastirmasi

# .venv yoksa:
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\playwright install chromium
```

### Adım 1: Offline smoke test

```powershell
.\.venv\Scripts\python.exe topla\scripts\smoke_test_batch.py
```

Beklenen çıktı:
- 10 marka BRANDS registry'de
- 7 markada `regex=var` (scraper'ı olanlar)
- 3 markada `regex=YOK (Faz 7)` (Sahco, Nya, CB)
- Mevcut JSON sayıları doğru (kvadrat=2, dedar=2, rubelli=2, zimmer_rohde=6, ado=6, etamine=4, travers=1)
- Regex extract test başarılı

### Adım 2: Tek bölge live test (manuel)

İnternet üzerinden gerçek bir bölge tara:

```powershell
.\scheduled_tasks\run_batch.ps1 -Region nordik
```

Çıktıları kontrol et:

```powershell
# Wrapper logu
Get-Content topla\logs\task_scheduler_nordik_*.log -Tail 30

# Batch log
Get-Content topla\logs\batch_nordik_*.log -Tail 20

# Aday JSON
Get-Content topla\ham_cikti\aday_nordik_*.json | ConvertFrom-Json | Format-List
```

Sorun olursa:
- Kvadrat'ta `fetch_failed` → site Vue.js, Playwright lazım; `use_playwright=True` ayarı zaten var
- Sahco'da `no_url_pattern` → beklenen davranış (Faz 7 hedef)

### Adım 3: Weekly review test

```powershell
.\scheduled_tasks\run_weekly_review.ps1
Get-Content (Get-ChildItem docs\haftalik_oz_degerlendirme_*.md | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
```

### Adım 4: Task Scheduler'a kaydet

```powershell
.\scheduled_tasks\register_tasks.ps1
```

Çıktı:
```
Kaydedildi: \Mobidik\ARGE_Pazar_Zekasi\Batch_nordik -> Monday 06:00
Kaydedildi: \Mobidik\ARGE_Pazar_Zekasi\Batch_italyan -> Wednesday 06:00
Kaydedildi: \Mobidik\ARGE_Pazar_Zekasi\Batch_alman -> Friday 06:00
Kaydedildi: \Mobidik\ARGE_Pazar_Zekasi\Weekly_Review -> Saturday 09:00
```

Doğrula:

```powershell
Get-ScheduledTask -TaskPath "\Mobidik\ARGE_Pazar_Zekasi\*" | Format-Table TaskName, State, Triggers
```

### Adım 5: Manuel tetikleme (test)

```powershell
Start-ScheduledTask -TaskPath "\Mobidik\ARGE_Pazar_Zekasi\" -TaskName "Batch_nordik"

# 10-30 sn bekle, sonra durum
Get-ScheduledTaskInfo -TaskPath "\Mobidik\ARGE_Pazar_Zekasi\" -TaskName "Batch_nordik" | Format-List
```

Son çalıştırma sonucu `LastTaskResult: 0` ise başarılı.

## Kullanım — Haftalık Akış

### Sabah (otomatik tetikleme sonrası)

1. Pazartesi/Çarşamba/Cuma 06:00 otomatik tetiklenir
2. Yeni `topla/ham_cikti/aday_<bolge>_<tarih>.json` üretilir
3. Kullanıcı sabah aday dosyasını açar:
   ```powershell
   notepad topla\ham_cikti\aday_nordik_$(Get-Date -Format yyyyMMdd).json
   ```

### Aday inceleme

Aday JSON'da her marka için:
- `yeni_aday_sayisi` — yeni keşfedilen URL sayısı
- `yeni_adaylar[].url` — incelenmesi gereken URL'ler
- `bilinen_urunler[]` — mevcut JSON'larda olanlar (ignore)

Kullanıcı ilginç bulduğu URL'i alıp:

```powershell
.\.venv\Scripts\python.exe -m topla.cli "https://dedar.com/cobra/?sku=00T1906300004"
```

Bu tek-URL akış mevcut, Anayasa #6 disiplini bozulmaz.

### Cumartesi öz-değerlendirme

`docs/haftalik_oz_degerlendirme_<YYYY-MM-DD>.md` üretilir. İçeriği:
- Son 7 günde değişen ürünler tablosu
- Yeni audit_history kayıtları
- Görsel değişiklikleri
- Git commit listesi
- Aday tarama sonuçları
- Boş "Yorum & Sonraki Adımlar" bölümü (Claude oturumunda doldurulur)

Cumartesi sabah kullanıcı bu dosyayı Claude Code'a açıp birlikte doldurur.

## Silme

```powershell
.\scheduled_tasks\unregister_tasks.ps1
```

## Troubleshooting

### Görev çalışmıyor (LastTaskResult ≠ 0)

```powershell
# Log dosyasını oku
Get-ChildItem topla\logs\ | Sort LastWriteTime -Desc | Select -First 5
Get-Content topla\logs\task_scheduler_nordik_*.log -Tail 50
```

Yaygın hata kodları:
- `0x1` — Python exception (log dosyasında traceback)
- `0x80070005` — Yetki yok (kullanıcı oturumda mı?)
- `0x41301` — Görev hâlâ çalışıyor
- `0x41306` — Görev sonlandırıldı (timeout — 2 saat limit)

### Z+R 429 rate-limit

Z+R 30 dk içinde tekrar tetiklenirse IP block atabilir. Çözüm:
- `topla/batch.py` zaten 5/10/20 sn backoff retry içeriyor
- Block uzun sürerse manuel re-run 30 dk sonra

### Kvadrat Vue.js timeout

`fetch_html_playwright` 60 sn timeout + 3.5 sn wait. Yetmezse `topla/batch.py`'da `wait_ms` arttır.

### Kategori URL'i değişti

`adaptorler/<marka>.md`'ye yeni URL not düş, `topla/batch.py` BRANDS dict'inde `category_url`'i güncelle.

### Sahco / Nya Nordiska / Création Baumann için scraper yok

Bu 3 markada şu an `product_url_regex=None`. Batch onları işlerken `status: "no_url_pattern"` döner. Faz 7'de eklenecek.

## Dosya Referansı

| Dosya | Açıklama |
|---|---|
| `topla/batch.py` | BRANDS registry + discover/diff/run_batch core |
| `topla/cli.py` | `--batch <bolge>` argümanı |
| `topla/scripts/weekly_review.py` | Cumartesi öz-değerlendirme |
| `topla/scripts/smoke_test_batch.py` | Offline regex test |
| `scheduled_tasks/run_batch.ps1` | Task Scheduler wrapper |
| `scheduled_tasks/run_weekly_review.ps1` | Weekly review wrapper |
| `scheduled_tasks/register_tasks.ps1` | Tüm 4 görevi kaydet |
| `scheduled_tasks/unregister_tasks.ps1` | Silme |
| `scheduled_tasks/README.md` | Klasör içi özet |

## Görev Tablosu

| Task Path | Trigger | Action |
|---|---|---|
| `\Mobidik\ARGE_Pazar_Zekasi\Batch_nordik` | Weekly Monday 06:00 | `run_batch.ps1 -Region nordik` |
| `\Mobidik\ARGE_Pazar_Zekasi\Batch_italyan` | Weekly Wednesday 06:00 | `run_batch.ps1 -Region italyan` |
| `\Mobidik\ARGE_Pazar_Zekasi\Batch_alman` | Weekly Friday 06:00 | `run_batch.ps1 -Region alman` |
| `\Mobidik\ARGE_Pazar_Zekasi\Weekly_Review` | Weekly Saturday 09:00 | `run_weekly_review.ps1` |

Her görev:
- Logon: Interactive (kullanıcı oturumda olmalı)
- ExecutionTimeLimit: 2 saat
- RestartOnFailure: 3 deneme, 10 dk arayla
- Battery: çalışır, çıkmaz
