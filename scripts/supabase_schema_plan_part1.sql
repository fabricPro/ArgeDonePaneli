-- tasarim-v2 Plan Parça 1 — products tablosuna plan (jsonb) kolonu
-- ===================================================================
-- Çalıştırma: Supabase Dashboard → SQL Editor → bu dosyayı yapıştır → Run
-- Idempotent: tekrar çalıştırmak güvenli.
--
-- Amaç: Ürün planlama (Plan alt-sekmesi) verisi. SÜRÜM-BAZLI tutulur:
-- her teknik sürümün (teknik.surumler[i].id) kendi planı, surum_id ile anahtarlı.
--   plan = {
--     "<surum_id>": {
--       "surum_id", "boya_yontemi": {cozgu, atki},
--       "cozgu_plani": {}, "atki_varyant_plani": {}, "top_boya_plani": {},
--       "kur_snapshot": {usd_try, eur_try, fetched_at},
--       "rapor_para_birimi", "guncelleme_tarihi"
--     }, ...
--   }
-- Parça 1: sadece boya_yontemi + kur_snapshot + rapor_para_birimi dolar;
-- cozgu_plani / atki_varyant_plani / top_boya_plani Parça 2-4'te kullanılacak (şimdilik {}).

alter table products
  add column if not exists plan jsonb default '{}'::jsonb;

-- Doğrulama:
-- select column_name, data_type from information_schema.columns
-- where table_name = 'products' and column_name = 'plan';
-- Beklenen: 1 satır, data_type = jsonb
