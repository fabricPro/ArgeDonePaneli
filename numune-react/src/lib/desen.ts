import type { DesenState, LoopRange } from "./types";

// Sinirlar (ERP ile ayni)
export const MIN_WARP = 2;
export const MAX_WARP = 120;
export const MIN_WEFT = 2;
export const MAX_WEFT = 120;
export const MIN_FRAME = 2;
export const MAX_FRAME = 24;
export const MIN_IRO = 1;
export const MAX_IRO = 8;

// Atki motoru/renk paleti (8)
export const IRO_COLORS = [
  "#5b8def",
  "#f0a830",
  "#3fb6a8",
  "#36c98a",
  "#e6b94a",
  "#e8674f",
  "#a78bfa",
  "#ec4899",
];

/** DESEN[warp][weft] = ARMUR[ TAHAR[warp] ][ weft ] — tahar+armür'den hesaplanir. */
export function computeDesen(tahar: number[], armur: boolean[][], weftCount: number): boolean[][] {
  const warpCount = tahar.length;
  const result: boolean[][] = [];
  for (let w = 0; w < warpCount; w++) {
    const f = tahar[w];
    const row: boolean[] = [];
    const src = f != null ? armur[f] : undefined;
    for (let p = 0; p < weftCount; p++) row.push(Boolean(src?.[p]));
    result.push(row);
  }
  return result;
}

/** Düz tahar (0,1,2,... wrap-around) */
export function buildDuzTahar(warpCount: number, frameCount: number): number[] {
  return Array.from({ length: warpCount }, (_, i) => i % frameCount);
}

export function buildEmptyArmur(frameCount: number, weftCount: number): boolean[][] {
  return Array.from({ length: frameCount }, () =>
    Array.from({ length: weftCount }, () => false),
  );
}

export function buildEmptyIroData(weftCount: number): number[] {
  return Array.from({ length: weftCount }, () => 1);
}

export function resizeTahar(tahar: number[], newWarpCount: number): number[] {
  if (newWarpCount === tahar.length) return tahar;
  if (newWarpCount < tahar.length) return tahar.slice(0, newWarpCount);
  return [...tahar, ...Array<number>(newWarpCount - tahar.length).fill(0)];
}

export function resizeArmur(
  armur: boolean[][],
  newFrameCount: number,
  newWeftCount: number,
): boolean[][] {
  return Array.from({ length: newFrameCount }, (_, f) => {
    const oldRow = armur[f] ?? [];
    return Array.from({ length: newWeftCount }, (_, p) => Boolean(oldRow[p]));
  });
}

export function resizeIroData(iroData: number[], newWeftCount: number): number[] {
  if (newWeftCount === iroData.length) return iroData;
  if (newWeftCount < iroData.length) return iroData.slice(0, newWeftCount);
  return [...iroData, ...Array<number>(newWeftCount - iroData.length).fill(1)];
}

export function clampTahar(tahar: number[], newFrameCount: number): number[] {
  return tahar.map((f) => (f < newFrameCount ? f : 0));
}

export function clampIroData(iroData: number[], newIroCount: number): number[] {
  return iroData.map((v) => (v >= 1 && v <= newIroCount ? v : 1));
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

/** Bir boyutu degistir + bagimli dizileri tutarli tut. */
export function setDimension(
  d: DesenState,
  dim: "warpCount" | "weftCount" | "frameCount" | "iroCount",
  value: number,
): DesenState {
  const next = { ...d };
  if (dim === "warpCount") {
    next.warpCount = clamp(value, MIN_WARP, MAX_WARP);
    next.tahar = resizeTahar(d.tahar, next.warpCount);
  } else if (dim === "weftCount") {
    next.weftCount = clamp(value, MIN_WEFT, MAX_WEFT);
    next.armur = resizeArmur(d.armur, d.frameCount, next.weftCount);
    next.iroData = resizeIroData(d.iroData, next.weftCount);
    next.loops = pruneLoops(d.loops ?? [], next.weftCount);
  } else if (dim === "frameCount") {
    next.frameCount = clamp(value, MIN_FRAME, MAX_FRAME);
    next.armur = resizeArmur(d.armur, next.frameCount, d.weftCount);
    next.tahar = clampTahar(d.tahar, next.frameCount);
  } else {
    next.iroCount = clamp(value, MIN_IRO, MAX_IRO);
    next.iroData = clampIroData(d.iroData, next.iroCount);
  }
  return next;
}

export function defaultDesen(): DesenState {
  const warpCount = 6;
  const weftCount = 6;
  const frameCount = 6;
  const iroCount = 1;
  return {
    warpCount,
    weftCount,
    frameCount,
    iroCount,
    raporX: 2,
    raporY: 2,
    tahar: buildDuzTahar(warpCount, frameCount),
    armur: buildEmptyArmur(frameCount, weftCount),
    iroData: buildEmptyIroData(weftCount),
    loops: [],
  };
}

// ============================================================
// DO…NEXT döngüleri — v0.2'de eklendi
// ============================================================

/** Sınırlar */
export const MIN_LOOP_COUNT = 2;
export const MAX_LOOP_COUNT = 99;

/** İki döngü atkı aralığı bakımından çakışıyor mu? */
export function loopsOverlap(a: LoopRange, b: LoopRange): boolean {
  return !(a.endPick < b.startPick || b.endPick < a.startPick);
}

/** Geçersiz hale gelmiş döngüleri eler ve sıralı döndürür.
 *  Bir döngü geçerli sayılır: startPick ≥ 0, endPick < weftCount,
 *  araya en az 1 pattern atkı sığar (endPick - startPick ≥ 2), count ≥ 2. */
export function pruneLoops(loops: LoopRange[], weftCount: number): LoopRange[] {
  return loops
    .filter(
      (l) =>
        l.startPick >= 0 &&
        l.endPick < weftCount &&
        l.endPick - l.startPick >= 2 &&
        l.count >= MIN_LOOP_COUNT,
    )
    .sort((a, b) => a.startPick - b.startPick);
}

/** Yeni bir döngü eklenebilir mi? Hata mesajı veya null döner. */
export function validateLoop(
  existingLoops: LoopRange[],
  loop: LoopRange,
  weftCount: number,
): string | null {
  if (loop.startPick < 0 || loop.endPick >= weftCount)
    return `Atkı 1-${weftCount} aralığında olmalı`;
  if (loop.endPick - loop.startPick < 2) return "DO ve NEXT arasında en az 1 atkı olmalı";
  if (loop.count < MIN_LOOP_COUNT || loop.count > MAX_LOOP_COUNT)
    return `Tekrar ${MIN_LOOP_COUNT}-${MAX_LOOP_COUNT} arası olmalı`;
  for (const lp of existingLoops) {
    if (loopsOverlap(loop, lp))
      return `Atkı ${lp.startPick + 1}-${lp.endPick + 1} döngüsü ile çakışıyor`;
  }
  return null;
}

export function addLoop(s: DesenState, loop: LoopRange): DesenState {
  return {
    ...s,
    loops: [...(s.loops ?? []), loop].sort((a, b) => a.startPick - b.startPick),
  };
}

export function removeLoopAt(s: DesenState, idx: number): DesenState {
  return { ...s, loops: (s.loops ?? []).filter((_, i) => i !== idx) };
}

/** Bir döngünün tekrar sayısını (count) günceller. MIN/MAX arasında clamp. */
export function updateLoopCount(
  s: DesenState,
  idx: number,
  newCount: number,
): DesenState {
  const clamped = Math.max(
    MIN_LOOP_COUNT,
    Math.min(MAX_LOOP_COUNT, Math.round(newCount)),
  );
  return {
    ...s,
    loops: (s.loops ?? []).map((lp, i) =>
      i === idx ? { ...lp, count: clamped } : lp,
    ),
  };
}

export function clearLoops(s: DesenState): DesenState {
  return { ...s, loops: [] };
}

/** pickIdx → { kind:'DO'|'NEXT', loop } eşlemesi. Marker satırı kontrolünde kullanılır. */
export type MarkerInfo =
  | { kind: "DO"; count: number; loop: LoopRange }
  | { kind: "NEXT"; loop: LoopRange };

export function buildMarkerMap(loops: LoopRange[]): Map<number, MarkerInfo> {
  const m = new Map<number, MarkerInfo>();
  for (const lp of loops) {
    m.set(lp.startPick, { kind: "DO", count: lp.count, loop: lp });
    m.set(lp.endPick, { kind: "NEXT", loop: lp });
  }
  return m;
}

/** Döngüleri açar: marker satırlar (DO/NEXT) atlanır, aradaki pattern atkıları
 *  N kez tekrar eder. Sonuç: gerçekte dokunacak orijinal pick indeksleri dizisi. */
export function expandPicks(s: DesenState): number[] {
  const result: number[] = [];
  const loops = pruneLoops(s.loops ?? [], s.weftCount);
  let p = 0;
  let li = 0;
  while (p < s.weftCount) {
    if (li < loops.length && p === loops[li].startPick) {
      const lp = loops[li];
      for (let r = 0; r < lp.count; r++) {
        for (let q = lp.startPick + 1; q < lp.endPick; q++) result.push(q);
      }
      p = lp.endPick + 1;
      li++;
    } else {
      result.push(p);
      p++;
    }
  }
  return result;
}

// ============================================================
// Satır ekle / sil — armür + iroData + loops birlikte güncellenir
// ============================================================

/** Belirtilen pick indeksindeki satırı siler.
 *  - Marker satırı silinirse o döngü tamamen kalkar.
 *  - Loop içinden pattern satırı silinirse loop daralır (en az 1 pattern kalmalı, yoksa loop kalkar).
 *  - Loop dışı satır silinirse sonraki loop'lar 1 birim öne kayar. */
export function deleteRow(s: DesenState, d: number): DesenState {
  if (s.weftCount <= MIN_WEFT) return s;
  if (d < 0 || d >= s.weftCount) return s;

  const newArmur = s.armur.map((row) => row.filter((_, i) => i !== d));
  const newIro = s.iroData.filter((_, i) => i !== d);

  const newLoops: LoopRange[] = [];
  for (const lp of s.loops ?? []) {
    if (d === lp.startPick || d === lp.endPick) continue; // marker → loop kalkar
    let startPick = lp.startPick;
    let endPick = lp.endPick;
    if (d < startPick) {
      startPick--;
      endPick--;
    } else if (d > startPick && d < endPick) {
      endPick--;
    }
    if (endPick - startPick >= 2) {
      newLoops.push({ startPick, endPick, count: lp.count });
    }
  }

  return {
    ...s,
    weftCount: s.weftCount - 1,
    armur: newArmur,
    iroData: newIro,
    loops: newLoops,
  };
}

/** Belirtilen pick indeksine boş satır ekler (0..weftCount).
 *  Yeni satır pick=i olur, eski pick i ve sonrası bir üst pick'e kayar.
 *  Loop'lar otomatik genişler veya kayar. */
export function insertRow(s: DesenState, i: number): DesenState {
  if (s.weftCount >= MAX_WEFT) return s;
  if (i < 0 || i > s.weftCount) return s;

  const newArmur = s.armur.map((row) => {
    const r = row.slice();
    r.splice(i, 0, false);
    return r;
  });
  const newIro = s.iroData.slice();
  newIro.splice(i, 0, 1);

  const newLoops = (s.loops ?? []).map((lp) => {
    let startPick = lp.startPick;
    let endPick = lp.endPick;
    if (i <= startPick) {
      startPick++;
      endPick++;
    } else if (i > startPick && i <= endPick) {
      endPick++;
    }
    return { startPick, endPick, count: lp.count };
  });

  return {
    ...s,
    weftCount: s.weftCount + 1,
    armur: newArmur,
    iroData: newIro,
    loops: newLoops,
  };
}

/** Eski kayıtlardan yüklenen DesenState'i normalize eder (loops yoksa []). */
export function normalizeDesen(d: DesenState | undefined): DesenState {
  if (!d) return defaultDesen();
  return { ...d, loops: d.loops ?? [] };
}
