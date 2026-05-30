import { useMemo } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import {
  Calculator,
  Activity,
  FlaskConical,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { calcKumasIcerik, num } from "../lib/calc";
import { fmt } from "../lib/format";
import type { AnalizState, CalcResult } from "../lib/types";
import { C } from "../theme";
import { useIsMobile } from "../lib/useIsMobile";
import { Card } from "./Card";
import { Field } from "./Field";

interface MaliyetTabProps {
  state: AnalizState;
  set: (patch: Partial<AnalizState>) => void;
  r: CalcResult;
}

export function MaliyetTab({ state, set, r }: MaliyetTabProps) {
  const isMobile = useIsMobile();
  const icerik = useMemo(() => calcKumasIcerik(state, r), [state, r]);
  const sapmaAbs = r.sapma == null ? null : Math.abs(r.sapma);
  const durum: { c: string; t: string; Icon: LucideIcon } =
    sapmaAbs == null
      ? { c: C.dim, t: "Ölçülen m² gramajı girin", Icon: AlertTriangle }
      : sapmaAbs <= 5
        ? { c: C.ok, t: "Tutarlı — analiz doğru", Icon: CheckCircle2 }
        : sapmaAbs <= 10
          ? { c: C.warn, t: "Sınırda — kontrol et", Icon: AlertTriangle }
          : { c: C.bad, t: "Tutmuyor — sayım/kalınlık/çekme'yi gözden geçir", Icon: XCircle };

  const donut = [
    { name: "İplik", value: r.topI, fill: C.accent },
    { name: "İşçilik", value: r.fasI, fill: C.warp },
    { name: "Terbiye", value: r.terbM, fill: C.weft },
    { name: "Fire", value: r.fireM, fill: C.bad },
    { name: "Kurşum+Ek", value: num(state.params.kursum) + num(state.params.ekMal), fill: C.dim },
  ].filter((d) => d.value > 0);

  const breakdown: Array<[string, number, string]> = [
    ["İplik (çözgü+atkı)", r.topI, C.accent],
    ["İşçilik (KDV dahil)", r.fasI, C.warp],
    ["Terbiye", r.terbM, C.weft],
    ["Fire", r.fireM, C.bad],
    ["Kurşum + Ek malzeme", num(state.params.kursum) + num(state.params.ekMal), C.dim],
  ];

  const stats: Array<[string, number, string, string]> = [
    ["Ölçülen", r.olcumM2, "g/m²", C.text],
    ["Hesaplanan", r.hesapM2, "g/m²", C.accent],
    ["Sapma", r.sapma == null ? 0 : r.sapma, "%", durum.c],
  ];

  return (
    <>
      <Card title="Gramaj Doğrulama" icon={<durum.Icon size={16} color={durum.c} />} accent={durum.c}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3,1fr)",
            gap: 12,
            marginBottom: 12,
          }}
        >
          {stats.map(([l, v, u, col]) => (
            <div
              key={l}
              style={{
                background: C.bg,
                border: `1px solid ${C.line}`,
                borderRadius: 10,
                padding: "12px 14px",
              }}
            >
              <div style={{ fontSize: 11, color: C.dim }}>{l}</div>
              <div
                style={{
                  fontSize: 24,
                  fontWeight: 700,
                  color: col,
                  fontFamily: "ui-monospace, monospace",
                }}
              >
                {l === "Sapma" && (r.sapma ?? 0) > 0 ? "+" : ""}
                {fmt(v, 1)} <span style={{ fontSize: 12, color: C.dim }}>{u}</span>
              </div>
            </div>
          ))}
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: isMobile ? "column" : "row",
            alignItems: isMobile ? "flex-start" : "center",
            gap: 8,
            padding: "10px 12px",
            background: C.bg,
            border: `1px solid ${durum.c}55`,
            borderRadius: 10,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <durum.Icon size={18} color={durum.c} />
            <span style={{ color: durum.c, fontWeight: 600, fontSize: 14 }}>{durum.t}</span>
          </div>
          <span style={{ marginLeft: isMobile ? 0 : "auto", fontSize: 11, color: C.dim }}>
            Çekme faktörü → çözgü ×{fmt(r.cozguFak, 3)} (%{fmt(r.cCek * 100)}) · atkı ×
            {fmt(r.atkiFak, 3)} (%{fmt(r.aCek * 100)})
          </span>
        </div>
      </Card>

      <Card title="Kumaş İçeriği" icon={<Sparkles size={16} color={C.weft} />} accent={C.weft}>
        {icerik.length === 0 ? (
          <span style={{ fontSize: 12, color: C.dim }}>
            İpliklere içerik (elyaf cinsi/oran) eklenmedi — info panelinden ekleyin.
          </span>
        ) : (
          <>
            <div
              style={{
                fontSize: isMobile ? 18 : 22,
                fontWeight: 800,
                fontFamily: "ui-monospace, monospace",
                color: C.text,
                marginBottom: 10,
                lineHeight: 1.3,
                wordBreak: "break-word",
              }}
            >
              {icerik
                .map((i) => `%${fmt(i.oran, i.oran >= 10 ? 0 : 1)} ${i.elyaf}`)
                .join(" · ")}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {icerik.map((i) => (
                <div
                  key={i.elyaf}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    fontSize: 12,
                    color: C.dim,
                  }}
                >
                  <span style={{ width: 50, fontFamily: "ui-monospace, monospace", color: C.text, fontWeight: 700 }}>
                    {i.elyaf}
                  </span>
                  <span style={{ flex: 1, fontFamily: "ui-monospace, monospace" }}>
                    %{fmt(i.oran, 2)}
                  </span>
                  <span style={{ fontFamily: "ui-monospace, monospace" }}>
                    {fmt(i.gramaj, 1)} g/mt
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </Card>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: isMobile ? "1fr" : "1.3fr 1fr",
          gap: 16,
        }}
      >
        <Card title="Maliyet Dökümü" icon={<Calculator size={16} color={C.accent} />}>
          {breakdown.map(([l, v, col]) => (
            <div
              key={l}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "9px 0",
                borderBottom: `1px solid ${C.line}`,
              }}
            >
              <span style={{ width: 9, height: 9, borderRadius: 2, background: col }} />
              <span style={{ fontSize: 13, color: C.dim }}>{l}</span>
              <span
                style={{
                  marginLeft: "auto",
                  fontFamily: "ui-monospace, monospace",
                  fontSize: 14,
                }}
              >
                {fmt(v, 3)} $
              </span>
            </div>
          ))}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              marginTop: 12,
              padding: "12px 14px",
              background: `${C.accent}18`,
              border: `1px solid ${C.accent}55`,
              borderRadius: 10,
            }}
          >
            <span style={{ fontWeight: 700, fontSize: 14 }}>TOPLAM</span>
            <span
              style={{
                marginLeft: "auto",
                fontFamily: "ui-monospace, monospace",
                fontSize: 24,
                fontWeight: 800,
                color: C.accent,
              }}
            >
              {fmt(r.total, 3)} <span style={{ fontSize: 13 }}>$/mt</span>
            </span>
          </div>
          <div
            style={{
              display: "flex",
              gap: 16,
              marginTop: 12,
              fontSize: 12,
              color: C.dim,
              flexWrap: "wrap",
            }}
          >
            <span>
              Toplam gramaj: <b style={{ color: C.text }}>{fmt(r.grmt, 1)} g/mt</b>
            </span>
            <span>
              Çözgü: <b style={{ color: C.warp }}>{fmt(r.grmtCozgu, 1)}</b>
            </span>
            <span>
              Atkı: <b style={{ color: C.weft }}>{fmt(r.grmtAtki, 1)}</b>
            </span>
            <span>
              Kapasite: <b style={{ color: C.text }}>{fmt(r.uAy, 0)} mt/ay</b>
            </span>
          </div>
        </Card>

        <Card title="Dağılım" icon={<Activity size={16} color={C.accent} />}>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={donut}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={2}
                >
                  {donut.map((d) => (
                    <Cell key={d.name} fill={d.fill} stroke={C.panel} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => `${fmt(Number(value), 3)} $`}
                  contentStyle={{
                    background: C.panel2,
                    border: `1px solid ${C.line}`,
                    borderRadius: 8,
                    color: C.text,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              justifyContent: "center",
            }}
          >
            {donut.map((d) => (
              <span
                key={d.name}
                style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: C.dim }}
              >
                <span style={{ width: 8, height: 8, borderRadius: 2, background: d.fill }} />
                {d.name}
              </span>
            ))}
          </div>
        </Card>
      </div>

      <Card
        title="Üretim & Finisaj Parametreleri"
        icon={<FlaskConical size={16} color={C.accent} />}
      >
        <div
          style={
            isMobile
              ? { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }
              : { display: "flex", gap: 12, flexWrap: "wrap" }
          }
        >
          <Field
            label="Tezgah devri"
            value={state.params.devir}
            onChange={(v) => set({ params: { ...state.params, devir: v } })}
            suffix="rpm"
            w={130}
          />
          <Field
            label="Randıman"
            value={state.params.randiman}
            onChange={(v) => set({ params: { ...state.params, randiman: v } })}
            suffix="%"
            w={120}
          />
          <Field
            label="Terbiye fiyat"
            value={state.params.terbiyeFiyat}
            onChange={(v) => set({ params: { ...state.params, terbiyeFiyat: v } })}
            suffix="$/kg"
            w={130}
          />
          <Field
            label="Genel fire"
            value={state.params.genelFire}
            onChange={(v) => set({ params: { ...state.params, genelFire: v } })}
            suffix="%"
            w={120}
          />
          <Field
            label="Kurşum + sabit"
            value={state.params.kursum}
            onChange={(v) => set({ params: { ...state.params, kursum: v } })}
            suffix="$/mt"
            w={130}
          />
          <Field
            label="Ek malzeme"
            value={state.params.ekMal}
            onChange={(v) => set({ params: { ...state.params, ekMal: v } })}
            suffix="$/mt"
            w={130}
          />
        </div>
      </Card>
    </>
  );
}
