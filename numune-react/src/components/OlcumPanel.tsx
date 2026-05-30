import { Scale } from "lucide-react";
import { olcumKalinlik, num } from "../lib/calc";
import { fmt } from "../lib/format";
import type { OlcumState } from "../lib/types";
import type { IplikTip } from "../lib/fpd";
import { C } from "../theme";
import { useIsMobile } from "../lib/useIsMobile";
import { Field } from "./Field";

interface OlcumPanelProps {
  olcum: OlcumState;
  onChange: (o: OlcumState) => void;
  onApply: (sistem: IplikTip, val: number) => void;
  color: string;
}

export function OlcumPanel({ olcum, onChange, onApply, color }: OlcumPanelProps) {
  const isMobile = useIsMobile();
  const res = olcumKalinlik(olcum.uzunluk, olcum.adet, olcum.agirlik);
  const sistemler: { key: IplikTip; val: number; fmt: number; hint: string }[] = [
    { key: "DENYE", val: res.denye, fmt: 1, hint: "g/9000m" },
    { key: "DTEX", val: res.dtex, fmt: 1, hint: "g/10000m" },
    { key: "NM", val: res.nm, fmt: 2, hint: "m/g" },
    { key: "NE", val: res.ne, fmt: 2, hint: "hank/lb" },
  ];
  return (
    <div
      style={{
        background: C.bg,
        border: `1px solid ${color}33`,
        borderRadius: 10,
        padding: 12,
        marginTop: 6,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
        <Scale size={14} color={color} />
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            color,
            letterSpacing: 0.5,
            textTransform: "uppercase",
          }}
        >
          İplik ölçümü — sök, ölç, tart
        </span>
      </div>
      <div
        style={
          isMobile
            ? { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 12 }
            : { display: "flex", gap: 8, marginBottom: 12 }
        }
      >
        <Field
          label="Uzunluk"
          value={olcum.uzunluk}
          onChange={(v) => onChange({ ...olcum, uzunluk: v })}
          suffix="cm"
        />
        <Field
          label="Adet"
          value={olcum.adet}
          onChange={(v) => onChange({ ...olcum, adet: v })}
          w={70}
          suffix="ad"
        />
        <Field
          label="Ağırlık"
          value={olcum.agirlik}
          onChange={(v) => onChange({ ...olcum, agirlik: v })}
          suffix="mg"
        />
      </div>
      <div style={{ fontSize: 10, color: C.dim, marginBottom: 8 }}>
        Hesaplanan kalınlık (uygulamak için tıkla):
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: isMobile ? "repeat(2,1fr)" : "repeat(4,1fr)",
          gap: 8,
        }}
      >
        {sistemler.map((s) => {
          const active = res.ok;
          return (
            <button
              key={s.key}
              disabled={!active}
              onClick={() => onApply(s.key, s.val)}
              style={{
                background: active ? `${color}18` : C.panel2,
                border: `1px solid ${active ? color + "66" : C.line}`,
                borderRadius: 8,
                padding: "8px 6px",
                cursor: active ? "pointer" : "not-allowed",
                textAlign: "left",
                color: C.text,
                transition: "all .15s",
              }}
              onMouseEnter={(e) => {
                if (active) e.currentTarget.style.background = `${color}30`;
              }}
              onMouseLeave={(e) => {
                if (active) e.currentTarget.style.background = `${color}18`;
              }}
            >
              <div
                style={{
                  fontSize: 10,
                  color: active ? color : C.dim,
                  fontWeight: 700,
                  letterSpacing: 0.8,
                }}
              >
                {s.key}
              </div>
              <div
                style={{
                  fontSize: 17,
                  fontWeight: 700,
                  fontFamily: "ui-monospace, monospace",
                  color: active ? C.text : C.dim,
                  lineHeight: 1.2,
                }}
              >
                {active ? fmt(s.val, s.fmt) : "—"}
              </div>
              <div style={{ fontSize: 9, color: C.dim }}>{s.hint}</div>
            </button>
          );
        })}
      </div>
      {res.ok && (
        <div
          style={{
            fontSize: 10,
            color: C.dim,
            marginTop: 8,
            fontFamily: "ui-monospace, monospace",
          }}
        >
          efektif uzunluk: {fmt(num(olcum.uzunluk) * Math.max(1, num(olcum.adet)), 0)} cm
          {" · "}1m ağırlık:{" "}
          {fmt(
            (num(olcum.agirlik) / (num(olcum.uzunluk) * Math.max(1, num(olcum.adet)))) * 100,
            2,
          )}{" "}
          mg
        </div>
      )}
    </div>
  );
}
