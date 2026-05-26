"""Faz 6.8: 5 ham_cikti'yi karsilastir, dokuma + description bilgisi cikar."""
import json
import sys
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HAM = PROJECT_ROOT / "topla" / "ham_cikti"

FILES = [
    "dedar_wide-linen-baobab_20260526T090048Z.json",
    "dedar_wide-linen-atelier-1930_20260526T090127Z.json",
    "dedar_wide-linen-signor-darcy_20260526T090205Z.json",
    "kvadrat_broken-twill-sheer_20260526T090355Z.json",
    "dedar_twillman_20260526T090434Z.json",
]


def main():
    for fname in FILES:
        fp = HAM / fname
        d = json.loads(fp.read_text(encoding="utf-8"))
        sd = d.get("source_data", {})
        print(f"\n{'='*70}")
        print(f"  {sd.get('product_name')} ({fname})")
        print(f"{'='*70}")
        print(f"  brand: {sd.get('brand')}")
        print(f"  code: {sd.get('product_code')}")
        print(f"  composition: {sd.get('composition_text')}")
        print(f"  width: {sd.get('width_cm')} cm")
        print(f"  weight: {sd.get('weight_gsm')}")
        print(f"  weave_type_raw: {sd.get('weave_type_raw')}")
        print(f"  weave_type: {sd.get('weave_type')}")
        print(f"  use: {sd.get('use_raw')}")
        print(f"  country: {sd.get('country_of_origin')}")
        print(f"  collection: {sd.get('collection')}")
        print(f"  lightfastness: {sd.get('lightfastness')}")
        print(f"  certifications: {sd.get('certifications')}")
        print(f"  variant_count: {len(sd.get('variants_raw') or [])}")
        desc_raw = sd.get('description_original') or sd.get('description') or ''
        if isinstance(desc_raw, dict):
            desc = desc_raw.get('text', '')
        else:
            desc = str(desc_raw)
        print(f"  description ({len(desc)} kar):")
        if desc:
            print(f"    {desc[:500]}")
        body = sd.get("_body_text_preview", "")
        # Body'de dokuma anahtar kelimelerini ara
        keywords = ["weave", "jacquard", "dobby", "leno", "twill", "plain", "sheer", "satin",
                    "Construction", "Type:", "Pattern:"]
        print(f"  body keyword arama:")
        for kw in keywords:
            idx = body.lower().find(kw.lower())
            if idx >= 0:
                ctx = body[max(0, idx-20):idx+100].replace("\n", " ")
                print(f"    '{kw}' bulundu: ...{ctx}...")


if __name__ == "__main__":
    main()
