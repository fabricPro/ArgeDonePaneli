/* v4.0-part-2 Sprint 11 — Albüm + Renk Paleti aracı (ürün öncesi)
 *
 * Araştırma detayı ve "Ürüne Çevir" ekranında, ürün oluşturulmadan ÖNCE
 * görselleri albümlere ("Renkler" galerisi dahil) ayırmak ve atkı/çözgü/toplam
 * renk seçip palet oluşturmak için kullanılır.
 *
 * Ürün tarafındaki (urun.html) mantığın generik, yeniden kullanılabilir hâli.
 * window.ColorPicker (color-picker.js) ve window.toast (toast.js) gerektirir.
 *
 * Yapılandırma — sayfa şu objeyi tanımlamalı (script'ten ÖNCE):
 *   window.__AC_CONFIG__ = {
 *     base: "/api/arastirma/<id>",   // albüm + /gorsel-renk endpoint kökü
 *     cardSelector: ".ardet-img-card" // data-path + data-albums taşıyan görsel kartları
 *   };
 */
(function () {
    "use strict";

    const CFG = window.__AC_CONFIG__;
    if (!CFG || !CFG.base) return;
    const BASE = CFG.base.replace(/\/$/, "");
    const CARD_SEL = CFG.cardSelector || ".ardet-img-card";

    async function postJson(url, body) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body || {}),
        });
        try { return await res.json(); }
        catch (e) { return { ok: false, error: "Sunucu yanıtı okunamadı" }; }
    }
    const toast = (msg, type) => (window.toast || function (m) { alert(m); })(msg, type);

    function cards() { return Array.from(document.querySelectorAll(CARD_SEL)); }

    // ============================================================
    // A) Albüm sekmeleri — filtre + CRUD
    // ============================================================
    (function () {
        const tabs = Array.from(document.querySelectorAll(".album-tab"));
        if (!tabs.length) return;

        function applyFilter(slug) {
            cards().forEach((el) => {
                let tags = [];
                try { tags = JSON.parse(el.dataset.albums || "[]"); } catch (e) {}
                el.dataset.acHidden = (slug && !tags.includes(slug)) ? "1" : "0";
                // Kart konteynerinin display'i: filtre gizlemesi VE 'kaldırıldı' birleşimi
                el.style.display = (el.dataset.acHidden === "1") ? "none" : "";
            });
        }

        tabs.forEach((tab) => {
            tab.addEventListener("click", (e) => {
                const action = e.target.closest(".album-edit")?.dataset.action;
                const slug = tab.dataset.album;
                if (action === "rename") {
                    e.stopPropagation();
                    const cur = tab.dataset.name || "";
                    const nn = prompt("Yeni albüm adı:", cur);
                    if (!nn || nn.trim() === cur) return;
                    postJson(`${BASE}/album-yeniden-adlandir`, { slug, new_name: nn.trim() })
                        .then((d) => d.ok ? location.reload() : toast(d.error || "Yeniden adlandırılamadı", "error"));
                    return;
                }
                if (action === "delete") {
                    e.stopPropagation();
                    if (!confirm(`"${tab.dataset.name}" albümü silinsin mi? Görseller silinmez, sadece etiket kaldırılır.`)) return;
                    postJson(`${BASE}/album-sil`, { slug })
                        .then((d) => d.ok ? location.reload() : toast(d.error || "Silinemedi", "error"));
                    return;
                }
                if (tab.id === "album-new-btn") {
                    const name = prompt("Yeni albüm adı (örn. Renkler, Varyantlar):", "");
                    if (!name || !name.trim()) return;
                    postJson(`${BASE}/album-ekle`, { name: name.trim() })
                        .then((d) => d.ok ? location.reload() : toast(d.error || "Albüm oluşturulamadı", "error"));
                    return;
                }
                tabs.forEach((t) => t.classList.toggle("is-active", t === tab));
                applyFilter(slug);
            });
        });
    })();

    // ============================================================
    // B) Görsel seçim modu + albüme atama
    // ============================================================
    (function () {
        const toggle = document.getElementById("img-select-toggle");
        const bar = document.getElementById("img-select-actionbar");
        const countEl = document.getElementById("img-sel-count");
        const cancelBtn = document.getElementById("img-sel-cancel");
        const assignSel = document.getElementById("album-assign");
        const unassignSel = document.getElementById("album-unassign");
        if (!toggle) return;

        const selected = new Set();
        const updateCount = () => { if (countEl) countEl.textContent = selected.size; };

        function setOn(on) {
            document.body.classList.toggle("image-select-on", on);
            toggle.classList.toggle("is-active", on);
            if (!on) {
                selected.clear();
                cards().forEach((c) => c.classList.remove("ac-selected"));
            }
            if (bar) bar.hidden = !on;
            updateCount();
        }
        toggle.addEventListener("click", () => setOn(!document.body.classList.contains("image-select-on")));
        cancelBtn?.addEventListener("click", () => setOn(false));

        // Seçim modunda kart tıklaması = seç/bırak (capture: diğer click'leri yut)
        document.addEventListener("click", (e) => {
            if (!document.body.classList.contains("image-select-on")) return;
            const card = e.target.closest(CARD_SEL);
            if (!card) return;
            e.preventDefault();
            e.stopPropagation();
            const p = card.dataset.path;
            if (!p) return;
            if (selected.has(p)) { selected.delete(p); card.classList.remove("ac-selected"); }
            else { selected.add(p); card.classList.add("ac-selected"); }
            updateCount();
        }, true);

        async function assign(slug, add) {
            if (selected.size === 0) { toast("Önce görsel seç", "warn"); return; }
            const d = await postJson(`${BASE}/album-atama`, { slug, paths: [...selected], add: !!add });
            if (d.ok) location.reload();
            else toast(d.error || "Atama hatası", "error");
        }

        assignSel?.addEventListener("change", async (e) => {
            const v = e.target.value;
            if (!v) return;
            if (v === "__new__") {
                const name = prompt("Yeni albüm adı:", "");
                e.target.value = "";
                if (!name || !name.trim()) return;
                const d = await postJson(`${BASE}/album-ekle`, { name: name.trim() });
                if (!d.ok) return toast(d.error || "Albüm oluşturulamadı", "error");
                await assign(d.slug, true);
                return;
            }
            await assign(v, true);
            e.target.value = "";
        });

        unassignSel?.addEventListener("change", async (e) => {
            const v = e.target.value;
            if (!v) return;
            await assign(v, false);
            e.target.value = "";
        });
    })();

    // ============================================================
    // C) Renk seçici (Atkı / Çözgü / Toplam)
    // ============================================================
    (function () {
        const sectionEl = document.getElementById("color-tools");
        if (!sectionEl || !window.ColorPicker) return;

        const canvas = document.getElementById("cp-canvas");
        const mag = document.getElementById("cp-magnifier");
        const imageSel = document.getElementById("cp-image-sel");
        const detailsEl = document.getElementById("cp-details");
        if (!canvas || !imageSel) return; // "Renkler" albümü yoksa sadece palet görünür

        const avgEl = document.getElementById("cp-avg");
        const clearBtn = document.getElementById("cp-clear");
        const countEl = document.getElementById("cp-count");
        const tabs = sectionEl.querySelectorAll(".cp-role-tab");
        const swatch = document.getElementById("cp-swatch");
        const nameEl = document.getElementById("cp-name");
        const deEl = document.getElementById("cp-de");
        const hexEl = document.getElementById("cp-hex");
        const rgbEl = document.getElementById("cp-rgb");
        const labEl = document.getElementById("cp-lab");
        const qualEl = document.getElementById("cp-quality");
        const saveBtn = document.getElementById("cp-save");
        const saveLabel = document.getElementById("cp-save-label");
        const paletteGrid = document.getElementById("palette-grid");
        const paletteCnt = document.getElementById("palette-cnt");

        const ROLE_TR = { weft: "Atkı", warp: "Çözgü", mix: "Toplam" };
        const ROLE_SHORT = { weft: "A", warp: "Ç", mix: "T" };
        let activeRole = "weft";

        function escapeHtml(s) {
            return String(s).replace(/[&<>"']/g, (ch) => ({
                "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
            }[ch]));
        }

        function updateUI(role, res, n) {
            if (countEl) countEl.textContent = (n || 0) + " nokta";
            if (!res || !res.hex) {
                swatch.style.background = "transparent";
                nameEl.textContent = "—";
                deEl.textContent = ""; hexEl.textContent = "—";
                rgbEl.textContent = "—"; labEl.textContent = "—";
                qualEl.hidden = true; qualEl.className = "cp-quality";
                saveBtn.disabled = true;
                return;
            }
            swatch.style.background = res.hex;
            nameEl.textContent = res.name || "—";
            if (res.delta_e != null) {
                const tag = res.delta_e < 3 ? " (tam isabet)" : res.delta_e < 6 ? " (yakın)" : " (yaklaşık)";
                deEl.textContent = "ΔE2000 = " + res.delta_e.toFixed(1) + tag;
            } else { deEl.textContent = ""; }
            hexEl.textContent = res.hex;
            rgbEl.textContent = res.rgb.join(", ");
            labEl.textContent = "L " + res.lab[0].toFixed(1) + " · a " + res.lab[1].toFixed(1) + " · b " + res.lab[2].toFixed(1);
            if (res.quality === "ok") {
                qualEl.hidden = false; qualEl.className = "cp-quality ok";
                qualEl.textContent = "Tutarlı (yayılım ΔE " + res.spread.toFixed(1) + ")";
            } else if (res.quality === "warn") {
                qualEl.hidden = false;
                qualEl.className = "cp-quality warn" + ((role === "weft" || role === "warp") ? " is-critical" : "");
                qualEl.textContent = "Yayılım yüksek (ΔE " + res.spread.toFixed(1) + ") — aynı tondan topla";
            } else { qualEl.hidden = true; qualEl.className = "cp-quality"; }
            saveBtn.disabled = false;
        }

        function setActiveTab(role) {
            activeRole = role;
            tabs.forEach((t) => t.classList.toggle("is-active", t.dataset.role === role));
            saveLabel.textContent = ROLE_TR[role] + "'a Ata";
        }

        tabs.forEach((t) => t.addEventListener("click", () => window.ColorPicker.setRole(t.dataset.role)));
        avgEl?.addEventListener("change", () => window.ColorPicker.setAvg(avgEl.checked));
        clearBtn?.addEventListener("click", () => window.ColorPicker.clearPoints(activeRole));

        async function loadImage(url) {
            try { await window.ColorPicker.setImage(url); }
            catch (err) { toast("Görsel yüklenemedi (CORS olabilir)", "error"); console.error(err); }
        }
        imageSel.addEventListener("change", () => loadImage(imageSel.value));

        // Karta çift tık → o görseli renk seçiciye yükle
        cards().forEach((card) => {
            card.addEventListener("dblclick", () => {
                if (document.body.classList.contains("image-select-on")) return;
                const path = card.dataset.path;
                const opt = [...imageSel.options].find((o) => o.dataset.path === path);
                if (!opt) { toast('Bu görsel "Renkler" albümünde değil', "warn"); return; }
                imageSel.value = opt.value;
                if (detailsEl && !detailsEl.open) detailsEl.open = true;
                loadImage(opt.value);
                imageLoaded = true;
                sectionEl.scrollIntoView({ behavior: "smooth", block: "start" });
            });
        });

        function rebuildPalette(palette) {
            if (!paletteGrid) return;
            if (paletteCnt) paletteCnt.textContent = palette.length;
            paletteGrid.innerHTML = palette.map((c) => {
                const roles = c.roles.map((r) => '<em class="chip-role chip-role-' + r + '">' + (ROLE_SHORT[r] || "?") + "</em>").join("");
                return '<button type="button" class="palette-chip" data-hex="' + c.hex + '" ' +
                    'title="' + escapeHtml(c.name) + " · " + c.hex + " · L " + Math.round(c.lab[0]) + '">' +
                    '<span class="chip-swatch" style="background:' + c.hex + '"></span>' +
                    '<span class="chip-info"><span class="chip-name">' + escapeHtml(c.name) + "</span>" +
                    '<span class="chip-roles">' + roles + "</span></span></button>";
            }).join("");
            const emptyHint = sectionEl.querySelector(".ct-empty");
            if (palette.length && emptyHint) emptyHint.remove();
        }

        function updateImageBadges(path, colors) {
            const card = document.querySelector(`${CARD_SEL}[data-path="${CSS.escape(path)}"]`);
            if (!card) return;
            let badgesEl = card.querySelector(".img-color-badges");
            if (!Object.keys(colors || {}).length) { if (badgesEl) badgesEl.remove(); return; }
            if (!badgesEl) {
                badgesEl = document.createElement("div");
                badgesEl.className = "img-color-badges";
                badgesEl.dataset.path = path;
                card.appendChild(badgesEl);
            }
            const ROLE_LONG = { weft: "Atkı", warp: "Çözgü", mix: "Toplam" };
            badgesEl.innerHTML = ["weft", "warp", "mix"].filter((r) => colors[r]).map((r) => {
                const c = colors[r];
                return '<span class="color-badge color-badge-' + r + '" style="--c:' + c.hex + '" ' +
                    'title="' + ROLE_LONG[r] + ": " + escapeHtml(c.name) + " (" + c.hex + ')">' +
                    '<em class="cb-role">' + (ROLE_SHORT[r] || "?") + "</em>" +
                    '<span class="cb-name">' + escapeHtml(c.name) + "</span></span>";
            }).join("");
        }

        saveBtn.addEventListener("click", async () => {
            const role = activeRole;
            const result = window.ColorPicker.getResult(role);
            if (!result || !result.hex) { toast("Önce nokta seç", "warn"); return; }
            const opt = imageSel.options[imageSel.selectedIndex];
            const path = opt.dataset.path;
            const d = await postJson(`${BASE}/gorsel-renk`, { path, colors: { [role]: result } });
            if (d.ok) {
                toast(ROLE_TR[role] + " kaydedildi: " + result.name, "success");
                rebuildPalette(d.palette);
                updateImageBadges(path, d.image_colors);
                window.ColorPicker.clearPoints(role);
                const next = { weft: "warp", warp: "mix", mix: null }[role];
                if (next) window.ColorPicker.setRole(next);
            } else { toast(d.error || "Kayıt hatası", "error"); }
        });

        let pickerReady = false;
        let imageLoaded = false;
        window.ColorPicker.init({
            canvasEl: canvas,
            magnifierEl: mag,
            dictionaryUrl: CFG.dictionaryUrl || "/static/data/renkler.json",
            onChange: (role, res, n) => updateUI(role, res, n),
            onRoleChange: (role) => setActiveTab(role),
        }).then((info) => {
            pickerReady = true;
            if (detailsEl && detailsEl.open && imageSel.value) { loadImage(imageSel.value); imageLoaded = true; }
        });

        if (detailsEl) {
            detailsEl.addEventListener("toggle", () => {
                if (!detailsEl.open || !pickerReady || imageLoaded) return;
                if (imageSel.value) { loadImage(imageSel.value); imageLoaded = true; }
            });
        }
    })();
})();
