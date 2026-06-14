-- Senkron Modülü — Sprint 3 şeması (idempotent)
-- ===================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Tekrar tekrar çalıştırılabilir (CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).
--
-- Amaç: ATKI renk eşleme. "Bu tezgahtaki bu ürünün, bu atkı pozisyonundaki bu renk =
-- havuzdaki şu kalem". Tüketim BURADA TUTULMAZ — atki_varyant_plani'ndan canlı hesaplanır
-- (reconcile-on-read). Master (products/teknik/atki_varyant_plani) SALT OKUNUR.
--
-- Eşleme cascade: loom_product veya material_stock silinince eşleme otomatik düşer (öksüz kalmaz).

create table if not exists weft_color_mappings (
    id                text primary key,        -- wm_<uuid hex[:10]>
    loom_product_id   text not null references loom_products(id) on delete cascade,
    surum_id          text not null,            -- hangi sürümün atkı planı
    iplik_index       integer not null,         -- atki_varyant_plani iplik pozisyonu
    cell_key          text not null,            -- hücre kimliği (iplik kolonundaki renk: lower(hex)|lower(ad))
    material_stock_id text not null references material_stock(id) on delete cascade,
    notes             text,
    created_at        timestamptz default now(),
    unique(loom_product_id, surum_id, iplik_index, cell_key)
);

-- idempotent kolon ekleri
alter table weft_color_mappings add column if not exists notes      text;
alter table weft_color_mappings add column if not exists created_at timestamptz default now();

-- Eski tabloda unique kısıt yoksa idempotent ekle
do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'weft_color_mappings_natural_key'
    ) then
        alter table weft_color_mappings add constraint weft_color_mappings_natural_key
            unique (loom_product_id, surum_id, iplik_index, cell_key);
    end if;
end $$;

create index if not exists idx_weft_map_loom_product on weft_color_mappings(loom_product_id);
create index if not exists idx_weft_map_material_stock on weft_color_mappings(material_stock_id);

-- Güvenlik: products ile aynı model — RLS açık, policy yok → yalnız service_role (sunucu).
alter table weft_color_mappings enable row level security;

-- Doğrulama:
-- select table_name from information_schema.tables where table_name = 'weft_color_mappings';
-- Beklenen: 1 satır.
