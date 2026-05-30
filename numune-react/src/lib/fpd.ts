/** FPD sabitleri — armur-desktop ile birebir ayni aritmetik. */
export const FPD = {
  denye_base: 9000,
  dtex_base: 10000,
  ne_factor: 1.69,
  bin_thr: 12,
  bin_mul: 1000,
  bin_base: 8000,
  dak: 60,
  saat: 24,
  ay_gun: 26,
  iscilikKdv: 1.1,
} as const;

export const TIPLER = ["DENYE", "DTEX", "NM", "NE"] as const;
export type IplikTip = (typeof TIPLER)[number];
