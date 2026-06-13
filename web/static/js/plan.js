/**
 * tasarim-v2 Plan — Planlama alt-sekmesi.
 *
 * Parça 1: ⚙️ Kur & Rapor Ayarı, 0️⃣ Özet (readonly), 1️⃣ Boya Yöntemi.
 * Parça 2: 2️⃣ Çözgü Planı (düz/blanket, renk atama, iplik ihtiyacı kg).
 *
 * Hesap PAYLAŞIMI: çözgü g/mt teknik.js'den (window.TeknikCalc.cozguGmt) çağrılır —
 * plan.js'te formül KOPYALANMAZ. Renk şeridi window.IMAGE_COLORS warp[]'tan (salt-okuma).
 * Veri SÜRÜM-BAZLI: products.plan[surum_id]. Auto-save: 1500ms debounce → POST /api/urun/<id>/plan.
 * NOT: dirty izleme yalnız kullanıcı GİRDİLERİNE bakar; hesaplanan (tel adedi, iplik ihtiyacı)
 *      kayıt anında tazelenir ama teknik düzenlemesi tek başına plan'ı "kirli" yapmaz.
 */
(function () {
    "use strict";

    const URUN_ID = window.URUN_ID;
    if (!URUN_ID) return;

    const planSection = document.querySelector('[data-numune-section="plan"]');
    if (!planSection) return;

    // === DOM refs (Parça 1) ===
    const statusEl    = document.getElementById('plan-status');
    const raporParaEl = document.getElementById('plan-rapor-para');
    const usdInput    = document.getElementById('plan-kur-usd');
    const eurInput    = document.getElementById('plan-kur-eur');
    const kurInfoEl   = document.getElementById('plan-kur-info');
    const fetchBtn    = document.getElementById('plan-kur-fetch');
    const boyaCozguEl = document.getElementById('plan-boya-cozgu');
    const boyaAtkiEl  = document.getElementById('plan-boya-atki');
    const ozetEl      = document.getElementById('plan-ozet');
    const planTabBtn  = document.querySelector('.numune-tab[data-numune-tab="plan"]');

    // === DOM refs (Parça 2 — çözgü planı) ===
    const metrajInput    = document.getElementById('plan-cozgu-metraj');
    const telAdediEl     = document.getElementById('plan-cozgu-teladedi');
    const telDetailEl    = document.getElementById('plan-cozgu-tel-detail');
    const warpPaletteEl  = document.getElementById('plan-warp-palette');
    const warpHintEl     = document.getElementById('plan-cozgu-renk-hint');
    const warpManualColor= document.getElementById('plan-warp-color');
    const warpAddBtn     = document.getElementById('plan-warp-add');
    const warpSavePalChk = document.getElementById('plan-warp-savepalette');
    const cozguGruplarHost = document.getElementById('plan-cozgu-gruplar');
    const cozumYeriEl    = document.getElementById('plan-cozum-yeri');
    const cozumBedelWrap = document.getElementById('plan-cozum-bedel-wrap');
    const cozumBedelInput= document.getElementById('plan-cozum-bedel');
    const cozumParaEl    = document.getElementById('plan-cozum-para');
    const gecisTipEl     = document.getElementById('plan-gecis-tip');
    const gecisBedelInput= document.getElementById('plan-gecis-bedel');
    const gecisParaEl    = document.getElementById('plan-gecis-para');

    // === DOM refs (Parça 3 — atkı/varyant + top boya) ===
    const atkiBlock          = document.getElementById('plan-atki-block');
    const topBoyaBlock       = document.getElementById('plan-topboya-block');
    const varyantSayisiInput = document.getElementById('plan-varyant-sayisi');
    const varyantOneriEl     = document.getElementById('plan-varyant-oneri');
    const varsayilanMetreInput = document.getElementById('plan-varsayilan-metre');
    const metreUygulaBtn     = document.getElementById('plan-metre-uygula');
    const weftPaletteEl      = document.getElementById('plan-weft-palette');
    const weftManualColor    = document.getElementById('plan-weft-color');
    const weftAddBtn         = document.getElementById('plan-weft-add');
    const weftSavePalChk     = document.getElementById('plan-weft-savepalette');
    const weftTargetEl       = document.getElementById('plan-weft-target');
    const variantTableEl     = document.getElementById('plan-varyant-table');
    const atkiOzetEl         = document.getElementById('plan-atki-ozet');
    const ekruMetreInput     = document.getElementById('plan-ekru-metre');
    const ekruTuketimEl      = document.getElementById('plan-ekru-tuketim');
    const kazanKapInput      = document.getElementById('plan-kazan-kap');
    const faturaMinInput     = document.getElementById('plan-fatura-min');
    const kazanBedelInput    = document.getElementById('plan-kazan-bedel');
    const kazanParaEl        = document.getElementById('plan-kazan-para');
    const boyaPaletteEl      = document.getElementById('plan-boya-palette');
    const boyaManualColor    = document.getElementById('plan-boya-color');
    const boyaAddBtn         = document.getElementById('plan-boya-add');
    const boyaSavePalChk     = document.getElementById('plan-boya-savepalette');
    const boyaRenklerEl      = document.getElementById('plan-boya-renkler');
    const renkSayisiOutEl    = document.getElementById('plan-renk-sayisi');
    const toplamKazanBedelEl = document.getElementById('plan-toplam-kazan-bedel');

    // === DOM refs (Parça 4 — maliyet özeti + PDF) ===
    const maliyetBarEl     = document.getElementById('plan-maliyet-bar');
    const maliyetTableEl   = document.getElementById('plan-maliyet-table');
    const maliyetTotalEl   = document.getElementById('plan-maliyet-total');
    const maliyetKurNoteEl = document.getElementById('plan-maliyet-kurnote');
    const planPdfBtn       = document.getElementById('plan-pdf-btn');

    // === State ===
    const DEBOUNCE_MS = 1500;
    let PLAN_MAP = {};
    let activeSurumId = null;
    let fetchedAt = null;
    // tasarim-v2 — çözgü gruplar (alt/üst/üst_2). Her grup birden fazla bağımsız çözgüden oluşur;
    // her çözgü kendi tip + renk_sayisi + renk_atamalari'na sahip (örn. 1. çözgü düz mavi,
    // 2. çözgü blanket 2 renk, 3. çözgü düz beyaz — hepsi aynı grupta).
    const DURUMLAR = ['alt', 'ust', 'ust_2'];
    const DURUM_LABEL = { alt: 'Alt Çözgü', ust: 'Üst Çözgü', ust_2: 'Üst Çözgü 2' };
    // Her çözgü kendi metrajına sahip (null → grup üstündeki ortak/varsayılan metraj fallback).
    function emptyCozgu() { return { tip: 'duz', renk_sayisi: 1, renk_atamalari: [], metraj: null }; }
    function emptyGrup() { return { cozguler: [] }; }
    let cozguGruplar = { alt: emptyGrup(), ust: emptyGrup(), ust_2: emptyGrup() };
    let activeCozgu = { durum: 'alt', idx: 0 };   // renk şeridi/manuel ekleme bu çözgüye gider
    // Parça 3 — atkı/varyant + top boya state
    let varyantlar = [];          // [{ad, metre, renk_atamalari:[{iplik_ref,palet_renk_id,ad,hex}|null]}]
    let atkiMoq = {};             // {iplik_ref: kg}
    let activeCell = null;        // {vi, yi} — varyant tablosunda aktif renk hücresi
    let selectedWeft = null;      // {hex, ad} — son seçilen atkı rengi (≡ aynı renk için)
    let boyanacakRenkler = [];    // top boya: [{palet_renk_id, ad, hex}]
    let lastSavedSnapshot = null;
    let saveTimer = null, checkTimer = null, autoSaving = false, recalcRaf = null;

    try {
        const raw = document.getElementById('plan-data');
        PLAN_MAP = raw ? (JSON.parse(raw.textContent || '{}') || {}) : {};
        if (typeof PLAN_MAP !== 'object' || Array.isArray(PLAN_MAP)) PLAN_MAP = {};
    } catch (e) { PLAN_MAP = {}; }

    // === Genel yardımcılar ===
    async function api(method, url, body) {
        const opts = { method, headers: { 'Content-Type': 'application/json' } };
        if (body !== undefined) opts.body = JSON.stringify(body);
        const res = await fetch(url, opts);
        let data;
        try { data = await res.json(); } catch (e) { data = { ok: false, error: 'JSON parse hatası' }; }
        return data;
    }
    function setStatus(text, kind) {
        if (!statusEl) return;
        statusEl.textContent = text || '';
        statusEl.dataset.kind = kind || '';
    }
    function fmtDateTime(iso) {
        if (!iso) return '';
        try {
            const d = new Date(iso);
            if (isNaN(d)) return '';
            const p = n => String(n).padStart(2, '0');
            return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
        } catch (e) { return ''; }
    }
    function segVal(segEl, fallback) {
        const a = segEl && segEl.querySelector('.plan-seg-btn.is-active');
        return a ? a.dataset.val : fallback;
    }
    function setSeg(segEl, val) {
        if (!segEl) return;
        segEl.querySelectorAll('.plan-seg-btn').forEach(b => b.classList.toggle('is-active', b.dataset.val === val));
    }
    function numOrNull(inp) {
        const v = parseFloat(((inp && inp.value) || '').replace(',', '.'));
        return isNaN(v) ? null : v;
    }
    function toast(msg, type) { if (window.toast) window.toast(msg, type || 'info'); }
    function escapeHtml(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, m =>
            ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
    }
    function round3(x) { return Math.round(x * 1000) / 1000; }
    function fmtKg(kg) { return (kg == null || !isFinite(kg)) ? '—' : kg.toFixed(3); }
    function hexToRgbArr(hex) {
        const h = String(hex || '').replace('#', '');
        if (h.length !== 6) return null;
        return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
    }
    function colorName(hex) {
        const rgb = hexToRgbArr(hex);
        if (rgb && window.ColorPicker && typeof window.ColorPicker._nearestColorName === 'function') {
            try { const r = window.ColorPicker._nearestColorName(rgb[0], rgb[1], rgb[2]); if (r && r.name) return r.name; } catch (e) {}
        }
        return String(hex || '').toUpperCase();
    }
    function colorLab(hex) {
        const rgb = hexToRgbArr(hex);
        if (rgb && window.ColorPicker && typeof window.ColorPicker._rgbToLab === 'function') {
            try { return window.ColorPicker._rgbToLab(rgb[0], rgb[1], rgb[2]); } catch (e) {}
        }
        return null;
    }

    // === Slice (sürüm planı) ===
    function defaultSlice() {
        return {
            surum_id: activeSurumId,
            boya_yontemi: { cozgu: 'iplik_boya', atki: 'iplik_boya' },
            rapor_para_birimi: 'TL',
            kur_snapshot: { usd_try: null, eur_try: null, fetched_at: null },
            cozgu_plani: {}, atki_varyant_plani: {}, top_boya_plani: {},
        };
    }
    function currentSlice() {
        const s = PLAN_MAP[activeSurumId];
        return (s && typeof s === 'object' && !Array.isArray(s)) ? s : defaultSlice();
    }
    // includeComputed=false → yalnız kullanıcı girdileri (dirty izleme); true → hesaplananlar dahil (kayıt)
    function buildSlice(includeComputed) {
        return {
            surum_id: activeSurumId,
            boya_yontemi: { cozgu: segVal(boyaCozguEl, 'iplik_boya'), atki: segVal(boyaAtkiEl, 'iplik_boya') },
            rapor_para_birimi: segVal(raporParaEl, 'TL'),
            kur_snapshot: { usd_try: numOrNull(usdInput), eur_try: numOrNull(eurInput), fetched_at: fetchedAt },
            cozgu_plani: readCozguPlan(includeComputed),
            atki_varyant_plani: readAtkiPlan(includeComputed),
            top_boya_plani: readTopBoyaPlan(includeComputed),
            // Parça 4 — maliyet yalnız kayıtta (PDF için); dirty snapshot'ta yok (undefined → JSON'da atlanır)
            maliyet_ozeti: includeComputed ? computeMaliyet() : undefined,
        };
    }
    function readSlice() { return buildSlice(true); }
    function snapshot() { try { return JSON.stringify(buildSlice(false)); } catch (e) { return null; } }

    function render(slice) {
        setSeg(raporParaEl, slice.rapor_para_birimi || 'TL');
        const by = slice.boya_yontemi || {};
        setSeg(boyaCozguEl, by.cozgu || 'iplik_boya');
        setSeg(boyaAtkiEl, by.atki || 'iplik_boya');
        const ks = slice.kur_snapshot || {};
        if (usdInput) usdInput.value = (ks.usd_try != null ? ks.usd_try : '');
        if (eurInput) eurInput.value = (ks.eur_try != null ? ks.eur_try : '');
        fetchedAt = ks.fetched_at || null;
        updateKurInfo(null);
        renderCozgu(slice.cozgu_plani || {});
        renderAtki(slice.atki_varyant_plani || {});
        renderTopBoya(slice.top_boya_plani || {});
        updateAtkiTopVisibility();
        renderMaliyet();
    }
    function updateKurInfo(data) {
        if (!kurInfoEl) return;
        const lines = [];
        if (fetchedAt) {
            const tag = data && data.stale ? ' (önceki gün)' : (data && data.cached ? ' (cache)' : '');
            lines.push('Plan kuru: ' + fmtDateTime(fetchedAt) + tag);
        }
        // Plan'ın frozen kuru cache'ten farklıysa güncel TCMB'yi hint olarak göster
        const hint = lastKurHint;
        if (hint && (hint.usd_try != null || hint.eur_try != null)) {
            const planUsd = numOrNull(usdInput), planEur = numOrNull(eurInput);
            const diffUsd = hint.usd_try != null && planUsd != null && Math.abs(planUsd - hint.usd_try) > 0.0001;
            const diffEur = hint.eur_try != null && planEur != null && Math.abs(planEur - hint.eur_try) > 0.0001;
            if (diffUsd || diffEur || planUsd == null || planEur == null) {
                const parts = [];
                if (hint.usd_try != null) parts.push(`1 USD = ${hint.usd_try.toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 4})} TL`);
                if (hint.eur_try != null) parts.push(`1 EUR = ${hint.eur_try.toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 4})} TL`);
                lines.push('Güncel TCMB: ' + parts.join(' · '));
            }
        }
        kurInfoEl.innerHTML = lines.map(l => `<span>${escapeHtml(l)}</span>`).join('');
    }

    // === 0️⃣ Özet (readonly, teknik form DOM'undan) ===
    function setOzet(key, val) {
        const el = ozetEl && ozetEl.querySelector(`[data-ozet="${key}"]`);
        if (el) el.textContent = (val === '' || val == null) ? '—' : val;
    }
    function refreshOzet() {
        const dok = k => { const e = document.querySelector(`[data-dokuma-key="${k}"]`); return e ? e.value.trim() : ''; };
        setOzet('atki_sikligi', dok('atki_sikligi'));
        setOzet('ham_en_cm', dok('ham_en_cm'));
        setOzet('mamul_en_cm', dok('mamul_en_cm'));
        const cozguRows = document.querySelectorAll('[data-iplik-rows="cozgu"] .iplik-row');
        const atkiRows = document.querySelectorAll('[data-iplik-rows="atki"] .iplik-row');
        setOzet('cozgu_adet', cozguRows.length);
        setOzet('atki_adet', atkiRows.length);
        const sik = cozguSikligiToplam(readWarpYarns());
        setOzet('cozgu_sikligi', sik > 0 ? (Math.round(sik * 100) / 100) : '');
    }

    // ============================================================
    // 2️⃣ Çözgü Planı (Parça 2)
    // ============================================================

    // --- Teknik (aktif sürüm) çözgü verisini DOM'dan oku ---
    function readWarpYarns() {
        const rows = document.querySelectorAll('[data-iplik-rows="cozgu"] .iplik-row');
        const out = [];
        rows.forEach((r, i) => {
            const val = sel => { const e = r.querySelector(sel); return e ? e.value : ''; };
            const durum = val('[data-iplik-key="cozgu_durum"]') || 'alt';
            out.push({
                idx: i,                                    // global iplik index (maliyet için)
                tip: val('[data-iplik-key="tip"]') || 'DENYE',
                iplik: val('[data-iplik-key="iplik"]'),
                siklik: val('[data-iplik-key="siklik"]'),
                fiyat: val('[data-iplik-key="fiyat"]'),
                durum: DURUMLAR.indexOf(durum) >= 0 ? durum : 'alt',
            });
        });
        return out;
    }
    function hamEnCm() {
        const e = document.querySelector('[data-dokuma-key="ham_en_cm"]');
        const v = e ? parseFloat((e.value || '').replace(',', '.')) : NaN;
        return isFinite(v) ? v : null;
    }
    function cozguSikligiToplam(yarns) {
        return yarns.reduce((s, y) => {
            const v = parseFloat((y.siklik || '').replace(',', '.'));
            return s + (isFinite(v) ? v : 0);
        }, 0);
    }

    // --- Çözgü rolündeki palet renkleri (window.IMAGE_COLORS warp[], salt-okuma, hex dedup) ---
    function warpPalette() {
        const map = window.IMAGE_COLORS || {};
        const seen = new Set(), out = [];
        Object.keys(map).forEach(path => {
            const arr = (map[path] && map[path].colors && map[path].colors.warp) || [];
            (Array.isArray(arr) ? arr : []).forEach(c => {
                if (!c || !c.hex) return;
                const key = String(c.hex).toUpperCase();
                if (seen.has(key)) return;
                seen.add(key);
                out.push({ hex: c.hex, ad: c.name || c.hex });
            });
        });
        return out;
    }
    function activeCozguLabel() {
        const g = cozguGruplar[activeCozgu.durum];
        const n = (g && g.cozguler) ? g.cozguler.length : 0;
        return `${DURUM_LABEL[activeCozgu.durum]} · Çözgü ${activeCozgu.idx + 1}${n > 1 ? `/${n}` : ''}`;
    }
    function renderWarpPalette() {
        if (!warpPaletteEl) return;
        const pal = warpPalette();
        if (!pal.length) {
            warpPaletteEl.innerHTML = '';
            if (warpHintEl) warpHintEl.textContent = `— → ${activeCozguLabel()} · Galeri ▸ Renk Paleti'nden ata veya manuel ekle`;
            return;
        }
        if (warpHintEl) warpHintEl.textContent = `(tıkla → ${activeCozguLabel()})`;
        warpPaletteEl.innerHTML = pal.map(c =>
            `<button type="button" class="plan-swatch" data-hex="${escapeHtml(c.hex)}" data-name="${escapeHtml(c.ad)}" title="${escapeHtml(c.ad)} · ${escapeHtml(c.hex)}">` +
            `<span class="plan-swatch-sw" style="background:${escapeHtml(c.hex)}"></span>` +
            `<span class="plan-swatch-name">${escapeHtml(c.ad)}</span></button>`
        ).join('');
    }

    // Grup yardımcıları
    function activeDurumlar() {
        // Aktif gruplar = yarn'larda görünen distinct durumlar (sıralı: alt, ust, ust_2)
        const yarns = readWarpYarns();
        const set = new Set(yarns.map(y => y.durum));
        return DURUMLAR.filter(d => set.has(d));
    }
    function yarnsByDurum(yarns) {
        const m = { alt: [], ust: [], ust_2: [] };
        yarns.forEach(y => { (m[y.durum] || m.alt).push(y); });
        return m;
    }
    function groupRenkSayisi(g) {
        if (!g || g.tip !== 'blanket') return 1;
        const n = parseInt(g.renk_sayisi, 10);
        return (n >= 1 && n <= 4) ? n : 2;
    }

    function tableHtml(headers, rows) {
        const thead = '<tr>' + headers.map(h => `<th>${escapeHtml(h)}</th>`).join('') + '</tr>';
        const tbody = rows.map(r => '<tr>' + r.map((c, i) => `<td${i === 0 ? ' class="plan-td-ref"' : ''}>${escapeHtml(c)}</td>`).join('') + '</tr>').join('');
        return `<table class="plan-table"><thead>${thead}</thead><tbody>${tbody}</tbody></table>`;
    }

    // Tek grup hesabı — kg per yarn (yarn.idx ile maliyet için identifier korunur).
    // Düz: kg = gmt × metraj / 1000  ·  Blanket(n): her renk = gmt / n × metraj / 1000
    // Tek bir çözgü için detay (tip + renk_sayisi + atamalar → perYarn + flat).
    // metraj: çözgünün KENDİ metrajı kullanılır; boşsa defaultMetraj (grup üstü ortak alan) fallback.
    function computeOneCozgu(cozgu, yarns, hamEn, defaultMetraj, durum, ci) {
        const tip = cozgu.tip === 'blanket' ? 'blanket' : 'duz';
        const n = (tip === 'blanket')
            ? Math.max(1, Math.min(4, parseInt(cozgu.renk_sayisi, 10) || 2))
            : 1;
        const cm = parseFloat(cozgu && cozgu.metraj);
        const metraj = (isFinite(cm) && cm > 0) ? cm : defaultMetraj;
        const calc = window.TeknikCalc;
        const ready = yarns.length > 0 && metraj != null && metraj > 0 && hamEn != null;
        const perYarn = yarns.map(y => {
            const ref = ((y.iplik || '').trim() ? `${y.iplik} ${y.tip}` : (y.tip || '—'));
            const gmt = (calc && typeof calc.cozguGmt === 'function') ? calc.cozguGmt(y, hamEn) : null;
            const cols = (tip === 'duz') ? 1 : n;
            const perColor = []; let total = null;
            if (ready && gmt != null) {
                total = gmt * metraj / 1000;
                for (let i = 0; i < cols; i++) perColor.push(tip === 'duz' ? total : (gmt / n * metraj / 1000));
            } else {
                for (let i = 0; i < cols; i++) perColor.push(null);
            }
            return { idx: y.idx, ref, gmt, perColor, total };
        });
        const flat = [];
        perYarn.forEach(yr => {
            if (tip === 'duz') {
                const a = cozgu.renk_atamalari && cozgu.renk_atamalari[0];
                flat.push({ iplik_idx: yr.idx, iplik_ref: yr.ref, durum, cozgu_idx: ci, renk: (a && a.ad) || null, kg: yr.perColor[0] == null ? null : round3(yr.perColor[0]) });
            } else {
                for (let i = 0; i < n; i++) {
                    const a = cozgu.renk_atamalari && cozgu.renk_atamalari[i];
                    flat.push({ iplik_idx: yr.idx, iplik_ref: yr.ref, durum, cozgu_idx: ci, renk: a ? a.ad : `Renk ${i + 1}`, kg: yr.perColor[i] == null ? null : round3(yr.perColor[i]) });
                }
            }
        });
        return { tip, n, perYarn, flat, ready, metraj };
    }
    function computeCozguGroup(durum, yarns, hamEn, metraj) {
        const g = cozguGruplar[durum] || emptyGrup();
        const cozguler = Array.isArray(g.cozguler) ? g.cozguler : [];
        const sikToplam = cozguSikligiToplam(yarns);
        const teladediTek = (hamEn != null && sikToplam > 0) ? Math.round(sikToplam * hamEn) : null;
        // Her çözgü ayrı bir çözüm operasyonu → kendi flat'i, kendi tel adedi (×N grup toplamı)
        const cozguResults = cozguler.map((c, ci) => {
            const detay = computeOneCozgu(c, yarns, hamEn, metraj, durum, ci);
            detay.teladedi = teladediTek;          // tek çözgüde teladedi sabit
            return detay;
        });
        const teladediGrup = (teladediTek != null && cozguler.length > 0) ? teladediTek * cozguler.length : null;
        const flatAll = []; cozguResults.forEach(c => flatAll.push(...c.flat));
        return { yarns, cozguler: cozguResults, teladedi: teladediGrup, flat: flatAll, cozgu_sayisi: cozguler.length };
    }
    // Tüm aktif gruplar için aggregate
    function computeCozgu() {
        const yarns = readWarpYarns();
        const hamEn = hamEnCm();
        const metraj = numOrNull(metrajInput);
        const byD = yarnsByDurum(yarns);
        const durumlar = activeDurumlar();
        const groups = {};
        let teladediToplam = 0, anyTel = false;
        const flat = [];
        durumlar.forEach(d => {
            const comp = computeCozguGroup(d, byD[d], hamEn, metraj);
            groups[d] = comp;
            if (comp.teladedi != null) { teladediToplam += comp.teladedi; anyTel = true; }
            flat.push(...comp.flat);
        });
        return { yarns, durumlar, groups, teladedi: anyTel ? teladediToplam : null, metraj, flat };
    }

    // --- Grup + her çözgü için sub-block render ---
    function grupHeaderHtml(durum, comp) {
        const yarnCount = (comp.yarns || []).length;
        const cozguSayisi = comp.cozgu_sayisi || (comp.cozguler ? comp.cozguler.length : 0);
        const tel = (comp.teladedi != null) ? String(comp.teladedi) : '—';
        const draftBadge = cozguSayisi > 1 ? ` · <b class="plan-grup-mult">${cozguSayisi} çözgü</b>` : '';
        return `<div class="plan-grup-head" data-grup-head="${durum}">` +
            `<b>${escapeHtml(DURUM_LABEL[durum])}</b> ` +
            `<em>${yarnCount} iplik · ${tel} tel${draftBadge}</em>` +
            `<button type="button" class="btn-mini plan-cozgu-add" data-grup-cozgu-add="${durum}" title="Bu gruba yeni bir çözgü ekle (kendi tipi + renkleri)">+ Çözgü Ekle</button>` +
            `</div>`;
    }
    function cozguCardHtml(durum, ci, cozgu, cozguDetay) {
        const tip = (cozgu.tip === 'blanket') ? 'blanket' : 'duz';
        const n = (tip === 'blanket')
            ? Math.max(1, Math.min(4, parseInt(cozgu.renk_sayisi, 10) || 2))
            : 1;
        const isActive = (activeCozgu.durum === durum && activeCozgu.idx === ci);
        const grupCozguCount = ((cozguGruplar[durum] || {}).cozguler || []).length;
        let html = `<div class="plan-cozgu-card${isActive ? ' is-active' : ''}" data-cozgu-card="${durum}:${ci}">`;
        // Header: "Çözgü 1/3 · Düz" + aktif rozet + sil butonu
        html += `<div class="plan-cozgu-card-head">` +
            `<b>Çözgü ${ci + 1}${grupCozguCount > 1 ? ` / ${grupCozguCount}` : ''}</b> ` +
            `<em>· ${tip === 'blanket' ? `Blanket ${n} renk` : 'Düz'}${isActive ? ' · ● aktif' : ''}</em>` +
            (grupCozguCount > 1 ? `<button type="button" class="plan-cozgu-del-btn" data-grup-cozgu-del="${durum}:${ci}" title="Bu çözgüyü kaldır">×</button>` : '') +
            `</div>`;
        // Tip + renk sayısı controls
        html += '<div class="plan-grup-controls">';
        html += `<label class="plan-field"><span>Tip</span>` +
            `<span class="plan-seg" data-grup-cozgu-tip="${durum}:${ci}" role="group">` +
            `<button type="button" class="plan-seg-btn ${tip === 'duz' ? 'is-active' : ''}" data-val="duz">Düz</button>` +
            `<button type="button" class="plan-seg-btn ${tip === 'blanket' ? 'is-active' : ''}" data-val="blanket">Blanket</button>` +
            `</span></label>`;
        if (tip === 'blanket') {
            html += `<label class="plan-field"><span>Renk sayısı</span>` +
                `<span class="plan-seg" data-grup-cozgu-renksayisi="${durum}:${ci}" role="group">`;
            [2, 3, 4].forEach(k => {
                html += `<button type="button" class="plan-seg-btn ${n === k ? 'is-active' : ''}" data-val="${k}">${k}</button>`;
            });
            html += `</span></label>`;
        }
        // Bu çözgünün KENDİ metrajı (boş → grup üstündeki varsayılan metraj placeholder olarak gösterilir)
        const defMet = numOrNull(metrajInput);
        const metVal = (cozgu.metraj != null && cozgu.metraj !== '') ? cozgu.metraj : '';
        html += `<label class="plan-field plan-cozgu-metraj-field"><span>Metraj <em>(m)</em></span>` +
            `<input type="number" step="1" min="0" class="plan-input plan-cozgu-metraj-input" ` +
            `data-grup-cozgu-metraj="${durum}:${ci}" value="${escapeHtml(String(metVal))}" ` +
            `placeholder="${defMet != null ? escapeHtml(String(defMet)) : '0'}"></label>`;
        html += '</div>';
        // Atanmış renkler
        const slots = (tip === 'duz') ? 1 : n;
        let chips = '';
        for (let i = 0; i < slots; i++) {
            const a = cozgu.renk_atamalari && cozgu.renk_atamalari[i];
            if (a) {
                chips += `<span class="plan-assigned-chip">` +
                    `<span class="plan-swatch-sw" style="background:${escapeHtml(a.hex)}"></span>` +
                    `<span class="plan-swatch-name">${escapeHtml(a.ad || a.hex)}</span>` +
                    `<button type="button" class="plan-assigned-del" data-grup-cozgu-del-renk="${durum}:${ci}:${i}" title="Kaldır" aria-label="Kaldır">×</button></span>`;
            } else {
                chips += `<span class="plan-assigned-chip is-empty">Renk ${i + 1}: boş</span>`;
            }
        }
        html += `<div class="plan-warp-assigned">${chips}</div>`;
        // Blanket önizleme
        if (tip === 'blanket') {
            let bands = '';
            for (let i = 0; i < n; i++) {
                const a = cozgu.renk_atamalari && cozgu.renk_atamalari[i];
                const col = a ? a.hex : 'var(--bg-elev)';
                bands += `<span class="plan-band" style="background:${escapeHtml(col)};width:${(100 / n).toFixed(4)}%" title="${a ? escapeHtml(a.ad) : 'boş'}"></span>`;
            }
            html += `<div class="plan-blanket-preview">${bands}</div>`;
        }
        // İhtiyaç tablosu
        html += '<div class="plan-cozgu-ihtiyac">' + cozguIhtiyacHtml(cozgu, cozguDetay) + '</div>';
        html += `</div>`;
        return html;
    }
    function cozguIhtiyacHtml(cozgu, detay) {
        if (!detay || !detay.perYarn || !detay.perYarn.length) return '<p class="plan-empty">Bu grupta çözgü ipliği yok.</p>';
        if (!detay.ready) return '<p class="plan-empty">Metraj ve ham en girilince iplik ihtiyacı hesaplanır.</p>';
        if (detay.tip === 'duz') {
            const a = cozgu.renk_atamalari && cozgu.renk_atamalari[0];
            const head = 'kg' + (a ? ` · ${a.ad}` : '');
            return tableHtml(['İplik', head], detay.perYarn.map(yr => [yr.ref, fmtKg(yr.perColor[0])]));
        }
        const headers = ['İplik'];
        for (let i = 0; i < detay.n; i++) { const a = cozgu.renk_atamalari && cozgu.renk_atamalari[i]; headers.push(a ? a.ad : `Renk ${i + 1}`); }
        headers.push('Toplam');
        const rows = detay.perYarn.map(yr => {
            const cells = [yr.ref];
            for (let i = 0; i < detay.n; i++) cells.push(fmtKg(yr.perColor[i]));
            cells.push(fmtKg(yr.total));
            return cells;
        });
        return tableHtml(headers, rows);
    }
    function grupBodyHtml(durum, comp) {
        const g = cozguGruplar[durum] || emptyGrup();
        const cozguler = Array.isArray(g.cozguler) ? g.cozguler : [];
        let html = '<div class="plan-grup-body">';
        if (!cozguler.length) {
            html += '<p class="plan-empty">Henüz çözgü eklenmedi. "+ Çözgü Ekle" butonuyla başlayın.</p>';
        } else {
            cozguler.forEach((c, ci) => {
                const detay = (comp.cozguler && comp.cozguler[ci]) || { perYarn: [], ready: false, tip: 'duz', n: 1 };
                html += cozguCardHtml(durum, ci, c, detay);
            });
        }
        html += '</div>';
        return html;
    }
    function renderCozguGroups() {
        if (!cozguGruplarHost) return;
        const compAll = computeCozgu();
        if (!compAll.durumlar.length) {
            cozguGruplarHost.innerHTML = '<p class="plan-empty">Teknik analizde çözgü ipliği yok.</p>';
            return;
        }
        // Her aktif grupta en az 1 çözgü olsun (UX: kullanıcı yarn ekledikten sonra otomatik 1 çözgü hazır)
        compAll.durumlar.forEach(d => {
            const g = cozguGruplar[d] || (cozguGruplar[d] = emptyGrup());
            if (!Array.isArray(g.cozguler)) g.cozguler = [];
            if (g.cozguler.length === 0) g.cozguler.push(emptyCozgu());
        });
        // Aktif grup yarn listesinden düşmüşse default'a çek
        if (!compAll.durumlar.includes(activeCozgu.durum)) {
            activeCozgu = { durum: compAll.durumlar[0], idx: 0 };
        }
        // Aktif çözgü idx grup için geçerli mi?
        const ag = cozguGruplar[activeCozgu.durum];
        const acN = (ag && ag.cozguler) ? ag.cozguler.length : 0;
        if (activeCozgu.idx >= acN) activeCozgu.idx = Math.max(0, acN - 1);
        // Aktif grup değiştiyse compAll'i tekrar hesapla (yeni cozguler eklenmiş olabilir)
        const compAfterEnsure = computeCozgu();
        cozguGruplarHost.innerHTML = compAfterEnsure.durumlar.map(d => {
            const isActiveGrup = (d === activeCozgu.durum) ? ' is-active' : '';
            return `<fieldset class="plan-grup${isActiveGrup}" data-grup="${d}">` + grupHeaderHtml(d, compAfterEnsure.groups[d]) + grupBodyHtml(d, compAfterEnsure.groups[d]) + `</fieldset>`;
        }).join('');
        // Toplam tel readout + detay (yeni cozguler eklenmiş olabilir → compAfterEnsure kullan)
        if (telAdediEl) telAdediEl.textContent = (compAfterEnsure.teladedi != null ? String(compAfterEnsure.teladedi) : '—');
        if (telDetailEl) {
            telDetailEl.textContent = (compAfterEnsure.durumlar.length > 1)
                ? compAfterEnsure.durumlar.map(d => `${DURUM_LABEL[d].toLowerCase()}: ${compAfterEnsure.groups[d].teladedi != null ? compAfterEnsure.groups[d].teladedi : '—'}`).join(' · ')
                : '';
        }
    }
    function scheduleRecalc() {
        if (recalcRaf) cancelAnimationFrame(recalcRaf);
        recalcRaf = requestAnimationFrame(() => { recalcRaf = null; renderCozguGroups(); });
    }
    // Tek bir çözgü kartının ihtiyaç tablosunu yerinde güncelle (metraj input'unda her tuş vuruşunda
    // full re-render yapılsa focus kaybolur → sadece o kartın .plan-cozgu-ihtiyac içeriğini değiştir).
    function patchCozguIhtiyac(durum, ci) {
        if (!cozguGruplarHost) return;
        const g = cozguGruplar[durum];
        const c = (g && Array.isArray(g.cozguler)) ? g.cozguler[ci] : null;
        if (!c) return;
        const byD = yarnsByDurum(readWarpYarns());
        const detay = computeOneCozgu(c, byD[durum] || [], hamEnCm(), numOrNull(metrajInput), durum, ci);
        const card = cozguGruplarHost.querySelector('[data-cozgu-card="' + durum + ':' + ci + '"]');
        if (!card) return;
        const host = card.querySelector('.plan-cozgu-ihtiyac');
        if (host) host.innerHTML = cozguIhtiyacHtml(c, detay);
    }

    function assignColor(color) {
        const { durum, idx: cIdx } = activeCozgu;
        const g = cozguGruplar[durum] || (cozguGruplar[durum] = emptyGrup());
        if (!Array.isArray(g.cozguler)) g.cozguler = [];
        if (!g.cozguler[cIdx]) g.cozguler[cIdx] = emptyCozgu();
        const c = g.cozguler[cIdx];
        const tip = c.tip === 'blanket' ? 'blanket' : 'duz';
        const n = (tip === 'blanket')
            ? Math.max(1, Math.min(4, parseInt(c.renk_sayisi, 10) || 2))
            : 1;
        if (!Array.isArray(c.renk_atamalari)) c.renk_atamalari = [];
        let slot = -1;
        for (let i = 0; i < n; i++) { if (!c.renk_atamalari[i]) { slot = i; break; } }
        if (slot === -1) {
            if (n === 1) slot = 0;
            else { toast(`${activeCozguLabel()} tüm renk slotları dolu — birini kaldırın`, 'warn'); return; }
        }
        c.renk_atamalari[slot] = { palet_renk_id: color.palet_renk_id || null, ad: color.ad || color.hex, hex: color.hex };
        renderCozguGroups(); scheduleDirtyCheck();
    }

    function readCozguPlan(includeComputed) {
        const cozumYeri = segVal(cozumYeriEl, 'devoretex');
        const compAll = includeComputed ? computeCozgu() : null;
        const gruplar = {};
        // Yarn'larda görünen durumları kaydet; tek alt grup varsa sadece o yazılır
        const durumlar = activeDurumlar();
        durumlar.forEach(d => {
            const g = cozguGruplar[d] || emptyGrup();
            const cozguler = Array.isArray(g.cozguler) ? g.cozguler : [];
            const compGrup = compAll && compAll.groups[d];
            const serializedCozguler = cozguler.map((c, ci) => {
                const tip = c.tip === 'blanket' ? 'blanket' : 'duz';
                const n = (tip === 'blanket')
                    ? Math.max(1, Math.min(4, parseInt(c.renk_sayisi, 10) || 2))
                    : 1;
                const cm = parseFloat(c.metraj);
                const sc = {
                    tip,
                    renk_sayisi: n,
                    renk_atamalari: (c.renk_atamalari || []).slice(0, n).map(a => a ? { palet_renk_id: a.palet_renk_id || null, ad: a.ad, hex: a.hex } : null),
                    metraj: (isFinite(cm) && cm >= 0) ? cm : null,
                };
                if (includeComputed && compGrup && compGrup.cozguler && compGrup.cozguler[ci]) {
                    const det = compGrup.cozguler[ci];
                    sc.toplam_tel_adedi = det.teladedi;
                    sc.iplik_ihtiyaci = det.flat;
                    sc.metraj_efektif = det.metraj;   // fallback dahil efektif metraj (PDF gösterir)
                }
                return sc;
            });
            const grup = { cozguler: serializedCozguler };
            if (includeComputed && compGrup) {
                grup.toplam_tel_adedi = compGrup.teladedi;       // grup toplamı (×cozgu sayısı)
                grup.iplik_ihtiyaci = compGrup.flat;             // grup flat (tüm çözgüler birleşik)
                grup.cozgu_sayisi = cozguler.length;
            }
            gruplar[d] = grup;
        });
        const base = {
            gruplar,
            metraj_m: numOrNull(metrajInput),
            cozum_yeri: cozumYeri,
            cozum_bedeli: cozumYeri === 'fason' ? (numOrNull(cozumBedelInput) || 0) : 0,
            cozum_para_birimi: segVal(cozumParaEl, 'TL'),
            gecis: segVal(gecisTipEl, 'tahar'),
            gecis_bedeli: numOrNull(gecisBedelInput) || 0,
            gecis_para_birimi: segVal(gecisParaEl, 'TL'),
        };
        if (includeComputed && compAll) {
            base.toplam_tel_adedi = compAll.teladedi;
            base.iplik_ihtiyaci = compAll.flat;
        }
        return base;
    }
    function updateCozguVisibility() {
        if (cozumBedelWrap) cozumBedelWrap.hidden = (segVal(cozumYeriEl, 'devoretex') !== 'fason');
    }
    // Bir grubun raw kaydını {cozguler: [...]} şemasına migrate eder (geriye dönük uyum).
    function migrateGrupSrc(src) {
        if (!src || typeof src !== 'object') return { cozguler: [] };
        // Yeni şema (cozguler array zaten var) — düzleştir + validate
        if (Array.isArray(src.cozguler)) {
            const cozguler = src.cozguler.map(c => {
                const tip = c && c.tip === 'blanket' ? 'blanket' : 'duz';
                let n = parseInt(c && c.renk_sayisi, 10);
                if (!(n >= 1 && n <= 4)) n = (tip === 'blanket' ? 2 : 1);
                const cm = parseFloat(c && c.metraj);
                return {
                    tip, renk_sayisi: n,
                    renk_atamalari: Array.isArray(c && c.renk_atamalari)
                        ? c.renk_atamalari.map(a => a ? { palet_renk_id: a.palet_renk_id || null, ad: a.ad || a.hex, hex: a.hex } : null)
                        : [],
                    metraj: (isFinite(cm) && cm >= 0) ? cm : null,
                };
            });
            return { cozguler };
        }
        // Eski şema (tip + renk_sayisi + renk_atamalari [+ cozgu_adedi multiplier])
        if (src.tip || src.renk_atamalari) {
            const tip = src.tip === 'blanket' ? 'blanket' : 'duz';
            let n = parseInt(src.renk_sayisi, 10);
            if (!(n >= 1 && n <= 4)) n = (tip === 'blanket' ? 2 : 1);
            const base = {
                tip, renk_sayisi: n,
                renk_atamalari: Array.isArray(src.renk_atamalari)
                    ? src.renk_atamalari.map(a => a ? { palet_renk_id: a.palet_renk_id || null, ad: a.ad || a.hex, hex: a.hex } : null)
                    : [],
            };
            // cozgu_adedi N varsa, N kopya çıkar (eski multiplier semantic'i koru)
            const adedi = Math.max(1, Math.min(10, parseInt(src.cozgu_adedi, 10) || 1));
            const cozguler = [];
            for (let i = 0; i < adedi; i++) {
                cozguler.push({ tip: base.tip, renk_sayisi: base.renk_sayisi, renk_atamalari: base.renk_atamalari.slice(), metraj: null });
            }
            return { cozguler };
        }
        return { cozguler: [] };
    }
    function renderCozgu(plan) {
        plan = (plan && typeof plan === 'object') ? plan : {};
        // Geriye dönük migration: en eski düz şema → gruplar.alt
        let gruplar = plan.gruplar;
        if (!gruplar && (plan.tip || plan.renk_atamalari)) {
            gruplar = { alt: { tip: plan.tip || 'duz', renk_sayisi: plan.renk_sayisi || 1, renk_atamalari: plan.renk_atamalari || [], cozgu_adedi: plan.cozgu_adedi } };
        }
        gruplar = gruplar || {};
        DURUMLAR.forEach(d => { cozguGruplar[d] = migrateGrupSrc(gruplar[d]); });
        // Ortak alanlar
        if (metrajInput) metrajInput.value = (plan.metraj_m != null ? plan.metraj_m : '');
        const cozumYeri = plan.cozum_yeri === 'fason' ? 'fason' : 'devoretex';
        setSeg(cozumYeriEl, cozumYeri);
        if (cozumBedelInput) cozumBedelInput.value = (plan.cozum_bedeli ? plan.cozum_bedeli : '');
        setSeg(cozumParaEl, plan.cozum_para_birimi || 'TL');
        setSeg(gecisTipEl, plan.gecis === 'isbag' ? 'isbag' : 'tahar');
        if (gecisBedelInput) gecisBedelInput.value = (plan.gecis_bedeli ? plan.gecis_bedeli : '');
        setSeg(gecisParaEl, plan.gecis_para_birimi || 'TL');
        // İlk render: aktif çözgü = ilk aktif durumun ilk çözgüsü
        const durumlar = activeDurumlar();
        if (!durumlar.includes(activeCozgu.durum)) activeCozgu = { durum: durumlar[0] || 'alt', idx: 0 };
        updateCozguVisibility();
        renderWarpPalette();
        renderCozguGroups();
    }
    // Teknik (sürüm) değerleri değişince renk şeridi + tablolar tazelensin (kullanıcı seçimine dokunma)
    function refreshCozguFromTeknik() {
        renderWarpPalette();
        renderCozguGroups();
    }

    function onWarpAdd() {
        const raw = ((warpManualColor && warpManualColor.value) || '').replace('#', '');
        if (!/^[0-9a-fA-F]{6}$/.test(raw)) return;
        const hex = '#' + raw.toLowerCase();
        const color = { palet_renk_id: null, ad: colorName(hex), hex: hex };
        assignColor(color);
        if (warpSavePalChk && warpSavePalChk.checked) saveColorToPalette(color);
    }
    async function saveColorToPalette(color, role) {
        role = role || 'warp';
        let path = null;
        try { path = window.cpCurrentImagePath && window.cpCurrentImagePath(); } catch (e) { path = null; }
        if (!path) { const keys = Object.keys(window.IMAGE_COLORS || {}); path = keys.length ? keys[0] : null; }
        if (!path) { toast('Palete kaydetmek için renk-atama görseli yok', 'warn'); return; }
        const map = window.IMAGE_COLORS || {};
        const existing = ((map[path] && map[path].colors && map[path].colors[role]) || []).slice();
        if (existing.some(c => c && String(c.hex).toUpperCase() === color.hex.toUpperCase())) { toast('Renk zaten palette var', 'info'); return; }
        existing.push({ hex: color.hex, name: color.ad, rgb: hexToRgbArr(color.hex), lab: colorLab(color.hex) });
        try {
            const data = await api('POST', `/api/urun/${encodeURIComponent(URUN_ID)}/gorsel-renk`, { path: path, colors: { [role]: existing } });
            if (data && data.ok) {
                if (map[path]) map[path].colors = data.image_colors || map[path].colors;
                renderWarpPalette();
                renderWeftStrips();
                toast('Renk palete kaydedildi', 'success');
            } else { toast((data && data.error) || 'Palete kaydedilemedi', 'error'); }
        } catch (e) { toast('Palete kaydedilemedi', 'error'); }
    }

    // ============================================================
    // 3️⃣ Atkı & Varyant + 4️⃣ Top Boya (Parça 3)
    // Hesap: window.TeknikCalc.atkiGmt (teknik.js paylaşımı). Renkler IMAGE_COLORS.weft (salt-okuma).
    // ============================================================

    function readAtkiYarns() {
        const rows = document.querySelectorAll('[data-iplik-rows="atki"] .iplik-row');
        const out = [];
        rows.forEach(r => {
            const val = sel => { const e = r.querySelector(sel); return e ? e.value : ''; };
            out.push({
                tip: val('[data-iplik-key="tip"]') || 'DENYE',
                iplik: val('[data-iplik-key="iplik"]'),
                siklik: val('[data-iplik-key="siklik"]'),
                fiyat: val('[data-iplik-key="fiyat"]'),
            });
        });
        return out;
    }
    function atkiYarnRef(y, i) {
        return ((y && (y.iplik || '').trim()) ? `${y.iplik} ${y.tip}` : ((y && y.tip) || `İplik ${i + 1}`));
    }

    // --- Atkı (weft) palet — IMAGE_COLORS.weft, hex dedup ---
    function weftPalette() {
        const map = window.IMAGE_COLORS || {};
        const seen = new Set(), out = [];
        Object.keys(map).forEach(path => {
            const arr = (map[path] && map[path].colors && map[path].colors.weft) || [];
            (Array.isArray(arr) ? arr : []).forEach(c => {
                if (!c || !c.hex) return;
                const key = String(c.hex).toUpperCase();
                if (seen.has(key)) return;
                seen.add(key);
                out.push({ hex: c.hex, ad: c.name || c.hex });
            });
        });
        return out;
    }
    function weftStripHtml() {
        const pal = weftPalette();
        if (!pal.length) return '<span class="plan-empty">Galeri ▸ Renk Paleti\'nden atkı renkleri atayın ya da manuel ekleyin</span>';
        return pal.map(c =>
            `<button type="button" class="plan-swatch" data-hex="${escapeHtml(c.hex)}" data-name="${escapeHtml(c.ad)}" title="${escapeHtml(c.ad)} · ${escapeHtml(c.hex)}">` +
            `<span class="plan-swatch-sw" style="background:${escapeHtml(c.hex)}"></span>` +
            `<span class="plan-swatch-name">${escapeHtml(c.ad)}</span></button>`
        ).join('');
    }
    function renderWeftStrips() {
        const html = weftStripHtml();
        if (weftPaletteEl) weftPaletteEl.innerHTML = html;
        if (boyaPaletteEl) boyaPaletteEl.innerHTML = html;
    }

    // --- Varyant state yönetimi ---
    function reconcileColors(yc) {
        varyantlar.forEach(v => {
            if (!Array.isArray(v.renk_atamalari)) v.renk_atamalari = [];
            while (v.renk_atamalari.length < yc) v.renk_atamalari.push(null);
            if (v.renk_atamalari.length > yc) v.renk_atamalari.length = yc;
        });
    }
    function setVaryantCount(n) {
        n = Math.max(0, n || 0);
        const yc = readAtkiYarns().length;
        while (varyantlar.length < n) {
            const i = varyantlar.length;
            varyantlar.push({ ad: 'Varyant ' + (i + 1), metre: numOrNull(varsayilanMetreInput), renk_atamalari: new Array(yc).fill(null) });
        }
        if (varyantlar.length > n) varyantlar.length = n;
    }

    function computeAtki() {
        const yarns = readAtkiYarns();
        const hamEn = hamEnCm();
        const calc = window.TeknikCalc;
        const yc = yarns.length;
        const gmt = yarns.map(y => (calc && typeof calc.atkiGmt === 'function') ? calc.atkiGmt(y, hamEn) : null);
        const toplamMetre = varyantlar.reduce((s, v) => s + (parseFloat(v.metre) || 0), 0);
        const varyantKg = varyantlar.map(v => {
            const m = parseFloat(v.metre) || 0;
            if (!(m > 0)) return null;
            let sum = 0, any = false;
            for (let j = 0; j < yc; j++) { if (gmt[j] != null) { sum += gmt[j] * m / 1000; any = true; } }
            return any ? sum : null;
        });
        const iplikOzet = yarns.map((y, j) => {
            const moq = parseFloat(atkiMoq[j]);
            const moqV = (isFinite(moq) && moq > 0) ? moq : null;
            // MOQ HER VARYANT/RENK için ayrı lot (iplik boya = renk başına ayrı boyama):
            //   alım = Σ max(MOQ, varyant_tüketimi) ; artakalan = Σ max(0, MOQ − varyant_tüketimi)
            let tuketim = 0, alim = 0, artakalan = 0, lot = 0;
            varyantlar.forEach(v => {
                const m = parseFloat(v.metre) || 0;
                if (gmt[j] != null && m > 0) {
                    const t = gmt[j] * m / 1000;                       // bu varyantta bu ipliğin tüketimi
                    tuketim += t;
                    alim += (moqV != null && moqV > t) ? moqV : t;     // o renk lotunda alınan
                    artakalan += Math.max(0, (moqV != null ? moqV : 0) - t);
                    lot++;
                }
            });
            return {
                iplik_ref: j, ref: atkiYarnRef(y, j),
                tuketim_kg: lot ? round3(tuketim) : null,
                moq_kg: moqV,
                alim_kg: lot ? round3(alim) : null,
                artakalan_kg: lot ? round3(artakalan) : null,
                lot_sayisi: lot,
            };
        });
        return { yarns, yc, gmt, toplamMetre, varyantKg, iplikOzet };
    }

    function renderVariantTable() {
        if (!variantTableEl) return;
        const yarns = readAtkiYarns();
        const yc = yarns.length;
        if (!yc) { variantTableEl.innerHTML = '<p class="plan-empty">Teknik analizde atkı ipliği yok.</p>'; return; }
        reconcileColors(yc);
        const comp = computeAtki();
        let html = '<table class="plan-table plan-varyant-table"><thead><tr><th>Varyant</th><th>Metre</th>';
        for (let j = 0; j < yc; j++) html += `<th>${escapeHtml(atkiYarnRef(yarns[j], j))}</th>`;
        html += '<th>kg</th><th></th></tr></thead><tbody>';
        varyantlar.forEach((v, vi) => {
            html += `<tr data-vi="${vi}">`;
            html += `<td class="plan-td-ref"><input type="text" class="plan-vinput plan-vad" data-vi="${vi}" value="${escapeHtml(v.ad || ('Varyant ' + (vi + 1)))}"></td>`;
            html += `<td><input type="number" min="0" step="1" class="plan-vinput plan-vmetre" data-vi="${vi}" value="${v.metre != null ? v.metre : ''}"></td>`;
            for (let j = 0; j < yc; j++) {
                const a = v.renk_atamalari[j];
                html += `<td class="plan-cell-color" data-vi="${vi}" data-yi="${j}" title="${a ? escapeHtml(a.ad) : 'renk seç'}">` +
                    (a ? `<span class="plan-swatch-sw" style="background:${escapeHtml(a.hex)}"></span><span class="plan-cell-name">${escapeHtml(a.ad)}</span>` : '<span class="plan-cell-empty">—</span>') +
                    '</td>';
            }
            html += `<td class="plan-vkg" data-vi="${vi}">${fmtKg(comp.varyantKg[vi])}</td>`;
            html += `<td><button type="button" class="plan-row-apply" data-vi="${vi}" title="Seçili rengi tüm ipliklere uygula">≡</button></td>`;
            html += '</tr>';
        });
        html += '</tbody></table>';
        variantTableEl.innerHTML = html;
        markActiveCell();
    }
    function renderAtkiOzet() {
        if (!atkiOzetEl) return;
        const comp = computeAtki();
        if (!comp.yc) { atkiOzetEl.innerHTML = ''; return; }
        let html = '<table class="plan-table plan-atki-ozet-table"><thead><tr><th>İplik</th><th>Tüketim kg</th><th>MOQ kg/renk</th><th>Alım kg</th><th>Artakalan kg</th></tr></thead><tbody>';
        comp.iplikOzet.forEach(o => {
            html += `<tr data-yi="${o.iplik_ref}">` +
                `<td class="plan-td-ref">${escapeHtml(o.ref)}</td>` +
                `<td class="plan-tuketim">${fmtKg(o.tuketim_kg)}</td>` +
                `<td><input type="number" min="0" step="0.1" class="plan-moq-input" data-yi="${o.iplik_ref}" value="${o.moq_kg != null ? o.moq_kg : ''}"></td>` +
                `<td class="plan-alim">${fmtKg(o.alim_kg)}</td>` +
                `<td class="plan-artakalan">${fmtKg(o.artakalan_kg)}</td></tr>`;
        });
        html += '</tbody></table>';
        atkiOzetEl.innerHTML = html;
    }

    // --- Varyant etkileşim ---
    function markActiveCell() {
        if (!variantTableEl) return;
        variantTableEl.querySelectorAll('.plan-cell-color.is-active').forEach(c => c.classList.remove('is-active'));
        if (activeCell) {
            const c = variantTableEl.querySelector(`.plan-cell-color[data-vi="${activeCell.vi}"][data-yi="${activeCell.yi}"]`);
            if (c) c.classList.add('is-active');
        }
    }
    function updateWeftTargetLabel() {
        if (!weftTargetEl) return;
        if (activeCell && varyantlar[activeCell.vi]) {
            const yarns = readAtkiYarns();
            const yref = yarns[activeCell.yi] ? atkiYarnRef(yarns[activeCell.yi], activeCell.yi) : `İplik ${activeCell.yi + 1}`;
            weftTargetEl.textContent = `→ ${varyantlar[activeCell.vi].ad || ('Varyant ' + (activeCell.vi + 1))} · ${yref}`;
        } else weftTargetEl.textContent = 'Bir renk hücresi seçin';
    }
    function updateColorCell(vi, yi) {
        const cell = variantTableEl && variantTableEl.querySelector(`.plan-cell-color[data-vi="${vi}"][data-yi="${yi}"]`);
        if (!cell) return;
        const a = varyantlar[vi] && varyantlar[vi].renk_atamalari[yi];
        cell.innerHTML = a ? `<span class="plan-swatch-sw" style="background:${escapeHtml(a.hex)}"></span><span class="plan-cell-name">${escapeHtml(a.ad)}</span>` : '<span class="plan-cell-empty">—</span>';
        cell.title = a ? a.ad : 'renk seç';
    }
    function updateVariantKg(vi) {
        const comp = computeAtki();
        const kgCell = variantTableEl && variantTableEl.querySelector(`.plan-vkg[data-vi="${vi}"]`);
        if (kgCell) kgCell.textContent = fmtKg(comp.varyantKg[vi]);
        renderAtkiOzet();
    }
    function advanceActiveCell() {
        if (!activeCell) return;
        const yc = readAtkiYarns().length;
        let vi = activeCell.vi, yi = activeCell.yi + 1;
        if (yi >= yc) { yi = 0; vi++; }
        if (vi >= varyantlar.length) { activeCell = null; } else { activeCell = { vi, yi }; }
        markActiveCell(); updateWeftTargetLabel();
    }
    function assignWeftToActive(color) {
        if (!activeCell) { toast('Önce bir renk hücresi seçin', 'warn'); return; }
        const v = varyantlar[activeCell.vi];
        if (!v) return;
        v.renk_atamalari[activeCell.yi] = { iplik_ref: activeCell.yi, palet_renk_id: color.palet_renk_id || null, ad: color.ad || color.hex, hex: color.hex };
        selectedWeft = { hex: color.hex, ad: color.ad || color.hex };
        updateColorCell(activeCell.vi, activeCell.yi);
        updateVariantKg(activeCell.vi);
        advanceActiveCell();
        scheduleDirtyCheck();
    }
    function applySameColor(vi) {
        if (!selectedWeft) { toast('Önce şeritten bir renk seçin', 'warn'); return; }
        const v = varyantlar[vi]; if (!v) return;
        const yc = readAtkiYarns().length;
        for (let j = 0; j < yc; j++) {
            v.renk_atamalari[j] = { iplik_ref: j, palet_renk_id: null, ad: selectedWeft.ad, hex: selectedWeft.hex };
            updateColorCell(vi, j);
        }
        updateVariantKg(vi);
        scheduleDirtyCheck();
    }
    function onWeftStripClick(e) {
        const b = e.target.closest('.plan-swatch'); if (!b) return;
        const color = { palet_renk_id: null, ad: b.dataset.name || b.dataset.hex, hex: b.dataset.hex };
        selectedWeft = { hex: color.hex, ad: color.ad };
        assignWeftToActive(color);
    }
    function onWeftAdd() {
        const raw = ((weftManualColor && weftManualColor.value) || '').replace('#', '');
        if (!/^[0-9a-fA-F]{6}$/.test(raw)) return;
        const hex = '#' + raw.toLowerCase();
        const color = { palet_renk_id: null, ad: colorName(hex), hex: hex };
        selectedWeft = { hex: color.hex, ad: color.ad };
        assignWeftToActive(color);
        if (weftSavePalChk && weftSavePalChk.checked) saveColorToPalette(color, 'weft');
    }
    function onMoqInput(e) {
        const inp = e.target.closest('.plan-moq-input'); if (!inp) return;
        const yi = parseInt(inp.dataset.yi, 10);
        atkiMoq[yi] = inp.value;
        const comp = computeAtki();
        const o = comp.iplikOzet[yi];
        const row = inp.closest('tr');
        if (row && o) {
            const al = row.querySelector('.plan-alim'); if (al) al.textContent = fmtKg(o.alim_kg);
            const ar = row.querySelector('.plan-artakalan'); if (ar) ar.textContent = fmtKg(o.artakalan_kg);
        }
        scheduleDirtyCheck();
    }
    function onVMetreInput(e) {
        const inp = e.target.closest('.plan-vmetre'); if (!inp) return;
        const vi = parseInt(inp.dataset.vi, 10);
        if (varyantlar[vi]) varyantlar[vi].metre = (inp.value === '' ? null : parseFloat(inp.value));
        updateVariantKg(vi);   // kg + özet
        scheduleDirtyCheck();
    }
    function onVAdInput(e) {
        const inp = e.target.closest('.plan-vad'); if (!inp) return;
        const vi = parseInt(inp.dataset.vi, 10);
        if (varyantlar[vi]) varyantlar[vi].ad = inp.value;
        scheduleDirtyCheck();
    }
    function applyDefaultMetre() {
        const m = numOrNull(varsayilanMetreInput);
        varyantlar.forEach(v => { v.metre = m; });
        renderVariantTable(); renderAtkiOzet(); scheduleDirtyCheck();
    }

    function readAtkiPlan(includeComputed) {
        const base = {
            varyant_sayisi: varyantlar.length,
            varsayilan_metre: numOrNull(varsayilanMetreInput),
            varyantlar: varyantlar.map(v => ({
                ad: v.ad || '',
                metre: v.metre != null ? v.metre : null,
                renk_atamalari: (v.renk_atamalari || []).map(a => a ? { iplik_ref: a.iplik_ref, palet_renk_id: a.palet_renk_id || null, ad: a.ad, hex: a.hex } : null),
            })),
            moq: {},
        };
        Object.keys(atkiMoq).forEach(k => { const v = parseFloat(atkiMoq[k]); if (isFinite(v) && v > 0) base.moq[k] = v; });
        if (includeComputed) {
            const comp = computeAtki();
            base.iplik_ozet = comp.iplikOzet;
            base.varyantlar.forEach((v, i) => { v.kg = (comp.varyantKg[i] != null) ? round3(comp.varyantKg[i]) : null; });  // PDF için varyant kg
        }
        return base;
    }
    function renderAtki(plan) {
        plan = (plan && typeof plan === 'object') ? plan : {};
        varyantlar = Array.isArray(plan.varyantlar) ? plan.varyantlar.map(v => ({
            ad: (v && v.ad) || '',
            metre: (v && v.metre != null) ? v.metre : null,
            renk_atamalari: Array.isArray(v && v.renk_atamalari)
                ? v.renk_atamalari.map(a => a ? { iplik_ref: a.iplik_ref, palet_renk_id: a.palet_renk_id || null, ad: a.ad || a.hex, hex: a.hex } : null) : [],
        })) : [];
        atkiMoq = (plan.moq && typeof plan.moq === 'object') ? Object.assign({}, plan.moq) : {};
        if (varsayilanMetreInput) varsayilanMetreInput.value = (plan.varsayilan_metre != null ? plan.varsayilan_metre : '');
        if (!varyantlar.length) setVaryantCount(1);   // taze plan: 1 varyant ile başla
        if (varyantSayisiInput) varyantSayisiInput.value = String(varyantlar.length);
        activeCell = null; selectedWeft = null;
        if (varyantOneriEl) {
            const n = (typeof window.PLAN_IMG_COUNT === 'number' && window.PLAN_IMG_COUNT > 0)
                ? window.PLAN_IMG_COUNT : Object.keys(window.IMAGE_COLORS || {}).length;
            varyantOneriEl.textContent = n > 0 ? `Öneri: ${n}` : '';
        }
        renderWeftStrips();
        renderVariantTable();
        renderAtkiOzet();
        updateWeftTargetLabel();
    }

    // --- Top Boya ---
    function computeTopBoya() {
        const yarns = readAtkiYarns();
        const hamEn = hamEnCm();
        const calc = window.TeknikCalc;
        const ekru = numOrNull(ekruMetreInput);
        const tuketim = yarns.map((y, j) => {
            const g = (calc && typeof calc.atkiGmt === 'function') ? calc.atkiGmt(y, hamEn) : null;
            const kg = (g != null && ekru != null && ekru > 0) ? g * ekru / 1000 : null;
            return { iplik_ref: j, ref: atkiYarnRef(y, j), kg: kg == null ? null : round3(kg) };
        });
        const renkSayisi = boyanacakRenkler.length;
        const kazanBedel = numOrNull(kazanBedelInput) || 0;
        return { yarns, tuketim, renkSayisi, toplam: round3(renkSayisi * kazanBedel) };
    }
    function renderEkruTuketim() {
        if (!ekruTuketimEl) return;
        const comp = computeTopBoya();
        if (!comp.yarns.length) { ekruTuketimEl.innerHTML = '<p class="plan-empty">Teknik analizde atkı ipliği yok.</p>'; return; }
        const ekru = numOrNull(ekruMetreInput);
        if (ekru == null || ekru <= 0) { ekruTuketimEl.innerHTML = '<p class="plan-empty">Ekru metresi girilince iplik tüketimi hesaplanır.</p>'; return; }
        ekruTuketimEl.innerHTML = tableHtml(['İplik', 'kg'], comp.tuketim.map(t => [t.ref, fmtKg(t.kg)]));
    }
    function renderBoyaRenkler() {
        if (boyaRenklerEl) {
            boyaRenklerEl.innerHTML = boyanacakRenkler.length
                ? boyanacakRenkler.map((c, i) => `<span class="plan-assigned-chip"><span class="plan-swatch-sw" style="background:${escapeHtml(c.hex)}"></span><span class="plan-swatch-name">${escapeHtml(c.ad || c.hex)}</span><button type="button" class="plan-assigned-del" data-bdel="${i}" title="Kaldır" aria-label="Kaldır">×</button></span>`).join('')
                : '<span class="plan-assigned-chip is-empty">Boyanacak renk eklenmedi</span>';
        }
        const comp = computeTopBoya();
        if (renkSayisiOutEl) renkSayisiOutEl.textContent = String(comp.renkSayisi);
        if (toplamKazanBedelEl) toplamKazanBedelEl.textContent = comp.toplam ? comp.toplam.toFixed(2) : '0';
    }
    function addBoyaRenk(color) {
        if (boyanacakRenkler.some(c => String(c.hex).toUpperCase() === String(color.hex).toUpperCase())) { toast('Renk zaten ekli', 'info'); return; }
        boyanacakRenkler.push({ palet_renk_id: color.palet_renk_id || null, ad: color.ad || color.hex, hex: color.hex });
        renderBoyaRenkler(); scheduleDirtyCheck();
    }
    function onBoyaStripClick(e) {
        const b = e.target.closest('.plan-swatch'); if (!b) return;
        addBoyaRenk({ palet_renk_id: null, ad: b.dataset.name || b.dataset.hex, hex: b.dataset.hex });
    }
    function onBoyaAdd() {
        const raw = ((boyaManualColor && boyaManualColor.value) || '').replace('#', '');
        if (!/^[0-9a-fA-F]{6}$/.test(raw)) return;
        const hex = '#' + raw.toLowerCase();
        const color = { palet_renk_id: null, ad: colorName(hex), hex: hex };
        addBoyaRenk(color);
        if (boyaSavePalChk && boyaSavePalChk.checked) saveColorToPalette(color, 'weft');
    }
    function readTopBoyaPlan(includeComputed) {
        const base = {
            ekru_metre: numOrNull(ekruMetreInput),
            boyahane_profili: {
                kazan_kapasitesi_kg: numOrNull(kazanKapInput),
                faturalanan_min_kg: numOrNull(faturaMinInput),
                kazan_bedeli: numOrNull(kazanBedelInput),
                para_birimi: segVal(kazanParaEl, 'TL'),
            },
            boyanacak_renkler: boyanacakRenkler.map(c => ({ palet_renk_id: c.palet_renk_id || null, ad: c.ad, hex: c.hex })),
        };
        if (includeComputed) {
            const comp = computeTopBoya();
            base.renk_sayisi = comp.renkSayisi;
            base.toplam_kazan_bedeli = comp.toplam;
            base.iplik_tuketimi = comp.tuketim;
        }
        return base;
    }
    function renderTopBoya(plan) {
        plan = (plan && typeof plan === 'object') ? plan : {};
        if (ekruMetreInput) ekruMetreInput.value = (plan.ekru_metre != null ? plan.ekru_metre : '');
        const bp = plan.boyahane_profili || {};
        if (kazanKapInput) kazanKapInput.value = (bp.kazan_kapasitesi_kg != null ? bp.kazan_kapasitesi_kg : '');
        if (faturaMinInput) faturaMinInput.value = (bp.faturalanan_min_kg != null ? bp.faturalanan_min_kg : '');
        if (kazanBedelInput) kazanBedelInput.value = (bp.kazan_bedeli != null ? bp.kazan_bedeli : '');
        setSeg(kazanParaEl, bp.para_birimi || 'TL');
        boyanacakRenkler = Array.isArray(plan.boyanacak_renkler)
            ? plan.boyanacak_renkler.map(c => ({ palet_renk_id: c.palet_renk_id || null, ad: c.ad || c.hex, hex: c.hex })) : [];
        renderWeftStrips();
        renderEkruTuketim();
        renderBoyaRenkler();
    }

    function updateAtkiTopVisibility() {
        const m = segVal(boyaAtkiEl, 'iplik_boya');
        if (atkiBlock) atkiBlock.hidden = (m !== 'iplik_boya');
        if (topBoyaBlock) topBoyaBlock.hidden = (m !== 'top_boya');
    }
    // Teknik (sürüm) değişince atkı tarafını tazele (kullanıcı seçimine dokunma)
    function refreshAtkiFromTeknik() {
        renderWeftStrips();
        renderVariantTable();
        renderAtkiOzet();
        renderEkruTuketim();
        renderBoyaRenkler();
    }

    // ============================================================
    // 5️⃣ Toplam Proje Maliyeti Özeti (Parça 4)
    // Tüm bedeller kendi biriminde → kur_snapshot ile TL normalize → rapor birimi.
    // İplik kg'leri window.TeknikCalc paylaşımıyla; canlı /api/kur YOK.
    // ============================================================
    function rateToTL(b, usd, eur) {
        return b === 'TL' ? 1 : b === 'USD' ? (usd > 0 ? usd : null) : b === 'EUR' ? (eur > 0 ? eur : null) : null;
    }
    function money(n) {
        return (n == null || !isFinite(n)) ? '—' : n.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    function _parseFiyat(v) { const f = parseFloat(String(v == null ? '' : v).replace(',', '.')); return isFinite(f) ? f : null; }

    function computeMaliyet() {
        const usd = numOrNull(usdInput), eur = numOrNull(eurInput);
        const rapor = segVal(raporParaEl, 'TL');
        const hamEn = hamEnCm();
        const metraj = numOrNull(metrajInput);
        const atkiMode = segVal(boyaAtkiEl, 'iplik_boya');
        const calc = window.TeknikCalc;
        const kalemler = [];

        // 1) Çözgü iplik alımı — grup-bazlı (alt/üst/üst_2 ayrı tip/blanket olabilir)
        //    Her yarn'ın kg'si grubunun düz/blanket tipine göre hesaplanır (computeCozgu().flat).
        //    Yarn başına tüm renklerdeki kg toplanır → tüm gruplar için tek kalem altında alt-satır.
        (function () {
            const yarns = readWarpYarns();
            const compCozgu = computeCozgu();   // flat: [{iplik_idx, durum, kg, ...}]
            const yarnKgMap = new Map();
            compCozgu.flat.forEach(it => {
                if (it.kg == null) return;
                yarnKgMap.set(it.iplik_idx, (yarnKgMap.get(it.iplik_idx) || 0) + it.kg);
            });
            const alt_ = []; let toplam = 0;
            yarns.forEach(y => {
                const kg = yarnKgMap.get(y.idx);
                if (kg == null || kg <= 0) return;
                const fiyat = _parseFiyat(y.fiyat);
                const tutar = (fiyat != null && fiyat > 0) ? kg * fiyat : null;
                if (tutar != null) toplam += tutar;
                const baseRef = ((y.iplik || '').trim() ? `${y.iplik} ${y.tip}` : (y.tip || '—'));
                const ref = `${baseRef} (${y.durum === 'ust_2' ? 'üst 2' : (y.durum === 'ust' ? 'üst' : 'alt')})`;
                alt_.push({ ref, kg: round3(kg), fiyat, tutar: tutar != null ? round3(tutar) : null });
            });
            const durumSayisi = compCozgu.durumlar.length;
            const aciklama = durumSayisi > 1 ? `${alt_.length} iplik · ${durumSayisi} grup · tüketim` : `${alt_.length} iplik · tüketim`;
            kalemler.push({ key: 'cozgu_iplik', ad: 'Çözgü iplik alımı', aciklama, alt_satirlar: alt_, orijinal_deger: round3(toplam), orijinal_birim: 'USD' });
        })();

        // 2) Atkı iplik alımı — iplik boya: MOQ alım · top boya: ekru tüketim
        (function () {
            const yarns = readAtkiYarns(); const alt = []; let toplam = 0;
            if (atkiMode === 'top_boya') {
                computeTopBoya().tuketim.forEach((t, j) => {
                    const fiyat = _parseFiyat((yarns[j] || {}).fiyat);
                    const tutar = (t.kg != null && fiyat != null && fiyat > 0) ? t.kg * fiyat : null;
                    if (tutar != null) toplam += tutar;
                    if (t.kg != null) alt.push({ ref: t.ref, kg: t.kg, fiyat: fiyat, tutar: tutar != null ? round3(tutar) : null });
                });
                kalemler.push({ key: 'atki_iplik', ad: 'Atkı iplik (ekru)', aciklama: `${alt.length} iplik · ekru tüketim`, alt_satirlar: alt, orijinal_deger: round3(toplam), orijinal_birim: 'USD' });
            } else {
                computeAtki().iplikOzet.forEach((o, j) => {
                    const fiyat = _parseFiyat((yarns[j] || {}).fiyat);
                    const tutar = (o.alim_kg != null && fiyat != null && fiyat > 0) ? o.alim_kg * fiyat : null;
                    if (tutar != null) toplam += tutar;
                    if (o.alim_kg != null) alt.push({ ref: o.ref, kg: o.alim_kg, fiyat: fiyat, tutar: tutar != null ? round3(tutar) : null });
                });
                kalemler.push({ key: 'atki_iplik', ad: 'Atkı iplik alımı (MOQ)', aciklama: `${alt.length} iplik · MOQ alım`, alt_satirlar: alt, orijinal_deger: round3(toplam), orijinal_birim: 'USD' });
            }
        })();

        // 3) Çözgü çözüm bedeli (Devoretex=0 / Fason)
        (function () {
            const yer = segVal(cozumYeriEl, 'devoretex');
            kalemler.push({ key: 'cozgu_cozum', ad: 'Çözgü çözüm bedeli', aciklama: yer === 'fason' ? 'Fason' : 'Devoretex (dahili)', orijinal_deger: yer === 'fason' ? (numOrNull(cozumBedelInput) || 0) : 0, orijinal_birim: segVal(cozumParaEl, 'TL') });
        })();

        // 4) Tahar/İşbağ geçiş bedeli
        (function () {
            const tip = segVal(gecisTipEl, 'tahar');
            kalemler.push({ key: 'gecis', ad: 'Geçiş bedeli', aciklama: tip === 'isbag' ? 'İşbağ' : 'Tahar', orijinal_deger: numOrNull(gecisBedelInput) || 0, orijinal_birim: segVal(gecisParaEl, 'TL') });
        })();

        // 5) Top boya kazan bedeli (yalnız atki=top_boya)
        if (atkiMode === 'top_boya') {
            const comp = computeTopBoya();
            kalemler.push({ key: 'top_boya_kazan', ad: 'Top boya kazan bedeli', aciklama: `${comp.renkSayisi} renk × kazan`, orijinal_deger: comp.toplam || 0, orijinal_birim: segVal(kazanParaEl, 'TL') });
        }

        // Çevrim: TL normalize → rapor
        const raporRate = rateToTL(rapor, usd, eur);
        let toplam_tl = 0, eksik = false;
        kalemler.forEach(k => {
            const rate = rateToTL(k.orijinal_birim, usd, eur);
            if (rate != null) {
                k.deger_tl = k.orijinal_deger * rate;
                toplam_tl += k.deger_tl;
                k.rapor_deger = (raporRate != null) ? round3(k.deger_tl / raporRate) : null;
                k.kur_gerekli = false;
            } else {
                k.deger_tl = null; k.rapor_deger = null;
                k.kur_gerekli = (k.orijinal_deger > 0);
                if (k.kur_gerekli) eksik = true;
            }
        });
        return {
            rapor_para_birimi: rapor, usd_try: usd, eur_try: eur, fetched_at: fetchedAt,
            kalemler,
            toplam_tl: round3(toplam_tl),
            toplam_rapor: (raporRate != null) ? round3(toplam_tl / raporRate) : null,
            toplam_usd: (usd > 0) ? round3(toplam_tl / usd) : null,
            toplam_eur: (eur > 0) ? round3(toplam_tl / eur) : null,
            eksik_kur: eksik,
        };
    }

    // tasarim-v2 Faz 5 — maliyet çubuğu grafik paleti Stüdyo chart token'larına çekildi (kontrastlı 5).
    const MALIYET_RENK = { cozgu_iplik: '#5253c8', atki_iplik: '#9a9bdc', cozgu_cozum: '#0f857c', gecis: '#b98a3e', top_boya_kazan: '#c2657e' };
    function renderMaliyet() {
        if (!maliyetTableEl && !maliyetTotalEl) return;
        const m = computeMaliyet();
        const rapor = m.rapor_para_birimi;
        if (maliyetTableEl) {
            const rows = m.kalemler.map(k => {
                const orij = `${money(k.orijinal_deger)} ${escapeHtml(k.orijinal_birim)}`;
                const rap = k.kur_gerekli ? '<span class="plan-kur-gerekli">⚠ kur gerekli</span>' : (k.rapor_deger != null ? `${money(k.rapor_deger)} ${escapeHtml(rapor)}` : '—');
                let sub = '';
                if (k.alt_satirlar && k.alt_satirlar.length) {
                    sub = '<div class="plan-kalem-alt">' + k.alt_satirlar.map(a =>
                        `<span>${escapeHtml(a.ref)}: ${fmtKg(a.kg)} kg × ${a.fiyat != null ? money(a.fiyat) : '—'} $ = ${a.tutar != null ? money(a.tutar) : '—'} $</span>`).join('') + '</div>';
                }
                return `<tr><td class="plan-td-ref">${escapeHtml(k.ad)}${sub}</td><td>${escapeHtml(k.aciklama || '')}</td><td>${orij}</td><td>${rap}</td></tr>`;
            }).join('');
            maliyetTableEl.innerHTML = `<table class="plan-table"><thead><tr><th>Kalem</th><th>Açıklama</th><th>Orijinal</th><th>Rapor (${escapeHtml(rapor)})</th></tr></thead><tbody>${rows}</tbody></table>`;
        }
        if (maliyetBarEl) {
            const segs = m.kalemler.filter(k => k.deger_tl != null && k.deger_tl > 0);
            const tot = segs.reduce((s, k) => s + k.deger_tl, 0);
            maliyetBarEl.innerHTML = (tot > 0) ? segs.map(k =>
                `<span class="plan-bar-seg" style="width:${(k.deger_tl / tot * 100).toFixed(2)}%;background:${MALIYET_RENK[k.key] || '#888'}" title="${escapeHtml(k.ad)}: ${money(k.deger_tl)} TL"></span>`).join('') : '';
        }
        if (maliyetTotalEl) {
            const big = (m.toplam_rapor != null) ? `${money(m.toplam_rapor)} ${escapeHtml(rapor)}` : '—';
            maliyetTotalEl.innerHTML =
                `<div class="plan-total-big">GENEL TOPLAM <b>${big}</b></div>` +
                `<div class="plan-total-trio"><span>${money(m.toplam_tl)} TL</span><span>${m.toplam_eur != null ? money(m.toplam_eur) + ' EUR' : '— EUR'}</span><span>${m.toplam_usd != null ? money(m.toplam_usd) + ' USD' : '— USD'}</span></div>`;
        }
        if (maliyetKurNoteEl) {
            const parts = [];
            if (m.usd_try) parts.push(`1 USD = ${money(m.usd_try)} TL`);
            if (m.eur_try) parts.push(`1 EUR = ${money(m.eur_try)} TL`);
            let note = parts.length ? ('Kur: ' + parts.join(' · ')) : 'Kur girilmemiş — ⚙️ Kur & Rapor Ayarı bloğundan girin/çekin';
            if (m.fetched_at) { const t = fmtDateTime(m.fetched_at); if (t) note += ' · ' + t; }
            if (m.eksik_kur) note += ' · ⚠ bazı kalemler kur gerektiriyor';
            maliyetKurNoteEl.textContent = note;
        }
    }

    // === Auto-save ===
    function isDirty() {
        const s = snapshot();
        return s !== null && lastSavedSnapshot !== null && s !== lastSavedSnapshot;
    }
    function scheduleDirtyCheck() {
        clearTimeout(checkTimer);
        checkTimer = setTimeout(() => {
            renderMaliyet();                 // Parça 4 — her plan değişiminde maliyet özetini tazele
            if (!activeSurumId) return;
            if (isDirty()) {
                setStatus('Değişti…', 'dirty');
                clearTimeout(saveTimer);
                saveTimer = setTimeout(autoSave, DEBOUNCE_MS);
            }
        }, 200);
    }
    async function autoSave() {
        if (!activeSurumId || autoSaving) return;
        const sid = activeSurumId;
        const snap = snapshot();                 // girdi-temelli (dirty izleme)
        if (snap === null) return;
        if (snap === lastSavedSnapshot) { setStatus('Kaydedildi ✓', 'ok'); return; }
        autoSaving = true;
        setStatus('Kaydediliyor…', 'saving');
        try {
            const payload = readSlice();         // TAM (hesaplananlar dahil)
            const data = await api('POST', `/api/urun/${encodeURIComponent(URUN_ID)}/plan`, { surum_id: sid, plan: payload });
            if (!data || !data.ok) { setStatus('⚠ Kaydedilemedi', 'error'); return; }
            PLAN_MAP[sid] = data.plan || payload;
            if (sid === activeSurumId) lastSavedSnapshot = snap;
            setStatus('Kaydedildi ✓', 'ok');
        } catch (e) {
            setStatus('⚠ Kaydedilemedi', 'error');
        } finally {
            autoSaving = false;
        }
    }

    // === TCMB kur ===
    async function onFetchKur() {
        if (!fetchBtn) return;
        const old = fetchBtn.textContent;
        fetchBtn.disabled = true;
        fetchBtn.textContent = '⏳ Alınıyor…';
        try {
            const data = await api('GET', '/api/kur');
            if (data && (data.usd_try != null || data.eur_try != null)) {
                if (usdInput && data.usd_try != null) usdInput.value = data.usd_try;
                if (eurInput && data.eur_try != null) eurInput.value = data.eur_try;
                fetchedAt = data.fetched_at || new Date().toISOString();
                lastKurHint = data;
                updateKurInfo(data);
                scheduleDirtyCheck();
            } else { setStatus('Kur alınamadı — manuel girin', 'error'); }
        } catch (e) { setStatus('Kur alınamadı — manuel girin', 'error'); }
        finally { fetchBtn.disabled = false; fetchBtn.textContent = old; }
    }

    // === Sürüm yükle / değiştir ===
    function loadActive() {
        activeSurumId = (window.URUN_TEKNIK_STATE || {}).activeSurumId || null;
        render(currentSlice());
        refreshOzet();
        lastSavedSnapshot = snapshot();
        setStatus('', '');
        // Günlük otomatik kur — server lazy refresh'i tetikler; plan boşsa cache'ten doldurur
        maybeAutoFetchKur();
    }

    // Sessiz auto-fetch: plan'ın kuru DOLU ise dokunma (frozen / geçmiş tutarlılık),
    // BOŞ ise app_state.kur_tcmb_daily cache'ten doldur ve dirty tetikle (sonraki kayıtta snapshot'a gider).
    let lastKurHint = null;
    async function maybeAutoFetchKur() {
        try {
            const data = await api('GET', '/api/kur');
            if (!data || (data.usd_try == null && data.eur_try == null)) return;
            lastKurHint = data;
            const hasUsd = numOrNull(usdInput) != null;
            const hasEur = numOrNull(eurInput) != null;
            const fillUsd = !hasUsd && data.usd_try != null;
            const fillEur = !hasEur && data.eur_try != null;
            if (fillUsd) usdInput.value = data.usd_try;
            if (fillEur) eurInput.value = data.eur_try;
            if (fillUsd || fillEur) {
                fetchedAt = data.fetched_at || new Date().toISOString();
                updateKurInfo(data);
                scheduleDirtyCheck();   // boş alanları doldurduk → kaydet
            } else {
                // Plan'ın frozen kuru var; güncel cache'i hint olarak göster
                updateKurInfo(null);
            }
        } catch (e) { /* sessiz — manuel butona düşer */ }
    }
    function onSurumChanged(e) {
        if (activeSurumId && isDirty()) { clearTimeout(saveTimer); autoSave(); }
        activeSurumId = (e && e.detail && e.detail.surum_id) ||
                        (window.URUN_TEKNIK_STATE || {}).activeSurumId || null;
        render(currentSlice());
        refreshOzet();
        lastSavedSnapshot = snapshot();
        setStatus('', '');
    }

    // === Segment toggle (opsiyonel onChange) ===
    function bindSeg(segEl, onChange) {
        if (!segEl) return;
        segEl.addEventListener('click', (e) => {
            const btn = e.target.closest('.plan-seg-btn');
            if (!btn || btn.classList.contains('is-active')) return;
            segEl.querySelectorAll('.plan-seg-btn').forEach(b => b.classList.toggle('is-active', b === btn));
            if (onChange) onChange(btn.dataset.val);
            scheduleDirtyCheck();
        });
    }

    // === Bağlama ===
    // Parça 1
    bindSeg(raporParaEl);
    bindSeg(boyaCozguEl);
    bindSeg(boyaAtkiEl, () => updateAtkiTopVisibility());
    if (usdInput) usdInput.addEventListener('input', scheduleDirtyCheck);
    if (eurInput) eurInput.addEventListener('input', scheduleDirtyCheck);
    if (fetchBtn) fetchBtn.addEventListener('click', onFetchKur);
    // Parça 2 — Çözgü Planı (grup-bazlı)
    bindSeg(cozumYeriEl, () => updateCozguVisibility());
    bindSeg(cozumParaEl);
    bindSeg(gecisTipEl);
    bindSeg(gecisParaEl);
    if (metrajInput) metrajInput.addEventListener('input', () => { scheduleRecalc(); scheduleDirtyCheck(); });
    if (cozumBedelInput) cozumBedelInput.addEventListener('input', scheduleDirtyCheck);
    if (gecisBedelInput) gecisBedelInput.addEventListener('input', scheduleDirtyCheck);
    if (warpAddBtn) warpAddBtn.addEventListener('click', onWarpAdd);
    if (warpPaletteEl) warpPaletteEl.addEventListener('click', (e) => {
        const b = e.target.closest('.plan-swatch'); if (!b) return;
        assignColor({ palet_renk_id: null, ad: b.dataset.name || b.dataset.hex, hex: b.dataset.hex });
    });
    // Grup + çözgü etkileşimi — tek delegation host'a (yeni şema: çözgüler bağımsız sub-card)
    function parseDurumCi(s) {
        const parts = (s || '').split(':');
        return { durum: parts[0], ci: parseInt(parts[1], 10) };
    }
    if (cozguGruplarHost) cozguGruplarHost.addEventListener('click', (e) => {
        // (a) "+ Çözgü Ekle"
        const addBtn = e.target.closest('[data-grup-cozgu-add]');
        if (addBtn) {
            const d = addBtn.dataset.grupCozguAdd;
            const g = cozguGruplar[d] || (cozguGruplar[d] = emptyGrup());
            if (!Array.isArray(g.cozguler)) g.cozguler = [];
            g.cozguler.push(emptyCozgu());
            activeCozgu = { durum: d, idx: g.cozguler.length - 1 };
            renderWarpPalette(); renderCozguGroups(); scheduleDirtyCheck();
            e.stopPropagation();
            return;
        }
        // (b) Çözgü sil "×"
        const cDelBtn = e.target.closest('[data-grup-cozgu-del]');
        if (cDelBtn) {
            const { durum: d, ci } = parseDurumCi(cDelBtn.dataset.grupCozguDel);
            const g = cozguGruplar[d];
            if (g && Array.isArray(g.cozguler) && ci >= 0 && ci < g.cozguler.length) {
                if (g.cozguler.length === 1) { toast('En az 1 çözgü olmalı', 'warn'); return; }
                g.cozguler.splice(ci, 1);
                if (activeCozgu.durum === d) {
                    if (activeCozgu.idx === ci) activeCozgu.idx = Math.max(0, ci - 1);
                    else if (activeCozgu.idx > ci) activeCozgu.idx -= 1;
                }
                renderWarpPalette(); renderCozguGroups(); scheduleDirtyCheck();
            }
            e.stopPropagation();
            return;
        }
        // (c) Tip segment (per cozgu)
        const tipSeg = e.target.closest('[data-grup-cozgu-tip] .plan-seg-btn');
        if (tipSeg) {
            const segEl = tipSeg.closest('[data-grup-cozgu-tip]');
            const { durum: d, ci } = parseDurumCi(segEl.dataset.grupCozguTip);
            const val = tipSeg.dataset.val;
            const c = cozguGruplar[d] && cozguGruplar[d].cozguler && cozguGruplar[d].cozguler[ci];
            if (c && c.tip !== val) {
                c.tip = val;
                activeCozgu = { durum: d, idx: ci };
                renderWarpPalette(); renderCozguGroups(); scheduleDirtyCheck();
            }
            return;
        }
        // (d) Renk sayısı segment (per cozgu)
        const nSeg = e.target.closest('[data-grup-cozgu-renksayisi] .plan-seg-btn');
        if (nSeg) {
            const segEl = nSeg.closest('[data-grup-cozgu-renksayisi]');
            const { durum: d, ci } = parseDurumCi(segEl.dataset.grupCozguRenksayisi);
            const n = parseInt(nSeg.dataset.val, 10);
            const c = cozguGruplar[d] && cozguGruplar[d].cozguler && cozguGruplar[d].cozguler[ci];
            if (c && (n >= 1 && n <= 4) && c.renk_sayisi !== n) {
                c.renk_sayisi = n;
                activeCozgu = { durum: d, idx: ci };
                renderCozguGroups(); scheduleDirtyCheck();
            }
            return;
        }
        // (e) Renk chip kaldır (per cozgu, per slot)
        const chipDel = e.target.closest('[data-grup-cozgu-del-renk]');
        if (chipDel) {
            const parts = (chipDel.dataset.grupCozguDelRenk || '').split(':');
            const d = parts[0], ci = parseInt(parts[1], 10), si = parseInt(parts[2], 10);
            const c = cozguGruplar[d] && cozguGruplar[d].cozguler && cozguGruplar[d].cozguler[ci];
            if (c && Array.isArray(c.renk_atamalari) && si >= 0) {
                c.renk_atamalari[si] = null;
                activeCozgu = { durum: d, idx: ci };
                renderCozguGroups(); scheduleDirtyCheck();
            }
            return;
        }
        // (f) Çözgü kartına tıkla → aktif çözgü olsun (renk şeridi bu kart'a ekler)
        const cozguCard = e.target.closest('[data-cozgu-card]');
        if (cozguCard) {
            const { durum: d, ci } = parseDurumCi(cozguCard.dataset.cozguCard);
            if (d && (activeCozgu.durum !== d || activeCozgu.idx !== ci)) {
                activeCozgu = { durum: d, idx: ci };
                renderWarpPalette(); renderCozguGroups();
            }
            return;
        }
        // (g) Grup body boş alana tıkla → ilk çözgüyü aktif yap
        const grupEl = e.target.closest('.plan-grup');
        if (grupEl) {
            const d = grupEl.dataset.grup;
            if (d && activeCozgu.durum !== d) {
                activeCozgu = { durum: d, idx: 0 };
                renderWarpPalette(); renderCozguGroups();
            }
        }
    });
    // Çözgü kartı içindeki metraj input'u — her tuş vuruşunda sadece o kartın ihtiyaç tablosunu güncelle
    // (full re-render focus'u kaybeder). Maliyet + kayıt scheduleDirtyCheck ile (debounce) tazelenir.
    if (cozguGruplarHost) cozguGruplarHost.addEventListener('input', (e) => {
        const metInp = e.target.closest('[data-grup-cozgu-metraj]');
        if (!metInp) return;
        const { durum: d, ci } = parseDurumCi(metInp.dataset.grupCozguMetraj);
        const c = cozguGruplar[d] && cozguGruplar[d].cozguler && cozguGruplar[d].cozguler[ci];
        if (!c) return;
        const v = parseFloat(metInp.value);
        c.metraj = (isFinite(v) && v >= 0) ? v : null;
        activeCozgu = { durum: d, idx: ci };
        patchCozguIhtiyac(d, ci);
        scheduleDirtyCheck();
    });
    // Parça 3 — atkı/varyant + top boya
    if (varyantSayisiInput) varyantSayisiInput.addEventListener('input', () => {
        const n = parseInt(varyantSayisiInput.value, 10);
        if (isFinite(n)) { setVaryantCount(n); renderVariantTable(); renderAtkiOzet(); scheduleDirtyCheck(); }
    });
    if (varsayilanMetreInput) varsayilanMetreInput.addEventListener('input', scheduleDirtyCheck);
    if (metreUygulaBtn) metreUygulaBtn.addEventListener('click', applyDefaultMetre);
    if (variantTableEl) {
        variantTableEl.addEventListener('click', (e) => {
            const applyBtn = e.target.closest('.plan-row-apply');
            if (applyBtn) { applySameColor(parseInt(applyBtn.dataset.vi, 10)); return; }
            const cell = e.target.closest('.plan-cell-color');
            if (cell) { activeCell = { vi: parseInt(cell.dataset.vi, 10), yi: parseInt(cell.dataset.yi, 10) }; markActiveCell(); updateWeftTargetLabel(); }
        });
        variantTableEl.addEventListener('input', (e) => {
            if (e.target.closest('.plan-vmetre')) onVMetreInput(e);
            else if (e.target.closest('.plan-vad')) onVAdInput(e);
        });
    }
    if (weftPaletteEl) weftPaletteEl.addEventListener('click', onWeftStripClick);
    if (weftAddBtn) weftAddBtn.addEventListener('click', onWeftAdd);
    if (atkiOzetEl) atkiOzetEl.addEventListener('input', (e) => { if (e.target.closest('.plan-moq-input')) onMoqInput(e); });
    // top boya
    if (ekruMetreInput) ekruMetreInput.addEventListener('input', () => { renderEkruTuketim(); scheduleDirtyCheck(); });
    if (kazanKapInput) kazanKapInput.addEventListener('input', scheduleDirtyCheck);
    if (faturaMinInput) faturaMinInput.addEventListener('input', scheduleDirtyCheck);
    if (kazanBedelInput) kazanBedelInput.addEventListener('input', () => { renderBoyaRenkler(); scheduleDirtyCheck(); });
    bindSeg(kazanParaEl);
    if (boyaPaletteEl) boyaPaletteEl.addEventListener('click', onBoyaStripClick);
    if (boyaAddBtn) boyaAddBtn.addEventListener('click', onBoyaAdd);
    if (boyaRenklerEl) boyaRenklerEl.addEventListener('click', (e) => {
        const d = e.target.closest('[data-bdel]'); if (!d) return;
        const i = parseInt(d.dataset.bdel, 10);
        if (i >= 0) { boyanacakRenkler.splice(i, 1); renderBoyaRenkler(); scheduleDirtyCheck(); }
    });
    // Parça 4 — PDF raporu (önce kaydet, sonra print sayfasını yeni sekmede aç)
    if (planPdfBtn) planPdfBtn.addEventListener('click', async () => {
        if (!activeSurumId) { toast('Önce teknik sürüm gerekli', 'warn'); return; }
        if (isDirty()) { clearTimeout(saveTimer); await autoSave(); }   // taze maliyet_ozeti garanti
        window.open(`/urun/${encodeURIComponent(URUN_ID)}/plan/${encodeURIComponent(activeSurumId)}/print`, '_blank', 'noopener');
    });
    // Sekme açılınca özet + çözgü/atkı + maliyet teknik'ten tazelensin
    if (planTabBtn) planTabBtn.addEventListener('click', () => { refreshOzet(); refreshCozguFromTeknik(); refreshAtkiFromTeknik(); renderMaliyet(); });
    document.addEventListener('teknik-surum-changed', onSurumChanged);

    window.addEventListener('beforeunload', () => {
        if (activeSurumId && isDirty()) {
            try {
                const blob = new Blob([JSON.stringify({ surum_id: activeSurumId, plan: readSlice() })], { type: 'application/json' });
                navigator.sendBeacon(`/api/urun/${URUN_ID}/plan`, blob);
            } catch (e) { /* ignore */ }
        }
    });

    loadActive();
})();
