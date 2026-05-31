/* v4.0-part-2 Adım 3 Faz A — Desen Modülü saf fonksiyonlar (vanilla JS port)
 *
 * NumuneAtilim Desen Editör spec'inin port'u. React/TypeScript yerine
 * JSDoc tip yorumları + IIFE export pattern.
 *
 * Tüm fonksiyonlar PURE — input mutate etmez, yeni DesenState döner (immutable).
 *
 * Kullanım:
 *   const d = DesenCore.defaultDesen();
 *   const d2 = DesenCore.setDimension(d, 'warpCount', 8);
 *   const matrix = DesenCore.computeDesen(d.tahar, d.armur, d.weftCount);
 *
 * Domain:
 *   - tahar[warpIdx] = frameIdx (0-based) — hangi çözgü hangi çerçeveden geçer
 *   - armur[frameIdx][weftIdx] = boolean — her atkıda çerçeve kalkar mı
 *   - iroData[weftIdx] = iroValue (1-based) — atkı motor/renk no
 *   - DESEN[warp][weft] = ARMUR[ TAHAR[warp] ][ weft ] (türetilir, saklanmaz)
 *
 * @typedef {Object} LoopRange
 * @property {number} startPick  - DO marker (0-based atkı indeksi)
 * @property {number} endPick    - NEXT marker (0-based)
 * @property {number} count      - tekrar sayısı (>= 2)
 *
 * @typedef {Object} DesenState
 * @property {number} warpCount
 * @property {number} weftCount
 * @property {number} frameCount
 * @property {number} iroCount
 * @property {number} raporX
 * @property {number} raporY
 * @property {number[]} tahar
 * @property {boolean[][]} armur
 * @property {number[]} iroData
 * @property {LoopRange[]} loops
 *
 * @typedef {{ kind: 'DO', count: number, loop: LoopRange }
 *         | { kind: 'NEXT', loop: LoopRange }} MarkerInfo
 */

(function () {
    "use strict";

    // === Sabitler ===
    const MIN_WARP = 2,   MAX_WARP = 120;
    const MIN_WEFT = 2,   MAX_WEFT = 120;
    const MIN_FRAME = 2,  MAX_FRAME = 24;
    const MIN_IRO = 1,    MAX_IRO = 8;
    const MIN_LOOP_COUNT = 2, MAX_LOOP_COUNT = 99;
    const MIN_RAPOR = 1,  MAX_RAPOR = 8;

    // İro renk paleti — 8 sabit renk, sırayla i1, i2, ...
    const IRO_COLORS = [
        "#5b8def", "#f0a830", "#3fb6a8", "#36c98a",
        "#e6b94a", "#e8674f", "#a78bfa", "#ec4899"
    ];

    // === Helpers — clamp + utility ===
    function clamp(v, min, max) {
        const n = Number(v);
        if (!isFinite(n)) return min;
        return Math.max(min, Math.min(max, Math.round(n)));
    }

    // === Builders ===

    /** Düz tahar: [0,1,2,...,(frameCount-1),0,1,...] wrap-around */
    function buildDuzTahar(warpCount, frameCount) {
        const w = clamp(warpCount, MIN_WARP, MAX_WARP);
        const f = clamp(frameCount, MIN_FRAME, MAX_FRAME);
        const out = new Array(w);
        for (let i = 0; i < w; i++) out[i] = i % f;
        return out;
    }

    /** Boş armür: frameCount × weftCount tümü false */
    function buildEmptyArmur(frameCount, weftCount) {
        const f = clamp(frameCount, MIN_FRAME, MAX_FRAME);
        const p = clamp(weftCount, MIN_WEFT, MAX_WEFT);
        const out = new Array(f);
        for (let i = 0; i < f; i++) {
            out[i] = new Array(p).fill(false);
        }
        return out;
    }

    /** Boş iroData: weftCount uzunluğunda, hepsi 1 */
    function buildEmptyIroData(weftCount) {
        const p = clamp(weftCount, MIN_WEFT, MAX_WEFT);
        return new Array(p).fill(1);
    }

    /** Default DesenState — 6×6×6×1, raporX/Y=2 */
    function defaultDesen() {
        return {
            warpCount: 6,
            weftCount: 6,
            frameCount: 6,
            iroCount: 1,
            raporX: 2,
            raporY: 2,
            tahar: buildDuzTahar(6, 6),
            armur: buildEmptyArmur(6, 6),
            iroData: buildEmptyIroData(6),
            loops: []
        };
    }

    // === Çekirdek hesap ===

    /**
     * Desen matrisi: DESEN[warp][weft] = ARMUR[TAHAR[warp]][weft]
     * @param {number[]} tahar
     * @param {boolean[][]} armur
     * @param {number} weftCount
     * @returns {boolean[][]}
     */
    function computeDesen(tahar, armur, weftCount) {
        const wc = (tahar && tahar.length) || 0;
        const result = new Array(wc);
        for (let w = 0; w < wc; w++) {
            const f = tahar[w];
            const src = (f != null && armur && armur[f]) ? armur[f] : undefined;
            const row = new Array(weftCount);
            for (let p = 0; p < weftCount; p++) {
                row[p] = Boolean(src && src[p]);
            }
            result[w] = row;
        }
        return result;
    }

    // === Resize / Clamp helpers ===

    /** Tahar resize: kısa → kes, uzun → 0 ile doldur */
    function resizeTahar(tahar, newWarpCount) {
        const n = clamp(newWarpCount, MIN_WARP, MAX_WARP);
        const out = new Array(n);
        for (let i = 0; i < n; i++) {
            out[i] = (i < tahar.length) ? tahar[i] : 0;
        }
        return out;
    }

    /** Armür resize: eski hücreleri koru, yeni alanlar false */
    function resizeArmur(armur, newFrameCount, newWeftCount) {
        const fNew = clamp(newFrameCount, MIN_FRAME, MAX_FRAME);
        const pNew = clamp(newWeftCount, MIN_WEFT, MAX_WEFT);
        const out = new Array(fNew);
        for (let f = 0; f < fNew; f++) {
            const oldRow = (f < armur.length) ? armur[f] : null;
            const row = new Array(pNew);
            for (let p = 0; p < pNew; p++) {
                row[p] = (oldRow && p < oldRow.length) ? Boolean(oldRow[p]) : false;
            }
            out[f] = row;
        }
        return out;
    }

    /** İroData resize: kısa → kes, uzun → 1 ile doldur */
    function resizeIroData(iroData, newWeftCount) {
        const n = clamp(newWeftCount, MIN_WEFT, MAX_WEFT);
        const out = new Array(n);
        for (let i = 0; i < n; i++) {
            out[i] = (i < iroData.length) ? iroData[i] : 1;
        }
        return out;
    }

    /** Tahar clamp: frame index ≥ newFrameCount → 0 */
    function clampTahar(tahar, newFrameCount) {
        const f = clamp(newFrameCount, MIN_FRAME, MAX_FRAME);
        return tahar.map(v => (v >= 0 && v < f) ? v : 0);
    }

    /** İroData clamp: 1..newIroCount dışındakileri 1'e indir */
    function clampIroData(iroData, newIroCount) {
        const ic = clamp(newIroCount, MIN_IRO, MAX_IRO);
        return iroData.map(v => (v >= 1 && v <= ic) ? v : 1);
    }

    // === setDimension — tek noktadan boyut değişikliği ===

    /**
     * @param {DesenState} d
     * @param {"warpCount"|"weftCount"|"frameCount"|"iroCount"|"raporX"|"raporY"} dim
     * @param {number} value
     * @returns {DesenState} yeni state
     */
    function setDimension(d, dim, value) {
        // raporX / raporY → sadece görsel
        if (dim === 'raporX' || dim === 'raporY') {
            return { ...d, [dim]: clamp(value, MIN_RAPOR, MAX_RAPOR) };
        }

        if (dim === 'warpCount') {
            const newW = clamp(value, MIN_WARP, MAX_WARP);
            return {
                ...d,
                warpCount: newW,
                tahar: clampTahar(resizeTahar(d.tahar, newW), d.frameCount)
            };
        }

        if (dim === 'weftCount') {
            const newP = clamp(value, MIN_WEFT, MAX_WEFT);
            return {
                ...d,
                weftCount: newP,
                armur: resizeArmur(d.armur, d.frameCount, newP),
                iroData: clampIroData(resizeIroData(d.iroData, newP), d.iroCount),
                loops: pruneLoops(d.loops, newP)
            };
        }

        if (dim === 'frameCount') {
            const newF = clamp(value, MIN_FRAME, MAX_FRAME);
            return {
                ...d,
                frameCount: newF,
                armur: resizeArmur(d.armur, newF, d.weftCount),
                tahar: clampTahar(d.tahar, newF)
            };
        }

        if (dim === 'iroCount') {
            const newI = clamp(value, MIN_IRO, MAX_IRO);
            return {
                ...d,
                iroCount: newI,
                iroData: clampIroData(d.iroData, newI)
            };
        }

        return d;
    }

    // === Loop helpers ===

    /** İki loop çakışıyor mu? */
    function loopsOverlap(a, b) {
        return !(a.endPick < b.startPick || b.endPick < a.startPick);
    }

    /**
     * Loop'ları geçerli tutar:
     *   - startPick ≥ 0
     *   - endPick < weftCount
     *   - endPick - startPick ≥ 2 (en az 1 pattern atkı arada)
     *   - count ≥ MIN_LOOP_COUNT
     * startPick'e göre artan sırada döner.
     */
    function pruneLoops(loops, weftCount) {
        if (!Array.isArray(loops)) return [];
        return loops
            .filter(l =>
                l &&
                Number.isInteger(l.startPick) && l.startPick >= 0 &&
                Number.isInteger(l.endPick) && l.endPick < weftCount &&
                (l.endPick - l.startPick) >= 2 &&
                Number.isInteger(l.count) && l.count >= MIN_LOOP_COUNT
            )
            .map(l => ({
                startPick: l.startPick,
                endPick: l.endPick,
                count: clamp(l.count, MIN_LOOP_COUNT, MAX_LOOP_COUNT)
            }))
            .sort((a, b) => a.startPick - b.startPick);
    }

    /**
     * Yeni loop ekleme öncesi validasyon — null = geçerli, string = Türkçe hata
     * @returns {string | null}
     */
    function validateLoop(existing, loop, weftCount) {
        if (!loop ||
            !Number.isFinite(loop.startPick) ||
            !Number.isFinite(loop.endPick) ||
            !Number.isFinite(loop.count)) {
            return "Tüm alanları doldur";
        }
        if (loop.startPick < 0 || loop.endPick >= weftCount ||
            loop.startPick >= weftCount || loop.endPick < 0) {
            return `Atkı 1-${weftCount} aralığında olmalı`;
        }
        if (loop.endPick - loop.startPick < 2) {
            return "DO ve NEXT arasında en az 1 atkı olmalı";
        }
        if (loop.count < MIN_LOOP_COUNT || loop.count > MAX_LOOP_COUNT) {
            return `Tekrar ${MIN_LOOP_COUNT}-${MAX_LOOP_COUNT} arası olmalı`;
        }
        // Çakışma kontrolü
        for (const ex of (existing || [])) {
            if (loopsOverlap(ex, loop)) {
                return `Atkı ${ex.startPick + 1}-${ex.endPick + 1} döngüsü ile çakışıyor`;
            }
        }
        return null;
    }

    /** Loop ekle (sıralı insert). Geçerlilik çağıran tarafa ait — validateLoop önce çağrılmalı. */
    function addLoop(d, loop) {
        const newLoops = [...(d.loops || []), {
            startPick: loop.startPick,
            endPick: loop.endPick,
            count: clamp(loop.count, MIN_LOOP_COUNT, MAX_LOOP_COUNT)
        }].sort((a, b) => a.startPick - b.startPick);
        return { ...d, loops: newLoops };
    }

    /** Loop sil (idx ile) */
    function removeLoopAt(d, idx) {
        const loops = (d.loops || []).filter((_, i) => i !== idx);
        return { ...d, loops };
    }

    /** Loop count güncelle */
    function updateLoopCount(d, idx, newCount) {
        const loops = (d.loops || []).map((l, i) =>
            i === idx
                ? { ...l, count: clamp(newCount, MIN_LOOP_COUNT, MAX_LOOP_COUNT) }
                : l
        );
        return { ...d, loops };
    }

    /** Tüm loop'ları temizle */
    function clearLoops(d) {
        return { ...d, loops: [] };
    }

    // === Marker map + Expand ===

    /**
     * pickIdx → MarkerInfo. UI'da satırın marker olup olmadığını O(1) kontrol için.
     * @returns {Map<number, MarkerInfo>}
     */
    function buildMarkerMap(loops) {
        const map = new Map();
        (loops || []).forEach(loop => {
            map.set(loop.startPick, { kind: 'DO', count: loop.count, loop });
            map.set(loop.endPick, { kind: 'NEXT', loop });
        });
        return map;
    }

    /**
     * Loop'ları açarak gerçek dokuma sırasını döndürür.
     * Marker satırlar atlanır, aradaki pattern atkıları `count` kez tekrar eder.
     * @param {DesenState} state
     * @returns {number[]} dokunacak orijinal pick indeksleri (0-based)
     */
    function expandPicks(state) {
        const loops = pruneLoops(state.loops || [], state.weftCount);
        const startMap = new Map(loops.map(l => [l.startPick, l]));
        const result = [];
        let p = 0;
        while (p < state.weftCount) {
            const loop = startMap.get(p);
            if (loop) {
                // Marker atla, pattern (startPick+1 .. endPick-1) count kez tekrar
                for (let r = 0; r < loop.count; r++) {
                    for (let q = loop.startPick + 1; q <= loop.endPick - 1; q++) {
                        result.push(q);
                    }
                }
                p = loop.endPick + 1;
            } else {
                result.push(p);
                p++;
            }
        }
        return result;
    }

    // === Satır insert / delete (loops birlikte kayar) ===

    /**
     * Belirtilen pickIdx üstüne boş satır ekler.
     * Loops kayma kuralları:
     *   - i ≤ startPick → loop tamamen kayar (+1)
     *   - startPick < i ≤ endPick → loop genişler (endPick++)
     *   - i > endPick → loop dokunulmaz
     */
    function insertRow(d, atPickIdx) {
        if (d.weftCount >= MAX_WEFT) return d;
        const newWeftCount = d.weftCount + 1;
        const idx = clamp(atPickIdx, 0, d.weftCount);

        // Armür her satıra (frame için) idx pozisyonuna false ekle
        const newArmur = d.armur.map(row => {
            const out = row.slice();
            out.splice(idx, 0, false);
            return out;
        });

        // İroData'ya idx pozisyonuna 1 ekle
        const newIroData = d.iroData.slice();
        newIroData.splice(idx, 0, 1);

        // Loops kaydır
        const newLoops = (d.loops || []).map(loop => {
            if (idx <= loop.startPick) {
                return { ...loop, startPick: loop.startPick + 1, endPick: loop.endPick + 1 };
            }
            if (idx <= loop.endPick) {
                return { ...loop, endPick: loop.endPick + 1 };
            }
            return loop;
        });

        return {
            ...d,
            weftCount: newWeftCount,
            armur: newArmur,
            iroData: newIroData,
            loops: pruneLoops(newLoops, newWeftCount)
        };
    }

    /**
     * Satır sil. Kurallar:
     *   - weftCount > MIN_WEFT olmalı
     *   - Marker satırı silinirse o döngü tamamen kalkar
     *   - Loop içi pattern silinirse loop daralır (endPick--).
     *     endPick - startPick < 2 olursa loop kalkar.
     *   - Loop dışı satır silinirse sonraki loop'lar 1 birim öne kayar.
     */
    function deleteRow(d, pickIdx) {
        if (d.weftCount <= MIN_WEFT) return d;
        const idx = clamp(pickIdx, 0, d.weftCount - 1);
        const newWeftCount = d.weftCount - 1;

        // Armür her satırdan idx pozisyonu kaldır
        const newArmur = d.armur.map(row => {
            const out = row.slice();
            out.splice(idx, 1);
            return out;
        });

        // İroData'dan idx pozisyonu kaldır
        const newIroData = d.iroData.slice();
        newIroData.splice(idx, 1);

        // Loops kayma:
        const newLoops = [];
        for (const loop of (d.loops || [])) {
            // Marker satırı (start veya end) siliniyorsa loop tamamen kaldır
            if (idx === loop.startPick || idx === loop.endPick) {
                continue;
            }
            if (idx < loop.startPick) {
                // Loop tamamen kayar
                newLoops.push({
                    ...loop,
                    startPick: loop.startPick - 1,
                    endPick: loop.endPick - 1
                });
            } else if (idx < loop.endPick) {
                // Loop daralır
                const newEnd = loop.endPick - 1;
                if (newEnd - loop.startPick >= 2) {
                    newLoops.push({ ...loop, endPick: newEnd });
                }
                // Aksi takdirde loop kaldırıldı
            } else {
                // idx > loop.endPick → dokunulmaz
                newLoops.push(loop);
            }
        }

        return {
            ...d,
            weftCount: newWeftCount,
            armur: newArmur,
            iroData: newIroData,
            loops: pruneLoops(newLoops, newWeftCount)
        };
    }

    // === Normalize (load için backward-compat) ===

    /**
     * Eski/yarım kayıtları geçerli DesenState'e tamamlar.
     * d null/undefined ise defaultDesen() döner.
     */
    function normalizeDesen(d) {
        if (!d || typeof d !== 'object') return defaultDesen();

        const base = defaultDesen();
        // Yardımcı: değer geçerli sayı ise clamp, değilse fallback kullan
        const numOr = (v, min, max, fallback) => {
            if (v == null || !isFinite(Number(v))) return fallback;
            return clamp(v, min, max);
        };
        const out = {
            warpCount:  numOr(d.warpCount,  MIN_WARP,  MAX_WARP,  base.warpCount),
            weftCount:  numOr(d.weftCount,  MIN_WEFT,  MAX_WEFT,  base.weftCount),
            frameCount: numOr(d.frameCount, MIN_FRAME, MAX_FRAME, base.frameCount),
            iroCount:   numOr(d.iroCount,   MIN_IRO,   MAX_IRO,   base.iroCount),
            raporX:     numOr(d.raporX,     MIN_RAPOR, MAX_RAPOR, base.raporX),
            raporY:     numOr(d.raporY,     MIN_RAPOR, MAX_RAPOR, base.raporY),
            tahar: Array.isArray(d.tahar) ? d.tahar.slice() : null,
            armur: Array.isArray(d.armur) ? d.armur.map(r => Array.isArray(r) ? r.slice() : []) : null,
            iroData: Array.isArray(d.iroData) ? d.iroData.slice() : null,
            loops: Array.isArray(d.loops) ? d.loops.slice() : []
        };

        // Tahar boyutu warpCount'a uyumlu olsun
        if (!out.tahar || out.tahar.length !== out.warpCount) {
            out.tahar = out.tahar
                ? clampTahar(resizeTahar(out.tahar, out.warpCount), out.frameCount)
                : buildDuzTahar(out.warpCount, out.frameCount);
        } else {
            out.tahar = clampTahar(out.tahar, out.frameCount);
        }

        // Armür boyutu frame × weft uyumlu olsun
        if (!out.armur || out.armur.length !== out.frameCount ||
            (out.armur[0] && out.armur[0].length !== out.weftCount)) {
            out.armur = out.armur
                ? resizeArmur(out.armur, out.frameCount, out.weftCount)
                : buildEmptyArmur(out.frameCount, out.weftCount);
        }

        // İroData uzunluğu weftCount uyumlu olsun
        if (!out.iroData || out.iroData.length !== out.weftCount) {
            out.iroData = out.iroData
                ? clampIroData(resizeIroData(out.iroData, out.weftCount), out.iroCount)
                : buildEmptyIroData(out.weftCount);
        } else {
            out.iroData = clampIroData(out.iroData, out.iroCount);
        }

        // Loops prune
        out.loops = pruneLoops(out.loops, out.weftCount);

        return out;
    }

    // === Export — window.DesenCore ===
    window.DesenCore = {
        // Sabitler
        MIN_WARP, MAX_WARP, MIN_WEFT, MAX_WEFT,
        MIN_FRAME, MAX_FRAME, MIN_IRO, MAX_IRO,
        MIN_LOOP_COUNT, MAX_LOOP_COUNT,
        MIN_RAPOR, MAX_RAPOR,
        IRO_COLORS,

        // Builders
        defaultDesen,
        buildDuzTahar,
        buildEmptyArmur,
        buildEmptyIroData,

        // Çekirdek
        computeDesen,

        // Resize / Clamp
        resizeTahar, resizeArmur, resizeIroData,
        clampTahar, clampIroData,

        // setDimension
        setDimension,

        // Loop helpers
        loopsOverlap, pruneLoops, validateLoop,
        addLoop, removeLoopAt, updateLoopCount, clearLoops,
        buildMarkerMap, expandPicks,

        // Row ops
        insertRow, deleteRow,

        // Normalize
        normalizeDesen
    };
})();
