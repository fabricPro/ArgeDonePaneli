/* Senkron Çözgü düzenle — warp alanları + yarn havuz eşleme + metre dağıtım.
   Master (cozgu_plani) salt okunur; yazma yalnız warps/warp_yarns/warp_product_allocations. */
(function () {
    const root = document.getElementById('snk-cozgu');
    if (!root) return;
    const warpId = root.dataset.warpId;
    const loomId = root.dataset.loomId;

    const post = (url, body) => fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
    }).then(r => r.json()).catch(() => ({ ok: false, error: 'Ağ hatası' }));
    const $ = id => document.getElementById(id);
    const numOrNull = v => { const s = String(v == null ? '' : v).trim(); return s === '' ? null : s; };
    function setStatus(el, msg, kind) { if (el) { el.textContent = msg || ''; el.dataset.kind = kind || ''; } }

    // --- Warp alanlarını kaydet ---
    if ($('snk-cozgu-save')) $('snk-cozgu-save').addEventListener('click', async () => {
        const body = {};
        root.querySelectorAll('[data-wk]').forEach(el => { body[el.dataset.wk] = numOrNull(el.value); });
        const d = await post(`/api/senkron/cozgu/${encodeURIComponent(warpId)}/kaydet`, body);
        setStatus($('snk-cozgu-status'), d.ok ? 'Kaydedildi — en/işbağ güncelleniyor…' : (d.error || 'Hata'), d.ok ? 'ok' : 'error');
        if (d.ok) setTimeout(() => location.reload(), 500);   // türetilen (en uyarısı/işbağ) tazelensin
    });

    // --- Çözgüyü sil ---
    if ($('snk-cozgu-del')) $('snk-cozgu-del').addEventListener('click', async () => {
        if (!confirm('Çözgü silinsin mi? (iplik eşlemeleri + metre dağıtımları da gider)')) return;
        const d = await post(`/api/senkron/cozgu/${encodeURIComponent(warpId)}/sil`, {});
        if (d.ok) location.href = d.redirect || `/senkron/${encodeURIComponent(loomId)}`;
    });

    // --- Yarn → havuz eşleme ---
    root.addEventListener('change', async (e) => {
        const sel = e.target.closest('.snk-wy-sel');
        if (!sel) return;
        const row = sel.closest('.snk-wyrow');
        sel.disabled = true;
        const d = await post(`/api/senkron/cozgu/${encodeURIComponent(warpId)}/yarn/${encodeURIComponent(row.dataset.wyId)}/eslem`,
            { material_stock_id: sel.value });
        sel.disabled = false;
        if (!d.ok) setStatus($('snk-cozgu-status'), d.error || 'Eşleme hatası', 'error');
    });

    // --- Metre dağıtım ekle ---
    if ($('snk-alloc-add-btn')) $('snk-alloc-add-btn').addEventListener('click', async () => {
        const lp = $('snk-alloc-lp').value;
        const m = $('snk-alloc-m').value;
        if (!lp) { return; }
        const d = await post(`/api/senkron/cozgu/${encodeURIComponent(warpId)}/allocate`,
            { loom_product_id: lp, allocated_m: numOrNull(m) });
        if (d.ok) location.reload();   // Σ / kalan / uyarı tazelensin
    });

    // --- Dağıtım kaldır ---
    const allocList = $('snk-alloc-list');
    if (allocList) allocList.addEventListener('click', async (e) => {
        const btn = e.target.closest('.snk-alloc-del');
        if (!btn) return;
        const row = btn.closest('.snk-alloc-row');
        const d = await post(`/api/senkron/cozgu/${encodeURIComponent(warpId)}/allocate-sil`,
            { alloc_id: row.dataset.allocId });
        if (d.ok) location.reload();
    });
})();
