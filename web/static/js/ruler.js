/* v3.7 — Hero Cetvel + Rapor Ölçümü
 *
 * Manuel kalibrasyon (2 nokta + bilinen cm) → cetvel gerçek cm gösterir.
 * Sürüklenebilir yatay + dikey cetvel.
 * Ölçüm: 2 nokta tıkla → mesafe cm → "Boyuna/Enine Rapora Kaydet" butonları.
 *
 * localStorage key: ruler_calibration_<urun_id>_<image_path>
 * Save endpoint: POST /api/urun/<id>/meta { repeat_vertical_cm | repeat_horizontal_cm }
 */
(function () {
    "use strict";

    const state = {
        urunId: null,
        currentPath: null,
        active: false,
        mode: 'idle',                  // 'idle' | 'calibrate' | 'measure'
        px_per_cm: null,
        points: [],                    // current click points (max 2)
        lastMeasureCm: null,
        rulerH: { y_px: null },        // null → otomatik orta
        rulerV: { x_px: null },
        els: {},                       // DOM refs
    };

    // === LocalStorage ===
    function calibKey(urunId, path) { return `ruler_calibration_${urunId}_${path}`; }
    function loadCalibration() {
        if (!state.urunId || !state.currentPath) return null;
        try {
            const v = localStorage.getItem(calibKey(state.urunId, state.currentPath));
            return v ? JSON.parse(v) : null;
        } catch (e) { return null; }
    }
    function saveCalibration(px_per_cm) {
        try {
            localStorage.setItem(
                calibKey(state.urunId, state.currentPath),
                JSON.stringify({ px_per_cm, calibrated_at: new Date().toISOString() })
            );
        } catch (e) {}
    }

    // === Koordinat dönüşümü — sayfa → hero-stage relative px ===
    function stageCoords(evt) {
        const stage = state.els.stage;
        const rect = stage.getBoundingClientRect();
        const cx = evt.clientX !== undefined ? evt.clientX : (evt.touches?.[0]?.clientX || 0);
        const cy = evt.clientY !== undefined ? evt.clientY : (evt.touches?.[0]?.clientY || 0);
        return [cx - rect.left, cy - rect.top];
    }

    // === Status mesajı ===
    function setStatus(msg, cls) {
        const el = state.els.status;
        if (!el) return;
        el.textContent = msg;
        el.className = 'ruler-status' + (cls ? ' ' + cls : '');
    }

    // === SVG temizle ===
    function clearSVG(svg) { while (svg.firstChild) svg.removeChild(svg.firstChild); }

    // === Cetvel çizimi ===
    function drawRulers() {
        if (!state.px_per_cm) return;
        const stage = state.els.stage;
        const W = stage.clientWidth;
        const H = stage.clientHeight;
        const pxcm = state.px_per_cm;

        // Yatay cetvel pozisyonu (Y_px) — kullanıcı sürüklemediyse merkezde
        const yPos = state.rulerH.y_px != null ? state.rulerH.y_px : Math.round(H / 2);
        const xPos = state.rulerV.x_px != null ? state.rulerV.x_px : Math.round(W / 2);

        // === Yatay cetvel ===
        const svgH = state.els.svgH;
        svgH.setAttribute('width', W);
        svgH.setAttribute('height', 32);
        svgH.style.top = (yPos - 16) + 'px';
        svgH.style.left = '0';
        clearSVG(svgH);
        // Arka plan strip (yarı saydam)
        const bgH = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bgH.setAttribute('x', 0); bgH.setAttribute('y', 0);
        bgH.setAttribute('width', W); bgH.setAttribute('height', 32);
        bgH.setAttribute('fill', 'rgba(15,17,20,0.65)');
        svgH.appendChild(bgH);
        // Baz çizgi
        const baseH = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        baseH.setAttribute('x1', 0); baseH.setAttribute('y1', 30);
        baseH.setAttribute('x2', W); baseH.setAttribute('y2', 30);
        baseH.setAttribute('stroke', '#fff'); baseH.setAttribute('stroke-width', 1.5);
        svgH.appendChild(baseH);
        // Tick'ler — 0'dan başlayıp her cm
        const maxCmH = Math.floor(W / pxcm);
        for (let cm = 0; cm <= maxCmH; cm++) {
            const x = cm * pxcm;
            if (x > W) break;
            const isMajor = cm % 10 === 0, isMid = cm % 5 === 0;
            const len = isMajor ? 16 : (isMid ? 10 : 5);
            const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            tick.setAttribute('x1', x); tick.setAttribute('y1', 30 - len);
            tick.setAttribute('x2', x); tick.setAttribute('y2', 30);
            tick.setAttribute('stroke', '#fff');
            tick.setAttribute('stroke-width', isMajor ? 1.5 : (isMid ? 1.25 : 1));
            svgH.appendChild(tick);
            if (isMajor && cm > 0) {
                const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                label.setAttribute('x', x + 3); label.setAttribute('y', 11);
                label.setAttribute('fill', '#fff');
                label.setAttribute('font-size', 10);
                label.setAttribute('font-family', 'Inter, sans-serif');
                label.setAttribute('font-weight', '600');
                label.textContent = cm;
                svgH.appendChild(label);
            }
        }

        // === Dikey cetvel ===
        const svgV = state.els.svgV;
        svgV.setAttribute('width', 32);
        svgV.setAttribute('height', H);
        svgV.style.left = (xPos - 16) + 'px';
        svgV.style.top = '0';
        clearSVG(svgV);
        const bgV = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bgV.setAttribute('x', 0); bgV.setAttribute('y', 0);
        bgV.setAttribute('width', 32); bgV.setAttribute('height', H);
        bgV.setAttribute('fill', 'rgba(15,17,20,0.65)');
        svgV.appendChild(bgV);
        const baseV = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        baseV.setAttribute('x1', 30); baseV.setAttribute('y1', 0);
        baseV.setAttribute('x2', 30); baseV.setAttribute('y2', H);
        baseV.setAttribute('stroke', '#fff'); baseV.setAttribute('stroke-width', 1.5);
        svgV.appendChild(baseV);
        const maxCmV = Math.floor(H / pxcm);
        for (let cm = 0; cm <= maxCmV; cm++) {
            const y = cm * pxcm;
            if (y > H) break;
            const isMajor = cm % 10 === 0, isMid = cm % 5 === 0;
            const len = isMajor ? 16 : (isMid ? 10 : 5);
            const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            tick.setAttribute('x1', 30 - len); tick.setAttribute('y1', y);
            tick.setAttribute('x2', 30); tick.setAttribute('y2', y);
            tick.setAttribute('stroke', '#fff');
            tick.setAttribute('stroke-width', isMajor ? 1.5 : (isMid ? 1.25 : 1));
            svgV.appendChild(tick);
            if (isMajor && cm > 0) {
                const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                label.setAttribute('x', 4); label.setAttribute('y', y - 3);
                label.setAttribute('fill', '#fff');
                label.setAttribute('font-size', 10);
                label.setAttribute('font-family', 'Inter, sans-serif');
                label.setAttribute('font-weight', '600');
                label.textContent = cm;
                svgV.appendChild(label);
            }
        }

        // === Handle pozisyonları ===
        state.els.handleH.style.top = (yPos - 8) + 'px';
        state.els.handleH.style.left = '4px';
        state.els.handleV.style.left = (xPos - 8) + 'px';
        state.els.handleV.style.top = '4px';
    }

    // === Nokta marker'ları (kalibrasyon + ölçüm için) ===
    function drawPoints() {
        const svg = state.els.points;
        const stage = state.els.stage;
        svg.setAttribute('width', stage.clientWidth);
        svg.setAttribute('height', stage.clientHeight);
        clearSVG(svg);
        if (state.points.length === 0) return;
        state.points.forEach((p, i) => {
            const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            c.setAttribute('cx', p.x); c.setAttribute('cy', p.y);
            c.setAttribute('r', 6);
            c.setAttribute('fill', state.mode === 'calibrate' ? '#d4af7f' : '#5b8def');
            c.setAttribute('stroke', '#fff');
            c.setAttribute('stroke-width', 2);
            svg.appendChild(c);
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', p.x + 10); label.setAttribute('y', p.y - 8);
            label.setAttribute('fill', '#fff');
            label.setAttribute('font-size', 11);
            label.setAttribute('font-family', 'Inter, sans-serif');
            label.setAttribute('font-weight', '700');
            label.setAttribute('stroke', 'rgba(0,0,0,0.7)');
            label.setAttribute('stroke-width', 0.4);
            label.textContent = i + 1;
            svg.appendChild(label);
        });
        // 2. nokta varsa mesafe çizgisi
        if (state.points.length === 2) {
            const [p1, p2] = state.points;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', p1.x); line.setAttribute('y1', p1.y);
            line.setAttribute('x2', p2.x); line.setAttribute('y2', p2.y);
            line.setAttribute('stroke', '#d4af7f');
            line.setAttribute('stroke-width', 2);
            line.setAttribute('stroke-dasharray', '4 3');
            svg.appendChild(line);
        }
    }

    // === Kalibrasyon ===
    function calibrateStart() {
        state.mode = 'calibrate';
        state.points = [];
        drawPoints();
        setStatus('Bilinen mesafenin iki ucunu görsele tıkla');
        state.els.stage.style.cursor = 'crosshair';
        state.els.calibrate.classList.add('is-active');
        state.els.measure.classList.remove('is-active');
    }

    function measureStart() {
        if (!state.px_per_cm) {
            setStatus('Önce "🎯 Kalibre Et" yap', 'warn');
            return;
        }
        state.mode = 'measure';
        state.points = [];
        drawPoints();
        setStatus('Ölçmek istediğin iki noktayı görsele tıkla');
        state.els.stage.style.cursor = 'crosshair';
        state.els.measure.classList.add('is-active');
        state.els.calibrate.classList.remove('is-active');
    }

    function endActiveMode() {
        state.mode = 'idle';
        state.els.stage.style.cursor = '';
        state.els.calibrate.classList.remove('is-active');
        state.els.measure.classList.remove('is-active');
    }

    function onStageClick(evt) {
        if (!state.active) return;
        if (state.mode !== 'calibrate' && state.mode !== 'measure') return;
        // Toolbar veya handle tıklamasını yutma
        if (evt.target.closest('.ruler-handle')) return;
        if (evt.target.closest('.hero-arrow')) return;
        if (evt.target.closest('.hero-tool-btn')) return;
        evt.preventDefault();
        evt.stopPropagation();
        const [x, y] = stageCoords(evt);
        state.points.push({ x, y });
        drawPoints();
        if (state.points.length === 2) {
            const [p1, p2] = state.points;
            const px_dist = Math.hypot(p2.x - p1.x, p2.y - p1.y);
            if (state.mode === 'calibrate') {
                const raw = prompt('Bu mesafe gerçek kumaşta kaç cm?\n\n(örn. 10)');
                const cm = parseFloat((raw || '').replace(',', '.'));
                if (cm > 0 && isFinite(cm)) {
                    state.px_per_cm = px_dist / cm;
                    saveCalibration(state.px_per_cm);
                    setStatus(`Kalibre edildi: 1 cm = ${state.px_per_cm.toFixed(1)} px`, 'ok');
                    drawRulers();
                    state.els.measure.disabled = false;
                } else {
                    setStatus('Kalibrasyon iptal — geçerli cm değeri girilmedi', 'warn');
                }
                state.points = [];
                drawPoints();
                endActiveMode();
            } else if (state.mode === 'measure') {
                const cm = px_dist / state.px_per_cm;
                state.lastMeasureCm = cm;
                setStatus(`Mesafe: ${cm.toFixed(1)} cm`, 'ok');
                updateSaveButtons(cm);
                endActiveMode();
            }
        }
    }

    function updateSaveButtons(cm) {
        const v = cm.toFixed(1);
        state.els.saveV.hidden = false;
        state.els.saveH.hidden = false;
        state.els.saveV.textContent = `Boyuna Rapora Kaydet (${v} cm)`;
        state.els.saveH.textContent = `Enine Rapora Kaydet (${v} cm)`;
    }

    async function saveAsReport(orientation) {
        const cm = state.lastMeasureCm;
        if (!cm) return;
        const key = orientation === 'v' ? 'repeat_vertical_cm' : 'repeat_horizontal_cm';
        const body = {}; body[key] = parseFloat(cm.toFixed(1));
        try {
            const res = await fetch(`/api/urun/${state.urunId}/meta`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await res.json();
            if (data.ok) {
                const lbl = orientation === 'v' ? 'Boyuna' : 'Enine';
                (window.toast || alert)(`${lbl} rapor kaydedildi: ${cm.toFixed(1)} cm`, 'success');
                // Detay sayfasındaki "Rapor (boy × en)" hücresini güncelle
                refreshReportCell(orientation, cm.toFixed(1));
            } else {
                (window.toast || alert)(data.error || 'Kayıt hatası', 'error');
            }
        } catch (e) {
            (window.toast || alert)('Ağ hatası: ' + e.message, 'error');
        }
    }

    function refreshReportCell(orientation, valueStr) {
        // .meta-list içinde "Rapor (boy × en)" hücresini bul ve güncelle
        const dts = document.querySelectorAll('.meta-list dt');
        let dd = null;
        for (const dt of dts) {
            if (/Rapor/i.test(dt.textContent)) {
                dd = dt.nextElementSibling;
                break;
            }
        }
        if (!dd) return;
        const txt = dd.textContent || '';
        const m = txt.match(/(\S+)\s*×\s*(\S+)/);
        let v = m ? m[1] : '–';
        let h = m ? m[2] : '–';
        if (orientation === 'v') v = valueStr;
        if (orientation === 'h') h = valueStr;
        dd.textContent = `${v} × ${h} cm`;
    }

    // === Sürükleme (handle drag) ===
    function bindDrag(handleEl, axis) {
        let dragging = false;
        let startCoord = 0, startVal = 0;

        function onDown(evt) {
            dragging = true;
            const stageRect = state.els.stage.getBoundingClientRect();
            const clientCoord = evt.touches?.[0]?.[axis === 'y' ? 'clientY' : 'clientX'] ?? evt[axis === 'y' ? 'clientY' : 'clientX'];
            startCoord = clientCoord;
            const cur = axis === 'y'
                ? (state.rulerH.y_px != null ? state.rulerH.y_px : stageRect.height / 2)
                : (state.rulerV.x_px != null ? state.rulerV.x_px : stageRect.width / 2);
            startVal = cur;
            evt.preventDefault();
        }
        function onMove(evt) {
            if (!dragging) return;
            const stageRect = state.els.stage.getBoundingClientRect();
            const clientCoord = evt.touches?.[0]?.[axis === 'y' ? 'clientY' : 'clientX'] ?? evt[axis === 'y' ? 'clientY' : 'clientX'];
            const delta = clientCoord - startCoord;
            let newVal = startVal + delta;
            const limit = axis === 'y' ? stageRect.height : stageRect.width;
            newVal = Math.max(0, Math.min(limit, newVal));
            if (axis === 'y') state.rulerH.y_px = newVal;
            else state.rulerV.x_px = newVal;
            drawRulers();
            evt.preventDefault();
        }
        function onUp() { dragging = false; }

        handleEl.addEventListener('mousedown', onDown);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        handleEl.addEventListener('touchstart', onDown, { passive: false });
        document.addEventListener('touchmove', onMove, { passive: false });
        document.addEventListener('touchend', onUp);
    }

    // === Toggle ===
    function toggle() {
        state.active = !state.active;
        state.els.overlay.hidden = !state.active;
        state.els.toolbar.hidden = !state.active;
        state.els.toggleBtn.classList.toggle('is-active', state.active);
        if (state.active) {
            // Mevcut görselin kalibrasyonu var mı?
            const cal = loadCalibration();
            if (cal && cal.px_per_cm) {
                state.px_per_cm = cal.px_per_cm;
                state.els.measure.disabled = false;
                setStatus(`Kalibre: 1 cm = ${cal.px_per_cm.toFixed(1)} px`, 'ok');
                drawRulers();
            } else {
                state.px_per_cm = null;
                state.els.measure.disabled = true;
                setStatus('Kalibrasyon gerekli — "🎯 Kalibre Et"');
                clearSVG(state.els.svgH);
                clearSVG(state.els.svgV);
            }
        } else {
            // Kapanırken state temizle
            state.mode = 'idle';
            state.points = [];
            clearSVG(state.els.points);
            state.els.stage.style.cursor = '';
            state.els.saveV.hidden = true;
            state.els.saveH.hidden = true;
        }
    }

    function setCurrentImagePath(path) {
        if (state.currentPath === path) return;
        state.currentPath = path;
        if (!state.active) return;
        // Yeni görsel → kalibrasyon yeniden yükle
        const cal = loadCalibration();
        state.points = [];
        state.lastMeasureCm = null;
        state.els.saveV.hidden = true;
        state.els.saveH.hidden = true;
        state.rulerH.y_px = null;
        state.rulerV.x_px = null;
        clearSVG(state.els.points);
        if (cal && cal.px_per_cm) {
            state.px_per_cm = cal.px_per_cm;
            state.els.measure.disabled = false;
            setStatus(`Kalibre: 1 cm = ${cal.px_per_cm.toFixed(1)} px`, 'ok');
            drawRulers();
        } else {
            state.px_per_cm = null;
            state.els.measure.disabled = true;
            setStatus('Bu görsel için kalibrasyon yok — "🎯 Kalibre Et"');
            clearSVG(state.els.svgH);
            clearSVG(state.els.svgV);
        }
    }

    // === Resize handler ===
    function onResize() {
        if (state.active && state.px_per_cm) drawRulers();
        if (state.active) drawPoints();
    }

    // === Public API ===
    window.Ruler = {
        init(opts) {
            state.urunId = opts.urunId;
            state.currentPath = opts.initialPath || null;
            state.els = {
                stage: opts.stage,
                overlay: opts.overlay,
                svgH: opts.svgH, svgV: opts.svgV,
                handleH: opts.handleH, handleV: opts.handleV,
                points: opts.points,
                toolbar: opts.toolbar,
                status: opts.status,
                toggleBtn: opts.toggleBtn,
                calibrate: opts.calibrateBtn,
                measure: opts.measureBtn,
                saveV: opts.saveVBtn,
                saveH: opts.saveHBtn,
                close: opts.closeBtn,
            };

            opts.toggleBtn.addEventListener('click', toggle);
            opts.calibrateBtn.addEventListener('click', calibrateStart);
            opts.measureBtn.addEventListener('click', measureStart);
            opts.saveVBtn.addEventListener('click', () => saveAsReport('v'));
            opts.saveHBtn.addEventListener('click', () => saveAsReport('h'));
            opts.closeBtn.addEventListener('click', () => { if (state.active) toggle(); });

            // Stage click — kalibrasyon/ölçüm noktaları
            opts.stage.addEventListener('click', onStageClick, true);

            // Drag
            bindDrag(opts.handleH, 'y');
            bindDrag(opts.handleV, 'x');

            // Resize
            window.addEventListener('resize', onResize);
        },
        setCurrentImagePath,
        isActive() { return state.active; },
    };
})();
