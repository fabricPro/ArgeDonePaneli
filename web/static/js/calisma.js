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
  // Tasarım modu (drag-drop sıralama) — Galeri muadili, pointer-events (mouse + dokunmatik)
  const designToggle = $('#cw-design-toggle');
  const designSave = $('#cw-design-save');
  const designCancel = $('#cw-design-cancel');
  const designHint = $('#cw-design-hint');
  let designMode = false;
  let dragEl = null;
  let preDesignOrder = [];

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

  // Kart click → split (tasarım/seç modunda bastırılır; çip × → klasörden çıkar)
  $$('.cw-card-main').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const x = e.target.closest('.cwf-x');   // çoklu klasör rozetindeki × → o klasörden çıkar
      if (x) {
        e.preventDefault(); e.stopPropagation();
        const chip = x.closest('.cw-folder-chip');
        if (chip) removeCardFromAlbum(btn.dataset.urunid, chip.dataset.albumId);
        return;
      }
      if (selectMode) {           // çoka-çok toplu seç
        e.preventDefault(); e.stopPropagation();
        toggleSelect(btn.closest('.cw-card'));
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      if (designMode) return;   // sıralama modunda tıklama split açmaz
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
  let activeAlbumId = '';            // '' = Tümü (kök kapsam)
  let scopeOrders = window.CW_SCOPE_ORDERS || {};   // kapsam(klasör id)→sıra; kök = items/fabric_ids
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

  // Faz 3.1 — kart klasör etiketi (canlı). albumPath = ad zinciri.
  function albumPath(id) {
    const byId = {}; albums.forEach(a => { byId[a.id] = a; });
    const names = []; let cur = byId[id]; const guard = new Set();
    while (cur && !guard.has(cur.id)) { guard.add(cur.id); names.push(cur.name || ''); cur = byId[cur.parent_id]; }
    return names.reverse().filter(Boolean).join(' / ');
  }
  // Çoka-çok — kart üzerindeki albüm id listesi (data-album-ids="a,b,c")
  function cardAlbumIds(card) { return (card.dataset.albumIds || '').split(',').filter(Boolean); }
  function setCardAlbumIds(card, ids) { card.dataset.albumIds = (ids || []).filter(Boolean).join(','); }
  function albumById(id) { return albums.find(a => a.id === id); }
  // Çoklu klasör rozetlerini (× ile çıkarılabilir) bir kart için yeniden çiz
  function renderCardFolders(uid, albumIds) {
    const card = $(`.cw-card[data-urunid="${uid}"]`);
    const box = card ? card.querySelector('.cw-card-folders') : null;
    if (!box) return;
    box.innerHTML = (albumIds || []).filter(Boolean).map(id => {
      const a = albumById(id);
      if (!a) return '';
      const col = a.color ? ` style="color:${escAttr(a.color)}"` : '';
      return `<span class="cw-folder-chip" data-album-id="${escAttr(id)}" title="Klasör: ${escAttr(albumPath(id))}">` +
        `<svg class="icon"${col}><use href="#ic-folder"/></svg>` +
        `<span class="cwf-name">${escAttr(a.name || '')}</span>` +
        `<span class="cwf-x" role="button" tabindex="0" title="Bu klasörden çıkar" aria-label="Klasörden çıkar"><svg class="icon"><use href="#ic-x"/></svg></span>` +
        `</span>`;
    }).join('');
  }
  function refreshAllCardFolders() {
    $$('.cw-card').forEach(card => renderCardFolders(card.dataset.urunid, cardAlbumIds(card)));
  }

  // ---- Kapsam başına sıra (per-scope order) ----
  function rootOrder() { return items.map(i => i.urun_id); }
  function scopeMemberSet(scope) {
    // scope='' → kök (tüm pinler). Aksi: ÜYELİKLERDEN biri ∈ {scope} ∪ descendants(scope) (çoka-çok)
    const allowed = descendantsOf(scope); allowed.add(scope);
    const set = new Set();
    items.forEach(i => { if ((i.album_ids || []).some(a => allowed.has(a))) set.add(i.urun_id); });
    return set;
  }
  function computeScopeOrder(scope) {
    const root = rootOrder();
    if (!scope) return root.slice();                       // kök = items/fabric_ids sırası
    const members = scopeMemberSet(scope);
    const saved = (scopeOrders[scope] || []).filter(id => members.has(id));
    const savedSet = new Set(saved);
    const rest = root.filter(id => members.has(id) && !savedSet.has(id));  // kaydedilmemiş üyeler → kök sırasında sona
    return saved.concat(rest);
  }
  function applyScopeOrder(scope) {
    // grid DOM'unu kapsam sırasına diz: önce üye kartlar (kapsam sırasında), sonra üye-olmayanlar (gizlenecek)
    const order = computeScopeOrder(scope);
    const byId = {}; $$('.cw-card').forEach(c => { byId[c.dataset.urunid] = c; });
    const placed = new Set();
    order.forEach(uid => { const c = byId[uid]; if (c) { grid.appendChild(c); placed.add(uid); } });
    rootOrder().forEach(uid => { if (!placed.has(uid)) { const c = byId[uid]; if (c) grid.appendChild(c); } });
  }

  function applyAlbumFilter() {
    if (!designMode) applyScopeOrder(activeAlbumId);   // kapsam sırasına diz (tasarım modunda sürükleme korunur)
    const showAll = !activeAlbumId;
    let allowed = null;
    if (!showAll) { allowed = descendantsOf(activeAlbumId); allowed.add(activeAlbumId); }
    $$('.cw-card').forEach(card => {
      const albs = cardAlbumIds(card);   // çoka-çok: kart birden çok klasörde olabilir
      const show = showAll || albs.some(a => allowed.has(a));
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
      // Çoka-çok: silinen klasör yalnız ÜYELİKTEN düşer (promote yok); diğer üyelikler korunur
      $$('.cw-card').forEach(card => setCardAlbumIds(card, cardAlbumIds(card).filter(a => a !== albId)));
      items.forEach(it => { if (Array.isArray(it.album_ids)) it.album_ids = it.album_ids.filter(a => a !== albId); });
      if (activeAlbumId === albId) activeAlbumId = parent || '';
      collapsed.delete(albId);
      renderTree();
      refreshAllCardFolders();
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
      refreshAllCardFolders();
      toast('Yeniden adlandırıldı', 'success');
    } catch (err) { toast('Bağlantı hatası', 'error'); }
  }

  // Kart "+" / toplu → klasöre EKLE (girintili ağaç listesi; çoka-çok, "yok" seçeneği YOK)
  function folderOptions() {
    const lines = [];
    const idMap = [];
    (function walk(pid, depth) {
      childrenOf(pid).forEach(a => {
        lines.push(`${idMap.length} — ${'　'.repeat(depth)}${a.name}`);
        idMap.push(a.id);
        walk(a.id, depth + 1);
      });
    })(null, 0);
    return { lines, idMap };
  }
  function pickFolder(promptText) {
    if (!albums.length) { toast('Önce "+ Yeni klasör" ile bir klasör oluştur', 'warn'); return null; }
    const { lines, idMap } = folderOptions();
    const choice = prompt(promptText + '\n' + lines.join('\n'));
    if (choice === null || choice.trim() === '') return null;
    const idx = parseInt(choice, 10);
    if (isNaN(idx) || idx < 0 || idx >= idMap.length) { toast('Geçersiz seçim', 'warn'); return null; }
    return idMap[idx];
  }

  async function addCardToAlbum(uid, albumId) {
    if (!albumId) return;
    try {
      const res = await fetch('/api/calisma/urun-albume-ekle', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urun_id: uid, album_id: albumId }),
      });
      const d = await res.json();
      if (!d.ok) { toast(d.error || 'Hata', 'error'); return; }
      albums = d.albums || albums;
      const card = $(`.cw-card[data-urunid="${uid}"]`);
      if (card) setCardAlbumIds(card, d.album_ids || []);
      const it = items.find(i => i.urun_id === uid);
      if (it) it.album_ids = d.album_ids || [];
      renderTree();
      renderCardFolders(uid, d.album_ids || []);
      toast('Klasöre eklendi', 'success');
    } catch (err) { toast('Bağlantı hatası', 'error'); }
  }

  async function removeCardFromAlbum(uid, albumId) {
    if (!albumId) return;
    try {
      const res = await fetch('/api/calisma/urun-albume-cikar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urun_id: uid, album_id: albumId }),
      });
      const d = await res.json();
      if (!d.ok) { toast(d.error || 'Hata', 'error'); return; }
      albums = d.albums || albums;
      const card = $(`.cw-card[data-urunid="${uid}"]`);
      if (card) setCardAlbumIds(card, d.album_ids || []);
      const it = items.find(i => i.urun_id === uid);
      if (it) it.album_ids = d.album_ids || [];
      renderTree();
      renderCardFolders(uid, d.album_ids || []);
      if (activeAlbumId) applyAlbumFilter();   // aktif klasör görünümünden düşmüşse gizle
      toast('Klasörden çıkarıldı', 'success');
    } catch (err) { toast('Bağlantı hatası', 'error'); }
  }

  $$('.cw-card-album-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault(); e.stopPropagation();
      if (selectMode) return;
      const uid = btn.dataset.urunid;
      const albumId = pickFolder('Bu kumaşı hangi klasöre ekle?');
      if (albumId) addCardToAlbum(uid, albumId);
    });
  });

  // ===== Çoka-çok — toplu seç → Klasöre Ekle (galeri/ön-çalışma deseni) =====
  let selectMode = false;
  const selectedIds = new Set();
  const selToggle = $('#cw-select-toggle');
  const selBar = $('#cw-select-bar');
  const selNEl = $('#cw-sel-n');
  const selFolderBtn = $('#cw-sel-folder');
  const selCancelBtn = $('#cw-sel-cancel');
  function updateSelCount() { if (selNEl) selNEl.textContent = selectedIds.size; }
  function setSelectMode(on) {
    selectMode = on;
    page.classList.toggle('cw-select-on', on);
    if (selToggle) selToggle.classList.toggle('is-active', on);
    if (selBar) selBar.hidden = !on;
    if (!on) {
      selectedIds.clear();
      $$('.cw-card.is-selected').forEach(c => c.classList.remove('is-selected'));
    }
    updateSelCount();
  }
  function toggleSelect(card) {
    if (!card) return;
    const uid = card.dataset.urunid;
    if (selectedIds.has(uid)) { selectedIds.delete(uid); card.classList.remove('is-selected'); }
    else { selectedIds.add(uid); card.classList.add('is-selected'); }
    updateSelCount();
  }
  selToggle?.addEventListener('click', () => setSelectMode(!selectMode));
  selCancelBtn?.addEventListener('click', () => setSelectMode(false));
  selFolderBtn?.addEventListener('click', async () => {
    if (!selectedIds.size) { toast('Önce kumaş seç', 'warn'); return; }
    const albumId = pickFolder(`${selectedIds.size} kumaşı hangi klasöre ekle?`);
    if (!albumId) return;
    try {
      const res = await fetch('/api/calisma/toplu-albume-ekle', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urun_ids: [...selectedIds], album_id: albumId }),
      });
      const d = await res.json();
      if (d.ok) { toast(`${d.added} kumaş klasöre eklendi`, 'success'); location.reload(); }
      else toast(d.error || 'Hata', 'error');
    } catch (err) { toast('Bağlantı hatası', 'error'); }
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

  // ===== Tasarım modu: sürükle-bırak sıralama (Galeri muadili; pointer-events → dokunmatik) =====
  function cardOrderFromDom() {
    return $$('.cw-card').map(c => c.dataset.urunid);
  }
  function reorderDomTo(order) {
    const byId = {};
    $$('.cw-card').forEach(c => { byId[c.dataset.urunid] = c; });
    order.forEach(uid => { const c = byId[uid]; if (c) grid.appendChild(c); });
  }
  function setDesignMode(on) {
    designMode = on;
    page.classList.toggle('cw-design-on', on);
    if (designToggle) designToggle.hidden = on;
    if (designSave) designSave.hidden = !on;
    if (designCancel) designCancel.hidden = !on;
    if (designHint) designHint.hidden = !on;
    if (on) preDesignOrder = cardOrderFromDom();
  }
  // Pointer sürükleme (delegation) — mouse + dokunmatik. dragEl yerinde reflow olur (Galeri deseni).
  function endDrag() {
    if (dragEl) dragEl.classList.remove('dragging');
    dragEl = null;
  }
  grid?.addEventListener('pointerdown', (e) => {
    if (!designMode) return;
    if (e.target.closest('.cw-unpin, .cw-card-album-btn')) return;  // bu butonlar drag başlatmaz
    const card = e.target.closest('.cw-card');
    if (!card) return;
    e.preventDefault();
    dragEl = card;
    card.classList.add('dragging');
    try { card.setPointerCapture(e.pointerId); } catch (_) { /* yok say */ }
  });
  grid?.addEventListener('pointermove', (e) => {
    if (!designMode || !dragEl) return;
    e.preventDefault();
    const under = document.elementFromPoint(e.clientX, e.clientY);
    const t = under && under.closest ? under.closest('.cw-card') : null;
    if (!t || t === dragEl || t.style.display === 'none') return;
    const rect = t.getBoundingClientRect();
    const after = (e.clientX - rect.left) > rect.width / 2;
    grid.insertBefore(dragEl, after ? t.nextSibling : t);
  });
  grid?.addEventListener('pointerup', endDrag);
  grid?.addEventListener('pointercancel', endDrag);

  designToggle?.addEventListener('click', () => setDesignMode(true));
  designCancel?.addEventListener('click', () => {
    reorderDomTo(preDesignOrder);   // değişiklikleri geri al (sunucuya yazma yok)
    setDesignMode(false);
    applyAlbumFilter();
  });
  designSave?.addEventListener('click', async () => {
    // Yalnız GÖRÜNÜR (aktif kapsam üyesi) kartların sırası — yalnız bu kapsam kaydedilir
    const order = $$('.cw-card').filter(c => c.style.display !== 'none').map(c => c.dataset.urunid);
    const scope = activeAlbumId || '';
    try {
      const res = await fetch('/api/calisma/sirala', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scope, urun_ids: order }),
      });
      const d = await res.json();
      if (!d.ok) { toast(d.error || 'Sıra kaydedilemedi', 'error'); return; }
      if (scope) {
        scopeOrders[scope] = order.slice();   // klasör kapsamı — yalnız bunu güncelle
      } else {
        // kök: items'ı yeni sıraya diz (rail + kapsam türetmeleri için)
        const byId = {}; items.forEach(i => { byId[i.urun_id] = i; });
        items = order.map(uid => byId[uid]).filter(Boolean);
      }
      setDesignMode(false);
      applyAlbumFilter();
      toast('Sıra kaydedildi', 'success');
    } catch (err) { toast('Bağlantı hatası', 'error'); }
  });

  // İlk yüklemede URL hash varsa o ürünü aç (örn. #urun-kvadrat_qs3847)
  const hash = location.hash.slice(1);
  if (hash && hash.startsWith('urun-')) {
    const target = hash.slice(5);
    if (items.some(i => i.urun_id === target)) {
      // Hemen seç
      setTimeout(() => selectFabric(target), 50);
    }
  }

  // Sol foto pane'ini GEÇİCİ tam-pane büyüt (oran/teknik pane kalıcı daralmaz). cw-fullscreen simetriği.
  const leftExpandBtn = document.getElementById('cw-left-expand');
  function setLeftFull(on) {
    document.body.classList.toggle('cw-left-full', !!on);
    if (leftExpandBtn) {
      leftExpandBtn.title = on ? 'Küçült' : 'Fotoğrafı büyüt';
      leftExpandBtn.setAttribute('aria-label', leftExpandBtn.title);
      const use = leftExpandBtn.querySelector('use');
      if (use) use.setAttribute('href', on ? '#ic-minimize' : '#ic-maximize');
    }
    requestAnimationFrame(positionDivider);
  }
  if (leftExpandBtn) leftExpandBtn.addEventListener('click', () =>
    setLeftFull(!document.body.classList.contains('cw-left-full')));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && document.body.classList.contains('cw-left-full')) setLeftFull(false);
  });

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
