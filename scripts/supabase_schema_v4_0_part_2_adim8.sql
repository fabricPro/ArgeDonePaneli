-- v4.0-part-2 Adım 8 — Ön Çalışma Alanı (research_pool) + Galeri Filtreleri
--
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Idempotent (IF NOT EXISTS / IF EXISTS): tekrar çalıştırmak güvenli.

-- ============================================================
-- 1) products tablosuna yeni sütunlar
-- ============================================================

-- 1.1 Çalışma durumu: 'active' (galeride görünür) | 'archived' ("çalışma yapıldı", soluk/filtrelenebilir)
alter table products
  add column if not exists status text default 'active';
-- CHECK constraint'i ayrı ekle (idempotent: önce drop sonra add)
alter table products drop constraint if exists products_status_check;
alter table products add constraint products_status_check
  check (status in ('active', 'archived'));

-- 1.2 ISO-2 ülke kodu (filtre + sıralama için normalize)
alter table products
  add column if not exists country_code text;

-- 1.3 source_url normalize edilmiş MD5 (dedup için — research_pool ile çapraz kontrol)
alter table products
  add column if not exists source_url_hash text;

-- Index'ler
create index if not exists idx_products_status        on products(status);
create index if not exists idx_products_country_code  on products(country_code);
create index if not exists idx_products_source_url_h  on products(source_url_hash);

-- ============================================================
-- 2) research_pool — Ön Çalışma havuzu
-- ============================================================
-- Akış: kullanıcı internette gezerken link biriktirir → "pending" durumunda kayıt
--       → boş zamanda detay çekip ürüne dönüştürür → "imported"
--       → silmek yerine "dismissed" (soft delete) — geri açılabilir.

create table if not exists research_pool (
  id                   uuid primary key default gen_random_uuid(),
  master_url           text not null,           -- "https://www.dedar.com/curtains?w_min=300"
  product_url          text not null,           -- "https://www.dedar.com/curtains/cobra-101"
  product_url_hash     text not null,           -- normalize edilmiş MD5 (UNIQUE)
  brand                text not null,           -- "Dedar" (görüntü)
  brand_slug           text not null,           -- "dedar" (registry id)
  country              text not null,           -- "İtalya"
  country_code         text,                    -- "IT"
  thumb_url            text,                    -- og:image cache (CDN url)
  status               text default 'pending',  -- pending | imported | dismissed
  imported_product_id  text,                    -- ürüne dönüştüyse hangi urun_id
  added_at             timestamptz default now(),
  imported_at          timestamptz,
  notes                text,                    -- kısa serbest not (opsiyonel)
  constraint research_pool_url_unique unique (product_url_hash)
);

-- Status check
alter table research_pool drop constraint if exists research_pool_status_check;
alter table research_pool add constraint research_pool_status_check
  check (status in ('pending', 'imported', 'dismissed'));

-- Index'ler
create index if not exists idx_research_pool_status     on research_pool(status);
create index if not exists idx_research_pool_brand_slug on research_pool(brand_slug);
create index if not exists idx_research_pool_country    on research_pool(country_code);
create index if not exists idx_research_pool_added      on research_pool(added_at desc);

-- ============================================================
-- 3) Notlar — products.notlar_html (mevcut, ürün-seviyesi) korunur
--    Ek olarak teknik.surumler[].notlar_html JSONB içinde tutulur (DDL gereksiz)
-- ============================================================
-- Not: surum-seviyesi notlar `teknik` JSONB sütunun içindeki array
-- elemanlarına eklenir; Python tarafı yazar/okur, SQL şeması değişmez.
-- Geriye uyum: surum.notlar_html boşsa product.notlar_html fallback gösterilir.

-- ============================================================
-- DOĞRULAMA (manuel sorular)
-- ============================================================
-- select column_name, data_type, column_default
-- from information_schema.columns
-- where table_name = 'products' and column_name in ('status','country_code','source_url_hash');
--
-- select count(*) from research_pool;
--
-- select column_name from information_schema.columns where table_name = 'research_pool';
