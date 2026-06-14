-- Senkron Modülü — Sprint 7 (REFACTOR: tezgaha atanan birim ÜRÜN → SÜRÜM) — idempotent
-- ===================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Tekrar tekrar çalıştırılabilir.
--
-- Amaç: loom_products satırı artık bir (loom, urun, SÜRÜM) atamasıdır.
--   - loom_products'a surum_id eklenir (NOT NULL).
--   - unique(loom_id, urun_id) → unique(urun_id, surum_id) (aynı sürüm TEK tezgahta;
--     bir ürünün farklı sürümleri farklı tezgahlarda olabilir).
--   - loom_product_versions TABLOSU KALDIRILIR (atama = seçim; ayrı toggle gerekmez).
--   - Atkı çocukları (weft_color_mappings / weft_variant_actuals) ve çözgü allocations
--     ZATEN loom_products.id'ye FK; dokunulmaz. Çözgü allocations otomatik sürüm-bazlı olur
--     (hedef satır artık bir sürüm).
--
-- Bağlam: bu refactor öncesi alt-akış (mappings/actuals/allocations/warps) BOŞ (beta).
--   loom_products'taki birkaç eski satır aşağıda aktif sürüme (yoksa 'v1') backfill edilir.

-- 1) surum_id kolonu (önce nullable — backfill için) -----------------
alter table loom_products add column if not exists surum_id text;

-- 2) Eski satırları backfill et: products.teknik.active_surum_id (yoksa 'v1') ----
update loom_products lp
   set surum_id = coalesce(nullif(p.teknik->>'active_surum_id', ''), 'v1')
  from products p
 where p.urun_id = lp.urun_id
   and (lp.surum_id is null or lp.surum_id = '');

-- products eşleşmeyen olası öksüz satırlar için son çare (FK cascade nedeniyle teorik):
update loom_products set surum_id = 'v1' where surum_id is null or surum_id = '';

-- 3) NOT NULL'a çek --------------------------------------------------
do $$
begin
    if not exists (
        select 1 from information_schema.columns
        where table_name = 'loom_products' and column_name = 'surum_id' and is_nullable = 'NO'
    ) then
        alter table loom_products alter column surum_id set not null;
    end if;
end $$;

-- 4) Unique kısıtı değiştir: (loom_id,urun_id) DÜŞ → (urun_id,surum_id) EKLE ----
do $$
begin
    if exists (select 1 from pg_constraint where conname = 'loom_products_loom_id_urun_id_key') then
        alter table loom_products drop constraint loom_products_loom_id_urun_id_key;
    end if;
    if not exists (select 1 from pg_constraint where conname = 'loom_products_urun_surum_key') then
        alter table loom_products add constraint loom_products_urun_surum_key
            unique (urun_id, surum_id);
    end if;
end $$;

create index if not exists idx_loom_products_surum on loom_products(surum_id);

-- 5) loom_product_versions KALDIRILIR (artık atama = seçim) -----------
drop table if exists loom_product_versions cascade;

-- Doğrulama:
-- select column_name from information_schema.columns
--   where table_name='loom_products' and column_name='surum_id';   -- 1 satır
-- select conname from pg_constraint where conname='loom_products_urun_surum_key'; -- 1 satır
-- select to_regclass('loom_product_versions');  -- NULL (tablo gitti)
