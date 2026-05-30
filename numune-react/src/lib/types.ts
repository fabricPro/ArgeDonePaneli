import type { IplikTip } from "./fpd";

export interface OlcumState {
  uzunluk: string;
  adet: string;
  agirlik: string;
  acik: boolean;
}

/** Iplik elyaf icerigi (icerik ekleme). Iplik basina max 6 satir. */
export interface IplikContent {
  /** PES, LI, CO, WO, PA, AC, VI, EL, SE… (kullanici serbestce yazar, render'da uppercase) */
  elyaf: string;
  /** Yuzde (%) — string olarak tutulur (Field uyumlu) */
  oran: string;
}

/** Iplik bilgi alanlari — SADECE bilgi, maliyete (calcAll) girmez */
export interface IplikInfo {
  /** Info paneli acik mi */
  acik: boolean;
  iplikAdi: string;
  firmaAdi: string;
  /** "Fason islem" checkbox */
  fason: boolean;
  fasonFirma: string;
  fasonIslem: string;
  fasonFiyat: string;
}

export interface Iplik {
  id: number;
  tip: IplikTip;
  /** Ham giris: "300*2" gibi (kalinlik*kat) */
  raw: string;
  /** Siklik (ad/cm) */
  sik: string;
  /** Birim fiyat ($/kg) */
  fiyat: string;
  olcum: OlcumState;
  /** Sadece bilgi — maliyeti etkilemez */
  info: IplikInfo;
  /** Elyaf icerigi (max 6). Kumas icerik hesabina girer — ana maliyeti degistirmez. */
  contents: IplikContent[];
}

export interface TemelOlcu {
  /** Olculen m2 gramaj (g/m2) */
  gramajM2: string;
  tarakEn: string;
  mamulEn: string;
}

export interface CekmePair {
  lDuz: string;
  lKumas: string;
}

export interface CekmeState {
  cozgu: CekmePair;
  atki: CekmePair;
}

export interface Params {
  devir: string;
  randiman: string;
  terbiyeFiyat: string;
  genelFire: string;
  kursum: string;
  ekMal: string;
}

export interface Meta {
  numuneAd: string;
  musteri: string;
  tarih: string;
}

export interface Photo {
  id: number;
  url: string;
  label: string;
}

/** DO…NEXT döngüsü — atkı raporu satırlarını tekrarlar.
 *  startPick = DO marker satırı, endPick = NEXT marker satırı (0-based).
 *  Aradaki pattern satırları count kez dokunur.
 *  Marker satırlardaki armür/iro hücreleri görsel olarak gizlenir; veri korunur. */
export interface LoopRange {
  startPick: number;
  endPick: number;
  count: number;
}

/** Dokuma deseni — tahar / armür / desen(hesaplanır) / atkı raporu(iro) / döngüler */
export interface DesenState {
  warpCount: number;
  weftCount: number;
  frameCount: number;
  iroCount: number;
  /** Rapor tekrar (döşeme önizlemesi) */
  raporX: number;
  raporY: number;
  /** tahar[warpIdx] = frameIdx (0-based) */
  tahar: number[];
  /** armur[frameIdx][weftIdx] = o atkıda çerçeve kalkıyor mu */
  armur: boolean[][];
  /** iroData[weftIdx] = atkı motoru/rengi (1-based) */
  iroData: number[];
  /** DO…NEXT döngüleri (disjoint, sıralı tutulur). v0.2'de eklendi — eski kayıtlarda yoksa [] olarak yüklenir. */
  loops: LoopRange[];
}

/** Tarak raporu state'i — tarak modülü v0.3'te eklendi. */
export interface TarakState {
  /** Tarak sıklığı (diş/cm) */
  siklik: string;
  /** Rapor diş sayısı (UI'ın source of truth'u — cm modunda hesaplanarak buraya yazılır) */
  raporDis: string;
  /** Mod: hangi alanı düzenliyoruz ("dis" = diş bazlı, "cm" = cm bazlı) */
  mode: "dis" | "cm";
  /** cm modu için manuel girilen rapor cm (mode === "cm" iken anlamlı) */
  raporCm: string;
  /** dentThreads[i] = i. dişe geçen tel sayısı (uzunluğu = raporDis sayısal değeri) */
  dentThreads: number[];
}

export interface AnalizState {
  meta: Meta;
  photos: Photo[];
  olcum: TemelOlcu;
  cozgu: Iplik[];
  atki: Iplik[];
  cekme: CekmeState;
  params: Params;
  desen: DesenState;
  /** Tarak (reed) raporu — v0.3'te eklendi. Eski kayıtlarda yoksa default'lanır. */
  tarak: TarakState;
}

/** olcumKalinlik() ciktisi — sok/olc/tart ile iplik no tayini */
export interface OlcumSonuc {
  denye: number;
  dtex: number;
  nm: number;
  ne: number;
  ok: boolean;
}

/** Kumas icerik dagilimi — calcKumasIcerik() ciktisi */
export interface KumasIcerik {
  /** Normalize edilmis elyaf kodu (uppercase, ornek "PES") */
  elyaf: string;
  /** O elyaftan toplam (g/mt) */
  gramaj: number;
  /** Toplam icerik icindeki yuzde (0-100) */
  oran: number;
}

/** calcAll() ciktisi */
export interface CalcResult {
  topI: number;
  grmt: number;
  grmtCozgu: number;
  grmtAtki: number;
  fasI: number;
  terbM: number;
  fireM: number;
  uAy: number;
  total: number;
  cozguFak: number;
  atkiFak: number;
  cCek: number;
  aCek: number;
  hesapM2: number;
  olcumM2: number;
  sapma: number | null;
}
