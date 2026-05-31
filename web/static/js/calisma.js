// Çalışma Alanı — split-screen workspace UI
// v4.0-part-2 Sprint 8

(function () {
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const toast = (msg, type) => (window.toast || alert)(msg, type);

  const page = $('#calisma-page');
  const grid = $('#cw-grid');
  const split = $('#cw-split');
  const railList = $('#cw-rail-list');
  const leftIframe = $('#cw-left-iframe');
  const rightIframe = $('#cw-right-iframe');
  const backBtn = $('#cw-back');

  // Aktif ürünleri server-side rendered liste'den oku, JS state'i de güncel tut
  let items = (window.CW_ITEMS || []).slice();
  let activeId = null;

  // ---- Sprint 8.5 — Telefon yatay otomatik kilit ----
  function isMobilePortrait() {
    return window.matchMedia('(max-width: 900px)').matches &&
           window.matchMedia('(orientation: portrait)').matches;
  }

  function isPwaStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches ||
           window.matchMedia('(display-mode: fullscreen)').matches ||
           // iOS Safari standalone
           (window.navigator && window.navigator.standalone === true);
  }

  function tryLockLandscape() {
    // Sadece mobile portrait'ta dene; desktop'ta gereksiz
    if (!isMobilePortrait()) return;
    if (!(screen.orientation && screen.orientation.lock)) return;

    // PWA standalone: lock'u doğrudan dene (fullscreen şart değil)
    screen.orientation.lock('landscape').catch(() => {
      // Browser tab'ında lock'a izin yok — fullscreen alıp tekrar dene
      const el = document.documentElement;
      const reqFs = el.requestFullscreen || el.webkitRequestFullscreen ||
                    el.mozRequestFullScreen || el.msRequestFullscreen;
      if (!reqFs) return;
      try {
        const p = reqFs.call(el);
        Promise.resolve(p).then(() => {
          screen.orientation.lock('landscape').catch(() => {/* iOS no-op */});
        }).catch(() => {});
      } catch (e) {/* ignore */}
    });
  }

  function tryUnlock() {
    try {
      if (screen.orientation && screen.orientation.unlock) {
        screen.orientation.unlock();
      }
    } catch (e) {/* ignore */}
    try {
      const exitFs = document.exitFullscreen || document.webkitExitFullscreen ||
                     document.mozCancelFullScreen || document.msExitFullscreen;
      const fsEl = document.fullscreenElement || document.webkitFullscreenElement;
      if (exitFs && fsEl) exitFs.call(document).catch(() => {});
    } catch (e) {/* ignore */}
  }

  // ---- Mode geçişleri ----
  function selectFabric(urun_id) {
    if (!urun_id) return;
    activeId = urun_id;
    page.dataset.mode = 'focus';
    grid.hidden = true;
    split.hidden = false;
    // iframe URL'leri yükle (paralel)
    leftIframe.src = `/urun/${encodeURIComponent(urun_id)}?embed=calisma-left`;
    rightIframe.src = `/urun/${encodeURIComponent(urun_id)}?embed=calisma-right`;
    renderRail();
    // Title'ı güncelle
    const item = items.find(i => i.urun_id === urun_id);
    if (item) document.title = `${item.product_name} — Çalışma Alanı`;
    // Sprint 8.5 — telefonda otomatik yatay aç (kullanıcı tap'i = user gesture)
    tryLockLandscape();
  }

  function closeSplit() {
    activeId = null;
    page.dataset.mode = 'grid';
    split.hidden = true;
    grid.hidden = false;
    leftIframe.src = 'about:blank';
    rightIframe.src = 'about:blank';
    document.title = 'Çalışma Alanı';
    // Sprint 8.5 — split kapanınca dik moda dön
    tryUnlock();
  }

  function renderRail() {
    railList.innerHTML = '';
    if (!items.length) return;
    items.forEach(item => {
      const li = document.createElement('li');
      li.className = 'cw-rail-item';
      if (item.urun_id === activeId) li.classList.add('is-active');
      li.dataset.urunid = item.urun_id;
      const img = item.cover_image
        ? `<img src="${item.cover_image}" loading="lazy" alt="">`
        : `<div class="cw-rail-noimg"><svg class="icon"><use href="#ic-image"/></svg></div>`;
      li.innerHTML = `
        ${img}
        <div class="cw-rail-text">
          <div class="cw-rail-brand">${escapeHtml(item.brand || '')}</div>
          <div class="cw-rail-name">${escapeHtml(item.product_name || item.urun_id)}</div>
        </div>
      `;
      li.addEventListener('click', () => selectFabric(item.urun_id));
      railList.appendChild(li);
    });
  }

  function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  // ---- Event handlers ----

  // Kart click → split
  $$('.cw-card-main').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      selectFabric(btn.dataset.urunid);
    });
  });

  // Unpin (× butonu)
  $$('.cw-unpin').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const uid = btn.dataset.urunid;
      const card = btn.closest('.cw-card');
      const name = card?.querySelector('.cw-name')?.textContent?.trim() || uid;
      if (!confirm(`"${name}" çalışmadan çıkarılsın mı?`)) return;
      try {
        const res = await fetch('/api/calisma/cikar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ urun_id: uid }),
        });
        const d = await res.json();
        if (d.ok) {
          toast('Çalışmadan çıkarıldı', 'success');
          card?.remove();
          items = items.filter(i => i.urun_id !== uid);
          // Aktif olan çıkarıldıysa kapat
          if (activeId === uid) closeSplit();
          // Tüm liste boşaldıysa empty state göster
          if (!items.length) location.reload();
        } else {
          toast(d.error || 'Çıkarılamadı', 'error');
        }
      } catch (err) {
        toast('Bağlantı hatası', 'error');
      }
    });
  });

  // Geri butonu
  backBtn?.addEventListener('click', closeSplit);

  // ESC → liste'ye dön
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && page.dataset.mode === 'focus') {
      closeSplit();
    }
  });

  // Sprint 8.6 — Manuel "Yatay Aç" butonu (mobil portrait'ta görünür)
  const rotateBtn = $('#cw-rotate-btn');
  if (rotateBtn) {
    rotateBtn.addEventListener('click', () => {
      tryLockLandscape();
    });
  }

  // İlk yüklemede URL hash varsa o ürünü aç (örn. #urun-kvadrat_qs3847)
  const hash = location.hash.slice(1);
  if (hash && hash.startsWith('urun-')) {
    const target = hash.slice(5);
    if (items.some(i => i.urun_id === target)) {
      // Hemen seç
      setTimeout(() => selectFabric(target), 50);
    }
  }
})();
