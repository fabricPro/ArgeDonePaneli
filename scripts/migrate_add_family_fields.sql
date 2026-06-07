-- OnCalisma-V2 (Problem 1) — research_pool ürün ailesi / varyant tespiti kolonları
-- ===================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
--             (OTOMATİK ÇALIŞTIRILMADI — elle/CI ile uygulanmalı.)
-- Idempotent: tekrar çalıştırmak güvenli. Hepsi nullable + güvenli default →
--             mevcut ~125 kayıt bozulmaz (yeni alanlar null/false kalır).
-- Geri alma: alttaki DROP bloğu (opsiyonel, kolonlar zaten zararsız).
--
-- Amaç: Aynı kumaşın farklı renk varyantlarının (ayrı URL) havuza ayrı kayıt
-- girip kalabalık yaratmasını "işaretleyerek" yönetmek. DEDUP DEĞİŞMEZ
-- (product_url_hash UNIQUE + image_sha256 katmanları aynen kalır); bu yalnız
-- bilgilendirici 3. katman. Birleştirme kararı kullanıcıya ait (Anayasa #6).

alter table research_pool add column if not exists family_key           text;
alter table research_pool add column if not exists base_code            text;
alter table research_pool add column if not exists is_variant_candidate boolean default false;
alter table research_pool add column if not exists variant_of           uuid;

-- variant_of: aynı ailedeki en eski (ana) kaydın id'si; yoksa null.
-- FK İSTEĞE BAĞLI (uygulanmadı — self-FK backfill riskini önlemek için plain UUID):
--   alter table research_pool add constraint research_pool_variant_of_fk
--     foreign key (variant_of) references research_pool(id) on delete set null;

create index if not exists idx_research_family_key on research_pool(family_key);

-- Doğrulama:
-- select column_name from information_schema.columns
--   where table_name = 'research_pool'
--   and column_name in ('family_key','base_code','is_variant_candidate','variant_of');
-- Beklenen: 4 satır.

-- Geri alma (opsiyonel):
-- drop index if exists idx_research_family_key;
-- alter table research_pool drop column if exists variant_of;
-- alter table research_pool drop column if exists is_variant_candidate;
-- alter table research_pool drop column if exists base_code;
-- alter table research_pool drop column if exists family_key;
