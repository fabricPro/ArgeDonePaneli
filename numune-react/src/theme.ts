import type { CSSProperties } from "react";

/**
 * Uygulama paleti — tek kaynak (inline stiller bunu kullanir).
 * Ayni degerler src/index.css `@theme` blogunda Tailwind token'lari olarak da var;
 * birini degistirince digerini de guncelle.
 */
export const C = {
  bg: "#0f1115",
  panel: "#171a21",
  panel2: "#1d212b",
  line: "#2a3040",
  text: "#e7ebf2",
  dim: "#8b94a7",
  accent: "#5b8def",
  warp: "#f0a830",
  weft: "#3fb6a8",
  ok: "#36c98a",
  warn: "#e6b94a",
  bad: "#e8674f",
} as const;

export const btnAdd = (col: string): CSSProperties => ({
  display: "flex",
  alignItems: "center",
  gap: 6,
  marginTop: 12,
  padding: "10px 16px",
  background: `${col}1c`,
  border: `1px solid ${col}66`,
  color: col,
  borderRadius: 10,
  cursor: "pointer",
  fontWeight: 600,
  fontSize: 13,
  width: "100%",
  justifyContent: "flex-start",
});
