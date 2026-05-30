/* v3.8 Faz 1 — Teknik Çalışma sekmesi
 *
 * Sürüm yönetimi (yeni/rename/sil/aktif) + 5 temel parametre form bind + Kaydet.
 * İplikler/tahar/tarak placeholder — Faz 2-3'te eklenecek.
 *
 * Veri kaynağı: <script id="teknik-data" type="application/json"> içine server-side gömülmüş JSON.
 * URUN_ID global olarak tanımlı (urun.html script bloğu başında).
 */
(function () {
    "use strict";

    const dataEl = document.getElementById('teknik-data');
    const surumSel = document.getElementById('teknik-surum-select');
    const yeniBtn = document.getElementById('teknik-surum-yeni');
    const renameBtn = document.getElementById('teknik-surum-rename');
    const silBtn = document.getElementById('teknik-surum-sil');
    const pdfBtn = document.getElementById('teknik-pdf');
    const kaydetBtn = document.getElementById('teknik-kaydet');
    const emptyBtn = document.getElementById('teknik-empty-new');
    const grid = document.getElementById('teknik-grid');
    const emptyEl = document.querySelector('.teknik-empty');

    if (!dataEl || !surumSel) return;

    let teknik;
    try {
        teknik = JSON.parse(dataEl.textContent || '{}');
    } catch (e) {
        teknik = {};
    }
    if (!teknik || typeof teknik !== 'object') teknik = {};
    if (!Array.isArray(teknik.surumler)) teknik.surumler = [];

    const URUN_ID = window.URUN_ID || (document.querySelector('[data-urun-id]') || {}).dataset?.urunId;

    // === Helpers ===
    function findSurum(id) {
        return teknik.surumler.find(s => s.id === id) || null;
    }
    function activeSurum() {
        return findSurum(teknik.active_surum_id) || teknik.surumler[0] || null;
    }
    function fmtNum(v) {
        if (v === null || v === undefined || v === '') return '';
        const n = Number(v);
        if (!isFinite(n)) return '';
        // 0.0 görünmesini önle, ama 0 girilebilir
        return Number.isInteger(n) ? String(n) : String(n);
    }

    // === Forma sürümün değerlerini bas ===
    function loadFormFromSurum(surum) {
        if (!grid) return;
        const param = (surum && surum.parametreler) || {};
        grid.querySelectorAll('[data-key]').forEach(el => {
            const key = el.dataset.key;
            if (key === 'notlar') {
                el.value = (surum && surum.notlar) || '';
            } else if (param.hasOwnProperty(key)) {
                el.value = fmtNum(param[key]);
            } else {
                el.value = '';
            }
        });
    }

    function readFormToSurum() {
        const param = {};
        let notlar = '';
        grid.querySelectorAll('[data-key]').forEach(el => {
            const key = el.dataset.key;
            if (key === 'notlar') {
                notlar = el.value;
            } else {
                const v = el.value.trim();
                param[key] = v === '' ? null : Number(v.replace(',', '.'));
            }
        });
        return { parametreler: param, notlar };
    }

    function refreshButtonsAndVisibility() {
        const has = teknik.surumler.length > 0;
        renameBtn && (renameBtn.disabled = !has);
        silBtn && (silBtn.disabled = !has);
        kaydetBtn && (kaydetBtn.disabled = !has);
        if (pdfBtn) {
            pdfBtn.hidden = !has;
            const surum = activeSurum();
            pdfBtn.href = surum ? `/api/urun/${encodeURIComponent(URUN_ID)}/teknik/${encodeURIComponent(surum.id)}/pdf` : '#';
        }
        if (grid) grid.hidden = !has;
        if (emptyEl) emptyEl.style.display = has ? 'none' : '';
    }

    function refreshDropdown() {
        surumSel.innerHTML = '';
        if (!teknik.surumler.length) {
            const opt = document.createElement('option');
            opt.value = ''; opt.textContent = '— Sürüm yok —';
            surumSel.appendChild(opt);
            return;
        }
        teknik.surumler.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = s.ad;
            if (s.id === teknik.active_surum_id) opt.selected = true;
            surumSel.appendChild(opt);
        });
    }

    function renderActive() {
        refreshDropdown();
        refreshButtonsAndVisibility();
        const surum = activeSurum();
        loadFormFromSurum(surum);
    }

    // === API helpers ===
    async function api(method, url, body) {
        const opts = { method, headers: { 'Content-Type': 'application/json' } };
        if (body !== undefined) opts.body = JSON.stringify(body);
        const res = await fetch(url, opts);
        let data;
        try { data = await res.json(); } catch (e) { data = { ok: false, error: 'JSON parse hatası' }; }
        return data;
    }

    // === Sürüm: yeni oluştur ===
    async function createSurum() {
        const ad = prompt('Yeni sürüm adı:', `v${teknik.surumler.length + 1} — Standart 2026`);
        if (!ad || !ad.trim()) return;
        const data = await api('POST', `/api/urun/${encodeURIComponent(URUN_ID)}/teknik/surum`, { ad: ad.trim() });
        if (!data.ok) {
            (window.toast || alert)(data.error || 'Sürüm oluşturulamadı', 'error');
            return;
        }
        (window.toast || alert)(`Sürüm oluşturuldu: ${data.surum.ad}`, 'success');
        // v3.9: numune-react'in yeni sürümle remount olabilmesi için reload
        setTimeout(() => location.reload(), 400);
    }

    yeniBtn && yeniBtn.addEventListener('click', createSurum);
    emptyBtn && emptyBtn.addEventListener('click', createSurum);

    // === Sürüm: aktif değiştir ===
    surumSel.addEventListener('change', async () => {
        const newId = surumSel.value;
        if (!newId || newId === teknik.active_surum_id) return;
        const data = await api('POST', `/api/urun/${encodeURIComponent(URUN_ID)}/teknik/aktif`, { surum_id: newId });
        if (!data.ok) {
            (window.toast || alert)(data.error || 'Aktif sürüm değiştirilemedi', 'error');
            return;
        }
        teknik.active_surum_id = newId;
        const surum = activeSurum();
        loadFormFromSurum(surum);
        refreshButtonsAndVisibility();
    });

    // === Sürüm: yeniden adlandır ===
    renameBtn && renameBtn.addEventListener('click', async () => {
        const surum = activeSurum();
        if (!surum) return;
        const yeni = prompt('Yeni sürüm adı:', surum.ad);
        if (!yeni || !yeni.trim() || yeni.trim() === surum.ad) return;
        const data = await api('POST', `/api/urun/${encodeURIComponent(URUN_ID)}/teknik/${encodeURIComponent(surum.id)}/ad`, { yeni_ad: yeni.trim() });
        if (!data.ok) {
            (window.toast || alert)(data.error || 'Yeniden adlandırılamadı', 'error');
            return;
        }
        surum.ad = data.ad;
        renderActive();
        (window.toast || alert)('Sürüm adı güncellendi', 'success');
    });

    // === Sürüm: sil ===
    silBtn && silBtn.addEventListener('click', async () => {
        const surum = activeSurum();
        if (!surum) return;
        if (!confirm(`"${surum.ad}" sürümünü silmek istediğine emin misin?`)) return;
        const res = await fetch(`/api/urun/${encodeURIComponent(URUN_ID)}/teknik/${encodeURIComponent(surum.id)}`, { method: 'DELETE' });
        const data = await res.json();
        if (!data.ok) {
            (window.toast || alert)(data.error || 'Sürüm silinemedi', 'error');
            return;
        }
        teknik.surumler = teknik.surumler.filter(s => s.id !== surum.id);
        teknik.active_surum_id = data.active_surum_id;
        renderActive();
        (window.toast || alert)('Sürüm silindi', 'success');
    });

    // === Kaydet ===
    kaydetBtn && kaydetBtn.addEventListener('click', async () => {
        const surum = activeSurum();
        if (!surum) return;
        const payload = readFormToSurum();
        const data = await api('POST', `/api/urun/${encodeURIComponent(URUN_ID)}/teknik/${encodeURIComponent(surum.id)}`, payload);
        if (!data.ok) {
            (window.toast || alert)(data.error || 'Kayıt hatası', 'error');
            return;
        }
        // Local state'i güncelle
        const updated = data.surum;
        const idx = teknik.surumler.findIndex(s => s.id === surum.id);
        if (idx >= 0) teknik.surumler[idx] = updated;
        (window.toast || alert)('Sürüm kaydedildi', 'success');
    });

    // === Init ===
    renderActive();
})();
