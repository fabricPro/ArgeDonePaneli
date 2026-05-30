import { useState, type ReactNode, type CSSProperties } from "react";
import {
  Grid3x3,
  Wand2,
  Eraser,
  Minus,
  Plus,
  X,
  Repeat,
  Trash2,
} from "lucide-react";
import type { DesenState, LoopRange } from "../lib/types";
import {
  computeDesen,
  buildDuzTahar,
  buildEmptyArmur,
  setDimension,
  IRO_COLORS,
  MIN_WARP,
  MAX_WARP,
  MIN_WEFT,
  MAX_WEFT,
  MIN_FRAME,
  MAX_FRAME,
  MIN_IRO,
  MAX_IRO,
  MIN_LOOP_COUNT,
  MAX_LOOP_COUNT,
  buildMarkerMap,
  expandPicks,
  validateLoop,
  addLoop,
  removeLoopAt,
  updateLoopCount,
  clearLoops,
  insertRow,
  deleteRow,
  type MarkerInfo,
} from "../lib/desen";
import { C, btnAdd } from "../theme";
import { Card } from "./Card";

// Hücre boyutu — armür/atkı bölgesinde
const CELL = 22;
// Desen önizleme hücresi
const PREV = 14;
// Pick numarası label genişliği
const PICK_LABEL_W = 28;
// Çözgü/iro grid'leri arası boşluk
const GRID_GAP_PX = 12;
// Bracket SVG genişliği
const BRACKET_W = 32;
const BRACKET_COLOR = "#e8674f"; // C.bad — döngü vurgusu
const ROW_GAP = 2;

interface DesenTabProps {
  desen: DesenState;
  onChange: (d: DesenState) => void;
}

// ============================================================
// Stepper
// ============================================================

function Stepper({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  const btn = (txt: ReactNode, dv: number, disabled: boolean) => (
    <button
      onClick={() => onChange(value + dv)}
      disabled={disabled}
      style={{
        width: 26,
        height: 26,
        borderRadius: 6,
        border: `1px solid ${C.line}`,
        background: C.bg,
        color: disabled ? C.line : C.text,
        cursor: disabled ? "not-allowed" : "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {txt}
    </button>
  );
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: 11, color: C.dim }}>{label}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {btn(<Minus size={14} />, -1, value <= min)}
        <span
          style={{
            width: 28,
            textAlign: "center",
            fontFamily: "ui-monospace, monospace",
            fontSize: 14,
            fontWeight: 700,
          }}
        >
          {value}
        </span>
        {btn(<Plus size={14} />, +1, value >= max)}
      </div>
    </label>
  );
}

// ============================================================
// Tahar Grid (mevcut yapı korundu)
// ============================================================

function colHeader(count: number, renk: (i: number) => string, prefix: string) {
  return (
    <div style={{ display: "flex", gap: 2 }}>
      <span style={{ width: PICK_LABEL_W }} />
      {Array.from({ length: count }).map((_, i) => (
        <span
          key={i}
          style={{
            width: CELL,
            fontSize: 8,
            color: renk(i),
            textAlign: "center",
            fontWeight: 700,
          }}
        >
          {prefix}
          {i + 1}
        </span>
      ))}
    </div>
  );
}

const cellBox = (filled: boolean, bg: string, onClick?: () => void): CSSProperties => ({
  width: CELL,
  height: CELL,
  borderRadius: 3,
  border: `1px solid ${C.line}`,
  background: filled ? bg : C.bg,
  cursor: onClick ? "pointer" : "default",
});

function TaharGrid({ desen: d, onChange }: DesenTabProps) {
  return (
    <div style={{ overflowX: "auto" }}>
      <div style={{ display: "inline-flex", flexDirection: "column", gap: 2 }}>
        {Array.from({ length: d.frameCount }).map((_, top) => {
          const f = d.frameCount - 1 - top;
          return (
            <div key={f} style={{ display: "flex", alignItems: "center", gap: 2 }}>
              <span
                style={{
                  width: PICK_LABEL_W,
                  fontSize: 10,
                  color: C.dim,
                  textAlign: "right",
                  paddingRight: 4,
                }}
              >
                F{f + 1}
              </span>
              {Array.from({ length: d.warpCount }).map((__, w) => (
                <div
                  key={w}
                  style={cellBox(d.tahar[w] === f, C.warp, () =>
                    onChange({ ...d, tahar: d.tahar.map((t, i) => (i === w ? f : t)) }),
                  )}
                  onClick={() =>
                    onChange({ ...d, tahar: d.tahar.map((t, i) => (i === w ? f : t)) })
                  }
                />
              ))}
            </div>
          );
        })}
        {colHeader(d.warpCount, () => C.dim, "")}
      </div>
    </div>
  );
}

// ============================================================
// Armür + Atkı raporu — birleşik, döngü desteği
// ============================================================

function BracketSvg({ d }: { d: DesenState }) {
  if (!d.loops || d.loops.length === 0) return null;
  const totalH = d.weftCount * CELL + (d.weftCount - 1) * ROW_GAP;
  const tickLen = BRACKET_W - 6;
  const xLine = 3;
  return (
    <svg width={BRACKET_W} height={totalH} style={{ display: "block", flexShrink: 0 }}>
      {d.loops.map((lp, i) => {
        const yTopRow = (d.weftCount - 1 - lp.endPick) * (CELL + ROW_GAP);
        const yBotRow = (d.weftCount - 1 - lp.startPick) * (CELL + ROW_GAP);
        const yTop = yTopRow + CELL / 2;
        const yBot = yBotRow + CELL / 2;
        return (
          <g key={i} stroke={BRACKET_COLOR} strokeWidth={1.5} fill="none">
            <line x1={xLine} y1={yTop} x2={xLine} y2={yBot} />
            <line x1={xLine} y1={yTop} x2={xLine + tickLen} y2={yTop} />
            <line x1={xLine} y1={yBot} x2={xLine + tickLen} y2={yBot} />
          </g>
        );
      })}
    </svg>
  );
}

function RowBtn({
  onClick,
  disabled,
  title,
  variant,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  title?: string;
  variant?: "danger";
  children: ReactNode;
}) {
  const danger = variant === "danger";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={{
        width: 18,
        height: 18,
        padding: 0,
        borderRadius: 4,
        border: `1px solid ${C.line}`,
        background: C.bg,
        color: danger ? "#e8674f" : C.dim,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.3 : 1,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 13,
        lineHeight: 1,
        fontFamily: "inherit",
      }}
    >
      {children}
    </button>
  );
}

function PickRow({
  p,
  marker,
  d,
  onChange,
}: {
  p: number;
  marker: MarkerInfo | undefined;
  d: DesenState;
  onChange: (d: DesenState) => void;
}) {
  const isMarker = !!marker;
  const armurW = d.frameCount * CELL + (d.frameCount - 1) * 2;
  const iroW = d.iroCount * CELL + (d.iroCount - 1) * 2;
  const totalContentW = armurW + GRID_GAP_PX + iroW;

  // Section 33: Marker click artık loop kaldırmaz — count edit eder.
  // Kaldırma sadece Döngüler kartından (LoopRow × butonu).
  const loopIdx = marker ? (d.loops ?? []).indexOf(marker.loop) : -1;
  const adjustCount = (delta: number) => {
    if (!marker || marker.kind !== "DO" || loopIdx < 0) return;
    onChange(updateLoopCount(d, loopIdx, marker.count + delta));
  };
  const stepBtnStyle: React.CSSProperties = {
    width: 18,
    height: 18,
    padding: 0,
    border: "1px solid rgba(232,103,79,0.5)",
    borderRadius: 3,
    background: "rgba(255,255,255,0.7)",
    color: "#e8674f",
    fontFamily: "ui-monospace, monospace",
    fontSize: 12,
    fontWeight: 700,
    lineHeight: 1,
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 2,
        height: CELL,
        background: isMarker ? "rgba(232,103,79,0.08)" : "transparent",
        borderRadius: 3,
      }}
    >
      <span
        style={{
          width: PICK_LABEL_W,
          fontSize: 10,
          textAlign: "right",
          paddingRight: 4,
          color: isMarker ? "#e8674f" : C.dim,
          fontWeight: isMarker ? 700 : 400,
          fontFamily: "ui-monospace, monospace",
        }}
      >
        {p + 1}
      </span>

      {isMarker ? (
        <div
          style={{
            width: totalContentW,
            height: CELL,
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "0 10px",
            borderRadius: 3,
            background: "rgba(232,103,79,0.18)",
            border: "1px solid rgba(232,103,79,0.4)",
            cursor: "default",
            userSelect: "none",
            fontFamily: "ui-monospace, monospace",
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 0.5,
          }}
        >
          <Repeat size={12} color="#e8674f" />
          {marker!.kind === "DO" ? (
            <>
              <span style={{ color: "#e8674f" }}>DO</span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  adjustCount(-1);
                }}
                disabled={marker!.count <= MIN_LOOP_COUNT}
                title="Tekrarı azalt"
                style={{
                  ...stepBtnStyle,
                  opacity: marker!.count <= MIN_LOOP_COUNT ? 0.4 : 1,
                  cursor:
                    marker!.count <= MIN_LOOP_COUNT ? "not-allowed" : "pointer",
                }}
              >
                −
              </button>
              <span
                style={{
                  minWidth: 18,
                  textAlign: "center",
                  color: "#e8674f",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {marker!.count}
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  adjustCount(1);
                }}
                disabled={marker!.count >= MAX_LOOP_COUNT}
                title="Tekrarı artır"
                style={{
                  ...stepBtnStyle,
                  opacity: marker!.count >= MAX_LOOP_COUNT ? 0.4 : 1,
                  cursor:
                    marker!.count >= MAX_LOOP_COUNT ? "not-allowed" : "pointer",
                }}
              >
                +
              </button>
            </>
          ) : (
            <span style={{ color: "#e8674f" }}>NEXT</span>
          )}
          <span
            style={{
              marginLeft: "auto",
              fontSize: 9,
              fontWeight: 400,
              letterSpacing: 0,
              color: C.dim,
            }}
          >
            {marker!.kind === "DO"
              ? `↺${marker!.count}×  döngü başlar`
              : "döngü biter"}
          </span>
        </div>
      ) : (
        <>
          {/* Armür hücreleri */}
          <div style={{ display: "flex", gap: 2 }}>
            {Array.from({ length: d.frameCount }).map((_, f) => {
              const filled = !!d.armur[f]?.[p];
              return (
                <div
                  key={f}
                  style={cellBox(filled, C.accent)}
                  onClick={() =>
                    onChange({
                      ...d,
                      armur: d.armur.map((row, fi) =>
                        fi === f ? row.map((c, pi) => (pi === p ? !c : c)) : row,
                      ),
                    })
                  }
                />
              );
            })}
          </div>
          {/* Boşluk */}
          <div style={{ width: GRID_GAP_PX }} />
          {/* İro hücreleri */}
          <div style={{ display: "flex", gap: 2 }}>
            {Array.from({ length: d.iroCount }).map((_, i) => {
              const sel = d.iroData[p] === i + 1;
              return (
                <div
                  key={i}
                  style={cellBox(sel, IRO_COLORS[i % IRO_COLORS.length])}
                  onClick={() =>
                    onChange({
                      ...d,
                      iroData: d.iroData.map((v, pi) => (pi === p ? i + 1 : v)),
                    })
                  }
                />
              );
            })}
          </div>
        </>
      )}

      {/* +/× butonları */}
      <div style={{ marginLeft: 8, display: "flex", gap: 3 }}>
        <RowBtn
          onClick={() => onChange(insertRow(d, p + 1))}
          disabled={d.weftCount >= MAX_WEFT}
          title="Üstüne yeni satır ekle"
        >
          <Plus size={11} />
        </RowBtn>
        <RowBtn
          variant="danger"
          onClick={() => onChange(deleteRow(d, p))}
          disabled={d.weftCount <= MIN_WEFT}
          title="Bu satırı sil"
        >
          <X size={11} />
        </RowBtn>
      </div>
    </div>
  );
}

function ArmurAtkiSection({ desen: d, onChange }: DesenTabProps) {
  const markers = buildMarkerMap(d.loops ?? []);

  return (
    <div style={{ overflowX: "auto" }}>
      <div style={{ display: "inline-flex", alignItems: "flex-start", gap: 0 }}>
        {/* Bracket alanı (loop varsa) */}
        {d.loops && d.loops.length > 0 ? (
          <BracketSvg d={d} />
        ) : (
          <div style={{ width: BRACKET_W, flexShrink: 0 }} />
        )}

        {/* Satırlar + alt etiketler */}
        <div style={{ display: "flex", flexDirection: "column", gap: ROW_GAP }}>
          {Array.from({ length: d.weftCount }).map((_, top) => {
            const p = d.weftCount - 1 - top;
            return (
              <PickRow key={p} p={p} marker={markers.get(p)} d={d} onChange={onChange} />
            );
          })}

          {/* En alta satır ekle */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              height: 20,
              marginTop: 4,
              paddingLeft: PICK_LABEL_W + 2,
            }}
          >
            <RowBtn
              onClick={() => onChange(insertRow(d, 0))}
              disabled={d.weftCount >= MAX_WEFT}
              title="En alta yeni satır ekle (pick 1 altına)"
            >
              <Plus size={11} />
            </RowBtn>
            <span style={{ fontSize: 10, color: C.dim }}>en alta satır ekle</span>
          </div>

          {/* Alt: F1..Fn ve i1..in etiketleri */}
          <div style={{ display: "flex", alignItems: "flex-start", marginTop: 6 }}>
            <div style={{ width: PICK_LABEL_W + 2 }} />
            <div style={{ display: "flex", gap: 2 }}>
              {Array.from({ length: d.frameCount }).map((_, f) => (
                <span
                  key={f}
                  style={{
                    width: CELL,
                    fontSize: 8,
                    color: C.dim,
                    textAlign: "center",
                    fontWeight: 700,
                  }}
                >
                  F{f + 1}
                </span>
              ))}
            </div>
            <div style={{ width: GRID_GAP_PX }} />
            <div style={{ display: "flex", gap: 2 }}>
              {Array.from({ length: d.iroCount }).map((_, i) => (
                <span
                  key={i}
                  style={{
                    width: CELL,
                    fontSize: 8,
                    color: IRO_COLORS[i % IRO_COLORS.length],
                    textAlign: "center",
                    fontWeight: 700,
                  }}
                >
                  i{i + 1}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Döngü formu + listesi
// ============================================================

function LoopForm({ desen: d, onChange }: DesenTabProps) {
  const [startStr, setStartStr] = useState("");
  const [endStr, setEndStr] = useState("");
  const [count, setCount] = useState<number>(MIN_LOOP_COUNT);
  const [error, setError] = useState("");

  const handleAdd = () => {
    const s = parseInt(startStr, 10);
    const e = parseInt(endStr, 10);
    if (!s || !e || !count) {
      setError("Tüm alanları doldur");
      return;
    }
    const loop: LoopRange = { startPick: s - 1, endPick: e - 1, count };
    const err = validateLoop(d.loops ?? [], loop, d.weftCount);
    if (err) {
      setError(err);
      return;
    }
    setError("");
    onChange(addLoop(d, loop));
    setStartStr("");
    setEndStr("");
    setCount(MIN_LOOP_COUNT);
  };

  const inputCss: CSSProperties = {
    width: 70,
    height: 30,
    padding: "4px 8px",
    borderRadius: 6,
    border: `1px solid ${C.line}`,
    background: C.bg,
    color: C.text,
    fontFamily: "ui-monospace, monospace",
    fontSize: 13,
  };
  const labelCss: CSSProperties = { fontSize: 11, color: C.dim, marginBottom: 4 };

  const loops = d.loops ?? [];

  return (
    <>
      <div
        style={{
          display: "flex",
          gap: 10,
          alignItems: "flex-end",
          flexWrap: "wrap",
          marginBottom: 8,
        }}
      >
        <label style={{ display: "flex", flexDirection: "column" }}>
          <span style={labelCss}>DO atkı</span>
          <input
            type="number"
            min={1}
            max={d.weftCount}
            value={startStr}
            onChange={(ev) => setStartStr(ev.target.value)}
            onKeyDown={(ev) => {
              if (ev.key === "Enter") handleAdd();
            }}
            style={inputCss}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column" }}>
          <span style={labelCss}>NEXT atkı</span>
          <input
            type="number"
            min={1}
            max={d.weftCount}
            value={endStr}
            onChange={(ev) => setEndStr(ev.target.value)}
            onKeyDown={(ev) => {
              if (ev.key === "Enter") handleAdd();
            }}
            style={inputCss}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column" }}>
          <span style={labelCss}>Tekrar (N)</span>
          <input
            type="number"
            min={MIN_LOOP_COUNT}
            max={MAX_LOOP_COUNT}
            value={count}
            onChange={(ev) => setCount(parseInt(ev.target.value, 10) || MIN_LOOP_COUNT)}
            onKeyDown={(ev) => {
              if (ev.key === "Enter") handleAdd();
            }}
            style={inputCss}
          />
        </label>
        <button
          onClick={handleAdd}
          style={{ ...btnAdd(C.bad), width: "auto", marginTop: 0 }}
        >
          <Repeat size={14} /> Döngü ekle
        </button>
        {loops.length > 0 && (
          <button
            onClick={() => onChange(clearLoops(d))}
            style={{ ...btnAdd(C.dim), width: "auto", marginTop: 0 }}
          >
            <Trash2 size={14} /> Hepsini temizle
          </button>
        )}
        {error && (
          <span style={{ fontSize: 11, color: "#e8674f", marginLeft: 6 }}>{error}</span>
        )}
      </div>

      <p
        style={{
          fontSize: 10,
          color: C.dim,
          fontStyle: "italic",
          marginBottom: 10,
          lineHeight: 1.5,
        }}
      >
        DO ve NEXT satırları renkli marker olur, aralarında en az 1 atkı olmalı. Marker'a
        tıkla → döngü kalkar. Satırın yanındaki <Plus size={9} /> ile üstüne yeni satır
        eklenir, <X size={9} /> ile silinir.
      </p>

      {loops.length === 0 ? (
        <span style={{ fontSize: 11, color: C.dim, fontStyle: "italic" }}>
          Henüz döngü yok — atkı raporu ve armür olduğu gibi dokunur.
        </span>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {loops.map((lp, idx) => {
            const patternRows = lp.endPick - lp.startPick - 1;
            const woven = patternRows * lp.count;
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "6px 10px",
                  background: C.panel2,
                  borderRadius: 6,
                  fontSize: 13,
                  fontFamily: "ui-monospace, monospace",
                }}
              >
                <span
                  style={{
                    color: "#e8674f",
                    fontWeight: 700,
                    letterSpacing: 0.5,
                    fontSize: 11,
                  }}
                >
                  DO {lp.count}
                </span>
                <span style={{ color: C.text }}>
                  Atkı {lp.startPick + 1} (DO) → {lp.endPick + 1} (NEXT)
                </span>
                <span style={{ color: C.dim, fontSize: 11 }}>
                  {patternRows} pattern × {lp.count} = {woven} dokuma
                </span>
                <button
                  onClick={() => onChange(removeLoopAt(d, idx))}
                  title="Döngüyü sil"
                  style={{
                    marginLeft: "auto",
                    width: 22,
                    height: 22,
                    borderRadius: 5,
                    border: "none",
                    background: "transparent",
                    color: C.dim,
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <X size={14} />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}

// ============================================================
// Desen önizleme — döngüleri açar
// ============================================================

function DesenPreview({ d, colored }: { d: DesenState; colored: boolean }) {
  const matrix = computeDesen(d.tahar, d.armur, d.weftCount);
  const expanded = expandPicks(d);
  const fullSeq: number[] = [];
  for (let r = 0; r < Math.max(1, d.raporY); r++) {
    for (let i = 0; i < expanded.length; i++) fullSeq.push(expanded[i]);
  }
  const totalCols = d.warpCount * Math.max(1, d.raporX);
  const totalRows = fullSeq.length;

  if (totalRows === 0) {
    return (
      <div style={{ padding: 20, color: C.dim, fontStyle: "italic", fontSize: 12 }}>
        Tüm atkılar marker — dokunacak satır yok
      </div>
    );
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <div
        style={{
          display: "inline-flex",
          flexDirection: "column",
          border: `1px solid ${C.line}`,
        }}
      >
        {Array.from({ length: totalRows }).map((_, top) => {
          const idx = totalRows - 1 - top;
          const p = fullSeq[idx];
          // Section 33: Renkli mod ON → boş hücre atkı'nın iro rengiyle dolar.
          const iroIdx = ((d.iroData?.[p] ?? 1) - 1) % IRO_COLORS.length;
          const emptyBg = colored
            ? IRO_COLORS[(iroIdx + IRO_COLORS.length) % IRO_COLORS.length]
            : "transparent";
          return (
            <div key={top} style={{ display: "flex" }}>
              {Array.from({ length: totalCols }).map((__, col) => {
                const w = col % d.warpCount;
                const filled = !!matrix[w]?.[p];
                return (
                  <div
                    key={col}
                    style={{
                      width: PREV,
                      height: PREV,
                      background: filled ? C.text : emptyBg,
                      borderRight: `0.5px solid ${C.line}`,
                      borderBottom: `0.5px solid ${C.line}`,
                    }}
                  />
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DesenInfo({ d }: { d: DesenState }) {
  const expanded = expandPicks(d);
  const markerCount = (d.loops ?? []).length * 2;
  const patternCount = d.weftCount - markerCount;
  const totalCols = d.warpCount * Math.max(1, d.raporX);
  const totalRows = expanded.length * Math.max(1, d.raporY);
  return (
    <span
      style={{
        display: "inline-block",
        padding: "4px 10px",
        borderRadius: 6,
        background: C.panel2,
        fontSize: 10,
        color: C.dim,
        fontFamily: "ui-monospace, monospace",
        letterSpacing: 0.2,
      }}
    >
      Armür {d.weftCount} atkı ({markerCount} marker + {patternCount} pattern) · Dokuma{" "}
      {expanded.length} atkı · Toplam {totalCols}×{totalRows}
    </span>
  );
}

// ============================================================
// Ana component
// ============================================================

export function DesenTab({ desen: d, onChange }: DesenTabProps) {
  // Section 33: Desen önizlemesi için renkli mod toggle (boş hücreyi atkı iro
  // rengiyle doldur). Lokal state — persist YOK.
  const [colored, setColored] = useState(false);

  const dimStep =
    (dim: "warpCount" | "weftCount" | "frameCount" | "iroCount"): ((v: number) => void) =>
    (v) =>
      onChange(setDimension(d, dim, v));
  const rapor =
    (key: "raporX" | "raporY"): ((v: number) => void) =>
    (v) =>
      onChange({ ...d, [key]: Math.max(1, Math.min(8, v)) });

  return (
    <>
      <Card title="Desen Boyutları" icon={<Grid3x3 size={16} color={C.accent} />}>
        <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
          <Stepper
            label="Çözgü (warp)"
            value={d.warpCount}
            min={MIN_WARP}
            max={MAX_WARP}
            onChange={dimStep("warpCount")}
          />
          <Stepper
            label="Atkı (weft)"
            value={d.weftCount}
            min={MIN_WEFT}
            max={MAX_WEFT}
            onChange={dimStep("weftCount")}
          />
          <Stepper
            label="Çerçeve"
            value={d.frameCount}
            min={MIN_FRAME}
            max={MAX_FRAME}
            onChange={dimStep("frameCount")}
          />
          <Stepper
            label="İro (renk)"
            value={d.iroCount}
            min={MIN_IRO}
            max={MAX_IRO}
            onChange={dimStep("iroCount")}
          />
          <Stepper label="Rapor X" value={d.raporX} min={1} max={8} onChange={rapor("raporX")} />
          <Stepper label="Rapor Y" value={d.raporY} min={1} max={8} onChange={rapor("raporY")} />
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
          <button
            onClick={() => onChange({ ...d, tahar: buildDuzTahar(d.warpCount, d.frameCount) })}
            style={{ ...btnAdd(C.accent), width: "auto", marginTop: 0 }}
          >
            <Wand2 size={14} /> Düz tahar
          </button>
          <button
            onClick={() => onChange({ ...d, armur: buildEmptyArmur(d.frameCount, d.weftCount) })}
            style={{ ...btnAdd(C.dim), width: "auto", marginTop: 0 }}
          >
            <Eraser size={14} /> Armür temizle
          </button>
        </div>
      </Card>

      <Card
        title="Tahar — çözgü hangi çerçeveden"
        icon={<Grid3x3 size={16} color={C.warp} />}
        accent={C.warp}
      >
        <TaharGrid desen={d} onChange={onChange} />
      </Card>

      <Card
        title="Armür + Atkı raporu — döngülü"
        icon={<Grid3x3 size={16} color={C.accent} />}
        accent={C.accent}
      >
        <ArmurAtkiSection desen={d} onChange={onChange} />
      </Card>

      <Card
        title="Döngüler (DO N … NEXT)"
        icon={<Repeat size={16} color={C.bad} />}
        accent={C.bad}
      >
        <LoopForm desen={d} onChange={onChange} />
      </Card>

      <Card title="Desen — döngüler expand edilmiş" icon={<Grid3x3 size={16} color={C.text} />}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 10,
            flexWrap: "wrap",
          }}
        >
          <DesenInfo d={d} />
          <button
            type="button"
            onClick={() => setColored((v) => !v)}
            title="Boş hücreleri atkı iro rengiyle doldur"
            style={{
              marginLeft: "auto",
              fontSize: 12,
              padding: "5px 12px",
              borderRadius: 6,
              border: `1px solid ${colored ? C.accent : C.line}`,
              background: colored
                ? `color-mix(in oklch, ${C.accent} 18%, transparent)`
                : C.panel,
              color: colored ? C.accent : C.text,
              cursor: "pointer",
              fontFamily: "inherit",
              fontWeight: colored ? 600 : 400,
            }}
          >
            Renkli: {colored ? "açık" : "kapalı"}
          </button>
        </div>
        <DesenPreview d={d} colored={colored} />
      </Card>
    </>
  );
}
