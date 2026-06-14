-- Senkron Modülü — Sprint 4 şeması (idempotent)
-- ===================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Tekrar tekrar çalıştırılabilir (CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).
--
-- Amaç: ÇÖZGÜ. Senkron'da AYRI fiziksel kayıt (warps) — birden çok ürün paylaşır.
-- cozgu_plani'dan SEED alır ama kendi hayatını yaşar. Master (cozgu_plani/products/teknik) SALT OKUNUR.
-- İki eksen: (a) metre bütçesi ürünlere dağılır (warp_product_allocations),
--            (b) kurulum kg'si havuzdan düşer (warp_yarns→material_stock; atkı ile aynı kalemde toplanır).
-- Tüketim/işbağ/üst-tahar BU TABLOLARDA TUTULMAZ — canlı hesaplanır (reconcile-on-read).

-- 1) ÇÖZGÜLER --------------------------------------------------------
create table if not exists warps (
    id                    text primary key,     -- w_<uuid hex[:10]>
    loom_id               text not null references looms(loom_id) on delete cascade,
    name                  text,
    layer                 text default 'alt',   -- 'alt' | 'ust'
    kind                  text default 'duz',   -- 'duz' | 'blanket'
    thread_count          numeric,              -- tel adedi
    width_cm              numeric,
    length_m              numeric,              -- çözgü uzunluğu
    consumed_kg_override  numeric,              -- elle override; null = otomatik
    tie_group_override    text,                 -- elle işbağ düzeltmesi
    source_product_id     text,                 -- seed nereden (nullable)
    source_surum_id       text,
    source_durum          text,                 -- alt/ust/ust_2 (seed kaynağı)
    sequence              integer default 0,
    notes                 text,
    created_at            timestamptz default now(),
    updated_at            timestamptz default now()
);
alter table warps add column if not exists consumed_kg_override numeric;
alter table warps add column if not exists tie_group_override   text;
alter table warps add column if not exists source_product_id    text;
alter table warps add column if not exists source_surum_id      text;
alter table warps add column if not exists source_durum         text;
alter table warps add column if not exists sequence             integer default 0;
alter table warps add column if not exists notes                text;
alter table warps add column if not exists created_at           timestamptz default now();
alter table warps add column if not exists updated_at           timestamptz default now();

-- 2) ÇÖZGÜ İPLİKLERİ (kg buradan; blanket'te renk başına satır) -------
create table if not exists warp_yarns (
    id                 text primary key,        -- wy_<uuid hex[:10]>
    warp_id            text not null references warps(id) on delete cascade,
    material_stock_id  text references material_stock(id) on delete set null,  -- havuz kalemi silinince eşleme düşer, yarn kalır
    thread_count       numeric,                 -- bu rengin tel payı
    yarn_tip           text,                    -- seed kopyası (auto kg için — warp master'dan bağımsız)
    yarn_iplik         text,                    -- seed kopyası ("300*2" vb.)
    seed_renk_ad       text,
    seed_renk_hex      text,
    notes              text,
    created_at         timestamptz default now()
);
alter table warp_yarns add column if not exists material_stock_id text references material_stock(id) on delete set null;
alter table warp_yarns add column if not exists yarn_tip      text;
alter table warp_yarns add column if not exists yarn_iplik    text;
alter table warp_yarns add column if not exists seed_renk_ad  text;
alter table warp_yarns add column if not exists seed_renk_hex text;
alter table warp_yarns add column if not exists notes         text;
alter table warp_yarns add column if not exists created_at    timestamptz default now();

-- 3) METRE BÜTÇESİ DAĞILIMI ------------------------------------------
create table if not exists warp_product_allocations (
    id               text primary key,          -- wa_<uuid hex[:10]>
    warp_id          text not null references warps(id) on delete cascade,
    loom_product_id  text not null references loom_products(id) on delete cascade,
    allocated_m      numeric,
    notes            text,
    created_at       timestamptz default now(),
    unique(warp_id, loom_product_id)
);
alter table warp_product_allocations add column if not exists allocated_m numeric;
alter table warp_product_allocations add column if not exists notes       text;
alter table warp_product_allocations add column if not exists created_at  timestamptz default now();
do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'warp_alloc_natural_key') then
        alter table warp_product_allocations add constraint warp_alloc_natural_key unique (warp_id, loom_product_id);
    end if;
end $$;

create index if not exists idx_warps_loom on warps(loom_id);
create index if not exists idx_warp_yarns_warp on warp_yarns(warp_id);
create index if not exists idx_warp_yarns_ms on warp_yarns(material_stock_id);
create index if not exists idx_warp_alloc_warp on warp_product_allocations(warp_id);
create index if not exists idx_warp_alloc_lp on warp_product_allocations(loom_product_id);

-- Güvenlik: products ile aynı model — RLS açık, policy yok → yalnız service_role.
alter table warps enable row level security;
alter table warp_yarns enable row level security;
alter table warp_product_allocations enable row level security;

-- Doğrulama:
-- select table_name from information_schema.tables
-- where table_name in ('warps','warp_yarns','warp_product_allocations');
-- Beklenen: 3 satır.
