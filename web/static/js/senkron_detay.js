/* Senkron tezgah detayı — SÜRÜM atama (ürün seç → sürüm seç) + sıra (yukarı/aşağı) + çıkar.
   Tezgaha atanan birim bir ürün sürümüdür; eksik sürüm atanamaz, sürüm tek tezgahta olabilir.
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

    // --- Ürün listesi (lazy fetch + arama) ---
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
                <div class="snk-pick-row">
                    <div class="snk-pick-thumb">${p.cover_image ? `<img src="${esc(p.cover_image)}" loading="lazy" alt="">` : ''}</div>
                    <div class="snk-pick-body">
                        <div class="snk-pick-name">${esc(p.product_name)}</div>
                        <div class="snk-pick-brand">${esc(p.brand)}</div>
                    </div>
                    <button type="button" class="btn btn-sm btn-secondary snk-pick-toggle">Sürümler</button>
                </div>
                <div class="snk-surum-pick" hidden></div>
            </div>`).join('') : '<div class="snk-empty-inline">Eşleşen ürün yok.</div>';
    }
    if (searchEl) searchEl.addEventListener('input', () => { if (productsCache) renderProducts(); });

    // --- Ürün → sürümleri aç (lazy) ---
    async function openSurumler(card) {
        const box = card.querySelector('.snk-surum-pick');
        const urun_id = card.dataset.urunId;
        if (box.dataset.loaded) { box.hidden = !box.hidden; return; }
        box.innerHTML = '<div class="snk-loading">Sürümler yükleniyor…</div>';
        box.hidden = false;
        const d = await fetch(`/api/senkron/urun/${encodeURIComponent(urun_id)}/surumler`)
            .then(r => r.json()).catch(() => ({ ok: false }));
        if (!d.ok) { box.innerHTML = `<div class="snk-empty-inline">${esc(d.error || 'Hata')}</div>`; return; }
        box.dataset.loaded = '1';
        box.innerHTML = (d.surumler && d.surumler.length)
            ? d.surumler.map(s => {
                const assigned = !!s.assigned_loom_no;
                const disabled = assigned || !s.complete;
                const cls = assigned ? 'snk-surum-opt-assigned' : (!s.complete ? 'snk-surum-opt-eksik' : 'snk-surum-opt-ok');
                const note = assigned ? ` · ${esc(s.assigned_loom_no)}'te`
                    : (!s.complete ? ` · eksik: ${esc((s.eksik || []).join(', '))}` : '');
                return `<button type="button" class="snk-surum-opt ${cls}"${disabled ? ' disabled' : ''}
                    data-surum-id="${esc(s.surum_id)}" title="${esc(s.ad)}${note}">${esc(s.ad)}${note}</button>`;
            }).join('')
            : '<div class="snk-empty-inline">Bu üründe sürüm yok.</div>';
    }

    if (listEl) listEl.addEventListener('click', async (e) => {
        const toggle = e.target.closest('.snk-pick-toggle');
        if (toggle) { openSurumler(toggle.closest('.snk-pick')); return; }
        const opt = e.target.closest('.snk-surum-opt');
        if (!opt || opt.disabled) return;
        const card = opt.closest('.snk-pick');
        opt.disabled = true;
        const d = await post(`/api/senkron/${encodeURIComponent(loomId)}/ata-urun`,
            { urun_id: card.dataset.urunId, surum_id: opt.dataset.surumId });
        if (d.ok && d.added) {
            showStatus('Sürüm atandı.', 'ok');
            setTimeout(() => location.reload(), 450);
        } else if (d.ok) {
            showStatus(d.msg || 'Bu sürüm zaten atalı.', 'error'); opt.disabled = false;
        } else { showStatus(d.error || 'Hata', 'error'); opt.disabled = false; }
    });

    loadProducts();   // tek panel — hemen yükle

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

    // --- Çözgü ekle (Sprint 4): cozgu_plani'ndan seed veya boş ---
    const warpStatus = document.getElementById('snk-warp-status');
    async function addWarp(body) {
        const d = await post('/api/senkron/cozgu/seed-sec', body);
        if (d.ok && d.redirect) { location.href = d.redirect; }
        else if (warpStatus) { warpStatus.textContent = d.error || 'Hata'; warpStatus.dataset.kind = 'error'; }
    }
    const seedAdd = document.getElementById('snk-warp-seed-add');
    if (seedAdd) seedAdd.addEventListener('click', () => {
        const sel = document.getElementById('snk-warp-seed');
        const val = sel ? sel.value : '';
        if (!val) { if (warpStatus) { warpStatus.textContent = 'Önce seed seç'; warpStatus.dataset.kind = 'error'; } return; }
        const [lpId, durum, ci] = val.split('|');
        addWarp({ loom_id: loomId, loom_product_id: lpId, durum, cozgu_idx: parseInt(ci, 10) });
    });
    const blankAdd = document.getElementById('snk-warp-blank-add');
    if (blankAdd) blankAdd.addEventListener('click', () => addWarp({ loom_id: loomId }));
})();
