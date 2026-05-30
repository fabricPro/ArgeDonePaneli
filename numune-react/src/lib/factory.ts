import type { Iplik, IplikInfo } from "./types";

export const DEFAULT_INFO: IplikInfo = {
  acik: false,
  iplikAdi: "",
  firmaAdi: "",
  fason: false,
  fasonFirma: "",
  fasonIslem: "",
  fasonFiyat: "",
};

export function yeniIplik(defaults: Partial<Iplik> = {}): Iplik {
  return {
    id: Date.now() + Math.random(),
    tip: "DENYE",
    raw: "",
    sik: "",
    fiyat: "",
    olcum: { uzunluk: "", adet: "1", agirlik: "", acik: false },
    info: { ...DEFAULT_INFO },
    contents: [],
    ...defaults,
  };
}
