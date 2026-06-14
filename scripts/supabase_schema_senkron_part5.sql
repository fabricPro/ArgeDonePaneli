-- Senkron Modülü — Sprint 5 (SON) şeması (idempotent)
-- ===================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Tekrar tekrar çalıştırılabilir (CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).
--
-- Amaç: DOKUMA SONRASI GERÇEKLEŞEN. Master (atki_varyant_plani/cozgu_plani/products) SALT OKUNUR.
-- Gerçekleşen Senkron'un kendi kaydında durur. Planlanan (Sprint 3-4) ZERRE değişmez.
--   Atkı: varyant bazlı "dokundu mu" + "gerçek metre" (boşsa plan metresi geçerli).
--   Çözgü: warps.actual_length_m (boşsa length_m geçerli).

-- 1) ATKI VARYANT GERÇEKLEŞENİ -------------------------------------
create table if not exists weft_variant_actuals (
    id               text primary key,          -- wva_<uuid hex[:10]>
    loom_product_id  text not null references loom_products(id) on delete cascade,
    surum_id         text not null,
    variant_index    integer not null,
    woven            boolean default true,       -- false → o varyant tüketimden çıkar
    actual_m         numeric,                    -- boşsa plan metresi
    notes            text,
    created_at       timestamptz default now(),
    unique(loom_product_id, surum_id, variant_index)
);
alter table weft_variant_actuals add column if not exists woven    boolean default true;
alter table weft_variant_actuals add column if not exists actual_m numeric;
alter table weft_variant_actuals add column if not exists notes    text;
alter table weft_variant_actuals add column if not exists created_at timestamptz default now();
do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'weft_variant_actuals_natural_key') then
        alter table weft_variant_actuals add constraint weft_variant_actuals_natural_key
            unique (loom_product_id, surum_id, variant_index);
    end if;
end $$;
create index if not exists idx_wva_lp on weft_variant_actuals(loom_product_id);

-- 2) ÇÖZGÜ GERÇEKLEŞEN UZUNLUĞU ------------------------------------
alter table warps add column if not exists actual_length_m numeric;

-- Güvenlik: products ile aynı model — RLS açık, policy yok → yalnız service_role.
alter table weft_variant_actuals enable row level security;

-- Doğrulama:
-- select table_name from information_schema.tables where table_name = 'weft_variant_actuals';
-- select column_name from information_schema.columns where table_name='warps' and column_name='actual_length_m';
