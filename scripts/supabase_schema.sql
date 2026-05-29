-- Mobidik Kumas Paneli — Supabase semasi
-- Supabase Dashboard -> SQL Editor -> bu dosyayi yapistir -> Run

create table if not exists products (
  urun_id              text primary key,
  brand                text,
  brand_slug           text,
  country              text,
  collection           text,
  product_name         text,
  product_code         text,
  composition          text,
  width_cm             integer,
  weave_type           text,
  repeat_vertical_cm   numeric,
  repeat_horizontal_cm numeric,
  arge_notu            text,
  notes                text,
  source_url           text,
  images               jsonb not null default '[]'::jsonb,
  created_at           timestamptz default now(),
  updated_at           timestamptz default now()
);

-- Guvenlik: RLS acik + policy yok => tabloya sadece service_role (sunucu) erisir.
-- (Uygulama service_role anahtariyla baglanir; RLS'i bypass eder. anon/public okuyamaz.)
alter table products enable row level security;

-- Not: 'gorseller' Storage bucket'i tasima scripti (upload_to_supabase.py)
-- tarafindan otomatik olusturulur (herkese acik okuma). Elle de olusturabilirsin:
-- Storage -> New bucket -> ad: gorseller, Public: ON
