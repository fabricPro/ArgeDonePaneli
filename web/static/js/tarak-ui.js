/* v4.0-part-2 Adım 4 — Tarak Modülü UI (Faz B-G)
 *
 * TarakCore (tarak.js) pure functions üzerine inşa edilmiş UI katmanı.
 * State management + 4 kart render + event delegation.
 *
 * Bağımlılıklar: window.TarakCore (tarak.js)
 * Export: window.TarakModule = { loadFromSurum, readToPayload, render, getState, onSendToDesen }
 *
 * Entegrasyon: teknik.js'in loadFormFromSurum / readFormToSurum'undan çağrılır.
 * Bridge: teknik.js init'inde TarakModule.onSendToDesen → DesenModule köprüsü kurulur.
 */
(function () {
    "use strict";

    if (!window.TarakCore) {
        console.warn('[TarakModule] TarakCore yüklenmemiş — tarak.js gerekli');
        return;
    }
    const TC = window.TarakCore;

    // === State ===
    let state = TC.defaultTarak();
    let copyTimer = null;

    // === DOM cache ===
    const $ = id => document.getElementById(id);

    // === LOAD / SAVE ===
    function loadFromSurum(surum) {
        state = TC.normalizeTarak((surum && surum.tarak) || null);
        // Yüklendikten sonra mode/raporDis/raporCm tutarsız olabilir — bir sync geçir
        state = TC.syncDentThreads(state);
        render();
    }

    function readToPayload() {
        return state;
    }

    function getState() {
        return state;
    }

    // === MASTER RENDER ===
    function render() {
        renderParams();
        renderHint();
        renderStats();
        renderDentGrid();
        renderReport();
    }

    // === KART 1 — TARAK PARAMETRELERİ ===
    function renderParams() {
        const siklikInput = $('tarak-siklik');
        const raporDisInput = $('tarak-rapor-dis');
        const raporCmInput = $('tarak-rapor-cm');
        const raporDisWrap = document.querySelector('[data-tarak-rapor="dis"]');
        const raporCmWrap = document.querySelector('[data-tarak-rapor="cm"]');

        if (siklikInput && document.activeElement !== siklikInput) {
            siklikInput.value = state.siklik;
        }
        if (raporDisInput && document.activeElement !== raporDisInput) {
            raporDisInput.value = state.raporDis;
        }
        if (raporCmInput && document.activeElement !== raporCmInput) {
            raporCmInput.value = state.raporCm;
        }

        // Mode'a göre input görünürlük
        if (raporDisWrap) raporDisWrap.hidden = (state.mode !== 'dis');
        if (raporCmWrap)  raporCmWrap.hidden  = (state.mode !== 'cm');

        // Mode toggle butonları
        document.querySelectorAll('[data-tarak-mode]').forEach(btn => {
            btn.classList.toggle('is-active', btn.dataset.tarakMode === state.mode);
        });
    }

    function renderHint() {
        const el = $('tarak-hint');
        if (!el) return;
        const hint = TC.calcHint(state);
        if (!hint) {
            el.hidden = true;
            el.textContent = '';
            return;
        }
        el.hidden = false;
        el.innerHTML = `<b>${hint.from}</b> = <span class="tarak-hint-to">${hint.to}</span>`;
    }

    // === KART 2 — HESAPLANAN DEĞERLER ===
    function renderStats() {
        const sum = TC.calcTarakSummary(state);
        const fmt = (n, d) => {
            if (n == null || !isFinite(n) || n === 0) {
                // Eğer tüm girdiler boşsa "—" göster
                return (sum.siklik > 0 || sum.dis > 0) ? '0' : '—';
            }
            return n.toFixed(d != null ? d : 2);
        };
        setText('tarak-stat-siklik', sum.siklik > 0 ? fmt(sum.siklik, 1) : '—');
        setText('tarak-stat-dis',    sum.dis > 0    ? String(sum.dis) : '—');
        setText('tarak-stat-toplam', sum.toplamTel > 0 ? String(sum.toplamTel) : '—');
        setText('tarak-stat-ort',    sum.dis > 0 ? fmt(sum.ortTelDis, 2) : '—');
        setText('tarak-stat-cozgu',  sum.cozguSiklik > 0 ? fmt(sum.cozguSiklik, 2) : '—');
        setText('tarak-stat-cm',     sum.raporCm > 0 ? fmt(sum.raporCm, 4) : '—');
    }

    function setText(id, txt) {
        const el = $(id);
        if (el) el.textContent = txt;
    }

    // === KART 3 — DİŞ DİZİMİ ===
    function renderDentGrid() {
        const host = $('tarak-dent-grid');
        if (!host) return;
        if (state.mode === 'manuel') { renderManuelGrid(host); return; }
        const dis = state.dentThreads.length;

        if (dis === 0) {
            host.innerHTML = `<div class="tarak-empty">Tarak sıklığı ve rapor değerini girin</div>`;
            return;
        }

        // Hücre genişliği dinamik
        const cellW = Math.max(20, Math.min(40, Math.floor(620 / dis)));

        // Max thread (bar chart için)
        let maxThread = 0;
        for (let i = 0; i < dis; i++) {
            if (state.dentThreads[i] > maxThread) maxThread = state.dentThreads[i];
        }

        // Hücre satırı
        const cells = [];
        const numbers = [];
        const bars = [];
        for (let i = 0; i < dis; i++) {
            const tel = state.dentThreads[i] || 0;
            const isFilled = tel > 0;
            cells.push(`<button type="button" class="tarak-dent-cell ${isFilled ? 'is-filled' : ''}"
                        data-dent-i="${i}" aria-label="Diş ${i + 1}: ${tel} tel"
                        style="width:${cellW}px;height:${cellW}px;">${tel || ''}</button>`);
            numbers.push(`<span class="tarak-dent-num" style="width:${cellW}px">${i + 1}</span>`);
            // Bar yüksekliği — maxThread'e oranlı (0..50px)
            const barH = (maxThread > 0 && tel > 0) ? Math.max(2, Math.round((tel / maxThread) * 50)) : 0;
            bars.push(`<span class="tarak-dent-bar ${tel === 0 ? 'is-empty' : ''}"
                       style="width:${cellW}px;height:${barH}px;"></span>`);
        }

        host.innerHTML = `
            <div class="tarak-dent-grid-inner">
                <div class="tarak-dent-cells">${cells.join('')}</div>
                <div class="tarak-dent-numbers">${numbers.join('')}</div>
                <div class="tarak-dent-bars">${bars.join('')}</div>
            </div>
        `;
    }

    // Manuel mod — diş-başına birim: aralarda "+" ekleme noktası, her dişte × çıkar + tel hücresi.
    function renderManuelGrid(host) {
        const dis = state.dentThreads.length;
        let maxThread = 0;
        for (let i = 0; i < dis; i++) if (state.dentThreads[i] > maxThread) maxThread = state.dentThreads[i];
        const ins = (k, title) => `<button type="button" class="tarak-mins" data-dent-insert="${k}" title="${title}" aria-label="${title}">+</button>`;
        let row = '<div class="tarak-manuel-row">' + ins(0, 'Başa diş ekle');
        for (let i = 0; i < dis; i++) {
            const tel = state.dentThreads[i] || 0;
            const filled = tel > 0;
            const barH = (maxThread > 0 && tel > 0) ? Math.max(2, Math.round((tel / maxThread) * 34)) : 0;
            row += `<div class="tarak-mdent">
                <button type="button" class="tarak-mdent-del" data-dent-del="${i}" title="Bu dişi çıkar" aria-label="Diş ${i + 1} çıkar">×</button>
                <span class="tarak-mdent-bar ${tel === 0 ? 'is-empty' : ''}" style="height:${barH}px"></span>
                <button type="button" class="tarak-dent-cell ${filled ? 'is-filled' : ''}" data-dent-i="${i}" aria-label="Diş ${i + 1}: ${tel} tel">${tel || ''}</button>
                <span class="tarak-mdent-num">${i + 1}</span>
            </div>`;
            row += ins(i + 1, 'Araya diş ekle');
        }
        row += '</div>';
        const empty = dis === 0 ? '<div class="tarak-empty">Sıklığı gir, <b>+</b> ile diş ekle</div>' : '';
        const hint = '<div class="tarak-manuel-hint">Dişe sol-tık <b>+1 tel</b> · sağ-tık <b>−1 tel</b> · aradaki <b>+</b> araya ekler · <b>×</b> dişi çıkarır</div>';
        host.innerHTML = empty + row + hint;
    }

    // === KART 4 — TARAK RAPORU ===
    function renderReport() {
        const card = $('tarak-report-card');
        if (!card) return;
        const sum = TC.calcTarakSummary(state);

        // Koşullu görünüm
        if (sum.siklik <= 0 || sum.dis <= 0) {
            card.hidden = true;
            return;
        }
        card.hidden = false;

        // Üst özet bandı
        const groups = TC.rle(state.dentThreads);
        setText('tarak-report-summary',
            `Tarak sıklığı: ${sum.siklik} diş/cm · Rapor diş: ${sum.dis} · Rapor cm: ${sum.raporCm.toFixed(4)} · Grup sayısı: ${groups.length}`
        );

        // RLE liste
        const listEl = $('tarak-rle-list');
        if (listEl) {
            const rows = groups.map((g, idx) => {
                const total = g.dis * g.tel;
                const isEmpty = g.tel === 0;
                const result = isEmpty ? 'boş' : `${total} tel`;
                return `
                    <div class="tarak-rle-row ${isEmpty ? 'is-empty' : ''}">
                        <span class="rle-idx">#${idx + 1}</span>
                        <span class="rle-dis">${g.dis} diş</span>
                        <span class="rle-x">×</span>
                        <span class="rle-tel">${g.tel} tel</span>
                        <span class="rle-eq">=</span>
                        <span class="rle-result">${result}</span>
                    </div>
                `;
            }).join('');
            listEl.innerHTML = rows;
        }

        // Alt 3 mini stat
        const statsEl = $('tarak-report-stats');
        if (statsEl) {
            statsEl.innerHTML = `
                <div class="tarak-mini-stat">
                    <span class="mini-label">Toplam diş</span>
                    <span class="mini-value">${sum.dis}</span>
                </div>
                <div class="tarak-mini-stat tarak-mini-stat-hero">
                    <span class="mini-label">Toplam tel</span>
                    <span class="mini-value">${sum.toplamTel}</span>
                </div>
                <div class="tarak-mini-stat tarak-mini-stat-green">
                    <span class="mini-label">Çözgü sıklığı</span>
                    <span class="mini-value">${sum.cozguSiklik.toFixed(2)} <em>tel/cm</em></span>
                </div>
            `;
        }
    }

    // === Event handlers ===

    // Sıklık input
    function bindInputs() {
        const siklikEl = $('tarak-siklik');
        const raporDisEl = $('tarak-rapor-dis');
        const raporCmEl = $('tarak-rapor-cm');

        if (siklikEl) siklikEl.addEventListener('input', () => {
            state = TC.syncDentThreads({ ...state, siklik: siklikEl.value });
            // Sıklık değişiminde render kapsamı: hint + stats + grid + report
            renderHint();
            renderStats();
            renderDentGrid();
            renderReport();
            // Mode cm ise raporDis input'unu güncelle (focus dışında)
            if (state.mode === 'cm') {
                const di = $('tarak-rapor-dis');
                if (di && document.activeElement !== di) di.value = state.raporDis;
            }
        });

        if (raporDisEl) raporDisEl.addEventListener('input', () => {
            state = TC.syncDentThreads({ ...state, raporDis: raporDisEl.value, mode: 'dis' });
            renderHint();
            renderStats();
            renderDentGrid();
            renderReport();
        });

        if (raporCmEl) raporCmEl.addEventListener('input', () => {
            state = TC.syncDentThreads({ ...state, raporCm: raporCmEl.value, mode: 'cm' });
            // raporDis input'unu da güncelle
            const di = $('tarak-rapor-dis');
            if (di && document.activeElement !== di) di.value = state.raporDis;
            renderHint();
            renderStats();
            renderDentGrid();
            renderReport();
        });

        // Mode toggle
        document.querySelectorAll('[data-tarak-mode]').forEach(btn => {
            btn.addEventListener('click', () => {
                const newMode = btn.dataset.tarakMode;
                if (newMode === state.mode) return;
                state = TC.syncDentThreads({ ...state, mode: newMode });
                // Manuel'e geçişte diş yoksa ilk dişi aç (kullanıcı "+" ile devam eder)
                if (newMode === 'manuel' && state.dentThreads.length === 0) {
                    state = TC.addDent(state);
                }
                render();
            });
        });

        // Reset butonu
        const resetBtn = $('tarak-reset');
        if (resetBtn) resetBtn.addEventListener('click', () => {
            if (state.dentThreads.length === 0) return;
            if (!confirm('Tüm dişler 0\'a indirilecek. Uzunluk korunur. Emin misin?')) return;
            state = TC.resetThreads(state);
            renderDentGrid();
            renderStats();
            renderReport();
        });
    }

    // Diş grid click (sol-tık +1, sağ-tık -1)
    function bindDentGrid() {
        const host = $('tarak-dent-grid');
        if (!host) return;
        host.addEventListener('click', evt => {
            // Manuel mod — araya diş ekle / o dişi çıkar
            const insBtn = evt.target.closest('[data-dent-insert]');
            if (insBtn) {
                state = TC.insertDent(state, parseInt(insBtn.dataset.dentInsert, 10));
                renderDentGrid(); renderStats(); renderReport(); renderHint();
                return;
            }
            const delBtn = evt.target.closest('[data-dent-del]');
            if (delBtn) {
                state = TC.removeDent(state, parseInt(delBtn.dataset.dentDel, 10));
                renderDentGrid(); renderStats(); renderReport(); renderHint();
                return;
            }
            const cell = evt.target.closest('[data-dent-i]');
            if (!cell) return;
            const i = parseInt(cell.dataset.dentI, 10);
            if (!isFinite(i)) return;
            state = TC.incThread(state, i, +1);
            renderDentGrid();
            renderStats();
            renderReport();
        });
        host.addEventListener('contextmenu', evt => {
            const cell = evt.target.closest('[data-dent-i]');
            if (!cell) return;
            evt.preventDefault();
            const i = parseInt(cell.dataset.dentI, 10);
            if (!isFinite(i)) return;
            state = TC.incThread(state, i, -1);
            renderDentGrid();
            renderStats();
            renderReport();
        });
    }

    // RLE Kopyala + Desen'e Aktar
    function bindReportActions() {
        const copyBtn = $('tarak-rle-copy');
        const copyLabel = $('tarak-rle-copy-label');
        if (copyBtn) copyBtn.addEventListener('click', async () => {
            const text = TC.rleToText(state.dentThreads);
            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(text);
                } else {
                    // Fallback: textarea + execCommand
                    const ta = document.createElement('textarea');
                    ta.value = text;
                    ta.style.position = 'fixed';
                    ta.style.left = '-9999px';
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    document.body.removeChild(ta);
                }
                if (copyLabel) copyLabel.textContent = '✓ Kopyalandı';
                copyBtn.classList.add('is-success');
                clearTimeout(copyTimer);
                copyTimer = setTimeout(() => {
                    if (copyLabel) copyLabel.textContent = 'RLE Kopyala';
                    copyBtn.classList.remove('is-success');
                }, 1200);
            } catch (e) {
                if (window.toast) window.toast('Kopyalanamadı', 'error');
                else alert('Kopyalanamadı: ' + text);
            }
        });

    }

    // === Init ===
    function init() {
        bindInputs();
        bindDentGrid();
        bindReportActions();
        render();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // === Export ===
    window.TarakModule = {
        loadFromSurum,
        readToPayload,
        render,
        getState
    };
})();
