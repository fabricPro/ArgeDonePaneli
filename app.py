"""Streamlit demo — ARGE Perdelik Pazar Zekası v1.

Playwright Windows'ta Streamlit'in SelectorEventLoop'unda subprocess
kuramıyor (NotImplementedError). Bu nedenle scrape işi alt process'te
yapılıyor — Streamlit sadece UI + sonuç gösterimi.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="ARGE Perdelik Pazar Zekası",
    layout="centered",
)

st.title("ARGE Perdelik Pazar Zekası")
st.caption(
    "Premium perdelik üreticilerini izleyen veri sistemi — demo v1 "
    "(şu anda yalnız Kvadrat destekleniyor)"
)

url = st.text_input(
    "Ürün URL'si",
    placeholder="https://www.kvadrat.dk/en/products/curtains/5539-air-line",
)


def run_scrape(url: str) -> dict:
    """Scrape'i alt process'te çalıştır (Windows asyncio sorununu aş)."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "topla.cli",
            url,
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Scrape failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )
    # Subprocess JSON satırını stdout'un sonuna yazar
    last_line = result.stdout.strip().splitlines()[-1]
    return json.loads(last_line)


if st.button("Tara", type="primary", disabled=not url):
    with st.spinner("Tarama yapılıyor… 30 sn sürebilir"):
        try:
            r = run_scrape(url.strip())
        except ValueError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Tarama hatası: {e}")
            st.stop()

    st.success("Tarama tamam.")

    def show(label, value):
        if value in (None, "", []):
            st.markdown(f"**{label}:** _(veri bulunamadı)_")
        elif isinstance(value, list):
            st.markdown(f"**{label}:** {', '.join(value)}")
        else:
            st.markdown(f"**{label}:** {value}")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Ürün")
        show("Marka", r.get("brand"))
        show("Ürün adı", r.get("product_name"))
        show("Kompozisyon", r.get("composition_text"))
        show("En", f"{int(r['width_cm'])} cm" if r.get("width_cm") else None)
        show("Dokuma", r.get("weave_type"))

    with col2:
        st.subheader("Üretim & Sertifikasyon")
        show("Üretim ülkesi", r.get("country_of_origin"))
        show("Sertifikalar", r.get("certifications"))

    st.divider()
    st.subheader("Mobidik Değerlendirme")

    m1, m2 = st.columns(2)
    with m1:
        st.metric("Mobidik Genel Puan", f"{r['mobidik_score']}/100")
    with m2:
        st.metric("Stäubli Yapılabilirlik", f"{r['staubli_score']}/5")

    st.markdown("**Türkçe stratejik not:**")
    st.info(r["strategic_note"])

    st.divider()

    gorseller = r.get("gorseller") or []
    indirilenler = [g for g in gorseller if g.get("dosya_yolu")]

    if not indirilenler:
        st.subheader("Görseller")
        st.caption("(görsel bulunamadı)")
    else:
        ana = [g for g in indirilenler if g["tip"] == "ana"]
        varyant = [g for g in indirilenler if g["tip"] == "varyant"]
        detay = [g for g in indirilenler if g["tip"] == "detay"]
        lifestyle = [g for g in indirilenler if g["tip"] == "lifestyle"]

        if ana:
            st.subheader("Ana Görsel")
            st.image(ana[0]["dosya_yolu"], use_container_width=True)

        if varyant:
            st.subheader(f"Renk Varyantları ({len(varyant)})")
            cols = st.columns(4)
            for i, v in enumerate(varyant):
                with cols[i % 4]:
                    st.image(
                        v["dosya_yolu"],
                        caption=v.get("varyant_adi") or f"#{i + 1}",
                        use_container_width=True,
                    )

        if detay:
            st.subheader(f"Detay Görselleri ({len(detay)})")
            cols = st.columns(3)
            for i, d in enumerate(detay):
                with cols[i % 3]:
                    st.image(d["dosya_yolu"], use_container_width=True)

        if lifestyle:
            st.subheader(f"Lifestyle ({len(lifestyle)})")
            cols = st.columns(2)
            for i, l in enumerate(lifestyle):
                with cols[i % 2]:
                    st.image(l["dosya_yolu"], use_container_width=True)

        # Toplam indirme özeti
        toplam_kb = sum(
            (g.get("dosya_boyutu_kb") or 0) for g in indirilenler
        )
        st.caption(
            f"Toplam {len(indirilenler)} görsel indirildi · "
            f"{toplam_kb / 1024:.1f} MB"
        )

    st.caption(f"Ham JSON kaydedildi: `{r['ham_cikti_path']}`")
