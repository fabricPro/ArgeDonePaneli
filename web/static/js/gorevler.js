/**
 * Faz 3 — Görevler panosu (ürün-gruplu).
 *
 * - Filtre/arama/tamamlandı-toggle tamamen client-side (yeniden sorgu yok).
 * - İzin verilen yazma: durum hapı döngüsü + "tamamla" check → POST /api/gorev/<id>/durum.
 *   (Oluşturma/düzenleme/silme YOK — onlar ürün To-Do panelinde.)
 * - Deep-link: ürün başlığı → /urun/<id>; görev satırı → /urun/<id>?tab=teknik&sub=todo[&surum=].
 */
(function () {
    "use strict";

    const groupsEl = document.getElementById("gor-groups");
    if (!groupsEl) return;

    const searchEl = document.getElementById("gor-search");
    const fDurum = document.getElementById("gor-f-durum");
    const fOncelik = document.getElementById("gor-f-oncelik");
    const fFolder = document.getElementById("gor-f-folder");
    const showDoneEl = document.getElementById("gor-show-done");
    const emptyEl = document.getElementById("gor-empty");
    const totalEl = document.getElementById("gor-total-open");

    const DURUM_CYCLE = ["acik", "yapiliyor", "tamamlandi"];
    const DURUM_LABEL = { acik: "Açık", yapiliyor: "Yapılıyor", tamamlandi: "Tamamlandı" };

    function toast(msg, type) { if (window.toast) window.toast(msg, type || "info"); }
    function lc(s) { return (s || "").toLowerCase(); }

    // ---- Filtreleme ----
    function applyFilters() {
        const q = lc(searchEl ? searchEl.value.trim() : "");
        const dDurum = fDurum ? fDurum.value : "";
        const dOnc = fOncelik ? fOncelik.value : "";
        const dFolder = fFolder ? fFolder.value : "";
        const showDone = !!(showDoneEl && showDoneEl.checked);

        let anyVisible = false;
        groupsEl.querySelectorAll(".gor-group").forEach(group => {
            const folders = (group.dataset.folders || "").split(",").filter(Boolean);
            const folderOk = !dFolder || folders.indexOf(dFolder) >= 0;
            const prodName = lc(group.querySelector(".gor-prod-name")?.textContent);
            let visibleCount = 0;

            group.querySelectorAll(".gor-task").forEach(task => {
                const durum = task.dataset.durum;
                const onc = task.dataset.oncelik || "";
                const text = lc(task.querySelector(".gor-task-text")?.textContent);

                let ok = folderOk;
                // durum: filtre seçiliyse ona eşit; değilse tamamlandı (showDone kapalıysa) gizli
                if (ok) {
                    if (dDurum) ok = durum === dDurum;
                    else ok = showDone || durum !== "tamamlandi";
                }
                // öncelik
                if (ok && dOnc) ok = (dOnc === "__none__") ? onc === "" : onc === dOnc;
                // arama (görev metni VEYA ürün adı)
                if (ok && q) ok = text.indexOf(q) >= 0 || prodName.indexOf(q) >= 0;

                task.hidden = !ok;
                if (ok) visibleCount++;
            });

            const groupVisible = folderOk && visibleCount > 0;
            group.hidden = !groupVisible;
            if (groupVisible) anyVisible = true;
        });

        if (emptyEl) emptyEl.hidden = anyVisible;
    }

    // ---- Sayaçlar (grup açık sayısı + hero + nav rozeti) ----
    function recomputeCounts() {
        let total = 0;
        groupsEl.querySelectorAll(".gor-group").forEach(group => {
            let open = 0;
            group.querySelectorAll(".gor-task").forEach(task => {
                if (task.dataset.durum !== "tamamlandi") open++;
            });
            total += open;
            const chip = group.querySelector(".gor-prod-count");
            if (chip) { chip.textContent = open + " açık"; chip.dataset.open = String(open); }
            group.dataset.open = String(open);
        });
        if (totalEl) totalEl.textContent = String(total);
        updateNavBadge(total);
    }

    function updateNavBadge(total) {
        const link = document.querySelector('.appbar-nav a[href$="/gorevler"]');
        if (!link) return;
        let badge = link.querySelector(".appbar-badge");
        if (total > 0) {
            if (!badge) {
                badge = document.createElement("span");
                badge.className = "appbar-badge";
                link.appendChild(badge);
            }
            badge.textContent = String(total);
        } else if (badge) {
            badge.remove();
        }
    }

    // ---- Durum yazımı (döngü + tamamla) ----
    async function writeDurum(task, durum) {
        const id = task.dataset.id;
        if (!id) return;
        const prev = task.dataset.durum;
        if (durum === prev) return;
        // iyimser güncelle
        setTaskDurum(task, durum);
        try {
            const res = await fetch(`/api/gorev/${id}/durum`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ durum }),
            });
            const data = await res.json();
            if (!data.ok) {
                setTaskDurum(task, prev);  // geri al
                toast(data.error || "Güncellenemedi", "error");
            }
        } catch (e) {
            setTaskDurum(task, prev);
            toast("Bağlantı hatası", "error");
        }
    }

    function setTaskDurum(task, durum) {
        task.dataset.durum = durum;
        const pill = task.querySelector(".tek-todo-status");
        if (pill) { pill.dataset.durum = durum; pill.textContent = DURUM_LABEL[durum]; }
        task.classList.toggle("is-done", durum === "tamamlandi");
        recomputeCounts();
        applyFilters();   // tamamlanan, showDone kapalıysa gizlensin
    }

    function cycleStatus(task) {
        const i = DURUM_CYCLE.indexOf(task.dataset.durum);
        writeDurum(task, DURUM_CYCLE[(i + 1) % DURUM_CYCLE.length]);
    }

    // ---- Navigasyon (deep-link) ----
    function goProduct(group) {
        if (group && group.dataset.urunId) location.href = `/urun/${group.dataset.urunId}`;
    }
    function goTask(task) {
        const group = task.closest(".gor-group");
        if (!group) return;
        const uid = group.dataset.urunId;
        const surum = task.dataset.surum;
        let url = `/urun/${uid}?tab=teknik&sub=todo`;
        if (surum) url += `&surum=${encodeURIComponent(surum)}`;
        location.href = url;
    }

    // ---- Olaylar ----
    groupsEl.addEventListener("click", (e) => {
        if (e.target.closest(".tek-todo-status")) { cycleStatus(e.target.closest(".gor-task")); return; }
        if (e.target.closest(".gor-task-complete")) { writeDurum(e.target.closest(".gor-task"), "tamamlandi"); return; }
        const prod = e.target.closest(".gor-prod");
        if (prod) { goProduct(prod.closest(".gor-group")); return; }
        const task = e.target.closest(".gor-task");
        if (task) { goTask(task); return; }
    });

    groupsEl.addEventListener("keydown", (e) => {
        if (e.key !== "Enter" && e.key !== " ") return;
        const prod = e.target.closest(".gor-prod");
        const task = e.target.closest(".gor-task");
        if (prod) { e.preventDefault(); goProduct(prod.closest(".gor-group")); }
        else if (task) { e.preventDefault(); goTask(task); }
    });

    [searchEl, fDurum, fOncelik, fFolder, showDoneEl].forEach(el => {
        if (!el) return;
        el.addEventListener("input", applyFilters);
        el.addEventListener("change", applyFilters);
    });

    // İlk filtre uygula (tamamlandı varsayılan gizli)
    applyFilters();
})();
