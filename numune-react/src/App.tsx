/**
 * App.tsx — kendi yazımız (NumuneAnaliz orijinali değil).
 *
 * Sorumluluk:
 *  - initialState'i normalize et (Desen + Tarak için)
 *  - "Desen" ve "Tarak" iç sekmeleri arasında geçiş
 *  - DesenTab/TarakTab callback'lerinden state'i topla
 *  - Debounced (500 ms) parent.onChange ile sunucuya senkron
 *  - Tarak → Desen "warpCount aktar" köprüsü
 */
import { useState, useEffect, useRef } from "react";
import type { CSSProperties } from "react";
import { Grid3x3, Sliders } from "lucide-react";
import { defaultDesen, normalizeDesen, setDimension } from "./lib/desen";
import { defaultTarak, normalizeTarak } from "./lib/tarak";
import { DesenTab } from "./components/DesenTab";
import { TarakTab } from "./components/TarakTab";
import type { DesenState, TarakState } from "./lib/types";
import { C } from "./theme";

/** Server'dan gelen `{}` boş obje veya partial state → default + merge + normalize.
 *  normalizeDesen tek başına boş objeyi handle etmiyor (sadece loops ekliyor),
 *  bu yüzden burada default ile merge edip eksik field'ları garantiliyoruz. */
function safeNormalizeDesen(input: unknown): DesenState {
  if (!input || typeof input !== "object" || Object.keys(input).length === 0) {
    return defaultDesen();
  }
  const merged = { ...defaultDesen(), ...(input as Partial<DesenState>) } as DesenState;
  return normalizeDesen(merged);
}
function safeNormalizeTarak(input: unknown): TarakState {
  if (!input || typeof input !== "object" || Object.keys(input).length === 0) {
    return defaultTarak();
  }
  const merged = { ...defaultTarak(), ...(input as Partial<TarakState>) } as TarakState;
  return normalizeTarak(merged);
}

interface Props {
  initialState: { desen?: unknown; tarak?: unknown };
  urunId: string;
  surumId: string;
  onChange?: (state: { desen: DesenState; tarak: TarakState }) => void;
}

type Tab = "desen" | "tarak";

export function App({ initialState, onChange }: Props) {
  // initialState server'dan jsonb olarak gelir; boş obje {} ise default.
  const [desen, setDesen] = useState<DesenState>(() => safeNormalizeDesen(initialState.desen));
  const [tarak, setTarak] = useState<TarakState>(() => safeNormalizeTarak(initialState.tarak));
  const [tab, setTab] = useState<Tab>("desen");
  const firstSync = useRef(true);

  // Debounced sunucu senkron — initial mount tetiklemez
  useEffect(() => {
    if (firstSync.current) {
      firstSync.current = false;
      return;
    }
    if (!onChange) return;
    const t = setTimeout(() => onChange({ desen, tarak }), 500);
    return () => clearTimeout(t);
  }, [desen, tarak, onChange]);

  const tabBtn = (active: boolean): CSSProperties => ({
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "10px 16px",
    background: active ? C.panel : "transparent",
    color: active ? C.accent : C.dim,
    border: "none",
    borderBottom: `2px solid ${active ? C.accent : "transparent"}`,
    cursor: "pointer",
    fontWeight: 600,
    fontSize: 14,
    marginBottom: -1,
    transition: "color 120ms, border-color 120ms",
  });

  return (
    <div style={{ padding: 12 }}>
      <nav style={{ display: "flex", gap: 4, borderBottom: `1px solid ${C.line}`, marginBottom: 14 }}>
        <button type="button" style={tabBtn(tab === "desen")} onClick={() => setTab("desen")}>
          <Grid3x3 size={16} /> Desen
        </button>
        <button type="button" style={tabBtn(tab === "tarak")} onClick={() => setTab("tarak")}>
          <Sliders size={16} /> Tarak
        </button>
      </nav>

      {tab === "desen" && <DesenTab desen={desen} onChange={setDesen} />}

      {tab === "tarak" && (
        <TarakTab
          tarak={tarak}
          onChange={setTarak}
          onSendToDesen={(info) => {
            // TarakTab köprüsü: cozguSiklik + raporCm + warpCount birlikte gelir.
            // Şimdilik sadece warpCount'u Desen'e uyguluyoruz.
            // (Sıklık + rapor cm Flask "Temel Parametreler" formuna ileride bağlanabilir.)
            setDesen((d) => setDimension(d, "warpCount", info.warpCount));
            setTab("desen");
          }}
        />
      )}
    </div>
  );
}
