import { C } from "../theme";
import { useIsMobile } from "../lib/useIsMobile";

interface FieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  suffix?: string;
  w?: number | string;
  type?: string;
  placeholder?: string;
}

export function Field({
  label,
  value,
  onChange,
  suffix,
  w,
  type = "text",
  placeholder,
}: FieldProps) {
  const isMobile = useIsMobile();
  return (
    <label
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 4,
        ...(isMobile ? { width: "100%" } : { width: w || "auto", flex: w ? "none" : 1 }),
      }}
    >
      <span style={{ fontSize: 11, color: C.dim, letterSpacing: 0.3 }}>{label}</span>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          background: C.bg,
          border: `1px solid ${C.line}`,
          borderRadius: 8,
        }}
      >
        <input
          type={type}
          value={value}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            outline: "none",
            color: C.text,
            padding: "9px 10px",
            fontSize: 14,
            width: "100%",
            fontFamily: "ui-monospace, monospace",
          }}
        />
        {suffix && (
          <span style={{ color: C.dim, fontSize: 11, padding: "0 10px" }}>{suffix}</span>
        )}
      </div>
    </label>
  );
}
