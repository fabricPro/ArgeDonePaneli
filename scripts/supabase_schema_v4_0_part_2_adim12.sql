-- v4.0-part-2 Sprint 12 — Ön Çalışma → Ürün: "Ürüne Çevir" çekmecede birleşti
-- ====================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Idempotent: tekrar çalıştırmak güvenli.
--
-- Amaç: Bir ön çalışma satırını, ayrı /ekle ekranına gitmeden doğrudan
-- "Düzenle" çekmecesinde ürüne çevirebilmek. Çekmecedeki genişletilmiş
-- ürün alanları (ürün adı, kompozisyon, en, gramaj, üretim ülkesi,
-- referans fiyat vb.) tek bir JSONB kolonunda "taslak" olarak saklanır.

-- ====================================================================
-- research_pool.product_draft — ürün-öncesi taslak (JSONB)
-- ====================================================================
-- Eleman şeması (hepsi opsiyonel):
--   {
--     "product_name": "...", "product_code": "...", "collection": "...",
--     "composition": "...", "width_cm": 315, "weight_gsm": 180,
--     "weave_type": "dobby",
--     "repeat_vertical_cm": 27, "repeat_horizontal_cm": null,
--     "production_country": "Türkiye",
--     "reference_price": "140,74 EUR", "reference_price_type": "from",
--     "reference_price_evidence": "Configure from 140,74 €",
--     "arge_notu": "..."
--   }
-- NOT: brand, country, category, pattern, color_family, weave_tags,
-- style_tags, color_count, ai_notu ZATEN gerçek research_pool kolonları;
-- product_draft'a girmez.

alter table research_pool
  add column if not exists product_draft jsonb default '{}'::jsonb;

-- ====================================================================
-- DOĞRULAMA
-- ====================================================================
-- select column_name, data_type from information_schema.columns
-- where table_name='research_pool' and column_name='product_draft';
-- Beklenen: product_draft | jsonb
