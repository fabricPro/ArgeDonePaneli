/* Galeri not hover-kartı — ürün kartına çıpalı küçük popover.
   Masaüstü: kart hover (gecikmeli). Dokunmatik/kalem: .nh-trigger göstergesine dokun.
   Yalnız data-has-notlar="true" kartlar. .studio self-scope. */
(function () {
  'use strict';
  if (!document.querySelector('.product-card[data-urunid]')) return;
  var HOVER_DELAY = 300, HIDE_GRACE = 160;
  var cache = {}, pending = null, openUid = null;
  var root = null, cardEl = null, anchorEl = null, showTimer = null, hideTimer = null;
  var coarse = window.matchMedia ? window.matchMedia('(hover: none), (pointer: coarse)') : { matches: false };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function clean(html) {
    if (!html) return '';
    return String(html)
      .replace(/<\s*(script|iframe|object|embed|style)[\s\S]*?<\s*\/\s*\1\s*>/gi, '')
      .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
      .replace(/(href|src)\s*=\s*("javascript:[^"]*"|'javascript:[^']*')/gi, "$1=''");
  }
  function svgUse(id) { var sprite = ''; var u = document.querySelector('svg use[href]'); if (u) { sprite = (u.getAttribute('href') || '').split('#')[0]; } return '<svg class="icon" aria-hidden="true"><use href="' + sprite + '#' + id + '"/></svg>'; }
  function build() {
    root = document.createElement('div'); root.className = 'studio nh-root'; root.setAttribute('role', 'presentation');
    cardEl = document.createElement('div'); cardEl.className = 'nh-card';
    cardEl.setAttribute('role', 'dialog'); cardEl.setAttribute('aria-modal', 'false'); cardEl.setAttribute('aria-label', 'Ürün notları'); cardEl.setAttribute('tabindex', '-1');
    root.appendChild(cardEl);
    cardEl.addEventListener('mouseenter', function () { if (!coarse.matches) clearTimeout(hideTimer); });
    cardEl.addEventListener('mouseleave', function () { if (!coarse.matches) scheduleHide(); });
    cardEl.addEventListener('click', function (e) { if (e.target.closest('.nh-x')) { e.preventDefault(); e.stopPropagation(); hideNow(); } });
    document.body.appendChild(root);
  }
  function reposition() {
    if (!cardEl || !anchorEl) return;
    var GAP = 8, M = 8, r = anchorEl.getBoundingClientRect(), vw = window.innerWidth, vh = window.innerHeight, pw = cardEl.offsetWidth, ph = cardEl.offsetHeight;
    var left = r.left; if (left + pw > vw - M) left = vw - M - pw; if (left < M) left = M;
    var below = vh - r.bottom - GAP, top; if (ph <= below || below >= r.top - GAP) top = r.bottom + GAP; else top = Math.max(M, r.top - GAP - ph);
    cardEl.style.left = Math.round(left) + 'px'; cardEl.style.top = Math.round(top) + 'px';
  }
  function render(uid, html) {
    if (!cardEl) build();
    var sel = (window.CSS && CSS.escape) ? CSS.escape(uid) : uid;
    var card = document.querySelector('.product-card[data-urunid="' + sel + '"]');
    var name = (card && card.getAttribute('data-name-label')) || 'Not';
    var body = clean(html);
    cardEl.innerHTML = '<div class="nh-head"><span class="nh-title">' + svgUse('ic-pencil') + '<span class="nh-name">' + esc(name) + '</span></span>' +
      '<button type="button" class="nh-x" aria-label="Kapat">' + svgUse('ic-x') + '</button></div>' +
      '<div class="nh-body">' + (body && body.trim() ? body : '<p class="nh-empty">Bu ürün için not girilmemiş.</p>') + '</div>';
    reposition();
  }
  function fetchNotes(uid) {
    if (Object.prototype.hasOwnProperty.call(cache, uid)) return Promise.resolve(cache[uid]);
    if (pending && pending.uid !== uid && pending.ctrl) { try { pending.ctrl.abort(); } catch (e) {} }
    var ctrl = (typeof AbortController !== 'undefined') ? new AbortController() : null; pending = { uid: uid, ctrl: ctrl };
    return fetch('/api/urun/' + encodeURIComponent(uid) + '/notlar', { headers: { 'Accept': 'application/json' }, signal: ctrl ? ctrl.signal : undefined })
      .then(function (r) { return r.json(); }).then(function (d) { var html = (d && d.ok) ? (d.html || '') : ''; cache[uid] = html; if (pending && pending.uid === uid) pending = null; return html; })
      .catch(function () { return ''; });
  }
  function show(anchor, card) { var uid = card.getAttribute('data-urunid'); if (!uid) return; anchorEl = anchor; openUid = uid; clearTimeout(hideTimer);
    fetchNotes(uid).then(function (html) { if (openUid !== uid) return; render(uid, html); }); }
  function scheduleHide() { clearTimeout(hideTimer); hideTimer = setTimeout(hideNow, HIDE_GRACE); }
  function hideNow() { clearTimeout(showTimer); clearTimeout(hideTimer); openUid = null; anchorEl = null; if (root && root.parentNode) root.parentNode.removeChild(root); root = null; cardEl = null; }
  function openUidCard() { if (!openUid) return null; var sel = (window.CSS && CSS.escape) ? CSS.escape(openUid) : openUid; return document.querySelector('.product-card[data-urunid="' + sel + '"]'); }
  document.addEventListener('mouseover', function (e) {
    if (coarse.matches) return;
    var card = e.target.closest('.product-card[data-urunid]');
    if (!card || card.getAttribute('data-has-notlar') !== 'true') return;
    if (document.body.classList.contains('select-on') || document.body.classList.contains('design-on')) return;
    if (card === openUidCard()) return;
    clearTimeout(showTimer); clearTimeout(hideTimer); showTimer = setTimeout(function () { show(card, card); }, HOVER_DELAY);
  });
  document.addEventListener('mouseout', function (e) {
    if (coarse.matches) return;
    var card = e.target.closest('.product-card[data-urunid]'); if (!card) return;
    var to = e.relatedTarget; if (to && (to.closest('.product-card[data-urunid]') === card || (root && root.contains(to)))) return;
    clearTimeout(showTimer); scheduleHide();
  });
  document.addEventListener('click', function (e) {
    var trig = e.target.closest('.card-indicators .ind.nh-trigger'); if (!trig) return; if (!coarse.matches) return;
    var card = trig.closest('.product-card[data-urunid]'); if (!card) return;
    e.preventDefault(); e.stopPropagation();
    if (openUid === card.getAttribute('data-urunid')) { hideNow(); return; } show(trig, card);
  }, true);
  document.addEventListener('click', function (e) { if (!openUid) return; if (root && root.contains(e.target)) return; if (e.target.closest('.card-indicators .ind.nh-trigger')) return; hideNow(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && openUid) hideNow(); });
  window.addEventListener('scroll', function () { if (openUid) reposition(); }, true);
  window.addEventListener('resize', function () { if (openUid) reposition(); });
  window.NoteHoverCard = { invalidate: function (uid, html) { if (uid == null) return; if (typeof html === 'string') cache[uid] = html; else delete cache[uid]; } };
})();
