-- v4.0-part-2 Sprint 11 — Ürün öncesi albüm + renk paleti (research_pool)
--
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Idempotent: tekrar çalıştırmak güvenli.
-- Önce adim10.sql (images jsonb) çalışmış olmalı.
--
-- Amaç: Ön çalışma (research_pool) kayıtlarında, ürün oluşturulmadan ÖNCE
-- görselleri albümlere ("Renkler" galerisi dahil) ayırabilmek ve atkı/çözgü/
-- toplam renk seçip renk paletini hazırlayabilmek. "Ürüne Çevir" sırasında bu
-- veri ürüne kopyalanır.

-- ============================================================
-- 1) Yeni kolon: albums JSONB array (ürün albums kolonuyla aynı yapı)
-- ============================================================
-- Eleman şeması: { "slug": "<slug>", "name": "Görünen Ad" }
-- "Renkler" slug'lı/adlı albüm renk çözümleme için özel rol oynar.

alter table research_pool
  add column if not exists albums jsonb default '[]'::jsonb;

-- ============================================================
-- 2) images[] eleman şeması GENİŞLETİLDİ (DDL değişikliği yok — JSONB)
-- ============================================================
-- adim10'daki images[] elemanına opsiyonel iki alan eklendi:
--   {
--     "sha256":           "<64-hex>",
--     "storage_path":     "_inbox/<brand_slug>/<sha8>.jpg",
--     "alt":              "kullanıcı alt text",
--     "source_image_url": "https://original-image-url",
--     "added_at":         "ISO timestamp",
--     "albums":           ["renkler", "varyantlar"],          -- YENİ (opsiyonel) albüm slug listesi
--     "colors":           {                                    -- YENİ (opsiyonel) renk atamaları
--       "weft": {"hex":"#RRGGBB","rgb":[r,g,b],"lab":[L,a,b],"name":"...", "picked_at":"ISO"},
--       "warp": {...},
--       "mix":  {...}
--     }
--   }
-- JSONB olduğu için kolon değişikliği gerekmez; uygulama katmanı yazar.

-- ============================================================
-- DOĞRULAMA (manuel sorular)
-- ============================================================
-- albums kolonu eklendi mi:
-- select column_name, data_type from information_schema.columns
-- where table_name='research_pool' and column_name='albums';
-- Beklenen: albums | jsonb
--
-- Bir entry'de albüm + renkli görsel örneği:
-- select id, brand, albums,
--        jsonb_array_length(images) as img_count,
--        images->0->'albums' as first_img_albums,
--        images->0->'colors' as first_img_colors
-- from research_pool
-- where albums <> '[]'::jsonb
-- limit 5;
