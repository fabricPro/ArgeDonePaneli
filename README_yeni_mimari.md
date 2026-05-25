# ARGE Perdelik Pazar Zekası

Premium perdelik üreticilerini (Kvadrat, Dedar, Rubelli, Sahco, Nya Nordiska, Création Baumann, Zimmer + Rohde) sistematik izleyen veri / strateji sistemi. Mobidik ARGE için.

## Mimari

**Python script (`topla/topla.py`):** Link verince marka tespit eder, adaptör mantığıyla site verisini çeker (HTML + PDF + görseller). Çıktı: ham JSON.

**Claude Code (sen):** Ham JSON'u alır, anayasa denetimi yapar, Türkçe yorum üretir, `mobidik_evaluation` puanlar, final JSON yazar.

İki katman ayrıdır, bilgi kaybı yoktur. Detay: `CLAUDE.md` Altın Kural #9.

## Mevcut Durum

- 7 altın kural + 2 yeni (#8 denetlenmiş veri önceliği, #9 mimari sınırı) anayasada
- Kapasite tablosu Mobidik için tanımlı (max 360 cm tezgah eni, leno + çift atkı / çözgü TAM, metallic YOK)
- Şema v1.3 (urun) + v1.1 (marka profili)
- 2 adaptör denetlenmiş (Kvadrat v1.2, Dedar v1.0)
- 1 marka profili (Kvadrat, n=1)
- **Streamlit demo v1 çalışır** — Kvadrat Air Line için 8/10 alan dolu sonuç üretiyor
- Ürün JSON'ları: ham çıktılar `topla/ham_cikti/`'da (Claude Code denetim sonrası `markalar/urunler/`'e geçer)

## Sonraki Adımlar

1. `topla.py` iskelet kurulumu (Playwright + PDF extractor + image downloader)
2. Kvadrat Air Line pilot kalibrasyonu (eski denetlenmiş çıktı ile karşılaştır)
3. Dedar Cobra pilot kalibrasyonu
4. Diğer 5 marka adaptör inşası (gerçek ürün denetimiyle)
5. Master zincir aktivasyonu (n=3 marka)
6. Vercel + Supabase geçiş (3-4 hafta)

## Klasör Haritası

```
ARGE_Perdelik_Pazar_Zekasi/
├── CLAUDE.md                 # Anayasa v2.0 (her oturumda okunur)
├── README.md                 # Bu dosya
├── .gitignore
├── kapasite/
│   └── staubli_uretim_kapasitesi.md
├── sema/
│   ├── urun.json             # Şema v1.3
│   └── marka_profili.json    # Şema v1.1
├── adaptorler/
│   ├── kvadrat.md            # v1.2 (denetlenmiş)
│   └── dedar.md              # v1.0 (denetlenmiş)
├── markalar/
│   ├── kvadrat.json          # Marka profili (n=1)
│   └── urunler/              # Ürün JSON'ları (boş)
├── gorseller/                # Marka / ürün görselleri (gitignore)
├── pdfler/                   # PDF kaynakları (gitignore)
├── app.py                    # Streamlit demo arayüzü
├── requirements.txt          # Python bağımlılıkları
├── topla/
│   ├── topla.py              # Orchestrator (URL → scrape → puanla → JSON)
│   ├── cli.py                # `python -m topla.cli <URL>` komut satırı
│   ├── scrapers/kvadrat.py   # Kvadrat-spesifik scraper (Playwright)
│   ├── parsers/pdf_parser.py # PDF technical spec (pdfplumber)
│   ├── puanlama/
│   │   ├── staubli.py        # Stäubli 1-5 (kapasite kuralları)
│   │   ├── mobidik.py        # Mobidik 0-100 (4 alt-puan)
│   │   └── strategic_note.py # Türkçe template not
│   └── ham_cikti/            # Python ham çıktısı (gitignore)
├── docs/
│   ├── neden_python_script.md       # Cowork engeli tarihçesi
│   └── mimari_gecis_2026-05-14.md   # Geçiş notu
└── _arsiv_referans/          # Gerekirse seçici referans (boş)
```

## Demoyu Çalıştırma (Mobidik kullanıcısı için)

**Bir kerelik kurulum** (yaklaşık 5 dakika, Chromium 150 MB indirme dahil):

PowerShell aç:

```
cd C:\Users\PC\CoWork_R&D\ARGE_Perdelik_Pazar_Zekasi
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium
```

**Her seferinde çalıştırma** (tek komut):

```
.venv\Scripts\python.exe -m streamlit run app.py
```

Tarayıcı otomatik açılır: `http://localhost:8501`

1. URL kutusuna Kvadrat ürün linkini yapıştır (örnek: `https://www.kvadrat.dk/en/products/curtains/5539-air-line`)
2. **Tara** butonuna bas
3. 30-60 saniye bekle (arka planda gizli tarayıcı sayfayı açıp veriyi çekiyor)
4. Ekrana 10 alan çıkar: marka, ürün adı, kompozisyon, en, dokuma, üretim ülkesi, sertifikalar, Mobidik puanı (0-100), Stäubli yapılabilirlik (1-5), Türkçe stratejik not

**Çıkmak için**: PowerShell penceresinde `Ctrl+C`.

**Notlar**:
- Şu anda yalnızca **Kvadrat** destekleniyor. Dedar bir sonraki adım.
- Bazı alanlar sayfada yayınlanmamış olabilir — bu durumda **"(veri bulunamadı)"** gösterilir. Sistem **tahmin yapmaz** (anayasa kuralı).
- Türkçe stratejik not şu an basit bir şablon. Detaylı stratejik yorum Claude Code oturumunda yapılır.
- Her tarama bir ham JSON dosyasına kaydedilir (`topla/ham_cikti/`). Bu dosya Claude Code denetimine girer, denetim geçince `markalar/urunler/`'e geçer.

## Hızlı Başlangıç (Claude Code oturumu için)

Yeni bir oturum açtığında `CLAUDE.md` otomatik okunur. Ham veri varsa `topla/ham_cikti/`'da bekler — denetim / yorum / yazım işin.
