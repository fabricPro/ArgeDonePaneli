-- ============================================================================
-- OnCalisma-V2 (Problem 2) — Taksonomi sınıflandırma alanları
-- ============================================================================
-- Kumaşları ülke/firma yerine ÜÇ BAĞIMSIZ EKSENDE sınıflandırmak için 5 yeni
-- alan: category, pattern, weave_tags, style_tags, color_family.
-- Hem products hem research_pool tablosuna eklenir.
--
-- DİKKAT: Bu dosya OTOMATİK ÇALIŞTIRILMAZ. Supabase SQL editöründe ELLE uygula.
-- Idempotent (IF NOT EXISTS) — birden çok kez çalıştırmak güvenlidir.
-- Tüm kolonlar nullable + güvenli default → mevcut kayıtlar bozulmaz (null / '[]').
--
-- Controlled vocabulary KODDA sabittir (web/store.py: VALID_CATEGORIES vb.) —
-- DB'de CHECK constraint YOK (esneklik + tek kaynak kodda).
-- ============================================================================

-- ---- products -------------------------------------------------------------
alter table products add column if not exists category     text;
alter table products add column if not exists pattern      text;
alter table products add column if not exists weave_tags   jsonb default '[]'::jsonb;
alter table products add column if not exists style_tags   jsonb default '[]'::jsonb;
alter table products add column if not exists color_family text;

create index if not exists idx_products_category     on products (category);
create index if not exists idx_products_pattern      on products (pattern);
create index if not exists idx_products_color_family on products (color_family);
-- GIN: jsonb containment sorgusu — örn. weave_tags @> '["vual"]' ("çizgili vual tüller")
create index if not exists idx_products_weave_tags   on products using gin (weave_tags);

-- ---- research_pool --------------------------------------------------------
alter table research_pool add column if not exists category     text;
alter table research_pool add column if not exists pattern      text;
alter table research_pool add column if not exists weave_tags   jsonb default '[]'::jsonb;
alter table research_pool add column if not exists style_tags   jsonb default '[]'::jsonb;
alter table research_pool add column if not exists color_family text;

create index if not exists idx_research_category     on research_pool (category);
create index if not exists idx_research_pattern      on research_pool (pattern);
create index if not exists idx_research_color_family on research_pool (color_family);
create index if not exists idx_research_weave_tags   on research_pool using gin (weave_tags);

-- ---- Doğrulama (uyguladıktan sonra çalıştırıp gör) ------------------------
-- select column_name, data_type, column_default
--   from information_schema.columns
--  where table_name in ('products','research_pool')
--    and column_name in ('category','pattern','weave_tags','style_tags','color_family')
--  order by table_name, column_name;
