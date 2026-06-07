-- ============================================================================
-- OnCalisma-V2 (Problem 4a) — "Linkten Doldur" havuz zenginleştirme staging
-- ============================================================================
-- research_pool'a İKİ KATMANLI staging + durum alanı:
--   extracted_facts   jsonb  → source_data: Gemini'nin KANITLI factual alanları
--                              {field: {value, evidence[, type]}} (Anayasa #2/#3)
--   ai_summary        jsonb  → ai_inferences: {arge_notu, model, generated_at[, suggested_*]}
--   enrichment_status text   → raw | enriched | verified  (onay akışı)
--
-- DİKKAT: Bu dosya OTOMATİK ÇALIŞTIRILMAZ. Supabase SQL editöründe ELLE uygula.
-- Idempotent (IF NOT EXISTS) — tekrar çalıştırmak güvenlidir.
-- products tablosuna DOKUNULMAZ; mevcut kolonlar değişmez.
-- Gerçek kolonlara OTOMATİK yazım YOK — kullanıcı havuzda onaylayınca promote edilir.
-- ============================================================================

alter table research_pool add column if not exists extracted_facts  jsonb;
alter table research_pool add column if not exists ai_summary       jsonb;
alter table research_pool add column if not exists enrichment_status text default 'raw';

-- Durum filtresi (raw/enriched/verified) için basit index.
create index if not exists idx_research_enrichment_status
  on research_pool (enrichment_status);

-- ---- Doğrulama (uyguladıktan sonra çalıştırıp gör) ------------------------
-- select column_name, data_type, column_default
--   from information_schema.columns
--  where table_name = 'research_pool'
--    and column_name in ('extracted_facts','ai_summary','enrichment_status')
--  order by column_name;
