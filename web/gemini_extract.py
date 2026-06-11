"""v4.0-part-2 Sprint 11 — Gemini destekli "Linkten Doldur" özelliği.

Bir kumaş ürün linkinden form alanlarına ÖNERİ üretir.
ANAYASA (CLAUDE.md kural #2/#3/#8): SADECE sayfada açıkça yazan bilgileri
çıkarır. Tahmin YASAK. Her alan için sayfadan alıntı (evidence) zorunlu.

Akış:
  fetch_clean_content(url) → temizlenmiş metin + meta + JSON-LD
  extract_fabric_fields(content) → Gemini'ye yolla → JSON öneri çıktısı

Form'a HİÇBİR ŞEY otomatik yazılmaz. UI tarafı önerileri gösterir, kullanıcı
tek tek veya toplu "Kabul" ile form'a basar.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Any

import requests
from bs4 import BeautifulSoup

import store  # P5 — taksonomi vocab tek kaynak (VALID_*) + validate_* (döngü yok: store gx import etmez)
# v4.0-part-2 Adım 8 — Birim/kısaltma normalize (paylaşılan modül)
from normalize import parse_width_cm, parse_weight_gsm, normalize_composition

# Gemini SDK opsiyonel — yoksa hatayı runtime'da göster, import zamanında crash etme
try:
    import google.generativeai as genai
    _SDK_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    _SDK_AVAILABLE = False


# ============================================================
# Yapılandırma
# ============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
# Not: 2026 itibarıyla gemini-1.5 deprecate; gemini-2.0-flash bu projenin
# free-tier'ında limit=0. 2.5-flash hem hızlı hem JSON mode destekli.
# Override için .env'e GEMINI_MODEL=... yaz.

FETCH_TIMEOUT = 10.0          # sn
FETCH_MAX_BYTES = 2_000_000   # 2 MB üst sınır (büyük sayfa savunması)
# P4a-2: 8000 -> 16000. Gürültü (nav/menü/footer) temizlendi + flash token başlığı
# yüksek; kırpma sınırına daha çok GERÇEK ürün metni sığsın diye yükseltildi.
TEXT_TRUNCATE = 16000         # Gemini'ye gönderilecek max düz metin
JSON_LD_TRUNCATE = 3000       # JSON-LD bloku max char
SCRIPT_JSON_TRUNCATE = 4000   # P4a-2: __NEXT_DATA__/application-json (JS-render kurtarma) max char

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 "
    "(MobidikARGE/1.0; +panel-prefill)"
)


# ============================================================
# Anayasa sistem promptu — Gemini'ye verilen kurallar
# ============================================================

SYSTEM_PROMPT = """Sen bir kumaş kataloğu okuma asistanısın. Görevin: kullanıcının verdiği WEB SAYFASI içeriğinden, SADECE AÇIKÇA YAZAN bilgileri çıkarıp Türkçe form alanlarına eşlemek.

KESİN KURALLAR (uyulmazsa cevabın geçersizdir):

1) ASLA TAHMİN YAPMA. Sayfada açıkça yazmıyorsa o alanı null bırak. "Genelde böyledir", "muhtemelen", "olabilir", "tipik olarak" gibi kalıpları KULLANMA. Bir bilgiyi inferans ile türetme — sadece sayfada birebir geçenleri al.

2) HER doldurduğun alan için "evidence" alanında SAYFADAN ALINTILANAN MIN 5, MAX 200 KARAKTER metin parçası ver. Bu alıntı sayfada gerçekten var olmalı; uydurma. Alıntı yapamıyorsan değeri null'a düşür.

3) Veriyi DEĞİŞTİRMEDEN çevir. Örnekler:
   - "100% Trevira CS" → composition.value: "%100 Trevira CS" (sayı + marka adı korunur)
   - "70% cotton, 30% linen" → composition.value: "%70 Pamuk, %30 Keten"
   - "Width 137 cm" → width_cm.value: 137
   - "Jacquard" → weave_type.value: "jacquard" (lowercase, mevcut listeyi tercih: dobby, jacquard, plain, leno, sheer, bouclé, saten, twill)
   - Renk varyantı, ürün kodu, SKU, marka adı: olduğu gibi bırak (çevirme)
   - Koleksiyon adı: orijinal dilinde bırak ("Cobra Collection" → "Cobra Collection")
   - KOMPOZİSYON KISALTMASI (ISO 1419): sayfa "%50 PES, %50 CO" gibi kısaltma kullanıyorsa
     Türkçe tam ad ver: "%50 Polyester, %50 Pamuk". Bilinen kısaltmalar:
       PES/PL/PET = Polyester, CO = Pamuk, VI/CV/VIS = Viskon, PA = Poliamid,
       WO = Yün, LI/FL = Keten, AC/PAN = Akrilik, EA/EL/SP = Elastan,
       SI/SE = İpek, KA/WS = Kaşmir, CMD/MD = Modal, TEN = Tencel, LY = Liyosel,
       CA = Asetat, RAM = Rami, JU = Jüt, HE = Kenevir, BA = Bambu, MO = Tiftik (Mohair).
     "Recycled X" / "rX" / "GRS X" → "Geri Dönüştürülmüş X" (örn. rPES → Geri Dönüştürülmüş Polyester).
     Tanımadığın kısaltmayı OLDUĞU GİBİ bırak (Python tarafı güvenlik ağı çevirir).

4) SAYISAL ALANLAR (width_cm, weight_gsm, repeat_*):
   - "Width: 137 cm" → 137 (integer)
   - "300-310 cm" gibi range → null (belirsizlik), evidence: "300-310 cm"
   - "g/m²" yoksa weight_gsm null
   - Sayı kesirli (137.5) ise integer'a yuvarlama YAPMA — null bırak ve evidence ver, kullanıcı karar versin
   - color_count (renk/varyant sayısı): "Available in N colours" / "N renk" / "N colourways" gibi AÇIK ifade ya da sayfada AÇIKÇA sayılabilir swatch/renk listesi → N (integer). Aralık ("5-7 renk") veya belirsizlik → null. TAHMİN YASAK (anayasa #3); evidence o ifadeyi içersin.
   - YABANCI BİRİM (inch, oz/yd², mm, m, kg/m²): sayfada YAZAN birimi STRING olarak ver,
     dönüştürme. Örnek: value="60 inch" / value="8 oz/yd²" / value="1.5 m" / value="0.18 kg/m²".
     Python tarafı dönüştürür (1 inch=2.54 cm, 1 oz/yd²=33.906 g/m², 1 kg=1000 g, vb.).
     "g/m²" / "gsm" / "cm" zaten Türkçe sistem birimi → integer ver (eski davranış).

5) ANAYASA KURAL #3 — bu alanlar AŞIRI HASSAS:
   - brand: Sayfanın header / meta etiketi (og:site_name, application_name) / footer / page title / breadcrumb içinde AÇIKÇA YAZAN marka adını al. Domain (örn. "kvadrat.dk") TEK BAŞINA evidence olarak yetmez — sayfa metninde mutlaka geçmeli; geçtiği yeri evidence'a yaz.
       * Multi-brand reseller (etoffe.com, romo.com vb.): ürün-spesifik marka açıkça yazıyorsa ("by Coordonné", "Coordonné collection") onu al; aksi halde NULL.
       * Tasarımcı/kolaboratör (Patricia Urquiola, Marc Newson) MARKA DEĞİL — onlar arge_notu_taslak'a girer.
       * Marka adı orijinal yazımıyla kalır (çevirme): "Coordonné", "Création Baumann", "Dedar", "Kvadrat".
       * Birden fazla aday varsa (örn. reseller sitede hem "Etoffe" hem "Coordonné") ürünü ÜRETEN/TASARLAYAN markayı tercih et.
   - composition: tam alıntı yapamıyorsan NULL. "Mostly natural fibers" gibi belirsiz ifadeler NULL.
   - production_country: SAYFA "Made in Italy" gibi üretim yeri belirtiyorsa "İtalya". Marka HQ (firma merkezi) ile KARIŞTIRMA. Belirtmiyorsa NULL.
   - brand_country: markanın MERKEZ/HQ ülkesi. Sayfada yazmasa BİLE markayı tanıyorsan GENEL/DÜNYA BİLGİNDEN Türkçe ülke adı ver (ör. Kvadrat→Danimarka, Dedar/Rubelli→İtalya, JAB ANSTOETZ/Carlucci/Zimmer + Rohde→Almanya, Création Baumann→İsviçre, Sahco→İsveç). Bu bir ÇIKARIMDIR — sayfa kanıtı ŞART DEĞİL; evidence'a bilgi kaynağını yaz (ör. "marka bilgisi"). production_country (Made in) ile KARIŞTIRMA — bunlar farklı olabilir. Markayı GERÇEKTEN tanımıyorsan NULL (uydurma).
   - HİÇBİR şartla sertifika/FR/MOQ/teslim alanı doldurma — bunlar bu çıktıda zaten yok, ama metinden çıkarıp arge_notu_taslak'a da SIZDIRMA.

6) REFERANS FİYAT (reference_price) — bu alan ÖZELDİR:
   - Sayfada açıkça yazan fiyatı al; YOKSA NULL.
   - Para birimi MUTLAKA olmalı (€, $, £, EUR, USD, GBP gibi). Para birimi yoksa NULL.
   - value: normalize edilmiş kısa biçim. Örnekler:
       * "€42.00 / meter"          → value: "42 EUR/m"
       * "Configure from 140,74 €" → value: "140,74 EUR"
       * "$85 per yard"            → value: "85 USD/yard"
       * "Price: 38,50 €/m"        → value: "38,50 EUR/m"
   - type alanı ZORUNLU:
       * "exact" → sayfada kesin/sabit fiyat ("€42.00 / meter", "Price: 38,50 €")
       * "from"  → başlangıç/taban fiyatı ("Configure from 140,74 €", "from €X",
                   "starting at", "ab €X", "à partir de", "desde €X")
   - evidence: fiyatın geçtiği TAM ifadeyi içermeli (sadece rakam değil — bağlamla).
       * Doğru: "Configure from 140,74 €"
       * Yanlış (eksik bağlam): "140,74 €"
   - YASAK ifadeler → NULL:
       * "Price on request", "Contact for price", "POA" → NULL
       * Çıplak sayı, para birimi olmadan → NULL
       * "premium markadır ~X olur" gibi tahmin → NULL (anayasa #3)
   - Kategori/galeri sayfasındaki "from €Y" varyant-aralık fiyatları:
     ürün spesifik bir fiyatsa "from" alabilirsin; tüm bir koleksiyonun fiyat aralığıysa NULL.

7) SAYFA TÜRÜ KONTROLÜ:
   - Sayfa bir kumaş ÜRÜN sayfası değilse (haber, blog, kategori listesi, anasayfa) → tüm alanları null, error: "page_not_product".
   - Sayfa erişilemez veya boş → error: "page_empty".

8) arge_notu_taslak: Sayfanın "About this fabric" / "Description" gibi tanıtım metinlerini SADELEŞTİRMİŞ Türkçe (max 300 karakter) çevir. Pazarlama dili kullanma, sadece teknik özellikleri ve kullanım amacını özetle. Kaynakta açıkça yazanı çevir, ekleme yapma. Sertifika/FR/fiyat/MOQ/teslim bilgilerini buraya SIZDIRMA — bunlar ya kendi alanlarına gider ya null kalır.

9) TAKSONOMİ (taxonomy) — SINIFLANDIRMA ÖNERİSİ (TAHMİN; verbatim kaynak şart değil ama gerekçeli ol):
   - category / pattern / color_family: yalnız USER mesajındaki VALID_* listelerinden BİR değer seç; hiçbiri uymuyorsa "" bırak.
   - weave_tags: VALID_WEAVE_TAGS'ten uygun olan(lar)ı (dizi; yoksa []).
   - style_tags: Kumaşın STİLİNİ tanımlayan SERBEST Türkçe etiketler (vocab YOK) — bunları SEN üret, ÜÇ KAYNAĞI BİRLİKTE harmanla:
       (1) GÖRSEL (sana kumaş görseli verildiyse): doku (düz/dokulu/kabartmalı), yüzey (mat/parlak), şeffaflık (tül/yarı-şeffaf/opak), desen, renk tonu/atmosfer;
       (2) İÇERİK: sayfadaki açıklama/tanıtım metninin anlattığı tarz/kullanım;
       (3) TEKNİK VERİ: kompozisyon, dokuma tipi, kategori.
     3-7 kısa, SOMUT sıfat üret (ör. premium, minimal, dokulu, mat, parlak, şeffaf, doğal-keten, modern, klasik, geometrik, bohem, lüks, sade, rustik, akışkan). Pazarlama klişesi DEĞİL — kumaşı gerçekten tanımlayan stil sıfatları. Görsel YOKSA yalnız içerik+teknikten üret. (dizi; hiçbir şey çıkmıyorsa []).
   - confidence (high|medium|low) + kısa reason (Türkçe). Emin değilsen "" + low. Bu bir TAHMİN — makul sınıflandırma yap, uydurma.

10) GÖRSEL ANALİZİ (image_analysis) — YALNIZ sana bir GÖRSEL verildiyse doldur; görsel YOKSA image_analysis = null:
   - dominant_colors: kumaşın baskın renkleri, hex (#RRGGBB) dizisi.
   - texture: kısa (düz/dokulu/kabartmalı/mat/parlak). transparency: tül | yarı-şeffaf | opak.
   - color_count: görselde sayılabilen renk/varyant sayısı (yalnız sayı). confidence + kısa note (Türkçe).
   - Görseldeki yazı/filigranı veri olarak kullanma; yalnız fiziksel görünümü yorumla.

11) ÇIKTI FORMATI: response_schema'ya UYGUN JSON. Her factual alan ya {value, evidence} (fiyat için {value, type, evidence}) ya null. taxonomy ve image_analysis nesnelerini uygunsa doldur, değilse null. Ek metin/açıklama EKLEME. Tek JSON object döndür."""


# ============================================================
# Gemini JSON response schema
# ============================================================

# Pydantic-eşdeğeri her field için ortak yapı
_FIELD_OBJECT = {
    "type": "object",
    "properties": {
        "value": {
            "type": "string",
            "description": "Çıkarılan değer (sayısal alanlar için string olarak; backend parse eder)",
        },
        "evidence": {
            "type": "string",
            "description": "Sayfadan alıntı (min 5, max 200 karakter)",
        },
    },
    "required": ["value", "evidence"],
}

# v4.0-part-2 Sprint 11.5 — fiyat alanı: ek 'type' (exact/from) enum'u
_PRICE_FIELD_OBJECT = {
    "type": "object",
    "properties": {
        "value": {
            "type": "string",
            "description": "Normalize fiyat ('140,74 EUR', '42 EUR/m')",
        },
        "type": {
            "type": "string",
            "enum": ["exact", "from"],
            "description": "exact = kesin fiyat, from = başlangıç/taban fiyat",
        },
        "evidence": {
            "type": "string",
            "description": "Sayfadan TAM alıntı (sadece rakam değil; bağlamla)",
        },
    },
    "required": ["value", "type", "evidence"],
}

# P5 — güven skoru (her AI çıkarımında; Anayasa: inference'ta confidence zorunlu)
_CONFIDENCE = {"type": "string", "enum": ["high", "medium", "low"]}

# P5 — Taksonomi ÖNERİSİ (INFERENCE; serbest string → backend validate_* ile temizler;
# izinli sözlük USER promptunda listelenir; emin değilse "" bırakabilir).
_TAXONOMY_OBJECT = {
    "type": "object",
    "properties": {
        "category":     {"type": "string", "description": "VALID_CATEGORIES'ten biri ya da ''"},
        "pattern":      {"type": "string", "description": "VALID_PATTERNS'ten biri ya da ''"},
        "weave_tags":   {"type": "array", "items": {"type": "string"}, "description": "VALID_WEAVE_TAGS alt kümesi"},
        "color_family": {"type": "string", "description": "VALID_COLOR_FAMILIES'ten biri ya da ''"},
        "style_tags":   {"type": "array", "items": {"type": "string"}, "description": "Serbest Türkçe stil etiketleri — GÖRSEL (doku/şeffaflık/renk) + İÇERİK + TEKNİK sentezi; 3-7 somut sıfat"},
        "confidence":   _CONFIDENCE,
        "reason":       {"type": "string", "description": "Kısa gerekçe (Türkçe)"},
    },
}

# P5 — Görsel analizi (INFERENCE; yalnız görsel verildiğinde doldurulur).
_IMAGE_ANALYSIS_OBJECT = {
    "type": "object",
    "properties": {
        "dominant_colors": {"type": "array", "items": {"type": "string"}, "description": "Baskın renkler, hex (#RRGGBB)"},
        "texture":         {"type": "string", "description": "Doku/yüzey (kısa: düz, dokulu, kabartmalı, mat, parlak…)"},
        "transparency":    {"type": "string", "description": "tül | yarı-şeffaf | opak"},
        "color_count":     {"type": "string", "description": "Görselde sayılabilen renk/varyant sayısı (yalnız sayı)"},
        "confidence":      _CONFIDENCE,
        "note":            {"type": "string", "description": "Kısa görsel notu (Türkçe)"},
    },
}

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "brand":                 _FIELD_OBJECT,   # v4.0-part-2 Sprint 11.6 — YENİ
        "product_name":          _FIELD_OBJECT,
        "product_code":          _FIELD_OBJECT,
        "collection":            _FIELD_OBJECT,
        "production_country":    _FIELD_OBJECT,   # v4.0-part-2 Sprint 11.5 — 'country' yerine
        "brand_country":         _FIELD_OBJECT,   # P4b — firma/marka HQ ülkesi (production ile KARIŞTIRMA)
        "composition":           _FIELD_OBJECT,
        "width_cm":              _FIELD_OBJECT,
        "weight_gsm":            _FIELD_OBJECT,
        "weave_type":            _FIELD_OBJECT,
        "repeat_vertical_cm":    _FIELD_OBJECT,
        "repeat_horizontal_cm":  _FIELD_OBJECT,
        "color_count":           _FIELD_OBJECT,   # P4b — renk/varyant sayısı (öneri; kullanıcı doğrular)
        "reference_price":       _PRICE_FIELD_OBJECT,  # v4.0-part-2 Sprint 11.5 — YENİ
        "arge_notu_taslak":      _FIELD_OBJECT,
        "taxonomy":              _TAXONOMY_OBJECT,       # P5 — sınıflandırma ÖNERİSİ (inference)
        # Sprint 12.1 — image_analysis KALDIRILDI: enrich salt-metin (görsel analizi ayrı:
        # analyze_fabric_image / _IMAGE_VISION_SCHEMA). Çıktı küçülür, AI doldurma hızlanır.
        "error":                 {"type": "string"},
    },
}


# ============================================================
# 1) HTML çek + temizle
# ============================================================

def fetch_clean_content(url: str) -> dict:
    """Sayfayı çek, anlamlı veri çıkar (Gemini token'ı düşük tutmak için).

    Returns dict:
      {
        "url":              kaynak URL
        "title":            <title> içeriği
        "meta_description": <meta name="description"> content
        "og_description":   <meta property="og:description"> content
        "json_ld":          list of parsed JSON-LD blocks
        "text":             temizlenmiş düz metin (max TEXT_TRUNCATE)
      }

    Raises:
      requests.HTTPError — 4xx/5xx response
      requests.RequestException — network/timeout
    """
    resp = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "tr,en;q=0.8",
        },
        timeout=FETCH_TIMEOUT,
        allow_redirects=True,
    )
    resp.raise_for_status()

    # Boyut sınırlama
    raw = resp.content[:FETCH_MAX_BYTES]
    encoding = resp.encoding or "utf-8"
    try:
        html = raw.decode(encoding, errors="ignore")
    except LookupError:
        html = raw.decode("utf-8", errors="ignore")

    soup = BeautifulSoup(html, "html.parser")

    # 1) Title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # 2) Meta description + og:description
    meta_description = ""
    og_description = ""
    for m in soup.find_all("meta"):
        name = (m.get("name") or "").lower()
        prop = (m.get("property") or "").lower()
        if name == "description":
            meta_description = (m.get("content") or "").strip()
        elif prop == "og:description":
            og_description = (m.get("content") or "").strip()

    # 3) JSON-LD (kumaş sitelerinde sık)
    json_ld_blocks: list[Any] = []
    for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(s.string or "{}")
            json_ld_blocks.append(payload)
        except Exception:
            pass

    # 3b) P4a-2 — JS-render siteleri (Next.js vb.) ürün verisini <script id="__NEXT_DATA__">
    # veya <script type="application/json"> içinde taşır. Decompose ETMEDEN ÖNCE yakala.
    script_json = ""
    _seen = 0
    for s in soup.find_all("script"):
        stype = (s.get("type") or "").lower()
        sid = (s.get("id") or "").lower()
        if stype == "application/json" or sid == "__next_data__":
            blob = (s.string or "").strip()
            if blob:
                script_json += blob + "\n"
                _seen += 1
                if len(script_json) > SCRIPT_JSON_TRUNCATE or _seen >= 5:
                    break
    if len(script_json) > SCRIPT_JSON_TRUNCATE:
        script_json = script_json[:SCRIPT_JSON_TRUNCATE] + " …[truncated]"

    # 4) Gürültü temizliği — P4a-2: script/style + nav/header/footer/form/menü/cookie sil
    for t in soup(["script", "style", "noscript", "iframe", "svg",
                   "nav", "header", "footer", "aside", "form", "button", "select"]):
        t.decompose()
    _noise = re.compile(r"(cookie|consent|gdpr|newsletter|breadcrumb|menu|navbar|sidebar)", re.I)
    for el in soup.find_all(attrs={"class": _noise}):
        el.decompose()
    for el in soup.find_all(attrs={"id": _noise}):
        el.decompose()
    for el in soup.find_all(attrs={"role": "navigation"}):
        el.decompose()

    # 4b) Ana içerik önceliği — main/article/[role=main]/ürün konteyneri; yoksa body fallback
    def _clean_text(node) -> str:
        if not node:
            return ""
        return " ".join(node.get_text(separator=" ", strip=True).split())

    main_node = (soup.find("main") or soup.find(attrs={"role": "main"}) or soup.find("article")
                 or soup.find(attrs={"class": re.compile(r"(product|detail|fabric|article)", re.I)}))
    main_text = _clean_text(main_node)
    body_text = _clean_text(soup.body or soup)
    # Ana içerik ANLAMLI ise (>=300 char) onu kullan; değilse tüm body (fallback garanti)
    text = main_text if len(main_text) >= 300 else body_text

    truncated = False
    if len(text) > TEXT_TRUNCATE:
        text = text[:TEXT_TRUNCATE] + " …[truncated]"
        truncated = True

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "og_description": og_description,
        "json_ld": json_ld_blocks,
        "script_json": script_json,   # P4a-2: JS-render structured data (varsa)
        "text": text,
        "truncated": truncated,
    }


# ============================================================
# 2) Gemini'ye yolla + JSON çıkarımı
# ============================================================

def _build_user_prompt(content: dict) -> str:
    """Gemini'ye verilecek tek mesaj — sayfanın temizlenmiş içeriği."""
    json_ld_str = json.dumps(content.get("json_ld") or [], ensure_ascii=False)
    if len(json_ld_str) > JSON_LD_TRUNCATE:
        json_ld_str = json_ld_str[:JSON_LD_TRUNCATE] + " …[truncated]"

    return f"""TARGET_URL: {content['url']}

PAGE_TITLE: {content.get('title', '')}

META_DESCRIPTION: {content.get('meta_description', '')}

OG_DESCRIPTION: {content.get('og_description', '')}

JSON_LD (yapısal veri, varsa):
{json_ld_str}

STRUCTURED_JSON (JS-render sayfa verisi, varsa — __NEXT_DATA__/application-json):
{content.get('script_json', '')}

PAGE_TEXT (temizlenmiş, gürültüsüz):
{content.get('text', '')}

VALID_TAXONOMY (taxonomy alanlarını SADECE bunlardan seç; uymuyorsa ""):
- category:     {", ".join(store.VALID_CATEGORIES)}
- pattern:      {", ".join(store.VALID_PATTERNS)}
- weave_tags:   {", ".join(store.VALID_WEAVE_TAGS)}
- color_family: {", ".join(store.VALID_COLOR_FAMILIES)}

Bu sayfa bir kumaş ÜRÜN sayfası mı? Eğer evetse, sistem promptundaki kurallara göre alanları doldur. Eğer ürün sayfası değilse error: "page_not_product" döndür."""


def extract_fabric_fields(content: dict, model: str | None = None, image_bytes: bytes | None = None) -> dict:
    """Gemini ile sayfayı oku + form alanlarına eşle.

    Args:
      content: fetch_clean_content çıktısı
      model:   opsiyonel model adı (kullanıcı UI'dan override edebilir);
               None ise MODEL_NAME (env / default) kullanılır.
      image_bytes: P5 — verilirse multimodal (vision) çağrı; image_analysis doldurulur.

    Returns:
      {field: {value, evidence} | null, "error"?: str}
      veya hata durumunda: {"error": "..."}
    """
    if not _SDK_AVAILABLE:
        return {"error": "sdk_not_installed"}
    if not GEMINI_API_KEY:
        return {"error": "no_api_key"}

    genai.configure(api_key=GEMINI_API_KEY)

    model_name = (model or MODEL_NAME or "").strip() or MODEL_NAME
    gen_model = genai.GenerativeModel(
        model_name,
        system_instruction=SYSTEM_PROMPT,
    )

    user_prompt = _build_user_prompt(content)
    # P5 — multimodal: görsel verildiyse [prompt + görsel]; yoksa yalnız metin
    parts: Any = [user_prompt]
    if image_bytes:
        parts.append({"mime_type": "image/jpeg", "data": image_bytes})

    try:
        response = gen_model.generate_content(
            parts,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": RESPONSE_SCHEMA,
                "temperature": 0.0,  # deterministik
                # v4.0-part-2 Sprint 11.5: 2000 -> 4000. Schema'da reference_price
                # eklendi (+3 alan); arge_notu_taslak Türkçe karakter yoğun olduğundan
                # token kullanımı artıyor — JSON yarıda kesilmesin diye yüksek tut.
                # P5: taxonomy + image_analysis eklendi → 4000'den 6000'e.
                "max_output_tokens": 6000,
            },
        )
    except Exception as e:
        return {"error": f"gemini_api_error: {e}"}

    text = response.text or ""
    if not text.strip():
        return {"error": "gemini_empty_response"}

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        return {"error": f"json_parse_failed: {e}", "raw": text[:500]}

    # value alanı schema'da "string" — sayısal alanlar için backend parse eder.
    # Burada gelişmiş bir post-processing YAPMA, sayı dönüşümünü route katmanına bırak.
    return result


# ============================================================
# 3) Kullanışlı tek-çağrı sarmalayıcı
# ============================================================

# ============================================================
# v4.0-part-2 Adım 8 — Post-process: birim çevirisi + kompozisyon normalize
# ============================================================
def _post_process_suggestions(sug: dict) -> dict:
    """Gemini çıktısı → normalize: inch→cm, oz/yd²→g/m², kısaltma→tam isim.
    Evidence'a orijinal birim ipucu eklenir (kullanıcı doğrulayabilir).
    """
    if not isinstance(sug, dict):
        return sug

    def _convert_numeric(field_key: str, converter, unit_label: str):
        """width_cm / weight_gsm için birim çevirisi + evidence enrichment."""
        field = sug.get(field_key)
        if not isinstance(field, dict):
            return
        raw = field.get("value")
        if raw is None:
            return
        # Eğer Gemini zaten integer döndürdüyse, dokunma (zaten dönüştürülmüş)
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            field["value"] = int(raw)
            return
        # String ise: parse + convert
        if isinstance(raw, str) and raw.strip():
            raw_str = raw.strip()
            converted = converter(raw_str)
            if converted is not None:
                # Gerçek dönüşüm var mı? (raw'daki sayı ≠ converted ise birim çevrildi)
                m = re.search(r"\d+(?:[.,]\d+)?", raw_str)
                actually_converted = False
                if m:
                    try:
                        raw_num = float(m.group().replace(",", "."))
                        actually_converted = abs(raw_num - converted) > 0.5
                    except (ValueError, TypeError):
                        pass
                if actually_converted:
                    ev = field.get("evidence") or raw_str
                    arrow = f" → {converted} {unit_label}"
                    if arrow not in ev:
                        field["evidence"] = f"{ev}{arrow}"
                field["value"] = converted
            else:
                # Parse edemedi (range vs.) — value null, evidence ham metni tut
                if not field.get("evidence"):
                    field["evidence"] = raw
                field["value"] = None

    _convert_numeric("width_cm", parse_width_cm, "cm")
    _convert_numeric("weight_gsm", parse_weight_gsm, "g/m²")
    _convert_numeric("repeat_vertical_cm", parse_width_cm, "cm")
    _convert_numeric("repeat_horizontal_cm", parse_width_cm, "cm")

    # Kompozisyon — kısaltma sözlüğü ile normalize
    comp = sug.get("composition")
    if isinstance(comp, dict):
        raw = comp.get("value")
        if isinstance(raw, str) and raw.strip():
            normalized = normalize_composition(raw)
            if normalized and normalized != raw:
                ev = comp.get("evidence") or raw
                tag = f" (orijinal: {raw})"
                if raw not in ev and tag not in ev:
                    comp["evidence"] = f"{ev}{tag}"
                comp["value"] = normalized

    return sug


def linkten_doldur(url: str, model: str | None = None, image_bytes: bytes | None = None) -> dict:
    """Tek çağrıda fetch + extract. Route'tan kullanılır.

    Args:
      url:   sayfa URL'i
      model: opsiyonel model override; None ise MODEL_NAME (env/default)
      image_bytes: P5 — verilirse multimodal (vision) çağrı (image_analysis doldurulur)

    Returns:
      {"ok": True, "suggestions": {...}, "title": "...", "model_used": "..."}
      veya
      {"ok": False, "error": "...", "stage": "fetch"|"extract", "model_used": "..."}
    """
    used = (model or MODEL_NAME or "").strip() or MODEL_NAME
    # 1) Fetch
    try:
        content = fetch_clean_content(url)
    except requests.HTTPError as e:
        # Önemli: Response.__bool__ 4xx için False döndürür → `if e.response`
        # yerine `is not None` ile kontrol et.
        code = e.response.status_code if e.response is not None else "?"
        return {
            "ok": False, "stage": "fetch",
            "error": f"http_{code}",
            "message": f"Sayfa erişim hatası (HTTP {code})",
            "model_used": used,
        }
    except requests.RequestException as e:
        return {
            "ok": False, "stage": "fetch",
            "error": "network",
            "message": f"Sayfa çekilemedi: {e}",
            "model_used": used,
        }
    except Exception as e:
        return {
            "ok": False, "stage": "fetch",
            "error": "unknown",
            "message": f"Sayfa çekilemedi: {e}",
            "model_used": used,
        }

    # 2) Extract (görsel verildiyse multimodal)
    suggestions = extract_fabric_fields(content, model=model, image_bytes=image_bytes)
    if "error" in suggestions and not any(
        k for k in suggestions if k != "error"
    ):
        # Sadece error var, hiç field yok → Gemini hatası
        return {
            "ok": False, "stage": "extract",
            "error": suggestions["error"],
            "message": _human_error(suggestions["error"]),
            "model_used": used,
        }

    # v4.0-part-2 Adım 8 — Birim/kısaltma normalize (post-process)
    suggestions = _post_process_suggestions(suggestions)

    return {
        "ok": True,
        "suggestions": suggestions,
        "title": content.get("title", ""),
        "truncated": content.get("truncated", False),
        "source_text": _source_text_for_verify(content),   # P6.1 — kanıt doğrulama kaynağı
        "model_used": used,
    }


# ============================================================
# P6.1 — Kanıt doğrulama (uydurma koruması)
# Model, sayfada olmayan değer + sahte "evidence" üretebiliyor (gözlemlendi: JAB/Carlucci
# ürününde ağırlık/fiyat/rapor uydurma). Prompt yasağı (#3) tek başına yetmiyor → her factual
# alanın evidence'ı, AI'ya GÖNDERİLEN sayfa metninde GERÇEKTEN geçmiyorsa o alan ATILIR.
# ============================================================
def _norm_for_match(s: str) -> str:
    """Kanıt eşleştirme için normalize: NFKC + küçük harf + akıllı tırnak/çizgi sadeleştir + boşluk daralt."""
    s = unicodedata.normalize("NFKC", str(s or "")).lower()
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), (" ", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def _source_text_for_verify(content: dict) -> str:
    """AI'ya gönderilen tüm metinsel içerik (evidence bu metinde gerçekten geçmeli)."""
    parts = [
        content.get("title", ""), content.get("meta_description", ""),
        content.get("og_description", ""),
        json.dumps(content.get("json_ld") or [], ensure_ascii=False),
        content.get("script_json", ""), content.get("text", ""),
    ]
    return "\n".join(p for p in parts if p)


# ============================================================
# 4) Staging payload ayırıcı (OnCalisma-V2 Problem 4a)
# ============================================================
# Gemini çıktısını research_pool'un İKİ KATMANLI staging alanlarına ayırır:
#   extracted_facts (source_data) ← kanıtlı factual alanlar {value, evidence}
#   ai_summary      (ai_inferences) ← arge_notu + model + generated_at
# Anayasa #2: source ↔ inference ayrı; #3: evidence'sız factual YAZILMAZ.
# Bu fonksiyon SAF (DB'ye dokunmaz); route research_update ile yazar.

_AI_SUMMARY_FIELD = "arge_notu_taslak"  # ai_inferences'e gider (factual değil)


def _factual_field_names() -> list[str]:
    """RESPONSE_SCHEMA'dan factual alanlar (arge_notu_taslak + error hariç) — tek kaynak."""
    props = (RESPONSE_SCHEMA.get("properties") or {})
    # P5: taxonomy + image_analysis factual DEĞİL (inference) → ai_summary'e ayrı işlenir.
    # P6.2: brand_country (firma HQ) ÇIKARIM (dünya bilgisi) → kanıt-doğrulamadan muaf, suggested'a gider.
    return [k for k in props if k not in (_AI_SUMMARY_FIELD, "error", "taxonomy", "image_analysis", "brand_country")]


def build_enrichment_payload(gemini_result: dict) -> dict:
    """linkten_doldur() sonucunu staging payload'a ayır.
    Dönüş: {"extracted_facts": {...}, "ai_summary": {...}} ; hata → +{"error": ...} (boş payload).
    """
    out: dict = {"extracted_facts": {}, "ai_summary": {}}
    if not isinstance(gemini_result, dict):
        out["error"] = "invalid_result"
        return out
    if not gemini_result.get("ok", False) or gemini_result.get("error"):
        out["error"] = gemini_result.get("error") or "extract_failed"
        return out
    suggestions = gemini_result.get("suggestions")
    if not isinstance(suggestions, dict):
        out["error"] = "no_suggestions"
        return out

    # 1) Factual → extracted_facts (yalnız value+evidence DOLU olanlar; #3)
    # P6.1/P6.3 — Kanıt doğrulama: source_text verildiyse evidence sayfada GERÇEKTEN geçmeli.
    # Geçmiyorsa ARTIK ATILMAZ; fact["unverified"]=True ile işaretlenir → panelde "⚠ Şüpheli"
    # grubunda gösterilir, bulk "Tümünü Kabul" ETMEZ, kullanıcı elle karar verir (#3 + #6).
    src_norm = _norm_for_match(gemini_result.get("source_text") or "")
    unverified: list[str] = []
    for name in _factual_field_names():
        v = suggestions.get(name)
        if not isinstance(v, dict):
            continue
        value = v.get("value")
        evidence = v.get("evidence")
        value_s = value.strip() if isinstance(value, str) else value
        evidence_s = evidence.strip() if isinstance(evidence, str) else evidence
        if not value_s or not evidence_s:   # boş/kanıtsız factual ATLA (Anayasa #3)
            continue
        fact = {"value": value_s, "evidence": evidence_s}
        if v.get("type"):                    # reference_price: exact|from (şüphelide de korunur)
            fact["type"] = v.get("type")
        if src_norm and _norm_for_match(evidence_s) not in src_norm:
            fact["unverified"] = True         # P6.3 — kanıt sayfada YOK → ŞÜPHELİ (atma; elle onay)
            unverified.append(name)
        out["extracted_facts"][name] = fact
    if unverified:
        out["unverified_fields"] = unverified   # şeffaflık: hangi alanlar sayfada doğrulanamadı (⚠ Şüpheli)

    # 2) arge_notu_taslak → ai_summary.arge_notu (≤300) + model + generated_at
    from datetime import datetime, timezone
    summary: dict = {}
    arge = suggestions.get(_AI_SUMMARY_FIELD)
    if isinstance(arge, dict):
        av = arge.get("value")
        if isinstance(av, str) and av.strip():
            summary["arge_notu"] = av.strip()[:300]
    summary["model"] = gemini_result.get("model_used") or gemini_result.get("model")
    summary["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 3) P5 — Taksonomi ÖNERİSİ (inference): validate_* ile vocab'a temizle → ai_summary.suggested
    tax = suggestions.get("taxonomy")
    if isinstance(tax, dict):
        sug: dict = {}
        cat = store.validate_category(tax.get("category"))
        pat = store.validate_pattern(tax.get("pattern"))
        cf = store.validate_color_family(tax.get("color_family"))
        wt = store.validate_enum_list(tax.get("weave_tags") or [], store.VALID_WEAVE_TAGS)
        st = store.validate_str_list(tax.get("style_tags") or [])   # serbest (vocab yok)
        if cat: sug["category"] = cat
        if pat: sug["pattern"] = pat
        if cf: sug["color_family"] = cf
        if wt: sug["weave_tags"] = wt
        if st: sug["style_tags"] = st
        if sug:
            if tax.get("confidence"): sug["confidence"] = tax.get("confidence")
            if tax.get("reason"): sug["reason"] = tax.get("reason")
            summary["suggested"] = sug

    # 3b) P6.2 — brand_country (firma HQ): ÇIKARIM (dünya bilgisi) → suggested (sayfa kanıtı GEREKMEZ).
    # Üretim ülkesi DEĞİL; firma merkezi. norm_country app.py'de accept anında uygulanır.
    bc = suggestions.get("brand_country")
    if isinstance(bc, dict):
        bc_val = bc.get("value")
        bc_val = bc_val.strip() if isinstance(bc_val, str) else None
        if bc_val:
            summary.setdefault("suggested", {})["brand_country"] = bc_val

    # 4) P5 — Görsel analizi (inference): temizle → ai_summary.image_analysis
    ia = suggestions.get("image_analysis")
    if isinstance(ia, dict):
        img: dict = {}
        dom = [str(c).strip() for c in (ia.get("dominant_colors") or []) if str(c).strip()]
        if dom:
            img["dominant_colors"] = dom
        for k in ("texture", "transparency", "color_count", "confidence", "note"):
            val = ia.get(k)
            if isinstance(val, str) and val.strip():
                img[k] = val.strip()
        if img:
            summary["image_analysis"] = img

    out["ai_summary"] = summary
    return out


# ============================================================
# 5) P6 — Ürün varyant görseli için VISION-ONLY renk analizi (sayfa yok)
# ============================================================
_IMAGE_VISION_SCHEMA = {"type": "object", "properties": {"image_analysis": _IMAGE_ANALYSIS_OBJECT}}
_IMAGE_VISION_PROMPT = (
    "Sana bir KUMAŞ varyant görseli veriliyor. SADECE görsele bakarak image_analysis'i doldur:\n"
    "- dominant_colors: baskın renkler, hex (#RRGGBB) dizisi (kumaşın gerçek renkleri, en baskından).\n"
    "- texture: kısa (düz/dokulu/kabartmalı/mat/parlak). transparency: tül | yarı-şeffaf | opak.\n"
    "- color_count: görselde ayırt edilebilen renk sayısı (yalnız sayı). confidence (high|medium|low) + kısa note (Türkçe).\n"
    "Görseldeki yazı/filigranı veri olarak kullanma; yalnız kumaşın fiziksel görünümünü yorumla. "
    "Yalnız image_analysis nesnesini içeren tek JSON döndür."
)


def analyze_fabric_image(image_bytes: bytes, model: str | None = None) -> dict:
    """P6 — Sayfa YOK; yalnız görselden renk/doku/şeffaflık analizi (vision).
    Dönüş: temizlenmiş image_analysis dict ya da {"error": ...}."""
    if not _SDK_AVAILABLE:
        return {"error": "sdk_not_installed"}
    if not GEMINI_API_KEY:
        return {"error": "no_api_key"}
    if not image_bytes:
        return {"error": "no_image"}
    genai.configure(api_key=GEMINI_API_KEY)
    model_name = (model or MODEL_NAME or "").strip() or MODEL_NAME
    gen_model = genai.GenerativeModel(model_name)
    try:
        response = gen_model.generate_content(
            [_IMAGE_VISION_PROMPT, {"mime_type": "image/jpeg", "data": image_bytes}],
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": _IMAGE_VISION_SCHEMA,
                "temperature": 0.0,
                "max_output_tokens": 1500,
            },
        )
    except Exception as e:
        return {"error": f"gemini_api_error: {e}"}
    text = (response.text or "").strip()
    if not text:
        return {"error": "gemini_empty_response"}
    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        return {"error": f"json_parse_failed: {e}"}
    ia = result.get("image_analysis") if isinstance(result, dict) else None
    if not isinstance(ia, dict):
        return {"error": "no_image_analysis"}
    out: dict = {}
    dom = [str(c).strip() for c in (ia.get("dominant_colors") or []) if str(c).strip()]
    if dom:
        out["dominant_colors"] = dom
    for k in ("texture", "transparency", "color_count", "confidence", "note"):
        v = ia.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()
    if not out:
        return {"error": "empty_analysis"}
    out["model"] = model_name
    return out


def _human_error(code: str) -> str:
    """Hata kodunu kullanıcı-dostu Türkçe mesaja çevir."""
    if code == "no_api_key":
        return "GEMINI_API_KEY tanımlı değil — yöneticiye sor."
    if code == "sdk_not_installed":
        return "Gemini SDK yüklü değil (pip install google-generativeai)."
    if code == "page_not_product":
        return "Bu link bir kumaş ürün sayfası gibi görünmüyor (kategori, blog veya anasayfa olabilir)."
    if code == "page_empty":
        return "Sayfa erişilemez veya boş."
    if code.startswith("http_"):
        return f"Sayfa erişim hatası ({code.upper()})."
    if code.startswith("json_parse_failed"):
        return "Gemini beklenmedik bir format döndürdü, manuel doldurmayı dene."
    if code.startswith("gemini_api_error"):
        return f"Gemini API hatası: {code.split(':', 1)[-1].strip()}"
    return f"Bilinmeyen hata: {code}"
