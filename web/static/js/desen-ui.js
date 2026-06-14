/* v4.0-part-2 Adım 3 — Desen Modülü UI (Faz B-G)
 *
 * DesenCore (desen.js) pure functions üzerine inşa edilmiş UI katmanı.
 * State management + 5 render fonksiyonu + event delegation.
 *
 * Bağımlılıklar: window.DesenCore (desen.js)
 * Export: window.DesenModule = { loadFromSurum, readToPayload, render }
 *
 * Entegrasyon: teknik.js'in loadFormFromSurum/readFormToSurum'ından çağrılır.
 */
(function () {
    "use strict";

    if (!window.DesenCore) {
        console.warn('[DesenModule] DesenCore not loaded — desen.js gerekli');
        return;
    }
    const DC = window.DesenCore;

    // === State ===
    let state = DC.defaultDesen();
    let renkliMode = false;
    let warpColor = '#000000';   // önizleme DOLU (çözgü) hücre rengi — varsayılan siyah, picker ile değişir

    // === DOM cache ===
    const $ = id => document.getElementById(id);
    const stepperValues = {};

    // === LOAD / SAVE ===
    function loadFromSurum(surum) {
        state = DC.normalizeDesen((surum && surum.desen) || null);
        render();
    }
    function readToPayload() {
        return state;
    }

    // === MASTER RENDER ===
    function render() {
        renderBoyutlar();
        renderTaharGrid();
        renderArmurAtkiRaporu();
        renderDongulerList();
        renderDesenPreview();
    }

    // === KART 1 — BOYUTLAR (steppers) ===
    const STEPPER_CONFIG = {
        warpCount:  { min: DC.MIN_WARP,  max: DC.MAX_WARP },
        weftCount:  { min: DC.MIN_WEFT,  max: DC.MAX_WEFT },
        frameCount: { min: DC.MIN_FRAME, max: DC.MAX_FRAME },
        iroCount:   { min: DC.MIN_IRO,   max: DC.MAX_IRO },
        raporX:     { min: DC.MIN_RAPOR, max: DC.MAX_RAPOR },
        raporY:     { min: DC.MIN_RAPOR, max: DC.MAX_RAPOR }
    };

    function renderBoyutlar() {
        Object.keys(STEPPER_CONFIG).forEach(key => {
            const cfg = STEPPER_CONFIG[key];
            const v = state[key];
            const out = document.querySelector(`[data-step-value="${key}"]`);
            if (out) out.textContent = String(v);
            const wrap = document.querySelector(`[data-desen-stepper="${key}"]`);
            if (wrap) {
                const minus = wrap.querySelector('[data-step="-1"]');
                const plus = wrap.querySelector('[data-step="+1"]');
                if (minus) minus.disabled = (v <= cfg.min);
                if (plus) plus.disabled = (v >= cfg.max);
            }
        });
    }

    function bindBoyutlarEvents() {
        document.querySelectorAll('[data-desen-stepper]').forEach(wrap => {
            const key = wrap.dataset.desenStepper;
            wrap.addEventListener('click', evt => {
                const btn = evt.target.closest('[data-step]');
                if (!btn || btn.disabled) return;
                const delta = parseInt(btn.dataset.step, 10);
                state = DC.setDimension(state, key, state[key] + delta);
                render();
            });
        });
        const dt = $('desen-duz-tahar');
        if (dt) dt.addEventListener('click', () => {
            state = { ...state, tahar: DC.buildDuzTahar(state.warpCount, state.frameCount) };
            render();
        });
        const at = $('desen-armur-temizle');
        if (at) at.addEventListener('click', () => {
            if (!confirm('Tüm armür hücreleri sıfırlanacak. Emin misin?')) return;
            state = { ...state, armur: DC.buildEmptyArmur(state.frameCount, state.weftCount) };
            render();
        });
    }

    // === KART 2 — TAHAR GRID ===
    function renderTaharGrid() {
        const host = $('desen-tahar-grid');
        if (!host) return;
        const { warpCount, frameCount, tahar } = state;
        // Grid: frameCount satır × (warpCount + 1) sütun (sol etiket)
        const gridTemplateCols = `28px repeat(${warpCount}, var(--desen-cell))`;
        const cells = [];
        // Üstten alta: F{N}..F1
        for (let f = frameCount - 1; f >= 0; f--) {
            cells.push(`<span class="dgrid-label">F${f + 1}</span>`);
            for (let w = 0; w < warpCount; w++) {
                const isOn = tahar[w] === f;
                cells.push(`<button class="dgrid-cell ${isOn ? 'is-warp' : ''}" type="button"
                            data-tahar-w="${w}" data-tahar-f="${f}" aria-pressed="${isOn}"></button>`);
            }
        }
        // Alt etiket satırı: warp 1..N
        cells.push(`<span class="dgrid-label"></span>`);
        for (let w = 0; w < warpCount; w++) {
            cells.push(`<span class="dgrid-label">${w + 1}</span>`);
        }
        host.innerHTML = `<div class="dgrid" style="grid-template-columns: ${gridTemplateCols}">${cells.join('')}</div>`;
    }

    function bindTaharEvents() {
        const host = $('desen-tahar-grid');
        if (!host) return;
        host.addEventListener('click', evt => {
            const btn = evt.target.closest('[data-tahar-w]');
            if (!btn) return;
            const w = parseInt(btn.dataset.taharW, 10);
            const f = parseInt(btn.dataset.taharF, 10);
            if (!isFinite(w) || !isFinite(f)) return;
            const newTahar = state.tahar.slice();
            newTahar[w] = f;
            state = { ...state, tahar: newTahar };
            renderTaharGrid();
            renderDesenPreview();
        });
    }

    // v4.0-part-2 Sprint 15 — birim rapor (loop açılmış gerçek dokuma) içinde
    // her iro'nun yüzdelik kullanımı. expandPicks marker satırlarını atlar,
    // DO Nx döngülerini açar → gerçek iplik tüketimini yansıtır.
    function computeIroUsage(st) {
        const order = DC.expandPicks(st);   // gerçek dokuma pick sırası
        const total = order.length;
        if (!total) return { total: 0, rows: [] };
        const counts = new Map();
        order.forEach(p => {
            const iro = st.iroData[p] || 1;
            counts.set(iro, (counts.get(iro) || 0) + 1);
        });
        const rows = [...counts.entries()]
            .sort((a, b) => a[0] - b[0])
            .map(([iro, count]) => ({
                iro, count,
                pct: Math.round((count / total) * 100),
                color: DC.IRO_COLORS[(iro - 1) % DC.IRO_COLORS.length],
            }));
        return { total, rows };
    }

    // === KART 3 — ARMÜR + ATKI RAPORU (döngülü) ===
    function renderArmurAtkiRaporu() {
        const host = $('desen-armur-grid');
        if (!host) return;
        const { weftCount, frameCount, iroCount, armur, iroData, loops } = state;
        const markers = DC.buildMarkerMap(loops);

        // Üst etiket satırı (frame 1..N + gap + iro 1..M)
        // NOT: padding-left CSS ile bracket+pick-label alanını ayırıyor (boş span yok)
        const headerCells = [];
        for (let f = 0; f < frameCount; f++) {
            headerCells.push(`<span class="dgrid-label">F${f + 1}</span>`);
        }
        headerCells.push(`<span class="desen-axis-gap"></span>`);
        for (let i = 0; i < iroCount; i++) {
            headerCells.push(`<span class="dgrid-label">i${i + 1}</span>`);
        }

        const rowsHtml = [];
        // v4.0-part-2 Sprint 12.2 — CSS var'dan oku: tabletteki küçük hücre değerleri
        // ile pill min-width OTOMATİK senkron olur (orantı korunur).
        const cs = getComputedStyle(host);
        const CELL_W = parseFloat(cs.getPropertyValue('--desen-cell')) || 22;
        const RG     = parseFloat(cs.getPropertyValue('--desen-row-gap')) || 2;
        const AXIS_GAP = parseFloat(cs.getPropertyValue('--desen-axis-gap')) || 12;
        const frameCellsW = frameCount * (CELL_W + RG) - RG;
        const iroCellsW   = iroCount  * (CELL_W + RG) - RG;
        const pillMinWidth = frameCellsW + AXIS_GAP + iroCellsW;
        const markerIcon = `<svg class="icon marker-icon" viewBox="0 0 24 24"><path d="M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
        const rowActions = (p) => `
            <span class="desen-row-actions">
                <button type="button" class="btn-add" data-row-action="insert" data-pick="${p}" title="Üstüne ekle">+</button>
                <button type="button" class="btn-del" data-row-action="delete" data-pick="${p}" title="Sil">×</button>
            </span>
        `;
        // Üstten alta: pick weftCount-1..0
        for (let p = weftCount - 1; p >= 0; p--) {
            const marker = markers.get(p);
            if (marker) {
                if (marker.kind === 'DO') {
                    rowsHtml.push(`
                        <div class="desen-armur-row desen-armur-row-marker" data-pick="${p}">
                            <span class="desen-pick-label">${p + 1}</span>
                            <div class="desen-marker-pill" style="min-width:${pillMinWidth}px">
                                ${markerIcon}
                                <span class="marker-label">DO</span>
                                <span class="stepper" data-loop-stepper="${getLoopIdxFromMarker(loops, marker)}">
                                    <button type="button" data-loop-step="-1">−</button>
                                    <output>${marker.count}</output>
                                    <button type="button" data-loop-step="+1">+</button>
                                </span>
                                <span class="marker-note">↺ ${marker.count}× döngü başlar</span>
                            </div>
                            ${rowActions(p)}
                        </div>
                    `);
                } else {
                    rowsHtml.push(`
                        <div class="desen-armur-row desen-armur-row-marker" data-pick="${p}">
                            <span class="desen-pick-label">${p + 1}</span>
                            <div class="desen-marker-pill" style="min-width:${pillMinWidth}px">
                                ${markerIcon}
                                <span class="marker-label">NEXT</span>
                                <span class="marker-note">↺ döngü biter</span>
                            </div>
                            ${rowActions(p)}
                        </div>
                    `);
                }
                continue;
            }
            // Normal satır
            const armurCells = [];
            for (let f = 0; f < frameCount; f++) {
                const isOn = !!(armur[f] && armur[f][p]);
                armurCells.push(`<button class="dgrid-cell ${isOn ? 'is-on' : ''}" type="button"
                                data-armur-f="${f}" data-armur-p="${p}" aria-pressed="${isOn}"></button>`);
            }
            const iroCells = [];
            const currentIro = iroData[p] || 1;
            for (let i = 0; i < iroCount; i++) {
                const isOn = (currentIro === i + 1);
                const color = DC.IRO_COLORS[i % DC.IRO_COLORS.length];
                iroCells.push(`<button class="dgrid-cell dgrid-iro-cell ${isOn ? 'is-on' : ''}" type="button"
                                style="background:${isOn ? color : 'var(--bg)'};${isOn ? '' : 'border-color:' + color}"
                                data-iro-p="${p}" data-iro-v="${i + 1}" aria-pressed="${isOn}"></button>`);
            }
            rowsHtml.push(`
                <div class="desen-armur-row" data-pick="${p}">
                    <span class="desen-pick-label">${p + 1}</span>
                    <div class="desen-row-cells">${armurCells.join('')}</div>
                    <div class="desen-iro-cells">${iroCells.join('')}</div>
                    <span class="desen-row-actions">
                        <button type="button" class="btn-add" data-row-action="insert" data-pick="${p}" title="Üstüne ekle">+</button>
                        <button type="button" class="btn-del" data-row-action="delete" data-pick="${p}" title="Sil">×</button>
                    </span>
                </div>
            `);
        }

        // v4.0-part-2 Sprint 12.2 — bracket SVG de CSS var ile aynı CELL/RG kullanır
        const bracketSvg = renderBracketSvg(loops, weftCount, CELL_W, RG);

        // v4.0-part-2 Sprint 15 — iro yüzdelik kullanım özeti (birim rapor)
        const usage = computeIroUsage(state);
        const iroOzetHtml = usage.total ? `
            <div class="desen-iro-ozet">
                <span class="iro-ozet-baslik">İro kullanımı <em>(birim rapor — ${usage.total} atkı)</em></span>
                <div class="iro-ozet-chips">
                    ${usage.rows.map(r => `
                        <span class="iro-ozet-chip" title="i${r.iro} · ${r.count} atkı · %${r.pct}">
                            <span class="iro-ozet-sw" style="background:${r.color}"></span>
                            <span class="iro-ozet-no">i${r.iro}</span>
                            <b class="iro-ozet-pct">%${r.pct}</b>
                            <em class="iro-ozet-cnt">(${r.count} atkı)</em>
                        </span>
                    `).join('')}
                </div>
            </div>
        ` : '';

        host.innerHTML = `
            <div class="desen-armur-area">
                <div class="desen-armur-headers">
                    ${headerCells.join('')}
                </div>
                <div class="desen-armur-rows-wrap">
                    ${bracketSvg}
                    <div class="desen-armur-rows">${rowsHtml.join('')}</div>
                </div>
                <div class="desen-armur-foot">
                    <button type="button" class="btn-mini" data-row-action="append">+ Satır Ekle</button>
                </div>
                ${iroOzetHtml}
            </div>
        `;
    }

    function getLoopIdxFromMarker(loops, marker) {
        return (loops || []).findIndex(l => l === marker.loop ||
            (l.startPick === marker.loop.startPick && l.endPick === marker.loop.endPick));
    }

    // Bracket SVG: rows-wrap içinde (header offset yok)
    // Her satır height: CELL, gap: ROW_GAP
    // Üstten alta sıralama: weftCount-1, ..., 1, 0
    // Pick k satırının üst kenarı: (weftCount-1-k) * (CELL+ROW_GAP)
    // Pick k satırının merkezi: (weftCount-1-k) * (CELL+ROW_GAP) + CELL/2
    function renderBracketSvg(loops, weftCount, CELL, ROW_GAP) {
        if (!loops || !loops.length) return '';
        const H = weftCount * (CELL + ROW_GAP) - ROW_GAP;
        const lines = [];
        loops.forEach(loop => {
            // NEXT marker (endPick) UI'da üstte → yTop küçük
            const yTop = (weftCount - 1 - loop.endPick) * (CELL + ROW_GAP) + CELL / 2;
            // DO marker (startPick) UI'da altta → yBot büyük
            const yBot = (weftCount - 1 - loop.startPick) * (CELL + ROW_GAP) + CELL / 2;
            lines.push(`<path d="M22 ${yTop} L4 ${yTop} L4 ${yBot} L22 ${yBot}"
                        fill="none" stroke="#d23b3b" stroke-width="1.75" stroke-linecap="round"/>`);
        });
        return `<svg class="desen-bracket" width="32" height="${H}" viewBox="0 0 32 ${H}" preserveAspectRatio="none" aria-hidden="true">${lines.join('')}</svg>`;
    }

    function bindArmurEvents() {
        const host = $('desen-armur-grid');
        if (!host) return;
        host.addEventListener('click', evt => {
            // Armür hücresi toggle
            const aCell = evt.target.closest('[data-armur-f]');
            if (aCell) {
                const f = parseInt(aCell.dataset.armurF, 10);
                const p = parseInt(aCell.dataset.armurP, 10);
                const newArmur = state.armur.map((row, fi) =>
                    fi === f ? row.map((v, pi) => pi === p ? !v : v) : row
                );
                state = { ...state, armur: newArmur };
                renderArmurAtkiRaporu();
                renderDesenPreview();
                return;
            }
            // İro radio
            const iCell = evt.target.closest('[data-iro-p]');
            if (iCell) {
                const p = parseInt(iCell.dataset.iroP, 10);
                const v = parseInt(iCell.dataset.iroV, 10);
                const newIro = state.iroData.slice();
                newIro[p] = v;
                state = { ...state, iroData: newIro };
                renderArmurAtkiRaporu();
                renderDesenPreview();
                return;
            }
            // Loop count stepper (DO marker satırında)
            const lStepBtn = evt.target.closest('[data-loop-step]');
            if (lStepBtn) {
                const wrap = lStepBtn.closest('[data-loop-stepper]');
                if (!wrap) return;
                const idx = parseInt(wrap.dataset.loopStepper, 10);
                const delta = parseInt(lStepBtn.dataset.loopStep, 10);
                const cur = state.loops[idx];
                if (!cur) return;
                state = DC.updateLoopCount(state, idx, cur.count + delta);
                renderArmurAtkiRaporu();
                renderDongulerList();
                renderDesenPreview();
                return;
            }
            // Satır + / × veya alt "Satır Ekle"
            const rowBtn = evt.target.closest('[data-row-action]');
            if (rowBtn) {
                const action = rowBtn.dataset.rowAction;
                const pick = parseInt(rowBtn.dataset.pick, 10);
                if (action === 'insert' && isFinite(pick)) {
                    // v4.0-part-2 Sprint 12.2: satırın ÜSTÜNE ekle
                    // (render reverse olduğundan pick+1 yeni satır görsel olarak basılan satırın üstünde belirir)
                    state = DC.insertRow(state, pick + 1);
                } else if (action === 'delete' && isFinite(pick)) {
                    state = DC.deleteRow(state, pick);
                } else if (action === 'append') {
                    // v4.0-part-2 Sprint 12.2: alt "+ Satır Ekle" butonu EN ALTA ekler
                    // (pick=0 = en küçük → render reverse → grid'in altında yeni satır)
                    state = DC.insertRow(state, 0);
                }
                render();
                return;
            }
        });
    }

    // === KART 4 — DÖNGÜLER ===
    function renderDongulerList() {
        const list = $('loop-list');
        const clearBtn = $('loop-clear');
        if (!list) return;
        list.innerHTML = '';
        const loops = state.loops || [];
        loops.forEach((loop, idx) => {
            const m = loop.endPick - loop.startPick - 1;  // pattern atkı sayısı
            const total = m * loop.count;                  // toplam dokuma
            const item = document.createElement('div');
            item.className = 'desen-loop-item';
            item.innerHTML = `
                <span class="loop-info">
                    <b>${idx + 1}.</b>
                    Atkı <b>${loop.startPick + 1}</b> (DO) → <b>${loop.endPick + 1}</b> (NEXT)
                    <em>· ${m} pattern × ${loop.count} = ${total} dokuma</em>
                </span>
                <button class="btn-loop-del" data-loop-del="${idx}" title="Sil">×</button>
            `;
            list.appendChild(item);
        });
        if (clearBtn) clearBtn.hidden = (loops.length === 0);
    }

    function bindLoopEvents() {
        const addBtn = $('loop-add');
        const errorEl = $('loop-error');
        const doInput = $('loop-do');
        const nextInput = $('loop-next');
        const countInput = $('loop-count');

        function tryAddLoop() {
            const doV = parseInt(doInput.value, 10);
            const nextV = parseInt(nextInput.value, 10);
            const countV = parseInt(countInput.value, 10);
            const loop = {
                startPick: isFinite(doV) ? doV - 1 : -1,
                endPick: isFinite(nextV) ? nextV - 1 : -1,
                count: isFinite(countV) ? countV : -1
            };
            const err = DC.validateLoop(state.loops, loop, state.weftCount);
            if (err) {
                if (errorEl) {
                    errorEl.textContent = err;
                    errorEl.hidden = false;
                }
                return;
            }
            state = DC.addLoop(state, loop);
            if (errorEl) errorEl.hidden = true;
            doInput.value = '';
            nextInput.value = '';
            countInput.value = '2';
            render();
        }
        if (addBtn) addBtn.addEventListener('click', tryAddLoop);
        // Enter ile ekle
        [doInput, nextInput, countInput].forEach(el => {
            if (!el) return;
            el.addEventListener('keydown', evt => {
                if (evt.key === 'Enter') { evt.preventDefault(); tryAddLoop(); }
            });
        });
        // Loop sil
        const list = $('loop-list');
        if (list) {
            list.addEventListener('click', evt => {
                const delBtn = evt.target.closest('[data-loop-del]');
                if (!delBtn) return;
                const idx = parseInt(delBtn.dataset.loopDel, 10);
                if (!isFinite(idx)) return;
                state = DC.removeLoopAt(state, idx);
                render();
            });
        }
        // Tümünü temizle
        const clearBtn = $('loop-clear');
        if (clearBtn) clearBtn.addEventListener('click', () => {
            if (!confirm('Tüm döngüler silinecek. Emin misin?')) return;
            state = DC.clearLoops(state);
            render();
        });
    }

    // === KART 5 — DESEN ÖNİZLEME ===
    function renderDesenPreview() {
        const host = $('desen-preview-grid');
        const statsEl = $('desen-preview-stats');
        if (!host) return;
        const { warpCount, weftCount, raporX, raporY, tahar, armur, iroData, loops } = state;
        // Stats
        const markerCount = (loops || []).length * 2;
        const patternCount = weftCount - markerCount;
        const expanded = DC.expandPicks(state);
        const dokuma = expanded.length;
        if (statsEl) {
            statsEl.textContent =
                `Armür ${weftCount} atkı (${markerCount} marker + ${patternCount} pattern) · ` +
                `Dokuma ${dokuma} atkı · Toplam ${warpCount * raporX}×${dokuma * raporY}`;
        }
        // Desen matrisi: desen[warp][weft]
        const desen = DC.computeDesen(tahar, armur, weftCount);
        // Render: raporY × raporX tile
        const totalRows = dokuma * raporY;
        const totalCols = warpCount * raporX;
        const cellSize = `var(--desen-prev)`;
        const cells = [];
        // Üstten alta: dokuma sırası (expanded son atkı altta)
        for (let r = totalRows - 1; r >= 0; r--) {
            const expIdx = r % dokuma;
            const origPick = expanded[expIdx];
            const iroIdx = ((iroData[origPick] || 1) - 1) % DC.IRO_COLORS.length;
            const iroColor = DC.IRO_COLORS[iroIdx];
            for (let c = 0; c < totalCols; c++) {
                const w = c % warpCount;
                const isOn = !!(desen[w] && desen[w][origPick]);
                // Önizleme: DOLU = çözgü rengi (varsayılan siyah, picker ile değişir);
                // BOŞ = beyaz (renkli modda atkı/iro rengi). Tahar/armür kırmızı kalır.
                const bg = isOn ? warpColor : (renkliMode ? iroColor : '#fff');
                cells.push(`<span class="dgrid-cell ${isOn ? 'is-on' : ''}" style="background:${bg}"></span>`);
            }
        }
        host.innerHTML = `<div class="dgrid desen-preview-grid" style="grid-template-columns: repeat(${totalCols}, var(--desen-prev))">${cells.join('')}</div>`;
    }

    function bindPreviewEvents() {
        const toggle = $('desen-renkli');
        if (toggle) toggle.addEventListener('change', () => {
            renkliMode = toggle.checked;
            renderDesenPreview();
        });
        // Çözgü (dolu hücre) rengi — opsiyonel görüntülenme rengi (varsayılan siyah)
        const warpInput = $('desen-warp-color');
        if (warpInput) {
            warpColor = warpInput.value || '#000000';
            warpInput.addEventListener('input', () => {
                warpColor = warpInput.value || '#000000';
                renderDesenPreview();
            });
        }
    }

    // === Init ===
    function init() {
        bindBoyutlarEvents();
        bindTaharEvents();
        bindArmurEvents();
        bindLoopEvents();
        bindPreviewEvents();
        render();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // v4.0-part-2 Adım 4 — Tarak → Desen bridge için public setter
    function setStateAndRender(newState) {
        if (!newState || typeof newState !== 'object') return;
        state = window.DesenCore.normalizeDesen(newState);
        render();
    }

    // === Export ===
    window.DesenModule = {
        loadFromSurum,
        readToPayload,
        render,
        getState: () => state,
        setStateAndRender   // Tarak → Desen köprüsü için
    };
})();
