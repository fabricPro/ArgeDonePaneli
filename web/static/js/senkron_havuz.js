/* Senkron İplik Havuzu — katalogdan ekle + hızlı ekle + satır kg/notes kaydet/sil.
   Katalog SALT OKUNUR (picker window.SNK_KATALOG'tan); hızlı-ekle sunucuda mevcut
   katalog yazma yolundan geçer. Mutasyon sonrası sayfa tazelenir (en sade yol). */
(function () {
    const root = document.getElementById('snk-havuz');
    if (!root) return;
    const KATALOG = window.SNK_KATALOG || [];

    const post = (url, body) => fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
    }).then(r => r.json()).catch(() => ({ ok: false, error: 'Ağ hatası' }));
    const $ = id => document.getElementById(id);
    function setStatus(el, msg, kind) { if (el) { el.textContent = msg || ''; el.dataset.kind = kind || ''; } }
    function numOrNull(v) { const s = String(v == null ? '' : v).trim(); return s === '' ? null : s; }

    // --- Kartela <select>'leri doldur (ekle paneli + hızlı-ekle mevcut) ---
    function fillKartelaSelect(sel) {
        if (!sel) return;
        KATALOG.forEach(k => {
            const o = document.createElement('option');
            o.value = k.kartela_id;
            const meta = [k.iplik_tipi, k.iplik_numarasi].filter(Boolean).join(' ');
            o.textContent = (k.ad || k.kartela_id) + (meta ? ` (${meta})` : '');
            sel.appendChild(o);
        });
    }
    fillKartelaSelect($('snk-kartela-sel'));
    fillKartelaSelect($('snk-quick-kartela'));

    // --- Panel aç/kapa ---
    function showPanel(id, on) { const p = $(id); if (p) p.hidden = !on; }
    if ($('snk-add-toggle')) $('snk-add-toggle').addEventListener('click', () => {
        const p = $('snk-add-panel'); showPanel('snk-add-panel', p.hidden); showPanel('snk-quick-panel', false);
    });
    if ($('snk-quick-toggle')) $('snk-quick-toggle').addEventListener('click', () => {
        const p = $('snk-quick-panel'); showPanel('snk-quick-panel', p.hidden); showPanel('snk-add-panel', false);
    });
    document.querySelectorAll('[data-close-panel]').forEach(b =>
        b.addEventListener('click', () => showPanel(b.dataset.closePanel, false)));

    // --- Katalogdan ekle: kartela → renk listesi + swatch ---
    const kartelaSel = $('snk-kartela-sel');
    const renkSel = $('snk-renk-sel');
    const swatch = $('snk-add-swatch');
    function colorsOf(kid) { const k = KATALOG.find(x => x.kartela_id === kid); return (k && k.colors) || []; }
    if (kartelaSel) kartelaSel.addEventListener('change', () => {
        const cols = colorsOf(kartelaSel.value);
        renkSel.innerHTML = '<option value="">— Renk seç —</option>' +
            cols.map(c => `<option value="${c.renk_id}" data-hex="${c.hex || ''}">${(c.ad || c.renk_id)}</option>`).join('');
        renkSel.disabled = !cols.length;
        if (swatch) swatch.style.background = 'transparent';
    });
    if (renkSel) renkSel.addEventListener('change', () => {
        const opt = renkSel.selectedOptions[0];
        if (swatch) swatch.style.background = (opt && opt.dataset.hex) || 'transparent';
    });
    if ($('snk-add-save')) $('snk-add-save').addEventListener('click', async () => {
        const kartela_id = kartelaSel.value, renk_id = renkSel.value;
        if (!kartela_id || !renk_id) { setStatus($('snk-add-status'), 'Kartela ve renk seç', 'error'); return; }
        const d = await post('/api/senkron/havuz/ekle', {
            kartela_id, renk_id,
            planned_purchase_kg: numOrNull($('snk-add-planned').value),
            actual_purchase_kg: numOrNull($('snk-add-actual').value),
            notes: $('snk-add-notes').value,
        });
        if (d.ok) { setStatus($('snk-add-status'), 'Eklendi', 'ok'); setTimeout(() => location.reload(), 500); }
        else setStatus($('snk-add-status'), d.error || 'Hata', 'error');
    });

    // --- Hızlı ekle: mod toggle + kaydet ---
    document.querySelectorAll('.snk-mode-btn[data-qmode]').forEach(b => b.addEventListener('click', () => {
        document.querySelectorAll('.snk-mode-btn[data-qmode]').forEach(x => x.classList.toggle('is-active', x === b));
        document.querySelectorAll('.snk-quick-pane').forEach(p => { p.hidden = (p.dataset.qpane !== b.dataset.qmode); });
    }));
    function quickMode() {
        const active = document.querySelector('.snk-mode-btn[data-qmode].is-active');
        return active ? active.dataset.qmode : 'existing';
    }
    if ($('snk-quick-save')) $('snk-quick-save').addEventListener('click', async () => {
        const renk_ad = $('snk-q-renk-ad').value.trim();
        if (!renk_ad) { setStatus($('snk-quick-status'), 'Renk adı zorunlu', 'error'); return; }
        const body = {
            renk_ad, renk_hex: $('snk-q-renk-hex').value,
            planned_purchase_kg: numOrNull($('snk-q-planned').value),
        };
        if (quickMode() === 'existing') {
            body.kartela_id = $('snk-quick-kartela').value;
            if (!body.kartela_id) { setStatus($('snk-quick-status'), 'Kartela seç', 'error'); return; }
        } else {
            body.kartela_ad = $('snk-q-kartela-ad').value.trim();
            body.iplik_tipi = $('snk-q-iplik-tipi').value.trim();
            body.iplik_numarasi = $('snk-q-iplik-no').value.trim();
            if (!body.kartela_ad) { setStatus($('snk-quick-status'), 'Kartela adı zorunlu', 'error'); return; }
        }
        const d = await post('/api/senkron/havuz/hizli-ekle', body);
        if (d.ok) {
            setStatus($('snk-quick-status'), d.already ? 'Kataloğa eklendi (havuzda zaten vardı)' : 'Kataloğa + havuza eklendi', 'ok');
            setTimeout(() => location.reload(), 650);
        } else setStatus($('snk-quick-status'), d.error || 'Hata', 'error');
    });

    // --- Tezgah filtresi (Sprint 3: atkı eşlemesi üzerinden CANLI) ---
    const filterSel = $('snk-filter-loom');
    if (filterSel) filterSel.addEventListener('change', () => {
        const loom = filterSel.value;
        document.querySelectorAll('.snk-trow').forEach(row => {
            const ids = (row.dataset.loomIds || '').split(',').filter(Boolean);
            row.style.display = (!loom || ids.includes(loom)) ? '' : 'none';
        });
    });

    // --- Tablo satırı: kaydet / sil ---
    const table = $('snk-table');
    if (table) table.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-act]'); if (!btn) return;
        const row = btn.closest('.snk-trow'); const ms_id = row.dataset.msId;
        if (btn.dataset.act === 'remove') {
            if (!confirm('Bu iplik+renk havuzdan silinsin mi? (katalog etkilenmez)')) return;
            const d = await post(`/api/senkron/havuz/${encodeURIComponent(ms_id)}/sil`, {});
            if (d.ok) location.reload();
        } else {
            const d = await post(`/api/senkron/havuz/${encodeURIComponent(ms_id)}/guncelle`, {
                planned_purchase_kg: numOrNull(row.querySelector('.snk-kg-planned').value),
                actual_purchase_kg: numOrNull(row.querySelector('.snk-kg-actual').value),
                notes: row.querySelector('.snk-note-inp').value,
            });
            btn.classList.toggle('snk-saved-ok', !!d.ok);
            if (d.ok) setTimeout(() => btn.classList.remove('snk-saved-ok'), 1200);
        }
    });
})();
