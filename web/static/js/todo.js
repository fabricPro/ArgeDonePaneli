/**
 * Faz 2 — Ürün To-Do sekmesi: ürün-bazlı adım listesi (checklist).
 *
 * IIFE; URUN_ID + #todo-data'dan beslenir. Her değişiklikte 1500ms debounce auto-save
 * → POST /api/urun/<id>/todo (tüm liste; client durumu otorite). notlar.js ile aynı
 * kayıt ritmi + durum dili ("Kaydedildi ✓ / Değişti… / Hata").
 *
 * Davranış: adım ekle (form), tamamla (check), metni tıkla→satır-içi düzenle (boş→sil),
 * sil (çöp). İlerleme X/Y hem sekme başlığında hem sekme etiketinde.
 */
(function () {
    "use strict";

    const URUN_ID = window.URUN_ID;
    if (!URUN_ID) return;

    const listEl = document.getElementById("todo-list");
    const emptyEl = document.getElementById("todo-empty");
    const form = document.getElementById("todo-add");
    const input = document.getElementById("todo-input");
    const statusEl = document.getElementById("todo-status");
    const progressEl = document.getElementById("todo-progress");
    const tabCountEl = document.getElementById("todo-tab-count");
    if (!listEl || !form || !input) return;

    function toast(msg, type) { if (window.toast) window.toast(msg, type || "info"); }

    // --- State (sıraya göre) ---
    let items = [];
    try {
        const raw = JSON.parse(document.getElementById("todo-data")?.textContent || "[]");
        if (Array.isArray(raw)) {
            items = raw.map((t, i) => ({
                id: String(t.id || ("t" + i)),
                text: String(t.text || ""),
                done: !!t.done,
                order: typeof t.order === "number" ? t.order : i,
            })).sort((a, b) => a.order - b.order);
        }
    } catch (e) { items = []; }

    let saveTimer = null;
    let saving = false;

    function serialize() {
        return items.map((t, i) => ({ id: t.id, text: t.text, done: t.done, order: i }));
    }
    let lastSavedJson = JSON.stringify(serialize());

    function setStatus(text, kind) {
        if (!statusEl) return;
        statusEl.textContent = text;
        statusEl.dataset.kind = kind || "";
    }
    function newId() {
        return "t" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    }
    function escapeHtml(s) {
        return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        }[c]));
    }

    function updateProgress() {
        const total = items.length;
        const done = items.filter(t => t.done).length;
        const txt = `${done}/${total}`;
        const complete = total > 0 && done === total;
        [progressEl, tabCountEl].forEach(el => {
            if (!el) return;
            if (total) { el.hidden = false; el.textContent = txt; el.classList.toggle("is-complete", complete); }
            else el.hidden = true;
        });
    }

    function render() {
        listEl.innerHTML = "";
        items.forEach(t => {
            const li = document.createElement("li");
            li.className = "todo-item" + (t.done ? " is-done" : "");
            li.dataset.id = t.id;
            li.innerHTML =
                `<button type="button" class="todo-check" title="Tamamlandı" aria-pressed="${t.done}"><svg class="icon"><use href="#ic-check"/></svg></button>` +
                `<span class="todo-text" contenteditable="true" role="textbox" spellcheck="false">${escapeHtml(t.text)}</span>` +
                `<button type="button" class="todo-del" title="Sil" aria-label="Sil"><svg class="icon"><use href="#ic-trash"/></svg></button>`;
            listEl.appendChild(li);
        });
        if (emptyEl) emptyEl.hidden = items.length > 0;
        updateProgress();
    }

    function scheduleSave() {
        setStatus("Değişti…", "dirty");
        clearTimeout(saveTimer);
        saveTimer = setTimeout(save, 1500);
    }

    async function save() {
        if (saving) return;
        const payload = serialize();
        const json = JSON.stringify(payload);
        if (json === lastSavedJson) { setStatus("Kaydedildi", "ok"); return; }
        saving = true;
        setStatus("Kaydediliyor…", "saving");
        try {
            const res = await fetch(`/api/urun/${URUN_ID}/todo`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ todo: payload }),
            });
            const data = await res.json();
            if (data.ok) {
                lastSavedJson = JSON.stringify(data.todo || payload);
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

    // --- Adım ekle ---
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = (input.value || "").trim();
        if (!text) return;
        items.push({ id: newId(), text, done: false, order: items.length });
        input.value = "";
        render();
        scheduleSave();
    });

    // --- Tamamla / Sil (delegation) ---
    listEl.addEventListener("click", (e) => {
        const li = e.target.closest(".todo-item");
        if (!li) return;
        const t = items.find(x => x.id === li.dataset.id);
        if (!t) return;
        if (e.target.closest(".todo-check")) {
            t.done = !t.done;
            li.classList.toggle("is-done", t.done);
            const cb = li.querySelector(".todo-check");
            if (cb) cb.setAttribute("aria-pressed", String(t.done));
            updateProgress();
            scheduleSave();
        } else if (e.target.closest(".todo-del")) {
            items = items.filter(x => x.id !== t.id);
            render();
            scheduleSave();
        }
    });

    // --- Satır-içi metin düzenleme: Enter commit, boş→sil ---
    listEl.addEventListener("keydown", (e) => {
        const el = e.target;
        if (el.classList && el.classList.contains("todo-text") && e.key === "Enter") {
            e.preventDefault();
            el.blur();
        }
    });
    listEl.addEventListener("blur", (e) => {
        const el = e.target;
        if (!el.classList || !el.classList.contains("todo-text")) return;
        const li = el.closest(".todo-item");
        const t = li ? items.find(x => x.id === li.dataset.id) : null;
        if (!t) return;
        const newText = (el.textContent || "").trim();
        if (!newText) {
            items = items.filter(x => x.id !== t.id);
            render();
            scheduleSave();
            return;
        }
        if (newText !== t.text) {
            t.text = newText;
            scheduleSave();
        }
    }, true);   // capture: blur kabarcıklanmaz

    // --- Sayfa kapanırken son fırsat save ---
    window.addEventListener("beforeunload", () => {
        if (JSON.stringify(serialize()) !== lastSavedJson) {
            try {
                const blob = new Blob([JSON.stringify({ todo: serialize() })], { type: "application/json" });
                navigator.sendBeacon(`/api/urun/${URUN_ID}/todo`, blob);
            } catch (e) { /* ignore */ }
        }
    });

    // İlk render
    render();
    setStatus("Kaydedildi", "ok");
})();
