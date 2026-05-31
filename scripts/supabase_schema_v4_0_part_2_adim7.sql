-- v4.0-part-2 Adım 7 — Detay sayfasına PDF + Notlar sekmeleri
--
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Idempotent (IF NOT EXISTS): tekrar çalıştırmak güvenli.

-- 1) PDF dosyalar listesi (her ürün için liste)
--    Saklanan format:
--      [{"path":"<urun_id>/<uuid8>_<ad>.pdf","name":"Spec.pdf","size":524288,"uploaded_at":"..."}]
alter table products add column if not exists pdfs jsonb default '[]'::jsonb;

-- 2) Rich-text Notlar (HTML — bleach ile sanitize edilmiş)
alter table products add column if not exists notlar_html text default '';

-- ⚠ Bucket kurulumu (Dashboard'dan):
--    Storage → "New bucket" → Name: pdfler, Public: ON
--    File size limit: 25 MB (yeterli; teknik PDF'ler genelde 2-10 MB)
