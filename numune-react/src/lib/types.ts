/**
 * NumuneAnaliz "feat/tarak-ve-desen-loop" branch'inden alınan
 * Desen + Tarak modüllerinin TİP tanımları.
 *
 * Orijinal types.ts içindeki Iplik/AnalizState/CalcResult vs. atlandı
 * (bunlar bizim için gereksiz; ana host Flask kendi şemasını kullanıyor).
 *
 * Üst sistemden (Flask product.teknik.surumler[*].tahar_grid ve tarak_raporu)
 * gelen state DesenState / TarakState formatında olur. Eski kayıtlarda
 * eksik alanlar normalizeDesen / normalizeTarak ile doldurulur.
 */

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
