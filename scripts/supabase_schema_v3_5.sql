-- v3.5 — Album sistemi (etiket / çoklu üyelik)
-- products tablosuna albums jsonb kolonu (default boş liste).
-- Her ürünün albums alanı: [{slug: "...", name: "..."}, ...]
-- images[i] dict'i içinde de "albums" alanı eklenir (jsonb içinde, şema dışı).
-- Backward-compat: tüm okuma noktalarında .get("albums", []) fallback.

alter table products add column if not exists albums jsonb default '[]'::jsonb;

-- Doğrulama
select column_name, data_type, column_default
from information_schema.columns
where table_name = 'products' and column_name = 'albums';
