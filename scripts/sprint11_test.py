"""Sprint 11 yerel test: Linkten Doldur endpoint'i.

- .env'den APP_PASSWORD okur (yazdırmaz)
- Flask /login'e POST → session cookie alır
- 3 senaryoyu çalıştırır + sonucu özet halinde basar
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import requests

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE = "http://localhost:5000"
PASSWORD = os.environ.get("APP_PASSWORD", "")
HAS_GEMINI = bool(os.environ.get("GEMINI_API_KEY"))


def login(s):
    if not PASSWORD:
        print("X APP_PASSWORD .env'de bulunamadi")
        return False
    r = s.post(BASE + "/login", data={"password": PASSWORD},
               allow_redirects=False, timeout=10)
    if r.status_code in (302, 303) and "login" not in (r.headers.get("Location") or ""):
        print("OK Login -> " + str(r.headers.get("Location")))
        return True
    print("X Login basarisiz: " + str(r.status_code))
    return False


def test_case(s, name, url):
    print("\n------ " + name)
    print("  URL: " + url)
    r = s.post(BASE + "/api/urun/linkten-doldur",
               json={"url": url}, timeout=60)
    print("  HTTP " + str(r.status_code))
    try:
        data = r.json()
    except Exception:
        print("  X JSON parse hatasi: " + r.text[:200])
        return {}
    if data.get("ok"):
        sug = data.get("suggestions") or {}
        title = data.get("title", "")
        print("  OK ok=True  title=" + repr(title[:80]))
        if not sug:
            print("    (onerisiz)")
        else:
            for k, v in sug.items():
                if k == "error":
                    print("    ! error: " + str(v))
                    continue
                if not isinstance(v, dict):
                    print("    - " + k + ": (skip non-object)")
                    continue
                val = v.get("value")
                ev = v.get("evidence", "")
                # v4.0-part-2 Sprint 11.5 — reference_price 'type' alani da goster
                typ = v.get("type")
                if typ:
                    print("    * " + k.ljust(22) + " = " + repr(str(val)[:60]) + "  [type=" + str(typ) + "]")
                else:
                    print("    * " + k.ljust(22) + " = " + repr(str(val)[:60]))
                print("      evidence: " + repr(ev[:120]))
    else:
        print("  X ok=False  stage=" + str(data.get("stage")) + "  error=" + str(data.get("error")))
        print("     message: " + str(data.get("message")))
    return data


def main():
    print("GEMINI_API_KEY: " + ("set" if HAS_GEMINI else "X TANIMSIZ"))
    print("APP_PASSWORD:   " + ("set" if PASSWORD else "X TANIMSIZ"))
    if not PASSWORD:
        sys.exit(1)

    s = requests.Session()
    if not login(s):
        sys.exit(1)

    # 1) Kvadrat Daybreak — production_country test (Made in Turkey)
    test_case(s, "1) Kvadrat Daybreak (production_country=TR beklenir)",
              "https://www.kvadrat.dk/en/products/curtains/1073-daybreak-3")

    # 2) Etoffe — reference_price test (genelde 'from EUR' var)
    test_case(s, "2) Etoffe huipil (reference_price 'from' beklenir)",
              "https://www.etoffe.com/en/furnishing-fabrics/49612-huipil-outdoor-fabric-coordonne.html")

    # 3) Wikipedia anasayfa (urun degil)
    test_case(s, "3) Wikipedia anasayfa (page_not_product beklenir)",
              "https://en.wikipedia.org/wiki/Main_Page")

    # 4) Gecersiz / olmayan URL
    test_case(s, "4) Olmayan domain (fetch hatasi beklenir)",
              "https://this-domain-does-not-exist-test-12345.invalid/x")

    print("\nBitti.")


if __name__ == "__main__":
    main()
