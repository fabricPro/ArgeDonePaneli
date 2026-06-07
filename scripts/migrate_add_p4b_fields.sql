-- ============================================================================
-- OnCalisma-V2 (Problem 4b) — Renk sayısı + AI notu (kalıcı)
-- ============================================================================
-- products VE research_pool'a:
--   color_count integer  → renk/varyant sayısı (AI önerir, kullanıcı doğrular)
--   ai_notu     text      → AI'nın ürün notu (arge_notu_taslak'tan); kullanıcının
--                           kendi arge_notu'sundan BAĞIMSIZ — AI doğruluğunu izlemek için
--
-- DİKKAT: OTOMATİK ÇALIŞTIRILMAZ. Supabase SQL editöründe ELLE uygula.
-- Idempotent (IF NOT EXISTS). SADECE EKLER — color_family DAHİL hiçbir kolon DROP edilmez.
-- (color_family kolonu korunur; arayüzden emekli edildi, DB'de boş kalır — zararsız.)
-- ============================================================================

alter table products      add column if not exists color_count integer;
alter table products      add column if not exists ai_notu     text;
alter table research_pool add column if not exists color_count integer;
alter table research_pool add column if not exists ai_notu     text;

create index if not exists idx_products_color_count on products (color_count);
create index if not exists idx_research_color_count on research_pool (color_count);

-- ---- Doğrulama (uyguladıktan sonra) --------------------------------------
-- select column_name, data_type from information_schema.columns
--   where table_name in ('products','research_pool')
--     and column_name in ('color_count','ai_notu') order by table_name, column_name;
