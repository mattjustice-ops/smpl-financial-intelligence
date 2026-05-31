"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

const apiBase =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

type Org = { id: string; name: string };

type ChartPoint = {
  period: string;
  value: string | number;
  period_type: "actual" | "forecast" | string;
  series?: string | null;
};

type TableRow = {
  period: string;
  period_type: "actual" | "forecast" | string;
  values: Record<string, string | number | null>;
};

type ScheduleResponse = {
  schedule_name: string;
  actual_periods: string[];
  forecast_periods: string[];
  rows: TableRow[];
  charts: Record<string, ChartPoint[]>;
  metadata?: Record<string, unknown>;
};

type DriverSummaryResponse = {
  organization_id: string;
  scenario: string;
  start_period: string;
  end_period: string;
  actual_periods: string[];
  forecast_periods: string[];
  kpis: Record<string, string | number>;
  schedules: Record<string, ScheduleResponse>;
  dbt_models: string[];
  frontend_visualizations: Record<string, string[]>;
};

const scheduleLabels: Record<string, string> = {
  cash_flow: "Cash Flow",
  deferred_revenue_waterfall: "Deferred Revenue",
  working_capital: "Working Capital",
  operating_cash_bridge: "OCF Bridge",
  balance_sheet: "Balance Sheet",
  assumptions: "Driver Assumptions",
};

const defaultOrgId = "8571e520-0687-4516-bdee-379f37c58c1f";

function money(value: string | number | null | undefined) {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function labelize(key: string) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function compactPeriod(period: string) {
  const d = new Date(period);
  return d.toLocaleDateString("en-US", { month: "short", timeZone: "UTC" });
}

function MiniLineChart({ points }: { points: ChartPoint[] }) {
  const nums = points.map((p) => Number(p.value ?? 0));
  const min = Math.min(...nums, 0);
  const max = Math.max(...nums, 1);
  const width = 720;
  const height = 180;
  const pad = 22;
  const range = max - min || 1;
  const coords = points.map((p, i) => {
    const x = pad + (i * (width - pad * 2)) / Math.max(points.length - 1, 1);
    const y = height - pad - ((Number(p.value) - min) / range) * (height - pad * 2);
    return { x, y, point: p };
  });
  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"} ${c.x} ${c.y}`).join(" ");

  return (
    <div style={{ overflowX: "auto" }}>
      <svg width={width} height={height} role="img" aria-label="Forecast line chart">
        <line x1={pad} x2={width - pad} y1={height - pad} y2={height - pad} stroke="#e5e7eb" />
        <line x1={pad} x2={pad} y1={pad} y2={height - pad} stroke="#e5e7eb" />
        <path d={path} fill="none" stroke="#2563eb" strokeWidth={2.5} />
        {coords.map((c) => (
          <g key={`${c.point.period}-${c.point.series ?? ""}`}>
            <circle
              cx={c.x}
              cy={c.y}
              r={4}
              fill={c.point.period_type === "actual" ? "#111827" : "#2563eb"}
            />
            <text x={c.x} y={height - 6} textAnchor="middle" fontSize={10} fill="#6b7280">
              {compactPeriod(c.point.period)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function ScheduleTable({ schedule }: { schedule: ScheduleResponse }) {
  const metrics = useMemo(() => {
    const keys = new Set<string>();
    schedule.rows.forEach((row) => Object.keys(row.values).forEach((k) => keys.add(k)));
    return Array.from(keys);
  }, [schedule]);

  return (
    <div style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: 10 }}>
      <table style={{ width: "100%", minWidth: 980, borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#f9fafb" }}>
            <th style={{ ...th, position: "sticky", left: 0, background: "#f9fafb", zIndex: 2 }}>
              Metric
            </th>
            {schedule.rows.map((row) => (
              <th key={row.period} style={{ ...th, textAlign: "right" }}>
                {row.period.slice(0, 7)}
                <div style={{ marginTop: 4 }}>
                  <span style={pill(row.period_type)}>{row.period_type}</span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric) => (
            <tr key={metric}>
              <td
                style={{
                  ...td,
                  position: "sticky",
                  left: 0,
                  background: "#fff",
                  fontWeight: 600,
                  zIndex: 1,
                }}
              >
                {labelize(metric)}
              </td>
              {schedule.rows.map((row) => (
                <td key={`${metric}-${row.period}`} style={{ ...td, textAlign: "right" }}>
                  {formatScheduleCell(metric, row.values[metric])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatScheduleCell(metric: string, value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  if (metric === "dso" || metric === "dpo" || metric === "dio") return n.toFixed(0);
  return money(value);
}

export function ForecastDashboard() {
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [orgId, setOrgId] = useState(defaultOrgId);
  const [scenario, setScenario] = useState("Forecast");
  const [startPeriod, setStartPeriod] = useState("2026-01-01");
  const [endPeriod, setEndPeriod] = useState("2026-12-31");
  const [summary, setSummary] = useState<DriverSummaryResponse | null>(null);
  const [selectedSchedule, setSelectedSchedule] = useState("cash_flow");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${apiBase}/api/v1/organizations/?_=${Date.now()}`, {
          cache: "no-store",
        });
        if (!res.ok) return;
        const data = (await res.json()) as Org[];
        if (cancelled) return;
        setOrgs(data);
        if (data.length && !orgId) setOrgId(data[0].id);
      } catch {
        // Dashboard still supports manually entered org IDs.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [orgId]);

  const load = async () => {
    setBusy(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        organization_id: orgId,
        scenario,
        start_period: startPeriod,
        end_period: endPeriod,
        _: String(Date.now()),
      });
      const res = await fetch(`${apiBase}/api/v1/forecast/driver-summary?${params.toString()}`, {
        cache: "no-store",
        headers: {
          "Cache-Control": "no-cache",
        },
      });
      const text = await res.text();
      if (!res.ok) throw new Error(text || `Forecast API returned ${res.status}`);
      const data = JSON.parse(text) as DriverSummaryResponse;
      setSummary(data);
      setLastRefreshedAt(new Date().toLocaleString());
      if (!data.schedules[selectedSchedule]) {
        setSelectedSchedule(Object.keys(data.schedules)[0] ?? "cash_flow");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const schedule = summary?.schedules[selectedSchedule];
  const primaryChart = schedule ? Object.values(schedule.charts).find((series) => series.length > 0) : undefined;

  return (
    <section style={card}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 20 }}>Driver-Based Forecast Dashboard</h2>
          <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.5 }}>
            Three-statement SaaS forecast schedules with visible Actual to Forecast transition.
          </p>
        </div>
        <button type="button" onClick={load} disabled={busy || !orgId}>
          {busy ? "Loading..." : "Refresh Forecast"}
        </button>
      </div>
      {lastRefreshedAt && (
        <div style={{ marginTop: 8, color: "var(--muted)", fontSize: 12 }}>
          Last refreshed from API: {lastRefreshedAt}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(160px, 1fr))", gap: 10, marginTop: 16 }}>
        <label style={label}>
          Organization
          <select style={input} value={orgId} onChange={(e) => setOrgId(e.target.value)}>
            <option value={orgId}>{orgId}</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </label>
        <label style={label}>
          Scenario
          <select style={input} value={scenario} onChange={(e) => setScenario(e.target.value)}>
            <option>Forecast</option>
            <option>Combined</option>
            <option>Actual</option>
            <option>Budget</option>
          </select>
        </label>
        <label style={label}>
          Start Period
          <input style={input} type="date" value={startPeriod} onChange={(e) => setStartPeriod(e.target.value)} />
        </label>
        <label style={label}>
          End Period
          <input style={input} type="date" value={endPeriod} onChange={(e) => setEndPeriod(e.target.value)} />
        </label>
      </div>

      {error && <pre style={errorBox}>{error}</pre>}

      {summary && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(140px, 1fr))", gap: 10, marginTop: 16 }}>
            <Metric title="Ending Cash" value={money(summary.kpis.ending_cash)} />
            <Metric title="Actual Months" value={String(summary.actual_periods.length)} />
            <Metric title="Forecast Months" value={String(summary.forecast_periods.length)} />
            <Metric title="Scenario" value={summary.scenario} />
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
            {Object.keys(summary.schedules).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setSelectedSchedule(key)}
                style={{
                  borderColor: key === selectedSchedule ? "var(--accent)" : "var(--border)",
                  background: key === selectedSchedule ? "#eff6ff" : "#fff",
                }}
              >
                {scheduleLabels[key] ?? labelize(key)}
              </button>
            ))}
          </div>

          {schedule && (
            <div style={{ marginTop: 16, display: "grid", gap: 14 }}>
              <div style={subCard}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <strong>{scheduleLabels[selectedSchedule] ?? labelize(selectedSchedule)}</strong>
                  <span style={{ color: "var(--muted)", fontSize: 13 }}>
                    {schedule.actual_periods.length} actual periods / {schedule.forecast_periods.length} forecast periods
                  </span>
                </div>
                {primaryChart ? <MiniLineChart points={primaryChart} /> : <p>No chart series available.</p>}
              </div>

              <ScheduleTable schedule={schedule} />

              <div style={subCard}>
                <strong>Recommended dbt Models</strong>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
                  {summary.dbt_models.map((m) => (
                    <code key={m} style={codePill}>
                      {m}
                    </code>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Metric({ title, value }: { title: string; value: string }) {
  return (
    <div style={subCard}>
      <div style={{ color: "var(--muted)", fontSize: 12 }}>{title}</div>
      <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}

const card: CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 16,
  background: "var(--card)",
};

const subCard: CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: 10,
  padding: 14,
  background: "#fff",
};

const label: CSSProperties = { fontSize: 13, minWidth: 0 };
const input: CSSProperties = { display: "block", width: "100%", marginTop: 4, padding: 8 };
const th: CSSProperties = { textAlign: "left", padding: 10, borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" };
const td: CSSProperties = { padding: 10, borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" };
const errorBox: CSSProperties = { color: "#b91c1c", background: "#fef2f2", padding: 12, borderRadius: 8, whiteSpace: "pre-wrap" };
const codePill: CSSProperties = { background: "#f3f4f6", border: "1px solid var(--border)", borderRadius: 999, padding: "4px 8px" };

function pill(type: string): CSSProperties {
  return {
    borderRadius: 999,
    padding: "2px 8px",
    fontSize: 12,
    background: type === "actual" ? "#f3f4f6" : "#dbeafe",
    color: type === "actual" ? "#111827" : "#1d4ed8",
  };
}
