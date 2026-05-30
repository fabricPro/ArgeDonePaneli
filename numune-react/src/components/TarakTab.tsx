import { useState, type CSSProperties } from "react";
import {
  Settings,
  BarChart3,
  Grid3x3,
  FileText,
  Copy,
  Check,
  RefreshCcw,
  ArrowRight,
} from "lucide-react";
import type { TarakState } from "../lib/types";
import {
  calcTarakSummary,
  calcHint,
  syncDentThreads,
  incThread,
  resetThreads,
  rle,
  rleToText,
  parseN,
  MIN_SIKLIK,
  MAX_SIKLIK,
} from "../lib/tarak";
import { C } from "../theme";
import { Card } from "./Card";

interface TarakTabProps {
  tarak: TarakState;
  onChange: (t: TarakState) => void;
  /** Köprü: Çözgü sıklığı + rapor cm bilgisini analiz/desen tarafına ilet.
   *  Opsiyonel — verilmezse buton görünmez. */
  onSendToDesen?: (info: { cozguSiklik: number; raporCm: number; warpCount: number }) => void;
}

const inputCss: CSSProperties = {
  width: "100%",
  height: 32,
  padding: "4px 10px",
  borderRadius: 6,
  border: `1px solid ${C.line}`,
  background: C.bg,
  color: C.text,
  fontFamily: "ui-monospace, monospace",
  fontSize: 13,
};
const labelCss: CSSProperties = { fontSize: 11, color: C.dim, marginBottom: 4, display: "block" };

const statCard = (label: string, value: string, accent?: string): React.ReactNode => (
  <div
    style={{
      background: C.panel2,
      borderRadius: 8,
      padding: "10px 12px",
      display: "flex",
      flexDirection: "column",
      gap: 2,
      minWidth: 110,
      flex: 1,
    }}
  >
    <span
      style={{
        fontSize: 9,
        color: C.dim,
        letterSpacing: 1.2,
        textTransform: "uppercase",
        fontWeight: 600,
      }}
    >
      {label}
    </span>
    <span
      style={{
        fontSize: 18,
        fontWeight: 700,
        fontFamily: "ui-monospace, monospace",
        color: accent ?? C.text,
      }}
    >
      {value}
    </span>
  </div>
);

function Stats({ tarak }: { tarak: TarakState }) {
  const s = calcTarakSummary(tarak);
  const fmt = (n: number, d = 2) => (n > 0 ? n.toFixed(d) : "—");
  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
      {statCard("Sıklık", s.siklik > 0 ? String(s.siklik) : "—")}
      {statCard("Rapor diş", s.dis > 0 ? String(s.dis) : "—")}
      {statCard("Toplam tel", String(s.toplamTel), C.accent)}
      {statCard("Ort. tel/diş", fmt(s.ortTelDis))}
      {statCard("Çözgü sıklığı", s.cozguSiklik > 0 ? `${s.cozguSiklik.toFixed(2)} tel/cm` : "—", C.ok)}
      {statCard("Rapor cm", s.raporCm > 0 ? `${s.raporCm.toFixed(4)} cm` : "—")}
    </div>
  );
}

function DentGrid({ tarak, onChange }: { tarak: TarakState; onChange: (t: TarakState) => void }) {
  const dis = tarak.dentThreads.length;
  if (dis === 0) {
    return (
      <div
        style={{
          padding: 30,
          textAlign: "center",
          color: C.dim,
          fontSize: 13,
          fontStyle: "italic",
        }}
      >
        Tarak sıklığı ve rapor değerini girin
      </div>
    );
  }

  const cellW = Math.max(20, Math.min(40, Math.floor(620 / dis)));
  const maxThread = Math.max(1, ...tarak.dentThreads, 3);

  return (
    <div style={{ overflowX: "auto" }}>
      {/* Hücreler */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${dis}, ${cellW}px)`,
          gap: 2,
        }}
      >
        {tarak.dentThreads.map((cnt, i) => {
          const filled = cnt > 0;
          const bg = filled ? C.bad : C.panel2;
          const tx = filled ? "#fff" : C.dim;
          return (
            <div
              key={i}
              onClick={() => onChange(incThread(tarak, i, +1))}
              onContextMenu={(ev) => {
                ev.preventDefault();
                onChange(incThread(tarak, i, -1));
              }}
              style={{
                width: cellW,
                height: cellW,
                borderRadius: 3,
                background: bg,
                color: tx,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: cellW > 26 ? 13 : 11,
                fontWeight: 700,
                cursor: "pointer",
                userSelect: "none",
                fontFamily: "ui-monospace, monospace",
              }}
            >
              {cnt}
            </div>
          );
        })}
      </div>
      {/* Numara satırı */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${dis}, ${cellW}px)`,
          gap: 2,
          marginTop: 4,
        }}
      >
        {tarak.dentThreads.map((_, i) => (
          <div
            key={i}
            style={{
              height: 14,
              textAlign: "center",
              fontSize: 10,
              color: C.dim,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "ui-monospace, monospace",
            }}
          >
            {i + 1}
          </div>
        ))}
      </div>
      {/* Bar chart */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${dis}, ${cellW}px)`,
          gap: 2,
          marginTop: 8,
        }}
      >
        {tarak.dentThreads.map((cnt, i) => {
          const h = cnt === 0 ? 6 : Math.max(8, Math.round((cnt / maxThread) * 36));
          const empty = cnt === 0;
          return (
            <div
              key={i}
              style={{
                height: 42,
                display: "flex",
                alignItems: "flex-end",
                justifyContent: "center",
              }}
            >
              <div
                style={{
                  width: "100%",
                  height: h,
                  background: empty ? "transparent" : C.bad,
                  border: empty ? `1px dashed ${C.line}` : "none",
                  borderRadius: 3,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 10,
                  fontWeight: 700,
                  color: empty ? C.dim : "#fff",
                  fontFamily: "ui-monospace, monospace",
                }}
              >
                {empty ? "" : cnt}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Report({
  tarak,
  onSendToDesen,
}: {
  tarak: TarakState;
  onSendToDesen?: TarakTabProps["onSendToDesen"];
}) {
  const [copied, setCopied] = useState(false);
  const s = calcTarakSummary(tarak);
  if (s.dis === 0) return null;

  const groups = rle(tarak.dentThreads);
  const handleCopy = async () => {
    const txt = rleToText(tarak.dentThreads);
    try {
      await navigator.clipboard.writeText(txt);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      /* ignore */
    }
  };

  const handleSend = () => {
    if (!onSendToDesen) return;
    onSendToDesen({
      cozguSiklik: s.cozguSiklik,
      raporCm: s.raporCm,
      // warpCount önerisi: rapor cm'i 1 cm gibi varsayıp tel/cm'i kullan
      // Bu sadece pratik bir öneri — kullanıcı DesenTab'da değiştirebilir.
      warpCount: Math.max(2, Math.min(120, Math.round(s.toplamTel))),
    });
  };

  return (
    <>
      <div
        style={{
          fontSize: 11,
          color: C.dim,
          paddingBottom: 8,
          borderBottom: `1px solid ${C.line}`,
          marginBottom: 8,
          fontFamily: "ui-monospace, monospace",
        }}
      >
        Tarak sıklığı: {s.siklik} diş/cm · Rapor diş: {s.dis} · Rapor cm:{" "}
        {s.raporCm.toFixed(4)} · Grup sayısı: {groups.length}
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {groups.map((g, idx) => {
          const res = g.dis * g.tel;
          const empty = g.tel === 0;
          return (
            <div
              key={idx}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "5px 10px",
                fontSize: 13,
                fontFamily: "ui-monospace, monospace",
                background: idx % 2 === 0 ? C.panel2 : "transparent",
                borderRadius: 4,
                opacity: empty ? 0.55 : 1,
              }}
            >
              <span style={{ fontSize: 10, color: C.dim, minWidth: 30 }}>#{idx + 1}</span>
              <span style={{ color: C.dim, minWidth: 56 }}>{g.dis} diş</span>
              <span style={{ color: C.dim, width: 12, textAlign: "center" }}>×</span>
              <span
                style={{
                  minWidth: 56,
                  color: empty ? C.dim : C.warp,
                  fontWeight: empty ? 400 : 700,
                  fontStyle: empty ? "italic" : "normal",
                }}
              >
                {g.tel} tel
              </span>
              <span style={{ color: C.dim, width: 12, textAlign: "center" }}>=</span>
              <span style={{ color: C.bad, fontWeight: 700, flex: 1 }}>
                {empty ? "boş" : `${res} tel`}
              </span>
            </div>
          );
        })}
      </div>

      <div
        style={{
          display: "flex",
          gap: 10,
          marginTop: 12,
          paddingTop: 10,
          borderTop: `1px solid ${C.line}`,
          flexWrap: "wrap",
        }}
      >
        <div style={{ flex: 1, minWidth: 110 }}>{statCard("Toplam diş", String(s.dis))}</div>
        <div style={{ flex: 1, minWidth: 110 }}>
          {statCard("Toplam tel", String(s.toplamTel), C.accent)}
        </div>
        <div style={{ flex: 1, minWidth: 140 }}>
          {statCard(
            "Çözgü sıklığı",
            s.cozguSiklik > 0 ? `${s.cozguSiklik.toFixed(2)} tel/cm` : "—",
            C.ok,
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
        <button
          onClick={handleCopy}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "8px 12px",
            background: C.panel2,
            border: `1px solid ${C.line}`,
            color: C.text,
            borderRadius: 8,
            cursor: "pointer",
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
          {copied ? "Kopyalandı" : "RLE kopyala"}
        </button>
        {onSendToDesen && (
          <button
            onClick={handleSend}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 12px",
              background: `${C.ok}1c`,
              border: `1px solid ${C.ok}66`,
              color: C.ok,
              borderRadius: 8,
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            <ArrowRight size={14} />
            Desen tab'a aktar
          </button>
        )}
      </div>
    </>
  );
}

// ============================================================
// Ana component
// ============================================================

export function TarakTab({ tarak, onChange, onSendToDesen }: TarakTabProps) {
  const hint = calcHint(tarak);

  const updateSiklik = (v: string) => {
    onChange(syncDentThreads({ ...tarak, siklik: v }));
  };
  const updateRaporDis = (v: string) => {
    onChange(syncDentThreads({ ...tarak, raporDis: v, mode: "dis" }));
  };
  const updateRaporCm = (v: string) => {
    onChange(syncDentThreads({ ...tarak, raporCm: v, mode: "cm" }));
  };
  const switchMode = (m: "dis" | "cm") => {
    onChange(syncDentThreads({ ...tarak, mode: m }));
  };

  return (
    <>
      <Card title="Tarak Parametreleri" icon={<Settings size={16} color={C.accent} />} accent={C.accent}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr auto",
            gap: 12,
            alignItems: "end",
          }}
        >
          <div>
            <label style={labelCss}>Tarak sıklığı (diş/cm)</label>
            <input
              type="number"
              min={MIN_SIKLIK}
              max={MAX_SIKLIK}
              step={0.1}
              value={tarak.siklik}
              onChange={(ev) => updateSiklik(ev.target.value)}
              placeholder="örn: 8"
              style={inputCss}
            />
          </div>
          {tarak.mode === "dis" ? (
            <div>
              <label style={labelCss}>
                Rapor diş <span style={{ color: C.dim }}>→ cm hesaplanır</span>
              </label>
              <input
                type="number"
                min={1}
                max={500}
                value={tarak.raporDis}
                onChange={(ev) => updateRaporDis(ev.target.value)}
                placeholder="örn: 16"
                style={inputCss}
              />
            </div>
          ) : (
            <div>
              <label style={labelCss}>
                Rapor cm <span style={{ color: C.dim }}>→ diş hesaplanır</span>
              </label>
              <input
                type="number"
                min={0.001}
                max={9999}
                step={0.001}
                value={tarak.raporCm}
                onChange={(ev) => updateRaporCm(ev.target.value)}
                placeholder="örn: 2"
                style={inputCss}
              />
            </div>
          )}
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <div
              style={{
                display: "inline-flex",
                border: `1px solid ${C.line}`,
                borderRadius: 8,
                overflow: "hidden",
                background: C.bg,
              }}
            >
              {(["dis", "cm"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => switchMode(m)}
                  style={{
                    padding: "8px 14px",
                    fontSize: 12,
                    border: "none",
                    background: tarak.mode === m ? C.accent : "transparent",
                    color: tarak.mode === m ? "#fff" : C.dim,
                    cursor: "pointer",
                    fontWeight: 600,
                  }}
                >
                  {m === "dis" ? "Diş" : "cm"}
                </button>
              ))}
            </div>
            <button
              onClick={() => onChange(resetThreads(tarak))}
              disabled={tarak.dentThreads.length === 0}
              title="Tüm dişleri sıfırla"
              style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                border: `1px solid ${C.line}`,
                background: C.bg,
                color: C.dim,
                cursor: tarak.dentThreads.length === 0 ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <RefreshCcw size={15} />
            </button>
          </div>
        </div>
        {hint && (
          <div
            style={{
              fontSize: 11,
              color: C.dim,
              fontFamily: "ui-monospace, monospace",
              marginTop: 8,
            }}
          >
            <span style={{ color: C.text }}>{hint.from}</span> ={" "}
            <span style={{ color: C.ok, fontWeight: 700 }}>{hint.to}</span>
          </div>
        )}
      </Card>

      <Card title="Hesaplanan Değerler" icon={<BarChart3 size={16} color={C.accent} />}>
        <Stats tarak={tarak} />
      </Card>

      <Card
        title="Diş Dizimi"
        icon={<Grid3x3 size={16} color={C.bad} />}
        accent={C.bad}
      >
        <div
          style={{
            fontSize: 10,
            color: C.dim,
            marginBottom: 8,
            fontStyle: "italic",
          }}
        >
          Sol tık → +1 tel · Sağ tık → −1 tel
        </div>
        <DentGrid tarak={tarak} onChange={onChange} />
      </Card>

      {parseN(tarak.siklik) > 0 && tarak.dentThreads.length > 0 && (
        <Card title="Tarak Raporu" icon={<FileText size={16} color={C.warp} />} accent={C.warp}>
          <Report tarak={tarak} onSendToDesen={onSendToDesen} />
        </Card>
      )}
    </>
  );
}
