"""Playwright browser launch helper — env-bagimsiz path resolve.

Faz 7.10e fix: Flask subprocess sandbox'ta hem LOCALAPPDATA eksik hem
Path.exists() check de sandbox file system view sinirli. Cozum: path'i
ASLA check etme, dogrudan Playwright'a ver (file system access subprocess
icinde gercek user context'inde olur).
"""
import os
from pathlib import Path


def _candidate_headless_paths() -> list[str]:
    """Olasi headless shell path'leri (oncelik sirasi)."""
    paths = []

    # 1) Hardcoded — Mobidik kullanicisi PC (en kesin)
    paths.append("C:/Users/PC/AppData/Local/ms-playwright/chromium_headless_shell-1148/chrome-win/headless_shell.exe")

    # 2) USERPROFILE base
    userprofile = os.environ.get("USERPROFILE", "").strip()
    if userprofile:
        paths.append(str(Path(userprofile) / "AppData/Local/ms-playwright/chromium_headless_shell-1148/chrome-win/headless_shell.exe"))

    # 3) LOCALAPPDATA base
    localappdata = os.environ.get("LOCALAPPDATA", "").strip()
    if localappdata:
        paths.append(str(Path(localappdata) / "ms-playwright/chromium_headless_shell-1148/chrome-win/headless_shell.exe"))

    # 4) Custom PLAYWRIGHT_BROWSERS_PATH
    custom = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if custom:
        paths.append(str(Path(custom) / "chromium_headless_shell-1148/chrome-win/headless_shell.exe"))

    # Unique
    seen = set()
    out = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def launch_chromium(playwright, headless: bool = True, **kwargs):
    """Chromium browser launch — birden fazla path dene.

    Path'i ASLA check etme (sandbox file system view eksik olabilir).
    Direkt Playwright'a ver, fail ederse bir sonraki path'i dene.
    Hicbiri olmazsa default (PLAYWRIGHT_BROWSERS_PATH env) ile son deneme.
    """
    last_error = None
    if headless and "executable_path" not in kwargs:
        for candidate in _candidate_headless_paths():
            try:
                return playwright.chromium.launch(
                    headless=True,
                    executable_path=candidate,
                    **kwargs,
                )
            except Exception as e:
                last_error = e
                continue

    # Default (env-based) fallback
    try:
        return playwright.chromium.launch(headless=headless, **kwargs)
    except Exception as e:
        # Tum denemeler basarisiz — son hatayi raise et
        if last_error:
            raise last_error
        raise e
