/**
 * App.tsx — 4 sekmeli NumuneAnaliz mount adapter.
 * Sekmeler: Analiz · Maliyet · Desen · Tarak
 *
 * AnalizState parent state. Tüm sekmeler aynı state üzerinde çalışır.
 * onChange callback'i 500ms debounced ile sunucuya tam state'i yollar.
 */
import { useState, useEffect, useMemo, useRef } from "react";
import type { CSSProperties } from "react";
import { Grid3x3, Sliders, Ruler, Calculator } from "lucide-react";
import { defaultDesen, normalizeDesen } from "./lib/desen";
import { defaultTarak, normalizeTarak } from "./lib/tarak";
import { calcAll } from "./lib/calc";
import { yeniIplik } from "./lib/factory";
import { AnalizTab } from "./components/AnalizTab";
import { MaliyetTab } from "./components/MaliyetTab";
import { DesenTab } from "./components/DesenTab";
import { TarakTab } from "./components/TarakTab";
import type { AnalizState, DesenState, TarakState } from "./lib/types";
import { C } from "./theme";

interface Props {
  initialState: { analiz?: unknown; desen?: unknown; tarak?: unknown };
  urunId: string;
  surumId: string;
  onChange?: (state: { analiz: AnalizState }) => void;
}

type Tab = "analiz" | "maliyet" | "desen" | "tarak";

function defaultAnalizState(): AnalizState {
  return {
    meta: { numuneAd: "", musteri: "", tarih: "" },
    photos: [],
    olcum: { gramajM2: "", tarakEn: "", mamulEn: "" },
    cozgu: [yeniIplik()],
    atki: [yeniIplik()],
    cekme: {
      cozgu: { lDuz: "", lKumas: "" },
      atki: { lDuz: "", lKumas: "" },
    },
    params: {
      devir: "",
      randiman: "",
      terbiyeFiyat: "",
      genelFire: "",
      kursum: "",
      ekMal: "",
    },
    desen: defaultDesen(),
    tarak: defaultTarak(),
  };
}

function safeNormalizeAnaliz(input: unknown): AnalizState {
  const def = defaultAnalizState();
  if (!input || typeof input !== "object") return def;
  const i = input as Partial<AnalizState>;
  return {
    meta: { ...def.meta, ...(i.meta || {}) },
    photos: Array.isArray(i.photos) ? i.photos : def.photos,
    olcum: { ...def.olcum, ...(i.olcum || {}) },
    cozgu: Array.isArray(i.cozgu) && i.cozgu.length > 0 ? i.cozgu : def.cozgu,
    atki: Array.isArray(i.atki) && i.atki.length > 0 ? i.atki : def.atki,
    cekme: {
      cozgu: { ...def.cekme.cozgu, ...(i.cekme?.cozgu || {}) },
      atki: { ...def.cekme.atki, ...(i.cekme?.atki || {}) },
    },
    params: { ...def.params, ...(i.params || {}) },
    desen: normalizeDesen(
      (i.desen && Object.keys(i.desen).length > 0
        ? { ...def.desen, ...(i.desen as Partial<DesenState>) }
        : def.desen) as DesenState,
    ),
    tarak: normalizeTarak(
      (i.tarak && Object.keys(i.tarak).length > 0
        ? { ...def.tarak, ...(i.tarak as Partial<TarakState>) }
        : def.tarak) as TarakState,
    ),
  };
}

export function App({ initialState, onChange }: Props) {
  const initial = useMemo<AnalizState>(() => {
    const src = initialState.analiz
      ? initialState.analiz
      : { desen: initialState.desen, tarak: initialState.tarak };
    return safeNormalizeAnaliz(src);
  }, [initialState]);

  const [state, setState] = useState<AnalizState>(initial);
  const [tab, setTab] = useState<Tab>("analiz");
  const firstSync = useRef(true);

  // Patch helper — set({ olcum: {...} }) gibi kısmi state update
  const set = (patch: Partial<AnalizState>) =>
    setState((s) => ({ ...s, ...patch }));

  // Debounced sunucu senkron
  useEffect(() => {
    if (firstSync.current) {
      firstSync.current = false;
      return;
    }
    if (!onChange) return;
    const t = setTimeout(() => onChange({ analiz: state }), 500);
    return () => clearTimeout(t);
  }, [state, onChange]);

  // Maliyet hesaplama — useMemo ile state değişince yenilenir
  const r = useMemo(() => calcAll(state), [state]);

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
    whiteSpace: "nowrap",
  });

  return (
    <div style={{ padding: 12 }}>
      <nav
        style={{
          display: "flex",
          gap: 4,
          borderBottom: `1px solid ${C.line}`,
          marginBottom: 14,
          overflowX: "auto",
        }}
      >
        <button type="button" style={tabBtn(tab === "analiz")} onClick={() => setTab("analiz")}>
          <Ruler size={16} /> Analiz
        </button>
        <button type="button" style={tabBtn(tab === "maliyet")} onClick={() => setTab("maliyet")}>
          <Calculator size={16} /> Maliyet
        </button>
        <button type="button" style={tabBtn(tab === "desen")} onClick={() => setTab("desen")}>
          <Grid3x3 size={16} /> Desen
        </button>
        <button type="button" style={tabBtn(tab === "tarak")} onClick={() => setTab("tarak")}>
          <Sliders size={16} /> Tarak
        </button>
      </nav>

      {tab === "analiz" && (
        <AnalizTab
          state={state}
          set={set}
          setState={setState}
          onNext={() => setTab("maliyet")}
        />
      )}

      {tab === "maliyet" && <MaliyetTab state={state} set={set} r={r} />}

      {tab === "desen" && (
        <DesenTab
          desen={state.desen}
          onChange={(d: DesenState) => set({ desen: d })}
        />
      )}

      {tab === "tarak" && (
        <TarakTab
          tarak={state.tarak}
          onChange={(t: TarakState) => set({ tarak: t })}
          onSendToDesen={(info) => {
            set({ desen: { ...state.desen, warpCount: info.warpCount } });
            setTab("desen");
          }}
        />
      )}
    </div>
  );
}
