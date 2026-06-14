/* Senkron tezgah detayı — ürün atama (klasör/tekil) + sıra (yukarı/aşağı) + çıkar.
   Mutasyon sonrası sayfayı tazeler (sunucu sıralı listeyi yeniden render eder — en sade yol). */
(function () {
    const root = document.getElementById('snk-detay');
    if (!root) return;
    const loomId = (window.SNK && window.SNK.loomId) || root.dataset.loomId;

    const post = (url, body) => fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
    }).then(r => r.json()).catch(() => ({ ok: false, error: 'Ağ hatası' }));

    const statusEl = document.getElementById('snk-assign-status');
    function showStatus(msg, kind) {
        if (!statusEl) return;
        statusEl.hidden = false;
        statusEl.textContent = msg;
        statusEl.dataset.kind = kind || '';
    }
    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g,
            c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    // --- Mod toggle (Klasörden / Tekil) ---
    document.querySelectorAll('.snk-mode-btn').forEach(b => b.addEventListener('click', () => {
        document.querySelectorAll('.snk-mode-btn').forEach(x => x.classList.toggle('is-active', x === b));
        document.querySelectorAll('.snk-assign-pane').forEach(p => { p.hidden = (p.dataset.pane !== b.dataset.mode); });
        if (b.dataset.mode === 'single') loadProducts();
    }));

    // --- Klasörden toplu ata ---
    const folderSel = document.getElementById('snk-folder-select');
    const folderBtn = document.getElementById('snk-folder-add');
    if (folderBtn) folderBtn.addEventListener('click', async () => {
        const album_id = folderSel ? folderSel.value : '';
        if (!album_id) { showStatus('Önce bir klasör seç.', 'error'); return; }
        folderBtn.disabled = true;
        const d = await post(`/api/senkron/${encodeURIComponent(loomId)}/ata-klasor`, { album_id });
        if (d.ok) {
            showStatus(`${d.added} eklendi · ${d.already} zaten vardı (${d.total} üründen)`, 'ok');
            setTimeout(() => location.reload(), 750);
        } else { showStatus(d.error || 'Hata', 'error'); folderBtn.disabled = false; }
    });

    // --- Tekil ürün listesi (lazy fetch + arama) ---
    let productsCache = null;
    const listEl = document.getElementById('snk-product-list');
    const searchEl = document.getElementById('snk-product-search');
    async function loadProducts() {
        if (productsCache) return;
        const d = await fetch('/api/senkron/urunler').then(r => r.json()).catch(() => ({ ok: false }));
        productsCache = (d && d.urunler) || [];
        renderProducts();
    }
    function renderProducts() {
        if (!listEl) return;
        const q = (searchEl ? searchEl.value : '').toLowerCase().trim();
        const rows = productsCache.filter(p =>
            !q || (`${p.brand || ''} ${p.product_name || ''}`).toLowerCase().includes(q)).slice(0, 200);
        listEl.innerHTML = rows.length ? rows.map(p => `
            <div class="snk-pick" data-urun-id="${esc(p.urun_id)}">
                <div class="snk-pick-thumb">${p.cover_image ? `<img src="${esc(p.cover_image)}" loading="lazy" alt="">` : ''}</div>
                <div class="snk-pick-body">
                    <div class="snk-pick-name">${esc(p.product_name)}</div>
                    <div class="snk-pick-brand">${esc(p.brand)}</div>
                </div>
                <button type="button" class="btn btn-sm btn-secondary snk-pick-add">Ekle</button>
            </div>`).join('') : '<div class="snk-empty-inline">Eşleşen ürün yok.</div>';
    }
    if (searchEl) searchEl.addEventListener('input', () => { if (productsCache) renderProducts(); });
    if (listEl) listEl.addEventListener('click', async (e) => {
        const btn = e.target.closest('.snk-pick-add');
        if (!btn) return;
        const card = btn.closest('.snk-pick');
        const urun_id = card.dataset.urunId;
        btn.disabled = true;
        const d = await post(`/api/senkron/${encodeURIComponent(loomId)}/ata-urun`, { urun_id });
        if (d.ok && d.added) {
            showStatus('Eklendi.', 'ok');
            setTimeout(() => location.reload(), 450);
        } else if (d.ok) {
            btn.textContent = 'Zaten var';
        } else { showStatus(d.error || 'Hata', 'error'); btn.disabled = false; }
    });

    // --- Atanan liste: yukarı / aşağı / çıkar ---
    const assigned = document.getElementById('snk-assigned-list');
    if (assigned) assigned.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-act]');
        if (!btn) return;
        const row = btn.closest('.snk-row');
        const lp_id = row.dataset.lpId;
        const act = btn.dataset.act;
        if (act === 'remove') {
            if (!confirm('Ürün tezgahtan çıkarılsın mı? (ürün/galeri etkilenmez)')) return;
            const d = await post(`/api/senkron/${encodeURIComponent(loomId)}/cikar`, { lp_id });
            if (d.ok) location.reload();
        } else {
            const d = await post(`/api/senkron/${encodeURIComponent(loomId)}/sirala`, { lp_id, direction: act });
            if (d.ok && d.moved) location.reload();
        }
    });
})();
