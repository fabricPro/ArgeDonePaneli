/* Uygulama geneli sağ-tık (context) menüsü — tek global örnek, .studio self-scope.
   Idiom: note-hovercard.js / folder-picker.js (IIFE, document.body'ye tek kök,
   svgUse/esc yardımcıları, viewport flip/clamp, Esc/dış-tık/scroll kapanma,
   coarse-pointer için long-press). window.toast + tasarım token'ları kullanır.

   Genel API (window.ContextMenu):
     open({ x, y, items, anchorEl })   — koordinatta menü aç
     register(selector, itemsFn)       — seçici kaydet; sağ-tıkta itemsFn(el, ev) → items
     close()
     openInNewTab(url) / copyLink(url) — hazır item fabrikaları
   items: [{ label, icon, danger, disabled, onSelect }, '---' (ayraç), ...]
   itemsFn null/[] döndürürse native menü gösterilir (karışılmaz). */
(function () {
  'use strict';

  var M = 8;                       // viewport kenar payı
  var LONGPRESS_MS = 550;          // dokunmatik uzun-bas eşiği
  var MOVE_CANCEL = 10;            // uzun-bas iptal hareket eşiği (px)
  var registrations = [];          // { selector, fn }
  var root = null, menuEl = null;  // açık menü DOM'u
  var coarse = window.matchMedia ? window.matchMedia('(hover: none), (pointer: coarse)') : { matches: false };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function svgUse(id) {
    var sprite = '';
    var u = document.querySelector('svg use[href]');
    if (u) sprite = (u.getAttribute('href') || '').split('#')[0];
    return '<svg class="icon" aria-hidden="true"><use href="' + sprite + '#' + id + '"/></svg>';
  }
  function notify(msg, kind) {
    if (window.toast) { try { window.toast(msg, kind || 'success'); return; } catch (e) {} }
  }

  // ---- Hazır item fabrikaları ----
  function openInNewTab(url, label) {
    return { label: label || 'Yeni sekmede aç', icon: 'ic-external-link',
      onSelect: function () { window.open(url, '_blank', 'noopener'); } };
  }
  function copyLink(url, label) {
    return { label: label || 'Bağlantıyı kopyala', icon: 'ic-clipboard', onSelect: function () {
      var abs = url;
      try { abs = new URL(url, window.location.origin).href; } catch (e) {}
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(abs).then(function () { notify('Bağlantı kopyalandı'); })
          .catch(function () { legacyCopy(abs); });
      } else { legacyCopy(abs); }
    } };
  }
  function legacyCopy(text) {
    try {
      var ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.focus(); ta.select();
      var ok = document.execCommand('copy');
      document.body.removeChild(ta);
      notify(ok ? 'Bağlantı kopyalandı' : 'Kopyalanamadı', ok ? 'success' : 'error');
    } catch (e) { notify('Kopyalanamadı', 'error'); }
  }

  // ---- Menü DOM ----
  function close() {
    if (root && root.parentNode) root.parentNode.removeChild(root);
    root = null; menuEl = null;
  }
  function buildMenu(items) {
    root = document.createElement('div');
    root.className = 'studio ctx-root';
    root.setAttribute('role', 'presentation');
    menuEl = document.createElement('div');
    menuEl.className = 'ctx-menu';
    menuEl.setAttribute('role', 'menu');
    menuEl.setAttribute('tabindex', '-1');

    items.forEach(function (it) {
      if (it === '---') {
        var sep = document.createElement('div');
        sep.className = 'ctx-sep'; sep.setAttribute('role', 'separator');
        menuEl.appendChild(sep);
        return;
      }
      var row = document.createElement('button');
      row.type = 'button';
      row.className = 'ctx-item' + (it.danger ? ' is-danger' : '');
      row.setAttribute('role', 'menuitem');
      if (it.disabled) { row.setAttribute('aria-disabled', 'true'); row.disabled = true; }
      row.innerHTML = (it.icon ? svgUse(it.icon) : '<span class="icon" aria-hidden="true"></span>') +
        '<span class="ctx-label">' + esc(it.label) + '</span>';
      if (!it.disabled) {
        row.addEventListener('click', function (e) {
          e.preventDefault(); e.stopPropagation();
          close();
          try { if (typeof it.onSelect === 'function') it.onSelect(); } catch (err) {}
        });
      }
      menuEl.appendChild(row);
    });

    root.appendChild(menuEl);
    document.body.appendChild(root);
  }
  function position(x, y) {
    var vw = window.innerWidth, vh = window.innerHeight;
    var pw = menuEl.offsetWidth, ph = menuEl.offsetHeight;
    var left = x, top = y;
    if (left + pw > vw - M) left = Math.max(M, vw - M - pw);   // sağ kenarda sola çevir
    if (top + ph > vh - M) top = Math.max(M, vh - M - ph);     // alt kenarda yukarı çevir
    if (left < M) left = M;
    if (top < M) top = M;
    menuEl.style.left = Math.round(left) + 'px';
    menuEl.style.top = Math.round(top) + 'px';
  }
  function focusItem(idx) {
    var rows = menuEl.querySelectorAll('.ctx-item:not([aria-disabled="true"])');
    if (!rows.length) return;
    var i = ((idx % rows.length) + rows.length) % rows.length;
    rows.forEach(function (r) { r.removeAttribute('data-active'); });
    rows[i].setAttribute('data-active', '');
    rows[i].focus();
  }
  function activeIndex() {
    var rows = [].slice.call(menuEl.querySelectorAll('.ctx-item:not([aria-disabled="true"])'));
    return rows.indexOf(document.activeElement);
  }

  function open(opts) {
    var items = (opts && opts.items) || [];
    items = items.filter(function (it, i, arr) {
      // baştaki/sondaki/çift ayraçları temizle
      if (it !== '---') return true;
      return i > 0 && i < arr.length - 1 && arr[i - 1] !== '---';
    });
    if (!items.length) return;
    close();
    buildMenu(items);
    position(opts.x || 0, opts.y || 0);
    // açılışta ilk satıra odak
    requestAnimationFrame(function () { if (menuEl) focusItem(0); });
  }

  // ---- Kayıt eşleşmesi ----
  function resolveItems(target, ev) {
    // 1) Programatik kayıtlar (son kaydedilen önce — daha özel entegrasyonlar üstte)
    for (var i = registrations.length - 1; i >= 0; i--) {
      var reg = registrations[i];
      var el = target.closest(reg.selector);
      if (el) {
        var items = null;
        try { items = reg.fn(el, ev); } catch (e) { items = null; }
        if (items && items.length) return items;
      }
    }
    // 2) Declarative data-ctx-menu="product" + data-ctx-urunid
    var d = target.closest('[data-ctx-menu]');
    if (d && d.getAttribute('data-ctx-menu') === 'product') {
      var id = d.getAttribute('data-ctx-urunid');
      if (id) {
        var url = '/urun/' + encodeURIComponent(id);
        return [openInNewTab(url), copyLink(url)];
      }
    }
    return null;
  }

  function shouldSkip(target) {
    // Form alanları + açık opt-out: native menü korunur
    return !!(target.closest('input, textarea, [contenteditable="true"], select, [data-ctx-native]'));
  }
  function inBlockingMode() {
    return document.body.classList.contains('select-on') || document.body.classList.contains('design-on');
  }

  // ---- Sağ-tık (contextmenu) ----
  document.addEventListener('contextmenu', function (ev) {
    if (ev.defaultPrevented) return;             // örn. tarak-ui.js kendi menüsünü işler
    if (shouldSkip(ev.target)) { close(); return; }
    var items = resolveItems(ev.target, ev);
    if (!items) return;                          // eşleşme yok → native menü
    ev.preventDefault();
    open({ x: ev.clientX, y: ev.clientY, items: items });
  }, true);

  // ---- Dokunmatik: uzun-bas ----
  (function () {
    if (!coarse.matches) return;
    var lpTimer = null, sx = 0, sy = 0, lpTarget = null, fired = false;
    function clear() { if (lpTimer) { clearTimeout(lpTimer); lpTimer = null; } lpTarget = null; }
    document.addEventListener('pointerdown', function (ev) {
      if (ev.pointerType === 'mouse') return;
      if (inBlockingMode()) return;              // sürükle/seç modlarında karışma
      if (shouldSkip(ev.target)) return;
      lpTarget = ev.target; sx = ev.clientX; sy = ev.clientY; fired = false;
      clearTimeout(lpTimer);
      lpTimer = setTimeout(function () {
        var items = resolveItems(lpTarget, ev);
        if (!items) return;
        fired = true;
        open({ x: sx, y: sy, items: items });
      }, LONGPRESS_MS);
    }, true);
    document.addEventListener('pointermove', function (ev) {
      if (!lpTimer) return;
      if (Math.abs(ev.clientX - sx) > MOVE_CANCEL || Math.abs(ev.clientY - sy) > MOVE_CANCEL) clear();
    }, true);
    document.addEventListener('pointerup', clear, true);
    document.addEventListener('pointercancel', clear, true);
    // Uzun-bas sonrası gelen click'i bir kez bastır (navigasyon tetiklenmesin)
    document.addEventListener('click', function (ev) {
      if (fired) { fired = false; ev.preventDefault(); ev.stopPropagation(); }
    }, true);
  })();

  // ---- Kapanma & klavye ----
  document.addEventListener('mousedown', function (e) {
    if (!menuEl) return;
    if (root && root.contains(e.target)) return;
    close();
  }, true);
  document.addEventListener('keydown', function (e) {
    if (!menuEl) return;
    if (e.key === 'Escape') { e.preventDefault(); close(); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); focusItem(activeIndex() + 1); return; }
    if (e.key === 'ArrowUp') { e.preventDefault(); focusItem(activeIndex() - 1); return; }
    if (e.key === 'Enter' || e.key === ' ') {
      if (document.activeElement && document.activeElement.classList.contains('ctx-item')) {
        e.preventDefault(); document.activeElement.click();
      }
    }
  });
  window.addEventListener('scroll', function () { if (menuEl) close(); }, true);
  window.addEventListener('resize', function () { if (menuEl) close(); });

  window.ContextMenu = {
    open: open,
    close: close,
    register: function (selector, fn) { if (selector && typeof fn === 'function') registrations.push({ selector: selector, fn: fn }); },
    openInNewTab: openInNewTab,
    copyLink: copyLink
  };
})();
