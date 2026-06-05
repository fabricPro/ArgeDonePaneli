/**
 * İplik Kataloğu — kartela meta düzenleme auto-save (plan.js pattern'i).
 *
 * - data-k input/select/textarea → state alanı; her değişimde 1500ms debounce → POST.
 * - Yeni kayıt: kartela_id='yeni' POST edilir; server uuid üretir, cevapta döner;
 *   URL history.replaceState ile /iplik-katalogu/<id>'ye çevrilir.
 * - sayfalar (Parça 2 JSONB) state'e dokunulmaz; ilk veriden alınıp aynen geri gönderilir.
 */
(function () {
    "use strict";

    const DEBOUNCE_MS = 1500;
    const statusEl = document.getElementById('katalog-status');
    const tipSelect = document.getElementById('k-iplik-tipi');
    const otherInput = document.getElementById('iplik-tipi-other');
    // Parça 2-A — sayfa yönetimi DOM ref'leri
    const sayfaInput = document.getElementById('sayfa-foto-input');
    const sayfaProgress = document.getElementById('sayfa-upload-progress');
    const sayfaHost = document.getElementById('sayfa-kartlari');
    const sayfaEmpty = document.getElementById('sayfa-empty');
    const sayfalarFieldset = document.getElementById('sayfalar-fieldset');
    const MAX_FOTO_BYTES = 15 * 1024 * 1024;
    // Parça 2-B — renk yakalama modalı DOM ref'leri + state
    const renkModal = document.getElementById('renk-modal');
    const renkCanvas = document.getElementById('renk-canvas');
    const overlayLayer = document.getElementById('renk-overlay-layer');
    const renkListesiEl = document.getElementById('renk-listesi');
    const renkSayacEl = document.getElementById('renk-sayac');
    const renkEmptyEl = document.getElementById('renk-listesi-empty');
    const renkAvgEl = document.getElementById('renk-avg');
    const renkModalStatusEl = document.getElementById('renk-modal-status');
    const renkModalBaslikEl = document.getElementById('renk-modal-baslik');
    const renkAutoBtn = document.getElementById('renk-auto');
    const renkAutoCountSel = document.getElementById('renk-auto-count');
    const RENK_DICT_URL = '/static/data/renkler.json';
    const MODAL_DEBOUNCE_MS = 800;
    let aktifSayfaId = null;
    let modalRenkler = [];
    let modalRenklerDirty = false;
    let colorPickerInited = false;
    let modalDebounceTimer = null;

    let kartelaId = 'yeni';
    let sayfalar = [];                 // Parça 2 verisi — korunur
    let lastSavedSnapshot = null;
    let saveTimer = null, checkTimer = null, autoSaving = false;

    // İlk veri: kartela_id + sayfalar (form alanları DOM'dan okunur)
    try {
        const raw = document.getElementById('kartela-data');
        const initial = raw ? JSON.parse(raw.textContent || 'null') : null;
        if (initial && typeof initial === 'object') {
            kartelaId = initial.kartela_id || 'yeni';
            sayfalar = Array.isArray(initial.sayfalar) ? initial.sayfalar : [];
        }
    } catch (e) { /* yeni kayıt */ }

    function setStatus(text, kind) {
        if (!statusEl) return;
        statusEl.textContent = text || '';
        statusEl.dataset.kind = kind || '';
    }

    async function api(method, url, body) {
        const opts = { method, headers: { 'Content-Type': 'application/json' } };
        if (body !== undefined) opts.body = JSON.stringify(body);
        const res = await fetch(url, opts);
        let data = null;
        try { data = await res.json(); } catch (e) { data = null; }
        return data || { ok: false, error: 'HTTP ' + res.status };
    }

    // DOM → payload (kartela_id + tüm data-k alanları + korunan sayfalar)
    function readForm() {
        const obj = { kartela_id: kartelaId };
        document.querySelectorAll('[data-k]').forEach(el => {
            const key = el.dataset.k;
            if (el.dataset.type === 'num') {
                const f = parseFloat(String(el.value).replace(',', '.'));
                obj[key] = isFinite(f) ? f : null;
            } else {
                const v = (el.value == null) ? '' : String(el.value).trim();
                obj[key] = v === '' ? null : v;
            }
        });
        // İplik Tipi "Diğer" → serbest metin değeri
        if (tipSelect && tipSelect.value === '__other__') {
            const ov = (otherInput && otherInput.value || '').trim();
            obj.iplik_tipi = ov || null;
        }
        obj.sayfalar = sanitizeSayfalar();   // türetilmiş foto_url DB'ye sızmasın
        return obj;
    }

    // Persist edilecek sayfa şekli (render-only foto_url ÇIKARILIR)
    function sanitizeSayfalar() {
        return (sayfalar || []).map(s => ({
            sayfa_id: s.sayfa_id,
            sira: s.sira,
            foto_path: s.foto_path,
            renkler: s.renkler || [],
        }));
    }

    // Dirty izleme: kartela_id hariç (yeni→uuid değişimi kirlilik saymasın)
    function snapshot() {
        try {
            const f = readForm();
            delete f.kartela_id;
            return JSON.stringify(f);
        } catch (e) { return null; }
    }

    function isDirty() {
        const s = snapshot();
        return s !== null && lastSavedSnapshot !== null && s !== lastSavedSnapshot;
    }

    function scheduleDirtyCheck() {
        clearTimeout(checkTimer);
        checkTimer = setTimeout(() => {
            if (isDirty()) {
                setStatus('Değişti…', 'dirty');
                clearTimeout(saveTimer);
                saveTimer = setTimeout(autoSave, DEBOUNCE_MS);
            }
        }, 200);
    }

    async function autoSave() {
        if (autoSaving) return;
        const payload = readForm();
        if (!payload.ad) { setStatus('Kartela adı gerekli', 'error'); return; }
        const snap = snapshot();
        if (snap === lastSavedSnapshot) { setStatus('Kaydedildi ✓', 'ok'); return; }
        autoSaving = true;
        setStatus('Kaydediliyor…', 'saving');
        try {
            const data = await api('POST', '/iplik-katalogu/' + encodeURIComponent(kartelaId), payload);
            if (!data || !data.ok) { setStatus(data && data.error ? data.error : '⚠ Kaydedilemedi', 'error'); return; }
            if (data.kartela_id && data.kartela_id !== kartelaId) {
                kartelaId = data.kartela_id;
                try { history.replaceState(null, '', '/iplik-katalogu/' + kartelaId); } catch (e) {}
                // İlk kayıt: artık kartela_id var → Sayfalar bloğunu aç (sayfa yüklenebilir)
                if (sayfalarFieldset) sayfalarFieldset.hidden = false;
                renderSayfalar();
            }
            lastSavedSnapshot = snapshot();
            setStatus('Kaydedildi ✓', 'ok');
        } catch (e) {
            setStatus('⚠ Kaydedilemedi', 'error');
        } finally {
            autoSaving = false;
        }
    }

    // İplik Tipi "Diğer" toggle
    function syncTipOther() {
        if (!tipSelect || !otherInput) return;
        otherInput.style.display = (tipSelect.value === '__other__') ? 'block' : 'none';
    }

    // ========================================================
    // Parça 2-A — Sayfa fotoğrafı yönetimi (renk seçimi B2-b'de)
    // ========================================================
    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function renderSayfalar() {
        if (!sayfaHost) return;
        if (!sayfalar.length) {
            sayfaHost.innerHTML = '';
            if (sayfaEmpty) sayfaEmpty.hidden = false;
            return;
        }
        if (sayfaEmpty) sayfaEmpty.hidden = true;
        sayfaHost.innerHTML = sayfalar.map(s => {
            const sira = s.sira;
            const renkSayisi = (s.renkler || []).length;
            const src = s.foto_url || '';
            return '<div class="sayfa-card" data-sayfa-id="' + escapeHtml(s.sayfa_id) + '">' +
                '<div class="sayfa-thumb"><img src="' + escapeHtml(src) + '" alt="Sayfa ' + escapeHtml(sira) + '" loading="lazy"></div>' +
                '<div class="sayfa-info">' +
                    '<div class="sayfa-baslik">Sayfa ' + escapeHtml(sira) + '</div>' +
                    '<div class="sayfa-meta">' + renkSayisi + ' renk</div>' +
                '</div>' +
                '<div class="sayfa-actions">' +
                    '<button class="btn btn-sm btn-primary" data-action="renkleri-duzenle" title="Renkleri yönet">🎨 Renkleri Düzenle</button>' +
                    '<button class="btn btn-sm btn-danger" data-action="sayfa-sil" title="Sayfayı sil">🗑</button>' +
                '</div>' +
            '</div>';
        }).join('');
    }

    async function onSayfaUpload(e) {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        if (file.size > MAX_FOTO_BYTES) {
            (window.toast || alert)('Dosya çok büyük (max ~15 MB)', 'warn');
            sayfaInput.value = '';
            return;
        }
        if (sayfaProgress) sayfaProgress.hidden = false;
        sayfaInput.disabled = true;
        try {
            const fd = new FormData();
            fd.append('foto', file);
            const res = await fetch('/iplik-katalogu/' + encodeURIComponent(kartelaId) + '/sayfa/yukle', { method: 'POST', body: fd });
            let data = null;
            try { data = await res.json(); } catch (e2) { data = null; }
            if (data && data.ok && data.sayfa) {
                data.sayfa.foto_url = data.public_url || null;
                sayfalar.push(data.sayfa);
                renderSayfalar();
                lastSavedSnapshot = snapshot();   // push edilen sayfa meta'yı dirty yapmasın
                (window.toast || alert)('Sayfa eklendi', 'success');
            } else {
                (window.toast || alert)((data && data.error) || 'Sayfa yüklenemedi', 'error');
            }
        } catch (err) {
            (window.toast || alert)('Sayfa yüklenemedi', 'error');
        } finally {
            if (sayfaProgress) sayfaProgress.hidden = true;
            sayfaInput.disabled = false;
            sayfaInput.value = '';
        }
    }

    async function onSayfaHostClick(e) {
        // Parça 2-B — "Renkleri Düzenle" → modal aç
        const editBtn = e.target.closest('[data-action="renkleri-duzenle"]');
        if (editBtn) {
            const c = editBtn.closest('.sayfa-card');
            if (c) openRenkModal(c.dataset.sayfaId);
            return;
        }
        const delBtn = e.target.closest('[data-action="sayfa-sil"]');
        if (!delBtn) return;
        const card = delBtn.closest('.sayfa-card');
        if (!card) return;
        const sid = card.dataset.sayfaId;
        const s = sayfalar.find(x => x.sayfa_id === sid);
        if (!s) return;
        const renkSayisi = (s.renkler || []).length;
        const mesaj = renkSayisi > 0
            ? 'Bu sayfada ' + renkSayisi + ' renk var. Sayfa silinince renkler de silinecek. Devam edilsin mi?'
            : 'Sayfa ' + s.sira + ' silinsin mi?';
        if (!confirm(mesaj)) return;
        try {
            const res = await fetch('/iplik-katalogu/' + encodeURIComponent(kartelaId) + '/sayfa/' + encodeURIComponent(sid) + '/sil', { method: 'POST' });
            let data = null;
            try { data = await res.json(); } catch (e2) { data = null; }
            if (data && data.ok) {
                sayfalar = sayfalar.filter(x => x.sayfa_id !== sid);
                sayfalar.forEach((x, i) => { x.sira = i + 1; });
                renderSayfalar();
                lastSavedSnapshot = snapshot();
                (window.toast || alert)('Sayfa silindi', 'success');
            } else {
                (window.toast || alert)((data && data.error) || 'Sayfa silinemedi', 'error');
            }
        } catch (err) {
            (window.toast || alert)('Sayfa silinemedi', 'error');
        }
    }

    // ========================================================
    // Parça 2-B — Renk yakalama modalı (color-picker salt-tüketici)
    // ========================================================
    function uuid12() {
        try {
            const a = new Uint8Array(6);
            (window.crypto || window.msCrypto).getRandomValues(a);
            return Array.from(a, b => b.toString(16).padStart(2, '0')).join('');
        } catch (e) {
            let s = '';
            while (s.length < 12) s += Math.floor(Math.random() * 16).toString(16);
            return s.slice(0, 12);
        }
    }

    function setModalStatus(text, kind) {
        if (!renkModalStatusEl) return;
        renkModalStatusEl.textContent = text || '';
        renkModalStatusEl.dataset.kind = kind || '';
    }

    // renkler.json (ticari isim sözlüğü) → verilen rgb'ye en yakın ticari ad
    function nearestName(rgb) {
        try {
            const cp = window.ColorPicker;
            if (cp && cp._nearestColorName && Array.isArray(rgb) && rgb.length === 3) {
                const nm = cp._nearestColorName(rgb[0], rgb[1], rgb[2]);
                if (nm && nm.name && nm.name !== '—') return nm.name;
            }
        } catch (e) {}
        return '';
    }

    function cssEsc(v) {
        return (window.CSS && CSS.escape) ? CSS.escape(v) : String(v).replace(/"/g, '\\"');
    }

    async function openRenkModal(sayfaId) {
        const sayfa = sayfalar.find(s => s.sayfa_id === sayfaId);
        if (!sayfa) return;
        if (!window.ColorPicker) { (window.toast || alert)('Renk motoru yüklenemedi', 'error'); return; }
        aktifSayfaId = sayfaId;
        modalRenkler = JSON.parse(JSON.stringify(sayfa.renkler || []));
        modalRenklerDirty = false;
        if (renkModalBaslikEl) renkModalBaslikEl.textContent = 'Sayfa ' + sayfa.sira + ' — Renkleri Düzenle';
        setModalStatus('', '');
        renkModal.hidden = false;
        document.body.style.overflow = 'hidden';
        try {
            if (!colorPickerInited) {
                await window.ColorPicker.init({
                    canvasEl: renkCanvas,
                    dictionaryUrl: RENK_DICT_URL,
                    onChange: (role, res, n) => handleCp(res),
                });
                colorPickerInited = true;
            }
            await window.ColorPicker.setImage(sayfa.foto_url);
            window.ColorPicker.setRole('weft');
            window.ColorPicker.setAvg(renkAvgEl ? renkAvgEl.checked : true);
            window.ColorPicker.setMultiPoint(false);
            window.ColorPicker.clearPoints();
        } catch (err) {
            setModalStatus('Renk motoru/görsel yüklenemedi', 'error');
            (window.toast || alert)('Renk motoru veya görsel yüklenemedi', 'error');
        }
        normalizeAndRender();
    }

    // color-picker onChange → tek nokta yakala (clearPoints sonrası her zaman 1 nokta → res = o tıklama)
    function handleCp(res) {
        if (!res || !res.points || !res.points.length) return;   // setImage/clearPoints/setRole notify'larını ele
        if (!renkCanvas.width || !renkCanvas.height) return;
        const last = res.points[res.points.length - 1];
        // Otomatik ticari ad: color-picker'ın sözlük önerisi (res.name); boşsa rgb'den en yakın ticari isim
        const ad = (res.name && res.name !== '—') ? res.name : nearestName(res.rgb);
        modalRenkler.push({
            renk_id: uuid12(),
            numara: modalRenkler.length + 1,
            kod: '',
            ad: ad,
            hex: res.hex,
            rgb: res.rgb,
            lab: res.lab,
            secim_noktasi: { x: last.x / renkCanvas.width, y: last.y / renkCanvas.height },
        });
        modalRenklerDirty = true;
        normalizeAndRender();
        scheduleModalSave();
        try { window.ColorPicker.clearPoints(); } catch (e) {}   // anlık native marker'ı sil → yalnız overlay
    }

    function renderRenkListesi() {
        if (renkSayacEl) renkSayacEl.textContent = modalRenkler.length;
        if (!renkListesiEl) return;
        if (!modalRenkler.length) {
            renkListesiEl.innerHTML = '';
            if (renkEmptyEl) renkEmptyEl.hidden = false;
            return;
        }
        if (renkEmptyEl) renkEmptyEl.hidden = true;
        renkListesiEl.innerHTML = modalRenkler.map(r => {
            const hex = escapeHtml(r.hex || '');
            const oneri = nearestName(r.rgb);   // sözlükteki en yakın ticari isim (öneri)
            return '<div class="renk-satir" data-renk-id="' + escapeHtml(r.renk_id) + '" data-numara="' + escapeHtml(r.numara) + '">' +
                '<div class="renk-numara">' + escapeHtml(r.numara) + '</div>' +
                '<div class="renk-swatch" style="background:' + hex + '"></div>' +
                '<div class="renk-info">' +
                    '<input type="text" class="renk-kod" placeholder="Kod (örn. 4203)" value="' + escapeHtml(r.kod || '') + '">' +
                    '<input type="text" class="renk-ad" placeholder="Ad (örn. Krem)" value="' + escapeHtml(r.ad || '') + '">' +
                    '<div class="renk-meta">' + hex + (oneri ? ' · ' + escapeHtml(oneri) : '') + '</div>' +
                '</div>' +
                '<button type="button" class="renk-sil-btn" data-renk-id="' + escapeHtml(r.renk_id) + '" aria-label="Sil">✕</button>' +
            '</div>';
        }).join('');
    }

    function renderOverlayMarkers() {
        if (!overlayLayer) return;
        // Yalnız konumu olan (manuel yakalanan) renkler marker alır; otomatik bulunanların konumu yok.
        overlayLayer.innerHTML = modalRenkler.filter(r => r.secim_noktasi).map(r => {
            const p = r.secim_noktasi;
            const left = (p.x * 100).toFixed(3);
            const top = (p.y * 100).toFixed(3);
            return '<div class="renk-marker-overlay" data-renk-id="' + escapeHtml(r.renk_id) + '" ' +
                'style="left:' + left + '%;top:' + top + '%" title="Renk ' + escapeHtml(r.numara) + ' — ' + escapeHtml(r.hex || '') + '">' +
                '<span class="renk-marker-numara">' + escapeHtml(r.numara) + '</span></div>';
        }).join('');
    }

    // Açıktan koyuya sırala (algısal parlaklık) + 1'den numaralandır, sonra render et.
    function labL(r) {
        const rgb = (r && Array.isArray(r.rgb)) ? r.rgb : [0, 0, 0];
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];   // 0-255, sıralama için tutarlı
    }
    function normalizeAndRender() {
        modalRenkler.sort((a, b) => labL(b) - labL(a));   // en açık üstte
        modalRenkler.forEach((r, i) => { r.numara = i + 1; });
        renderRenkListesi();
        renderOverlayMarkers();
    }

    // Otomatik bulunan her renge fotoğrafta temsilî konum ata (o renge EN YAKIN piksel) → marker gösterilsin.
    function assignPositionsFromImage(colors) {
        const cp = window.ColorPicker;
        if (!cp || typeof cp._rgbToLab !== 'function' || !renkCanvas || !renkCanvas.width || !renkCanvas.height) return;
        const W = renkCanvas.width, H = renkCanvas.height;
        let data;
        try {
            const ctx = renkCanvas.getContext('2d', { willReadFrequently: true });
            data = ctx.getImageData(0, 0, W, H).data;
        } catch (e) { return; }   // tainted canvas → konum atanmaz (marker olmaz, sorun değil)
        const targets = colors.map(c => {
            let lab = Array.isArray(c.lab) ? c.lab : null;
            if (!lab && Array.isArray(c.rgb)) { try { lab = cp._rgbToLab(c.rgb[0], c.rgb[1], c.rgb[2]); } catch (e) {} }
            return { c, lab: lab || [0, 0, 0], bestD: Infinity, x: null, y: null };
        });
        const step = Math.max(2, Math.floor(Math.sqrt((W * H) / 12000)));   // ~12k örnek (hızlı)
        for (let y = 0; y < H; y += step) {
            for (let x = 0; x < W; x += step) {
                const i = (y * W + x) * 4;
                if (data[i + 3] < 128) continue;
                let lab;
                try { lab = cp._rgbToLab(data[i], data[i + 1], data[i + 2]); } catch (e) { continue; }
                for (const t of targets) {
                    const dl = lab[0] - t.lab[0], da = lab[1] - t.lab[1], db = lab[2] - t.lab[2];
                    const d = dl * dl + da * da + db * db;
                    if (d < t.bestD) { t.bestD = d; t.x = x; t.y = y; }
                }
            }
        }
        targets.forEach(t => { if (t.x != null) t.c.secim_noktasi = { x: t.x / W, y: t.y / H }; });
    }

    // Otomatik renk bulma — color-picker'ın K-means dominant renk motoru (Galeri ile aynı).
    function onAutoExtract() {
        const cp = window.ColorPicker;
        if (!cp || typeof cp.extractPalette !== 'function') {
            (window.toast || alert)('Otomatik renk motoru yüklü değil', 'error');
            return;
        }
        const k = parseInt(renkAutoCountSel ? renkAutoCountSel.value : '8', 10) || 8;
        let palette = [];
        try { palette = cp.extractPalette(k) || []; } catch (e) { palette = []; }
        if (!palette.length) { (window.toast || alert)('Renk bulunamadı (önce fotoğraf yüklenmeli)', 'warn'); return; }
        if (modalRenkler.length && !confirm('Mevcut ' + modalRenkler.length + ' renk, otomatik bulunan ' + palette.length + ' renk ile değiştirilsin mi?')) return;
        modalRenkler = palette.map(c => ({
            renk_id: uuid12(),
            numara: 0,
            kod: '',
            ad: (c.name && c.name !== '—') ? c.name : nearestName(c.rgb),
            hex: c.hex,
            rgb: c.rgb,
            lab: c.lab,
            secim_noktasi: null,   // aşağıda en-yakın-piksel ile doldurulur (marker için)
        }));
        assignPositionsFromImage(modalRenkler);   // her renge fotoğrafta temsilî konum → marker
        modalRenklerDirty = true;
        normalizeAndRender();
        scheduleModalSave();
        (window.toast || alert)(palette.length + ' renk bulundu (açıktan koyuya sıralı)', 'success');
    }

    function clearMarkerHighlight() {
        if (!overlayLayer) return;
        overlayLayer.querySelectorAll('.renk-marker-overlay.is-hover-target').forEach(m => m.classList.remove('is-hover-target'));
    }
    function highlightMarker(renkId) {
        clearMarkerHighlight();
        if (!overlayLayer || !renkId) return;
        const m = overlayLayer.querySelector('.renk-marker-overlay[data-renk-id="' + cssEsc(renkId) + '"]');
        if (m) m.classList.add('is-hover-target');
    }
    // Ters yön: marker → liste satırı vurgula (hover)
    function clearRowHighlight() {
        if (!renkListesiEl) return;
        renkListesiEl.querySelectorAll('.renk-satir.is-hover-target').forEach(r => r.classList.remove('is-hover-target'));
    }
    function highlightRow(renkId) {
        clearRowHighlight();
        if (!renkListesiEl || !renkId) return;
        const row = renkListesiEl.querySelector('.renk-satir[data-renk-id="' + cssEsc(renkId) + '"]');
        if (row) row.classList.add('is-hover-target');
    }
    // Marker'a TIKLA → ilgili satırı seç (kaydır + vurgula). Yeni renk EKLENMEZ (click-through engellendi).
    function selectRenkRow(renkId) {
        if (!renkListesiEl || !renkId) return;
        const row = renkListesiEl.querySelector('.renk-satir[data-renk-id="' + cssEsc(renkId) + '"]');
        if (!row) return;
        try { row.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (e) {}
        renkListesiEl.querySelectorAll('.renk-satir.is-selected').forEach(r => r.classList.remove('is-selected'));
        row.classList.add('is-selected');
        highlightMarker(renkId);
    }

    function scheduleModalSave() {
        clearTimeout(modalDebounceTimer);
        setModalStatus('Değişti…', 'dirty');
        modalDebounceTimer = setTimeout(flushModalSave, MODAL_DEBOUNCE_MS);
    }

    async function flushModalSave() {
        if (!modalRenklerDirty || !aktifSayfaId) return;
        setModalStatus('Kaydediliyor…', 'saving');
        try {
            const res = await fetch('/iplik-katalogu/' + encodeURIComponent(kartelaId) + '/sayfa/' + encodeURIComponent(aktifSayfaId) + '/renkler', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ renkler: modalRenkler }),
            });
            let data = null;
            try { data = await res.json(); } catch (e) { data = null; }
            if (data && data.ok) {
                modalRenkler = data.renkler || [];
                modalRenklerDirty = false;
                const sayfa = sayfalar.find(s => s.sayfa_id === aktifSayfaId);
                if (sayfa) sayfa.renkler = data.renkler || [];
                setModalStatus('Kaydedildi ✓', 'ok');
                updateSayfaKartRenkSayisi(aktifSayfaId, (data.renkler || []).length);
                lastSavedSnapshot = snapshot();   // renk kaydı meta auto-save'i kirli yapmasın
            } else {
                setModalStatus('⚠ Kaydedilemedi', 'error');
                (window.toast || alert)((data && data.error) || 'Renkler kaydedilemedi', 'error');
            }
        } catch (e) {
            setModalStatus('⚠ Kaydedilemedi', 'error');
            (window.toast || alert)('Ağ hatası', 'error');
        }
    }

    function updateSayfaKartRenkSayisi(sayfaId, count) {
        if (!sayfaHost) return;
        const card = sayfaHost.querySelector('.sayfa-card[data-sayfa-id="' + cssEsc(sayfaId) + '"]');
        if (!card) return;
        const meta = card.querySelector('.sayfa-meta');
        if (meta) meta.textContent = count + ' renk';
    }

    async function closeRenkModal() {
        clearTimeout(modalDebounceTimer);
        if (modalRenklerDirty) { try { await flushModalSave(); } catch (e) {} }
        if (renkModal) renkModal.hidden = true;
        document.body.style.overflow = '';
        aktifSayfaId = null;
        modalRenkler = [];
        modalRenklerDirty = false;
        try { if (window.ColorPicker) window.ColorPicker.clearPoints(); } catch (e) {}
    }

    // === Bağlama ===
    document.querySelectorAll('[data-k]').forEach(el => {
        el.addEventListener('input', scheduleDirtyCheck);
        el.addEventListener('change', scheduleDirtyCheck);
    });
    if (tipSelect) tipSelect.addEventListener('change', () => { syncTipOther(); scheduleDirtyCheck(); });
    if (otherInput) otherInput.addEventListener('input', scheduleDirtyCheck);
    // Parça 2-A — sayfa yükleme + silme
    if (sayfaInput) sayfaInput.addEventListener('change', onSayfaUpload);
    if (sayfaHost) sayfaHost.addEventListener('click', onSayfaHostClick);
    // Parça 2-B — renk modalı
    if (renkListesiEl) {
        renkListesiEl.addEventListener('input', (e) => {
            const kodInp = e.target.closest('.renk-kod');
            const adInp = e.target.closest('.renk-ad');
            if (!kodInp && !adInp) return;
            const row = e.target.closest('.renk-satir');
            if (!row) return;
            const r = modalRenkler.find(x => x.renk_id === row.dataset.renkId);
            if (!r) return;
            if (kodInp) r.kod = kodInp.value; else r.ad = adInp.value;
            modalRenklerDirty = true;
            scheduleModalSave();
        });
        renkListesiEl.addEventListener('click', (e) => {
            const sil = e.target.closest('.renk-sil-btn');
            if (!sil) return;
            const id = sil.dataset.renkId;
            modalRenkler = modalRenkler.filter(x => x.renk_id !== id);
            modalRenklerDirty = true;
            normalizeAndRender();
            scheduleModalSave();
        });
        renkListesiEl.addEventListener('mouseover', (e) => {
            const row = e.target.closest('.renk-satir');
            if (row) highlightMarker(row.dataset.renkId);
        });
        renkListesiEl.addEventListener('mouseleave', clearMarkerHighlight);
    }
    // Marker etkileşimi: tıkla → satır seç (yeni renk eklemez); hover → satır vurgula
    if (overlayLayer) {
        overlayLayer.addEventListener('click', (e) => {
            const m = e.target.closest('.renk-marker-overlay');
            if (m) selectRenkRow(m.dataset.renkId);
        });
        overlayLayer.addEventListener('mouseover', (e) => {
            const m = e.target.closest('.renk-marker-overlay');
            if (m) highlightRow(m.dataset.renkId);
        });
        overlayLayer.addEventListener('mouseout', (e) => {
            const m = e.target.closest('.renk-marker-overlay');
            if (m) clearRowHighlight();
        });
    }
    if (renkAvgEl) renkAvgEl.addEventListener('change', () => {
        try { if (window.ColorPicker) window.ColorPicker.setAvg(renkAvgEl.checked); } catch (e) {}
    });
    if (renkAutoBtn) renkAutoBtn.addEventListener('click', onAutoExtract);
    const renkClearAllBtn = document.getElementById('renk-clear-all');
    if (renkClearAllBtn) renkClearAllBtn.addEventListener('click', () => {
        if (!modalRenkler.length) return;
        if (!confirm('Tüm renkler silinsin mi?')) return;
        modalRenkler = [];
        normalizeAndRender();
        try { if (window.ColorPicker) window.ColorPicker.clearPoints(); } catch (e) {}
        modalRenklerDirty = true;
        scheduleModalSave();
    });
    const renkModalX = document.getElementById('renk-modal-x');
    const renkModalKapat = document.getElementById('renk-modal-kapat');
    if (renkModalX) renkModalX.addEventListener('click', closeRenkModal);
    if (renkModalKapat) renkModalKapat.addEventListener('click', closeRenkModal);
    if (renkModal) renkModal.addEventListener('click', (e) => { if (e.target === renkModal) closeRenkModal(); });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && renkModal && !renkModal.hidden) closeRenkModal();
    });

    syncTipOther();
    lastSavedSnapshot = snapshot();
    setStatus('', '');
    renderSayfalar();   // mevcut kartela'da sayfa kartlarını bas (yeni'de fieldset gizli)
})();
