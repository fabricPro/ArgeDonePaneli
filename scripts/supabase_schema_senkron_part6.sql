-- Senkron Modülü — Sprint 6 (çok-sürümlü atkı) şeması (idempotent)
-- ===================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Tekrar tekrar çalıştırılabilir (CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).
--
-- Amaç: Bir loom_product için hangi ürün SÜRÜMLERİNİN bu tezgahta dokunacağı (seçim).
-- Her sürüm bağımsız atkı dokuma planı → seçili tüm sürümlerin tüketimi havuza TOPLANIR.
-- weft_color_mappings + weft_variant_actuals ZATEN surum_id taşıyor → motor çok-sürüme hazır;
-- bu tablo yalnızca "hangi sürümler seçili" bilgisini tutar. selected default TRUE.
-- Çözgü (warps) ETKİLENMEZ — sürümden bağımsız ürün-üstü kayıt.

create table if not exists loom_product_versions (
    id               text primary key,          -- lpv_<uuid hex[:10]>
    loom_product_id  text not null references loom_products(id) on delete cascade,
    surum_id         text not null,
    selected         boolean default true,
    created_at       timestamptz default now(),
    unique(loom_product_id, surum_id)
);
alter table loom_product_versions add column if not exists selected   boolean default true;
alter table loom_product_versions add column if not exists created_at timestamptz default now();
do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'loom_product_versions_natural_key') then
        alter table loom_product_versions add constraint loom_product_versions_natural_key
            unique (loom_product_id, surum_id);
    end if;
end $$;
create index if not exists idx_lpv_lp on loom_product_versions(loom_product_id);

-- Güvenlik: products ile aynı model — RLS açık, policy yok → yalnız service_role.
alter table loom_product_versions enable row level security;

-- Doğrulama:
-- select table_name from information_schema.tables where table_name = 'loom_product_versions';
