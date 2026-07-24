/* Ayarlar → Depolama Bakımı — yetim/kullanılmayan dosya denetimi + temizlik.
   Salt-okunur denetim + kategori bazlı GC (dry-run özeti → confirm → uygula). */
(function () {
  'use strict';
  var auditBtn = document.getElementById('st-audit-btn');
  if (!auditBtn) return;

  var hintEl = document.getElementById('st-hint');
  var resultEl = document.getElementById('st-result');
  var summaryEl = document.getElementById('st-summary');
  var actionsEl = document.getElementById('st-actions');
  var bucketsEl = document.getElementById('st-buckets');
  var topEl = document.getElementById('st-top-list');

  var CAT_LABEL = {
    active: 'Aktif (kullanımda)',
    orphan: 'Yetim dosyalar (referanssız)',
    research_imported_inbox: 'Aktarılmış araştırma orijinalleri (_inbox)',
    research_dismissed_inbox: 'Reddedilen araştırma görselleri',
  };
  // Temizlenebilir kategoriler (butonlar bu sırayla)
  var GC_CATS = ['orphan', 'research_imported_inbox', 'research_dismissed_inbox'];

  function toast(msg, type) { if (window.toast) window.toast(msg, type || 'info'); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fmtSize(bytes) {
    bytes = Number(bytes) || 0;
    if (bytes >= 1024 * 1024 * 1024) return (bytes / 1073741824).toFixed(2) + ' GB';
    if (bytes >= 1024 * 1024) return (bytes / 1048576).toFixed(1) + ' MB';
    if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return bytes + ' B';
  }
  function postJSON(url, body) {
    return fetch(url, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    }).then(function (r) { return r.json(); });
  }

  // Kategori başına (tüm bucket'lar toplamı) sayı/boyut
  function aggregateByCategory(audit) {
    var agg = {};
    var buckets = audit.buckets || {};
    Object.keys(buckets).forEach(function (b) {
      var cats = buckets[b].categories || {};
      Object.keys(cats).forEach(function (c) {
        if (!agg[c]) agg[c] = { count: 0, bytes: 0 };
        agg[c].count += cats[c].count;
        agg[c].bytes += cats[c].bytes;
      });
    });
    return agg;
  }

  function render(audit) {
    var t = audit.totals || {};
    summaryEl.innerHTML =
      '<div class="st-stat"><span class="st-stat-n">' + (t.count || 0) + '</span><span class="st-stat-l">toplam dosya</span></div>' +
      '<div class="st-stat"><span class="st-stat-n">' + fmtSize(t.bytes) + '</span><span class="st-stat-l">toplam boyut</span></div>' +
      '<div class="st-stat st-stat-warn"><span class="st-stat-n">' + fmtSize(t.deletable_bytes) + '</span><span class="st-stat-l">' + (t.deletable_count || 0) + ' silinebilir</span></div>';

    // Kategori temizleme butonları
    var agg = aggregateByCategory(audit);
    actionsEl.innerHTML = '';
    GC_CATS.forEach(function (cat) {
      var a = agg[cat] || { count: 0, bytes: 0 };
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn st-clean-btn' + (cat === 'orphan' ? ' st-clean-safe' : '');
      btn.disabled = !a.count;
      btn.dataset.cat = cat;
      btn.innerHTML = '<strong>' + esc(CAT_LABEL[cat]) + '</strong>' +
        '<span class="st-clean-meta">' + a.count + ' dosya · ' + fmtSize(a.bytes) + '</span>';
      btn.addEventListener('click', function () { cleanup(cat); });
      actionsEl.appendChild(btn);
    });

    // Bucket dökümü
    var buckets = audit.buckets || {};
    var rows = '';
    Object.keys(buckets).forEach(function (b) {
      var bk = buckets[b];
      rows += '<tr class="st-brow"><td colspan="3"><strong>' + esc(b) + '</strong> — ' +
        bk.total.count + ' dosya · ' + fmtSize(bk.total.bytes) + '</td></tr>';
      var cats = bk.categories || {};
      Object.keys(cats).forEach(function (c) {
        rows += '<tr><td class="st-cat">' + esc(CAT_LABEL[c] || c) + '</td>' +
          '<td class="st-num">' + cats[c].count + '</td>' +
          '<td class="st-num">' + fmtSize(cats[c].bytes) + '</td></tr>';
      });
    });
    bucketsEl.innerHTML = '<table class="st-table"><thead><tr><th>Kategori</th><th>Dosya</th><th>Boyut</th></tr></thead><tbody>' + rows + '</tbody></table>';

    // En büyük silinebilir dosyalar
    var top = audit.top_objects || [];
    topEl.innerHTML = top.length
      ? '<ul class="st-top-ul">' + top.map(function (o) {
          return '<li><code>' + esc(o.bucket) + '/' + esc(o.path) + '</code> ' +
            '<span class="st-top-size">' + fmtSize(o.size) + '</span> ' +
            '<span class="st-top-cat">' + esc(CAT_LABEL[o.category] || o.category) + '</span></li>';
        }).join('') + '</ul>'
      : '<p class="st-hint">Silinebilir dosya yok.</p>';

    hintEl.hidden = true;
    resultEl.hidden = false;
  }

  function loadAudit() {
    auditBtn.disabled = true;
    hintEl.hidden = false;
    hintEl.textContent = 'Depolama taranıyor…';
    fetch('/api/storage/audit', { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) { toast(d.error || 'Denetim başarısız', 'error'); hintEl.textContent = 'Denetim başarısız.'; return; }
        render(d.audit);
      })
      .catch(function () { toast('Denetim başarısız', 'error'); hintEl.textContent = 'Denetim başarısız.'; })
      .then(function () { auditBtn.disabled = false; });
  }

  function cleanup(cat) {
    // 1) dry-run: ne silineceğini öğren
    postJSON('/api/storage/gc', { categories: [cat], confirm: false })
      .then(function (d) {
        if (!d.ok) { toast(d.error || 'Hata', 'error'); return; }
        var s = (d.result.summary && d.result.summary[cat]) || { count: 0, bytes: 0 };
        if (!s.count) { toast('Bu kategoride silinecek dosya yok', 'info'); return; }
        var ok = window.confirm(
          (CAT_LABEL[cat] || cat) + '\n\n' + s.count + ' dosya · ' + fmtSize(s.bytes) +
          ' KALICI olarak silinecek. Devam edilsin mi?');
        if (!ok) return;
        // 2) uygula
        postJSON('/api/storage/gc', { categories: [cat], confirm: true })
          .then(function (r) {
            if (!r.ok) { toast(r.error || 'Silme başarısız', 'error'); return; }
            toast(r.result.total_count + ' dosya silindi · ' + fmtSize(r.result.freed_bytes) + ' boşaldı', 'success');
            loadAudit();
          });
      })
      .catch(function () { toast('Hata', 'error'); });
  }

  auditBtn.addEventListener('click', loadAudit);
})();
