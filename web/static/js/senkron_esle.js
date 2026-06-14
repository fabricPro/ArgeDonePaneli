/* Senkron Atkı Eşleme (çok-sürümlü) — her sürüm ayrı bölüm: havuz eşleme + Dokuma Sonrası + sürüm aç/kapa.
   set/actual çağrıları satırın bağlı olduğu SÜRÜMÜN surum_id'sini taşır. Master salt okunur. */
(function () {
    const root = document.getElementById('snk-esle');
    if (!root) return;
    const lpId = root.dataset.lpId;
    const post = (url, body) => fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}),
    }).then(r => r.json()).catch(() => ({ ok: false, error: 'Ağ hatası' }));
    const surumOf = (el) => { const s = el.closest('[data-surum-id]'); return s ? s.dataset.surumId : ''; };

    root.addEventListener('change', async (e) => {
        // (a) Sürüm aç/kapa — tüketime girsin mi
        const vsel = e.target.closest('.snk-vselect-cb');
        if (vsel) {
            const d = await post(`/api/senkron/esle/${encodeURIComponent(lpId)}/version`,
                { surum_id: surumOf(vsel), selected: vsel.checked });
            if (d.ok) location.reload();   // bölüm soluk/aktif + havuz tüketimi tazelensin
            return;
        }
        // (b) Havuz eşleme
        const sel = e.target.closest('.snk-map-sel');
        if (sel) {
            const row = sel.closest('.snk-trow');
            sel.disabled = true;
            const d = await post(`/api/senkron/esle/${encodeURIComponent(lpId)}/set`, {
                surum_id: surumOf(row), iplik_index: parseInt(row.dataset.iplikIndex, 10),
                cell_key: row.dataset.cellKey, material_stock_id: sel.value,
            });
            sel.disabled = false;
            const statusCell = row.querySelector('.snk-esle-status');
            statusCell.innerHTML = d.ok
                ? (sel.value ? '<span class="chip snk-chip-ok">eşlendi</span>'
                             : '<span class="chip snk-chip-excluded">tüketime dahil değil</span>')
                : '<span class="chip snk-chip-excluded">' + (d.error || 'hata') + '</span>';
            return;
        }
        // (c) Dokuma Sonrası (dokundu mu / gerçek metre)
        const dv = e.target.closest('.snk-dvrow');
        if (dv) {
            const woven = dv.querySelector('.snk-woven');
            const actual = dv.querySelector('.snk-actual-m');
            await post(`/api/senkron/esle/${encodeURIComponent(lpId)}/actual`, {
                surum_id: surumOf(dv), variant_index: parseInt(dv.dataset.variantIndex, 10),
                woven: woven ? woven.checked : true, actual_m: actual ? actual.value : '',
            });
        }
    });
})();
