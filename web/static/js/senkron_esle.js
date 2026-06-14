/* Senkron Atkı Eşleme — her (atkı pozisyonu, renk) için havuz kalemi seç.
   Eşleme yalnız weft_color_mappings'e yazar; master (atki_varyant_plani) salt okunur.
   Tüketim havuz KALAN'ında canlı hesaplanır (bu sayfa yalnız eşleme yazar). */
(function () {
    const root = document.getElementById('snk-esle');
    if (!root) return;
    const lpId = root.dataset.lpId;

    root.addEventListener('change', async (e) => {
        const sel = e.target.closest('.snk-map-sel');
        if (!sel) return;
        const row = sel.closest('.snk-trow');
        sel.disabled = true;
        const d = await fetch(`/api/senkron/esle/${encodeURIComponent(lpId)}/set`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                iplik_index: parseInt(row.dataset.iplikIndex, 10),
                cell_key: row.dataset.cellKey,
                material_stock_id: sel.value,
            }),
        }).then(r => r.json()).catch(() => ({ ok: false, error: 'Ağ hatası' }));
        sel.disabled = false;
        const statusCell = row.querySelector('.snk-esle-status');
        if (d.ok) {
            statusCell.innerHTML = sel.value
                ? '<span class="chip snk-chip-ok">eşlendi</span>'
                : '<span class="chip snk-chip-excluded">tüketime dahil değil</span>';
        } else {
            statusCell.innerHTML = '<span class="chip snk-chip-excluded">' + (d.error || 'hata') + '</span>';
        }
    });
})();
