// Çalışma Alanı — split-screen workspace UI
// v4.0-part-2 Sprint 8

(function () {
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const toast = (msg, type) => (window.toast || alert)(msg, type);

  const page = $('#calisma-page');
  const grid = $('#cw-grid');
  const browse = $('#cw-browse');   // Faz 3 — ağaç + grid sarmalı
  const split = $('#cw-split');
  const railList = $('#cw-rail-list');
  const leftIframe = $('#cw-left-iframe');
  const rightIframe = $('#cw-right-iframe');
  const backBtn = $('#cw-back');
  const divider = $('#cw-divider');

  // ---- tasarim-v2 — Ayarlanabilir split oranı (sol pane payı 0.15–0.85) ----
  const SPLIT_KEY = 'cw_split_ratio';
  let splitRatio = 0.5;
  try { const v = parseFloat(localStorage.getItem(SPLIT_KEY)); if (v >= 0.15 && v <= 0.85) splitRatio = v; } catch (e) {}
  function applySplitRatio() {
    if (!split) return;
    split.style.setProperty('--cw-l', splitRatio.toFixed(4) + 'fr');
    split.style.setProperty('--cw-r', (1 - splitRatio).toFixed(4) + 'fr');
  }
  function dividerHiddenNow() {
    return split.hidden ||
      document.body.classList.contains('cw-fullscreen') ||
      window.matchMedia('(max-width: 900px) and (orientation: portrait)').matches;
  }
  function positionDivider() {
    if (!divider || !split) return;
    if (dividerHiddenNow()) { divider.hidden = true; return; }
    const lp = $('#cw-left-pane');
    if (!lp || !lp.offsetParent) { divider.hidden = true; return; }
    const gap = parseFloat(getComputedStyle(split).columnGap) || 24;
    divider.hidden = false;
    divider.style.left = (lp.offsetLeft + lp.offsetWidth + gap / 2) + 'px';
  }
  function dragSplitTo(clientX) {
    const lp = $('#cw-left-pane'), rp = $('#cw-right-pane');
    if (!lp || !rp) return;
    const rect = split.getBoundingClientRect();
    const gap = parseFloat(getComputedStyle(split).columnGap) || 24;
    const paneStart = lp.offsetLeft;
    const paneEnd = rp.offsetLeft + rp.offsetWidth;
    const total = (paneEnd - paneStart) - gap;   // iki pane içeriği (orta gap hariç)
    if (total <= 0) return;
    let f = (clientX - rect.left - paneStart) / total;
    f = Math.max(0.15, Math.min(0.85, f));
    splitRatio = f;
    applySplitRatio();
    positionDivider();
  }
  if (divider) {
    divider.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      divider.classList.add('is-dragging');
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'col-resize';
      if (leftIframe) leftIframe.style.pointerEvents = 'none';   // iframe drag'i yutmasın
      if (rightIframe) rightIframe.style.pointerEvents = 'none';
      const move = (ev) => dragSplitTo(ev.clientX);
      const up = () => {
        divider.classList.remove('is-dragging');
        document.body.style.userSelect = '';
        document.body.style.cursor = '';
        if (leftIframe) leftIframe.style.pointerEvents = '';
        if (rightIframe) rightIframe.style.pointerEvents = '';
        try { localStorage.setItem(SPLIT_KEY, splitRatio.toFixed(4)); } catch (e2) {}
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerup', up);
        window.removeEventListener('pointercancel', up);
      };
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', up);
      window.addEventListener('pointercancel', up);
    });
    // Çift tık → 50/50 sıfırla
    divider.addEventListener('dblclick', () => {
      splitRatio = 0.5; applySplitRatio(); positionDivider();
      try { localStorage.setItem(SPLIT_KEY, '0.5000'); } catch (e) {}
    });
  }
  let _divRaf = null;
  window.addEventListener('resize', () => {
    if (_divRaf) cancelAnimationFrame(_divRaf);
    _divRaf = requestAnimationFrame(positionDivider);
  });
  applySplitRatio();

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
    if (browse) browse.hidden = true;   // ağaç + grid'i birlikte gizle
    split.hidden = false;
    applySplitRatio();
    requestAnimationFrame(positionDivider);   // layout oturunca bölücüyü konumla
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
    if (browse) browse.hidden = false;   // ağaç + grid'i tekrar göster
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
      // Ön çalışmadan taşınan sınıflandırma — dar rail için kompakt metin satırı (F5)
      const taxo = [item.category, item.pattern, item.color_family]
        .filter(Boolean).map(s => String(s).replace(/-/g, ' ')).join(' · ');
      const taxoHtml = taxo ? `<div class="cw-rail-taxo">${escapeHtml(taxo)}</div>` : '';
      li.innerHTML = `
        ${img}
        <div class="cw-rail-text">
          <div class="cw-rail-brand">${escapeHtml(item.brand || '')}</div>
          <div class="cw-rail-name">${escapeHtml(item.product_name || item.urun_id)}</div>
          ${taxoHtml}
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
  let activeAlbumId = '';            // '' = Tümü
  const collapsed = new Set();       // daraltılmış düğüm id'leri (varsayılan: hepsi açık)
  const treeEl = $('#cw-tree');

  function escAttr(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  // ---- Ağaç yardımcıları (parent_id ile sınırsız derinlik) ----
  function childrenOf(pid) {
    return albums
      .filter(a => (a.parent_id || null) === (pid || null))
      .sort((x, y) => String(x.name || '').localeCompare(String(y.name || ''), 'tr'));
  }
  function descendantsOf(id) {
    const out = new Set();
    (function walk(pid) { childrenOf(pid).forEach(c => { out.add(c.id); walk(c.id); }); })(id);
    return out;
  }

  function applyAlbumFilter() {
    const showAll = !activeAlbumId;
    let allowed = null;
    if (!showAll) { allowed = descendantsOf(activeAlbumId); allowed.add(activeAlbumId); }
    $$('.cw-card').forEach(card => {
      const alb = card.dataset.albumId || '';
      const show = showAll || (alb && allowed.has(alb));
      card.style.display = show ? '' : 'none';
    });
  }

  function nodeHtml(a) {
    const kids = childrenOf(a.id);
    const hasKids = kids.length > 0;
    const open = !collapsed.has(a.id);
    const isActive = a.id === activeAlbumId;
    const dot = a.color ? `<span class="cw-tree-dot" style="background:${escAttr(a.color)}"></span>` : '';
    const toggle = hasKids
      ? `<button type="button" class="cw-tree-toggle${open ? ' is-open' : ''}" data-toggle="${escAttr(a.id)}" aria-label="Aç/Kapat"><svg class="icon"><use href="#ic-chevron-down"/></svg></button>`
      : `<span class="cw-tree-toggle-sp" aria-hidden="true"></span>`;
    let html =
      `<li class="cw-tree-node" role="treeitem" style="--depth:${a.depth || 0}">` +
      `<div class="cw-tree-row${isActive ? ' is-active' : ''}">` +
        toggle +
        `<button type="button" class="cw-tree-label" data-album-id="${escAttr(a.id)}" title="${escAttr(a.name)}">${dot}<span class="cw-tree-name">${escAttr(a.name)}</span><span class="cw-tree-cnt">${a.count || 0}</span></button>` +
        `<button type="button" class="cw-tree-menu" data-menu="${escAttr(a.id)}" title="Klasör ayarları" aria-label="Klasör ayarları">⋯</button>` +
      `</div>`;
    if (hasKids && open) html += `<ul class="cw-tree-children" role="group">${kids.map(nodeHtml).join('')}</ul>`;
    return html + `</li>`;
  }

  function renderTree() {
    if (!treeEl) return;
    const allActive = activeAlbumId === '';
    const roots = childrenOf(null);
    treeEl.innerHTML =
      `<button type="button" class="cw-tree-all cw-tree-row${allActive ? ' is-active' : ''}" data-album-id=""><svg class="icon"><use href="#ic-grid"/></svg><span class="cw-tree-name">Tümü</span><span class="cw-tree-cnt">${items.length}</span></button>` +
      `<ul class="cw-tree-root" role="group">${roots.map(nodeHtml).join('')}</ul>` +
      `<button type="button" class="cw-tree-newroot" data-newroot="1"><svg class="icon"><use href="#ic-plus"/></svg> Yeni klasör</button>`;
    applyAlbumFilter();
  }

  function setActiveNode(id) {
    activeAlbumId = id || '';
    renderTree();
  }

  // Ağaç tıklamaları (delegation)
  treeEl?.addEventListener('click', async (e) => {
    const tog = e.target.closest('.cw-tree-toggle');
    if (tog) {
      e.stopPropagation();
      const id = tog.dataset.toggle;
      if (collapsed.has(id)) collapsed.delete(id); else collapsed.add(id);
      renderTree();
      return;
    }
    const menu = e.target.closest('.cw-tree-menu');
    if (menu) { e.stopPropagation(); await openNodeMenu(menu.dataset.menu); return; }
    if (e.target.closest('.cw-tree-newroot')) {
      const name = prompt('Yeni klasör adı:');
      if (name && name.trim()) await createAlbum(name.trim(), null);
      return;
    }
    if (e.target.closest('.cw-tree-all')) { setActiveNode(''); return; }
    const lbl = e.target.closest('.cw-tree-label');
    if (lbl) { setActiveNode(lbl.dataset.albumId); return; }
  });

  async function openNodeMenu(id) {
    const a = albums.find(x => x.id === id);
    const action = prompt(
      `"${a?.name || ''}" klasörü:\n` +
      `  1 — Yeniden adlandır\n` +
      `  2 — Sil (alt klasör/ürünler bir üste taşınır)\n` +
      `  3 — Alt klasör ekle\n` +
      `(1/2/3 yaz, vazgeç: boş)`
    );
    if (action === '1') {
      const nn = prompt('Yeni isim:', a?.name || '');
      if (nn && nn.trim()) await renameAlbum(id, nn.trim());
    } else if (action === '2') {
      if (confirm(`"${a?.name || ''}" klasörü silinsin mi?\n(Alt klasörler ve ürünler bir üst düzeye taşınır — veri kaybı yok.)`)) await deleteAlbum(id);
    } else if (action === '3') {
      const nn = prompt('Alt klasör adı:');
      if (nn && nn.trim()) { collapsed.delete(id); await createAlbum(nn.trim(), id); }
    }
  }

  async function createAlbum(name, parentId) {
    try {
      const res = await fetch('/api/calisma/album/ekle', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, parent_id: parentId || null }),
      });
      const d = await res.json();
      if (!d.ok) { toast(d.error || 'Hata', 'error'); return; }
      albums = d.albums || [];
      renderTree();
      toast(`"${name}" oluşturuldu`, 'success');
    } catch (err) { toast('Bağlantı hatası', 'error'); }
  }

  async function deleteAlbum(albId) {
    const parent = (albums.find(a => a.id === albId) || {}).parent_id || '';
    try {
      const res = await fetch(`/api/calisma/album/${albId}/sil`, { method: 'POST' });
      const d = await res.json();
      if (!d.ok) { toast(d.error || 'Hata', 'error'); return; }
      albums = d.albums || [];
      // Silinen düğümdeki kartlar/ürünler ebeveyne taşındı (promote)
      $$('.cw-card').forEach(card => { if ((card.dataset.albumId || '') === albId) card.dataset.albumId = parent; });
      items.forEach(it => { if (it.album_id === albId) it.album_id = parent || null; });
      if (activeAlbumId === albId) activeAlbumId = parent || '';
      collapsed.delete(albId);
      renderTree();
      toast('Klasör silindi', 'success');
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
      renderTree();
      toast('Yeniden adlandırıldı', 'success');
    } catch (err) { toast('Bağlantı hatası', 'error'); }
  }

  // Kart "⋯" → klasöre taşı (girintili ağaç listesi)
  function moveOptions() {
    const lines = ['0 — (yok / Tümü)'];
    const idMap = [null];
    (function walk(pid, depth) {
      childrenOf(pid).forEach(a => {
        lines.push(`${idMap.length} — ${'　'.repeat(depth)}${a.name}`);
        idMap.push(a.id);
        walk(a.id, depth + 1);
      });
    })(null, 0);
    return { lines, idMap };
  }

  async function moveCardToAlbum(uid, albumId) {
    try {
      const res = await fetch('/api/calisma/urun-albume-tasi', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urun_id: uid, album_id: albumId }),
      });
      const d = await res.json();
      if (!d.ok) { toast(d.error || 'Hata', 'error'); return; }
      albums = d.albums || [];
      const card = $(`.cw-card[data-urunid="${uid}"]`);
      if (card) card.dataset.albumId = albumId || '';
      const it = items.find(i => i.urun_id === uid);
      if (it) it.album_id = albumId || null;
      renderTree();
      toast(albumId ? 'Klasöre taşındı' : 'Tümü\'ye alındı', 'success');
    } catch (err) { toast('Bağlantı hatası', 'error'); }
  }

  $$('.cw-card-album-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault(); e.stopPropagation();
      const uid = btn.dataset.urunid;
      if (!albums.length) { toast('Önce "+ Yeni klasör" ile bir klasör oluştur', 'warn'); return; }
      const { lines, idMap } = moveOptions();
      const choice = prompt(`Bu kumaşı hangi klasöre taşı?\n` + lines.join('\n'));
      if (choice === null || choice.trim() === '') return;
      const idx = parseInt(choice, 10);
      if (isNaN(idx) || idx < 0 || idx >= idMap.length) { toast('Geçersiz seçim', 'warn'); return; }
      moveCardToAlbum(uid, idMap[idx]);
    });
  });

  // İlk ağaç render
  renderTree();

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

  // tasarim-v2 — Teknik iframe'inden gelen "tam ekran" sinyali (iframe sınırı aştırma)
  // Iframe sağ pane'in body'sine teknik-fullscreen class'ı eklemek yetmiyor (parent grid sabit
  // kalıyor); parent'a postMessage ile sinyal gönderiyor, biz burada body class'ı çevirip
  // CSS'in sol pane + rail'i gizleyip sağ pane'i tam genişliğe yaymasını sağlıyoruz.
  window.addEventListener('message', (e) => {
    if (!e.data || e.data.type !== 'teknik-fullscreen') return;
    // Origin doğrulama — yalnız aynı kaynaktan kabul (basit güvenlik)
    if (e.origin && e.origin !== window.location.origin) return;
    document.body.classList.toggle('cw-fullscreen', !!e.data.on);
    requestAnimationFrame(positionDivider);   // tam ekran aç/kapa → bölücüyü gizle/göster
  });
})();
