/**
 * v4.0-part-2 Adım 6 — Ayarlar sayfası: Firma CRUD + Modal + Yeniden Tara.
 *
 * IIFE; window'a expose etmez. Event delegation ile DOM'a bağlanır.
 * window.toast (toast.js) varsa kullanır, yoksa alert() fallback.
 */
(function () {
    "use strict";

    const tbody = document.getElementById("brands-tbody");
    const modal = document.getElementById("brand-modal");
    if (!modal) return;

    const I = {
        name: document.getElementById("brand-input-name"),
        slug: document.getElementById("brand-input-slug"),
        country: document.getElementById("brand-input-country"),
        website: document.getElementById("brand-input-website"),
        title: document.getElementById("brand-modal-title"),
        save: document.getElementById("brand-modal-save"),
        cancel: document.getElementById("brand-modal-cancel"),
    };

    let editingSlug = null;

    function toast(msg, type) {
        if (window.toast) window.toast(msg, type || "info");
        else alert(msg);
    }

    function openModal(brand) {
        editingSlug = brand ? brand.slug : null;
        I.title.textContent = brand ? "Firma Düzenle" : "Yeni Firma";
        I.name.value = (brand && brand.name) || "";
        I.slug.value = (brand && brand.slug) || "";
        I.country.value = (brand && brand.country) || "";
        I.website.value = (brand && brand.website) || "";
        modal.hidden = false;
        document.body.style.overflow = "hidden";
        // Bir tick bekle, sonra focus (display transition için)
        setTimeout(() => I.name.focus(), 50);
    }

    function closeModal() {
        modal.hidden = true;
        document.body.style.overflow = "";
        editingSlug = null;
    }

    async function postJson(url, body, method) {
        const opts = {
            method: method || "POST",
            headers: { "Content-Type": "application/json" },
        };
        if (body !== undefined) opts.body = JSON.stringify(body);
        const res = await fetch(url, opts);
        try { return await res.json(); }
        catch (e) { return { ok: false, error: "Beklenmedik yanıt" }; }
    }

    async function save() {
        const name = I.name.value.trim();
        if (!name) {
            toast("Ad zorunlu", "error");
            I.name.focus();
            return;
        }
        const payload = {
            name: name,
            country: I.country.value.trim() || null,
            website: I.website.value.trim() || null,
        };
        I.save.disabled = true;
        try {
            const url = editingSlug ? `/api/brands/${editingSlug}` : `/api/brands`;
            const data = await postJson(url, payload, "POST");
            if (data.ok) {
                toast(editingSlug ? "Güncellendi" : "Eklendi", "success");
                closeModal();
                location.reload();
            } else {
                toast(data.error || "Kayıt hatası", "error");
            }
        } finally {
            I.save.disabled = false;
        }
    }

    async function deleteBrand(slug, name) {
        if (!confirm(`"${name}" firması registry'den silinsin mi?\n\nNot: Mevcut ürünler etkilenmez — sadece "Yeni Ürün" dropdown'undan kalkar.`)) return;
        const data = await postJson(`/api/brands/${slug}`, undefined, "DELETE");
        if (data.ok) {
            toast("Silindi", "success");
            location.reload();
        } else {
            toast(data.error || "Silme hatası", "error");
        }
    }

    async function reseed() {
        if (!confirm("Firma kütüphanesi sıfırlanıp:\n\n• Sistemde tanımlı 10 marka\n• Mevcut ürünlerde geçen markalar\n\n…yeniden taranacak. Devam?")) return;
        const data = await postJson("/api/brands/reseed", {}, "POST");
        if (data.ok) {
            toast(`${data.count} firma yüklendi`, "success");
            location.reload();
        } else {
            toast(data.error || "Yeniden tarama hatası", "error");
        }
    }

    // === Event bindings ===
    document.getElementById("brand-add-btn").addEventListener("click", () => openModal(null));
    document.getElementById("brand-reseed-btn").addEventListener("click", reseed);
    I.save.addEventListener("click", save);
    I.cancel.addEventListener("click", closeModal);

    // Modal backdrop click (modal'ın kendi içine değil, dış'ına tıkla)
    modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });

    // ESC kapatma
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !modal.hidden) closeModal();
    });

    // Enter ile Kaydet (name input'ta)
    I.name.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); save(); }
    });
    I.country.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); save(); }
    });
    I.website.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); save(); }
    });

    // Tablo aksiyon delegation (edit / delete)
    if (tbody) {
        tbody.addEventListener("click", (e) => {
            const btn = e.target.closest("button[data-action]");
            if (!btn) return;
            const row = btn.closest("tr");
            if (!row) return;
            const brand = {
                slug: row.dataset.slug,
                name: row.dataset.name,
                country: row.dataset.country,
                website: row.dataset.website,
            };
            if (btn.dataset.action === "edit") {
                openModal(brand);
            } else if (btn.dataset.action === "delete") {
                deleteBrand(brand.slug, brand.name);
            }
        });
    }
})();
