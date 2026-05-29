# Bulut Kurulum — Supabase + Render

Hedef: panel her yerden (mobil dahil) 7/24 erişilir; veri Supabase Postgres'te,
görseller Supabase Storage'da, uygulama Render'da; şifreyle giriş.

---

## 1. Supabase projesi (~5 dk)
1. https://supabase.com → **Sign up** (GitHub/Google ile hızlı).
2. **New project** → Name: `mobidik-kumas`, bir **Database Password** belirle (kaydet),
   Region: **Central EU (Frankfurt)** (Türkiye'ye yakın). **Create**.
3. ~2 dk sonra: sol altta **Project Settings (dişli) → API**:
   - **Project URL**'i kopyala.
   - **Project API keys → `service_role` → Reveal → kopyala** (⚠️ GİZLİ anahtar).

## 2. Veritabanı şeması (~1 dk)
1. Sol menü **SQL Editor → New query**.
2. `scripts/supabase_schema.sql` dosyasının içeriğini yapıştır → **Run**.
   "Success" → `products` tablosu oluştu (RLS açık).

## 3. `.env` + veriyi taşı (yerelde, bir kez)
1. Proje kökünde `.env.example`'ı `.env` adıyla kopyala.
2. Doldur:
   - `SUPABASE_URL` = (1. adım)
   - `SUPABASE_SERVICE_KEY` = (1. adım, service_role)
   - `APP_PASSWORD` = panele girişte kullanacağın şifre
   - `SECRET_KEY` = rastgele uzun bir dize (örn. 40+ karakter)
3. Terminalde taşımayı çalıştır:
   ```
   .venv\Scripts\python.exe scripts\upload_to_supabase.py
   ```
   27 ürün + ~400 görsel yüklenir (birkaç dk). Sonunda "TAMAM ... Supabase" görmelisin.
   `gorseller` bucket'ı otomatik oluşturulur.
4. (İsteğe bağlı yerel test) `.venv\Scripts\python.exe web\app.py` → http://localhost:5000
   → şifreyle gir → ürünler artık Supabase'den geliyor.

## 4. Kodu GitHub'a it
Render, repo'dan otomatik deploy eder.
1. GitHub'da boş bir **private** repo aç.
2. ```
   git add -A
   git commit -m "Bulut: Supabase + Render"
   git remote add origin <repo-url>
   git push -u origin HEAD
   ```
   `.env` git'e **girmez** (gitignore'da) — gizli anahtarlar güvende.

## 5. Render deploy (~5 dk)
1. https://render.com → **Sign up** (GitHub ile).
2. **New + → Blueprint** → repo'yu seç (`render.yaml` otomatik okunur) → **Apply**.
   (Alternatif: New + → Web Service → repo seç; Python otomatik algılanır.)
3. **Environment** sekmesinde şu üç değeri gir (SECRET_KEY otomatik üretilir):
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `APP_PASSWORD`
4. Deploy bitince Render bir adres verir: `https://mobidik-kumas.onrender.com`

## 6. Test (mobil dahil)
- Telefon/bilgisayar tarayıcısında bu adresi aç → şifre → galeri.
- Yeni ürün ekle (telefondan kamerayla foto çek), kapak seç, görselleri sırala → her cihazda güncel.
- ⚠️ Ücretsiz Render servisi 15 dk hareketsizlikte uyur; ilk açılış ~30-60 sn sürebilir, sonra hızlanır.
- ⚠️ Ücretsiz Supabase projesi 7 gün hiç kullanılmazsa duraklar; panelde Supabase Dashboard'dan "Resume" yeter.

## Güvenlik
- `service_role` anahtarı yalnızca `.env` (yerel) + Render env'de durur; git'e/kimseye verme.
- Görsel bucket'ı herkese-açık-okuma (hızlı CDN). Ürün verisi (notlar/ARGE) RLS + panel şifresiyle korunur.
- Şifreni değiştirmek: Render → Environment → `APP_PASSWORD` güncelle.
