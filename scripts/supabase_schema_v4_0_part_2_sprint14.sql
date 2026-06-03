-- v4.0-part-2 Sprint 14 — products tablosuna from_research_id kolonu
-- ===================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Idempotent: tekrar çalıştırmak güvenli.
--
-- Amaç: Bir ürün ön çalışmadan (research_pool) oluşturulduğunda,
-- hangi research kaydından geldiğini saklamak. Ürün detayında "Ön Çalışma"
-- sekmesi bu alanı kullanır.

alter table products
  add column if not exists from_research_id text;

-- Hızlı join için index (opsiyonel — küçük tabloda fark az)
create index if not exists idx_products_from_research_id
  on products (from_research_id)
  where from_research_id is not null;

-- Doğrulama:
-- select column_name from information_schema.columns
-- where table_name = 'products' and column_name = 'from_research_id';
-- Beklenen: 1 satır
