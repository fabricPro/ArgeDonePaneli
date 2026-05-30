import { Trash2, Scale, ChevronUp, ChevronDown, Info } from "lucide-react";
import { parseIplikRaw, num } from "../lib/calc";
import { fmt } from "../lib/format";
import { TIPLER, type IplikTip } from "../lib/fpd";
import type { Iplik } from "../lib/types";
import { C } from "../theme";
import { useIsMobile } from "../lib/useIsMobile";
import { Field } from "./Field";
import { OlcumPanel } from "./OlcumPanel";
import { InfoPanel } from "./InfoPanel";

interface IplikRowProps {
  row: Iplik;
  onChange: (row: Iplik) => void;
  onDelete: () => void;
  sikLabel: string;
  color: string;
}

export function IplikRow({ row, onChange, onDelete, sikLabel, color }: IplikRowProps) {
  const isMobile = useIsMobile();
  const { denye, kat } = parseIplikRaw(row.raw);
  const olcumDolu = num(row.olcum.agirlik) > 0 && num(row.olcum.uzunluk) > 0;

  const applyOlcum = (sistem: IplikTip, val: number) => {
    const cKat = parseIplikRaw(row.raw).kat;
    const rounded =
      sistem === "DENYE" || sistem === "DTEX"
        ? Math.round(val * 10) / 10
        : Math.round(val * 100) / 100;
    const newRaw = cKat > 1 ? `${rounded}*${cKat}` : `${rounded}`;
    onChange({ ...row, tip: sistem, raw: newRaw });
  };

  const tipSelect = (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, width: 88 }}>
      <span style={{ fontSize: 11, color: C.dim }}>Tip</span>
      <select
        value={row.tip}
        onChange={(e) => onChange({ ...row, tip: e.target.value as IplikTip })}
        style={{
          background: C.bg,
          border: `1px solid ${C.line}`,
          borderRadius: 8,
          color: C.text,
          padding: "9px 6px",
          fontSize: 13,
        }}
      >
        {TIPLER.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
    </label>
  );

  const iplikNo = (
    <span style={{ display: "block", marginTop: 4, fontSize: 10, color: C.dim }}>
      → no {fmt(denye, 0)} · {kat} kat
      {olcumDolu && (
        <span style={{ color }}>
          {"  ·  ölçüm "}
          {fmt(num(row.olcum.uzunluk), 0)}cm×{fmt(num(row.olcum.adet), 0)} / {fmt(num(row.olcum.agirlik), 1)}mg
        </span>
      )}
    </span>
  );

  const toggleOlcum = () =>
    onChange({ ...row, olcum: { ...row.olcum, acik: !row.olcum.acik } });

  const olcumBtnBg = row.olcum.acik
    ? `${color}25`
    : olcumDolu
      ? `${color}12`
      : "transparent";

  const olcumPanelEl = row.olcum.acik && (
    <OlcumPanel
      olcum={row.olcum}
      color={color}
      onChange={(o) => onChange({ ...row, olcum: { ...o, acik: true } })}
      onApply={applyOlcum}
    />
  );

  const infoDolu = !!(row.info.iplikAdi || row.info.firmaAdi || row.info.fason);
  const toggleInfo = () =>
    onChange({ ...row, info: { ...row.info, acik: !row.info.acik } });
  const infoBtnBg = row.info.acik ? `${color}25` : infoDolu ? `${color}12` : "transparent";
  const infoPanelEl = row.info.acik && (
    <InfoPanel
      info={row.info}
      contents={row.contents}
      color={color}
      onChange={(i) => onChange({ ...row, info: { ...i, acik: true } })}
      onContentsChange={(contents) => onChange({ ...row, contents })}
    />
  );

  // ---- Mobil duzen: dikey gruplar ----
  if (isMobile) {
    return (
      <div style={{ padding: "12px 0", borderBottom: `1px solid ${C.line}` }}>
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ width: 4, alignSelf: "stretch", background: color, borderRadius: 2 }} />
          <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              {tipSelect}
              <div style={{ flex: 1, minWidth: 0 }}>
                <Field
                  label="İplik (örn 300*2)"
                  value={row.raw}
                  onChange={(v) => onChange({ ...row, raw: v })}
                  placeholder="kalınlık*kat"
                />
                {iplikNo}
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <Field
                label={sikLabel}
                value={row.sik}
                onChange={(v) => onChange({ ...row, sik: v })}
                suffix="ad/cm"
              />
              <Field
                label="Fiyat"
                value={row.fiyat}
                onChange={(v) => onChange({ ...row, fiyat: v })}
                suffix="$/kg"
              />
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={toggleOlcum}
                title="İplik ölçüm hesaplayıcı"
                style={{
                  flex: 1,
                  height: 40,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                  background: olcumBtnBg,
                  border: `1px solid ${olcumDolu ? color + "66" : C.line}`,
                  borderRadius: 8,
                  color: olcumDolu ? color : C.dim,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                <Scale size={15} /> İplik ölç
                {row.olcum.acik ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              <button
                onClick={toggleInfo}
                title="İplik bilgisi (ad / firma / fason)"
                style={{
                  width: 46,
                  height: 40,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: infoBtnBg,
                  border: `1px solid ${infoDolu ? color + "66" : C.line}`,
                  borderRadius: 8,
                  color: infoDolu ? color : C.dim,
                  cursor: "pointer",
                }}
              >
                <Info size={17} />
              </button>
              <button
                onClick={onDelete}
                title="Sil"
                style={{
                  width: 46,
                  height: 40,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "transparent",
                  border: `1px solid ${C.line}`,
                  borderRadius: 8,
                  color: C.bad,
                  cursor: "pointer",
                }}
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        </div>
        {olcumPanelEl}
        {infoPanelEl}
      </div>
    );
  }

  // ---- Desktop duzen: tek yatay satir ----
  return (
    <div style={{ padding: "10px 0", borderBottom: `1px solid ${C.line}` }}>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
        <div style={{ width: 4, alignSelf: "stretch", background: color, borderRadius: 2 }} />
        {tipSelect}
        <div style={{ flex: 1.2 }}>
          <Field
            label="İplik (örn 300*2)"
            value={row.raw}
            onChange={(v) => onChange({ ...row, raw: v })}
            placeholder="kalınlık*kat"
          />
          {iplikNo}
        </div>
        <Field
          label={sikLabel}
          value={row.sik}
          onChange={(v) => onChange({ ...row, sik: v })}
          w={92}
          suffix="ad/cm"
        />
        <Field
          label="Fiyat"
          value={row.fiyat}
          onChange={(v) => onChange({ ...row, fiyat: v })}
          w={88}
          suffix="$/kg"
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span aria-hidden style={{ fontSize: 11, visibility: "hidden", userSelect: "none" }}>
            ·
          </span>
          <button
            onClick={toggleInfo}
            title="İplik bilgisi (ad / firma / fason)"
            style={{
              height: 38,
              width: 38,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: infoBtnBg,
              border: `1px solid ${infoDolu ? color + "66" : C.line}`,
              borderRadius: 8,
              color: infoDolu ? color : C.dim,
              cursor: "pointer",
            }}
          >
            <Info size={16} />
          </button>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span aria-hidden style={{ fontSize: 11, visibility: "hidden", userSelect: "none" }}>
            ·
          </span>
          <button
            onClick={toggleOlcum}
            title="İplik ölçüm hesaplayıcı"
            style={{
              height: 38,
              background: olcumBtnBg,
              border: `1px solid ${olcumDolu ? color + "66" : C.line}`,
              borderRadius: 8,
              color: olcumDolu ? color : C.dim,
              padding: "0 8px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            <Scale size={14} />{" "}
            {row.olcum.acik ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span aria-hidden style={{ fontSize: 11, visibility: "hidden", userSelect: "none" }}>
            ·
          </span>
          <button
            onClick={onDelete}
            title="Sil"
            style={{
              height: 38,
              width: 38,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "transparent",
              border: `1px solid ${C.line}`,
              borderRadius: 8,
              color: C.bad,
              cursor: "pointer",
            }}
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
      {olcumPanelEl}
      {infoPanelEl}
    </div>
  );
}
