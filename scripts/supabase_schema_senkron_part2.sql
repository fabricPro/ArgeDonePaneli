-- Senkron Modülü — Sprint 2 şeması (idempotent)
-- ===================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Tekrar tekrar çalıştırılabilir (CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).
--
-- Amaç: İplik Havuzu (alım planı). Katalog-demirli (iplik+renk) çiftleri +
-- planlanan/gerçek alım kg. TÜKETİM/KALAN bu sprintte YOK (atkı=Sprint 3, çözgü=Sprint 4).
--
-- renk_id: katalog nested rengin KALICI renk_id'si (Sprint 0). Renk jsonb-nested olduğu
-- için DB-FK kurulamaz → tutarlılık UYGULAMA düzeyinde (kaydederken renk_id'nin o
-- kartelada var olduğu DOĞRULANIR: store.kartela_has_renk).

create table if not exists material_stock (
    id                   text primary key,    -- ms_<uuid hex[:10]>
    kartela_id           text not null references iplik_kartelalari(kartela_id) on delete cascade,
    renk_id              text not null,        -- katalog nested renk_id (FK kurulamaz; app doğrular)
    planned_purchase_kg  numeric,
    actual_purchase_kg   numeric,              -- çoğu zaman boş (nullable)
    notes                text,
    created_at           timestamptz default now(),
    updated_at           timestamptz default now(),
    unique(kartela_id, renk_id)               -- aynı iplik+renk havuzda tek satır
);

-- idempotent kolon ekleri (tablo eksik kolonla önceden varsa)
alter table material_stock add column if not exists planned_purchase_kg numeric;
alter table material_stock add column if not exists actual_purchase_kg  numeric;
alter table material_stock add column if not exists notes               text;
alter table material_stock add column if not exists created_at          timestamptz default now();
alter table material_stock add column if not exists updated_at          timestamptz default now();

-- Eski tabloda unique kısıt yoksa idempotent ekle
do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'material_stock_kartela_id_renk_id_key'
    ) then
        alter table material_stock add constraint material_stock_kartela_id_renk_id_key
            unique (kartela_id, renk_id);
    end if;
end $$;

create index if not exists idx_material_stock_kartela_id on material_stock(kartela_id);

-- Güvenlik: products ile aynı model — RLS açık, policy yok → yalnız service_role (sunucu) erişir.
alter table material_stock enable row level security;

-- Doğrulama:
-- select table_name from information_schema.tables where table_name = 'material_stock';
-- Beklenen: 1 satır.
