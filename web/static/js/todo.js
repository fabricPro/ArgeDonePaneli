/**
 * Faz 2 — Ürün To-Do paneli: durum + öncelik + sürüm bağı.
 *
 * IIFE; URUN_ID + #todo-data'dan beslenir. Her değişiklikte 1500ms debounce auto-save
 * → POST /api/urun/<id>/todo (tüm liste; client otorite). Cevap {ok, todo:[...]}.
 *
 * Item şekli: {id, text, durum, oncelik, surum_id, order}
 *   durum   : 'acik' | 'yapiliyor' | 'tamamlandi'   (hap tıkla → döngü)
 *   oncelik : null | 'dusuk' | 'orta' | 'yuksek'    (hap tıkla → döngü, null=yok)
 *   surum_id: null (ürün geneli) | sürüm id-string  (rozet sürüm adıyla)
 *
 * Liste ürünün TÜM görevlerini gösterir (geneli + her sürüm); sürüm değişince panel
 * yeniden sorgu YAPMAZ — hepsi zaten görünür, sürüme özel olanlar rozetli. Aktif sürüm
 * (yeni görevin "bu sürüme özel" hedefi) window.URUN_TEKNIK_STATE + 'teknik-surum-changed'
 * üzerinden takip edilir (notlar.js / plan.js ile aynı sözleşme).
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
    const scopeEl = document.getElementById("todo-scope");
    const scopeSurumBtn = document.getElementById("todo-scope-surum");
    if (!listEl || !form || !input) return;

    function toast(msg, type) { if (window.toast) window.toast(msg, type || "info"); }

    // --- Sabitler: durum / öncelik döngüsü + etiketler ---
    const DURUM_CYCLE = ["acik", "yapiliyor", "tamamlandi"];
    const DURUM_LABEL = { acik: "Açık", yapiliyor: "Yapılıyor", tamamlandi: "Tamamlandı" };
    const ONCELIK_CYCLE = ["", "dusuk", "orta", "yuksek"];  // "" = öncelik yok
    const ONCELIK_LABEL = { "": "Öncelik", dusuk: "Düşük", orta: "Orta", yuksek: "Yüksek" };

    // --- Sürüm adı haritası (#teknik-data'dan; surum_id → ad) ---
    const surumAd = {};
    try {
        const tk = JSON.parse(document.getElementById("teknik-data")?.textContent || "{}");
        (tk.surumler || []).forEach(s => { if (s && s.id) surumAd[s.id] = s.ad || s.id; });
    } catch (e) { /* yoksa boş harita */ }

    // --- Aktif sürüm takibi (yeni "bu sürüme özel" görevin hedefi) ---
    let activeSurumId = (window.URUN_TEKNIK_STATE || {}).activeSurumId || null;
    let scope = "genel";  // 'genel' = surum_id null | 'surum' = activeSurumId

    function normDurum(v) { return DURUM_CYCLE.indexOf(v) >= 0 ? v : "acik"; }
    function normOncelik(v) { return ["dusuk", "orta", "yuksek"].indexOf(v) >= 0 ? v : null; }

    // --- State ---
    let items = [];
    try {
        const raw = JSON.parse(document.getElementById("todo-data")?.textContent || "[]");
        if (Array.isArray(raw)) {
            items = raw.map((t, i) => ({
                id: String(t.id || ("t" + i)),
                text: String(t.text || ""),
                durum: normDurum(t.durum),
                oncelik: normOncelik(t.oncelik),
                surum_id: t.surum_id ? String(t.surum_id) : null,
                order: typeof t.order === "number" ? t.order : i,
            })).sort((a, b) => a.order - b.order);
        }
    } catch (e) { items = []; }

    let saveTimer = null;
    let saving = false;

    function serialize() {
        return items.map((t, i) => ({
            id: t.id, text: t.text, durum: t.durum,
            oncelik: t.oncelik, surum_id: t.surum_id, order: i,
        }));
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
        const done = items.filter(t => t.durum === "tamamlandi").length;
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
            li.className = "tek-todo-item" + (t.durum === "tamamlandi" ? " is-done" : "");
            li.dataset.id = t.id;
            const onc = t.oncelik || "";
            const surumHtml = t.surum_id
                ? `<span class="tek-todo-surum" title="${escapeHtml(surumAd[t.surum_id] || "Sürüm")} sürümüne özel"><svg class="icon"><use href="#ic-tag"/></svg><span>${escapeHtml(surumAd[t.surum_id] || "Sürüm")}</span></span>`
                : "";
            li.innerHTML =
                `<button type="button" class="tek-todo-status" data-durum="${t.durum}" title="Durumu değiştir">${DURUM_LABEL[t.durum]}</button>` +
                `<span class="tek-todo-text" contenteditable="true" role="textbox" spellcheck="false">${escapeHtml(t.text)}</span>` +
                `<span class="tek-todo-meta">` +
                    `<button type="button" class="tek-todo-prio" data-oncelik="${onc}" title="Öncelik değiştir"><span class="tek-todo-prio-dot"></span>${ONCELIK_LABEL[onc]}</button>` +
                    surumHtml +
                    `<button type="button" class="tek-todo-del" title="Sil" aria-label="Sil"><svg class="icon"><use href="#ic-trash"/></svg></button>` +
                `</span>`;
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

    // --- Kapsam toggle (ürün geneli / bu sürüme özel) ---
    function updateScopeAvailability() {
        if (!scopeSurumBtn) return;
        const ad = activeSurumId ? (surumAd[activeSurumId] || "seçili sürüm") : null;
        scopeSurumBtn.disabled = !activeSurumId;
        scopeSurumBtn.title = activeSurumId
            ? `${ad} sürümüne özel görev`
            : "Önce Teknik Analiz'de bir sürüm oluştur/seç";
        // Aktif sürüm yokken "bu sürüme özel" seçiliyse geneline düş
        if (!activeSurumId && scope === "surum") setScope("genel");
    }
    function setScope(next) {
        scope = next;
        if (scopeEl) {
            scopeEl.querySelectorAll(".tek-todo-scope-btn").forEach(b => {
                b.classList.toggle("is-active", b.dataset.scope === scope);
            });
        }
    }
    if (scopeEl) {
        scopeEl.addEventListener("click", (e) => {
            const btn = e.target.closest(".tek-todo-scope-btn");
            if (!btn || btn.disabled) return;
            setScope(btn.dataset.scope);
        });
    }

    // --- Görev ekle ---
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = (input.value || "").trim();
        if (!text) return;
        const surum_id = (scope === "surum" && activeSurumId) ? activeSurumId : null;
        items.push({ id: newId(), text, durum: "acik", oncelik: null, surum_id, order: items.length });
        input.value = "";
        render();
        scheduleSave();
    });

    // --- Durum / Öncelik döngüsü + Sil (delegation) ---
    listEl.addEventListener("click", (e) => {
        const li = e.target.closest(".tek-todo-item");
        if (!li) return;
        const t = items.find(x => x.id === li.dataset.id);
        if (!t) return;
        if (e.target.closest(".tek-todo-status")) {
            const i = DURUM_CYCLE.indexOf(t.durum);
            t.durum = DURUM_CYCLE[(i + 1) % DURUM_CYCLE.length];
            render();
            scheduleSave();
        } else if (e.target.closest(".tek-todo-prio")) {
            const cur = t.oncelik || "";
            const i = ONCELIK_CYCLE.indexOf(cur);
            const next = ONCELIK_CYCLE[(i + 1) % ONCELIK_CYCLE.length];
            t.oncelik = next || null;
            render();
            scheduleSave();
        } else if (e.target.closest(".tek-todo-del")) {
            items = items.filter(x => x.id !== t.id);
            render();
            scheduleSave();
        }
    });

    // --- Satır-içi başlık düzenleme: Enter commit, boş→sil ---
    listEl.addEventListener("keydown", (e) => {
        const el = e.target;
        if (el.classList && el.classList.contains("tek-todo-text") && e.key === "Enter") {
            e.preventDefault();
            el.blur();
        }
    });
    listEl.addEventListener("blur", (e) => {
        const el = e.target;
        if (!el.classList || !el.classList.contains("tek-todo-text")) return;
        const li = el.closest(".tek-todo-item");
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

    // --- Aktif sürüm değişimi (teknik.js yayar) ---
    document.addEventListener("teknik-surum-changed", (e) => {
        activeSurumId = (e && e.detail && e.detail.surum_id) ||
                        (window.URUN_TEKNIK_STATE || {}).activeSurumId || null;
        updateScopeAvailability();
    });

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
    updateScopeAvailability();
    render();
    setStatus("Kaydedildi", "ok");
})();
