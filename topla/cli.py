"""CLI: python -m topla.cli <URL> → stdout'a JSON tek satır."""

import json
import sys

from topla.topla import scrape_and_score


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m topla.cli <url>", file=sys.stderr)
        sys.exit(2)
    url = sys.argv[1]
    result = scrape_and_score(url)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
