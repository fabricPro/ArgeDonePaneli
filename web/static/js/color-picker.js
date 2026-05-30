/* v3.6 — Renk Çözümleme (Atkı / Çözgü / Toplam)
 * Demo HTML'in motor fonksiyonları birebir taşındı.
 * Renk isim kaynağı: meodai/color-names "best of" (MIT, ~4.930 isim).
 *   https://github.com/meodai/color-names
 * Fallback (sözlük yüklenemezse): 37-renk Türkçe mini kartela.
 */
(function () {
    "use strict";

    // === Fallback mini sözlük (Türkçe, demo'dakinin aynısı) ===
    const FALLBACK_COLORS = [
        ["Beyaz",[255,255,255]],["Kırık Beyaz",[245,243,235]],["Krem",[245,236,210]],
        ["Bej",[225,210,180]],["Kum",[200,185,150]],["Taş",[180,170,155]],
        ["Açık Gri",[200,200,200]],["Gri",[132,132,132]],["Koyu Gri",[90,90,90]],
        ["Antrasit",[55,58,64]],["Siyah",[20,20,20]],["Ekru",[235,225,200]],
        ["Vizon",[150,130,110]],["Kahve",[110,80,55]],["Koyu Kahve",[70,50,35]],
        ["Tarçın",[140,90,55]],["Kırmızı",[200,40,40]],["Bordo",[110,30,40]],
        ["Mercan",[235,110,90]],["Pembe",[235,150,170]],["Pudra",[230,200,200]],
        ["Fuşya",[200,40,120]],["Turuncu",[230,130,40]],["Hardal",[200,160,40]],
        ["Sarı",[235,210,60]],["Yeşil",[60,140,70]],["Açık Yeşil",[140,190,120]],
        ["Zeytin",[110,120,60]],["Petrol",[40,90,95]],["Turkuaz",[60,170,170]],
        ["Mint",[170,215,200]],["Mavi",[50,90,180]],["Lacivert",[35,45,90]],
        ["Açık Mavi",[150,190,225]],["Gri Mavi",[120,140,160]],["Mor",[120,70,150]],["Lila",[190,160,205]]
    ];

    // === RGB <-> LAB ve ΔE2000 — demo'dan birebir ===
    function rgbToLab(r, g, b) {
        r /= 255; g /= 255; b /= 255;
        r = r > 0.04045 ? Math.pow((r + 0.055) / 1.055, 2.4) : r / 12.92;
        g = g > 0.04045 ? Math.pow((g + 0.055) / 1.055, 2.4) : g / 12.92;
        b = b > 0.04045 ? Math.pow((b + 0.055) / 1.055, 2.4) : b / 12.92;
        let x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047;
        let y = (r * 0.2126 + g * 0.7152 + b * 0.0722);
        let z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883;
        const f = t => t > 0.008856 ? Math.cbrt(t) : (7.787 * t + 16 / 116);
        x = f(x); y = f(y); z = f(z);
        return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
    }

    function deltaE00(l1, l2) {
        const [L1, a1, b1] = l1, [L2, a2, b2] = l2;
        const avgL = (L1 + L2) / 2;
        const C1 = Math.hypot(a1, b1), C2 = Math.hypot(a2, b2), avgC = (C1 + C2) / 2;
        const G = 0.5 * (1 - Math.sqrt(Math.pow(avgC, 7) / (Math.pow(avgC, 7) + Math.pow(25, 7))));
        const a1p = a1 * (1 + G), a2p = a2 * (1 + G);
        const C1p = Math.hypot(a1p, b1), C2p = Math.hypot(a2p, b2), avgCp = (C1p + C2p) / 2;
        const h = (x, y) => { let hp = Math.atan2(y, x) * 180 / Math.PI; return hp < 0 ? hp + 360 : hp; };
        const h1p = h(a1p, b1), h2p = h(a2p, b2);
        const dLp = L2 - L1, dCp = C2p - C1p;
        let dhp;
        if (C1p * C2p === 0) dhp = 0;
        else if (Math.abs(h2p - h1p) <= 180) dhp = h2p - h1p;
        else dhp = h2p - h1p > 180 ? h2p - h1p - 360 : h2p - h1p + 360;
        const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin(dhp * Math.PI / 360);
        let avgHp;
        if (C1p * C2p === 0) avgHp = h1p + h2p;
        else if (Math.abs(h1p - h2p) <= 180) avgHp = (h1p + h2p) / 2;
        else avgHp = h1p + h2p < 360 ? (h1p + h2p + 360) / 2 : (h1p + h2p - 360) / 2;
        const T = 1 - 0.17 * Math.cos((avgHp - 30) * Math.PI / 180) + 0.24 * Math.cos((2 * avgHp) * Math.PI / 180)
            + 0.32 * Math.cos((3 * avgHp + 6) * Math.PI / 180) - 0.20 * Math.cos((4 * avgHp - 63) * Math.PI / 180);
        const dRo = 30 * Math.exp(-Math.pow((avgHp - 275) / 25, 2));
        const Rc = 2 * Math.sqrt(Math.pow(avgCp, 7) / (Math.pow(avgCp, 7) + Math.pow(25, 7)));
        const Sl = 1 + (0.015 * Math.pow(avgL - 50, 2)) / Math.sqrt(20 + Math.pow(avgL - 50, 2));
        const Sc = 1 + 0.045 * avgCp, Sh = 1 + 0.015 * avgCp * T;
        const Rt = -Math.sin(2 * dRo * Math.PI / 180) * Rc;
        return Math.sqrt(Math.pow(dLp / Sl, 2) + Math.pow(dCp / Sc, 2) + Math.pow(dHp / Sh, 2) + Rt * (dCp / Sc) * (dHp / Sh));
    }

    // === Sözlük + önhesap (LAB cache) ===
    let COLOR_LAB = [];
    let dictionaryReady = false;
    let dictionaryPromise = null;

    function loadDictionary(url) {
        if (dictionaryPromise) return dictionaryPromise;
        dictionaryPromise = fetch(url)
            .then(r => {
                if (!r.ok) throw new Error("dictionary fetch failed: " + r.status);
                return r.json();
            })
            .then(list => {
                // meodai best-of formatı: [{name, hex}, ...]
                // Fallback formatı: [["Name",[r,g,b]], ...]
                COLOR_LAB = list.map(item => {
                    if (Array.isArray(item)) {
                        const [name, rgb] = item;
                        return { name, hex: rgbToHex(rgb), rgb, lab: rgbToLab(...rgb) };
                    }
                    const rgb = hexToRgb(item.hex);
                    return { name: item.name, hex: item.hex.toUpperCase(), rgb, lab: rgbToLab(...rgb) };
                });
                dictionaryReady = true;
                console.log(`[ColorPicker] Sözlük yüklendi: ${COLOR_LAB.length} renk`);
                return COLOR_LAB.length;
            })
            .catch(err => {
                console.warn("[ColorPicker] Sözlük yüklenemedi, fallback kullanılıyor:", err);
                COLOR_LAB = FALLBACK_COLORS.map(([name, rgb]) => ({
                    name, hex: rgbToHex(rgb), rgb, lab: rgbToLab(...rgb),
                }));
                dictionaryReady = true;
                return COLOR_LAB.length;
            });
        return dictionaryPromise;
    }

    function nearestColorName(r, g, b) {
        const lab = rgbToLab(r, g, b);
        let best = null, min = Infinity;
        for (const c of COLOR_LAB) {
            const d = deltaE00(lab, c.lab);
            if (d < min) { min = d; best = { name: c.name, hex: c.hex, de: d }; }
        }
        return best;
    }

    function hexToRgb(hex) {
        const s = hex.replace(/^#/, "");
        const n = parseInt(s.length === 3 ? s.split("").map(c => c + c).join("") : s, 16);
        return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    }
    function rgbToHex(rgb) {
        return "#" + rgb.map(v => v.toString(16).padStart(2, "0")).join("").toUpperCase();
    }

    // === Tek noktadan örnek (5x5 ön-ortalama) ===
    function sampleAt(ctx, x, y, size) {
        const h = Math.floor(size / 2);
        // Clamp to canvas bounds to avoid getImageData errors at edges
        const cw = ctx.canvas.width, ch = ctx.canvas.height;
        const sx = Math.max(0, Math.min(cw - size, x - h));
        const sy = Math.max(0, Math.min(ch - size, y - h));
        const data = ctx.getImageData(sx, sy, size, size).data;
        let r = 0, g = 0, b = 0, n = 0;
        for (let i = 0; i < data.length; i += 4) { r += data[i]; g += data[i + 1]; b += data[i + 2]; n++; }
        return [Math.round(r / n), Math.round(g / n), Math.round(b / n)];
    }

    // === Kanal bazlı medyan ===
    function medianRGB(points) {
        const ch = k => {
            const s = points.map(p => p.rgb[k]).sort((a, b) => a - b);
            const m = s.length >> 1;
            return s.length % 2 ? s[m] : Math.round((s[m - 1] + s[m]) / 2);
        };
        return [ch(0), ch(1), ch(2)];
    }

    // ============================================================
    // ColorPicker IIFE — UI bağlama
    // ============================================================
    const state = {
        canvasEl: null,
        magEl: null,
        magCtx: null,
        ctx: null,
        img: null,
        avgEnabled: true,
        activeRole: "weft",                                 // 'weft' | 'warp' | 'mix'
        points: { weft: [], warp: [], mix: [] },            // per-role points persistent
        callbacks: { onChange: null, onSave: null, onRoleChange: null },
    };

    const MAG_W = 150, ZOOM = 8;

    function evtToPixel(evt, canvas) {
        const r = canvas.getBoundingClientRect();
        const cx = evt.clientX !== undefined ? evt.clientX : (evt.touches?.[0]?.clientX || 0);
        const cy = evt.clientY !== undefined ? evt.clientY : (evt.touches?.[0]?.clientY || 0);
        return [
            Math.floor((cx - r.left) * canvas.width / r.width),
            Math.floor((cy - r.top) * canvas.height / r.height),
        ];
    }

    function redraw() {
        const c = state.canvasEl, ctx = state.ctx, img = state.img;
        if (!c || !ctx || !img) return;
        ctx.drawImage(img, 0, 0);
        const pts = state.points[state.activeRole] || [];
        pts.forEach((p, i) => {
            ctx.beginPath();
            ctx.arc(p.x, p.y, 7, 0, Math.PI * 2);
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.fillStyle = "rgba(0,0,0,.55)";
            ctx.fill();
            ctx.fillStyle = "#fff";
            ctx.font = "11px sans-serif";
            ctx.fillText(String(i + 1), p.x + 9, p.y + 4);
        });
    }

    function drawMagAt(px, py) {
        const m = state.magCtx;
        const img = state.img;
        if (!m || !img) return;
        const src = MAG_W / ZOOM;
        m.clearRect(0, 0, MAG_W, MAG_W);
        m.drawImage(img, px - src / 2, py - src / 2, src, src, 0, 0, MAG_W, MAG_W);
        const size = state.avgEnabled ? 5 : 1;
        const boxPx = size * ZOOM;
        m.strokeStyle = "rgba(255,255,255,.9)"; m.lineWidth = 1;
        m.strokeRect(MAG_W / 2 - boxPx / 2, MAG_W / 2 - boxPx / 2, boxPx, boxPx);
        m.strokeStyle = "rgba(255,80,60,.95)"; m.lineWidth = 1;
        m.beginPath();
        m.moveTo(MAG_W / 2 - 9, MAG_W / 2); m.lineTo(MAG_W / 2 + 9, MAG_W / 2);
        m.moveTo(MAG_W / 2, MAG_W / 2 - 9); m.lineTo(MAG_W / 2, MAG_W / 2 + 9);
        m.stroke();
    }

    function placeMag(clientX, clientY, offsetTouch) {
        const m = state.magEl;
        if (!m) return;
        const box = state.canvasEl.parentElement.getBoundingClientRect();
        // Mobil touch'ta yukarı ofset (parmak altında kalmasın)
        const oy = offsetTouch ? 80 : 0;
        m.style.left = (clientX - box.left - MAG_W / 2) + "px";
        m.style.top = (clientY - box.top - MAG_W / 2 - oy) + "px";
    }

    function compute() {
        const pts = state.points[state.activeRole];
        if (!pts.length) {
            return null;
        }
        const [r, g, b] = medianRGB(pts);
        const lab = rgbToLab(r, g, b);
        const nearest = dictionaryReady ? nearestColorName(r, g, b) : { name: "—", de: 0 };
        // Kalite: spread ΔE medyana göre
        let quality = null, spread = 0;
        if (pts.length >= 2) {
            spread = Math.max(...pts.map(p => deltaE00(lab, rgbToLab(...p.rgb))));
            quality = spread < 3 ? "ok" : "warn";
        }
        const hex = rgbToHex([r, g, b]);
        return {
            name: nearest ? nearest.name : "—",
            hex, rgb: [r, g, b], lab,
            delta_e: nearest ? +nearest.de.toFixed(2) : null,
            points: pts.map(p => ({ x: p.x, y: p.y, rgb: p.rgb })),
            quality, spread: +spread.toFixed(2),
        };
    }

    function addPointAt(x, y, mode) {
        if (!state.img) return;
        const size = state.avgEnabled ? 5 : 1;
        const rgb = sampleAt(state.ctx, x, y, size);
        if (mode === "replace") state.points[state.activeRole] = [];
        state.points[state.activeRole].push({ x, y, rgb });
        redraw();
        notify();
    }

    function notify() {
        if (state.callbacks.onChange) {
            state.callbacks.onChange(state.activeRole, compute(), state.points[state.activeRole].length);
        }
    }

    function bindCanvas(canvasEl, magEl) {
        state.canvasEl = canvasEl;
        state.ctx = canvasEl.getContext("2d", { willReadFrequently: true });
        if (magEl) {
            state.magEl = magEl;
            state.magCtx = magEl.getContext("2d");
            state.magCtx.imageSmoothingEnabled = false;
        }

        // === Mouse (masaüstü) ===
        canvasEl.addEventListener("click", (e) => {
            if (!state.img) return;
            const [x, y] = evtToPixel(e, canvasEl);
            addPointAt(x, y, (e.ctrlKey || e.metaKey) ? "append" : "replace");
        });
        canvasEl.addEventListener("mousemove", (e) => {
            if (!state.img || !state.magEl) return;
            state.magEl.hidden = false;
            placeMag(e.clientX, e.clientY, false);
            const [px, py] = evtToPixel(e, canvasEl);
            drawMagAt(px, py);
        });
        canvasEl.addEventListener("mouseleave", () => {
            if (state.magEl) state.magEl.hidden = true;
        });

        // === Touch (mobil) — iOS-style loupe (drag-aim-release) ===
        let touchActive = false;
        let lastTouchPx = null;
        let pinchBase = null;        // {dist, scale} — TODO: gerçek pinch için canvas transform gerekli
        canvasEl.addEventListener("touchstart", (e) => {
            if (!state.img) return;
            if (e.touches.length === 1) {
                touchActive = true;
                if (state.magEl) state.magEl.hidden = false;
                const t = e.touches[0];
                placeMag(t.clientX, t.clientY, true);
                const [px, py] = evtToPixel(e, canvasEl);
                lastTouchPx = [px, py];
                drawMagAt(px, py);
                e.preventDefault();
            }
        }, { passive: false });
        canvasEl.addEventListener("touchmove", (e) => {
            if (!touchActive || !state.img) return;
            if (e.touches.length === 1) {
                const t = e.touches[0];
                placeMag(t.clientX, t.clientY, true);
                const [px, py] = evtToPixel(e, canvasEl);
                lastTouchPx = [px, py];
                drawMagAt(px, py);
                e.preventDefault();
            }
        }, { passive: false });
        canvasEl.addEventListener("touchend", (e) => {
            if (!touchActive) return;
            touchActive = false;
            if (state.magEl) state.magEl.hidden = true;
            if (lastTouchPx) {
                addPointAt(lastTouchPx[0], lastTouchPx[1], "replace");
                lastTouchPx = null;
            }
        });
        canvasEl.addEventListener("touchcancel", () => {
            touchActive = false;
            lastTouchPx = null;
            if (state.magEl) state.magEl.hidden = true;
        });
    }

    // === Public API ===
    window.ColorPicker = {
        async init(opts) {
            // opts: {canvasEl, magnifierEl, dictionaryUrl, onChange, onSave, onRoleChange}
            bindCanvas(opts.canvasEl, opts.magnifierEl);
            state.callbacks.onChange = opts.onChange || null;
            state.callbacks.onSave = opts.onSave || null;
            state.callbacks.onRoleChange = opts.onRoleChange || null;
            await loadDictionary(opts.dictionaryUrl || "/static/data/colornames.bestof.json");
            return { dictionarySize: COLOR_LAB.length };
        },
        async setImage(url) {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.crossOrigin = "anonymous";
                img.onload = () => {
                    state.canvasEl.width = img.naturalWidth;
                    state.canvasEl.height = img.naturalHeight;
                    state.img = img;
                    // Sadece aktif rol noktasını sıfırla? Hayır: yeni görsel = tüm noktalar reset
                    state.points = { weft: [], warp: [], mix: [] };
                    redraw();
                    notify();
                    resolve();
                };
                img.onerror = (e) => reject(new Error("Image load failed: " + url));
                img.src = url;
            });
        },
        setAvg(enabled) { state.avgEnabled = !!enabled; },
        setRole(role) {
            if (!["weft", "warp", "mix"].includes(role)) return;
            state.activeRole = role;
            redraw();
            if (state.callbacks.onRoleChange) state.callbacks.onRoleChange(role);
            notify();
        },
        getActiveRole() { return state.activeRole; },
        getResult(role) {
            const r = role || state.activeRole;
            const saved = state.activeRole;
            state.activeRole = r;
            const out = compute();
            state.activeRole = saved;
            return out;
        },
        getAll() {
            const out = {};
            for (const r of ["weft", "warp", "mix"]) {
                const saved = state.activeRole;
                state.activeRole = r;
                const v = compute();
                state.activeRole = saved;
                if (v) out[r] = v;
            }
            return out;
        },
        clearPoints(role) {
            if (role) state.points[role] = [];
            else state.points = { weft: [], warp: [], mix: [] };
            redraw();
            notify();
        },
        // Test helpers
        _rgbToLab: rgbToLab,
        _deltaE00: deltaE00,
        _nearestColorName: nearestColorName,
        _medianRGB: medianRGB,
    };
})();
