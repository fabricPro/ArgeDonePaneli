export const fmt = (n: number, d = 2): string =>
  (isFinite(n) ? n : 0).toLocaleString("tr-TR", {
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  });

/** Sondaki sifirlari kirpar: 40,0->40 · 4,00->4 · 0,20->0,2 · 106,7 kalir. */
export const nf = (n: number, maxDec = 2): string =>
  (isFinite(n) ? n : 0).toLocaleString("tr-TR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxDec,
  });
