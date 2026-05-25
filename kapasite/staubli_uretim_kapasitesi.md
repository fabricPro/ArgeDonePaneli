# Stäubli Üretim Kapasitesi — Mobidik İşletmesi

> Bu dosya `staubli_feasibility` puanlamasının kaynak referansıdır. 
> Buradaki her parametre Mobidik'in BUGÜNKÜ gerçek üretim 
> kapasitesini yansıtır — teorik "armür makinesinde yapılabilir 
> mi" değil, "bu işletmede yapılabilir mi" sorusuna cevap verir.
> 
> Güncelleme: Yeni aparat alındığında, yeni iplik kategorisi 
> denendiğinde, yeni sertifika alındığında, kapasite genişlediğinde 
> buraya yansıtılır. Versiyon artırılır.
> 
> Versiyon: 1.0
> Son güncelleme: 2026-05-13
> Kaynak: Kullanıcı doğrulaması (Mobidik, ARGE)

## 1. Tezgah Bilgileri

| Parametre | Değer | Durum |
|---|---|---|
| Marka | Stäubli | KESİN |
| Tezgah tipi | Armür/dobby | KESİN |
| Tezgah sayısı | 21-22 | TAHMİNİ (kesin sayım gerekli) |
| Maksimum bitmiş ürün eni | 360 cm | DOĞRULANDI (kullanıcı) |

## 2. Dokuma Yapıları

| Yapı | Kapasite | Notlar |
|---|---|---|
| Armür/dobby | TAM | Stäubli ana fonksiyon |
| Leno (giz) | TAM | Aparat var + aktif üretim var |
| Çift atkı | TAM | Doğrulandı |
| Çift çözgü | TAM | Doğrulandı |
| Jakar | YOK | Stäubli armür, jakar tezgahı değil |

## 3. İplik Kapasitesi

| İplik kategorisi | Kapasite | Notlar |
|---|---|---|
| Pamuk, keten, viskon, polyester (standart) | TAM | |
| Yün | TAM | Yün dokuma deneyimi mevcut |
| FR iplik (genel kategori) | TAM | FR iplikle çalışma deneyimi mevcut |
| Trevira CS (FR polyester, spesifik) | TEDARİK GEREKLİ | Spesifik olarak elde yok, ama piyasada bulunabilir, dokuma deneyimi FR kategorisinde mevcut |
| Outdoor / UV dayanımlı iplik | BELİRSİZ | Doğrulanmadı |
| Metallic iplik (lurex, foil, metal kaplama) | YOK | Yetkinlik yok (kullanıcı doğruladı) |

## 4. Sertifikasyon Kapasitesi

| Sertifika | Durum | Notlar |
|---|---|---|
| OEKO-TEX Standard 100 | VAR | Doğrulandı (kullanıcı) |
| ISO 9001 | VAR | Doğrulandı (kullanıcı) |
| ISO 14001 | VAR | Doğrulandı (kullanıcı) |
| FR son ürün sertifikası (M1, B1, BS 5852, NFPA 701, IMO MED) | BELİRSİZ | İplik FR olsa bile son ürün sertifikası ayrı süreç — doğrulanmadı |
| GRS (Global Recycled Standard) | BELİRSİZ | Doğrulanmadı |
| EU Ecolabel | BELİRSİZ | Doğrulanmadı |
| Cradle to Cradle (C2C) | BELİRSİZ | Doğrulanmadı |

## 5. staubli_feasibility Puanlama Kuralları

Bir rakip ürün incelenirken aşağıdaki tablo uygulanır:

### En (genişlik) kontrolü

| Bitmiş ürün eni | Etki |
|---|---|
| ≤ 360 cm | En parametresi feasibility'yi düşürmez |
| > 360 cm | Feasibility 0-2/5 (fiziksel sınır aşılıyor); strategic_note: "Bitmiş ürün eni Mobidik'in 360 cm sınırını aşıyor" |

### Dokuma yapısı kontrolü

| Yapı | Etki |
|---|---|
| Armür/dobby, leno, çift atkı, çift çözgü | TAM (feasibility yüksek) |
| Jakar | Feasibility 0-1/5 (Stäubli armür, jakar değil) |
| Egzotik/karma yapı | Feasibility 2-3/5, strategic_note ile detaylandır |

### İplik kontrolü

| İplik kategorisi | Etki |
|---|---|
| Standart (pamuk, keten, viskon, polyester) | TAM |
| Yün, FR genel, çift bileşen | TAM |
| Trevira CS spesifik | TAM ama strategic_note: "Trevira CS tedariki gerekli" |
| Outdoor/UV iplik | Feasibility 3/5, strategic_note: "Outdoor iplik tedarik kapasitesi doğrulanmadı" |
| Metallic / lurex | Feasibility max 2/5; strategic_note: "Metallic iplik yetkinliği yok, geliştirme gerekli" |

### Sertifika kontrolü (son ürün için gereken)

| Sertifika gerektiriyorsa | Etki |
|---|---|
| OEKO-TEX, ISO 9001, ISO 14001 | TAM (mevcut) |
| FR son ürün sertifikası gerekli | Feasibility tam, ama strategic_note: "FR son ürün sertifikası süreci gerekli (iplik FR olsa bile)" |
| GRS, EU Ecolabel, C2C | Strategic_note: "Sertifika süreci başlatılmamış, geliştirme gerekli" |

### Birden fazla eksik parametre varsa

Her eksik parametre feasibility puanını ayrı düşürür; en katı parametre kazanır (örnek: metallic gereken + jakar yapı → feasibility max 1/5).

## 6. Geliştirme Yol Haritası (TODO)

- [ ] Tezgah sayısı kesin sayımla doğrula (21 mi 22 mi)
- [ ] Outdoor / UV iplik tedarik kapasitesi netleştir
- [ ] FR son ürün sertifika süreci başlatma kararı
- [ ] GRS sertifikası: geri dönüştürülmüş iplik tedariki + sertifika
- [ ] EU Ecolabel başvuru süreci
- [ ] C2C başvuru süreci (sürdürülebilirlik için niş)
- [ ] Trevira CS numune tedariki ve doku denemesi
- [ ] Metallic iplik denemesi (lurex tedariki, statik elektrik testi) — uzun vadeli
