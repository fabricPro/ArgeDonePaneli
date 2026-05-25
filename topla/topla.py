"""Orchestrator: URL → marka tespit → scrape → puanla → ham JSON."""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from topla.scrapers.kvadrat import scrape_kvadrat
from topla.scrapers.dedar import scrape_dedar
from topla.images import download_all
from topla.puanlama.staubli import compute_staubli_feasibility
from topla.puanlama.mobidik import compute_mobidik_score
from topla.puanlama.strategic_note import generate_strategic_note

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HAM_CIKTI_DIR = PROJECT_ROOT / "topla" / "ham_cikti"


def detect_brand(url: str) -> str:
    host = urlparse(url).netloc.lower().replace("www.", "")
    if "kvadrat" in host:
        return "kvadrat"
    if "dedar" in host:
        return "dedar"
    raise ValueError(f"Desteklenmeyen marka: {host}")


def scrape_and_score(url: str) -> dict:
    brand = detect_brand(url)

    if brand == "kvadrat":
        source_data = scrape_kvadrat(url)
    elif brand == "dedar":
        source_data = scrape_dedar(url)
    else:
        raise ValueError(
            f"Adaptör henüz yok: {brand}. Şu anda Kvadrat ve Dedar destekleniyor."
        )

    image_specs = source_data.pop("_image_specs", [])
    urun_slug = source_data.get("product_slug", "unknown")
    gorseller = download_all(image_specs, brand, urun_slug, PROJECT_ROOT)

    staubli = compute_staubli_feasibility(source_data)
    mobidik = compute_mobidik_score(source_data, staubli)
    note = generate_strategic_note(source_data, staubli)

    HAM_CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = source_data.get("product_slug", "unknown")
    out_path = HAM_CIKTI_DIR / f"{brand}_{slug}_{timestamp}.json"

    full_record = {
        "brand": source_data.get("brand"),
        "brand_slug": brand,
        "source_url": url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source_data": source_data,
        "gorseller": gorseller,
        "ai_inferences": None,
        "mobidik_evaluation": {
            "staubli_feasibility": staubli,
            "overall_score": mobidik["score"],
            "components": mobidik["components"],
            "strategic_note_template": note,
            "_note": (
                "Demo template — detaylı strategic değerlendirme + "
                "ai_inferences alanı Claude Code oturumunda yapılır."
            ),
        },
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(full_record, f, ensure_ascii=False, indent=2)

    return {
        "brand": source_data.get("brand"),
        "product_name": source_data.get("product_name"),
        "composition_text": source_data.get("composition_text"),
        "width_cm": source_data.get("width_cm"),
        "weave_type": source_data.get("weave_type"),
        "country_of_origin": source_data.get("country_of_origin"),
        "certifications": source_data.get("certifications"),
        "mobidik_score": mobidik["score"],
        "staubli_score": staubli["score"],
        "staubli_reasons": staubli["reasons"],
        "strategic_note": note,
        "gorseller": gorseller,
        "ham_cikti_path": str(out_path.relative_to(PROJECT_ROOT)),
    }
