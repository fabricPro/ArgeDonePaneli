-- v4.0-part-2 Sprint 9 — Tarayıcı eklentisi görsel yakalama için kolonlar
--
-- Branch: GorselToplamaV2
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Idempotent (IF NOT EXISTS): tekrar çalıştırmak güvenli.
-- Önce supabase_schema_v4_0_part_2_adim8.sql + adim8_v2.sql çalışmış olmalı.

-- ============================================================
-- 1) Yeni kolonlar
-- ============================================================

-- 1.1 Görsel içerik hash'i (SHA-256). Tarayıcı eklentisinden gelen
--     orijinal görsel bytes üzerinden hesaplanır. UNIQUE = aynı görsel
--     ikinci kez yakalanırsa yeni satır eklenmez, mevcut döndürülür.
alter table research_pool
  add column if not exists image_sha256 text;

-- 1.2 Sayfa başlığı (tarayıcıda görselin bulunduğu sayfanın <title>'ı)
alter table research_pool
  add column if not exists page_title text;

-- 1.3 Storage path'i (gorseller bucket içinde).
--     Format: "_inbox/<brand_slug>/<sha[:8]>.jpg"
alter table research_pool
  add column if not exists image_storage_path text;

-- ============================================================
-- 2) Index'ler
-- ============================================================

-- Kısmi UNIQUE: sadece dolu sha256'lar benzersiz olmak zorunda.
-- Mevcut satırlarda image_sha256 null, çakışma yaratmaz.
-- İleride doldukça benzersizlik garantili (race condition + retry için ideal).
create unique index if not exists research_pool_image_sha256_unique
  on research_pool (image_sha256)
  where image_sha256 is not null;

-- Lookup için ek normal index
create index if not exists idx_research_pool_image_sha256
  on research_pool (image_sha256);

-- ============================================================
-- DOĞRULAMA (manuel sorular)
-- ============================================================
-- select column_name, data_type
-- from information_schema.columns
-- where table_name = 'research_pool'
--   and column_name in ('image_sha256', 'page_title', 'image_storage_path');
-- Beklenen: 3 satır
--
-- select indexname from pg_indexes where tablename = 'research_pool';
-- Beklenen: research_pool_image_sha256_unique listede
