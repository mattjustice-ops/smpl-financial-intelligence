import { DATA_SOURCES } from "../constants";

/** Server-safe data source badges with inline styles (no Tailwind gradient safelist dependency) */
const SOURCE_STYLES: Record<string, { bg: string; border: string }> = {
  salesforce: { bg: "rgba(14,165,233,0.18)", border: "rgba(56,189,248,0.35)" },
  hubspot: { bg: "rgba(249,115,22,0.18)", border: "rgba(251,146,60,0.35)" },
  netsuite: { bg: "rgba(59,130,246,0.18)", border: "rgba(96,165,250,0.35)" },
  stripe: { bg: "rgba(139,92,246,0.18)", border: "rgba(167,139,250,0.35)" },
  workday: { bg: "rgba(245,158,11,0.18)", border: "rgba(251,191,36,0.35)" },
  excel: { bg: "rgba(16,185,129,0.18)", border: "rgba(52,211,153,0.35)" },
  csv: { bg: "rgba(20,184,166,0.18)", border: "rgba(45,212,191,0.35)" },
  snowflake: { bg: "rgba(6,182,212,0.18)", border: "rgba(34,211,238,0.35)" },
};

export function DataHubDiagram() {
  return (
    <div className="mx-auto mt-12 w-full max-w-3xl">
      <div
        className="relative rounded-3xl border border-white/10 p-6 sm:p-10"
        style={{
          background: "linear-gradient(180deg, rgba(15,23,42,0.95) 0%, rgba(2,6,23,0.98) 100%)",
        }}
      >
        <svg
          className="pointer-events-none absolute inset-0 h-full w-full rounded-3xl"
          viewBox="0 0 600 360"
          preserveAspectRatio="xMidYMid meet"
          aria-hidden
        >
          <circle
            cx="300"
            cy="180"
            r="120"
            fill="none"
            stroke="rgba(45,212,191,0.25)"
            strokeWidth="1.5"
            strokeDasharray="8 6"
          />
          {DATA_SOURCES.map((_, i) => {
            const angle = (i / DATA_SOURCES.length) * Math.PI * 2 - Math.PI / 2;
            const x2 = 300 + Math.cos(angle) * 120;
            const y2 = 180 + Math.sin(angle) * 120;
            return (
              <line
                key={i}
                x1="300"
                y1="180"
                x2={x2}
                y2={y2}
                stroke="rgba(45,212,191,0.2)"
                strokeWidth="1"
              />
            );
          })}
        </svg>

        <div className="relative z-10 mb-8 flex justify-center">
          <div
            className="flex h-20 w-20 flex-col items-center justify-center rounded-2xl shadow-xl"
            style={{
              border: "1px solid rgba(45,212,191,0.5)",
              background: "linear-gradient(135deg, rgba(13,148,136,0.55), rgba(109,40,217,0.45))",
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden>
              <ellipse cx="12" cy="5" rx="8" ry="3" stroke="#99f6e4" strokeWidth="1.5" />
              <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" stroke="#99f6e4" strokeWidth="1.5" />
              <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" stroke="#99f6e4" strokeWidth="1.5" />
            </svg>
            <span className="mt-1 text-[11px] font-bold tracking-wide text-white">SMPL</span>
          </div>
        </div>

        <div className="relative z-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {DATA_SOURCES.map((source) => {
            const style = SOURCE_STYLES[source.id] ?? SOURCE_STYLES.csv;
            return (
              <div
                key={source.id}
                className="flex items-center justify-center rounded-xl px-3 py-3 text-center text-sm font-semibold text-white shadow-md"
                style={{
                  backgroundColor: style.bg,
                  border: `1px solid ${style.border}`,
                }}
              >
                {source.label}
              </div>
            );
          })}
        </div>
      </div>

      <p className="mt-4 text-center text-sm text-slate-500">
        Ingest · reconcile · validate · report
      </p>
    </div>
  );
}
