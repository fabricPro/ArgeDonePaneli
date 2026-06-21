/* v4.0-part-2 Adım 4 Faz A — Tarak Modülü saf fonksiyonlar (vanilla JS port)
 *
 * NumuneAtilim Tarak Modülü spec'inin port'u. React/TypeScript yerine
 * JSDoc tip yorumları + IIFE export pattern (Desen modülü ile aynı yaklaşım).
 *
 * Tüm fonksiyonlar PURE — input mutate etmez, yeni TarakState döner (immutable).
 *
 * Kullanım:
 *   const t = TarakCore.defaultTarak();
 *   const t2 = TarakCore.syncDentThreads({...t, siklik:"8", raporDis:"32"});
 *   const summary = TarakCore.calcTarakSummary(t2);
 *
 * Domain:
 *   - Tarak (reed): dokuma tezgahında çözgüleri hizalayan tarak
 *   - Sıklık (diş/cm): tarak sıklığı
 *   - Diş (dent): tarağın tek aralığı
 *   - Tel (thread): bir dişten geçen çözgü teli sayısı
 *   - Rapor: tekrarlayan diş dizimi (diş sayısı veya cm)
 *   - RLE: ardışık aynı tel sayısına sahip dişleri grupla
 *
 * @typedef {Object} TarakState
 * @property {string} siklik     - Tarak sıklığı (diş/cm), string format
 * @property {string} raporDis   - Rapor diş sayısı (UI source of truth)
 * @property {"dis"|"cm"} mode   - Hangi alan düzenleniyor
 * @property {string} raporCm    - cm modunda manuel girilen rapor cm
 * @property {number[]} dentThreads - Her dişe geçen tel sayısı (uzunluk == raporDis)
 *
 * @typedef {Object} TarakSummary
 * @property {number} siklik
 * @property {number} dis
 * @property {number} toplamTel
 * @property {number} ortTelDis
 * @property {number} cozguSiklik
 * @property {number} raporCm
 *
 * @typedef {Object} RleGroup
 * @property {number} dis    - bu gruptaki ardışık diş sayısı
 * @property {number} tel    - bu gruptaki her dişin tel sayısı
 * @property {number} start  - ilk dişin 0-based indeksi
 */

(function () {
    "use strict";

    // === Sabitler ===
    const MIN_SIKLIK = 0.1;
    const MAX_SIKLIK = 500;
    const MIN_DIS = 1;
    const MAX_DIS = 999;

    // === Helpers ===
    function clamp(v, min, max) {
        const n = Number(v);
        if (!isFinite(n)) return min;
        return Math.max(min, Math.min(max, n));
    }

    /**
     * String → number (virgül noktaya, geçersizse fallback)
     * @param {string|number|undefined} v
     * @param {number} [fallback=0]
     * @returns {number}
     */
    function parseN(v, fallback) {
        if (fallback == null) fallback = 0;
        if (v == null || v === '') return fallback;
        const s = String(v).trim().replace(',', '.');
        const n = parseFloat(s);
        return isFinite(n) ? n : fallback;
    }

    // === Default ===
    function defaultTarak() {
        return {
            siklik: "",
            raporDis: "",
            mode: "dis",
            raporCm: "",
            dentThreads: []
        };
    }

    // === Hesap özeti ===
    /**
     * @param {TarakState} t
     * @returns {TarakSummary}
     */
    function calcTarakSummary(t) {
        const siklik = parseN(t && t.siklik, 0);
        const threads = (t && Array.isArray(t.dentThreads)) ? t.dentThreads : [];
        const dis = threads.length;
        let toplamTel = 0;
        for (let i = 0; i < dis; i++) {
            const v = threads[i];
            if (typeof v === 'number' && isFinite(v) && v > 0) toplamTel += v;
        }
        const ortTelDis = dis > 0 ? toplamTel / dis : 0;
        const cozguSiklik = siklik * ortTelDis;
        const raporCm = siklik > 0 ? dis / siklik : 0;
        return {
            siklik,
            dis,
            toplamTel,
            ortTelDis,
            cozguSiklik,
            raporCm
        };
    }

    // === Mod hint ===
    /**
     * Kullanıcının girdiğinin tersini hesaplar (UI alt yazısı için)
     * @param {TarakState} t
     * @returns {{from:string, to:string} | null}
     */
    function calcHint(t) {
        const siklik = parseN(t && t.siklik, 0);
        if (siklik <= 0) return null;
        if (t.mode === 'manuel') {
            // Diş diş kurulur; uzunluk = dentThreads. Rapor cm bundan türetilir.
            const dis = (t && Array.isArray(t.dentThreads)) ? t.dentThreads.length : 0;
            if (dis <= 0) return null;
            const cm = dis / siklik;
            return { from: `${dis} diş ÷ ${siklik} diş/cm`, to: `rapor ${cm.toFixed(4)} cm` };
        }
        if (t.mode === 'dis') {
            const dis = parseN(t.raporDis, 0);
            if (dis <= 0) return null;
            const cm = dis / siklik;
            return {
                from: `${dis} diş ÷ ${siklik} diş/cm`,
                to: `rapor ${cm.toFixed(4)} cm`
            };
        } else {
            const cm = parseN(t.raporCm, 0);
            if (cm <= 0) return null;
            const dis = Math.round(siklik * cm);
            return {
                from: `${siklik} × ${cm} cm`,
                to: `${dis} diş`
            };
        }
    }

    // === dentThreads senkronizasyonu ===
    /**
     * Mode/siklik/rapor değişiminden sonra dentThreads uzunluğunu hedefe eşitler.
     * cm modunda raporDis de güncel tutulur (source of truth = dis).
     * Idempotent: zaten doğruysa state'i değiştirmez.
     *
     * @param {TarakState} t
     * @returns {TarakState}
     */
    function syncDentThreads(t) {
        if (!t) return defaultTarak();
        let target = 0;
        const siklik = parseN(t.siklik, 0);

        const current0 = Array.isArray(t.dentThreads) ? t.dentThreads : [];
        if (t.mode === 'manuel') {
            // Manuel: uzunluk DIŞARIDAN belirlenmez; dentThreads kullanıcının kurduğu kadar (addDent/removeDent ile).
            target = current0.length;
        } else if (t.mode === 'cm') {
            const cm = parseN(t.raporCm, 0);
            if (siklik > 0 && cm > 0) {
                target = Math.round(siklik * cm);
            }
        } else {
            target = Math.round(parseN(t.raporDis, 0));
        }

        // Clamp to safe range
        if (target < 0) target = 0;
        if (target > MAX_DIS) target = MAX_DIS;

        const current = current0;
        let newThreads = current;
        if (current.length !== target) {
            newThreads = new Array(target);
            for (let i = 0; i < target; i++) {
                newThreads[i] = (i < current.length && typeof current[i] === 'number' && current[i] >= 0)
                    ? current[i] : 0;
            }
        }

        // cm/manuel modunda raporDis'i diş sayısına eşitle (string)
        const newRaporDis = ((t.mode === 'cm' && target > 0) || t.mode === 'manuel') ? String(target) : t.raporDis;

        // Idempotent check — referans eşitliği
        if (newThreads === current && newRaporDis === t.raporDis) {
            return t;
        }

        return {
            ...t,
            dentThreads: newThreads,
            raporDis: newRaporDis
        };
    }

    // === Diş düzenleme ===
    /**
     * Bir dişin tel sayısını delta kadar değiştir (clamp >= 0)
     * @param {TarakState} t
     * @param {number} i - diş indeksi (0-based)
     * @param {number} delta
     * @returns {TarakState}
     */
    function incThread(t, i, delta) {
        if (!t || !Array.isArray(t.dentThreads)) return t;
        if (i < 0 || i >= t.dentThreads.length) return t;
        const cur = t.dentThreads[i] || 0;
        const next = Math.max(0, cur + delta);
        if (next === cur) return t;
        const newThreads = t.dentThreads.slice();
        newThreads[i] = next;
        return { ...t, dentThreads: newThreads };
    }

    /**
     * Tüm dişleri 0'la (uzunluk korunur)
     * @param {TarakState} t
     * @returns {TarakState}
     */
    function resetThreads(t) {
        if (!t || !Array.isArray(t.dentThreads)) return t;
        const n = t.dentThreads.length;
        return { ...t, dentThreads: new Array(n).fill(0) };
    }

    /**
     * Manuel mod — sona yeni boş diş (0 tel) ekle. raporDis diş sayısına eşitlenir. MAX_DIS sınırı.
     * @param {TarakState} t
     * @returns {TarakState}
     */
    function addDent(t) {
        if (!t) return defaultTarak();
        const cur = Array.isArray(t.dentThreads) ? t.dentThreads : [];
        if (cur.length >= MAX_DIS) return t;
        const newThreads = cur.concat(0);
        return { ...t, dentThreads: newThreads, raporDis: String(newThreads.length) };
    }

    /**
     * Manuel mod — bir dişi sil (i verilmezse SON diş). raporDis güncellenir.
     * @param {TarakState} t
     * @param {number} [i]
     * @returns {TarakState}
     */
    function removeDent(t, i) {
        if (!t || !Array.isArray(t.dentThreads) || t.dentThreads.length === 0) return t;
        const idx = (typeof i === 'number' && i >= 0 && i < t.dentThreads.length)
            ? i : (t.dentThreads.length - 1);
        const newThreads = t.dentThreads.slice();
        newThreads.splice(idx, 1);
        return { ...t, dentThreads: newThreads, raporDis: String(newThreads.length) };
    }

    // === RLE ===
    /**
     * Ardışık aynı tel sayısına sahip dişleri grupla
     * @param {number[]} threads
     * @returns {RleGroup[]}
     */
    function rle(threads) {
        if (!Array.isArray(threads) || threads.length === 0) return [];
        const groups = [];
        let curTel = threads[0];
        let curDis = 1;
        let curStart = 0;
        for (let i = 1; i < threads.length; i++) {
            if (threads[i] === curTel) {
                curDis++;
            } else {
                groups.push({ dis: curDis, tel: curTel, start: curStart });
                curTel = threads[i];
                curDis = 1;
                curStart = i;
            }
        }
        groups.push({ dis: curDis, tel: curTel, start: curStart });
        return groups;
    }

    /**
     * RLE'yi compact text formatına çevir
     * @param {number[]} threads
     * @returns {string} "4×3 · 24×2 · 4×0 · 24×2 · 4×3"
     */
    function rleToText(threads) {
        return rle(threads).map(g => `${g.dis}×${g.tel}`).join(' · ');
    }

    // === Normalize (load için backward-compat) ===
    /**
     * Eski/yarım kayıtları geçerli TarakState'e tamamlar.
     * t null/undefined ise defaultTarak() döner.
     * @param {TarakState|null|undefined} t
     * @returns {TarakState}
     */
    function normalizeTarak(t) {
        if (!t || typeof t !== 'object') return defaultTarak();

        const out = {
            siklik:    typeof t.siklik === 'string' ? t.siklik : (typeof t.siklik === 'number' ? String(t.siklik) : ''),
            raporDis:  typeof t.raporDis === 'string' ? t.raporDis : (typeof t.raporDis === 'number' ? String(t.raporDis) : ''),
            mode:      (t.mode === 'cm' || t.mode === 'dis' || t.mode === 'manuel') ? t.mode : 'dis',
            raporCm:   typeof t.raporCm === 'string' ? t.raporCm : (typeof t.raporCm === 'number' ? String(t.raporCm) : ''),
            dentThreads: Array.isArray(t.dentThreads)
                ? t.dentThreads.map(v => {
                    const n = parseInt(v, 10);
                    return (isFinite(n) && n >= 0) ? n : 0;
                })
                : []
        };

        return out;
    }

    // === Export — window.TarakCore ===
    window.TarakCore = {
        // Sabitler
        MIN_SIKLIK, MAX_SIKLIK, MIN_DIS, MAX_DIS,

        // Helpers
        parseN,

        // Builders
        defaultTarak,

        // Hesap
        calcTarakSummary,
        calcHint,

        // State ops
        syncDentThreads,
        incThread,
        resetThreads,
        addDent,
        removeDent,

        // RLE
        rle,
        rleToText,

        // Normalize
        normalizeTarak
    };
})();
