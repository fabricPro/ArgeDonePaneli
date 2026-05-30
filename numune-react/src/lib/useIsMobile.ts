import { useSyncExternalStore } from "react";

/** Mobil esigi — bunun altinda mobil duzen. */
export const MOBILE_QUERY = "(max-width: 768px)";

function subscribe(callback: () => void): () => void {
  const mql = window.matchMedia(MOBILE_QUERY);
  mql.addEventListener("change", callback);
  return () => mql.removeEventListener("change", callback);
}

function getSnapshot(): boolean {
  return window.matchMedia(MOBILE_QUERY).matches;
}

/** Ekran genisligi mobil esiginde mi? Resize'da otomatik gunceller. */
export function useIsMobile(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
