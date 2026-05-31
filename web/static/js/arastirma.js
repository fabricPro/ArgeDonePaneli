// Ön Çalışma Alanı — link havuzu UI
// v4.0-part-2 Adım 8 + Sprint 5 (favicon fallback)

(function () {
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const toast = (msg, type) => (window.toast || alert)(msg, type);

  // v4.0-part-2 Sprint 5 — Client-side favicon URL hesaplayıcı.
  // Google s2 servisi her HTTPS domain için favicon döner; bot bloke / Cloudflare
  // gibi sorunlarla karşılaşmaz, fetch yapmamızı gerektirmez.
  function googleFaviconUrl(productUrl, size = 64) {
    try {
      const u = new URL(productUrl);
      const domain = u.host.replace(/^www\./i, '');
      if (!domain) return null;
      return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=${size}`;
    } catch (e) {
      return null;
    }
  }

  // ---- State ----
  const elMaster = $('#master-url');
  const elRowsContainer = $('#ar-rows');
  const elListContainer = $('#ar-list');
  const elEmpty = $('#ar-empty');
  const tplRow = $('#tpl-ar-row');
  const tplItem = $('#tpl-ar-list-item');

  // Initial data from server
  let initialRows = [];
  try {
    initialRows = JSON.parse($('#initial-rows').textContent || '[]') || [];
  } catch (e) { initialRows = []; }

  // ---- Add panel: dynamic rows ----
  function addEmptyRow() {
    const node = tplRow.content.cloneNode(true);
    const row = node.querySelector('.ar-row');
    const brandSel = row.querySelector('.ar-row-brand');
    const brandNew = row.querySelector('.ar-row-brand-new');
    const country = row.querySelector('.ar-row-country');
    const delBtn = row.querySelector('.ar-row-del');

    brandSel.addEventListener('change', () => {
      const v = brandSel.value;
      if (v === '__new__') {
        brandNew.hidden = false;
        country.value = '';
        country.focus();
      } else if (v) {
        brandNew.hidden = true;
        brandNew.value = '';
        const opt = brandSel.options[brandSel.selectedIndex];
        const c = opt?.dataset.country || '';
        if (c && !country.value) country.value = c;
      } else {
        brandNew.hidden = true;
        brandNew.value = '';
      }
    });

    delBtn.addEventListener('click', () => row.remove());
    elRowsContainer.appendChild(node);
  }

  $('#btn-add-row').addEventListener('click', addEmptyRow);
  addEmptyRow(); // başlangıçta 1 boş satır

  // ---- Save all ----
  async function saveAll() {
    const masterUrl = elMaster.value.trim();
    if (!masterUrl || !/^https?:\/\//i.test(masterUrl)) {
      toast('Master URL zorunlu (http/https ile başlamalı)', 'error');
      elMaster.focus();
      return;
    }

    const rows = $$('.ar-row', elRowsContainer).filter(r => r.dataset.state !== 'saved');
    if (!rows.length) { toast('Eklenecek satır yok', 'info'); return; }

    let okCount = 0;
    let errCount = 0;

    for (const row of rows) {
      const url = $('.ar-row-url', row).value.trim();
      const brandSel = $('.ar-row-brand', row);
      const brandSlug = brandSel.value;
      const brandNew = $('.ar-row-brand-new', row).value.trim();
      const country = $('.ar-row-country', row).value.trim();
      const notes = $('.ar-row-notes', row).value.trim();
      const statusCell = $('.ar-row-status', row);

      if (!url) {
        statusCell.textContent = '— boş, atlandı';
        statusCell.className = 'ar-row-status warn';
        continue;
      }

      const payload = { master_url: masterUrl, product_url: url };
      if (notes) payload.notes = notes;
      if (brandSlug && brandSlug !== '__new__') {
        payload.brand_slug = brandSlug;
        if (country) payload.country = country; // override
      } else if (brandSlug === '__new__') {
        if (!brandNew) {
          statusCell.textContent = 'Yeni firma adı boş';
          statusCell.className = 'ar-row-status err';
          errCount++; continue;
        }
        if (!country) {
          statusCell.textContent = 'Ülke boş';
          statusCell.className = 'ar-row-status err';
          errCount++; continue;
        }
        payload.brand = brandNew;
        payload.country = country;
      } else {
        statusCell.textContent = 'Firma seçilmedi';
        statusCell.className = 'ar-row-status err';
        errCount++; continue;
      }

      statusCell.textContent = '⏳ kaydediliyor…';
      statusCell.className = 'ar-row-status';
      try {
        const res = await fetch('/api/arastirma/ekle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (data.ok) {
          row.dataset.state = 'saved';
          statusCell.textContent = '✓ kaydedildi';
          statusCell.className = 'ar-row-status ok';
          okCount++;
          // Satırı listede de göster
          renderListFromAPI();
        } else {
          statusCell.textContent = data.message || data.error || 'hata';
          statusCell.className = 'ar-row-status err';
          errCount++;
        }
      } catch (e) {
        statusCell.textContent = 'ağ hatası';
        statusCell.className = 'ar-row-status err';
        errCount++;
      }
    }

    if (okCount) toast(`${okCount} satır kaydedildi`, 'success');
    if (errCount) toast(`${errCount} satır eklenemedi`, 'error');

    // Başarılı satırları kaldır, master URL'i koru, yeni boş satır aç
    $$('.ar-row[data-state="saved"]', elRowsContainer).forEach(r => r.remove());
    if (!$$('.ar-row', elRowsContainer).length) addEmptyRow();
  }

  $('#btn-save-all').addEventListener('click', saveAll);

  // ---- Edit mode helpers (v4.0-part-2 Sprint 6) ----
  function openEditMode(article, r) {
    const form = article.querySelector('.ar-item-edit');
    form.querySelector('[data-field="product_url"]').value = r.product_url || '';
    form.querySelector('[data-field="master_url"]').value = r.master_url || '';
    form.querySelector('[data-field="notes"]').value = r.notes || '';
    form.querySelector('[data-field="country"]').value = r.country || '';
    const brandSel = form.querySelector('[data-field="brand_slug"]');
    const newBrandWrap = form.querySelector('.ar-edit-newbrand');
    const newBrandInput = newBrandWrap.querySelector('input');
    const opt = [...brandSel.options].find(o => o.value === r.brand_slug);
    if (opt) {
      brandSel.value = r.brand_slug;
      newBrandWrap.hidden = true;
      newBrandInput.value = '';
    } else {
      brandSel.value = '__new__';
      newBrandWrap.hidden = false;
      newBrandInput.value = r.brand || '';
    }
    form.hidden = false;
    article.classList.add('is-editing');
  }
  function closeEditMode(article) {
    const form = article.querySelector('.ar-item-edit');
    form.hidden = true;
    article.classList.remove('is-editing');
  }
  async function saveEdit(article, r) {
    const form = article.querySelector('.ar-item-edit');
    const payload = {
      product_url: form.querySelector('[data-field="product_url"]').value.trim(),
      master_url: form.querySelector('[data-field="master_url"]').value.trim(),
      notes: form.querySelector('[data-field="notes"]').value.trim(),
    };
    const brandSel = form.querySelector('[data-field="brand_slug"]');
    const country = form.querySelector('[data-field="country"]').value.trim();
    if (brandSel.value === '__new__') {
      const newName = form.querySelector('.ar-edit-newbrand input').value.trim();
      if (!newName) { toast('Yeni firma adı boş', 'error'); return null; }
      payload.brand = newName;
      payload.country = country;
    } else if (brandSel.value) {
      payload.brand_slug = brandSel.value;
      payload.country = country;
    } else {
      toast('Firma seçilmedi', 'error');
      return null;
    }
    try {
      const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const d = await res.json();
      if (d.ok) {
        toast('Kaydedildi', 'success');
        return d.row;
      }
      toast(d.message || d.error || 'Kaydedilemedi', 'error');
      return null;
    } catch (e) {
      toast('Bağlantı hatası', 'error');
      return null;
    }
  }

  // ---- Favori filtresi (v4.0-part-2 Sprint 6) ----
  function applyFavoriteFilter() {
    const onlyFav = $('#filter-favorites-only')?.checked;
    $$('.ar-item').forEach(art => {
      if (onlyFav && art.dataset.favorite !== 'true') {
        art.style.display = 'none';
      } else {
        art.style.display = '';
      }
    });
    // Boş grupları gizle
    $$('.ar-group').forEach(g => {
      const visible = $$('.ar-item', g).some(a => a.style.display !== 'none');
      g.style.display = visible ? '' : 'none';
    });
  }

  // ---- List rendering ----
  function brandCountryGroupKey(row) {
    return `${row.country || 'Belirtilmemiş'} / ${row.brand || row.brand_slug || '—'}`;
  }

  function renderList(rows) {
    elListContainer.innerHTML = '';
    elEmpty.hidden = rows.length > 0;
    if (!rows.length) return;

    // Group by country → brand
    const groups = {};
    rows.forEach(r => {
      const key = brandCountryGroupKey(r);
      (groups[key] ||= []).push(r);
    });

    // Sort: country asc, brand asc
    const sortedKeys = Object.keys(groups).sort((a, b) => a.localeCompare(b, 'tr'));

    sortedKeys.forEach(key => {
      const groupEl = document.createElement('div');
      groupEl.className = 'ar-group';
      const head = document.createElement('div');
      head.className = 'ar-group-head';
      head.innerHTML = `<span class="ar-group-title">${key}</span><span class="ar-group-count">${groups[key].length}</span>`;
      groupEl.appendChild(head);

      groups[key].forEach(r => {
        groupEl.appendChild(renderItem(r));
      });

      // v4.0-part-2 Sprint 7 — Grup-içi "+ Yeni satır" formu
      // Master URL + brand + country grup'taki ilk satırdan miras alınır
      const inheritFrom = groups[key][0];
      groupEl.appendChild(renderGroupAddRow(inheritFrom));

      elListContainer.appendChild(groupEl);
    });
    // Render sonrası favori filtresini uygula (eğer aktifse)
    applyFavoriteFilter();
  }

  // v4.0-part-2 Sprint 7 — Grup altı hızlı satır ekleme formu
  function renderGroupAddRow(inheritFrom) {
    const wrap = document.createElement('div');
    wrap.className = 'ar-group-add';
    wrap.innerHTML = `
      <button type="button" class="ar-group-add-trigger">
        <svg class="icon"><use href="#ic-plus"/></svg>
        <span>Yeni satır</span>
        <small class="ar-group-add-hint">(${inheritFrom.brand} / ${inheritFrom.country} master URL'ine eklenir)</small>
      </button>
      <div class="ar-group-add-form" hidden>
        <input type="url" class="ar-ga-url" placeholder="Ürün linki (https://…)" required>
        <input type="text" class="ar-ga-notes" placeholder="Not (opsiyonel)">
        <button type="button" class="btn btn-secondary ar-ga-cancel">İptal</button>
        <button type="button" class="btn btn-primary ar-ga-save">Ekle</button>
      </div>
    `;
    const trigger = wrap.querySelector('.ar-group-add-trigger');
    const form = wrap.querySelector('.ar-group-add-form');
    const urlInp = wrap.querySelector('.ar-ga-url');
    const notesInp = wrap.querySelector('.ar-ga-notes');
    const cancelBtn = wrap.querySelector('.ar-ga-cancel');
    const saveBtn = wrap.querySelector('.ar-ga-save');

    trigger.addEventListener('click', () => {
      trigger.hidden = true;
      form.hidden = false;
      urlInp.focus();
    });
    cancelBtn.addEventListener('click', () => {
      form.hidden = true;
      trigger.hidden = false;
      urlInp.value = '';
      notesInp.value = '';
    });
    saveBtn.addEventListener('click', async () => {
      const url = urlInp.value.trim();
      if (!url) { toast('Ürün URL boş olamaz', 'error'); return; }
      const payload = {
        master_url: inheritFrom.master_url,
        product_url: url,
        brand_slug: inheritFrom.brand_slug,
        brand: inheritFrom.brand,
        country: inheritFrom.country,
        notes: notesInp.value.trim() || undefined,
      };
      saveBtn.disabled = true;
      saveBtn.textContent = 'Kaydediliyor…';
      try {
        const res = await fetch('/api/arastirma/ekle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const d = await res.json();
        if (d.ok) {
          toast(`Eklendi: ${inheritFrom.brand}`, 'success');
          form.hidden = true;
          trigger.hidden = false;
          urlInp.value = '';
          notesInp.value = '';
          renderListFromAPI();
        } else {
          toast(d.message || d.error || 'Eklenemedi', 'error');
        }
      } catch (e) {
        toast('Bağlantı hatası', 'error');
      } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Ekle';
      }
    });
    return wrap;
  }

  function renderItem(r) {
    const node = tplItem.content.cloneNode(true);
    const article = node.querySelector('.ar-item');
    article.dataset.status = r.status || 'pending';
    article.dataset.id = r.id;
    article.dataset.favorite = r.is_favorite ? 'true' : 'false';

    // Yıldız (favori) — v4.0-part-2 Sprint 6
    const star = node.querySelector('.ar-fav-star');
    star.setAttribute('aria-pressed', r.is_favorite ? 'true' : 'false');
    star.addEventListener('click', async (e) => {
      e.stopPropagation();
      const next = article.dataset.favorite !== 'true';
      try {
        const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}/favorite`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ value: next }),
        });
        const d = await res.json();
        if (d.ok) {
          article.dataset.favorite = d.is_favorite ? 'true' : 'false';
          star.setAttribute('aria-pressed', d.is_favorite ? 'true' : 'false');
          r.is_favorite = d.is_favorite;
          // Aktif favori filtresi varsa, yıldız söndürülünce kart gizlenir
          applyFavoriteFilter();
        } else {
          toast(d.error || 'Favori güncellenemedi', 'error');
        }
      } catch (err) {
        toast('Bağlantı hatası', 'error');
      }
    });

    // Düzenleme — v4.0-part-2 Sprint 6
    const editBtn = node.querySelector('.ar-item-edit-btn');
    const editForm = node.querySelector('.ar-item-edit');
    editBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openEditMode(article, r);
    });
    node.querySelector('.ar-edit-cancel').addEventListener('click', () => {
      closeEditMode(article);
    });
    node.querySelector('.ar-edit-save').addEventListener('click', async () => {
      const updated = await saveEdit(article, r);
      if (updated) {
        Object.assign(r, updated);
        closeEditMode(article);
        renderListFromAPI();
      }
    });
    // Edit içindeki firma seçimi → ülke autofill + yeni firma toggle
    const editBrandSel = editForm.querySelector('[data-field="brand_slug"]');
    const editBrandNew = editForm.querySelector('.ar-edit-newbrand');
    const editCountry = editForm.querySelector('[data-field="country"]');
    editBrandSel.addEventListener('change', () => {
      const v = editBrandSel.value;
      if (v === '__new__') {
        editBrandNew.hidden = false;
      } else if (v) {
        editBrandNew.hidden = true;
        const opt = editBrandSel.options[editBrandSel.selectedIndex];
        const c = opt?.dataset.country || '';
        if (c) editCountry.value = c;
      } else {
        editBrandNew.hidden = true;
      }
    });

    const img = node.querySelector('.ar-item-thumb img');
    const placeholder = node.querySelector('.ar-thumb-placeholder');
    // v4.0-part-2 Sprint 5 — Önce manuel thumb_url, yoksa Google s2 favicon
    const fallbackFavicon = googleFaviconUrl(r.product_url, 64);
    const finalSrc = r.thumb_url || fallbackFavicon || '';
    if (finalSrc) {
      img.src = finalSrc;
      img.alt = r.product_url;
      img.referrerPolicy = 'no-referrer';
      placeholder.style.display = 'none';
      img.onerror = () => { img.style.display = 'none'; placeholder.style.display = ''; };
    } else {
      img.style.display = 'none';
    }

    const urlShort = shortUrl(r.product_url);
    node.querySelector('.ar-item-title').textContent = urlShort.path || r.product_url;
    node.querySelector('.ar-item-meta').textContent = `${r.brand} · ${r.country}${r.country_code ? ' (' + r.country_code + ')' : ''}`;
    // v4.0-part-2 Sprint 7 — Master URL tıklanabilir anchor
    const masterCell = node.querySelector('.ar-item-master');
    if (r.master_url) {
      masterCell.href = r.master_url;
      masterCell.textContent = `Master: ${shortUrl(r.master_url).host_path}`;
      masterCell.title = r.master_url;
      // Stop event propagation; ana karta click handler olmasın diye
      masterCell.addEventListener('click', (e) => e.stopPropagation());
    } else {
      masterCell.removeAttribute('href');
      masterCell.textContent = '';
    }
    const notesCell = node.querySelector('.ar-item-notes');
    if (r.notes) notesCell.textContent = `📝 ${r.notes}`;

    const openBtn = node.querySelector('.ar-item-open');
    openBtn.href = r.product_url;

    const importBtn = node.querySelector('.ar-item-import');
    importBtn.href = `/ekle?from_research=${encodeURIComponent(r.id)}`;
    if (r.status === 'imported') {
      importBtn.classList.remove('btn-primary');
      importBtn.classList.add('btn-secondary');
      importBtn.querySelector('span').textContent = `Ürün: ${r.imported_product_id || ''}`;
      importBtn.href = r.imported_product_id ? `/urun/${r.imported_product_id}` : '#';
    }

    const dismissBtn = node.querySelector('.ar-item-dismiss');
    const restoreBtn = node.querySelector('.ar-item-restore');
    if (r.status === 'dismissed') {
      dismissBtn.hidden = true;
      restoreBtn.hidden = false;
    }
    dismissBtn.addEventListener('click', async () => {
      if (!confirm('Bu kaydı reddetmek (gizlemek) istiyor musun?')) return;
      const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}`, { method: 'DELETE' });
      const d = await res.json();
      if (d.ok) { toast('Reddedildi', 'success'); renderListFromAPI(); }
      else toast('Silinemedi', 'error');
    });
    restoreBtn.addEventListener('click', async () => {
      const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}/status`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'pending' }),
      });
      const d = await res.json();
      if (d.ok) { toast('Geri açıldı', 'success'); renderListFromAPI(); }
      else toast('Geri açılamadı', 'error');
    });

    return node;
  }

  function shortUrl(u) {
    try {
      const p = new URL(u);
      return {
        host: p.host.replace(/^www\./i, ''),
        path: decodeURIComponent(p.pathname).split('/').filter(Boolean).pop() || p.host,
        host_path: p.host.replace(/^www\./i, '') + decodeURIComponent(p.pathname),
      };
    } catch (e) {
      return { host: u, path: u, host_path: u };
    }
  }

  // ---- Filtre uygula ----
  async function renderListFromAPI() {
    const status = $('#filter-status').value;
    const brand = $('#filter-brand').value;
    const country = $('#filter-country').value;
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (brand) params.set('brand_slug', brand);
    if (country) params.set('country_code', country);
    try {
      const res = await fetch('/api/arastirma/list?' + params.toString());
      const data = await res.json();
      if (data.ok) {
        renderList(data.rows || []);
        // Ülke filtresi seçeneklerini güncelle
        populateCountryFilter(data.rows || []);
      }
    } catch (e) {
      toast('Liste yüklenemedi', 'error');
    }
  }

  function populateCountryFilter(rows) {
    const sel = $('#filter-country');
    const current = sel.value;
    const seen = new Map();
    rows.forEach(r => {
      if (r.country_code && r.country) seen.set(r.country_code, r.country);
    });
    // Eski seçenekleri temizle (ilk hariç)
    while (sel.options.length > 1) sel.remove(1);
    Array.from(seen.entries()).sort((a, b) => a[1].localeCompare(b[1], 'tr')).forEach(([code, name]) => {
      const opt = document.createElement('option');
      opt.value = code;
      opt.textContent = `${name} (${code})`;
      sel.appendChild(opt);
    });
    if (current && Array.from(sel.options).some(o => o.value === current)) sel.value = current;
  }

  $('#filter-status').addEventListener('change', renderListFromAPI);
  $('#filter-brand').addEventListener('change', renderListFromAPI);
  $('#filter-country').addEventListener('change', renderListFromAPI);
  $('#filter-favorites-only').addEventListener('change', applyFavoriteFilter);
  $('#btn-refresh-list').addEventListener('click', renderListFromAPI);

  // Initial render
  renderList(initialRows);
  populateCountryFilter(initialRows);
})();
