-- v4.0-part-2 Adım 8 (v2) — research_pool: favori (yıldız) sütunu
--
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Idempotent (IF NOT EXISTS): tekrar çalıştırmak güvenli.
-- Önce supabase_schema_v4_0_part_2_adim8.sql çalışmış olmalı.

alter table research_pool
  add column if not exists is_favorite boolean default false;

-- Sadece favori satırları için kısmi index (filter sorgusu hızlı olsun)
create index if not exists idx_research_pool_favorite
  on research_pool (is_favorite)
  where is_favorite = true;

-- DOĞRULAMA
-- select column_name from information_schema.columns
--   where table_name='research_pool' and column_name='is_favorite';
