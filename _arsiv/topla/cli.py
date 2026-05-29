"""CLI:

Tek URL modu (mevcut):
    python -m topla.cli <URL> -> stdout'a JSON tek satir

Batch aday kesfi modu (Faz 6):
    python -m topla.cli --batch <bolge>
    -> topla/ham_cikti/aday_<bolge>_<tarih>.json
    Bolgeler: nordik, italyan, alman
"""

import json
import sys

from topla.batch import run_batch
from topla.topla import scrape_and_score


def main():
    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  python -m topla.cli <url>          # tek urun scrape + puanla\n"
            "  python -m topla.cli --batch <bolge>  # bolge aday kesfi",
            file=sys.stderr,
        )
        sys.exit(2)

    arg = sys.argv[1]
    if arg == "--batch":
        if len(sys.argv) < 3:
            print("Kullanim: python -m topla.cli --batch <bolge>", file=sys.stderr)
            print("Bolgeler: nordik, italyan, alman", file=sys.stderr)
            sys.exit(2)
        region = sys.argv[2]
        rapor = run_batch(region)
        if rapor.get("status") == "unknown_region":
            print(f"Hata: {rapor.get('error')}", file=sys.stderr)
            sys.exit(2)
        return

    # Tek URL modu
    url = arg
    result = scrape_and_score(url)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
