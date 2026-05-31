/**
 * v4.0-part-2 Adım 7 — Dokümanlar sekmesi: PDF upload/list/delete + iframe viewer.
 *
 * IIFE; URUN_ID global'inden ürün ID'sini alır.
 * window.toast varsa kullanır, yoksa alert fallback.
 *
 * Storage: Supabase 'pdfler' bucket'ı (public), path: <urun_id>/<uuid8>_<ad>.pdf
 */
(function () {
    "use strict";

    const URUN_ID = window.URUN_ID;
    if (!URUN_ID) return;

    const uploadInput = document.getElementById("pdf-upload-input");
    const pdfList = document.getElementById("pdf-list");
    const viewer = document.getElementById("pdf-viewer");
    const viewerWrap = document.getElementById("pdf-viewer-wrap");
    const emptyState = document.getElementById("pdf-empty");
    if (!uploadInput || !pdfList) return;

    function toast(msg, type) {
        if (window.toast) window.toast(msg, type || "info");
        else if (type === "error") alert(msg);
    }

    function fmtMB(bytes) {
        return (bytes / 1024 / 1024).toFixed(2) + " MB";
    }

    function fmtDateShort(iso) {
        return (iso || "").slice(0, 10);
    }

    function setActiveCard(card) {
        pdfList.querySelectorAll(".pdf-card").forEach(c => c.classList.toggle("is-active", c === card));
    }

    function showViewer(url) {
        if (!viewer || !viewerWrap) return;
        viewer.src = url || "about:blank";
        viewerWrap.hidden = !url;
        if (emptyState) emptyState.hidden = !!pdfList.querySelector(".pdf-card");
    }

    function renderCard(pdf) {
        const tpl = document.createElement("article");
        tpl.className = "pdf-card";
        tpl.dataset.path = pdf.path;
        tpl.dataset.url = pdf.url;
        tpl.dataset.name = pdf.name;
        tpl.innerHTML = `
            <svg class="pdf-icon"><use href="#ic-file"/></svg>
            <div class="pdf-info">
                <div class="pdf-name"></div>
                <div class="pdf-meta">
                    <span class="pdf-size"></span>
                    <span class="pdf-date"></span>
                </div>
            </div>
            <div class="pdf-actions">
                <a target="_blank" rel="noopener" class="btn-mini" title="Yeni sekmede aç" data-action="open">
                    <svg class="icon"><use href="#ic-external-link"/></svg>
                </a>
                <a class="btn-mini" title="İndir" data-action="download">
                    <svg class="icon"><use href="#ic-download"/></svg>
                </a>
                <button type="button" class="btn-mini btn-danger" title="Sil" data-action="delete">
                    <svg class="icon"><use href="#ic-trash"/></svg>
                </button>
            </div>
        `;
        tpl.querySelector(".pdf-name").textContent = pdf.name;
        tpl.querySelector(".pdf-size").textContent = fmtMB(pdf.size);
        tpl.querySelector(".pdf-date").textContent = fmtDateShort(pdf.uploaded_at);
        tpl.querySelector('[data-action="open"]').href = pdf.url;
        const dl = tpl.querySelector('[data-action="download"]');
        dl.href = pdf.url;
        dl.download = pdf.name;
        return tpl;
    }

    // === Upload ===
    uploadInput.addEventListener("change", async () => {
        const files = [...uploadInput.files];
        if (!files.length) return;
        const fd = new FormData();
        files.forEach(f => fd.append("files", f));
        const btnLabel = document.querySelector(".pdf-upload-label span");
        const origText = btnLabel ? btnLabel.textContent : "";
        if (btnLabel) btnLabel.textContent = "Yükleniyor…";
        try {
            const res = await fetch(`/api/urun/${URUN_ID}/pdf-ekle`, {
                method: "POST", body: fd,
            });
            const data = await res.json();
            if (data.ok && Array.isArray(data.added)) {
                data.added.forEach(pdf => {
                    const card = renderCard(pdf);
                    pdfList.appendChild(card);
                });
                // İlk PDF'i viewer'da göster
                const firstCard = pdfList.querySelector(".pdf-card");
                if (firstCard && !pdfList.querySelector(".pdf-card.is-active")) {
                    setActiveCard(firstCard);
                    showViewer(firstCard.dataset.url);
                }
                toast(`${data.added.length} PDF yüklendi`, "success");
                if (emptyState) emptyState.hidden = true;
                // Sekme buton sayısını güncelle
                updateTabCount(data.count);
            } else {
                toast(data.error || "Yükleme hatası", "error");
            }
        } catch (e) {
            toast("Bağlantı hatası: " + e, "error");
        } finally {
            uploadInput.value = "";
            if (btnLabel) btnLabel.textContent = origText;
        }
    });

    // === Click delegation ===
    pdfList.addEventListener("click", async (e) => {
        const card = e.target.closest(".pdf-card");
        if (!card) return;
        const actionBtn = e.target.closest("[data-action]");
        const action = actionBtn ? actionBtn.dataset.action : null;

        if (action === "delete") {
            e.preventDefault(); e.stopPropagation();
            const name = card.dataset.name;
            if (!confirm(`"${name}" silinsin mi?`)) return;
            try {
                const res = await fetch(`/api/urun/${URUN_ID}/pdf-sil`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({path: card.dataset.path}),
                });
                const data = await res.json();
                if (data.ok) {
                    const wasActive = card.classList.contains("is-active");
                    card.remove();
                    if (wasActive) {
                        const nextCard = pdfList.querySelector(".pdf-card");
                        if (nextCard) {
                            setActiveCard(nextCard);
                            showViewer(nextCard.dataset.url);
                        } else {
                            showViewer(null);
                            if (emptyState) emptyState.hidden = false;
                        }
                    }
                    toast("Silindi", "success");
                    updateTabCount(data.count);
                } else {
                    toast(data.error || "Silme hatası", "error");
                }
            } catch (e) {
                toast("Bağlantı hatası: " + e, "error");
            }
            return;
        }

        if (action === "open" || action === "download") {
            // Native link davranışı (yeni sekme / download) — preventDefault YOK
            // Aynı zamanda kartı aktif yap (UX)
            setActiveCard(card);
            return;
        }

        // Kart gövdesine tıklama → viewer'da aç
        setActiveCard(card);
        showViewer(card.dataset.url);
    });

    // === Sekme buton sayı badge'ini güncelle ===
    function updateTabCount(count) {
        const tabBtn = document.querySelector('.urun-main-tabs [data-tab="dokuman"]');
        if (!tabBtn) return;
        let cnt = tabBtn.querySelector(".utab-cnt");
        if (count > 0) {
            if (!cnt) {
                cnt = document.createElement("span");
                cnt.className = "utab-cnt";
                tabBtn.appendChild(cnt);
            }
            cnt.textContent = count;
        } else if (cnt) {
            cnt.remove();
        }
    }
})();
