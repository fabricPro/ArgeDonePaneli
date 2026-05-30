import type { TarakState } from "./types";

// Sinirlar
export const MIN_SIKLIK = 0.1;
export const MAX_SIKLIK = 500;
export const MIN_DIS = 1;
export const MAX_DIS = 999;

/** Yardımcı: string'i number'a çevir, geçersizse fallback (default 0). */
export function parseN(v: string | number | undefined, fallback = 0): number {
  if (typeof v === "number") return Number.isFinite(v) ? v : fallback;
  if (!v) return fallback;
  const n = parseFloat(v.replace(",", "."));
  return Number.isFinite(n) ? n : fallback;
}

/** Tarak hesap özeti — UI istatistik kartlarını ve raporu besler. */
export interface TarakSummary {
  /** Tarak sıklığı (diş/cm) — sayısal */
  siklik: number;
  /** Rapor diş sayısı — sayısal (dentThreads.length ile eşleşir) */
  dis: number;
  /** Toplam tel (dentThreads toplamı) */
  toplamTel: number;
  /** Ortalama tel/diş — dis === 0 ise 0 */
  ortTelDis: number;
  /** Çözgü sıklığı (tel/cm) = siklik × ortTelDis */
  cozguSiklik: number;
  /** Rapor cm = dis / siklik */
  raporCm: number;
}

export function calcTarakSummary(t: TarakState): TarakSummary {
  const siklik = parseN(t.siklik);
  const dis = t.dentThreads.length;
  const toplamTel = t.dentThreads.reduce((a, b) => a + b, 0);
  const ortTelDis = dis > 0 ? toplamTel / dis : 0;
  const cozguSiklik = siklik > 0 && dis > 0 ? siklik * ortTelDis : 0;
  const raporCm = siklik > 0 && dis > 0 ? dis / siklik : 0;
  return { siklik, dis, toplamTel, ortTelDis, cozguSiklik, raporCm };
}

/** Mod hint metni — UI'da girilen değerlerin tersine çevirisini gösterir. */
export function calcHint(t: TarakState): { from: string; to: string } | null {
  const siklik = parseN(t.siklik);
  if (siklik <= 0) return null;
  if (t.mode === "dis") {
    const d = parseN(t.raporDis);
    if (d <= 0) return null;
    const cm = d / siklik;
    return { from: `${d} diş ÷ ${siklik} diş/cm`, to: `rapor ${cm.toFixed(4)} cm` };
  } else {
    const cm = parseN(t.raporCm);
    if (cm <= 0) return null;
    const d = Math.round(siklik * cm);
    return { from: `${siklik} × ${cm} cm`, to: `${d} diş` };
  }
}

/** Mod değişikliğinden, rapor input'undan veya sıklık değişiminden sonra
 *  dentThreads dizisinin uzunluğunu hedef diş sayısına eşitler — mevcut veriyi korur. */
export function syncDentThreads(t: TarakState): TarakState {
  let target: number;
  if (t.mode === "dis") {
    target = Math.max(0, Math.round(parseN(t.raporDis)));
  } else {
    const siklik = parseN(t.siklik);
    const cm = parseN(t.raporCm);
    target = siklik > 0 && cm > 0 ? Math.max(0, Math.round(siklik * cm)) : 0;
  }
  if (target === t.dentThreads.length) return t;
  const next = new Array<number>(target).fill(0);
  for (let i = 0; i < Math.min(t.dentThreads.length, target); i++) {
    next[i] = t.dentThreads[i];
  }
  // cm modunda raporDis'i de güncel tut (UI'ın source of truth'u dis kalmalı)
  if (t.mode === "cm") {
    return { ...t, dentThreads: next, raporDis: String(target) };
  }
  return { ...t, dentThreads: next };
}

/** Bir dişe tel ekle / çıkar */
export function incThread(t: TarakState, i: number, delta: number): TarakState {
  if (i < 0 || i >= t.dentThreads.length) return t;
  const v = Math.max(0, t.dentThreads[i] + delta);
  if (v === t.dentThreads[i]) return t;
  const next = t.dentThreads.slice();
  next[i] = v;
  return { ...t, dentThreads: next };
}

/** Tüm dişleri sıfırla */
export function resetThreads(t: TarakState): TarakState {
  return { ...t, dentThreads: new Array<number>(t.dentThreads.length).fill(0) };
}

/** Run-length encoding — ardışık aynı tel sayısı olan dişleri grupla.
 *  Raporun "5 diş × 2 tel = 10 tel" satırlarını üretir. */
export interface RleGroup {
  dis: number;
  tel: number;
  start: number;
}

export function rle(threads: number[]): RleGroup[] {
  const out: RleGroup[] = [];
  let i = 0;
  while (i < threads.length) {
    const v = threads[i];
    let c = 1;
    while (i + c < threads.length && threads[i + c] === v) c++;
    out.push({ dis: c, tel: v, start: i });
    i += c;
  }
  return out;
}

/** RLE'yi compact tekst formatına çevirir — clipboard'a kopyalama için.
 *  Örnek: "4×3 · 24×2 · 4×0 · 24×2 · 4×3" */
export function rleToText(threads: number[]): string {
  return rle(threads)
    .map((g) => `${g.dis}×${g.tel}`)
    .join(" · ");
}

/** Default state — yeni numune açılırken kullanılır. */
export function defaultTarak(): TarakState {
  return {
    siklik: "",
    raporDis: "",
    mode: "dis",
    raporCm: "",
    dentThreads: [],
  };
}

/** Eski kayıtlardan yüklenen TarakState'i normalize eder (yoksa default). */
export function normalizeTarak(t: TarakState | undefined): TarakState {
  if (!t) return defaultTarak();
  return {
    siklik: t.siklik ?? "",
    raporDis: t.raporDis ?? "",
    mode: t.mode === "cm" ? "cm" : "dis",
    raporCm: t.raporCm ?? "",
    dentThreads: Array.isArray(t.dentThreads) ? t.dentThreads.map((n) => Math.max(0, n | 0)) : [],
  };
}
