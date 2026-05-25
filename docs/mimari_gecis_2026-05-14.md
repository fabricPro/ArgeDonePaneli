# Mimari Geçiş: Cowork → Claude Code

Tarih: 2026-05-14

## Sebep

Cowork mevcut araç setiyle "veri toplama" katmanını otomatize edemedi:

- web_fetch binary save desteği yok (PDF/görsel)
- Chrome MCP JavaScript binary fetch BLOCKED
- Scheduled task otomasyonu sınırlı

## Yeni Mimari

- Python script (topla.py) → mekanik veri toplama (Playwright + PDF + görsel indirme)
- Claude Code → anayasa denetimi + Türkçe yorum + mobidik_evaluation + final JSON yazımı
- Cowork → emekliye ayrıldı

## Bu Klasörün Durumu

Bu eski klasör arşivlenecek. Yeni klasör:

C:\Users\PC\CoWork_R&D\ARGE_Perdelik_Pazar_Zekasi\

Taşınacak dosyalar (seçici taşıma):

- CLAUDE.md (anayasa, 8 altın kural)
- _kapasite/staubli_uretim_kapasitesi.md
- _sema/*.json (v1.3)
- _adaptorler/kvadrat.md (v1.2)
- _adaptorler/dedar.md (v1.0)
- 01_veri/marka_profilleri/kvadrat.json
- 99_kalite_kontrol/cowork_arac_kisitlamalari.md

Taşınmayacak (yeniden çıkarılacak veya artık gerek yok):

- Ürün JSON'ları (Air Line, Cobra — 5 dakikada Python'la yeniden)
- Denetim raporları (anayasa içselleştirdi)
- Karantina (artık önemsiz)
- Cold storage 6 adaptör (gerektikçe yeniden yazılacak)
