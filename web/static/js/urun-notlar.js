/* Ürün-seviyesi serbest Notlar editörü (yeni "Notlar" ana sekmesi).
   notlar.js (sürüm-spesifik Teknik>Notlar) ile AYRI ve bağımsızdır.
   Daima /api/urun/<id>/notlar'a yazar. Kendi id'leri: #urun-notlar-*. */
(function () {
  "use strict";
  const URUN_ID = window.URUN_ID; if (!URUN_ID) return;
  const editor = document.getElementById("urun-notlar-content");
  const toolbar = document.getElementById("urun-notlar-toolbar");
  const saveBtn = document.getElementById("urun-notlar-save-btn");
  const statusEl = document.getElementById("urun-notlar-status");
  const fontSizeSel = document.getElementById("urun-notlar-fontsize");
  if (!editor || !toolbar) return;
  const SAVE_URL = `/api/urun/${encodeURIComponent(URUN_ID)}/notlar`;
  try { document.execCommand("defaultParagraphSeparator", false, "p"); document.execCommand("styleWithCSS", false, true); } catch (e) {}
  let lastSaved = editor.innerHTML, saveTimer = null, saving = false;
  function setStatus(t, k) { if (statusEl) { statusEl.textContent = t; statusEl.dataset.kind = k || ""; } }
  function markDirty() { setStatus("Değişti…", "dirty"); clearTimeout(saveTimer); saveTimer = setTimeout(save, 1500); }
  async function save() {
    if (saving) return;
    const html = editor.innerHTML;
    if (html === lastSaved) { setStatus("Kaydedildi", "ok"); return; }
    saving = true; setStatus("Kaydediliyor…", "saving");
    try {
      const res = await fetch(SAVE_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ html }) });
      const data = await res.json();
      if (data.ok) {
        lastSaved = data.html;
        if (data.html !== html) editor.innerHTML = data.html;
        try { if (window.NoteHoverCard && window.NoteHoverCard.invalidate) window.NoteHoverCard.invalidate(URUN_ID, data.html); } catch (e) {}
        setStatus("Kaydedildi ✓", "ok");
      } else { setStatus("Hata: " + (data.error || "?"), "error"); if (window.toast) window.toast(data.error || "Kayıt hatası", "error"); }
    } catch (e) { setStatus("Bağlantı hatası", "error"); } finally { saving = false; }
  }
  toolbar.addEventListener("mousedown", (e) => { if (e.target.closest("button, .rich-colors")) e.preventDefault(); });
  toolbar.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-cmd]"), colorBtn = e.target.closest("[data-color]");
    if (btn) { e.preventDefault(); document.execCommand(btn.dataset.cmd, false, null); editor.focus(); markDirty(); }
    else if (colorBtn) { e.preventDefault(); document.execCommand("foreColor", false, colorBtn.dataset.color); editor.focus(); markDirty(); }
  });
  if (fontSizeSel) fontSizeSel.addEventListener("change", (e) => { document.execCommand("fontSize", false, e.target.value); editor.focus(); markDirty(); });
  editor.addEventListener("input", markDirty);
  editor.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); clearTimeout(saveTimer); save(); } });
  if (saveBtn) saveBtn.addEventListener("click", () => { clearTimeout(saveTimer); save(); });
  window.addEventListener("beforeunload", () => {
    if (editor.innerHTML !== lastSaved) { try { navigator.sendBeacon(SAVE_URL, new Blob([JSON.stringify({ html: editor.innerHTML })], { type: "application/json" })); } catch (e) {} }
  });
})();
