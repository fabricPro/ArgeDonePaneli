"""Faz 3.4 detay denetim: kalan 15 urun icin mobidik_evaluation tam dolduran patch.

Her urun icin kapasite tablosu (anayasa #7) uygulanir, mobidik_evaluation:
- staubli_feasibility: skor + comment (kapasite uygulama gerekcesi)
- arge_value, market_gap, portfolio_fit
- overall_score + priority_level
- strategic_note (Turkce, aksiyon plani)
- audit_history.notes (denetim ozeti)

Skor dagilimi: 5/5 = 9 urun, 4/5 = 4 urun, 3/5 = 1 (Andria), 1/5 = 1 (Blanc de Lin orme)

Anayasa #9: Python mekanik JSON modify; degerlerin Claude denetimi sonucu.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URUNLER = ROOT / "markalar" / "urunler"
NOW = "2026-05-25T23:15:00Z"


def patch(filename: str, evaluation: dict, audit_note: str):
    """Tek urune mobidik_evaluation + audit + completeness patch."""
    path = URUNLER / filename
    with path.open(encoding="utf-8") as f:
        d = json.load(f)
    d["mobidik_evaluation"] = evaluation
    d["source_data"]["_provenance"]["constitutional_violations_check"] = f"passed_at_{NOW}"
    d["source_data"]["_provenance"]["audit_history"].append({
        "audit_id": f"{d['urun_id']}_v1.1_2026-05-25",
        "audit_date": "2026-05-25",
        "version_before": "v1.0 (Faz 3.4 batch migrate, mobidik_evaluation PENDING)",
        "version_after": "v1.1 (Faz 3.4 detay denetim, mobidik_evaluation tam)",
        "notes": audit_note,
    })
    d["last_updated"] = NOW
    d["data_quality"]["completeness_percent"] = 70
    with path.open("w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"  {filename}: staubli={evaluation['staubli_feasibility']['score']}/5, overall={evaluation['overall_score']}")


# === Z+R Group: 5 urun ===

# 1) Melange Linen — %100 keten plain sheer, Belcika (Belgian Linen)
patch("zimmer_rohde_10969-melange-linen.json", {
    "_description": "Melange Linen — Belgian Linen sertifikali %100 keten plain sheer, 283 cm. Kapasite tablosu #7 uygulandi: keten standart iplik TAM, plain TAM.",
    "staubli_feasibility": {
        "score": 5, "frame_count_estimate": "2-4",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun",
        "reed_density_estimate": "12-16 dent/cm (sheer plain)",
        "sizing_requirement": "Keten haşıl + sheer warp tension",
        "comment": "Tum Stabli kriterleri TAM: 283 cm ≤ 360, plain sheer TAM, %100 spun keten standart iplik. Mobidik mevcut keten kapasitesinde dogrudan replica.",
    },
    "arge_value": {"score": 80, "key_learnings": ["Belgian Linen sertifika sureci (Masters of Linen)", "10 renk melange iplik yonetimi", "Sheer keten plain dokuma — CO2-notr soylemi"],
                   "comment": "Belgian Linen referans urunu. AB ihracatinda sertifika kritik. Mobidik 'Anatolian Linen' sub-brand'i ile paralel pozisyon."},
    "market_gap": {"score": 80, "comment": "Turkiye'de Belgian Linen denkligi yok; lokal keten + EU Flax sertifikasi yatirim alani. Z+R retail 80-130 EUR/m -> Mobidik 20-30 EUR/m.",
                   "target_markets": ["TR (lux residential)", "AB (DE/BE/NL)", "GCC"]},
    "portfolio_fit": {"score": 85, "similar_existing_products": ["Kvadrat Air Line"], "comment": "Mobidik keten portfoyu icin omurga urun. Air Line ile birlikte 'pure linen' alt hatti."},
    "overall_score": 81, "priority_level": "yuksek",
    "strategic_note": "Kapasite TAM. Pilot: 3 notr ton x 100 m, 4-6 hafta. Belgian Linen yerine EU Flax + OEKO-TEX sertifika basvurusu paralel. Anatolian Linen alt hatti calismasinin temel urunu olabilir.",
}, "Plain sheer keten, kapasite TAM. Belgian Linen sertifikasinin Turk muadili EU Flax + OEKO-TEX acik is.")

# 2) Softgrid — 4-bilesen karisim (PES+Cot+Vis+Lin) dobby grid
patch("zimmer_rohde_10918-softgrid.json", {
    "_description": "Softgrid — 4-bilesen karisim (PES 36%, Cot 34%, Vis 16%, Lin 14%) dobby grid, 300 cm, 12 renk. Kapasite TAM ama iplik MOQ riski.",
    "staubli_feasibility": {
        "score": 5, "frame_count_estimate": "4-8",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun",
        "reed_density_estimate": "16-20 dent/cm (dobby grid)",
        "sizing_requirement": "Multi-fiber blend yarn warp tension hassasiyeti",
        "comment": "Stabli kriterleri TAM: 300 cm, dobby TAM, 4-bilesen karisim iplik standart kategoriler icinde. Asil darbogaz: 4-fiber MOQ.",
    },
    "arge_value": {"score": 75, "key_learnings": ["4-bilesen karisim iplik MOQ yonetimi", "3-bilesen muadili ile %90 yakinlik + maliyet -%20", "Sketchbook koleksiyon estetik benchmark"],
                   "comment": "4-bilesen iplik tedariki Turkiye'de niş (Korteks). 3-bilesen alternatif (PES+Cot+Lin) %90 yakinlik."},
    "market_gap": {"score": 70, "comment": "Multi-fiber dobby grid Türkiye'de yerel üretim yok. Mobidik 3-bilesen muadili ile maliyet avantaji.",
                   "target_markets": ["TR", "DACH", "Nordik"]},
    "portfolio_fit": {"score": 75, "similar_existing_products": [], "comment": "Mobidik karisim iplik portfoyune iyi ek. 12 renk yonetimi orta zorluk."},
    "overall_score": 74, "priority_level": "orta",
    "strategic_note": "Kapasite TAM, ana darbogaz 4-bilesen iplik MOQ. Onerilen: 3-bilesen muadil (PES+Cot+Lin) ile pilot, %90 gorsel yakinlik + %20 maliyet dususu. Pilot: 4 notr ton x 100 m, 6-8 hafta. Korteks 3-bilesen teklif talep et.",
}, "Dobby 4-bilesen karisim, kapasite TAM. 4-bilesen MOQ darboğaz, 3-bilesen muadili oneriliyor.")

# 3) Loops — %82 yun + %16 alpaka + %2 polyamide, boucle leno
patch("zimmer_rohde_10971-loops.json", {
    "_description": "Loops — yun+alpaka boucle (open semi-transparent), 315 cm. Kapasite: yun TAM, alpaka kapasitede explicit yok ama yun benzeri calisir, boucle iplik niş.",
    "staubli_feasibility": {
        "score": 4, "frame_count_estimate": "4-8",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun",
        "reed_density_estimate": "10-14 dent/cm (boucle open)",
        "sizing_requirement": "Yun/alpaka boucle warp tension hassasiyeti, anti-static treatment",
        "comment": "Dokuma TAM (boucle = dobby + ozel iplik); width 315<=360. Asil darbogaz: yun+alpaka boucle iplik tedariki — Yunsa/Polaron MOQ ~1000 kg, alpaka %16 nis. Skor 4 (5 degil) cunku iplik tedariki kritik.",
    },
    "arge_value": {"score": 80, "key_learnings": ["Yun+alpaka boucle iplik tedariki", "Premium boucle drapery — DACH segment", "Open weave semi-transparent yun"],
                   "comment": "Niket + Fil du Temps + Alpaca Leno + Loops = 4-urun premium leno/open hatti potansiyeli."},
    "market_gap": {"score": 80, "comment": "Türkiye'de yun+alpaka boucle yerel üretim yok. DACH premium yün/alpaka segment AB'de buyuyor. Z+R retail 100-150 EUR/m -> Mobidik 30-40 EUR/m.",
                   "target_markets": ["DACH", "Nordik", "TR premium konut"]},
    "portfolio_fit": {"score": 75, "similar_existing_products": ["Kvadrat Alpaca Leno"], "comment": "Alpaca Leno ile birlikte premium yun/alpaka segment. ARGE yatirimi (iplik) gerek."},
    "overall_score": 78, "priority_level": "yuksek",
    "strategic_note": "Yun+alpaka boucle = niş premium. Acil aksiyon: (1) Yunsa+Polaron yun+alpaka boucle iplik teklifi, MOQ muzakere, (2) Pilot: 3 notr ton x 60 m, 6-8 hafta, (3) DACH ihracat kanali (Almanya/Avusturya konut), (4) Alpaca Leno ile birlikte ROI hesabi.",
}, "Yun+alpaka boucle, dokuma kapasitede ama iplik MOQ darbogaz. Premium AB segment potansiyel yuksek.")

# 4) Ishari — %100 PES double-layer + effect yarns
patch("zimmer_rohde_11047-ishari.json", {
    "_description": "Ishari — double-layer PES + effect yarns (peak/valley), 310 cm. Kapasitede 'çift atki TAM' ve 'çift cozgu TAM' explicit; double-cloth bu kombinasyonla yapilabilir.",
    "staubli_feasibility": {
        "score": 4, "frame_count_estimate": "8-12",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun (cift atki TAM)", "repeat_size_compatibility": "uygun (kontrol gerek)",
        "reed_density_estimate": "18-22 dent/cm",
        "sizing_requirement": "Double-layer warp beam yonetimi + peak/valley programlama",
        "comment": "Kapasite: cift atki + cift cozgu TAM listelenmis (kapasite tablosu). Double-cloth bu iki teknigin kombinasyonu, Stabli'de 8-12 cerceve + ozel programlama. Skor 4 (programlama komplikasyonu, peak/valley defekt riski).",
    },
    "arge_value": {"score": 70, "key_learnings": ["Double-cloth programlama deneyimi", "Effect yarn tedariki", "Peak/valley defekt yonetimi"],
                   "comment": "Mobidik icin yeni teknik kategori — programlama capacity buyutme firsati."},
    "market_gap": {"score": 65, "comment": "Türkiye'de PES double-cloth yerel uretim sinirli. AB pazarinda Z+R 70-100 EUR/m, niş segment.",
                   "target_markets": ["DACH", "Nordik"]},
    "portfolio_fit": {"score": 70, "similar_existing_products": [], "comment": "Yeni teknik kategori — capacity yatirimi gerek."},
    "overall_score": 72, "priority_level": "orta",
    "strategic_note": "Cift atki + cozgu kapasite TAM, double-cloth Stabli'de yapilabilir ama 8-12 cerceve + programlama. Pilot: 1 nötr ton x 50 m, 8-10 hafta (test programlama dahil). Mevcut After The Rain koleksiyon temasi (yagmur sonrasi) ile Mobidik 'Anatolian After Rain' sub-brand'i.",
}, "Double-cloth = cift atki/cozgu kombinasyonu, kapasite TAM listelenmis. 8-12 cerceve programlama orta zorluk.")

# 5) Nuri — %57 keten + %43 pamuk (Documents raporu); crosshatch dobby
patch("zimmer_rohde_11049-nuri.json", {
    "_description": "Nuri — keten/pamuk crosshatch (variable thread density), 295/315 cm, After The Rain koleksiyonu. Kapasite TAM: dobby + keten/pamuk standart iplikler.",
    "staubli_feasibility": {
        "score": 5, "frame_count_estimate": "4-8",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun",
        "reed_density_estimate": "16-20 dent/cm (crosshatch)",
        "sizing_requirement": "Keten+pamuk karisim standart hasil",
        "comment": "Tum kriterler TAM: 315 cm <= 360, dobby crosshatch standart, keten+pamuk Turkiye lider tedarik (Bursa+Adana). Variable thread density programlama Stabli'de yapilabilir.",
    },
    "arge_value": {"score": 80, "key_learnings": ["Crosshatch variable density programlama", "Keten/pamuk karisim warp tension", "After The Rain estetik benchmark"],
                   "comment": "Mobidik keten/pamuk hattinin showcase urunu olabilir."},
    "market_gap": {"score": 80, "comment": "Türkiye keten/pamuk üretiminde lider; Nuri-tipi crosshatch yerel uretim yok. Z+R retail 60-90 EUR/m -> Mobidik 15-25 EUR/m.",
                   "target_markets": ["TR (residential)", "AB (DK/NL)", "GCC"]},
    "portfolio_fit": {"score": 85, "similar_existing_products": ["Mobidik mevcut keten/pamuk dobby"], "comment": "Mobidik core competency uzantisi."},
    "overall_score": 82, "priority_level": "yuksek",
    "strategic_note": "Kapasite TAM. Pilot: 3 ton (883, 990, 991 = 3 renk) x 120 m, 4-6 hafta. Anatolian After Rain sub-brand'inde Niket + Nuri + Ishari birlikte. Variable thread density Stabli programlama pilot test.",
}, "Crosshatch keten/pamuk, kapasite TAM. Core competency hatti showcase urunu.")


# === ADO Goldkante: 5 urun (Capri Plus zaten 5/5 audited) ===

# 6) ORA — %59 PES + %41 Cotton dobby kucuk dama, 11 renk
patch("ado_goldkante_3018-ora.json", {
    "_description": "ORA — PES/Cot melange iplik dobby check, 300 cm, 11 renk. Kapasite TAM: dobby + PES/Cot standart.",
    "staubli_feasibility": {
        "score": 5, "frame_count_estimate": "2-8",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun (kucuk dama <=8 cm)",
        "reed_density_estimate": "18-22 dent/cm",
        "sizing_requirement": "Standart PES/Cot melange hasil",
        "comment": "Tum kriterler TAM. PES/Cot melange iplik Turkiye yaygin (SASA, Korteks, Bossa). 11 renk yonetimi standart.",
    },
    "arge_value": {"score": 70, "key_learnings": ["Melange iplik yonetimi", "11-renk PES/Cot palette logistic"], "comment": "Kolay-orta replica adayi, capacity ogrenme firsati."},
    "market_gap": {"score": 70, "comment": "Türkiye'de PES/Cot dobby check yerel uretim sinirli ama tedarik kolay. ADO retail 50-80 EUR/m -> Mobidik 12-18 EUR/m.",
                   "target_markets": ["TR (ofis + residential)", "AB"]},
    "portfolio_fit": {"score": 80, "similar_existing_products": [], "comment": "ADO kolay-orta ilk replica adayi. 11 renkli ilk pilot uygun deneyim."},
    "overall_score": 73, "priority_level": "orta",
    "strategic_note": "Kapasite TAM. 3-4 notr ton x 100 m pilot, 4-6 hafta. Melange iplik Korteks teklif. Sketchbook/Heritage koleksiyon paralel ilk experience.",
}, "Dobby kucuk dama PES/Cot, kapasite TAM. Kolay replica adayi.")

# 7) Harry RE — %54 rPES + %46 PES sheer, 1 renk
patch("ado_goldkante_3009-harry-re.json", {
    "_description": "Harry RE — recycled PES + PES sheer voile, 315 cm. Kapasite TAM: rPES standart kategoride; sheer plain TAM. GRS sertifika sureci Mobidik icin acik is.",
    "staubli_feasibility": {
        "score": 5, "frame_count_estimate": "2",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun (rapor yok)",
        "reed_density_estimate": "10-14 dent/cm (sheer)",
        "sizing_requirement": "rPES texturized standart hasil",
        "comment": "Stabli kriterleri TAM: sheer plain + rPES standart iplik. 315 cm yakin sinir ama hala TAM. GRS sertifika sureci paralel.",
    },
    "arge_value": {"score": 85, "key_learnings": ["rPES iplik tedariki (SASA, Korteks GRS sertifikali)", "Post-consumer recycled supply chain", "GRS sertifika basvuru sureci"],
                   "comment": "ALTIN urun adayi: sürdürülebilirlik claim + Turkiye rPES lider. AB ihracat icin kritik."},
    "market_gap": {"score": 85, "comment": "Türkiye SASA + Korteks GRS sertifikali rPES uretiyor; lokal sheer rPES perde yok. ADO retail 60-90 EUR/m -> Mobidik 15-25 EUR/m.",
                   "target_markets": ["AB (sürdürülebilirlik claim)", "TR (yesil bina segment)", "Nordik"]},
    "portfolio_fit": {"score": 85, "similar_existing_products": [], "comment": "Mobidik surdurulebilir hatti core urunu olabilir."},
    "overall_score": 85, "priority_level": "yuksek",
    "strategic_note": "ALTIN urun adayi. Kapasite TAM, asıl iş: GRS sertifika basvurusu (3-6 ay). SASA + Korteks rPES teklifi al, GRS chain-of-custody sertifika basvur. Pilot: 2 ton x 100 m, 4-6 hafta. Capri Plus + Harry RE = ADO 2-urun ALTIN portfoy.",
}, "Sheer rPES, kapasite TAM. GRS sertifika basvurusu acik is — AB ihracat icin kritik.")

# 8) Pure White Tape — %100 PES vertical stripe boucle, 320 cm, 2 renk
patch("ado_goldkante_3302-pure-white-tape.json", {
    "_description": "Pure White Tape — vertical stripe boucle/loop texture, 320 cm (sinir yakin), 2 renk. Kapasite TAM ama boucle iplik ozel siparis.",
    "staubli_feasibility": {
        "score": 5, "frame_count_estimate": "4-6",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun (16 cm genislik)",
        "reed_density_estimate": "16-20 dent/cm (stripe + boucle texture)",
        "sizing_requirement": "Boucle iplik ozel hasil, warp tension hassasiyeti",
        "comment": "320 cm yakin sinir ama TAM (<=360). Vertical stripe dobby altkumesi TAM. PES boucle texture iplik ozel siparis (Korteks/SASA), MOQ ~500 kg.",
    },
    "arge_value": {"score": 75, "key_learnings": ["320 cm warp beam yonetimi (sinir yakin)", "Boucle texture iplik MOQ muzakere"],
                   "comment": "Wide-width + boucle iplik kombinasyonu, capacity gelistirme firsati."},
    "market_gap": {"score": 70, "comment": "Turkiye'de 320 cm wide boucle stripe yerel uretim yok. Pure White serisi AB kurumsal kanal guclu talep.",
                   "target_markets": ["AB (ofis/kurumsal)", "TR premium"]},
    "portfolio_fit": {"score": 80, "similar_existing_products": ["Pure White Pinstripe"], "comment": "Color Fields koleksiyonu ile birlikte sade premium portfoy."},
    "overall_score": 76, "priority_level": "orta",
    "strategic_note": "Kapasite TAM ama 320 cm sınır yakın — warp beam test gerekli. Boucle iplik Korteks/SASA teklif (MOQ ~500 kg). Pilot Pure White Pinstripe ile birlikte 2 ton x 150 m, 4-5 hafta. Color Fields alt hatti olabilir.",
}, "Vertical stripe boucle, 320 cm warp beam test gerek. Boucle iplik MOQ riski.")

# 9) Pure White Pinstripe — %90 PES + %10 Cot pinstripe slub, 320 cm
patch("ado_goldkante_3301-pure-white-pinstripe.json", {
    "_description": "Pure White Pinstripe — pinstripe + slub iplik (wild silk hissi), 320 cm, 2 renk. Kapasite TAM: plain altkumesi + slub iplik ozel siparis.",
    "staubli_feasibility": {
        "score": 5, "frame_count_estimate": "2-4",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun (14 cm)",
        "reed_density_estimate": "14-18 dent/cm",
        "sizing_requirement": "Slub iplik ozel hasil",
        "comment": "Kapasite TAM. Sade pinstripe Stabli icin basit (2-4 cerceve). 320 cm sinir yakin ama TAM. Slub iplik ozel siparis MOQ ~500 kg (Korteks/Yunsa).",
    },
    "arge_value": {"score": 80, "key_learnings": ["Slub iplik ozel tedariki", "Pinstripe wide-width yonetimi", "Wild silk hissi tekstil takdim"],
                   "comment": "Color Fields koleksiyonu icin sade premium temel; AB kurumsal kanal."},
    "market_gap": {"score": 80, "comment": "Türkiye'de slub iplikli pinstripe wide-width yerel uretim yok. AB kurumsal segment talep güçlü. ADO retail 55-85 EUR/m -> Mobidik 12-18 EUR/m.",
                   "target_markets": ["AB (ofis/kurumsal)", "TR premium"]},
    "portfolio_fit": {"score": 85, "similar_existing_products": ["Pure White Tape"], "comment": "Color Fields ankor urunu."},
    "overall_score": 81, "priority_level": "yuksek",
    "strategic_note": "Kapasite TAM. Slub iplik ozel siparis (Yünsa/Korteks MOQ ~500 kg). Pilot Pure White Tape ile beraber: 2 ton x 150 m, 4-5 hafta. ADO Color Fields ankor urunu — AB kurumsal kanal pitch ozelinde sunulabilir.",
}, "Pinstripe + slub iplik, kapasite TAM. Slub iplik MOQ darbogaz. Color Fields koleksiyon ankor.")

# 10) Drift FR — %100 PES (FR) stripe, 300 cm, 14 renk
patch("ado_goldkante_3610-drift-fr.json", {
    "_description": "Drift FR — FR PES stripe + effect yarn, 300 cm, 14 renk. Kapasite: PES FR iplik TAM (kategori); ama FR son urun sertifika sureci (B1, DIN 4102-1) Mobidik icin acik is.",
    "staubli_feasibility": {
        "score": 5, "frame_count_estimate": "2-6",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun (21 cm)",
        "reed_density_estimate": "16-20 dent/cm (stripe + effect)",
        "sizing_requirement": "FR PES ozel hasil",
        "comment": "Stabli kriterleri TAM: 300 cm <= 360, dobby stripe TAM, FR PES iplik kategori TAM (kapasite tablosu 'FR iplik genel TAM'). FR son urun sertifikasi ayrı sureç — Mobidik icin acik is.",
    },
    "arge_value": {"score": 75, "key_learnings": ["FR PES iplik tedariki + tedarikci sertifikasi", "B1 / DIN 4102-1 son urun sertifika basvuru sureci", "14 renk yonetimi"],
                   "comment": "FR segment AB kamusal/contract icin zorunlu; sertifika sureci ARGE acik is."},
    "market_gap": {"score": 75, "comment": "Türkiye'de B1 sertifikali yerel FR perde uretici nispeten az; AB ihracat icin guclu kanal. ADO retail 70-100 EUR/m.",
                   "target_markets": ["TR (kamusal/contract)", "AB (otel/hastane)", "GCC"]},
    "portfolio_fit": {"score": 80, "similar_existing_products": [], "comment": "Mobidik FR hatti acabilir — Drift FR ankor urunu olabilir."},
    "overall_score": 79, "priority_level": "yuksek",
    "strategic_note": "Kapasite TAM. ACIL: FR son urun sertifika sureci (B1, DIN 4102-1) basvurusu — sertifika 3-6 ay. Trevira CS PES iplik teklifi (Indorama, Toray Türkiye temsilci). Pilot: 3 notr ton x 100 m, 4-6 hafta. AB contract pazari kanal pitch ozel.",
}, "FR PES stripe, dokuma TAM. B1/DIN sertifika sureci kritik acik is — basvuru paralel.")


# === Etamine: 4 urun ===

# 11) Andria — Cotton/Linen/Viscose/PES broad-stripe + Maltinto artisanal
patch("etamine_19621-andria.json", {
    "_description": "Andria — Maltinto el-boyama artisanal, broad-striped woven, %68 Cot + %26 Lin + %5 Vis + %1 PES, 305 cm. Dokuma TAM ama Maltinto finishing replication zor.",
    "staubli_feasibility": {
        "score": 3, "frame_count_estimate": "4-8",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun (37 cm)",
        "reed_density_estimate": "16-20 dent/cm",
        "sizing_requirement": "Multi-fiber karisim warp tension",
        "comment": "Dokuma (broad-striped) Stabli TAM, ama Maltinto = el-boyama artisanal finishing (dokuma sonrasi), Mobidik replication kismi. Skor 3: dokuma yapilabilir, vintage patina yapilamaz.",
    },
    "arge_value": {"score": 60, "key_learnings": ["Multi-fiber karisim dokuma", "Plain version artisanal-suz uretim"],
                   "comment": "Maltinto fason zor — Mobidik icin replikasyon kismi."},
    "market_gap": {"score": 55, "comment": "Niche artisanal Turkiye'de fason calisan az. Plain version (Maltinto'suz) pilot mumkun ama orjinal estetik kaybediyor.",
                   "target_markets": ["TR (lux residential)", "AB (artisanal segment niche)"]},
    "portfolio_fit": {"score": 50, "similar_existing_products": [], "comment": "Mobidik portfoyune kismi uyum (artisanal segment dis)."},
    "overall_score": 55, "priority_level": "dusuk",
    "strategic_note": "DUSUK ONCELIK. Replication kismi: dokuma yapilabilir ama Maltinto el-boyama yatirim ister. Plain version pilot 3 ton x 60 m mumkun (Maltinto'suz), ama 'vintage patina' yok. Onerilen: pas gec, Etamine'nin Heure Bleue + Fil du Temps'a yogunlas.",
}, "Maltinto artisanal el-boyama dokuma sonrasi finishing — Stabli'de dokuma TAM, finishing replication kismi. Dusuk oncelik.")

# 12) Heure Bleue — %100 keten plain voile + digital gradient print
patch("etamine_19650-heure-bleue.json", {
    "_description": "Heure Bleue — %100 European Flax certified keten voile + digital gradient stripe baski, 300 cm. Kapasite TAM (plain keten); digital baski fason gerek.",
    "staubli_feasibility": {
        "score": 4, "frame_count_estimate": "2-4",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun (baski)",
        "reed_density_estimate": "12-16 dent/cm (voile)",
        "sizing_requirement": "Keten voile ozel hasil, sheer warp tension",
        "comment": "Dokuma Stabli TAM (plain voile keten, Melange Linen tipi). Asil iş: gradient digital baski + stone-wash finishing. Digital fabric printer ~80-150k EUR yatirim VEYA fason (Akin, Yunsa). Skor 4: dokuma kolay, baski ek yatirim/fason.",
    },
    "arge_value": {"score": 75, "key_learnings": ["European Flax sertifikasi (paralel EU Flax basvurusu)", "Gradient digital print yatirim/fason", "Stone-wash finishing"],
                   "comment": "Digital print kapasitesi Mobidik icin yeni teknik kategori — niş AB segment."},
    "market_gap": {"score": 70, "comment": "Türkiye'de European Flax + digital baski + perde kombinasyonu yok. AB print perdelik niş. Z+R retail 90-130 EUR/m -> Mobidik 25-40 EUR/m.",
                   "target_markets": ["AB (FR/DE residential)", "TR lux", "GCC otel"]},
    "portfolio_fit": {"score": 70, "similar_existing_products": ["Melange Linen"], "comment": "Keten voile + baski hatti acabilir."},
    "overall_score": 71, "priority_level": "orta",
    "strategic_note": "Kapasite TAM dokumada. Asil iş: digital baski yatirim (80-150k EUR) VEYA fason (Akin/Yunsa). Onerilen: fason stratejisi — 4 ton x 80 m pilot, 6-8 hafta. EU Flax + OEKO-TEX sertifika basvurusu Melange Linen ile birlikte paralel.",
}, "Plain keten voile + gradient baski. Dokuma TAM, baski fason/yatirim ek is.")

# 13) Blanc de Lin RE — %100 keten KNIT/ÖRME, 155 cm
patch("etamine_19635-blanc-de-lin-re.json", {
    "_description": "Blanc de Lin RE — KETEN ÖRME/KNIT (raşel makinesi), 155 cm dar. ATÖLYE DIŞI: Stabli armür DOKUMA tezgahi, örme yapamaz. Kapasite tablosu jakar YOK + örme bambaska kategori.",
    "staubli_feasibility": {
        "score": 1, "frame_count_estimate": "uygulanamaz",
        "warp_compatibility": "uygun_degil", "weft_compatibility": "uygun_degil", "repeat_size_compatibility": "uygun_degil",
        "reed_density_estimate": "uygulanamaz (örme)",
        "sizing_requirement": "Örme makinesi (Karl Mayer raşel)",
        "comment": "ATÖLYE DIŞI: Bu DOKUMA değil ÖRME ürünü. Stabli armür sadece dokuma yapar. Replication için Karl Mayer raşel makinesi ~100-200k EUR yatirim gerekir. Pazar gözlemi olarak rapor edilir, replication hedefi DEĞİL.",
    },
    "arge_value": {"score": 30, "key_learnings": ["Örme kategorisi pazar gözlemi", "European Flax + OEKO-TEX sertifika Etamine örnegi"],
                   "comment": "Replication hedefi değil — strateji disi."},
    "market_gap": {"score": 20, "comment": "Türkiye keten örme perdelik üreticisi yok; ama Mobidik'in is alani DOKUMA, örme kapsam disi.",
                   "target_markets": ["uygulanamaz (Mobidik kapsam disi)"]},
    "portfolio_fit": {"score": 0, "similar_existing_products": [], "comment": "Mobidik dokuma kapasitesinde örme replikasyon disi."},
    "overall_score": 13, "priority_level": "dusuk",
    "strategic_note": "STRATEJI DISI — replication hedefi değil. Mobidik DOKUMA tezgahi, örme kapsam disi. Bu urun pazar gozlemi olarak rapor edilir: Etamine artisanal koleksiyonunda örme kategori varligi tespit edildi. Yatirim secenegi (Karl Mayer raşel ~100-200k EUR) ARGE oncelik listesinde alt sira.",
}, "ÖRME/KNIT urunu, Stabli DOKUMA tezgahi yapamaz. Replication hedefi DEGIL — pazar gozlemi olarak rapor.")

# 14) Fil du Temps — %100 solution-dyed acrylic, crochet-inspired leno outdoor
patch("etamine_19649-fil-du-temps.json", {
    "_description": "Fil du Temps — solution-dyed acrylic crochet-inspired leno (gauzy outdoor), 297 cm. Kapasite: leno TAM, acrylic solution-dyed Aksa fason mumkun, outdoor finishing fason.",
    "staubli_feasibility": {
        "score": 4, "frame_count_estimate": "8-12",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun (crochet pattern)",
        "reed_density_estimate": "10-14 dent/cm (leno open)",
        "sizing_requirement": "Acrylic warp tension + outdoor finishing protocol",
        "comment": "Leno TAM (kapasite tablosu); width 297 ok. Solution-dyed acrylic iplik Aksa Türkiye uretici (fason teklif), outdoor finishing (water/UV/saltwater) ayri proses. Skor 4: dokuma TAM, ek finishing fason karmasik.",
    },
    "arge_value": {"score": 75, "key_learnings": ["Solution-dyed acrylic iplik tedariki (Aksa)", "Outdoor finishing fason (water-repellent + UV)", "Crochet-inspired leno programlama"],
                   "comment": "Niket + Alpaca Leno + Fil du Temps = 3-urun leno portfoyu (+ Loops yun/alpaka). Outdoor segment Etamine."},
    "market_gap": {"score": 65, "comment": "Türkiye outdoor acrylic perde yerel uretim sinirli. AB outdoor segment buyuyor. Etamine retail 100-150 EUR/m -> Mobidik 25-40 EUR/m.",
                   "target_markets": ["AB (DACH outdoor)", "TR otel terasi", "GCC"]},
    "portfolio_fit": {"score": 70, "similar_existing_products": ["Niket leno", "Alpaca Leno", "Capri Plus outdoor"], "comment": "Leno + outdoor kombinasyonu, Capri Plus ile birlikte outdoor hatti."},
    "overall_score": 72, "priority_level": "orta",
    "strategic_note": "Kapasite TAM dokumada (leno). Asil iş: (1) Aksa solution-dyed acrylic iplik teklif, (2) Outdoor finishing fason (water+UV+saltwater) tedarikci tespit, (3) Pilot: 2 ton x 60 m, 8-10 hafta. Leno portfoyu ROI hesabinda Niket + Alpaca Leno + Fil du Temps + Loops birlestir.",
}, "Solution-dyed acrylic leno outdoor. Leno + outdoor finishing kombinasyon, dokuma TAM. Capri Plus + leno hatti birlesimi.")


# === Travers: 1 urun ===

# 15) Garden Stripe — multi-fiber sheer pinstripe (parti03 raporu YOK, dashboard tek kaynak)
patch("travers_44187-garden-stripe.json", {
    "_description": "Garden Stripe — el-dokuma gorunumlu pinstripe, 4-bilesen iplik (66% Cot + 17% PES + 9% Lin + 8% Vis), 295 cm. Documents parti03 raporu YOK, dashboard tek kaynak. Kapasite TAM ama multi-fiber MOQ riski.",
    "staubli_feasibility": {
        "score": 5, "frame_count_estimate": "2-4",
        "warp_compatibility": "uygun", "weft_compatibility": "uygun", "repeat_size_compatibility": "uygun (2 cm pinstripe)",
        "reed_density_estimate": "14-18 dent/cm",
        "sizing_requirement": "Multi-fiber slub iplik warp tension hassasiyeti",
        "comment": "Kapasite TAM: plain pinstripe sheer + 4-bilesen iplik standart kategoriler. 295 cm <= 360. Basit pinstripe Stabli icin kolay (2-4 cerceve). El-dokuma gorunumlu slub iplik ozel siparis (Polaron, Yunsa fason).",
    },
    "arge_value": {"score": 75, "key_learnings": ["4-bilesen iplik MOQ yonetimi", "El-dokuma gorunumlu slub iplik tedariki", "Railroaded uygulama (yatay yon)"],
                   "comment": "Travers Amerikan dekoratif estetik benchmark; multi-fiber MOQ ana darbogaz."},
    "market_gap": {"score": 70, "comment": "Türkiye'de 4-bilesen el-dokuma gorunumlu sheer yerel uretim yok. Travers retail 70-100 EUR/m -> Mobidik 18-25 EUR/m.",
                   "target_markets": ["TR (residential)", "AB (DK/NL)", "ABD (uzun vade)"]},
    "portfolio_fit": {"score": 75, "similar_existing_products": [], "comment": "Mobidik multi-fiber sheer hatti ek urunu olabilir."},
    "overall_score": 76, "priority_level": "orta",
    "strategic_note": "Kapasite TAM. 4-bilesen slub iplik tedariki kritik: Polaron + Yunsa teklif (~500 kg MOQ). Pilot: 3 notr ton x 100 m, 4-6 hafta. Travers'in 'wallpaper coordinates' konseptini izleme — Mobidik icin uygun olabilir. Documents parti03 raporu YOK, bu denetim dashboard JS array tek kaynagi temel aldi.",
}, "Pinstripe sheer 4-bilesen iplik, kapasite TAM dokumada. Slub iplik MOQ darbogaz. Parti03 raporu yoktu, dashboard tek kaynaktan denetim.")


print()
print("=== Faz 3.4 detay denetim ozeti ===")
audited_files = sorted(URUNLER.glob("*.json"))
audited_count = 0
pending_count = 0
for jp in audited_files:
    with jp.open(encoding="utf-8") as f:
        d = json.load(f)
    if d["mobidik_evaluation"]["staubli_feasibility"]["score"] is not None:
        audited_count += 1
    else:
        pending_count += 1
print(f"Toplam {len(audited_files)} urun: audited {audited_count}, PENDING {pending_count}")
