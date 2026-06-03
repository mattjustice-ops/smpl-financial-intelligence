import type { CSSProperties } from "react";

type ModulePreviewProps = {
  variant: "bars" | "line" | "grid" | "chat";
};

export function ModulePreview({ variant }: ModulePreviewProps) {
  const frame: CSSProperties = {
    borderRadius: 8,
    border: "1px solid #e2e8f0",
    background: "#fff",
    padding: 10,
  };

  if (variant === "chat") {
    return (
      <div style={frame}>
        <div
          style={{
            marginLeft: "auto",
            maxWidth: "88%",
            borderRadius: 10,
            borderBottomRightRadius: 4,
            background: "#0f172a",
            color: "#fff",
            fontSize: 10,
            padding: "8px 10px",
            marginBottom: 8,
          }}
        >
          Why did EBITDA miss?
        </div>
        <div
          style={{
            borderRadius: 10,
            border: "1px solid #99f6e4",
            background: "#ecfdf5",
            color: "#334155",
            fontSize: 10,
            padding: "8px 10px",
          }}
        >
          GTM spend +4.2% vs plan…
        </div>
      </div>
    );
  }

  if (variant === "grid") {
    return (
      <div style={{ ...frame, display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 4 }}>
        {[40, 65, 55, 70, 48, 80].map((h, i) => (
          <div
            key={i}
            style={{
              height: h * 0.35,
              borderRadius: 3,
              background: "linear-gradient(to top, rgba(20,184,166,0.85), rgba(167,139,250,0.55))",
            }}
          />
        ))}
      </div>
    );
  }

  if (variant === "line") {
    return (
      <div style={frame}>
        <svg viewBox="0 0 120 40" style={{ width: "100%", height: 40 }}>
          <path
            d="M4,32 L24,28 L44,22 L64,18 L84,12 L104,8"
            fill="none"
            stroke="#14b8a6"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <path
            d="M4,36 L24,34 L44,30 L64,26 L84,22 L104,18"
            fill="none"
            stroke="#a78bfa"
            strokeWidth="1.5"
            strokeDasharray="3 3"
            opacity="0.75"
          />
        </svg>
      </div>
    );
  }

  return (
    <div style={{ ...frame, display: "flex", alignItems: "flex-end", gap: 4, height: 48 }}>
      {[35, 52, 44, 68, 58, 72].map((h, i) => (
        <div
          key={i}
          style={{
            flex: 1,
            height: h * 0.45,
            borderRadius: 3,
            background: "linear-gradient(to top, rgba(13,148,136,0.9), rgba(45,212,191,0.5))",
          }}
        />
      ))}
    </div>
  );
}
