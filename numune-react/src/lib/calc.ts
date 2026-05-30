import { FPD, type IplikTip } from "./fpd";
import type { AnalizState, CalcResult, KumasIcerik, OlcumSonuc } from "./types";

export const num = (v: unknown): number => {
  if (typeof v === "number") return v;
  const n = parseFloat(String(v ?? "").replace(",", "."));
  return isNaN(n) ? 0 : n;
};

export function parseIplikRaw(raw: string): { denye: number; kat: number } {
  const s = String(raw ?? "")
    .trim()
    .replace(",", ".");
  if (!s) return { denye: 0, kat: 1 };
  const m = s.match(/^([\d.]+)\s*[*xX/]\s*([\d.]+)$/);
  if (m) return { denye: num(m[1]), kat: num(m[2]) || 1 };
  return { denye: num(s), kat: 1 };
}

/**
 * Olcumden iplik numarasi tayini.
 * effLen_cm = uzunluk x adet; W = agirlik (mg)
 *   DENYE = (W * 900) / effLen ; DTEX = (W * 1000) / effLen
 *   NM = (effLen * 10) / W      ; NE = NM / 1.69
 */
export function olcumKalinlik(
  uzunluk: unknown,
  adet: unknown,
  agirlik: unknown,
): OlcumSonuc {
  const L = num(uzunluk) * Math.max(1, num(adet));
  const W = num(agirlik);
  if (L <= 0 || W <= 0) return { denye: 0, dtex: 0, nm: 0, ne: 0, ok: false };
  return {
    denye: (W * 900) / L,
    dtex: (W * 1000) / L,
    nm: (L * 10) / W,
    ne: (L * 10) / W / FPD.ne_factor,
    ok: true,
  };
}

/** Cozgu gramaji (g/mt) — tip + iplik no + kat + tel. */
export function tukH(
  tip: IplikTip,
  den: number,
  kat: number,
  tel: number,
  fak = 1,
): number {
  if (den <= 0 || tel <= 0) return 0;
  switch (tip) {
    case "DENYE":
      return ((tel / (FPD.denye_base / den)) * kat) / 1000 * fak * 1000;
    case "DTEX":
      return ((tel / (FPD.dtex_base / den)) * kat) / 1000 * fak * 1000;
    case "NM":
      return tel / (den / kat) / 1000 * fak * 1000;
    case "NE":
      return tel / ((FPD.ne_factor * den) / kat) / 1000 * fak * 1000;
    default:
      return 0;
  }
}

/** Atki gramaji (g/mt) — tarak eni faktoru ile. */
export function atkiGramaj(
  tip: IplikTip,
  den: number,
  kat: number,
  tel: number,
  tarakEn: number,
  fak = 1,
): number {
  if (den <= 0 || tel <= 0) return 0;
  const lenM = (tel * tarakEn) / 100;
  let t = 0;
  switch (tip) {
    case "DENYE":
      t = (lenM * den * kat) / FPD.denye_base;
      break;
    case "DTEX":
      t = (lenM * den * kat) / FPD.dtex_base;
      break;
    case "NM":
      t = (lenM * kat) / den;
      break;
    case "NE":
      t = (lenM * kat) / (FPD.ne_factor * den);
      break;
    default:
      t = 0;
  }
  return t * fak;
}

export const cekmeOran = (lDuz: number, lKumas: number): number =>
  lDuz > 0 ? (lDuz - lKumas) / lDuz : 0;

export function calcAll(state: AnalizState): CalcResult {
  const o = state.olcum;
  const tarakEn = num(o.tarakEn);
  const mamulEn = num(o.mamulEn) || tarakEn;
  const cCek = cekmeOran(num(state.cekme.cozgu.lDuz), num(state.cekme.cozgu.lKumas));
  const aCek = cekmeOran(num(state.cekme.atki.lDuz), num(state.cekme.atki.lKumas));
  const cozguFak = cCek < 0.999 ? 1 / (1 - cCek) : 1;
  const atkiFak = aCek < 0.999 ? 1 / (1 - aCek) : 1;

  let topI = 0;
  let grmt = 0;
  let grmtCozgu = 0;
  let grmtAtki = 0;

  state.cozgu.forEach((c) => {
    const { denye, kat } = parseIplikRaw(c.raw);
    const tel = num(c.sik) * tarakEn;
    const g = tukH(c.tip, denye, kat, tel, cozguFak);
    grmt += g;
    grmtCozgu += g;
    topI += (g * num(c.fiyat)) / 1000;
  });

  state.atki.forEach((a) => {
    const { denye, kat } = parseIplikRaw(a.raw);
    const tel = num(a.sik) * 100;
    const g = atkiGramaj(a.tip, denye, kat, tel, tarakEn, atkiFak);
    grmt += g;
    grmtAtki += g;
    topI += (g * num(a.fiyat)) / 1000;
  });

  const p = state.params;
  const totAtkiSik = state.atki.reduce((s, a) => s + num(a.sik), 0);
  const binD =
    totAtkiSik < FPD.bin_thr
      ? (FPD.bin_thr - totAtkiSik) * FPD.bin_mul + FPD.bin_base
      : FPD.bin_base;
  const uAy =
    totAtkiSik > 0
      ? ((num(p.devir) * FPD.dak * FPD.saat * FPD.ay_gun) / 100) /
        totAtkiSik *
        (num(p.randiman) / 100)
      : 0;
  const fasI = uAy > 0 ? (binD / uAy) * FPD.iscilikKdv : 0;
  const terbM = (grmt / 1000) * num(p.terbiyeFiyat);
  const fireM = (topI + fasI + terbM) * (num(p.genelFire) / 100);
  const total = topI + fasI + terbM + num(p.kursum) + num(p.ekMal) + fireM;

  const enM = mamulEn / 100;
  const hesapM2 = enM > 0 ? grmt / enM : 0;
  const olcumM2 = num(o.gramajM2);
  const sapma = olcumM2 > 0 ? ((hesapM2 - olcumM2) / olcumM2) * 100 : null;

  return {
    topI,
    grmt,
    grmtCozgu,
    grmtAtki,
    fasI,
    terbM,
    fireM,
    uAy,
    total,
    cozguFak,
    atkiFak,
    cCek,
    aCek,
    hesapM2,
    olcumM2,
    sapma,
  };
}

/**
 * Kumas icerik hesabi — her ipligin gramaj katkisi × elyaf orani -> elyafa gore topla, %'ye normalize.
 * Iplik basina oran toplami 100 olmasa da literal kullanilir; final % normalize toplam uzerinden.
 */
export function calcKumasIcerik(state: AnalizState, r: CalcResult): KumasIcerik[] {
  const tarakEn = num(state.olcum.tarakEn);
  const map = new Map<string, number>();

  const addContents = (g: number, contents: { elyaf: string; oran: string }[]) => {
    if (g <= 0 || !contents || contents.length === 0) return;
    for (const c of contents) {
      const elyaf = c.elyaf.trim().toUpperCase();
      const oran = num(c.oran) / 100;
      if (!elyaf || oran <= 0) continue;
      const w = g * oran;
      map.set(elyaf, (map.get(elyaf) ?? 0) + w);
    }
  };

  for (const c of state.cozgu) {
    const { denye, kat } = parseIplikRaw(c.raw);
    const tel = num(c.sik) * tarakEn;
    const g = tukH(c.tip, denye, kat, tel, r.cozguFak);
    addContents(g, c.contents);
  }
  for (const a of state.atki) {
    const { denye, kat } = parseIplikRaw(a.raw);
    const tel = num(a.sik) * 100;
    const g = atkiGramaj(a.tip, denye, kat, tel, tarakEn, r.atkiFak);
    addContents(g, a.contents);
  }

  const total = [...map.values()].reduce((a, b) => a + b, 0);
  if (total <= 0) return [];

  return [...map.entries()]
    .map(([elyaf, gramaj]) => ({ elyaf, gramaj, oran: (gramaj / total) * 100 }))
    .sort((a, b) => b.oran - a.oran);
}
