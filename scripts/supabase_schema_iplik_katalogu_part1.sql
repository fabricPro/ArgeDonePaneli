-- İplik Kataloğu — Parça 1 şeması (idempotent)
-- Tablo: iplik_kartelalari. Storage bucket "kartelalar" runtime'da ensure_bucket_kartelalar() ile oluşur.
-- Tekrar tekrar çalıştırılabilir (CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).

create table if not exists iplik_kartelalari (
    kartela_id        text primary key,
    ad                text not null,
    tedarikci         text,
    iplik_tipi        text,              -- PES/CO/VIS/PA/WO/AC/PAN/LI/MET/diğer (serbest)
    iplik_numarasi    text,
    kompozisyon       text,
    fiyat_tutar       numeric,
    fiyat_birim       text,              -- TL/EUR/USD
    fiyat_per         text,              -- kg/lb
    moq_kg            numeric,
    moq_notu          text,
    sayfalar          jsonb default '[]'::jsonb,   -- Parça 2 dolduracak (sayfa fotoğrafı + renkler)
    olusturma_tarihi  timestamptz default now(),
    guncelleme_tarihi timestamptz default now()
);

-- Tablo önceden (eksik kolonla) varsa diye idempotent kolon ekleri
alter table iplik_kartelalari add column if not exists tedarikci         text;
alter table iplik_kartelalari add column if not exists iplik_tipi        text;
alter table iplik_kartelalari add column if not exists iplik_numarasi    text;
alter table iplik_kartelalari add column if not exists kompozisyon       text;
alter table iplik_kartelalari add column if not exists fiyat_tutar       numeric;
alter table iplik_kartelalari add column if not exists fiyat_birim       text;
alter table iplik_kartelalari add column if not exists fiyat_per         text;
alter table iplik_kartelalari add column if not exists moq_kg            numeric;
alter table iplik_kartelalari add column if not exists moq_notu          text;
alter table iplik_kartelalari add column if not exists sayfalar          jsonb default '[]'::jsonb;
alter table iplik_kartelalari add column if not exists olusturma_tarihi  timestamptz default now();
alter table iplik_kartelalari add column if not exists guncelleme_tarihi timestamptz default now();
