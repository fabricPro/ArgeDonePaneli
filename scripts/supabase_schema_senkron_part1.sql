-- Senkron Modülü — Sprint 1 şeması (idempotent)
-- ===================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Tekrar tekrar çalıştırılabilir (CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).
--
-- Amaç: Tezgah (looms) + tezgaha atanan ürünler (loom_products).
-- Bu sprint SADECE bu 2 tablo. Havuz/çözgü/atkı/tüketim sonraki sprintlerde.
--
-- Bağlantı: loom_products.urun_id → products.urun_id (text PK).
--           loom_products.loom_id → looms.loom_id (text PK).
-- products ve app_state.workspace_data bu sprintte SALT OKUNUR (yazılmaz).

-- 1) TEZGAHLAR -------------------------------------------------------
create table if not exists looms (
    loom_id               text primary key,    -- kararlı PK (t_<uuid hex[:10]>); loom_no'dan AYRI
    loom_no               text not null,        -- görünen ad ("T01") — kullanıcı düzeltebilir
    max_width_cm          numeric,
    frame_count           integer,
    frame_purpose         text,                 -- SERBEST METİN ("1-6 alt çözgü, 8-9 kenar...")
    setup_name            text,
    reed_no               text,
    reed_report           text,
    working_warp_width_cm numeric,              -- ileride alt-çözgü validation'ında kullanılacak
    status                text default 'aktif',
    notes                 text,
    created_at            timestamptz default now(),
    updated_at            timestamptz default now()
);

-- idempotent kolon ekleri (tablo eksik kolonla önceden varsa)
alter table looms add column if not exists loom_no               text;
alter table looms add column if not exists max_width_cm          numeric;
alter table looms add column if not exists frame_count           integer;
alter table looms add column if not exists frame_purpose         text;
alter table looms add column if not exists setup_name            text;
alter table looms add column if not exists reed_no               text;
alter table looms add column if not exists reed_report           text;
alter table looms add column if not exists working_warp_width_cm numeric;
alter table looms add column if not exists status                text default 'aktif';
alter table looms add column if not exists notes                 text;
alter table looms add column if not exists created_at            timestamptz default now();
alter table looms add column if not exists updated_at            timestamptz default now();

-- 2) TEZGAHA ATANAN ÜRÜNLER -----------------------------------------
create table if not exists loom_products (
    id          text primary key,
    loom_id     text not null references looms(loom_id) on delete cascade,
    urun_id     text not null references products(urun_id) on delete cascade,
    sequence    integer default 0,            -- tezgah içi sıra
    notes       text,
    created_at  timestamptz default now(),
    unique(loom_id, urun_id)                  -- aynı ürün aynı tezgaha iki kez eklenmesin
);

alter table loom_products add column if not exists sequence   integer default 0;
alter table loom_products add column if not exists notes      text;
alter table loom_products add column if not exists created_at timestamptz default now();

-- Eski tabloda unique kısıt yoksa idempotent ekle
do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'loom_products_loom_id_urun_id_key'
    ) then
        alter table loom_products add constraint loom_products_loom_id_urun_id_key
            unique (loom_id, urun_id);
    end if;
end $$;

create index if not exists idx_loom_products_loom_id on loom_products(loom_id);
create index if not exists idx_loom_products_urun_id on loom_products(urun_id);

-- Güvenlik: products ile aynı model — RLS açık, policy yok → yalnız service_role (sunucu) erişir.
alter table looms enable row level security;
alter table loom_products enable row level security;

-- Doğrulama:
-- select table_name from information_schema.tables
-- where table_name in ('looms','loom_products');
-- Beklenen: 2 satır.
