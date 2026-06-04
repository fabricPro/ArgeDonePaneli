/* v3.8 Faz 1 + v4.0-part-2 Adım 1 — Teknik Çalışma sekmesi
 *
 * Sürüm yönetimi (yeni/rename/sil/aktif) + Numune Master iç sekme (Analiz/Maliyet/Desen/Tarak)
 * + NUMUNE KÜNYESİ (ad/müşteri/tarih) form bind + Kaydet.
 *
 * v3.8 Faz 1 parametreler/iplikler/tahar/tarak UI'sı v4.0-part-2'de kaldırıldı —
 * Numune Master UI'sından parça parça yeniden inşa ediliyor. Bu nedenle
 * eski [data-key] elementleri DOM'da olmayabilir; loadFormFromSurum bunları
 * tolere eder (sorgu boş döner, hiçbir şey olmaz).
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
    const statusEl = document.getElementById('numune-status-text');
    const statusWrap = statusEl ? statusEl.closest('.numune-status') : null;

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

    // === Forma sürümün değerlerini bas (parametreler + notlar + kunye) ===
    function loadFormFromSurum(surum) {
        if (!grid) return;
        const param = (surum && surum.parametreler) || {};
        // v3.8 Faz 1 legacy: [data-key] elementleri kaldırıldı, ama varsa tolere et
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
        // v4.0-part-2 — NUMUNE KÜNYESİ
        loadKunyeFromSurum(surum);
        // v4.0-part-2 Adım 2.3 — DOKUMA PARAMETRELERİ
        if (typeof loadDokumaFromSurum === 'function') loadDokumaFromSurum(surum);
        // v4.0-part-2 Adım 2.4 — ÜRETİM & FİNİSAJ PARAMETRELERİ
        if (typeof loadUretimFromSurum === 'function') loadUretimFromSurum(surum);
        // v4.0-part-2 Adım 2 — ÇÖZGÜ + ATKI iplikleri
        if (typeof loadIpliklerFromSurum === 'function') loadIpliklerFromSurum(surum);
        // v4.0-part-2 Adım 3 — Desen modülü
        if (window.DesenModule && typeof window.DesenModule.loadFromSurum === 'function') {
            window.DesenModule.loadFromSurum(surum);
        }
        // v4.0-part-2 Adım 4 — Tarak modülü
        if (window.TarakModule && typeof window.TarakModule.loadFromSurum === 'function') {
            window.TarakModule.loadFromSurum(surum);
        }
        // Maliyet UI ilk hesabı
        if (typeof updateMaliyetUI === 'function') updateMaliyetUI();
        // Status göstergesi
        updateNumuneStatus(surum);
    }

    function readFormToSurum() {
        const param = {};
        let notlar = '';
        let hasLegacyParam = false;
        if (grid) {
            grid.querySelectorAll('[data-key]').forEach(el => {
                hasLegacyParam = true;
                const key = el.dataset.key;
                if (key === 'notlar') {
                    notlar = el.value;
                } else {
                    const v = el.value.trim();
                    param[key] = v === '' ? null : Number(v.replace(',', '.'));
                }
            });
        }
        const payload = { kunye: readKunyeFromForm() };
        // v4.0-part-2 Adım 2.3 — DOKUMA parametreleri (ham_en, mamul_en, atki_sikligi)
        if (typeof readDokumaFromForm === 'function') {
            payload.parametreler = { ...(payload.parametreler || {}), ...readDokumaFromForm() };
        }
        // v4.0-part-2 Adım 2.4 — ÜRETİM & FİNİSAJ parametreleri
        if (typeof readUretimFromForm === 'function') {
            payload.parametreler = { ...(payload.parametreler || {}), ...readUretimFromForm() };
        }
        // v4.0-part-2 Adım 2 — iplikler her zaman gönder (UI varsa)
        if (typeof readIpliklerFromState === 'function') {
            payload.iplikler = readIpliklerFromState();
        }
        // v4.0-part-2 Adım 3 — desen
        if (window.DesenModule && typeof window.DesenModule.readToPayload === 'function') {
            payload.desen = window.DesenModule.readToPayload();
        }
        // v4.0-part-2 Adım 4 — tarak
        if (window.TarakModule && typeof window.TarakModule.readToPayload === 'function') {
            payload.tarak = window.TarakModule.readToPayload();
        }
        // v3.8 Faz 1 alanları DOM'da yoksa parametreler/notlar gönderme
        if (hasLegacyParam) {
            payload.parametreler = { ...(payload.parametreler || {}), ...param };
            payload.notlar = notlar;
        }
        return payload;
    }

    // === NUMUNE KÜNYESİ — load + save ===
    // v4.0-part-2 Adım 2.4 — kunye boşsa ürün metadata'sından (window.PRODUCT_CONTEXT) fallback
    // v4.0-part-2 Adım 2.5 — tarih boşsa BUGÜN
    function todayIsoLocal() {
        const d = new Date();
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    }
    function loadKunyeFromSurum(surum) {
        const k = (surum && surum.kunye) || {};
        const ctx = window.PRODUCT_CONTEXT || {};
        const fallbacks = {
            ad: ctx.product_code || ctx.product_name || '',
            musteri: ctx.brand || '',
            tarih: todayIsoLocal()
        };
        document.querySelectorAll('[data-kunye-key]').forEach(el => {
            const key = el.dataset.kunyeKey;
            const v = k[key];
            // Eğer kunye'de değer varsa onu, yoksa product/today fallback'i göster
            el.value = (v != null && String(v).trim() !== '') ? String(v) : (fallbacks[key] || '');
        });
    }

    function readKunyeFromForm() {
        const k = {};
        document.querySelectorAll('[data-kunye-key]').forEach(el => {
            k[el.dataset.kunyeKey] = (el.value || '').trim();
        });
        return k;
    }

    // === Status göstergesi (Kaydedilmemiş / Son kayıt: tarih) ===
    function fmtDateTime(iso) {
        if (!iso) return '';
        try {
            const d = new Date(iso);
            if (isNaN(d.getTime())) return '';
            return d.toLocaleString('tr-TR', {
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit'
            });
        } catch (e) { return ''; }
    }

    // tasarim-v2 Sprint 16 — kısa tarih (sadece gün.ay.yıl, saat yok) toolbar etiketi için
    function fmtDateShort(iso) {
        if (!iso) return '';
        try {
            const d = new Date(iso);
            if (isNaN(d.getTime())) return '';
            const dd = String(d.getDate()).padStart(2, '0');
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            return `${dd}.${mm}.${d.getFullYear()}`;
        } catch (e) { return ''; }
    }

    function updateNumuneStatus(surum) {
        if (!statusEl) return;
        if (!surum) {
            statusEl.textContent = 'Sürüm seçilmedi';
            statusWrap && statusWrap.classList.remove('is-saved');
            return;
        }
        const t = fmtDateTime(surum.guncelleme_tarihi);
        if (!t || surum.guncelleme_tarihi === surum.olusturma_tarihi) {
            // Yeni oluşturulup henüz düzenlenmemiş veya hiç kaydedilmemiş
            statusEl.textContent = 'Kaydedilmemiş numune';
            statusWrap && statusWrap.classList.remove('is-saved');
        } else {
            statusEl.textContent = 'Son kayıt: ' + t;
            statusWrap && statusWrap.classList.add('is-saved');
        }
    }

    // tasarim-v2 Sprint 16 — toolbar'da aktif sürümün son kayıt tarih etiketi
    function updateSurumInfo(surum) {
        const el = document.getElementById('teknik-surum-info');
        if (!el) return;
        if (!surum) { el.textContent = ''; return; }
        const saved = surum.guncelleme_tarihi && surum.guncelleme_tarihi !== surum.olusturma_tarihi;
        el.textContent = saved
            ? `(Son: ${fmtDateShort(surum.guncelleme_tarihi)})`
            : '(yeni — kaydedilmedi)';
    }

    // tasarim-v2 Sprint 16 — ana sekme badge (sürüm > 1) + boş sekme soluk senkronu
    function updateTeknikTabBadge() {
        const tab = document.querySelector('.utab-btn[data-tab="teknik"]');
        if (!tab) return;
        const n = (teknik.surumler || []).length;
        let badge = tab.querySelector('.utab-cnt');
        if (n > 1) {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'utab-cnt';
                tab.appendChild(badge);
            }
            badge.textContent = n;
        } else if (badge) {
            badge.remove();
        }
        tab.classList.toggle('is-empty', n === 0);
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
        // tasarim-v2 Sprint 16 — toolbar tarih etiketi + ana sekme badge/soluk senkronu
        updateSurumInfo(surum);
        updateTeknikTabBadge();
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

    // === Sürüm: yeni oluştur — v4.0-part-2 Adım 8 modal akışı ===
    const modalYeniSurum = document.getElementById('modal-yeni-surum');
    const inputYeniAd = document.getElementById('new-surum-ad');
    const sourceListEl = document.getElementById('surum-source-list');
    const btnConfirmCreate = document.getElementById('btn-confirm-create-surum');

    function openYeniSurumModal() {
        if (!modalYeniSurum) {
            // Fallback: modal yoksa prompt
            return createSurumLegacy();
        }
        // Default ad
        const defaultAd = `v${(teknik.surumler || []).length + 1} — Yeni Sürüm`;
        inputYeniAd.value = defaultAd;

        // Source list: mevcut sürümleri radio olarak doldur
        sourceListEl.innerHTML = '';
        (teknik.surumler || []).forEach(s => {
            const lbl = document.createElement('label');
            lbl.className = 'surum-source-opt';
            lbl.innerHTML = `
                <input type="radio" name="surum-source" value="${s.id}">
                <div>
                    <strong>${escapeHtml(s.ad || s.id)}</strong>
                    <small>${escapeHtml(s.id)} sürümünden 1·Analiz + 2·Desen miras al</small>
                </div>
            `;
            sourceListEl.appendChild(lbl);
        });

        // "Boş başla" default seçili
        const emptyOpt = modalYeniSurum.querySelector('input[name="surum-source"][value=""]');
        if (emptyOpt) emptyOpt.checked = true;

        if (typeof modalYeniSurum.showModal === 'function') {
            modalYeniSurum.showModal();
        } else {
            // Safari ≤14 fallback (dialog desteklemiyor)
            modalYeniSurum.setAttribute('open', '');
        }
        setTimeout(() => inputYeniAd.focus(), 50);
    }

    function closeYeniSurumModal() {
        if (!modalYeniSurum) return;
        if (typeof modalYeniSurum.close === 'function') modalYeniSurum.close();
        else modalYeniSurum.removeAttribute('open');
    }

    async function confirmCreateSurum() {
        const ad = (inputYeniAd.value || '').trim();
        if (!ad) {
            (window.toast || alert)('Sürüm adı zorunlu', 'error');
            inputYeniAd.focus();
            return;
        }
        const sourceRadio = modalYeniSurum.querySelector('input[name="surum-source"]:checked');
        const sourceId = (sourceRadio && sourceRadio.value) || '';

        const body = { ad };
        if (sourceId) body.source_surum_id = sourceId;

        btnConfirmCreate.disabled = true;
        btnConfirmCreate.textContent = 'Oluşturuluyor…';
        try {
            const data = await api('POST', `/api/urun/${encodeURIComponent(URUN_ID)}/teknik/surum`, body);
            if (!data.ok) {
                (window.toast || alert)(data.error || 'Sürüm oluşturulamadı', 'error');
                return;
            }
            teknik.surumler.push(data.surum);
            teknik.active_surum_id = data.active_surum_id;
            const inheritedMsg = sourceId ? ` (${sourceId}'den miras alındı)` : '';
            (window.toast || alert)(`Sürüm oluşturuldu: ${data.surum.ad}${inheritedMsg}`, 'success');
            closeYeniSurumModal();
            renderActive();
            // v4.0-part-2 Adım 8 — Notlar paneline haber ver (yeni sürüm aktif oldu)
            if (window.URUN_TEKNIK_STATE) window.URUN_TEKNIK_STATE.activeSurumId = data.active_surum_id;
            document.dispatchEvent(new CustomEvent('teknik-surum-changed', { detail: { surum_id: data.active_surum_id } }));
        } finally {
            btnConfirmCreate.disabled = false;
            btnConfirmCreate.textContent = 'Oluştur';
        }
    }

    // Eski prompt-based createSurum (modal yoksa fallback için tutulur)
    async function createSurumLegacy() {
        const ad = prompt('Yeni sürüm adı:', `v${teknik.surumler.length + 1} — Yeni Sürüm`);
        if (!ad || !ad.trim()) return;
        const data = await api('POST', `/api/urun/${encodeURIComponent(URUN_ID)}/teknik/surum`, { ad: ad.trim() });
        if (!data.ok) {
            (window.toast || alert)(data.error || 'Sürüm oluşturulamadı', 'error');
            return;
        }
        teknik.surumler.push(data.surum);
        teknik.active_surum_id = data.active_surum_id;
        (window.toast || alert)(`Sürüm oluşturuldu: ${data.surum.ad}`, 'success');
        renderActive();
    }

    function escapeHtml(s) {
        return String(s ?? '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        }[c]));
    }

    yeniBtn && yeniBtn.addEventListener('click', openYeniSurumModal);
    emptyBtn && emptyBtn.addEventListener('click', openYeniSurumModal);
    btnConfirmCreate && btnConfirmCreate.addEventListener('click', confirmCreateSurum);
    // Modal close buttons
    if (modalYeniSurum) {
        modalYeniSurum.querySelectorAll('[data-modal-close]').forEach(btn => {
            btn.addEventListener('click', closeYeniSurumModal);
        });
        // Backdrop click → kapat
        modalYeniSurum.addEventListener('click', (e) => {
            if (e.target === modalYeniSurum) closeYeniSurumModal();
        });
    }

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
        updateSurumInfo(surum);   // tasarim-v2 Sprint 16 — sürüm seçince toolbar tarih etiketi
        // v4.0-part-2 Adım 8 — Notlar paneline ve diğer dış modüllere haber ver
        if (window.URUN_TEKNIK_STATE) window.URUN_TEKNIK_STATE.activeSurumId = newId;
        document.dispatchEvent(new CustomEvent('teknik-surum-changed', { detail: { surum_id: newId } }));
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
        // Status göstergesini yenile (Kaydedilmemiş → Son kayıt: …)
        updateNumuneStatus(updated);
        updateSurumInfo(updated);   // tasarim-v2 Sprint 16 — toolbar tarih etiketi
        (window.toast || alert)('Sürüm kaydedildi', 'success');
    });

    // === v4.0-part-2 Adım 2 — ÇÖZGÜ + ATKI iplik tabloları ===

    const IPLIK_MAX = 8;
    const IPLIK_TIPLER = ['DENYE', 'DTEX', 'NM', 'NE'];

    // İplik metnini parse et → { value, kat }
    // TEKSTİL KONVANSİYONU:
    //   - "*" / "×" / "x" → her zaman KAT ayırıcı (her tip)
    //   - "/" → tip'e göre:
    //       DENYE, DTEX → "/" FİLAMENT sayısı (kat değil! → kat=1)
    //                     örn. "300/96" = 300 DENYE 96 filament, kat=1
    //       NM, NE      → "/" KAT sayısı
    //                     örn. "30/2 NM" = 30 NM, 2 kat
    //
    // Örnekler:
    //   ("300", "DENYE")     → { value: 300, kat: 1 }
    //   ("300*2", "DENYE")   → { value: 300, kat: 2 }    (yıldız her zaman kat)
    //   ("300/96", "DENYE")  → { value: 300, kat: 1 }    (slash filament, kat=1)
    //   ("30/2", "NM")       → { value: 30,  kat: 2 }    (slash NM için kat)
    //   ("20x4", "NE")       → { value: 20,  kat: 4 }
    function parseIplikValue(raw, tip) {
        if (raw === null || raw === undefined || raw === '') return { value: null, kat: 1 };
        const s = String(raw).trim();
        // 1) "*" / "×" / "x" → her zaman kat
        let m = s.match(/^\s*([0-9]+(?:[.,][0-9]+)?)\s*[\*xX×]\s*([0-9]+)\s*$/);
        if (m) {
            const val = parseFloat(m[1].replace(',', '.'));
            const k = parseInt(m[2], 10) || 1;
            return { value: isFinite(val) ? val : null, kat: k };
        }
        // 2) "/" → tip'e bakar
        m = s.match(/^\s*([0-9]+(?:[.,][0-9]+)?)\s*\/\s*([0-9]+)\s*$/);
        if (m) {
            const val = parseFloat(m[1].replace(',', '.'));
            const k = parseInt(m[2], 10) || 1;
            // DENYE/DTEX → "/" filament sayısı, kat=1
            // NM/NE      → "/" kat sayısı
            if (tip === 'NM' || tip === 'NE') {
                return { value: isFinite(val) ? val : null, kat: k };
            } else {
                return { value: isFinite(val) ? val : null, kat: 1 };
            }
        }
        // 3) Düz sayı
        const n = parseFloat(s.replace(',', '.'));
        return { value: isFinite(n) ? n : null, kat: 1 };
    }

    /**
     * İPLİK NUMARALANDIRMA SİSTEMLERİ — DÖNÜŞÜMLER + ANLAMLARI
     * ──────────────────────────────────────────────────────────
     * NM  (Numero Metric)        — 1 GRAM ipliğin METRE cinsinden uzunluğu
     *                              (örn. NM 30 = 1 gram iplik 30 metre)
     * DENYE (Denier)             — 9000 METRE ipliğin GRAM cinsinden ağırlığı
     *                              (örn. 300 Denye = 9000 m iplik 300 gram)
     * DTEX  (Decitex)            — 10000 METRE ipliğin GRAM cinsinden ağırlığı
     *                              (örn. 333 dTex = 10000 m iplik 333 gram)
     * NE   (Ne / Cotton Count)   — 840 yard (≈768.1 m) ipliğin pound (≈453.6 g)
     *                              cinsinden kaç tane sığdığı.
     *                              Pratik dönüşüm: NM = NE × 1.693
     *
     * Bu fonksiyon herhangi bir tipi NM (m/g) eşdeğerine çevirir.
     * → g/m hesabı = 1 / NM     (yani 1 g uzunluk = NM metre olduğundan)
     *
     * DOĞRULAMA (örnek: 300 DENYE):
     *   NM    = 9000 / 300 = 30   m/g
     *   DTEX  = 10000 / 30 = 333.33 (g/10000m)
     *   NE    = 30 / 1.693 = 17.72 (hank/lb)
     *   g/m   = 1 / 30 = 0.0333 g (tek tel için, kat = 1)
     */
    function nmEquivalent(tip, iplikValue) {
        const v = parseFloat(iplikValue);
        if (!isFinite(v) || v <= 0) return null;
        switch (tip) {
            case 'DENYE': return 9000 / v;   // 1g = (9000/Denye) metre
            case 'DTEX':  return 10000 / v;  // 1g = (10000/Dtex) metre
            case 'NM':    return v;          // NM zaten m/g
            case 'NE':    return v * 1.693;  // NE → NM (1.693 = 840*0.9144/453.59)
            default:      return null;
        }
    }

    // g/m hesabı (kat dahil)
    function gPerMt(tip, iplikValue, kat) {
        const nm = nmEquivalent(tip, iplikValue);
        if (nm === null || nm <= 0) return null;
        const k = parseFloat(kat) > 0 ? parseFloat(kat) : 1;
        return k / nm;
    }

    function dollarPerMt(gmt, fiyat) {
        const f = parseFloat(fiyat);
        if (gmt === null || !isFinite(f) || f < 0) return null;
        return (gmt / 1000) * f;   // fiyat $/kg → g'a böl
    }

    function fmtCalc(n, decimals) {
        if (n === null || !isFinite(n)) return '—';
        const d = decimals != null ? decimals : 3;
        return n.toFixed(d).replace(/\.?0+$/, '');
    }

    function genId() {
        return 'yarn_' + Math.random().toString(36).slice(2, 10);
    }

    // Default boş iplik satırı
    // NOT: kat field'ı artık state'te tutulmaz — iplik metninden (parseIplikValue)
    // her çağrıda türetilir. Veride sadece "iplik" metni var ("300*2", "30/3", "300").
    function emptyIplik() {
        return {
            id: genId(),
            tip: 'DENYE',
            iplik: '',
            siklik: '',           // cozgu için tel/cm, atki için tel adedi (yön'e göre anlam)
            fiyat: '',
            // 📊 Kompozisyon panel state
            olcum: {
                icerikler: [],            // [{elyaf, oran_yuzde}] max 6
                oran_yuzde: null          // bu ipliğin kompozisyondaki toplam oranı
            },
            // ⓘ Info panel state — iplik bilgisi (sade)
            bilgi: {
                iplik_adi: '',
                firma_adi: '',
                fason_var: false
            }
        };
    }

    // Açık panel state — her satır için { scale: bool, info: bool }
    const openPanels = {};   // key: rowId → {scale, info}

    // === DOKUMA PARAMETRELERİ — üst kart state ===
    const DOKUMA_KEYS = ['ham_en_cm', 'mamul_en_cm', 'atki_sikligi'];
    function loadDokumaFromSurum(surum) {
        const p = (surum && surum.parametreler) || {};
        DOKUMA_KEYS.forEach(k => {
            const el = document.querySelector(`[data-dokuma-key="${k}"]`);
            if (el) el.value = (p[k] != null) ? p[k] : '';
        });
    }
    function readDokumaFromForm() {
        const out = {};
        DOKUMA_KEYS.forEach(k => {
            const el = document.querySelector(`[data-dokuma-key="${k}"]`);
            if (!el) return;
            const v = el.value.trim();
            if (v === '') out[k] = null;
            else {
                const n = parseFloat(v.replace(',', '.'));
                out[k] = isFinite(n) ? n : null;
            }
        });
        return out;
    }

    // === ÜRETİM & FİNİSAJ PARAMETRELERİ — alt kart state ===
    const URETIM_KEYS = ['tezgah_devri', 'randiman', 'terbiye_fiyat',
                         'genel_fire', 'kursun_sabit', 'ek_malzeme'];
    // v4.0-part-2 Adım 2.5 — default değerler (boş kayıtlarda otomatik gösterilir)
    const URETIM_DEFAULTS = {
        tezgah_devri: 280,
        randiman: 85,
        terbiye_fiyat: 1,
        genel_fire: 5,
        kursun_sabit: 0.25,
        ek_malzeme: null
    };
    function loadUretimFromSurum(surum) {
        const p = (surum && surum.parametreler) || {};
        URETIM_KEYS.forEach(k => {
            const el = document.querySelector(`[data-uretim-key="${k}"]`);
            if (!el) return;
            const v = p[k];
            if (v != null && v !== '') {
                el.value = v;
            } else if (URETIM_DEFAULTS[k] != null) {
                el.value = URETIM_DEFAULTS[k];
            } else {
                el.value = '';
            }
        });
    }
    function readUretimFromForm() {
        const out = {};
        URETIM_KEYS.forEach(k => {
            const el = document.querySelector(`[data-uretim-key="${k}"]`);
            if (!el) return;
            const v = el.value.trim();
            if (v === '') out[k] = null;
            else {
                const n = parseFloat(v.replace(',', '.'));
                out[k] = isFinite(n) ? n : null;
            }
        });
        return out;
    }
    // Üretim input değişimi → maliyet recalc
    document.querySelectorAll('[data-uretim-key]').forEach(el => {
        el.addEventListener('input', () => updateMaliyetUI());
    });

    // Render tek satır — template clone
    function renderIplikRow(row, yon) {
        const tpl = document.getElementById('tpl-iplik-row');
        if (!tpl) return null;
        const node = tpl.content.firstElementChild.cloneNode(true);
        node.dataset.iplikId = row.id;
        node.dataset.yon = yon;
        // Üst field değerleri
        node.querySelector('[data-iplik-key="tip"]').value = row.tip || 'DENYE';
        node.querySelector('[data-iplik-key="iplik"]').value = row.iplik != null ? row.iplik : '';
        node.querySelector('[data-iplik-key="siklik"]').value = row.siklik != null ? row.siklik : '';
        node.querySelector('[data-iplik-key="fiyat"]').value = row.fiyat != null ? row.fiyat : '';
        // Yön'e göre Sıklık label ve placeholder → Atkı için "Tel Adedi"
        const siklikLabelEl = node.querySelector('[data-label-siklik]');
        const siklikInputEl = node.querySelector('[data-iplik-key="siklik"]');
        if (yon === 'atki') {
            if (siklikLabelEl) siklikLabelEl.innerHTML = 'Tel Adedi <em>(toplam)</em>';
            if (siklikInputEl) siklikInputEl.setAttribute('placeholder', '0');
        } else {
            if (siklikLabelEl) siklikLabelEl.innerHTML = 'Sıklık <em>(tel/cm)</em>';
            if (siklikInputEl) siklikInputEl.setAttribute('placeholder', '0');
        }
        // 📊 Olcum panel — oran input + tip kartları kaldırıldı (v4.0-part-2 Adım 2.6)
        const o = row.olcum || {};
        // ⓘ Bilgi panel inputları
        const b = row.bilgi || {};
        const setBilgi = (k, v) => {
            const el = node.querySelector(`[data-bilgi-key="${k}"]`);
            if (!el) return;
            if (el.type === 'checkbox') el.checked = !!v;
            else el.value = v || '';
        };
        setBilgi('iplik_adi', b.iplik_adi);
        setBilgi('firma_adi', b.firma_adi);
        setBilgi('fason_var', b.fason_var);
        // İçerikler — array'den render (artık olcum.icerikler)
        renderIcerikler(node, o.icerikler || []);
        // Açık panel state restore
        const panels = openPanels[row.id] || {};
        if (panels.scale) node.querySelector('[data-panel="scale"]').hidden = false;
        if (panels.info)  node.querySelector('[data-panel="info"]').hidden = false;
        // İlk hesap (üst chip'ler + maliyet UI)
        applyCalc(node, row);
        return node;
    }

    // İçerik satırlarını panel içinde render
    function renderIcerikler(rowNode, icerikler) {
        const host = rowNode.querySelector('[data-icerikler]');
        if (!host) return;
        host.innerHTML = '';
        const tpl = document.getElementById('tpl-iplik-icerik');
        icerikler.forEach((it, idx) => {
            const r = tpl.content.firstElementChild.cloneNode(true);
            r.dataset.idx = idx;
            r.querySelector('.iplik-icerik-elyaf').value = it.elyaf || '';
            r.querySelector('.iplik-icerik-oran').value = (it.oran_yuzde != null) ? it.oran_yuzde : '';
            host.appendChild(r);
        });
        // "+ İçerik ekle" disable
        const addBtn = rowNode.querySelector('[data-icerik-add]');
        if (addBtn) addBtn.disabled = icerikler.length >= 6;
    }

    // v4.0-part-2 Adım 2.6 — Tip eşdeğer kartları KALDIRILDI (kullanıcı istemedi).
    // recomputeOlcumCards artık no-op — geriye dönük çağrılar bozulmasın diye stub kalır.
    function recomputeOlcumCards(/* rowNode, row */) { /* no-op */ }

    // Hesap chips ve renk/not chip güncelle
    // v4.0-part-2 Adım 2.9 — Chip değerleri artık bu ipliğin 1 mt KUMAŞA
    // toplam katkısını gösterir (tek tel g/m değil).
    //   Çözgü:  g/mt = sıklık × ham_en × (g/m_tek_tel)   ($/mt = g/mt × fiyat/1000)
    //   Atkı:   g/mt = tel_adedi × (ham_en/100) × (g/m_tek_tel)
    function applyCalc(node, row) {
        const tip = row.tip;
        const parsed = parseIplikValue(row.iplik, tip);  // → { value, kat } (tip-aware)
        const iplikVal = parsed.value;
        const kat = parsed.kat;
        const gPerM = gPerMt(tip, iplikVal, kat);        // tek tel için g/m

        // Yön + ham_en farkındalığı — 1 mt kumaş için toplam ağırlık + maliyet
        const yon = node.dataset.yon;
        const hamEnEl = document.querySelector('[data-dokuma-key="ham_en_cm"]');
        const hamEn = hamEnEl ? parseFloat(hamEnEl.value) : null;
        const sik = parseFloat(row.siklik);              // çözgüde tel/cm · atkıda tel adedi
        let gmt_kumas = null;
        if (gPerM != null && isFinite(hamEn) && hamEn > 0 && isFinite(sik) && sik > 0) {
            if (yon === 'cozgu')      gmt_kumas = sik * hamEn * gPerM;          // tel/cm × cm × g/m
            else if (yon === 'atki')  gmt_kumas = sik * (hamEn / 100) * gPerM;  // tel × m × g/m
        }
        const fiy = parseFloat(row.fiyat);
        const dmt_kumas = (gmt_kumas != null && isFinite(fiy) && fiy > 0)
                          ? (gmt_kumas * fiy) / 1000 : null;

        // "no" = serbest etiket (iplik metni — kullanıcı ne yazdıysa o)
        const noText = (row.iplik && String(row.iplik).trim())
                       ? `${row.iplik} ${tip}`
                       : '—';
        node.querySelector('[data-calc-out="no"]').textContent = noText;
        node.querySelector('[data-calc-out="kat"]').textContent = kat;
        node.querySelector('[data-calc-out="gmt"]').textContent = fmtCalc(gmt_kumas, 2);
        node.querySelector('[data-calc-out="dmt"]').textContent = fmtCalc(dmt_kumas, 3);
        // İçerik chip — olcum.icerikler birleştir → "50% PES · 50% CO"
        const noteChip = node.querySelector('[data-calc="note"]');
        const ics = (row.olcum && row.olcum.icerikler) || [];
        const icText = ics
            .filter(it => it && it.elyaf && String(it.elyaf).trim())
            .map(it => it.oran_yuzde != null && isFinite(parseFloat(it.oran_yuzde))
                ? `${parseFloat(it.oran_yuzde)}% ${it.elyaf}`
                : it.elyaf)
            .join(' · ');
        if (icText) {
            noteChip.hidden = false;
            node.querySelector('[data-calc-out="kompozisyon"]').textContent = icText;
        } else {
            noteChip.hidden = true;
        }
        // Oran chip kaldırıldı (v4.0-part-2 Adım 2.6)
        const oranChip = node.querySelector('[data-calc="oran"]');
        if (oranChip) oranChip.hidden = true;
        // Action button active state
        const hasInfo = !!(row.bilgi && (
            row.bilgi.iplik_adi || row.bilgi.firma_adi || row.bilgi.fason_var
        ));
        const hasScale = !!(row.olcum &&
            Array.isArray(row.olcum.icerikler) && row.olcum.icerikler.length);
        const infoBtn = node.querySelector('[data-iplik-action="info"]');
        const scaleBtn = node.querySelector('[data-iplik-action="scale"]');
        if (infoBtn)  infoBtn.classList.toggle('is-active', hasInfo);
        if (scaleBtn) scaleBtn.classList.toggle('is-active', hasScale);
        // v4.0-part-2 Adım 2.4 — her input değişiminde maliyet UI'ı yenile
        scheduleMaliyetUpdate();
    }

    // Debounced maliyet recalc — sık input değişikliklerinde performans için
    let _maliyetTimer = null;
    function scheduleMaliyetUpdate() {
        if (_maliyetTimer) return;
        _maliyetTimer = requestAnimationFrame(() => {
            _maliyetTimer = null;
            updateMaliyetUI();
        });
    }

    // State: server'dan gelen + edit edilen iplikler
    let iplikState = { cozgu: [], atki: [] };

    function loadIpliklerFromSurum(surum) {
        const ipl = (surum && surum.iplikler) || {};
        // Backward-compat: eski kayıt → yeni şema
        //   { iplik:300, kat:2 }      → iplik:"300*2"
        //   { kompozisyon:"%100 PES" } → bilgi.icerikler:[{elyaf:"PES",oran:100}]
        //   { oran_yuzde:50 }          → olcum.oran_yuzde:50
        function normalizeRow(r) {
            const base = emptyIplik();
            base.id = (r && r.id) || genId();
            base.tip = (r && r.tip) || 'DENYE';
            base.siklik = r && r.siklik != null ? r.siklik : '';
            base.fiyat = r && r.fiyat != null ? r.fiyat : '';
            base.renk_hex = (r && r.renk_hex) || '';
            base.renk_ad = (r && r.renk_ad) || '';
            // iplik + kat → string
            if (r && r.kat != null && r.kat > 1 && r.iplik != null && r.iplik !== '' &&
                !String(r.iplik).match(/[\*xX×\/]/)) {
                base.iplik = `${r.iplik}*${r.kat}`;
            } else if (r && r.iplik != null) {
                base.iplik = String(r.iplik);
            }
            // olcum (içerikler + oran)
            const o = (r && r.olcum) || {};
            base.olcum = {
                icerikler: Array.isArray(o.icerikler) ? o.icerikler.slice(0, 6) : [],
                oran_yuzde: o.oran_yuzde != null ? o.oran_yuzde :
                            (r && r.oran_yuzde != null ? r.oran_yuzde : null)
            };
            // bilgi (sade — içerikler kaldırıldı)
            const b = (r && r.bilgi) || {};
            base.bilgi = {
                iplik_adi: b.iplik_adi || '',
                firma_adi: b.firma_adi || '',
                fason_var: !!b.fason_var
            };
            // Backward-compat: eski bilgi.icerikler varsa olcum'a taşı
            if (!base.olcum.icerikler.length && b && Array.isArray(b.icerikler) && b.icerikler.length) {
                base.olcum.icerikler = b.icerikler.slice(0, 6);
            }
            // Backward-compat: eski "kompozisyon" string varsa parse et
            if (!base.olcum.icerikler.length && r && r.kompozisyon && r.kompozisyon.trim()) {
                const km = r.kompozisyon.trim();
                const m = km.match(/^%?\s*(\d+(?:[.,]\d+)?)\s*[\s%]*(.+)$/);
                if (m) {
                    base.olcum.icerikler.push({
                        elyaf: m[2].trim(),
                        oran_yuzde: parseFloat(m[1].replace(',', '.'))
                    });
                } else {
                    base.olcum.icerikler.push({ elyaf: km, oran_yuzde: null });
                }
            }
            return base;
        }
        iplikState.cozgu = Array.isArray(ipl.cozgu) ? ipl.cozgu.map(normalizeRow) : [];
        iplikState.atki = Array.isArray(ipl.atki) ? ipl.atki.map(normalizeRow) : [];
        // Açık panel state sıfırla
        for (const k in openPanels) delete openPanels[k];
        renderAllIplikler();
        updateAtkiValidator();
    }

    function renderAllIplikler() {
        ['cozgu', 'atki'].forEach(yon => {
            const host = document.querySelector(`[data-iplik-rows="${yon}"]`);
            const countEl = document.querySelector(`[data-iplik-count="${yon}"]`);
            if (!host) return;
            host.innerHTML = '';
            iplikState[yon].forEach(row => {
                const node = renderIplikRow(row, yon);
                if (node) host.appendChild(node);
            });
            if (countEl) countEl.textContent = iplikState[yon].length;
            // + ekle butonu disable kontrolü
            const addBtn = document.querySelector(`[data-iplik-add="${yon}"]`);
            if (addBtn) addBtn.disabled = iplikState[yon].length >= IPLIK_MAX;
        });
    }

    function findRow(yon, id) {
        return iplikState[yon].find(r => r.id === id) || null;
    }

    // Field değişiklikleri (delegated)
    function bindIplikRowsEvents() {
        ['cozgu', 'atki'].forEach(yon => {
            const host = document.querySelector(`[data-iplik-rows="${yon}"]`);
            if (!host) return;

            // input/change delegation — tek listener tüm panellerde
            const inputHandler = evt => {
                const target = evt.target;
                const rowEl = target.closest('.iplik-row');
                if (!rowEl) return;
                const id = rowEl.dataset.iplikId;
                const row = findRow(yon, id);
                if (!row) return;

                // 1) Üst satır (tip/iplik/siklik/fiyat)
                if (target.dataset.iplikKey) {
                    row[target.dataset.iplikKey] = target.value;
                    applyCalc(rowEl, row);
                    // Atkı sıklık (tel adedi) değiştiğinde validator yenile
                    if (yon === 'atki' && target.dataset.iplikKey === 'siklik') {
                        updateAtkiTelValidator();
                    }
                    return;
                }
                // v4.0-part-2 Adım 2.6 — Olcum panelinde input KALMADI (oran + tip kartları kaldırıldı).
                // İçerik input'ları aşağıda (icerikRow check).
                // 3) Bilgi panel inputları
                if (target.dataset.bilgiKey) {
                    const key = target.dataset.bilgiKey;
                    if (target.type === 'checkbox') row.bilgi[key] = target.checked;
                    else row.bilgi[key] = target.value;
                    applyCalc(rowEl, row);
                    return;
                }
                // 4) İçerik elyaf/oran inputları (artık olcum.icerikler)
                const icerikRow = target.closest('.iplik-icerik-row');
                if (icerikRow) {
                    const idx = parseInt(icerikRow.dataset.idx, 10);
                    if (!isFinite(idx)) return;
                    if (!row.olcum.icerikler[idx]) row.olcum.icerikler[idx] = { elyaf: '', oran_yuzde: null };
                    if (target.classList.contains('iplik-icerik-elyaf')) {
                        row.olcum.icerikler[idx].elyaf = target.value;
                    } else if (target.classList.contains('iplik-icerik-oran')) {
                        const v = target.value.trim();
                        if (v === '') row.olcum.icerikler[idx].oran_yuzde = null;
                        else {
                            const n = parseFloat(v.replace(',', '.'));
                            row.olcum.icerikler[idx].oran_yuzde = isFinite(n) ? n : null;
                        }
                    }
                    applyCalc(rowEl, row);
                    return;
                }
            };
            host.addEventListener('input', inputHandler);
            host.addEventListener('change', inputHandler);  // checkbox için

            // click delegation
            host.addEventListener('click', evt => {
                const target = evt.target;
                const rowEl = target.closest('.iplik-row');
                if (!rowEl) return;
                const id = rowEl.dataset.iplikId;
                const row = findRow(yon, id);
                if (!row) return;

                // 1) İçerik ekle butonu (artık olcum.icerikler)
                if (target.closest('[data-icerik-add]')) {
                    if (!row.olcum.icerikler) row.olcum.icerikler = [];
                    if (row.olcum.icerikler.length >= 6) {
                        (window.toast || alert)('En fazla 6 içerik eklenebilir', 'warn');
                        return;
                    }
                    row.olcum.icerikler.push({ elyaf: '', oran_yuzde: null });
                    renderIcerikler(rowEl, row.olcum.icerikler);
                    applyCalc(rowEl, row);
                    return;
                }
                // 3) İçerik sil
                const delBtn = target.closest('.iplik-icerik-del');
                if (delBtn) {
                    const icerikRow = delBtn.closest('.iplik-icerik-row');
                    const idx = parseInt(icerikRow.dataset.idx, 10);
                    if (isFinite(idx)) {
                        row.olcum.icerikler.splice(idx, 1);
                        renderIcerikler(rowEl, row.olcum.icerikler);
                        applyCalc(rowEl, row);
                    }
                    return;
                }
                // 4) Üst action butonları (paint kaldırıldı)
                const actBtn = target.closest('[data-iplik-action]');
                if (actBtn) {
                    const action = actBtn.dataset.iplikAction;
                    switch (action) {
                        case 'info':   return handleIplikInfo(row, rowEl);
                        case 'scale':  return handleIplikScale(row, rowEl, yon);
                        case 'delete': return handleIplikDelete(yon, id);
                    }
                }
            });
        });
        // + ekle butonları
        document.querySelectorAll('[data-iplik-add]').forEach(btn => {
            btn.addEventListener('click', () => {
                const yon = btn.dataset.iplikAdd;
                if (iplikState[yon].length >= IPLIK_MAX) {
                    (window.toast || alert)(`En fazla ${IPLIK_MAX} iplik eklenebilir`, 'warn');
                    return;
                }
                iplikState[yon].push(emptyIplik());
                renderAllIplikler();
                updateAtkiValidator();
            });
        });
    }

    // Panel aç/kapa — toggle (inline expand)
    function togglePanel(row, rowEl, which) {
        const panel = rowEl.querySelector(`[data-panel="${which}"]`);
        if (!panel) return;
        const wasHidden = panel.hidden;
        panel.hidden = !wasHidden;
        // State sakla (sayfa yenilenirse açık panel kalmaz — bu OK, sadece in-memory)
        if (!openPanels[row.id]) openPanels[row.id] = {};
        openPanels[row.id][which] = !wasHidden;
        // Action button toggle visual
        const actBtn = rowEl.querySelector(`[data-iplik-action="${which === 'scale' ? 'scale' : 'info'}"]`);
        if (actBtn) {
            actBtn.classList.toggle('is-open', !wasHidden);
        }
    }

    function handleIplikInfo(row, rowEl) {
        togglePanel(row, rowEl, 'info');
    }

    function handleIplikScale(row, rowEl, yon) {
        togglePanel(row, rowEl, 'scale');
    }

    function handleIplikDelete(yon, id) {
        const row = findRow(yon, id);
        if (!row) return;
        const label = row.no || (row.iplik ? `${row.iplik} ${row.tip}` : 'bu iplik');
        if (!confirm(`"${label}" satırını sil?`)) return;
        iplikState[yon] = iplikState[yon].filter(r => r.id !== id);
        renderAllIplikler();
        updateAtkiValidator();
    }

    // === Atkı validator (v4.0-part-2 Adım 2.6 — oran input kaldırıldı, sadece tel adedi) ===
    function updateAtkiValidator() {
        updateAtkiTelValidator();
    }

    // Atkı tel adedi validator: Σ(tel_adedi) === atki_sikligi × 100 olmalı
    function updateAtkiTelValidator() {
        const el = document.getElementById('atki-tel-validator');
        if (!el) return;
        const dok = readDokumaFromForm();
        const atkSik = parseFloat(dok.atki_sikligi);
        const expected = (isFinite(atkSik) && atkSik > 0) ? atkSik * 100 : null;
        const rows = iplikState.atki || [];
        let total = 0, hasAny = false;
        rows.forEach(r => {
            const n = parseFloat(r.siklik);     // atki için "siklik" field = tel adedi
            if (isFinite(n) && n > 0) { total += n; hasAny = true; }
        });
        const txt = el.querySelector('.iplik-validator-text');
        if (expected === null) {
            el.dataset.state = 'empty';
            txt.textContent = `Tel adedi: ${Math.round(total)} / — (atkı sıklığı yok)`;
            return;
        }
        const totR = Math.round(total);
        const expR = Math.round(expected);
        txt.textContent = `Tel adedi: ${totR} / ${expR}`;
        if (!hasAny) { el.dataset.state = 'empty'; return; }
        const diff = Math.abs(totR - expR);
        if (diff < 1) el.dataset.state = 'ok';
        else if (totR < expR) el.dataset.state = 'warn';
        else el.dataset.state = 'over';
    }

    // v4.0-part-2 Adım 2.9 — Ham En değişince tüm satır chip'lerini canlı yenile
    function refreshAllRowChips() {
        document.querySelectorAll('.iplik-row').forEach(rowEl => {
            const yon = rowEl.dataset.yon;
            const id = rowEl.dataset.iplikId;
            const row = findRow(yon, id);
            if (row) applyCalc(rowEl, row);
        });
    }

    // Dokuma parametreleri input change → satır chip'leri + atkı tel validator + maliyet recalc
    document.querySelectorAll('[data-dokuma-key]').forEach(el => {
        el.addEventListener('input', () => {
            updateAtkiTelValidator();
            refreshAllRowChips();
            updateMaliyetUI();
        });
    });

    // Validator atki kompozisyon güncellemelerinde — input event'inden de tetiklensin
    document.querySelectorAll('[data-iplik-rows="atki"]').forEach(host => {
        host.addEventListener('input', () => updateAtkiValidator());
    });

    // Iplik state → backend POST body için clean array
    // NOT: "iplik" artık SERBEST METİN (örn. "300*2", "30/3", "300") — number değil.
    //      Kat ondan türetilir, ayrı field yok.
    function readIpliklerFromState() {
        const numOrNull = v => {
            if (v === '' || v == null) return null;
            const n = Number(String(v).replace(',', '.'));
            return isFinite(n) ? n : null;
        };
        const clean = yon => iplikState[yon].map(r => {
            const ics = (r.olcum && Array.isArray(r.olcum.icerikler))
                ? r.olcum.icerikler.filter(it => it && (it.elyaf || it.oran_yuzde != null)).slice(0, 6)
                  .map(it => ({
                      elyaf: (it.elyaf || '').trim(),
                      oran_yuzde: numOrNull(it.oran_yuzde)
                  }))
                : [];
            return {
                id: r.id,
                tip: r.tip,
                iplik: (r.iplik == null) ? '' : String(r.iplik).trim(),
                siklik: numOrNull(r.siklik),     // cozgu: tel/cm, atki: tel adedi
                fiyat: numOrNull(r.fiyat),
                olcum: {
                    icerikler: ics,
                    oran_yuzde: numOrNull(r.olcum && r.olcum.oran_yuzde)
                },
                bilgi: {
                    iplik_adi: (r.bilgi && r.bilgi.iplik_adi) || '',
                    firma_adi: (r.bilgi && r.bilgi.firma_adi) || '',
                    fason_var: !!(r.bilgi && r.bilgi.fason_var)
                }
            };
        });
        return { cozgu: clean('cozgu'), atki: clean('atki') };
    }

    // Bind events bir kez (sayfa yüklenince)
    bindIplikRowsEvents();

    // ============================================================
    // === v4.0-part-2 Adım 2.4 — MALİYET HESABI + UI GÜNCELLEMESİ
    // ============================================================

    // Sabit varsayım (kullanıcı sonradan input'a çevirebilir)
    const ISCILIK_USD_PER_HOUR = 30;     // tezgah saat ücreti (varsayım)
    const KDV_ORANI = 0.18;

    // Tek bir iplik satırı için g/m (kat dahil) — parseIplikValue + gPerMt sarmalı
    function rowGPerMt(row) {
        const parsed = parseIplikValue(row.iplik, row.tip);   // tip-aware parse
        return gPerMt(row.tip, parsed.value, parsed.kat);
    }

    /*
     * AĞIRLIK / TÜKETİM FORMÜLLERİ (kullanıcı standardı)
     * ────────────────────────────────────────────────────
     * 1 metre kumaş için (boy=1m, en=ham_en cm) iplik ağırlığı (gram):
     *
     *   Çözgü g/mt = çözgü_sıklığı (tel/cm) × ham_en (cm) × DENYE/9000
     *              = sıklık × ham_en × g_per_mt
     *
     *   Atkı  g/mt = atkı_tel_adedi × ham_en (mt) × DENYE/9000
     *              = tel_adedi × (ham_en/100) × g_per_mt
     *
     * Maliyet ($/mt) = (g/mt × fiyat $/kg) / 1000
     *
     * NOT: ham_en kullanılır çünkü iplik tüketimi çekme öncesi tarak eninde
     * gerçekleşir; mamul_en (çekme sonrası) gramaj/m² için kullanılır.
     */

    // ÇÖZGÜ g/mt = Σᵢ (sıklıkᵢ × ham_en × g/mᵢ)
    function calcCozguGramaj(hamEn) {
        if (!isFinite(hamEn) || hamEn <= 0) return 0;
        let total = 0;
        iplikState.cozgu.forEach(r => {
            const g = rowGPerMt(r);
            const s = parseFloat(r.siklik);
            if (g && isFinite(s) && s > 0) total += s * hamEn * g;
        });
        return total;
    }

    // ATKI g/mt = Σᵢ (tel_adediᵢ × ham_en_mt × g/mᵢ)
    function calcAtkiGramaj(hamEn) {
        if (!isFinite(hamEn) || hamEn <= 0) return 0;
        const hamEnMt = hamEn / 100;
        let total = 0;
        iplikState.atki.forEach(r => {
            const g = rowGPerMt(r);
            const n = parseFloat(r.siklik);    // atki için "siklik" field = tel adedi
            if (g && isFinite(n) && n > 0) total += n * hamEnMt * g;
        });
        return total;
    }

    // İplik maliyet ($/mt) — her iplik için g/mt × fiyat / 1000
    function calcIplikMaliyet(hamEn) {
        if (!isFinite(hamEn) || hamEn <= 0) return { total: 0, cozgu: 0, atki: 0 };
        const hamEnMt = hamEn / 100;
        let cozgu = 0;
        iplikState.cozgu.forEach(r => {
            const g = rowGPerMt(r);
            const s = parseFloat(r.siklik);
            const f = parseFloat(r.fiyat);
            if (g && isFinite(s) && isFinite(f) && s > 0 && f > 0) {
                // 1 mt kumaş için çözgü gram = s × hamEn × g
                // $/mt = gram × fiyat / 1000
                cozgu += (s * hamEn * g * f) / 1000;
            }
        });
        let atki = 0;
        iplikState.atki.forEach(r => {
            const g = rowGPerMt(r);
            const n = parseFloat(r.siklik);   // tel adedi
            const f = parseFloat(r.fiyat);
            if (g && isFinite(n) && isFinite(f) && n > 0 && f > 0) {
                // 1 mt kumaş için atkı gram = n × hamEnMt × g
                atki += (n * hamEnMt * g * f) / 1000;
            }
        });
        return { total: cozgu + atki, cozgu, atki };
    }

    // Kapasite mt/saat = (rpm × randıman/100 × 60) / (atki_sikligi × 100)
    // Kapasite mt/ay = mt/saat × 24 × 30
    function calcKapasite(uretim, dok) {
        const rpm = parseFloat(uretim.tezgah_devri);
        const rand = parseFloat(uretim.randiman);
        const atkSik = parseFloat(dok.atki_sikligi);
        if (!isFinite(rpm) || !isFinite(rand) || !isFinite(atkSik) ||
            rpm <= 0 || rand <= 0 || atkSik <= 0) return null;
        const mtPerMin = (rpm * (rand / 100)) / (atkSik * 100);
        const mtPerHour = mtPerMin * 60;
        const mtPerMonth = mtPerHour * 24 * 30;
        return { mt_per_hour: mtPerHour, mt_per_month: mtPerMonth };
    }

    // İşçilik ($/mt) = saat_ücreti / kapasite_mt_saat × (1 + KDV)
    function calcIscilik(kapasite) {
        if (!kapasite || !kapasite.mt_per_hour || kapasite.mt_per_hour <= 0) return 0;
        const usdPerMt = ISCILIK_USD_PER_HOUR / kapasite.mt_per_hour;
        return usdPerMt * (1 + KDV_ORANI);
    }

    // Terbiye ($/mt) = (toplam_gramaj / 1000) × terbiye_fiyat
    function calcTerbiye(toplamGramaj, terbiyeFiyat) {
        const f = parseFloat(terbiyeFiyat);
        if (!isFinite(f) || f < 0 || toplamGramaj <= 0) return 0;
        return (toplamGramaj / 1000) * f;
    }

    // Fire ($/mt) = (iplik + işçilik + terbiye) × (fire_% / 100)
    function calcFire(iplik, iscilik, terbiye, firePct) {
        const p = parseFloat(firePct);
        if (!isFinite(p) || p <= 0) return 0;
        return (iplik + iscilik + terbiye) * (p / 100);
    }

    // Kurşum + Ek malzeme ($/mt) sabit
    function calcKursun(uretim) {
        const k = parseFloat(uretim.kursun_sabit);
        const e = parseFloat(uretim.ek_malzeme);
        return (isFinite(k) ? k : 0) + (isFinite(e) ? e : 0);
    }

    // Çekme faktörü (ham_en / mamul_en)
    function calcCekme(dok) {
        const ham = parseFloat(dok.ham_en_cm);
        const mam = parseFloat(dok.mamul_en_cm);
        if (!isFinite(ham) || !isFinite(mam) || ham <= 0 || mam <= 0) return { factor: 1.0, pct: 0 };
        return {
            factor: ham / mam,
            pct: ((ham - mam) / ham) * 100
        };
    }

    // Kumaş içeriği — her elyaf için g/mt ve %
    function calcKumasIcerigi(hamEn, cozguGramaj, atkiGramaj) {
        const map = {};
        if (!isFinite(hamEn) || hamEn <= 0) return [];
        const hamEnMt = hamEn / 100;
        function eklePerSatir(rows, gramajFn) {
            rows.forEach(r => {
                const gContrib = gramajFn(r);
                if (!gContrib || gContrib <= 0) return;
                const icerikler = (r.olcum && r.olcum.icerikler) || [];
                if (!icerikler.length) {
                    map['Belirsiz'] = (map['Belirsiz'] || 0) + gContrib;
                    return;
                }
                icerikler.forEach(it => {
                    if (!it || !it.elyaf) return;
                    const oran = parseFloat(it.oran_yuzde);
                    const pct = isFinite(oran) ? oran / 100 : 0;
                    if (pct <= 0) return;
                    const key = it.elyaf.trim().toUpperCase();
                    map[key] = (map[key] || 0) + gContrib * pct;
                });
            });
        }
        eklePerSatir(iplikState.cozgu, r => {
            const g = rowGPerMt(r);
            const s = parseFloat(r.siklik);
            return (g && isFinite(s) && s > 0) ? s * hamEn * g : 0;
        });
        eklePerSatir(iplikState.atki, r => {
            const g = rowGPerMt(r);
            const n = parseFloat(r.siklik);
            return (g && isFinite(n) && n > 0) ? n * hamEnMt * g : 0;
        });
        const total = cozguGramaj + atkiGramaj;
        return Object.entries(map)
            .map(([name, g]) => ({
                name,
                gram_per_mt: g,
                percent: total > 0 ? (g / total) * 100 : 0
            }))
            .filter(it => it.gram_per_mt > 0)
            .sort((a, b) => b.percent - a.percent);
    }

    // Sayı formatla — Türkçe (virgüllü) tabular
    function fmtTr(n, decimals) {
        if (n == null || !isFinite(n)) return '—';
        const d = decimals != null ? decimals : 3;
        return n.toFixed(d).replace('.', ',');
    }
    function fmtTrInt(n) {
        if (n == null || !isFinite(n)) return '—';
        return Math.round(n).toLocaleString('tr-TR');
    }

    // DAĞILIM donut chart — 5 segment SVG arc
    function renderDagilim(parts, total) {
        const host = document.getElementById('dagilim-segments');
        if (!host) return;
        host.innerHTML = '';
        if (total <= 0) return;
        const colors = {
            iplik: '#5b8def',
            iscilik: '#d4af7f',
            terbiye: '#7fb37f',
            fire: '#e07260',
            kursun: '#8b8a87'
        };
        const order = ['iplik', 'iscilik', 'terbiye', 'fire', 'kursun'];
        const cx = 100, cy = 100, r = 80;
        const c = 2 * Math.PI * r;   // 502.65
        let offset = -25;             // başlangıçta üst-merkez (12 yönü)
        order.forEach(k => {
            const v = parts[k] || 0;
            if (v <= 0) return;
            const pct = v / total;
            const dash = pct * c;
            const seg = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            seg.setAttribute('cx', cx);
            seg.setAttribute('cy', cy);
            seg.setAttribute('r', r);
            seg.setAttribute('fill', 'none');
            seg.setAttribute('stroke', colors[k]);
            seg.setAttribute('stroke-width', '32');
            seg.setAttribute('stroke-dasharray', `${dash} ${c - dash}`);
            seg.setAttribute('stroke-dashoffset', String(-offset));
            seg.setAttribute('transform', `rotate(-90 ${cx} ${cy})`);
            host.appendChild(seg);
            offset += dash;
        });
    }

    // MASTER GÜNCELLEME — her şeyi yeniden hesaplar ve DOM'a yazar
    function updateMaliyetUI() {
        const dok = readDokumaFromForm();
        const uretim = readUretimFromForm();
        const hamEn = parseFloat(dok.ham_en_cm) || 0;
        // Gramaj (g/mt — 1 metre kumaş için iplik ağırlığı)
        const cozguG = calcCozguGramaj(hamEn);
        const atkiG = calcAtkiGramaj(hamEn);
        const totalG = cozguG + atkiG;
        const cekme = calcCekme(dok);
        // Maliyet (ham_en üzerinden — gerçek iplik tüketimi)
        const iplik = calcIplikMaliyet(hamEn);
        const kapasite = calcKapasite(uretim, dok);
        const iscilik = calcIscilik(kapasite);
        const terbiye = calcTerbiye(totalG, uretim.terbiye_fiyat);
        const fire = calcFire(iplik.total, iscilik, terbiye, uretim.genel_fire);
        const kursun = calcKursun(uretim);
        const toplam = iplik.total + iscilik + terbiye + fire + kursun;
        // İçerik dağılımı (g/mt bazında)
        const icerikler = calcKumasIcerigi(hamEn, cozguG, atkiG);
        // === DOM güncelle ===
        const set = (id, txt) => { const el = document.getElementById(id); if (el) el.textContent = txt; };
        set('gramaj-hesaplanan', fmtTr(totalG, 1));
        set('gramaj-cozgu', fmtTr(cozguG, 1));
        set('gramaj-atki', fmtTr(atkiG, 1));
        set('cekme-atki', fmtTr(cekme.factor, 3));
        set('cekme-atki-yuzde', '%' + fmtTr(cekme.pct, 2));
        // Maliyet listesi
        const setCost = (key, val) => {
            const el = document.querySelector(`[data-cost-out="${key}"]`);
            if (el) el.textContent = fmtTr(val, 3);
        };
        setCost('iplik', iplik.total);
        setCost('iscilik', iscilik);
        setCost('terbiye', terbiye);
        setCost('fire', fire);
        setCost('kursun', kursun);
        set('maliyet-toplam', fmtTr(toplam, 3));
        set('foot-gramaj', fmtTr(totalG, 1));
        set('foot-cozgu', fmtTr(cozguG, 1));
        set('foot-atki', fmtTr(atkiG, 1));
        set('foot-kapasite', kapasite ? fmtTrInt(kapasite.mt_per_month) : '—');
        // İçerik chip'leri (v4.0-part-2 Adım 2.11 — yatay flex)
        const empty = document.getElementById('icerik-empty');
        const list = document.getElementById('icerik-list');
        if (list && empty) {
            list.innerHTML = '';
            list.classList.add('icerik-chips');     // CSS yatay flex chip layout
            if (!icerikler.length || totalG <= 0) {
                empty.hidden = false;
                list.hidden = true;
            } else {
                empty.hidden = true;
                list.hidden = false;
                icerikler.forEach(it => {
                    const chip = document.createElement('span');
                    chip.className = 'icerik-chip';
                    chip.innerHTML =
                        `<em class="ic-name">${it.name}</em>` +
                        `<em class="ic-pct">%${fmtTr(it.percent, 1)}</em>` +
                        `<em class="ic-gm">${fmtTr(it.gram_per_mt, 1)} g/mt</em>`;
                    list.appendChild(chip);
                });
            }
        }
        // Dağılım donut
        renderDagilim({
            iplik: iplik.total, iscilik, terbiye, fire, kursun
        }, toplam);
    }

    // === v4.0-part-2 Adım 1 — İç sekme switch (1·Analiz | 2·Desen | 3·Tarak | 4·Notlar) ===
    const NUMUNE_TAB_KEY = 'numune_tab';
    // v4.0-part-2 Sprint 8.4 — Notlar 4. alt-sekme olarak eklendi (sürüm-spesifik)
    const NUMUNE_VALID_TABS = ['analiz', 'desen', 'tarak', 'notlar'];
    const numuneTabBtns = document.querySelectorAll('.numune-tab');
    const numuneSections = document.querySelectorAll('.numune-section');

    function setNumuneTab(name) {
        if (!NUMUNE_VALID_TABS.includes(name)) name = 'analiz';
        numuneTabBtns.forEach(b => {
            const active = b.dataset.numuneTab === name;
            b.classList.toggle('is-active', active);
            b.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        numuneSections.forEach(s => {
            s.hidden = s.dataset.numuneSection !== name;
        });
        try { localStorage.setItem(NUMUNE_TAB_KEY, name); } catch (e) {}
    }

    numuneTabBtns.forEach(b => {
        b.addEventListener('click', () => setNumuneTab(b.dataset.numuneTab));
    });

    // İlk yüklemede tercih edilen sekmeyi aç
    let initialTab = 'analiz';
    try { initialTab = localStorage.getItem(NUMUNE_TAB_KEY) || 'analiz'; } catch (e) {}
    setNumuneTab(initialTab);

    // === v4.0-part-2 Adım 2.10 — Tam Ekran toggle ===
    const FS_KEY = 'teknik_fullscreen';
    const fsBtn = document.getElementById('teknik-fullscreen');

    function setFullscreen(on) {
        document.body.classList.toggle('teknik-fullscreen', !!on);
        try { localStorage.setItem(FS_KEY, on ? '1' : '0'); } catch (e) {}
        // Sayfa scroll'ı en üste (yeni state geçişinde kafa karışmasın)
        if (on) window.scrollTo(0, 0);
    }

    if (fsBtn) {
        fsBtn.addEventListener('click', () => {
            setFullscreen(!document.body.classList.contains('teknik-fullscreen'));
        });
    }

    // İlk yüklemede tercih edilen state'i restore et (yalnız Teknik sekmesi açıkken)
    // Ana sekme nav'ını dinle — Galeri'ye geçince tam ekran otomatik kapanır
    function syncFsToTab() {
        const technicActive = document.querySelector('[data-tab="teknik"]') &&
                              !document.querySelector('[data-tab="teknik"]').hidden;
        if (!technicActive) {
            // Galeri sekmesi → fullscreen'ı kapat (kullanıcı görsele bakmak istiyor)
            if (document.body.classList.contains('teknik-fullscreen')) {
                document.body.classList.remove('teknik-fullscreen');
            }
        } else {
            // Teknik sekmesi açıldı → kaydedilmiş state'i geri yükle
            let saved = '0';
            try { saved = localStorage.getItem(FS_KEY) || '0'; } catch (e) {}
            document.body.classList.toggle('teknik-fullscreen', saved === '1');
        }
    }
    // Ana sekme butonlarına dinleyici (mevcut setTab handler'ından bağımsız)
    document.querySelectorAll('.urun-main-tabs .utab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // setTab kendi setUtab'ından sonra çalışır — kısa bir frame bekle
            requestAnimationFrame(syncFsToTab);
        });
    });
    // Sayfa açılışında başlangıç state
    requestAnimationFrame(syncFsToTab);

    // === Init ===
    renderActive();
})();
