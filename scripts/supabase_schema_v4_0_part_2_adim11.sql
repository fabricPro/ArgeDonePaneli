-- v4.0-part-2 Sprint 11 (BİRLEŞTİRİLMİŞ) — iki paralel çalışmayı tek dosyada toplar
-- ====================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Idempotent: tekrar çalıştırmak güvenli (her şey "if not exists" / koşullu).
-- Önce adim10.sql (research_pool.images jsonb) çalışmış olmalı.
--
-- İki Sprint birleşik:
--   A) Sprint 11 — Ürün öncesi albüm + renk paleti (research_pool.albums)
--   B) Sprint 11.5 — country ayrımı + reference_price (products & research_pool)

-- ====================================================================
-- BÖLÜM A — Sprint 11: research_pool.albums + images[] genişletmesi
-- ====================================================================
-- Eleman şeması: { "slug": "<slug>", "name": "Görünen Ad" }
-- "Renkler" slug'lı/adlı albüm renk çözümleme için özel rol oynar.

alter table research_pool
  add column if not exists albums jsonb default '[]'::jsonb;

-- images[] eleman şeması GENİŞLETİLDİ (DDL değişikliği yok — JSONB):
--   {
--     "sha256":           "<64-hex>",
--     "storage_path":     "_inbox/<brand_slug>/<sha8>.jpg",
--     "alt":              "kullanıcı alt text",
--     "source_image_url": "https://original-image-url",
--     "added_at":         "ISO timestamp",
--     "albums":           ["renkler", "varyantlar"],     -- YENİ (opsiyonel)
--     "colors":           {                              -- YENİ (opsiyonel)
--       "weft": {"hex":"#RRGGBB","rgb":[r,g,b],"lab":[L,a,b],"name":"...","picked_at":"ISO"},
--       "warp": {...},
--       "mix":  {...}
--     }
--   }
-- JSONB olduğu için kolon değişikliği gerekmez; uygulama katmanı yazar.

-- ====================================================================
-- BÖLÜM B — Sprint 11.5: country ayrımı + reference_price (products)
-- ====================================================================
-- 1. Mevcut tek "country" alanı (HQ semantiği) ikiye bölünür:
--      brand_country       = firma merkezi (HQ)        — mevcut country verisi taşınır
--      production_country  = üretim yeri ("Made in")   — sadece Gemini sayfadan çıkarır
-- 2. Yeni fiyat alanları:
--      reference_price          = "140,74 EUR" gibi normalize değer
--      reference_price_type     = 'exact' | 'from'
--      reference_price_evidence = sayfa alıntısı ("Configure from 140,74 €")
--
-- Eski country/country_code kolonları KORUNUR (geriye uyum için).
-- Senkron: backend her yazımda country = brand_country tutar.

-- B.1 products tablosu — country ayrımı
alter table products add column if not exists brand_country            text;
alter table products add column if not exists brand_country_code       text;
alter table products add column if not exists production_country       text;
alter table products add column if not exists production_country_code  text;

-- B.2 products tablosu — referans fiyat (anayasa #3 esnetildi)
alter table products add column if not exists reference_price          text;
alter table products add column if not exists reference_price_type     text;
alter table products add column if not exists reference_price_evidence text;

-- enum kısıtı: 'exact' veya 'from' (veya null). Backend'de de validasyon var.
do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints
        where constraint_name = 'products_reference_price_type_check'
          and table_name = 'products'
    ) then
        alter table products
            add constraint products_reference_price_type_check
            check (reference_price_type in ('exact', 'from') or reference_price_type is null);
    end if;
end $$;

-- B.3 Mevcut country verisini brand_country'ye taşı (HQ semantiği — kanıtlanmış)
update products
set brand_country      = country,
    brand_country_code = country_code
where brand_country is null
  and country is not null;

-- B.4 research_pool tablosu — country ayrımı (zaten HQ kullanıyordu)
alter table research_pool add column if not exists brand_country      text;
alter table research_pool add column if not exists brand_country_code text;

update research_pool
set brand_country      = country,
    brand_country_code = country_code
where brand_country is null
  and country is not null;

-- B.5 Filtre/arama indeksleri
create index if not exists idx_products_brand_country
    on products (brand_country);

create index if not exists idx_products_production_country
    on products (production_country);

create index if not exists idx_research_pool_brand_country
    on research_pool (brand_country);

-- ====================================================================
-- DOĞRULAMA (manuel sorgular — Run sonrası çalıştırılabilir)
-- ====================================================================
-- A) research_pool.albums kolonu eklendi mi:
-- select column_name, data_type from information_schema.columns
-- where table_name='research_pool' and column_name='albums';
-- Beklenen: albums | jsonb
--
-- B) products'taki yeni kolonlar:
-- select column_name from information_schema.columns
-- where table_name = 'products'
--   and column_name in ('brand_country','brand_country_code',
--                       'production_country','production_country_code',
--                       'reference_price','reference_price_type','reference_price_evidence');
-- Beklenen: 7 satır
--
-- C) Migration brand_country'yi doldurdu mu:
-- select urun_id, country, brand_country from products limit 5;
-- Beklenen: brand_country = country (her satır)
--
-- D) Check constraint var mı:
-- select conname from pg_constraint where conrelid = 'products'::regclass
--   and conname = 'products_reference_price_type_check';
-- Beklenen: 1 satır
