/* Senkron Atkı Eşleme (tek sürüm) — havuz eşleme + Dokuma Sonrası.
   Tezgaha atanan birim bir SÜRÜMDÜR (lp.surum_id); set/actual surum'u sunucu lp'den türetir.
   Master salt okunur. */
(function () {
    const root = document.getElementById('snk-esle');
    if (!root) return;
    const lpId = root.dataset.lpId;
    const post = (url, body) => fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}),
    }).then(r => r.json()).catch(() => ({ ok: false, error: 'Ağ hatası' }));

    root.addEventListener('change', async (e) => {
        // (a) Havuz eşleme
        const sel = e.target.closest('.snk-map-sel');
        if (sel) {
            const row = sel.closest('.snk-trow');
            sel.disabled = true;
            const d = await post(`/api/senkron/esle/${encodeURIComponent(lpId)}/set`, {
                iplik_index: parseInt(row.dataset.iplikIndex, 10),
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
        // (b) Dokuma Sonrası (dokundu mu / gerçek metre)
        const dv = e.target.closest('.snk-dvrow');
        if (dv) {
            const woven = dv.querySelector('.snk-woven');
            const actual = dv.querySelector('.snk-actual-m');
            await post(`/api/senkron/esle/${encodeURIComponent(lpId)}/actual`, {
                variant_index: parseInt(dv.dataset.variantIndex, 10),
                woven: woven ? woven.checked : true, actual_m: actual ? actual.value : '',
            });
        }
    });
})();
