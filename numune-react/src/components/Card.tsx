import type { ReactNode } from "react";
import { C } from "../theme";

interface CardProps {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  accent?: string;
}

export function Card({ title, icon, children, accent }: CardProps) {
  return (
    <div
      style={{
        background: C.panel,
        border: `1px solid ${C.line}`,
        borderRadius: 14,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "12px 16px",
          borderBottom: `1px solid ${C.line}`,
          borderLeft: accent ? `3px solid ${accent}` : "none",
        }}
      >
        {icon}
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: 0.4,
            textTransform: "uppercase",
            color: C.text,
          }}
        >
          {title}
        </span>
      </div>
      <div style={{ padding: 16 }}>{children}</div>
    </div>
  );
}
