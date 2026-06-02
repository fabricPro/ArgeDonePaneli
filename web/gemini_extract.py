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
from typing import Any

import requests
from bs4 import BeautifulSoup

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
TEXT_TRUNCATE = 8000          # Gemini'ye gönderilecek max düz metin (token tasarrufu)
JSON_LD_TRUNCATE = 3000       # JSON-LD bloku max char

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
   - "70% cotton, 30% linen" → composition.value: "%70 pamuk, %30 keten"
   - "Width 137 cm" → width_cm.value: 137
   - "Jacquard" → weave_type.value: "jacquard" (lowercase, mevcut listeyi tercih: dobby, jacquard, plain, leno, sheer, bouclé, saten, twill)
   - Renk varyantı, ürün kodu, SKU, marka adı: olduğu gibi bırak (çevirme)
   - Koleksiyon adı: orijinal dilinde bırak ("Cobra Collection" → "Cobra Collection")

4) SAYISAL ALANLAR (width_cm, weight_gsm, repeat_*):
   - "Width: 137 cm" → 137 (integer)
   - "300-310 cm" gibi range → null (belirsizlik), evidence: "300-310 cm"
   - "g/m²" yoksa weight_gsm null
   - Sayı kesirli (137.5) ise integer'a yuvarlama YAPMA — null bırak ve evidence ver, kullanıcı karar versin

5) ANAYASA KURAL #3 — bu alanlar AŞIRI HASSAS:
   - brand: Sayfanın header / meta etiketi (og:site_name, application_name) / footer / page title / breadcrumb içinde AÇIKÇA YAZAN marka adını al. Domain (örn. "kvadrat.dk") TEK BAŞINA evidence olarak yetmez — sayfa metninde mutlaka geçmeli; geçtiği yeri evidence'a yaz.
       * Multi-brand reseller (etoffe.com, romo.com vb.): ürün-spesifik marka açıkça yazıyorsa ("by Coordonné", "Coordonné collection") onu al; aksi halde NULL.
       * Tasarımcı/kolaboratör (Patricia Urquiola, Marc Newson) MARKA DEĞİL — onlar arge_notu_taslak'a girer.
       * Marka adı orijinal yazımıyla kalır (çevirme): "Coordonné", "Création Baumann", "Dedar", "Kvadrat".
       * Birden fazla aday varsa (örn. reseller sitede hem "Etoffe" hem "Coordonné") ürünü ÜRETEN/TASARLAYAN markayı tercih et.
   - composition: tam alıntı yapamıyorsan NULL. "Mostly natural fibers" gibi belirsiz ifadeler NULL.
   - production_country: SAYFA "Made in Italy" gibi üretim yeri belirtiyorsa "İtalya". Marka HQ (firma merkezi) ile KARIŞTIRMA. Belirtmiyorsa NULL.
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

9) ÇIKTI FORMATI: response_schema'ya UYGUN JSON. Her alan ya {value, evidence} (fiyat için {value, type, evidence}) ya null. Hiçbir şekilde ek metin veya açıklama EKLEME. Tek JSON object döndür."""


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

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "brand":                 _FIELD_OBJECT,   # v4.0-part-2 Sprint 11.6 — YENİ
        "product_name":          _FIELD_OBJECT,
        "product_code":          _FIELD_OBJECT,
        "collection":            _FIELD_OBJECT,
        "production_country":    _FIELD_OBJECT,   # v4.0-part-2 Sprint 11.5 — 'country' yerine
        "composition":           _FIELD_OBJECT,
        "width_cm":              _FIELD_OBJECT,
        "weight_gsm":            _FIELD_OBJECT,
        "weave_type":            _FIELD_OBJECT,
        "repeat_vertical_cm":    _FIELD_OBJECT,
        "repeat_horizontal_cm":  _FIELD_OBJECT,
        "reference_price":       _PRICE_FIELD_OBJECT,  # v4.0-part-2 Sprint 11.5 — YENİ
        "arge_notu_taslak":      _FIELD_OBJECT,
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

    # 4) Düz metin için script/style/nav/footer temizle
    for t in soup(["script", "style", "noscript", "iframe", "svg"]):
        t.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # Çoklu boşluk → tek boşluk
    text = " ".join(text.split())

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

PAGE_TEXT (temizlenmiş, max 8000 char):
{content.get('text', '')}

Bu sayfa bir kumaş ÜRÜN sayfası mı? Eğer evetse, sistem promptundaki kurallara göre alanları doldur. Eğer ürün sayfası değilse error: "page_not_product" döndür."""


def extract_fabric_fields(content: dict, model: str | None = None) -> dict:
    """Gemini ile sayfayı oku + form alanlarına eşle.

    Args:
      content: fetch_clean_content çıktısı
      model:   opsiyonel model adı (kullanıcı UI'dan override edebilir);
               None ise MODEL_NAME (env / default) kullanılır.

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

    try:
        response = gen_model.generate_content(
            user_prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": RESPONSE_SCHEMA,
                "temperature": 0.0,  # deterministik
                # v4.0-part-2 Sprint 11.5: 2000 -> 4000. Schema'da reference_price
                # eklendi (+3 alan); arge_notu_taslak Türkçe karakter yoğun olduğundan
                # token kullanımı artıyor — JSON yarıda kesilmesin diye yüksek tut.
                "max_output_tokens": 4000,
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

def linkten_doldur(url: str, model: str | None = None) -> dict:
    """Tek çağrıda fetch + extract. Route'tan kullanılır.

    Args:
      url:   sayfa URL'i
      model: opsiyonel model override; None ise MODEL_NAME (env/default)

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

    # 2) Extract
    suggestions = extract_fabric_fields(content, model=model)
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

    return {
        "ok": True,
        "suggestions": suggestions,
        "title": content.get("title", ""),
        "truncated": content.get("truncated", False),
        "model_used": used,
    }


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
