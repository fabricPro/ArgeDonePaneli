-- v4.0-part-2 Sprint 10 — research_pool = kumaş galerisi (Pinterest mantığı)
--
-- Branch: GorselToplamaV2
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Idempotent: tekrar çalıştırmak güvenli.
-- Önce supabase_schema_v4_0_part_2_adim8.sql + adim8_v2.sql + adim9.sql çalışmış olmalı.

-- ============================================================
-- 1) Yeni kolon: images JSONB array
-- ============================================================
-- Bir research_pool satırı artık birden fazla görsel barındırabilir.
-- Array elemanı şeması:
--   {
--     "sha256": "<64-hex>",
--     "storage_path": "_inbox/<brand_slug>/<sha8>.jpg",
--     "alt": "kullanıcı alt text",
--     "source_image_url": "https://original-image-url",
--     "added_at": "ISO timestamp"
--   }

alter table research_pool
  add column if not exists images jsonb default '[]'::jsonb;

-- ============================================================
-- 2) GIN index — SHA-256 dedup lookup için
-- ============================================================
-- Tüm rows'ta `images @> [{"sha256": "..."}]` containment sorgusu yapacağız.
-- GIN index olmadan full table scan olur.

create index if not exists idx_research_pool_images_gin
  on research_pool using gin (images);

-- ============================================================
-- 3) Geriye uyum migration: mevcut tek-görsel kolonları images[]'e taşı
-- ============================================================
-- Sprint 9'da yakalanan satırlar image_sha256 + image_storage_path kolonlarını
-- doldurdu. Onları images[0] olarak array'e aktar (sadece images boşsa).

update research_pool
set images = jsonb_build_array(
  jsonb_build_object(
    'sha256',           image_sha256,
    'storage_path',     image_storage_path,
    'alt',              notes,
    'source_image_url', null,
    'added_at',         added_at
  )
)
where image_storage_path is not null
  and image_sha256 is not null
  and (images is null or images = '[]'::jsonb);

-- ============================================================
-- DOĞRULAMA (manuel sorular)
-- ============================================================
-- Mevcut Sprint 9 yakalama satırları images[] olarak migrate oldu mu:
-- select id, brand, jsonb_array_length(images) as img_count,
--        images->0->>'sha256' as first_sha,
--        image_sha256 as legacy_sha
-- from research_pool
-- where image_sha256 is not null
-- limit 5;
--
-- Beklenen: img_count=1, first_sha = legacy_sha (eşit olmalı)
--
-- GIN index var mı:
-- select indexname from pg_indexes where tablename='research_pool';
-- Beklenen: idx_research_pool_images_gin listede
--
-- JSONB containment test (örnek bir sha ile):
-- select id, brand from research_pool
-- where images @> '[{"sha256": "0f80506b0eb2a3b7b8b33526f1ee349afeb7b0c1887fc6eac7bb18170569042f"}]'::jsonb;
-- Beklenen: o sha hangi entry'deyse o satır (Sprint 9'da yakalanan)
