-- Görevler (To-Do terfisi) — Faz 1 şeması (idempotent)
-- ===================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Tekrar tekrar çalıştırılabilir (CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).
--
-- Amaç: Bugüne kadar products.todo (jsonb dizi) içinde yaşayan To-Do listesini
--       gerçek bir tabloya (gorevler) taşımak. Bu faz SADECE backend zemini:
--       görünür UI (todo.js / urun.html) değişmedi; eski panel artık veriyi
--       bu tablodan alır/yazar.
--
-- Bağlantı: gorevler.product_id → products.urun_id (TEXT PK).
--   NOT: products tablosunda uuid 'id' kolonu YOKTUR; birincil anahtar urun_id (text).
--   Bu yüzden FK, looms/loom_products deseniyle aynı: references products(urun_id).
--   surum_id ürünün JSON 'teknik.surumler' listesindeki sürüm id'sidir → FK YOK
--   (sürümler ayrı tabloda değil, products içindeki jsonb'de yaşar). NULL = ürün geneli.
--
-- products.todo kolonuna DOKUNULMAZ — yerinde kalır (non-destructive). Veri taşıma
-- (backfill) yapılmaz: canlıda 0 todo item olduğu doğrulandı.

create table if not exists gorevler (
    id           uuid primary key default gen_random_uuid(),
    product_id   text not null references products(urun_id) on delete cascade,
    surum_id     text,                                 -- ürünün jsonb sürüm id'si; NULL = ürün geneli (FK yok)
    baslik       text not null,
    durum        text not null default 'acik'
                 check (durum in ('acik', 'yapiliyor', 'tamamlandi')),
    oncelik      text check (oncelik in ('dusuk', 'orta', 'yuksek')),  -- NULL serbest
    sira         integer not null default 0,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now(),
    completed_at timestamptz
);

-- idempotent kolon ekleri (tablo eksik kolonla önceden varsa)
alter table gorevler add column if not exists surum_id     text;
alter table gorevler add column if not exists baslik       text;
alter table gorevler add column if not exists durum        text not null default 'acik';
alter table gorevler add column if not exists oncelik      text;
alter table gorevler add column if not exists sira         integer not null default 0;
alter table gorevler add column if not exists created_at   timestamptz not null default now();
alter table gorevler add column if not exists updated_at   timestamptz not null default now();
alter table gorevler add column if not exists completed_at timestamptz;

-- CHECK kısıtları (tablo önceden kısıtsız varsa idempotent ekle)
do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'gorevler_durum_check') then
        alter table gorevler add constraint gorevler_durum_check
            check (durum in ('acik', 'yapiliyor', 'tamamlandi'));
    end if;
    if not exists (select 1 from pg_constraint where conname = 'gorevler_oncelik_check') then
        alter table gorevler add constraint gorevler_oncelik_check
            check (oncelik in ('dusuk', 'orta', 'yuksek'));
    end if;
end $$;

create index if not exists idx_gorevler_product_id on gorevler(product_id);
create index if not exists idx_gorevler_durum      on gorevler(durum);
create index if not exists idx_gorevler_surum_id   on gorevler(surum_id);

-- Güvenlik: products ile aynı model — RLS açık, policy yok → yalnız service_role (sunucu) erişir.
alter table gorevler enable row level security;

-- Doğrulama:
-- select table_name from information_schema.tables where table_name = 'gorevler';
-- Beklenen: 1 satır.
-- select count(*) from gorevler;  -- Beklenen (taşıma yok): 0.
