import type { ExecutiveKpi } from "../../lib/deriveExecutiveKpis";

export function ExecutiveKpiStrip({ kpis }: { kpis: ExecutiveKpi[] }) {
  if (!kpis.length) return null;
  return (
    <div className="os-kpi-strip">
      {kpis.map((k) => (
        <div key={k.label} className="os-kpi-card">
          <div className="os-kpi-label">{k.label}</div>
          <div className="os-kpi-value">{k.value}</div>
          {k.delta && <div className={`os-kpi-delta ${k.tone ?? "neu"}`}>{k.delta}</div>}
        </div>
      ))}
    </div>
  );
}
