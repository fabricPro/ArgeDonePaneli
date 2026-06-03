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

  /* ============================================================
     v4.0-part-2 Sprint 13 — Çalışma Alanı Albümleri
     ============================================================ */
  let albums = (window.CW_ALBUMS || []).slice();
  let activeAlbumId = '';   // boş string = Tümü
  const tabsEl = $('#cw-album-tabs');

  function escAttr(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function applyAlbumFilter() {
    $$('.cw-card').forEach(card => {
      const cardAlb = card.dataset.albumId || '';
      const show = !activeAlbumId || cardAlb === activeAlbumId;
      card.style.display = show ? '' : 'none';
    });
  }

  function recountAlbumTabs() {
    // Tümü
    const allCnt = items.length;
    const allBtn = tabsEl?.querySelector('.cw-tab[data-album-id=""]');
    if (allBtn) {
      const span = allBtn.querySelector('.cw-tab-cnt');
      if (span) span.textContent = allCnt;
    }
    // Her albüm
    const counts = {};
    items.forEach(it => {
      const a = it.album_id;
      if (a) counts[a] = (counts[a] || 0) + 1;
    });
    tabsEl?.querySelectorAll('.cw-tab[data-album-id]:not([data-album-id=""])').forEach(b => {
      const id = b.dataset.albumId;
      const span = b.querySelector('.cw-tab-cnt');
      if (span) span.textContent = counts[id] || 0;
    });
  }

  function setActiveTab(albId) {
    activeAlbumId = albId || '';
    tabsEl?.querySelectorAll('.cw-tab[data-album-id]').forEach(b => {
      const isActive = (b.dataset.albumId || '') === activeAlbumId;
      b.classList.toggle('is-active', isActive);
      b.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    applyAlbumFilter();
  }

  // Tab click handler (delegation — yeni tab'lar da yakalanır)
  tabsEl?.addEventListener('click', async (e) => {
    // Album menü "⋯"
    const menuBtn = e.target.closest('.cw-tab-menu-btn');
    if (menuBtn) {
      e.preventDefault(); e.stopPropagation();
      const albId = menuBtn.dataset.albumId;
      const album = albums.find(a => a.id === albId);
      const action = prompt(
        `"${album?.name || albId}" albümü:\n` +
        `  1 — Yeniden adlandır\n` +
        `  2 — Sil\n` +
        `(1 veya 2 yaz, vazgeçmek için boş bırak)`
      );
      if (action === '1') {
        const newName = prompt('Yeni isim:', album?.name || '');
        if (newName && newName.trim()) {
          await renameAlbum(albId, newName.trim());
        }
      } else if (action === '2') {
        if (confirm(`"${album?.name || albId}" albümü silinsin mi?\n(İçindeki ürünler "Tümü"de kalır.)`)) {
          await deleteAlbum(albId);
        }
      }
      return;
    }
    // + Yeni Albüm
    if (e.target.closest('#cw-album-new-btn')) {
      e.preventDefault();
      const name = prompt('Yeni albüm adı:');
      if (name && name.trim()) {
        await createAlbum(name.trim());
      }
      return;
    }
    // Tab seçimi
    const tab = e.target.closest('.cw-tab[data-album-id]');
    if (tab && !tab.classList.contains('cw-tab-new')) {
      setActiveTab(tab.dataset.albumId || '');
    }
  });

  async function createAlbum(name) {
    try {
      const res = await fetch('/api/calisma/album/ekle', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      const d = await res.json();
      if (!d.ok) { toast(d.error || 'Hata', 'error'); return; }
      albums = d.albums || [];
      rerenderTabs();
      toast(`"${name}" oluşturuldu`, 'success');
    } catch (err) { toast('Bağlantı hatası', 'error'); }
  }

  async function deleteAlbum(albId) {
    try {
      const res = await fetch(`/api/calisma/album/${albId}/sil`, { method: 'POST' });
      const d = await res.json();
      if (!d.ok) { toast(d.error || 'Hata', 'error'); return; }
      albums = d.albums || [];
      // Local kart membership cleanup
      items.forEach(it => { if (it.album_id === albId) it.album_id = null; });
      $$('.cw-card').forEach(card => {
        if ((card.dataset.albumId || '') === albId) card.dataset.albumId = '';
      });
      if (activeAlbumId === albId) activeAlbumId = '';
      rerenderTabs();
      toast('Albüm silindi', 'success');
    } catch (err) { toast('Bağlantı hatası', 'error'); }
  }

  async function renameAlbum(albId, newName) {
    try {
      const res = await fetch(`/api/calisma/album/${albId}/yeniden-adlandir`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName }),
      });
      const d = await res.json();
      if (!d.ok) { toast(d.error || 'Hata', 'error'); return; }
      albums = d.albums || [];
      rerenderTabs();
      toast('Yeniden adlandırıldı', 'success');
    } catch (err) { toast('Bağlantı hatası', 'error'); }
  }

  function rerenderTabs() {
    if (!tabsEl) return;
    const allBtn = `<button type="button" class="cw-tab ${activeAlbumId === '' ? 'is-active' : ''}" data-album-id="" role="tab" aria-selected="${activeAlbumId === '' ? 'true' : 'false'}">Tümü <span class="cw-tab-cnt">${items.length}</span></button>`;
    const albBtns = albums.map(a => {
      const isAct = a.id === activeAlbumId;
      const dot = a.color ? `<span class="cw-tab-dot" style="background:${escAttr(a.color)}"></span>` : '';
      return `<button type="button" class="cw-tab ${isAct ? 'is-active' : ''}" data-album-id="${escAttr(a.id)}" role="tab" aria-selected="${isAct ? 'true' : 'false'}">${dot}${escAttr(a.name)} <span class="cw-tab-cnt">${a.count || 0}</span><span class="cw-tab-menu-btn" data-album-id="${escAttr(a.id)}" title="Albüm ayarları">⋯</span></button>`;
    }).join('');
    const newBtn = `<button type="button" class="cw-tab cw-tab-new" id="cw-album-new-btn">+ Yeni Albüm</button>`;
    tabsEl.innerHTML = allBtn + albBtns + newBtn;
    recountAlbumTabs();
    applyAlbumFilter();
  }

  // Kart "⋯" menü → albüme taşı
  $$('.cw-card-album-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault(); e.stopPropagation();
      const uid = btn.dataset.urunid;
      if (!albums.length) {
        toast('Önce + Yeni Albüm ile bir albüm yarat', 'warn');
        return;
      }
      // Basit prompt — pratik
      const options = ['(yok / Tümü)'].concat(albums.map(a => a.name));
      const choice = prompt(
        `Bu kumaşı hangi albüme taşı?\n` +
        options.map((n, i) => `  ${i} — ${n}`).join('\n')
      );
      if (choice === null || choice === '') return;
      const idx = parseInt(choice, 10);
      if (isNaN(idx) || idx < 0 || idx > albums.length) {
        toast('Geçersiz seçim', 'warn');
        return;
      }
      const albumId = idx === 0 ? null : albums[idx - 1].id;
      try {
        const res = await fetch('/api/calisma/urun-albume-tasi', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ urun_id: uid, album_id: albumId }),
        });
        const d = await res.json();
        if (!d.ok) { toast(d.error || 'Hata', 'error'); return; }
        albums = d.albums || [];
        // Local güncelle
        const card = $(`.cw-card[data-urunid="${uid}"]`);
        if (card) card.dataset.albumId = albumId || '';
        const it = items.find(i => i.urun_id === uid);
        if (it) it.album_id = albumId || null;
        rerenderTabs();
        toast(albumId ? 'Albüme taşındı' : 'Tümü\'ye alındı', 'success');
      } catch (err) { toast('Bağlantı hatası', 'error'); }
    });
  });

  // Initial filter
  applyAlbumFilter();

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
