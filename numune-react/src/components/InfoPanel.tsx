import { Info, Plus, Trash2 } from "lucide-react";
import type { IplikContent, IplikInfo } from "../lib/types";
import { num } from "../lib/calc";
import { fmt } from "../lib/format";
import { C } from "../theme";
import { Field } from "./Field";

const MAX_CONTENTS = 6;
const ELYAF_LIST = ["PES", "LI", "CO", "VIS", "PAN", "WO"];

interface InfoPanelProps {
  info: IplikInfo;
  contents: IplikContent[];
  onChange: (info: IplikInfo) => void;
  onContentsChange: (contents: IplikContent[]) => void;
  color: string;
}

export function InfoPanel({ info, contents, onChange, onContentsChange, color }: InfoPanelProps) {
  const setContent = (i: number, patch: Partial<IplikContent>) => {
    onContentsChange(contents.map((c, idx) => (idx === i ? { ...c, ...patch } : c)));
  };
  const removeContent = (i: number) => {
    onContentsChange(contents.filter((_, idx) => idx !== i));
  };
  const addContent = () => {
    if (contents.length >= MAX_CONTENTS) return;
    onContentsChange([...contents, { elyaf: "", oran: "" }]);
  };

  const toplam = contents.reduce((s, c) => s + num(c.oran), 0);
  const toplamRenk = contents.length === 0 ? C.dim : Math.abs(toplam - 100) < 0.01 ? C.ok : C.warn;

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
      {/* Tum elyaf input'lari icin tek datalist */}
      <datalist id="elyaf-list">
        {ELYAF_LIST.map((e) => (
          <option key={e} value={e} />
        ))}
      </datalist>

      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
        <Info size={14} color={color} />
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            color,
            letterSpacing: 0.5,
            textTransform: "uppercase",
          }}
        >
          İplik bilgisi
        </span>
        <span style={{ marginLeft: "auto", fontSize: 10, color: C.dim }}>
          ana maliyeti etkilemez
        </span>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Field
          label="İplik adı"
          value={info.iplikAdi}
          onChange={(v) => onChange({ ...info, iplikAdi: v })}
          placeholder="örn. pamuk 30/1"
        />
        <Field
          label="Firma adı"
          value={info.firmaAdi}
          onChange={(v) => onChange({ ...info, firmaAdi: v })}
        />
      </div>

      <label
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginTop: 12,
          cursor: "pointer",
          fontSize: 13,
          color: C.text,
        }}
      >
        <input
          type="checkbox"
          checked={info.fason}
          onChange={(e) => onChange({ ...info, fason: e.target.checked })}
          style={{ width: 16, height: 16, accentColor: color, cursor: "pointer" }}
        />
        Fason işlem var
      </label>

      {info.fason && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
          <Field
            label="Fason firma"
            value={info.fasonFirma}
            onChange={(v) => onChange({ ...info, fasonFirma: v })}
          />
          <Field
            label="Fason işlem"
            value={info.fasonIslem}
            onChange={(v) => onChange({ ...info, fasonIslem: v })}
            placeholder="örn. büküm"
          />
          <Field
            label="Fason fiyat"
            value={info.fasonFiyat}
            onChange={(v) => onChange({ ...info, fasonFiyat: v })}
          />
        </div>
      )}

      {/* IÇERIK (elyaf cinsi + oran) */}
      <div
        style={{
          marginTop: 14,
          paddingTop: 10,
          borderTop: `1px dashed ${color}44`,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            marginBottom: 6,
          }}
        >
          <span style={{ fontSize: 11, fontWeight: 700, color: C.text, letterSpacing: 0.3 }}>
            İçerik (elyaf cinsi ve oranı)
          </span>
          <span style={{ marginLeft: "auto", fontSize: 10, color: toplamRenk, fontWeight: 700 }}>
            {contents.length > 0
              ? `Toplam: %${fmt(toplam, 1)}${Math.abs(toplam - 100) < 0.01 ? " ✓" : ""}`
              : "max 6 içerik"}
          </span>
        </div>

        {contents.map((c, i) => (
          <div
            key={i}
            style={{ display: "flex", gap: 6, alignItems: "flex-end", marginTop: 6 }}
          >
            <label style={{ display: "flex", flexDirection: "column", gap: 4, width: 110 }}>
              <span style={{ fontSize: 11, color: C.dim }}>Elyaf</span>
              <input
                list="elyaf-list"
                value={c.elyaf}
                onChange={(e) =>
                  setContent(i, { elyaf: e.target.value.toUpperCase() })
                }
                placeholder="PES"
                style={{
                  background: C.bg,
                  border: `1px solid ${C.line}`,
                  borderRadius: 8,
                  color: C.text,
                  padding: "9px 10px",
                  fontSize: 13,
                  fontFamily: "ui-monospace, monospace",
                  textTransform: "uppercase",
                  outline: "none",
                  width: "100%",
                }}
              />
            </label>
            <div style={{ flex: 1 }}>
              <Field
                label="Oran"
                value={c.oran}
                onChange={(v) => setContent(i, { oran: v })}
                suffix="%"
                placeholder="0"
              />
            </div>
            <button
              onClick={() => removeContent(i)}
              title="Sil"
              style={{
                width: 38,
                height: 38,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "transparent",
                border: `1px solid ${C.line}`,
                borderRadius: 8,
                color: C.bad,
                cursor: "pointer",
                marginBottom: 1,
              }}
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}

        <button
          onClick={addContent}
          disabled={contents.length >= MAX_CONTENTS}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            marginTop: 8,
            padding: "8px 14px",
            background: contents.length >= MAX_CONTENTS ? "transparent" : `${color}1c`,
            border: `1px solid ${color}66`,
            color: contents.length >= MAX_CONTENTS ? C.dim : color,
            borderRadius: 8,
            cursor: contents.length >= MAX_CONTENTS ? "not-allowed" : "pointer",
            fontWeight: 600,
            fontSize: 12,
            opacity: contents.length >= MAX_CONTENTS ? 0.5 : 1,
          }}
        >
          <Plus size={14} /> İçerik ekle
          {contents.length >= MAX_CONTENTS ? " (max 6)" : ""}
        </button>
      </div>
    </div>
  );
}
