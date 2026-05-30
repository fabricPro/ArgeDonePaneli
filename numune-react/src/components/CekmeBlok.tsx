import { cekmeOran, num } from "../lib/calc";
import { fmt } from "../lib/format";
import type { CekmePair } from "../lib/types";
import { C } from "../theme";
import { Field } from "./Field";

interface CekmeBlokProps {
  label: string;
  data: CekmePair;
  onChange: (d: CekmePair) => void;
  color: string;
}

export function CekmeBlok({ label, data, onChange, color }: CekmeBlokProps) {
  const oran = cekmeOran(num(data.lDuz), num(data.lKumas)) * 100;
  return (
    <div
      style={{
        background: C.bg,
        border: `1px solid ${C.line}`,
        borderRadius: 10,
        padding: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
        <span style={{ width: 8, height: 8, borderRadius: 2, background: color }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: C.text }}>{label}</span>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <Field
          label="L düz (sökülmüş)"
          value={data.lDuz}
          onChange={(v) => onChange({ ...data, lDuz: v })}
          suffix="mm/cm"
        />
        <Field
          label="L kumaş (içinde)"
          value={data.lKumas}
          onChange={(v) => onChange({ ...data, lKumas: v })}
          suffix="mm/cm"
        />
      </div>
      <div
        style={{
          marginTop: 10,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontSize: 11, color: C.dim }}>(L düz − L kumaş) / L düz</span>
        <span
          style={{
            fontSize: 18,
            fontWeight: 700,
            color,
            fontFamily: "ui-monospace, monospace",
          }}
        >
          %{fmt(oran)}
        </span>
      </div>
    </div>
  );
}
