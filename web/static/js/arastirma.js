// Ön Çalışma Alanı — link havuzu UI
// v4.0-part-2 Adım 8 + Sprint 5 (favicon fallback)

(function () {
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const toast = (msg, type) => (window.toast || alert)(msg, type);
  // AI paneli (kabul kartları) da [data-field] kullanıyor → form KONTROLLERİNİ tag ile sınırla.
  // Aksi halde querySelector('[data-field="brand"]') AI kart <div>'ini seçip .value=undefined döndürür.
  const CTRL = (name) => `input[data-field="${name}"], select[data-field="${name}"], textarea[data-field="${name}"]`;

  // Sprint 12.1 — Uzun süren AI isteklerinde butonda geçen süre + iptal göster.
  // runFn(signal) bir Promise döndürür; buton çalışırken tekrar tıklanınca isteği iptal eder (AbortController).
  function runWithProgress(btn, runningLabel, runFn) {
    if (!btn) return;
    if (btn.dataset.acRunning === '1') {           // zaten çalışıyor → iptal
      if (btn._acAbort) btn._acAbort.abort();
      return;
    }
    const baseLabel = btn.textContent;
    const ctrl = new AbortController();
    btn._acAbort = ctrl;
    btn.dataset.acRunning = '1';
    btn.classList.add('is-running');
    const t0 = Date.now();
    const render = () => {
      const s = Math.round((Date.now() - t0) / 1000);
      btn.textContent = `⏳ ${runningLabel} ${s}s · İptal`;
    };
    render();
    const timer = setInterval(render, 1000);
    Promise.resolve()
      .then(() => runFn(ctrl.signal))
      .catch((e) => {
        if (e && e.name === 'AbortError') toast('İptal edildi', 'warn');
        else { console.error(e); toast('Bağlantı hatası', 'error'); }
      })
      .finally(() => {
        clearInterval(timer);
        btn.dataset.acRunning = '0';
        btn._acAbort = null;
        btn.classList.remove('is-running');
        btn.textContent = baseLabel;
      });
  }

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
    const purlEl = form.querySelector(CTRL('product_url')); if (purlEl) purlEl.value = r.product_url || '';
    const murlEl = form.querySelector(CTRL('master_url')); if (murlEl) murlEl.value = r.master_url || '';
    // Master URL collapsed kalır; özet etiketi kayıtlı olup olmadığını gösterir (içerik kaydedilir)
    const masterSum = form.querySelector('.ar-edit-master-sum');
    if (masterSum) masterSum.textContent = r.master_url ? '🔗 Master URL (kayıtlı) — göster/düzenle' : '+ Master URL';
    const notesEl = form.querySelector(CTRL('notes')); if (notesEl) notesEl.value = r.notes || '';
    const countryEl = form.querySelector(CTRL('country')); if (countryEl) countryEl.value = r.country || '';
    // Marka: artık düz input + datalist (ülke gibi) — select/yeni-firma mantığı yok
    const brandEl = form.querySelector(CTRL('brand'));
    if (brandEl) brandEl.value = r.brand || brandFactValue(r) || '';
    // OnCalisma-V2 (Problem 2) — taksonomi + AI notu alanlarını doldur (P6: ortak helper)
    syncTaxonomyForm(form, r);
    syncDraftForm(form, r);   // Sprint 12 — Ürün Detayları (product_draft)
    // OnCalisma-V2 (Problem 4a) — AI Zenginleştirme paneli (salt-okuma) + durum
    const aiPanel = form.querySelector('.ar-ai-panel');
    if (aiPanel) aiPanel.innerHTML = renderAiPanel(r);
    const aiStatusEl = form.querySelector('.ar-enrich-status-edit');
    if (aiStatusEl) aiStatusEl.textContent = enrichStatusLabel(r.enrichment_status) || 'ham';
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
    if (!form) { toast('Düzenleme formu bulunamadı', 'error'); return null; }
    // Güvenli alan okuyucu: eleman yoksa / value string değilse boş döndür (çökmez) + tanı logu
    const val = (sel) => {
      const el = form.querySelector(sel);
      if (!el || typeof el.value !== 'string') {
        console.warn('[saveEdit] alan okunamadı:', sel, el);
        return '';
      }
      return el.value.trim();
    };
    const payload = {
      product_url: val(CTRL('product_url')),
      master_url: val(CTRL('master_url')),
      notes: val(CTRL('notes')),
    };
    // Marka: düz input (ülke gibi). Mevcut firmayla eşleşirse backend slug'ını korur.
    const brand = val(CTRL('brand'));
    const country = val(CTRL('country'));
    if (!brand) { toast('Firma adı boş', 'error'); return null; }
    payload.brand = brand;
    payload.country = country;
    // OnCalisma-V2 (Problem 2) — taksonomi (boş select → null; checkbox'lar → dizi; style → virgül böl)
    const selVal = (sel) => { const el = form.querySelector(sel); return el && el.value ? el.value : null; };
    payload.category = selVal(CTRL('category'));
    payload.pattern = selVal(CTRL('pattern'));
    const ccRaw = val(CTRL('color_count'));   // P4b renk sayısı
    payload.color_count = ccRaw ? parseInt(ccRaw, 10) : null;
    payload.ai_notu = val(CTRL('ai_notu')) || null;          // P4b AI notu
    payload.weave_tags = [...form.querySelectorAll('.ar-edit-weavetags input[type="checkbox"]:checked')].map(cb => cb.value);
    payload.style_tags = (form.querySelector(CTRL('style_tags'))?.value || '')
      .split(',').map(s => s.trim()).filter(Boolean);
    // Sprint 12 — Ürün Detayları (product_draft jsonb)
    payload.product_draft = collectDraft(form);
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

  // ---- İstemci-içi filtreler: favori (Sprint 6) + olası varyant (OnCalisma-V2) ----
  // Sunucudan gelen satırları yeniden çekmeden DOM'da gizler; birden fazla filtre AND'lenir.
  function applyClientFilters() {
    const onlyFav = $('#filter-favorites-only')?.checked;
    const onlyVariant = $('#filter-variants-only')?.checked;
    $$('.ar-item').forEach(art => {
      const failFav = onlyFav && art.dataset.favorite !== 'true';
      const failVariant = onlyVariant && art.dataset.isVariantCandidate !== 'true';
      art.style.display = (failFav || failVariant) ? 'none' : '';
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

  // OnCalisma-V2 — son çekilen satırlar (sıralama değişince yeniden render; fetch yok)
  let lastRows = [];
  // Çoklu seçim modu (galeri seç modu muadili): seç → sırayla toplu ürüne çevir
  let arSelectMode = false;
  const arSelectedIds = new Set();
  let batchConvertStop = false;
  // OnCalisma-V2 — "olası varyant" rozeti/filtresi için aile sayımı (her render'da listeden türetilir)
  let familyCounts = new Map();
  // OnCalisma-V2 — ISO (UTC) eklenme tarihini yerel saat:dakika ile göster
  function fmtDateTime(iso) {
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return '';
      return d.toLocaleString('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) { return ''; }
  }

  // OnCalisma-V2 (Problem 4a) — AI zenginleştirme yardımcıları (SALT-OKUMA gösterim)
  const FACT_LABELS = {
    brand: 'Marka', product_name: 'Ürün Adı', product_code: 'Ürün Kodu', collection: 'Koleksiyon',
    production_country: 'Üretim Ülkesi', brand_country: 'Firma Ülkesi', composition: 'Kompozisyon', width_cm: 'En (cm)',
    weight_gsm: 'Ağırlık (g/m²)', weave_type: 'Dokuma', repeat_vertical_cm: 'Rapor Boyuna (cm)',
    repeat_horizontal_cm: 'Rapor Enine (cm)', color_count: 'Renk Sayısı', reference_price: 'Fiyat',
    category: 'Kategori', pattern: 'Desen', weave_tags: 'Dokuma Etiketleri',
    color_family: 'Renk Ailesi', style_tags: 'Stil Etiketleri',
  };
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }
  function enrichStatusLabel(s) {
    return ({ raw: '', enriched: 'AI zenginleştirildi', verified: '✓ Doğrulandı' })[s || 'raw'] || '';
  }
  // P5 — yardımcılar
  function safeColor(c) {
    const s = String(c || '').trim();
    return /^#[0-9a-fA-F]{3,8}$/.test(s) ? s : 'transparent';   // CSS injection koruması
  }
  function arraysEqual(a, b) {
    a = a || []; b = b || [];
    if (a.length !== b.length) return false;
    const sa = [...a].sort(), sb = [...b].sort();
    return sa.every((v, i) => v === sb[i]);
  }
  function isSuggestionAccepted(r, field, sug) {
    if (field === 'weave_tags' || field === 'style_tags') return arraysEqual(r[field], sug[field]);
    if (field === 'ai_notu') return r.ai_notu != null && r.ai_notu !== '' && r.ai_notu === sug.ai_notu;
    if (field === 'brand_country') { const v = r.brand_country || r.country; return v != null && v !== '' && v === sug.brand_country; }
    return r[field] != null && r[field] !== '' && r[field] === sug[field];
  }
  // P6 — AI panelindeki kabul edilebilir öğe sayımı (factual + suggested taksonomi + ai_notu)
  function acceptCounts(r) {
    const ef = r.extracted_facts || {};
    const ai = r.ai_summary || {};
    const sug = ai.suggested || {};
    let total = 0, acc = 0;
    Object.keys(ef).forEach(k => {
      const f = ef[k];
      // P6.3 — ŞÜPHELİ alanlar "tümünü kabul" kapsamı DIŞI (sayıma katılmaz)
      if (f && typeof f === 'object' && f.value && !f.unverified) { total++; if (f.accepted) acc++; }
    });
    ['category', 'pattern', 'color_family', 'weave_tags', 'style_tags', 'brand_country'].forEach(field => {
      const has = Array.isArray(sug[field]) ? sug[field].length : !!sug[field];
      if (has) { total++; if (isSuggestionAccepted(r, field, sug)) acc++; }
    });
    if (ai.arge_notu) { total++; if (isSuggestionAccepted(r, 'ai_notu', { ai_notu: ai.arge_notu })) acc++; }
    return { acc, total };
  }
  function isEverythingAccepted(r) {
    const { acc, total } = acceptCounts(r);
    return total > 0 && acc === total;
  }
  // Kayıt tamamlanma durumu — kullanıcı kuralı: A VE B.
  //  A = AI dolduruldu (enriched/verified) ve önerilenin >%50'si kabul edildi.
  //  B = en az 1 foto var.  done = A && B; aksi = "Bekliyor".
  function researchCompletion(r) {
    const { acc, total } = acceptCounts(r);
    const ai = (r.enrichment_status === 'enriched' || r.enrichment_status === 'verified')
      && total > 0 && (acc / total) > 0.5;
    const photo = (r.images_count || (Array.isArray(r.images) ? r.images.length : 0)) >= 1;
    return { done: ai && photo, ai, photo };
  }
  // Sprint 11.6 — AI'nın çıkardığı firma adı (factual). Kabul edilmişse firma input'una yansır.
  // (Firma adı zorunlu; accept-all sonrası kaydet'in "firma adı boş" demesini önler.)
  function brandFactValue(r) {
    const f = r && r.extracted_facts && r.extracted_facts.brand;
    if (f && f.accepted && typeof f.value === 'string') return f.value.trim();
    return '';
  }
  // Firma input'u boşsa, kabul edilen AI firma adıyla doldur (kullanıcı yine de değiştirebilir).
  function fillBrandFromFact(form, r) {
    if (!form) return;
    const el = form.querySelector(CTRL('brand'));
    if (!el || el.value.trim()) return;
    const bf = brandFactValue(r);
    if (bf) el.value = bf;
  }
  // P6 — Düzenle formundaki taksonomi/ai_notu alanlarını r'den senkronla (openEditMode + accept-all paylaşır)
  function syncTaxonomyForm(form, r) {
    if (!form) return;
    const setSel = (name, v) => { const el = form.querySelector(CTRL(name)); if (el) el.value = v || ''; };
    setSel('country', r.country);   // P6.2 firma ülkesi (accept-all sonrası tazelensin)
    setSel('category', r.category);
    setSel('pattern', r.pattern);
    setSel('color_count', r.color_count);   // P4b: renk ailesi yerine renk sayısı
    const wtags = Array.isArray(r.weave_tags) ? r.weave_tags : [];
    form.querySelectorAll('.ar-edit-weavetags input[type="checkbox"]').forEach(cb => { cb.checked = wtags.includes(cb.value); });
    const stEl = form.querySelector(CTRL('style_tags'));
    if (stEl) stEl.value = (Array.isArray(r.style_tags) ? r.style_tags : []).join(', ');
    // P4b: kalıcı AI notu (yoksa AI taslağından doldur)
    const aiNotuEl = form.querySelector(CTRL('ai_notu'));
    if (aiNotuEl) aiNotuEl.value = r.ai_notu || (r.ai_summary && r.ai_summary.arge_notu) || '';
  }
  // Sprint 12 — "Ürün Detayları" alanlarını (product_draft) forma senkronla.
  // Öncelik: product_draft → kabul edilmiş extracted_facts → boş.
  function syncDraftForm(form, r) {
    if (!form) return;
    const pd = (r && r.product_draft) || {};
    const ef = (r && r.extracted_facts) || {};
    const acc = (k) => (ef[k] && ef[k].accepted && ef[k].value != null && ef[k].value !== '') ? ef[k].value : '';
    form.querySelectorAll('[data-draft]').forEach(el => {
      const k = el.dataset.draft;
      let v = (pd[k] != null && pd[k] !== '') ? pd[k] : acc(k);
      el.value = (v == null) ? '' : v;
    });
  }
  // Sprint 12 — Formdaki product_draft alanlarını topla (boş → null).
  function collectDraft(form) {
    const out = {};
    if (!form) return out;
    form.querySelectorAll('[data-draft]').forEach(el => {
      const k = el.dataset.draft;
      const v = (el.value || '').trim();
      out[k] = v === '' ? null : v;
    });
    return out;
  }
  // P4c — Edit drawer AI paneli: alan-alan KABUL kartları (Linkten Doldur tarzı).
  // Her kart: etiket + değer + kaynak alıntısı + Kabul/Geri-Al butonu. Anlık (accept-fact).
  function renderAiPanel(r) {
    const ef = r.extracted_facts || {};
    const ai = r.ai_summary || {};
    const parts = [];
    // P6 — AI Notu artık kabul edilebilir kart (arge_notu → ai_notu); diğer öneriler gibi tek tık
    if (ai.arge_notu) {
      const accN = isSuggestionAccepted(r, 'ai_notu', { ai_notu: ai.arge_notu });
      parts.push(
        `<div class="ar-ai-card${accN ? ' is-accepted' : ''}" data-sfield="ai_notu">` +
          `<div class="ar-ai-card-head">` +
            `<span class="ar-ai-fact-k"><span class="ar-ai-badge">AI</span> AI Notu</span>` +
            `<button type="button" class="ar-ai-suggest-btn" data-sfield="ai_notu">${accN ? '✓ Kabul edildi — Geri Al' : '✓ Kabul'}</button>` +
          `</div>` +
          `<div class="ar-ai-fact-v">${escHtml(ai.arge_notu)}</div>` +
        `</div>`
      );
    }
    // P6.3 — factual'ı DOĞRULANMIŞ / ŞÜPHELİ (unverified) diye ayır; tek kart yardımcısı
    const allKeys = Object.keys(ef).filter(k => ef[k] && typeof ef[k] === 'object' && ef[k].value);
    const verKeys = allKeys.filter(k => !ef[k].unverified);
    const unvKeys = allKeys.filter(k => ef[k].unverified);
    const renderFactCard = (k) => {
      const f = ef[k] || {};
      const acc = !!f.accepted, unv = !!f.unverified;
      const typ = f.type ? ` <em>(${escHtml(f.type)})</em>` : '';
      const cls = 'ar-ai-card' + (acc ? ' is-accepted' : '') + (unv ? ' is-unverified' : '');
      const warn = unv ? ' <span class="ar-ai-warn">⚠ doğrulanamadı</span>' : '';
      const evid = unv
        ? `Kanıt sayfada bulunamadı — model alıntısı: “${escHtml(f.evidence || '— (alıntı yok)')}”`
        : `Kaynak: “${escHtml(f.evidence || '— (alıntı yok)')}”`;
      return (
        `<div class="${cls}" data-field="${escHtml(k)}">` +
          `<div class="ar-ai-card-head">` +
            `<span class="ar-ai-fact-k">${escHtml(FACT_LABELS[k] || k)}${warn}</span>` +
            `<button type="button" class="ar-ai-accept-btn" data-field="${escHtml(k)}">${acc ? '✓ Kabul edildi — Geri Al' : '✓ Kabul'}</button>` +
          `</div>` +
          `<div class="ar-ai-fact-v">${escHtml(f.value)}${typ}</div>` +
          `<div class="ar-ai-evidence">${evid}</div>` +
        `</div>`
      );
    };
    if (verKeys.length) {
      parts.push('<div class="ar-ai-cards">');
      verKeys.forEach(k => parts.push(renderFactCard(k)));
      parts.push('</div>');
    }
    if (unvKeys.length) {
      // P6.3 — varsayılan KAPALI; kullanıcı açıp elle seçer (native <details>, ekstra JS yok)
      parts.push(
        '<details class="ar-ai-unverified">' +
          `<summary class="ar-ai-section-h ar-ai-section-warn">⚠ ${unvKeys.length} Şüpheli alan — sayfada doğrulanamadı (göster / elle seç)</summary>` +
          '<div class="ar-ai-cards">' +
            unvKeys.map(k => renderFactCard(k)).join('') +
          '</div>' +
        '</details>'
      );
    }
    // P5 — Taksonomi ÖNERİLERİ (tahmin) → accept-suggestion
    const sug = ai.suggested || {};
    const taxItems = [];
    if (sug.category) taxItems.push(['category', sug.category]);
    if (sug.pattern) taxItems.push(['pattern', sug.pattern]);
    if (sug.color_family) taxItems.push(['color_family', sug.color_family]);
    if (sug.weave_tags && sug.weave_tags.length) taxItems.push(['weave_tags', sug.weave_tags.join(', ')]);
    if (sug.style_tags && sug.style_tags.length) taxItems.push(['style_tags', sug.style_tags.join(', ')]);
    if (sug.brand_country) taxItems.push(['brand_country', sug.brand_country]);   // P6.2 firma ülkesi (çıkarım)
    if (taxItems.length) {
      const conf = sug.confidence ? ` <span class="ar-ai-conf ar-ai-conf-${escHtml(sug.confidence)}">${escHtml(sug.confidence)}</span>` : '';
      parts.push(`<div class="ar-ai-section-h">AI önerisi (tahmin)${conf}</div>`);
      if (sug.reason) parts.push(`<div class="ar-ai-evidence">${escHtml(sug.reason)}</div>`);
      parts.push('<div class="ar-ai-cards">');
      taxItems.forEach(([field, disp]) => {
        const acc = isSuggestionAccepted(r, field, sug);
        parts.push(
          `<div class="ar-ai-card${acc ? ' is-accepted' : ''}" data-sfield="${escHtml(field)}">` +
            `<div class="ar-ai-card-head">` +
              `<span class="ar-ai-fact-k">${escHtml(FACT_LABELS[field] || field)}</span>` +
              `<button type="button" class="ar-ai-suggest-btn" data-sfield="${escHtml(field)}">${acc ? '✓ Kabul edildi — Geri Al' : '✓ Kabul'}</button>` +
            `</div>` +
            `<div class="ar-ai-fact-v">${escHtml(disp)}</div>` +
          `</div>`
        );
      });
      parts.push('</div>');
    }
    // P5 — Görsel analizi (tahmin; gösterim). color_count "↳ yaz" → manuel color_count alanına.
    const ia = ai.image_analysis || {};
    if (ia.dominant_colors || ia.texture || ia.transparency || ia.color_count) {
      const sw = (ia.dominant_colors || []).map(c =>
        `<span class="ar-ai-swatch" style="background:${safeColor(c)}" title="${escHtml(c)}"></span>`).join('');
      const bits = [];
      if (ia.texture) bits.push('Doku: ' + escHtml(ia.texture));
      if (ia.transparency) bits.push('Şeffaflık: ' + escHtml(ia.transparency));
      if (ia.color_count) bits.push(`Renk sayısı: ${escHtml(ia.color_count)} <button type="button" class="ar-ai-applycc" data-cc="${escHtml(ia.color_count)}">↳ yaz</button>`);
      const conf = ia.confidence ? ` <span class="ar-ai-conf ar-ai-conf-${escHtml(ia.confidence)}">${escHtml(ia.confidence)}</span>` : '';
      parts.push(`<div class="ar-ai-section-h">Görsel analizi${conf}</div>`);
      parts.push('<div class="ar-ai-image">' +
        (sw ? `<div class="ar-ai-swatches">${sw}</div>` : '') +
        (bits.length ? `<div class="ar-ai-img-meta">${bits.join(' · ')}</div>` : '') +
        (ia.note ? `<div class="ar-ai-evidence">${escHtml(ia.note)}</div>` : '') +
      '</div>');
    }
    if (!parts.length) return '<div class="ar-ai-empty">Henüz zenginleştirilmedi. “AI ile Zenginleştir”e bas.</div>';
    return parts.join('');
  }
  // Kart başlığı altındaki tek-satır arge özeti (arge yoksa gizle — spec)
  function fillArgeLine(article, r) {
    const el = article.querySelector('.ar-item-arge');
    if (!el) return;
    const arge = (r.ai_summary && r.ai_summary.arge_notu) || '';
    if (!arge) { el.hidden = true; el.innerHTML = ''; return; }
    const st = enrichStatusLabel(r.enrichment_status);
    el.innerHTML = `<span class="ar-ai-badge">AI</span> <span class="ar-arge-text">${escHtml(arge)}</span>` +
      (st ? ` <span class="ar-enrich-status">${escHtml(st)}</span>` : '');
    el.hidden = false;
  }
  // P6 — Listede "Kabul N/M" rozeti (çekmeceyi açmadan onay durumu görünür)
  function updateAcceptBadge(article, r) {
    updateDoneBadge(article, r);   // her çağrıda (render + accept/enrich sonrası) durum rozetini de tazele
    updateGroupSummary(article);    // grup başlığı özet chip'lerini yerinde tazele (re-render/çekmece kapatmadan)
    const metaEl = article.querySelector('.ar-item-meta');
    if (!metaEl) return;
    let badge = metaEl.querySelector('.ar-accept-badge');
    const { acc, total } = acceptCounts(r);
    if (!total) { if (badge) badge.remove(); return; }
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'ar-accept-badge';
      metaEl.appendChild(badge);
    }
    badge.textContent = `Kabul ${acc}/${total}`;
    badge.classList.toggle('is-complete', acc === total);
  }
  // Grup başlığı özet chip'leri (✓Tamamlandı + AI a/n + Foto p/n) — renderList + yerinde tazeleme paylaşır
  function groupProgHtml(rows) {
    const n = rows.length;
    let doneN = 0, aiN = 0, photoN = 0;
    rows.forEach(x => { const c = researchCompletion(x); if (c.done) doneN++; if (c.ai) aiN++; if (c.photo) photoN++; });
    return (doneN ? `<span class="ar-grp-done" title="Tamamlandı (AI + foto) · bekleyen: ${n - doneN}"><svg class="icon"><use href="#ic-check"/></svg>${doneN}</span>` : '')
      + `<span class="ar-grp-ai" title="AI dolduruldu: ${aiN} · eksik: ${n - aiN}"><svg class="icon"><use href="#ic-zap"/></svg>${aiN}/${n}</span>`
      + `<span class="ar-grp-photo" title="Fotoğraflı: ${photoN} · foto yok: ${n - photoN}"><svg class="icon"><use href="#ic-image"/></svg>${photoN}/${n}</span>`;
  }
  // Çekmeceyi kapatmadan / listeyi re-render etmeden, yalnız ilgili grubun başlık sayılarını günceller.
  // (accept-all / enrich-apply / kombo / tek-tek kabul sonrası updateAcceptBadge üzerinden çağrılır.)
  function updateGroupSummary(article) {
    const groupEl = article && article.closest && article.closest('.ar-group');
    if (!groupEl) return;   // render anında (article henüz gruba eklenmemiş) → no-op
    const key = groupEl.dataset.key;
    const prog = groupEl.querySelector('.ar-group-prog');
    if (!prog) return;
    const rows = (lastRows || []).filter(x => brandCountryGroupKey(x) === key);
    if (rows.length) prog.innerHTML = groupProgHtml(rows);
  }
  // Kayıt durum rozeti: "Tamamlandı" (yeşil) / "Bekliyor" (amber, title eksiği söyler)
  function updateDoneBadge(article, r) {
    const metaEl = article.querySelector('.ar-item-meta');
    if (!metaEl) return;
    let badge = metaEl.querySelector('.ar-done-badge');
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'ar-done-badge';
      metaEl.insertBefore(badge, metaEl.firstChild);   // satırın başında, en görünür
    }
    const c = researchCompletion(r);
    badge.classList.toggle('is-done', c.done);
    if (c.done) {
      badge.textContent = 'Tamamlandı';
      badge.title = 'AI dolduruldu (>%50 kabul) ve en az 1 foto var';
    } else {
      const eksik = [!c.ai ? 'AI/%50' : null, !c.photo ? 'foto' : null].filter(Boolean).join(' + ');
      badge.textContent = 'Bekliyor';
      badge.title = 'Bekliyor — eksik: ' + eksik;
    }
  }

  function renderList(rows) {
    elListContainer.innerHTML = '';
    elEmpty.hidden = rows.length > 0;
    if (!rows.length) return;

    // OnCalisma-V2 — "olası varyant" türetme: aynı family_key'den listede ≥2 kayıt varsa
    // o ailenin TÜM üyeleri varyant adayı sayılır. Bir kayıt silinince renderListFromAPI
    // yeniden render eder → sayım güncellenir → tek kalan kayıttan rozet kendiliğinden kalkar.
    familyCounts = new Map();
    rows.forEach(r => {
      const fk = (r.family_key || '').trim();
      if (fk && !fk.endsWith(':')) familyCounts.set(fk, (familyCounts.get(fk) || 0) + 1);
    });

    // Group by country → brand
    const groups = {};
    rows.forEach(r => {
      const key = brandCountryGroupKey(r);
      (groups[key] ||= []).push(r);
    });

    // Sort: country asc, brand asc (grup sırası)
    const sortedKeys = Object.keys(groups).sort((a, b) => a.localeCompare(b, 'tr'));
    // OnCalisma-V2 — grup İÇİNDE eklenme tarihine göre sırala (yeni→eski varsayılan)
    const sortDir = ($('#filter-sort')?.value === 'date_asc') ? 1 : -1;

    sortedKeys.forEach(key => {
      groups[key].sort((a, b) => sortDir * String(a.added_at || '').localeCompare(String(b.added_at || '')));
      const groupEl = document.createElement('div');
      groupEl.className = 'ar-group';
      groupEl.dataset.key = key;   // accordion açık-durumunu re-render sonrası eşleştirmek için
      const head = document.createElement('div');
      head.className = 'ar-group-head';
      // Grup özeti (accordion açmadan): Tamamlandı (AI+foto) + AI ve Foto kırılımı (kaç var / toplam).
      head.innerHTML = `<span class="ar-group-title">${key}</span>`
        + `<span class="ar-group-prog">${groupProgHtml(groups[key])}</span>`;
      groupEl.appendChild(head);

      groups[key].forEach(r => {
        try {
          groupEl.appendChild(renderItem(r));
        } catch (err) {
          console.error('[renderItem] satır render hatası:', r && r.id, err);
        }
      });

      // v4.0-part-2 Sprint 7 — Grup-içi "+ Yeni satır" formu
      // Master URL + brand + country grup'taki ilk satırdan miras alınır
      const inheritFrom = groups[key][0];
      groupEl.appendChild(renderGroupAddRow(inheritFrom));

      elListContainer.appendChild(groupEl);
    });
    // Render sonrası favori filtresini uygula (eğer aktifse)
    applyClientFilters();
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
    // Çoklu seçim: re-render'da seçim korunur + seç modunda öğeye tıkla → seç/bırak
    if (arSelectedIds.has(r.id)) article.classList.add('is-selected');
    article.addEventListener('click', (e) => {
      if (!arSelectMode) return;
      if (e.target.closest('button, a, input, select, textarea, label')) return;  // kontrolleri ezme
      e.preventDefault();
      const id = article.dataset.id;
      if (arSelectedIds.has(id)) { arSelectedIds.delete(id); article.classList.remove('is-selected'); }
      else { arSelectedIds.add(id); article.classList.add('is-selected'); }
      arUpdateSelCount();
    });

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
          applyClientFilters();
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
    // P6 — "Tümünü Kabul" toggle (label r'nin onay durumuna göre güncellenir)
    const acceptAllBtn = node.querySelector('.ar-btn-accept-all');
    function refreshAcceptAllLabel() {
      if (acceptAllBtn) acceptAllBtn.textContent = isEverythingAccepted(r) ? '↩ Tümünü Geri Al' : '✓ Tümünü Kabul';
    }
    refreshAcceptAllLabel();
    editBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openEditMode(article, r);
    });
    node.querySelector('.ar-edit-cancel').addEventListener('click', () => {
      closeEditMode(article);
    });
    node.querySelector('.ar-edit-save').addEventListener('click', async () => {
      try {
        const updated = await saveEdit(article, r);
        if (updated) {
          Object.assign(r, updated);
          closeEditMode(article);
          renderListFromAPI();
        }
      } catch (err) {
        console.error('[Kaydet]', err);
        toast('Kaydet hatası: ' + (err && err.message ? err.message : err), 'error');
      }
    });
    // OnCalisma-V2 (Problem 4a / P4a-2) — AI Zenginleştir + model seçici + Doğrulandı işaretle
    // Model seçimi ekle.html ile AYNI localStorage anahtarında → kota dolunca tek yerden flash↔lite geçiş
    const MODEL_KEY = 'mobidik_gemini_model';
    const modelSel = node.querySelector('.ar-enrich-model');
    if (modelSel) {
      try { const saved = localStorage.getItem(MODEL_KEY); if (saved !== null) modelSel.value = saved; } catch (e) {}
      modelSel.addEventListener('change', () => { try { localStorage.setItem(MODEL_KEY, modelSel.value); } catch (e) {} });
    }
    // Kullanıcı isteği — "AI ile Zenginleştir" TEK TIK = AI Doldur (üzerine yaz) → Tümünü Kabul
    // (şüpheli/uydurma hariç, server P6.3) → Kaydet. Mevcut uçların zinciri; diğer butonlar +
    // batch /enrich endpoint'i DEĞİŞMEZ.
    const enrichBtn = node.querySelector('.ar-btn-enrich');
    if (enrichBtn) enrichBtn.addEventListener('click', () => runWithProgress(enrichBtn, 'AI dolduruyor + kabul + kaydet…', async (signal) => {
      const chosen = modelSel ? (modelSel.value || '') : '';
      // 1) AI Doldur (üzerine yaz) = enrich-apply (kolonlar + product_draft'a yaz)
      const r1 = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}/enrich-apply`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chosen ? { model: chosen } : {}), signal,
      });
      const d1 = await r1.json();
      if (!(d1.ok && d1.row)) {
        toast((d1.message || d1.error || 'AI doldurulamadı') + (d1.model ? ' (' + d1.model + ')' : ''), 'error');
        return;
      }
      Object.assign(r, d1.row);
      if (d1.model_invalid) toast('Geçersiz model — server varsayılanı kullanıldı', 'error');
      // 2) Tümünü Kabul (daima accept; server şüpheli/uydurma alanları P6.3 ile hariç tutar)
      try {
        const r2 = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}/accept-all`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ accepted: true }), signal,
        });
        const d2 = await r2.json();
        if (d2.ok) {
          if (d2.extracted_facts) r.extracted_facts = d2.extracted_facts;
          ['category', 'pattern', 'color_family', 'weave_tags', 'style_tags', 'ai_notu', 'brand_country', 'country', 'enrichment_status'].forEach(k => { if (k in d2) r[k] = d2[k]; });
        } else {
          toast('Kabul kısmı başarısız — yine de kaydediliyor', 'error');
        }
      } catch (e) { toast('Kabul kısmı atlandı (bağlantı) — kaydediliyor', 'error'); }
      // 3) Formu r'ye senkronla → Kaydet (saveEdit formdan kalıcılaştırır; extracted_facts'e dokunmaz)
      if (editForm) {
        const bEl = editForm.querySelector(CTRL('brand')); if (bEl) bEl.value = r.brand || '';
        syncTaxonomyForm(editForm, r);
        syncDraftForm(editForm, r);
        fillBrandFromFact(editForm, r);
      }
      const saved = await saveEdit(article, r);   // 'Kaydedildi' toast'ı + kalıcılaştırma
      if (saved) Object.assign(r, saved);
      // Panel + durum + rozetleri tazele
      if (editForm) {
        const p = editForm.querySelector('.ar-ai-panel'); if (p) p.innerHTML = renderAiPanel(r);
        const s = editForm.querySelector('.ar-enrich-status-edit'); if (s) s.textContent = enrichStatusLabel(r.enrichment_status) || 'ham';
      }
      fillArgeLine(article, r);
      updateAcceptBadge(article, r);
      refreshAcceptAllLabel();
      // P6.1 — sayfada kanıtı bulunamayan (uydurma şüpheli) alanlar kabul EDİLMEDİ; uyar
      if (d1.unverified_fields && d1.unverified_fields.length) {
        toast(`${d1.unverified_fields.length} alan sayfada doğrulanamadı — ⚠ Şüpheli (kabul edilmedi), elle kontrol et`, 'error');
      }
    }));
    // Sprint 12 — "AI Doldur (üzerine yaz)": enrich-apply → tüm form alanlarını AI ile üzerine yaz
    const enrichApplyBtn = node.querySelector('.ar-btn-enrich-apply');
    if (enrichApplyBtn) enrichApplyBtn.addEventListener('click', () => runWithProgress(enrichApplyBtn, 'AI dolduruyor…', async (signal) => {
      const chosen = modelSel ? (modelSel.value || '') : '';
      const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}/enrich-apply`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chosen ? { model: chosen } : {}), signal,
      });
      const d = await res.json();
      if (d.ok && d.row) {
        Object.assign(r, d.row);   // kolonlar + product_draft + staging güncellendi
        if (editForm) {
          const bEl = editForm.querySelector(CTRL('brand')); if (bEl) bEl.value = r.brand || '';
          syncTaxonomyForm(editForm, r);
          syncDraftForm(editForm, r);
          const p = editForm.querySelector('.ar-ai-panel'); if (p) p.innerHTML = renderAiPanel(r);
          const s = editForm.querySelector('.ar-enrich-status-edit'); if (s) s.textContent = enrichStatusLabel(r.enrichment_status) || 'ham';
        }
        fillArgeLine(article, r);
        updateAcceptBadge(article, r);
        refreshAcceptAllLabel();
        toast('AI dolduruldu (üzerine yazıldı)' + (d.model ? ' · ' + d.model : ''), 'success');
        if (d.model_invalid) toast('Geçersiz model — server varsayılanı kullanıldı', 'error');
        if (d.unverified_fields && d.unverified_fields.length) {
          toast(`${d.unverified_fields.length} alan sayfada doğrulanamadı — panelde ⚠ Şüpheli grubunda, elle kontrol et`, 'error');
        }
      } else {
        toast((d.message || d.error || 'Doldurulamadı') + (d.model ? ' (' + d.model + ')' : ''), 'error');
      }
    }));
    // Ortak çekirdek: kaydı ürüne çevir — FORM-BAĞIMSIZ (to-product sunucuda kalıcı
    // product_draft + kabul edilmiş extracted_facts'ten okur; DOM formu gerekmez).
    // openAfter=true → ürün sayfasına git · false → toast + listede kal (accordion korunur).
    // Hata/eksik veride (örn. product_name boş → 400) onFail() çağrılır.
    async function createFromResearch(openAfter, onFail) {
      try {
        const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}/to-product`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
        });
        const d = await res.json();
        if (d.ok) {
          if (openAfter) {
            toast('Ürün oluşturuldu', 'success');
            window.location.href = d.redirect || `/urun/${d.urun_id}`;
          } else {
            // Listede kal: satır 'imported'a döner (pending'de listeden düşer). renderListFromAPI accordion korur.
            toast('Ürün oluşturuldu ✓ — ' + (d.urun_id || ''), 'success', 5000);
            renderListFromAPI();
          }
          return true;
        }
        toast(d.error || d.message || 'Ürün oluşturulamadı', 'error');
        if (onFail) onFail();
        return false;
      } catch (e) {
        toast('Bağlantı hatası', 'error');
        if (onFail) onFail();
        return false;
      }
    }
    // Çekmece butonları: "Ürün Oluştur" (kal) / "Oluştur ve Aç" (git). Form doğrula + kaydet → createFromResearch.
    async function convertToProduct(btn, openAfter) {
      const brandEl = editForm && editForm.querySelector(CTRL('brand'));
      const pnEl = editForm && editForm.querySelector('[data-draft="product_name"]');
      if (brandEl && !brandEl.value.trim()) { toast('Marka boş', 'error'); brandEl.focus(); return; }
      if (pnEl && !pnEl.value.trim()) { toast('Ürün adı boş — AI Doldur ile getir veya elle yaz', 'error'); pnEl.focus(); return; }
      const convBtns = [node.querySelector('.ar-edit-to-product'), node.querySelector('.ar-edit-to-product-open')].filter(Boolean);
      const snapshot = convBtns.map(b => ({ b, html: b.innerHTML }));
      const undo = () => snapshot.forEach(x => { x.b.disabled = false; x.b.innerHTML = x.html; });
      convBtns.forEach(b => { b.disabled = true; });
      btn.innerHTML = 'Oluşturuluyor…';
      let saved;
      try { saved = await saveEdit(article, r); }   // çekmece açık → form senkron; product_draft kalıcılaşsın
      catch (e) { toast('Kaydet hatası', 'error'); undo(); return; }
      if (!saved) { undo(); return; }
      Object.assign(r, saved);
      await createFromResearch(openAfter, undo);
    }
    const toProductBtn = node.querySelector('.ar-edit-to-product');
    if (toProductBtn) toProductBtn.addEventListener('click', () => convertToProduct(toProductBtn, false));
    const toProductOpenBtn = node.querySelector('.ar-edit-to-product-open');
    if (toProductOpenBtn) toProductOpenBtn.addEventListener('click', () => convertToProduct(toProductOpenBtn, true));
    // P6 — Tümünü Kabul / Geri Al (toggle): tek istek, tüm AI öğeleri
    if (acceptAllBtn) acceptAllBtn.addEventListener('click', async () => {
      const wantAccept = !isEverythingAccepted(r);
      acceptAllBtn.disabled = true;
      acceptAllBtn.textContent = wantAccept ? 'Kabul ediliyor…' : 'Geri alınıyor…';
      try {
        const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}/accept-all`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ accepted: wantAccept }),
        });
        const d = await res.json();
        if (d.ok) {
          if (d.extracted_facts) r.extracted_facts = d.extracted_facts;
          ['category', 'pattern', 'color_family', 'weave_tags', 'style_tags', 'ai_notu', 'brand_country', 'country', 'enrichment_status'].forEach(k => {
            if (k in d) r[k] = d[k];
          });
          if (editForm) {
            syncTaxonomyForm(editForm, r);
            fillBrandFromFact(editForm, r);   // Sprint 11.6 — kabul edilen firma adını input'a yansıt
            const p = editForm.querySelector('.ar-ai-panel'); if (p) p.innerHTML = renderAiPanel(r);
            const s = editForm.querySelector('.ar-enrich-status-edit'); if (s) s.textContent = enrichStatusLabel(r.enrichment_status) || 'ham';
          }
          updateAcceptBadge(article, r);
          fillArgeLine(article, r);
          toast(wantAccept ? 'Tümü kabul edildi' : 'Tümü geri alındı', 'success');
        } else {
          toast(d.error || 'İşlem başarısız', 'error');
        }
      } catch (e) { toast('Bağlantı hatası', 'error'); }
      finally { acceptAllBtn.disabled = false; refreshAcceptAllLabel(); }
    });
    // P4c — Alan-alan KABUL/GERİ-AL (anlık). Delege: panel container'a tek listener
    // (innerHTML değişse de buton tıklamaları yakalanır). 'Doğrulandı' (bulk) kaldırıldı.
    const aiPanelEl = node.querySelector('.ar-ai-panel');
    if (aiPanelEl) aiPanelEl.addEventListener('click', async (ev) => {
      // P5 — görsel renk sayısını manuel color_count alanına uygula (client-only; Kaydet ile onaylanır)
      const applyCc = ev.target.closest('.ar-ai-applycc');
      if (applyCc) {
        const cc = editForm && editForm.querySelector(CTRL('color_count'));
        if (cc) { cc.value = String(applyCc.dataset.cc || '').replace(/[^0-9]/g, ''); toast('Renk sayısı alana yazıldı (Kaydet ile onayla)', 'success'); }
        return;
      }
      // P5/P6 — öneri (taksonomi + ai_notu) kabul/geri-al → /accept-suggestion (research kolonuna yazar)
      const sBtn = ev.target.closest('.ar-ai-suggest-btn');
      if (sBtn) {
        const sfield = sBtn.dataset.sfield;
        const sug = (r.ai_summary && r.ai_summary.suggested) || {};
        // P6 — ai_notu kaynağı suggested DEĞİL → ai_summary.arge_notu
        const cmp = sfield === 'ai_notu' ? { ai_notu: (r.ai_summary && r.ai_summary.arge_notu) } : sug;
        const wantAccept = !isSuggestionAccepted(r, sfield, cmp);
        const sOld = sBtn.textContent;
        sBtn.disabled = true; sBtn.textContent = '…';
        try {
          const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}/accept-suggestion`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ field: sfield, accepted: wantAccept }),
          });
          const d = await res.json();
          if (d.ok) {
            r[sfield] = d.value;
            if (editForm) {
              if (sfield === 'weave_tags') {
                const set = new Set(d.value || []);
                editForm.querySelectorAll('.ar-edit-weavetags input[type="checkbox"]').forEach(cb => { cb.checked = set.has(cb.value); });
              } else if (sfield === 'style_tags') {
                const el = editForm.querySelector(CTRL('style_tags')); if (el) el.value = (d.value || []).join(', ');
              } else if (sfield === 'ai_notu') {
                const el = editForm.querySelector(CTRL('ai_notu')); if (el) el.value = d.value || '';
              } else if (sfield === 'brand_country') {
                const el = editForm.querySelector(CTRL('country')); if (el) el.value = d.value || '';
                r.country = d.value;   // firma ülkesi = görünen country
              } else {
                const el = editForm.querySelector(CTRL(sfield)); if (el) el.value = d.value || '';
              }
              const p = editForm.querySelector('.ar-ai-panel'); if (p) p.innerHTML = renderAiPanel(r);
            }
            updateAcceptBadge(article, r);
            refreshAcceptAllLabel();
            toast(wantAccept ? 'Öneri kabul edildi' : 'Geri alındı', 'success');
          } else { toast(d.error || 'İşlem başarısız', 'error'); sBtn.disabled = false; sBtn.textContent = sOld; }
        } catch (e) { toast('Bağlantı hatası', 'error'); sBtn.disabled = false; sBtn.textContent = sOld; }
        return;
      }
      // P4c — factual KABUL/GERİ-AL → /accept-fact
      const btn = ev.target.closest('.ar-ai-accept-btn');
      if (!btn) return;
      const field = btn.dataset.field;
      const cur = !!(r.extracted_facts && r.extracted_facts[field] && r.extracted_facts[field].accepted);
      const bOld = btn.textContent;
      btn.disabled = true; btn.textContent = '…';
      try {
        const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}/accept-fact`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ field, accepted: !cur }),
        });
        const d = await res.json();
        if (d.ok) {
          if (!r.extracted_facts) r.extracted_facts = {};
          if (!r.extracted_facts[field]) r.extracted_facts[field] = {};
          r.extracted_facts[field].accepted = d.accepted;
          if (d.enrichment_status) r.enrichment_status = d.enrichment_status;
          if (field === 'brand' && d.accepted) fillBrandFromFact(editForm, r);  // Sprint 11.6 — firma adını input'a yansıt
          if (editForm) {
            const p = editForm.querySelector('.ar-ai-panel'); if (p) p.innerHTML = renderAiPanel(r);
            const s = editForm.querySelector('.ar-enrich-status-edit'); if (s) s.textContent = enrichStatusLabel(r.enrichment_status) || 'ham';
          }
          updateAcceptBadge(article, r);
          refreshAcceptAllLabel();
          toast(d.accepted ? 'Kabul edildi' : 'Geri alındı', 'success');
        } else { toast(d.error || 'İşlem başarısız', 'error'); btn.disabled = false; btn.textContent = bOld; }
      } catch (e) { toast('Bağlantı hatası', 'error'); btn.disabled = false; btn.textContent = bOld; }
    });
    // (Marka artık input+datalist; eski select 'change' autofill/yeni-firma toggle kaldırıldı.
    //  Bilinen markaya ülke otomatik dolumu artık backend'de yapılır — kaydet'te.)

    const img = node.querySelector('.ar-item-thumb img');
    const placeholder = node.querySelector('.ar-thumb-placeholder');
    // OnCalisma-V2 (Problem 3) — kapak önceliği TEK KAYNAK sunucuda (cover_url:
    // yakalanan görsel → og:image). JS yalnız UI fallback'i ekler: favicon → placeholder.
    const fallbackFavicon = googleFaviconUrl(r.product_url, 64);
    const finalSrc = r.cover_url || fallbackFavicon || '';
    if (finalSrc) {
      img.src = finalSrc;
      img.alt = r.product_url;
      img.referrerPolicy = 'no-referrer';
      placeholder.style.display = 'none';
      img.onerror = () => { img.style.display = 'none'; placeholder.style.display = ''; };
      // Gerçek galeri görseli ise cover-stilini ver (favicon değil)
      if (r.cover_url) {
        img.parentElement?.classList.add('has-cover');
      }
    } else {
      img.style.display = 'none';
    }

    const urlShort = shortUrl(r.product_url);
    // P4b — havuz listesi ÜRÜN ADIYLA: AI ürün adı → eklenti page_title → URL path (kriptik son çare)
    const _aiName = r.extracted_facts && r.extracted_facts.product_name && r.extracted_facts.product_name.value;
    node.querySelector('.ar-item-title').textContent = _aiName || r.page_title || urlShort.path || r.product_url;
    const imgCountStr = r.images_count > 0 ? ` · × ${r.images_count} görsel` : '';
    const metaEl = node.querySelector('.ar-item-meta');
    metaEl.textContent = `${r.brand} · ${r.country}${r.country_code ? ' (' + r.country_code + ')' : ''}${imgCountStr}`;
    // OnCalisma-V2 (Problem 1) — varyant adayı rozeti + family_key işareti (gizleme/silme YOK)
    const fk = (r.family_key || '').trim();
    if (fk) article.dataset.familyKey = fk;
    // OnCalisma-V2 — rozet/filtre DB bayrağından DEĞİL, listedeki aile sayısından türetilir
    // (aynı family_key'den ≥2 kayıt → varyant adayı). Silince yeniden hesaplanır → stale yok.
    const famCount = (fk && !fk.endsWith(':')) ? (familyCounts.get(fk) || 0) : 0;
    const isVariant = famCount >= 2;
    article.dataset.isVariantCandidate = isVariant ? 'true' : 'false';
    if (isVariant) {
      const vb = document.createElement('span');
      vb.className = 'ar-variant-badge';
      vb.textContent = '↔ olası varyant';
      vb.title = `Listede aynı üründen ${famCount} kayıt var · Aile: ${fk}`;
      metaEl.appendChild(vb);
    }
    // OnCalisma-V2 (Problem 2) — taksonomi etiketleri (linki açmadan ne olduğu görünür)
    [['category', r.category], ['pattern', r.pattern], ['color-family', r.color_family]].forEach(([kind, val]) => {
      if (!val) return;
      const tb = document.createElement('span');
      tb.className = 'ar-tax-badge ar-tax-' + kind;
      tb.textContent = val;
      metaEl.appendChild(tb);
    });
    // OnCalisma-V2 (Problem 4a) — başlık altı tek-satır AI arge özeti (yoksa gizli)
    fillArgeLine(article, r);
    // P6 — meta satırında "Kabul N/M" rozeti (onay durumu çekmece açmadan görünür)
    updateAcceptBadge(article, r);
    // OnCalisma-V2 — eklenme tarihi (saat:dakika)
    const dateEl = node.querySelector('.ar-item-date');
    if (dateEl) dateEl.textContent = r.added_at ? ('🕒 ' + fmtDateTime(r.added_at)) : '';

    // v4.0-part-2 Sprint 10 — Karta tıklayınca detay sayfasına git
    // (interactive child element'lere değil — buton/link/input/star)
    article.classList.add('is-clickable');
    article.addEventListener('click', (e) => {
      if (e.target.closest('button, a, input, select, textarea, .ar-fav-star, .ar-item-edit')) return;
      window.location.href = `/arastirma/${encodeURIComponent(r.id)}`;
    });
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
    // OnCalisma-V2 — Ürün URL'i (master altında); varyant tespiti için path + query görünür
    const productCell = node.querySelector('.ar-item-product');
    if (productCell) {
      if (r.product_url) {
        let label = shortUrl(r.product_url).host_path;
        try { const pu = new URL(r.product_url); if (pu.search) label += pu.search; } catch (e) {}
        productCell.href = r.product_url;
        productCell.textContent = `Ürün: ${label}`;
        productCell.title = r.product_url;
        productCell.addEventListener('click', (e) => e.stopPropagation());
      } else {
        productCell.removeAttribute('href');
        productCell.textContent = '';
      }
    }
    const notesCell = node.querySelector('.ar-item-notes');
    if (r.notes) notesCell.textContent = `📝 ${r.notes}`;

    const openBtn = node.querySelector('.ar-item-open');
    openBtn.href = r.product_url;

    const importBtn = node.querySelector('.ar-item-import');
    if (r.status === 'imported') {
      importBtn.classList.remove('btn-primary');
      importBtn.classList.add('btn-secondary');
      importBtn.querySelector('span').textContent = `Ürün: ${r.imported_product_id || ''}`;
      importBtn.href = r.imported_product_id ? `/urun/${r.imported_product_id}` : '#';
    } else {
      // UX: "Ürüne çevir" duruma-duyarlı. Bekliyor → çekmeceyi aç (bilgileri tamamla).
      // Tamamlandı → doğrudan ürün oluştur + galeriye gönder + LİSTEDE KAL (açmaz).
      importBtn.href = '#';
      const openDrawer = () => {
        openEditMode(article, r);
        const pd = article.querySelector('.ar-edit-product'); if (pd) pd.open = true;
        article.scrollIntoView({ behavior: 'smooth', block: 'start' });
      };
      // Görsel ipucu (render anı): hazırsa factory ("oluştur"), değilse plus ("aç")
      const doneNow = researchCompletion(r).done;
      const useEl = importBtn.querySelector('use');
      if (useEl) useEl.setAttribute('href', doneNow ? '#ic-factory' : '#ic-plus');
      importBtn.title = doneNow
        ? 'Hazır — tıkla: ürünü oluştur ve galeriye gönder (sayfayı açmaz)'
        : 'Bilgileri tamamlamak için aç';
      importBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        // Tıklama anında yeniden değerlendir (çekmecede kabul/AI sonrası r güncellenmiş olabilir)
        if (!researchCompletion(r).done) { openDrawer(); return; }   // Bekliyor → çekmece
        // Tamamlandı → doğrudan oluştur. saveEdit YOK (form açık değil; to-product kalıcı veriden okur).
        const span = importBtn.querySelector('span'); const old = span ? span.textContent : '';
        if (span) span.textContent = 'Oluşturuluyor…';
        importBtn.style.pointerEvents = 'none';
        const restore = () => { if (span) span.textContent = old; importBtn.style.pointerEvents = ''; };
        // Veri eksikse (örn. product_name boş → 400) çekmece açılır ki kullanıcı tamamlasın.
        await createFromResearch(false, () => { restore(); openDrawer(); });
        // Başarıda renderListFromAPI bu düğümü yeniler → restore gereksiz.
      });
    }

    const dismissBtn = node.querySelector('.ar-item-dismiss');
    const restoreBtn = node.querySelector('.ar-item-restore');
    const hardDelBtn = node.querySelector('.ar-item-harddelete');
    if (r.status === 'dismissed') {
      dismissBtn.hidden = true;
      restoreBtn.hidden = false;
      if (hardDelBtn) hardDelBtn.hidden = false;   // reddedilenlerde kalıcı sil
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
    if (hardDelBtn) hardDelBtn.addEventListener('click', async () => {
      if (!confirm('Bu kayıt KALICI olarak silinsin mi?\nBu işlem geri alınamaz; görselleri de silinir.')) return;
      try {
        const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}?hard=1`, { method: 'DELETE' });
        const d = await res.json();
        if (d.ok) { toast('Kalıcı silindi', 'success'); renderListFromAPI(); }
        else toast(d.error || 'Silinemedi', 'error');
      } catch (e) { toast('Ağ hatası', 'error'); }
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

  // ---- Accordion + scroll durumunu re-render boyunca koru ----
  // renderList() listeyi sıfırdan kurar (innerHTML=''), açık grup/scroll kaybolurdu.
  // Yakala → render → grupları data-key ile eşleştirip .is-open + scroll geri yükle.
  function captureListState() {
    return {
      openKeys: Array.from(elListContainer.querySelectorAll('.ar-group.is-open'))
        .map(g => g.dataset.key),
      scrollY: window.scrollY,
    };
  }
  function restoreListState(st) {
    if (!st) return;
    if (st.openKeys && st.openKeys.length) {
      const open = new Set(st.openKeys);
      elListContainer.querySelectorAll('.ar-group').forEach(g => {
        if (open.has(g.dataset.key)) g.classList.add('is-open');
      });
    }
    if (typeof st.scrollY === 'number') window.scrollTo(0, st.scrollY);
  }

  // ---- Filtre uygula ----
  async function renderListFromAPI() {
    const _st = captureListState();
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
        lastRows = data.rows || [];
        renderList(lastRows);
        // Ülke filtresi seçeneklerini güncelle
        populateCountryFilter(lastRows);
        restoreListState(_st);   // açık accordion + scroll'u koru
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
  $('#filter-favorites-only').addEventListener('change', applyClientFilters);
  // OnCalisma-V2 — "sadece olası varyantlar" istemci filtresi
  $('#filter-variants-only')?.addEventListener('change', applyClientFilters);
  // OnCalisma-V2 — sıralama değişince yeniden render (fetch yok, son satırları kullan)
  $('#filter-sort')?.addEventListener('change', () => { const _st = captureListState(); renderList(lastRows); applyClientFilters(); restoreListState(_st); });
  $('#btn-refresh-list').addEventListener('click', renderListFromAPI);

  // P6 — Ctrl/Cmd+S: açık düzenleme çekmecesini kaydet (tek global listener)
  document.addEventListener('keydown', (e) => {
    if (!((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S'))) return;
    const editing = document.querySelector('.ar-item.is-editing');
    if (!editing) return;
    e.preventDefault();
    editing.querySelector('.ar-edit-save')?.click();
  });

  // P5 — Toplu zenginleştirme: listedeki raw kayıtları sırayla /enrich'e gönder (seçili model, durdurulabilir)
  let batchStop = false;
  const batchBtn = $('#btn-enrich-batch');
  if (batchBtn) batchBtn.addEventListener('click', async () => {
    if (batchBtn.dataset.running === '1') { batchStop = true; batchBtn.textContent = 'Durduruluyor…'; return; }
    const raws = (lastRows || []).filter(r => (r.enrichment_status || 'raw') === 'raw' && String(r.product_url || '').startsWith('http'));
    if (!raws.length) { toast('Zenginleştirilecek (raw) kayıt yok', 'error'); return; }
    const model = localStorage.getItem('mobidik_gemini_model') || '';
    if (!confirm(`${raws.length} kaydı AI ile zenginleştir?\nModel: ${model || 'server varsayılanı'}\nBu API kotası harcar; istediğin an "Durdur" diyebilirsin.`)) return;
    batchStop = false; batchBtn.dataset.running = '1';
    let done = 0, ok = 0, err = 0;
    for (const r of raws) {
      if (batchStop) break;
      batchBtn.textContent = `Durdur (${done + 1}/${raws.length})`;
      try {
        const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}/enrich`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(model ? { model } : {}),
        });
        const d = await res.json();
        d.ok ? ok++ : err++;
      } catch (e) { err++; }
      done++;
    }
    batchBtn.dataset.running = '0'; batchBtn.textContent = 'AI Toplu';
    toast(`Toplu bitti: ${ok} ok · ${err} hata${batchStop ? ' (durduruldu)' : ''}`, err ? 'error' : 'success');
    renderListFromAPI();   // sonuçlar listeye yansısın (kabul için kartları aç)
  });

  // ============================================================
  // Çoklu seçim modu + sıralı toplu "Ürüne Çevir" kuyruğu
  // ============================================================
  function arUpdateSelCount() {
    const num = document.getElementById('ar-sel-count-num');
    if (num) num.textContent = String(arSelectedIds.size);
    const conv = document.getElementById('ar-sel-convert');
    if (conv && conv.dataset.running !== '1') {
      conv.innerHTML = '<svg class="icon"><use href="#ic-factory"/></svg> Ürüne Çevir'
        + (arSelectedIds.size ? ` (${arSelectedIds.size})` : '');
    }
  }
  function arSetSelectMode(on) {
    arSelectMode = on;
    document.body.classList.toggle('ar-select-on', on);
    const btn = document.getElementById('btn-select-mode'); if (btn) btn.classList.toggle('is-active', on);
    const bar = document.getElementById('ar-select-actionbar'); if (bar) bar.hidden = !on;
    if (!on) {
      arSelectedIds.clear();
      document.querySelectorAll('.ar-item.is-selected').forEach(el => el.classList.remove('is-selected'));
    }
    arUpdateSelCount();
  }
  const selModeBtn = $('#btn-select-mode');
  if (selModeBtn) selModeBtn.addEventListener('click', () => arSetSelectMode(!arSelectMode));
  const selCancelBtn = $('#ar-sel-cancel');
  if (selCancelBtn) selCancelBtn.addEventListener('click', () => arSetSelectMode(false));
  // "Tamamlandı'ları Seç": görünür/gizli tüm done kayıtları seç (kapalı accordion dahil)
  const selDoneBtn = $('#ar-sel-select-done');
  if (selDoneBtn) selDoneBtn.addEventListener('click', () => {
    if (!arSelectMode) arSetSelectMode(true);
    (lastRows || []).filter(r => researchCompletion(r).done).forEach(r => arSelectedIds.add(r.id));
    $$('.ar-item').forEach(el => { if (arSelectedIds.has(el.dataset.id)) el.classList.add('is-selected'); });
    arUpdateSelCount();
    if (!arSelectedIds.size) toast('Tamamlandı (AI + foto) kayıt yok', 'error');
  });
  // Sıralı toplu çevir (batch-enrich deseni): seçili Tamamlandı kayıtları tek tek /to-product
  const selConvertBtn = $('#ar-sel-convert');
  if (selConvertBtn) selConvertBtn.addEventListener('click', async () => {
    if (selConvertBtn.dataset.running === '1') { batchConvertStop = true; selConvertBtn.textContent = 'Durduruluyor…'; return; }
    const targets = (lastRows || []).filter(r => arSelectedIds.has(r.id) && researchCompletion(r).done);
    const skipped = arSelectedIds.size - targets.length;   // seçili ama tamamlanmamış
    if (!targets.length) {
      toast('Çevrilecek Tamamlandı kayıt seçili değil' + (skipped ? ` (${skipped} kayıt tamamlanmadığı için hariç)` : ''), 'error');
      return;
    }
    if (!confirm(`${targets.length} kaydı sırayla ürüne çevir + galeriye gönder?`
      + (skipped ? `\n(${skipped} tamamlanmamış kayıt atlanacak.)` : '')
      + `\nİstediğin an "Durdur" diyebilirsin.`)) return;
    batchConvertStop = false; selConvertBtn.dataset.running = '1';
    let ok = 0, err = 0, k = 0;
    for (const r of targets) {
      if (batchConvertStop) break;
      k++; selConvertBtn.innerHTML = `Durdur (${k}/${targets.length})`;
      try {
        const res = await fetch(`/api/arastirma/${encodeURIComponent(r.id)}/to-product`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
        });
        const d = await res.json();
        d.ok ? ok++ : err++;
      } catch (e) { err++; }
    }
    selConvertBtn.dataset.running = '0';
    const parts = [`${ok} ürün oluşturuldu`];
    if (err) parts.push(`${err} hata/eksik`);
    if (skipped) parts.push(`${skipped} tamamlanmamış atlandı`);
    if (batchConvertStop) parts.push('durduruldu');
    toast(parts.join(' · '), err ? 'error' : 'success', 6000);
    arSetSelectMode(false);
    renderListFromAPI();   // çevrilenler 'imported' → pending'den düşer; accordion korunur
  });

  // Initial render
  lastRows = initialRows;   // sort/diğer fetch'siz re-render'lar boş listeyi render etmesin
  renderList(initialRows);
  populateCountryFilter(initialRows);
})();
