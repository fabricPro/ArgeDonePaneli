/**
 * v4.0-part-2 Adım 7 — Notlar sekmesi: Rich-text editor (contentEditable + execCommand).
 *
 * IIFE; URUN_ID global'inden ürün ID'sini alır.
 * Toolbar: bold/italic/underline + font-size select + 5 renk swatch + liste + format temizle.
 * Auto-save 3s debounce + manuel "Kaydet" butonu + Ctrl+S klavye kısayolu.
 * Server-side bleach.clean ile sanitize → response.html ile DOM güncellenir.
 */
(function () {
    "use strict";

    const URUN_ID = window.URUN_ID;
    if (!URUN_ID) return;

    const editor = document.getElementById("rich-content");
    const toolbar = document.getElementById("rich-toolbar");
    const saveBtn = document.getElementById("notlar-save-btn");
    const statusEl = document.getElementById("notlar-status");
    const fontSizeSel = document.getElementById("rich-fontsize");
    if (!editor || !toolbar) return;

    function toast(msg, type) {
        if (window.toast) window.toast(msg, type || "info");
    }

    // execCommand default paragraph separator (FF kompat)
    try {
        document.execCommand("defaultParagraphSeparator", false, "p");
        document.execCommand("styleWithCSS", false, true);
    } catch (e) { /* ignore */ }

    let lastSaved = editor.innerHTML;
    let saveTimer = null;
    let saving = false;

    function setStatus(text, kind) {
        if (!statusEl) return;
        statusEl.textContent = text;
        statusEl.dataset.kind = kind || "";
    }

    function markDirty() {
        setStatus("Değişti…", "dirty");
        clearTimeout(saveTimer);
        saveTimer = setTimeout(save, 3000);
    }

    // v4.0-part-2 Adım 8 — Aktif sürüme yaz (yoksa ürün-seviyesine fallback)
    function getSaveUrl() {
        const state = window.URUN_TEKNIK_STATE || {};
        const sid = state.activeSurumId;
        if (sid) return `/api/urun/${URUN_ID}/teknik/${encodeURIComponent(sid)}/notlar`;
        return `/api/urun/${URUN_ID}/notlar`;
    }

    async function save() {
        if (saving) return;
        const html = editor.innerHTML;
        if (html === lastSaved) {
            setStatus("Kaydedildi", "ok");
            return;
        }
        saving = true;
        setStatus("Kaydediliyor…", "saving");
        try {
            const res = await fetch(getSaveUrl(), {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({html: html}),
            });
            const data = await res.json();
            if (data.ok) {
                lastSaved = data.html;
                // İçerik sanitize edilmiş halini geri yansıt (XSS tag'leri temizlenmişse)
                // Ancak cursor pozisyonu kaybolur — kullanıcı yazımdaysa rahatsız edici.
                // Bu yüzden DOM'u sadece içerik gerçekten değişmişse güncelle.
                if (data.html !== html) {
                    editor.innerHTML = data.html;
                }
                // Fallback hint'i kaldır (artık sürüm-spesifik not var)
                const hint = document.querySelector('.notlar-fallback-hint');
                if (hint) hint.remove();
                setStatus("Kaydedildi ✓", "ok");
            } else {
                setStatus("Hata: " + (data.error || "?"), "error");
                toast(data.error || "Kayıt hatası", "error");
            }
        } catch (e) {
            setStatus("Bağlantı hatası", "error");
        } finally {
            saving = false;
        }
    }

    // v4.0-part-2 Adım 8 — Aktif sürüm değişince notları reload
    async function reloadFromActiveSurum() {
        const state = window.URUN_TEKNIK_STATE || {};
        const sid = state.activeSurumId;
        if (!sid) return;  // sürüm yoksa, mevcut content'i bırak
        // Kayıtlanmamış değişiklik varsa kullanıcıyı uyar
        const hasDirty = editor.innerHTML !== lastSaved;
        if (hasDirty) {
            if (!confirm("Mevcut sürümün notlarında kaydedilmemiş değişiklik var. Yeni sürüme geçince kaybolacak. Devam edilsin mi?")) {
                return;
            }
        }
        try {
            setStatus("Yükleniyor…", "saving");
            const res = await fetch(`/api/urun/${URUN_ID}/teknik/${encodeURIComponent(sid)}/notlar`);
            const data = await res.json();
            if (data.ok) {
                editor.innerHTML = data.html || "";
                lastSaved = editor.innerHTML;
                setStatus(data.fallback ? "Ürün-seviyesinden gösteriliyor" : "Kaydedildi", "ok");
            }
        } catch (e) {
            setStatus("Yüklenemedi", "error");
        }
    }
    // teknik.js bir sürüm değişikliği yayınladığında dinle
    document.addEventListener('teknik-surum-changed', reloadFromActiveSurum);

    // === Toolbar handlers ===
    toolbar.addEventListener("mousedown", (e) => {
        // Editor'dan focus kaçmasın
        if (e.target.closest("button, .rich-colors")) e.preventDefault();
    });

    toolbar.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-cmd]");
        const colorBtn = e.target.closest("[data-color]");
        if (btn) {
            e.preventDefault();
            const cmd = btn.dataset.cmd;
            document.execCommand(cmd, false, null);
            editor.focus();
            markDirty();
        } else if (colorBtn) {
            e.preventDefault();
            document.execCommand("foreColor", false, colorBtn.dataset.color);
            editor.focus();
            markDirty();
        }
    });

    if (fontSizeSel) {
        fontSizeSel.addEventListener("change", (e) => {
            document.execCommand("fontSize", false, e.target.value);
            editor.focus();
            markDirty();
        });
    }

    // === Editor input + klavye ===
    editor.addEventListener("input", markDirty);

    editor.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
            e.preventDefault();
            clearTimeout(saveTimer);
            save();
        }
    });

    // === Manuel Kaydet ===
    if (saveBtn) {
        saveBtn.addEventListener("click", () => {
            clearTimeout(saveTimer);
            save();
        });
    }

    // === Sayfa kapanırken son save ===
    window.addEventListener("beforeunload", () => {
        if (editor.innerHTML !== lastSaved) {
            // Senkron beacon ile son fırsat save
            try {
                const blob = new Blob(
                    [JSON.stringify({html: editor.innerHTML})],
                    {type: "application/json"}
                );
                navigator.sendBeacon(`/api/urun/${URUN_ID}/notlar`, blob);
            } catch (e) { /* ignore */ }
        }
    });
})();
