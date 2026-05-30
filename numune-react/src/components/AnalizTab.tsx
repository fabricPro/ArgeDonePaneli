import { useRef, type Dispatch, type SetStateAction } from "react";
import {
  Camera,
  Plus,
  Trash2,
  Ruler,
  Layers,
  Activity,
  FlaskConical,
  ImageOff,
  ArrowRight,
  Wand2,
} from "lucide-react";
import type { AnalizState } from "../lib/types";
import { yeniIplik } from "../lib/factory";
import { useIsMobile } from "../lib/useIsMobile";
import { C, btnAdd } from "../theme";
import { Card } from "./Card";
import { Field } from "./Field";
import { IplikRow } from "./IplikRow";
import { CekmeBlok } from "./CekmeBlok";

interface AnalizTabProps {
  state: AnalizState;
  set: (patch: Partial<AnalizState>) => void;
  setState: Dispatch<SetStateAction<AnalizState>>;
  onNext: () => void;
}

export function AnalizTab({ state, set, setState, onNext }: AnalizTabProps) {
  const isMobile = useIsMobile();
  const fileRef = useRef<HTMLInputElement>(null);

  const addPhotos = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((f) => {
      const reader = new FileReader();
      reader.onload = (e) =>
        setState((s) => ({
          ...s,
          photos: [
            ...s.photos,
            { id: Date.now() + Math.random(), url: String(e.target?.result ?? ""), label: f.name },
          ],
        }));
      reader.readAsDataURL(f);
    });
  };

  return (
    <>
      <Card title="Numune Künyesi" icon={<FlaskConical size={16} color={C.accent} />}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Field
            label="Numune adı / kodu"
            value={state.meta.numuneAd}
            onChange={(v) => set({ meta: { ...state.meta, numuneAd: v } })}
            placeholder="örn. NUM-2026-014"
          />
          <Field
            label="Müşteri"
            value={state.meta.musteri}
            onChange={(v) => set({ meta: { ...state.meta, musteri: v } })}
          />
          <Field
            label="Tarih"
            type="date"
            value={state.meta.tarih}
            onChange={(v) => set({ meta: { ...state.meta, tarih: v } })}
            w={150}
          />
        </div>
      </Card>

      <Card title="Numune Fotoğrafları" icon={<Camera size={16} color={C.accent} />}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <button
            onClick={() => fileRef.current?.click()}
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              alignItems: "center",
              justifyContent: "center",
              width: 110,
              height: 110,
              border: `1.5px dashed ${C.line}`,
              borderRadius: 12,
              background: C.bg,
              color: C.dim,
              cursor: "pointer",
            }}
          >
            <Camera size={26} />
            <span style={{ fontSize: 11 }}>Çek / Yükle</span>
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            capture="environment"
            multiple
            style={{ display: "none" }}
            onChange={(e) => addPhotos(e.target.files)}
          />
          {state.photos.map((p) => (
            <div
              key={p.id}
              style={{
                position: "relative",
                width: 110,
                height: 110,
                borderRadius: 12,
                overflow: "hidden",
                border: `1px solid ${C.line}`,
              }}
            >
              <img
                src={p.url}
                alt={p.label}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
              <button
                onClick={() => set({ photos: state.photos.filter((x) => x.id !== p.id) })}
                style={{
                  position: "absolute",
                  top: 4,
                  right: 4,
                  background: "rgba(0,0,0,0.6)",
                  border: "none",
                  borderRadius: 6,
                  color: "#fff",
                  padding: 4,
                  cursor: "pointer",
                }}
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          {state.photos.length === 0 && (
            <span
              style={{
                color: C.dim,
                fontSize: 12,
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <ImageOff size={14} /> Henüz fotoğraf yok (tam çözünürlükte, cihazda saklanır)
            </span>
          )}
        </div>
      </Card>

      <Card title="Temel Ölçüler" icon={<Ruler size={16} color={C.accent} />}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Field
            label="Ölçülen m² gramaj"
            value={state.olcum.gramajM2}
            onChange={(v) => set({ olcum: { ...state.olcum, gramajM2: v } })}
            suffix="g/m²"
            w={170}
          />
          <Field
            label="Tarak eni"
            value={state.olcum.tarakEn}
            onChange={(v) => set({ olcum: { ...state.olcum, tarakEn: v } })}
            suffix="cm"
            w={140}
          />
          <Field
            label="Mamul eni"
            value={state.olcum.mamulEn}
            onChange={(v) => set({ olcum: { ...state.olcum, mamulEn: v } })}
            suffix="cm"
            w={140}
          />
        </div>
        <p style={{ fontSize: 11, color: C.dim, marginTop: 10, marginBottom: 0 }}>
          Ölçülen m² gramaj = teraziyle bulunan değer. Hesaplananla Maliyet sekmesinde
          karşılaştırılır.
        </p>
      </Card>

      <Card title="Çözgü İplikleri (warp)" icon={<Layers size={16} color={C.warp} />} accent={C.warp}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 11,
            color: C.dim,
            marginBottom: 4,
          }}
        >
          <Wand2 size={12} /> Terazi simgesine bas → iplik söküp ölç, kalınlık otomatik gelsin
        </div>
        {state.cozgu.map((row, i) => (
          <IplikRow
            key={row.id}
            row={row}
            color={C.warp}
            sikLabel="Çözgü sıklığı"
            onChange={(nr) => set({ cozgu: state.cozgu.map((x, j) => (j === i ? nr : x)) })}
            onDelete={() => set({ cozgu: state.cozgu.filter((_, j) => j !== i) })}
          />
        ))}
        <button onClick={() => set({ cozgu: [...state.cozgu, yeniIplik()] })} style={btnAdd(C.warp)}>
          <Plus size={15} /> Çözgü ekle
        </button>
      </Card>

      <Card title="Atkı İplikleri (weft)" icon={<Layers size={16} color={C.weft} />} accent={C.weft}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 11,
            color: C.dim,
            marginBottom: 4,
          }}
        >
          <Wand2 size={12} /> Terazi simgesine bas → iplik söküp ölç, kalınlık otomatik gelsin
        </div>
        {state.atki.map((row, i) => (
          <IplikRow
            key={row.id}
            row={row}
            color={C.weft}
            sikLabel="Atkı sıklığı"
            onChange={(nr) => set({ atki: state.atki.map((x, j) => (j === i ? nr : x)) })}
            onDelete={() => set({ atki: state.atki.filter((_, j) => j !== i) })}
          />
        ))}
        <button onClick={() => set({ atki: [...state.atki, yeniIplik()] })} style={btnAdd(C.weft)}>
          <Plus size={15} /> Atkı ekle
        </button>
      </Card>

      <Card title="Çekme Ölçümleri" icon={<Activity size={16} color={C.accent} />}>
        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 12 }}>
          <CekmeBlok
            label="Çözgü çekmesi"
            color={C.warp}
            data={state.cekme.cozgu}
            onChange={(d) => set({ cekme: { ...state.cekme, cozgu: d } })}
          />
          <CekmeBlok
            label="Atkı çekmesi"
            color={C.weft}
            data={state.cekme.atki}
            onChange={(d) => set({ cekme: { ...state.cekme, atki: d } })}
          />
        </div>
      </Card>

      <button
        onClick={onNext}
        style={{ ...btnAdd(C.accent), justifyContent: "center", padding: "13px", fontSize: 15 }}
      >
        Maliyet & Doğrulamaya geç <ArrowRight size={17} />
      </button>
    </>
  );
}
