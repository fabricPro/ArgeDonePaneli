-- Mobidik Kumas Paneli — Sema v3.3 migration
-- Supabase Dashboard -> SQL Editor -> bu dosyayi yapistir -> Run.
-- Idempotent: tekrar calistirilirsa hata vermez.

-- 1) products tablosuna yeni kolonlar
alter table products
    add column if not exists weight_gsm        integer,
    add column if not exists dashboard_order   integer;

-- 2) app_state tablosu — kullanici tercihleri (orn. country_order)
create table if not exists app_state (
    key        text primary key,
    value      jsonb not null,
    updated_at timestamptz default now()
);
alter table app_state enable row level security;

-- Not: images jsonb icindeki is_pinned alani sema disi; uygulama kodu yonetir.
