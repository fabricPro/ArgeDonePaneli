# ARGE Perdelik Pazar Araştırması

**Sahibi:** Mobidik ARGE
**Makine parkı:** Stäubli armür
**Hedef pazar:** Türkiye iç pazar + ihracat
**Başlangıç tarihi:** 2026-05-11

## Klasör Yapısı

| Klasör | İçerik |
|---|---|
| `01_raporlar/` | Markdown formatında parti raporları. Her parti `<marka>_parti<NN>_<tarih>.md` adıyla. Ayrıca `_karsilastirma_<tarih>.md` ve `_arge_firsat_haritasi.md` özetleri. |
| `02_gorseller/` | Marka klasörleri altında ürün görselleri. Dosya adı: `<urun_kodu>_<sira>.jpg` |
| `03_html_dashboard/` | `index.html` — tüm ürünleri grid kart görünümünde, marka / kompozisyon / en filtreli galeri. Detay modal'ı ile. |
| `04_kaynak_linkler/` | Her parti için yapıştırılan ham link listeleri (txt). Hangi linkin hangi tarihte işlendiğini takip etmek için. |

## Akış

1. Kullanıcı `04_kaynak_linkler/<marka>_parti<NN>.txt` içine link listesi yapıştırır.
2. Claude her linki gezer; ürün başına şu alanları çıkarır:
   - Marka, koleksiyon, ürün kodu, ürün adı
   - Kompozisyon, en, gramaj, rapor ölçüsü
   - Dokuma yapısı (plain / dobby / jacquard / sheer / leno)
   - Renk varyantları, performans özellikleri (FR, blackout vb.)
   - Ürün açıklaması ve stil notu
3. Her ürünün 3–6 ana görseli `02_gorseller/<marka>/` altına indirilir.
4. `01_raporlar/` içine markdown rapor yazılır — her ürün için tablo + görseller + **Mobidik Notu** (Stäubli armür yapılabilirlik yorumu). Sonunda karşılaştırma ve ARGE fırsat haritası.
5. `03_html_dashboard/index.html` güncellenir; yeni ürünler galerinin sonuna eklenir, filtreler ve detay modal'ı çalışır halde.

## Üretim Ülkesi Atama Kuralı

Bir ürün sayfasında üretim/dokuma yeri açıkça belirtilmediyse, **verinin çekildiği firmanın merkez ülkesi** baz alınır. Açık beyan varsa (örn. "Belgian Linen", "Made in Italy" sertifikası) o ülke kullanılır.

| Marka | Merkez | Varsayılan ülke | Not |
|---|---|---|---|
| Zimmer + Rohde | Oberursel/Frankfurt, DE | Almanya | Melange Linen → Belçika (Belgian Linen sertifikası) |
| ADO Goldkante | Aschendorf, DE (Z+R alt markası) | Almanya | — |
| Etamine | Paris/Lyon, FR (Z+R Fransız alt markası) | Fransa | Andria & Blanc de Lin RE → İtalya (explicit beyan) |
| Travers | New York, US (Z+R Group) | ABD | Tasarım ABD, üretim genelde Avrupa |
| Kvadrat | Ebeltoft, DK | Danimarka | **Air Line 5539 → Türkiye** (Kvadrat sayfa açıkça beyan ediyor — Mobidik için kritik benchmark) |

## Mobidik Notu nedir?

Her ürün için Stäubli armür makinesi ile yapılabilirlik değerlendirmesi:
- Çerçeve sayısı tahmini
- Rapor genişliği uygunluğu
- Atkı/çözgü kombinasyon zorluğu
- Tahmini maliyet/zorluk seviyesi (kolay / orta / zor / atölye dışı)
- Türk pazarı + ihracat için önerilen pozisyon

## Mevcut Durum (son güncelleme: 2026-05-25)

| Marka | Parti | Ürün | Renk varyantı | Görsel | Durum |
|---|---|---|---|---|---|
| Zimmer + Rohde | 01 + 02 | 5 + 5 | ~40 | ~100 | ✅ tam |
| ADO Goldkante | 01 + 02 (Z+R partileri içinde) | 5 + 5 | ~30 | ~90 | ✅ tam |
| Etamine | 02 | 4 | ~12 | ~50 | ✅ tam |
| Travers | 03 | 6 | ~17 | 18 | ⚠️ görseller var, rapor eksik |
| Kvadrat | 01 | 2 (Air Line 5539, Alpaca Leno 5544) | 5 + 4 = 9 | 5 (Air Line) + 4 (Alpaca Leno placeholder) | Air Line ✅ / Alpaca Leno ⚠️ görsel beklemede |

**Konsolide:** 23 ürün, 5 marka, **7 ülke** (DE / BE / IT / FR / US / **TR** / DK kaynaklı), 113 renk varyantı, ~400 görsel referansı.

Aktif şablon onaylandı; bu noktadan sonra yeni marka eklemeleri aşağıdaki akışla yapılacak.

## Yeni Marka Ekleme Akışı (Kvadrat tecrübesinden)

Yeni bir markaya başlarken sırasıyla:

1. **Sayfayı çek** (`web_fetch`). Statik HTML metni varsa kompozisyon / dokuma / renk / üretim ülkesi / sertifika alanlarını oradan al. JS-render varsa Chrome ile sayfa içeriği ve görsel URL'leri çıkarılmalı.
2. **Görsel kaynağını sınıflandır:**
   - **Direkt CDN URL pattern** (Z+R / ADO / Etamine / Travers): `fileadmin/_processed_/X/Y/csm_<urun_kodu>_<sira>.jpg` — `02_gorseller/indir.ps1` döngüsüne ekle.
   - **Toplu ZIP arşiv endpoint** (Kvadrat): `kvadrat-downloadcenter.azurewebsites.net/api/downloadcenter/downloadimages/<id>?culture=en&lowResolution=true` — markaya özel `indir_<marka>.ps1` script'i + Expand-Archive.
   - **Bireysel sayfa scraping** (yeni marka): Chrome MCP ile DOM'dan görsel URL listele.
3. **Klasör + script:** `02_gorseller/<marka>/` aç. ASCII-only PowerShell script yaz (aşağıdaki konvansiyon). Dosya adlandırma: `<urun_kodu><renk_kodu>_<sira>.jpg`.
4. **Markdown rapor:** `01_raporlar/<marka>_parti<NN>_<tarih>.md`. Her ürün için: tablo + görsel referansları + Mobidik Notu + karşılaştırma + ARGE fırsat haritası güncellemesi.
5. **Dashboard güncellemesi:** `03_html_dashboard/index.html` içindeki `const products = [...]` dizisinin sonuna yeni obje. Brace dengesi ve JSON parse kontrolü (Node.js ile).
6. **Link dosyası:** `04_kaynak_linkler/<marka>_parti<NN>.txt` — işlenen + kuyrukta + indirme endpoint linkleri.
7. **Doğrulama:** JSON parse, görsel path tutarlılığı (rapor MD ↔ dashboard ↔ disk), PowerShell brace dengesi, non-ASCII karakter kontrolü.

## Görsel İndirme Stratejisi

Marka tipine göre indirme yöntemi:

| Marka tipi | Pattern | Yöntem |
|---|---|---|
| **Z+R Group** (Z+R, ADO Goldkante, Etamine, Travers) | Direkt CDN URL: `csm_<kod>_<sira>.jpg` | `02_gorseller/indir.ps1` içine satır ekle, döngüde Invoke-WebRequest |
| **Kvadrat** | Tek ZIP arşivi (designer downloadcenter API) | Markaya özel script (`indir_<marka>.ps1`) + Expand-Archive |
| **Yeni marka** | Bilinmiyor | Önce sayfayı incele; statik HTML ise CDN URL yakala, JS-render ise Chrome MCP ile DOM'dan çıkar |

**Kvadrat özel notu:** Kvadrat sadece **20×20 cm swatch** görsel veriyor — lifestyle/oda fotoğrafı yok. Bu yüzden dashboard'da renk başına 1 görsel (Z+R'de ortalama 3 görsel). Dashboard JSON'unda `gorseller` array'i marka koşuluna göre ayarlanır.

## PowerShell Script Konvansiyonu

Windows PowerShell `.ps1` dosyalarını Windows-1252 olarak okur (UTF-8 BOM yoksa). Bu yüzden Türkçe karakter ve tip-grafik apostrof (`'`) string terminator gibi yorumlanabilir → parse hatası.

**Kurallar:**

- **Sadece ASCII karakter** kullan (Türkçe yorum/mesaj yok, em-dash `—` yerine hyphen `-`)
- **Apostrof içeren string yok** — `"Claude'a"` gibi ifadeler Windows-1252'de `'` ile string açıyor sanılır → `"Claude"` veya `("Claude" + "a")` kullan
- **try / catch** blokları aynı satırda kapat: `} catch {` formatı
- **Brace dengesi kontrolü:** her `.ps1` için açılan `{` = kapanan `}` (regex `\d{4}` de `{` `}` içerir, awk ile sayarken false-positive)
- **Dosyaları test et:** kayıt sonrası `awk 'BEGIN{o=0;c=0} { o+=gsub(/\{/, "{"); c+=gsub(/\}/, "}") } END{print o, c}'` ile brace farkı
- Marka-özel script'ler `02_gorseller/<marka>/indir_<marka>.ps1` altında; ortak (Z+R Group) için kök seviyesinde `02_gorseller/indir.ps1`

## Dashboard JSON Şeması

`03_html_dashboard/index.html` içindeki `const products = [...]` dizisine yeni ürün eklenirken bu şema:

```javascript
{
  "marka": "<marka adı>",
  "koleksiyon": "<koleksiyon>",
  "urun_kodu": "<ana ürün kodu — renk varyantı dahil>",  // örn: "5539-0101"
  "urun_adi": "<ürün adı>",
  "ulke": "<üretim ülkesi>",  // tablo kuralı ile
  "kompozisyon": "<%X Lif1, %Y Lif2>",
  "en": "<cm — yoksa 'üretici beyan etmiyor'>",
  "gramaj": "<g/m² — yoksa 'üretici beyan etmiyor'>",
  "rapor": "<rapor ölçüsü veya 'yok / strüktürel'>",
  "dokuma": "<plain / dobby / jacquard / sheer / leno / boucle / vs.>",
  "renkler": [
    {
      "kod": "<renk kodu>",
      "ad": "<renk adı>",
      "swatch": "<swatch URL veya boş>",
      "gorseller": ["../02_gorseller/<marka>/<urun_kodu><renk_kodu>_<sira>.jpg", ...]
    }
  ],
  "performans": ["FR", "Blackout", "Yıkanabilir 30°", ...],
  "aciklama": "<stil/teknik açıklama>",
  "stil_notu": "<pazarlama/koleksiyon notu>",
  "url": "<kaynak URL>",
  "mobidik_notu": "<b>Zorluk: ...</b> Çerçeve: ... Üretim önerisi: ..."  // HTML markup destekli
}
```

**Doğrulama:** Ekleme sonrası şu komut hatasız dönmeli:

```bash
node -e "const m = require('fs').readFileSync('index.html','utf8').match(/const products = (\[[\s\S]*?\n\]);/); JSON.parse(m[1])"
```

## Renk Kodu Eşleştirme Stratejisi

Yeni markada gerçek renk kodları henüz bilinmiyorsa:

1. Placeholder kodlarla (0001-0005 vb.) dashboard objesi oluştur
2. PowerShell script ile ZIP indir + dosya adlarından gerçek kodları çıkar
3. Script gerçek kodları rapor eder; rapor + dashboard'da güncelle
4. Bir kerelik `rename_<marka>.ps1` yazıp placeholder dosyaları gerçek isimlere taşı

**Kvadrat örneği:** Tahmin: 0001-0005. Gerçek: 0101 / 0111 / 0161 / 0331 / 0941 (Kvadrat'ın color code şemasında 01xx = ışıkları/nötrler, 03xx = orta tonlar, 09xx = derin yeşiller).
test
