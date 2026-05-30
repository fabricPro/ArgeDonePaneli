-- v3.8 — Teknik Çalışma alanı (multi-sürüm)
-- products tablosuna teknik jsonb kolonu.
-- İçinde { active_surum_id, surumler: [{id, ad, parametreler, iplikler, tahar_grid, tarak_raporu, ...}] }
-- Backward-compat: tüm okumalar .get("teknik", {}) fallback ile.

alter table products add column if not exists teknik jsonb default '{}'::jsonb;

-- Doğrulama
select column_name, data_type, column_default
from information_schema.columns
where table_name = 'products' and column_name = 'teknik';
