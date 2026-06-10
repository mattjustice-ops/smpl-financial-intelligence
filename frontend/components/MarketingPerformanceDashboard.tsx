"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

import { useActiveOrganization } from "../hooks/useActiveOrganization";

const apiBase =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";


type Org = { id: string; name: string };

type MarketingRow = {
  organization_id: string;
  scenario: string;
  period: string;
  marketing_channel: string | null;
  marketing_spend: string | number;
  mqls: string | number;
  sqls: string | number;
  sals: string | number;
  opportunities_created: string | number;
  pipeline_arr_created: string | number;
  closed_won_arr: string | number;
  closed_lost_arr: string | number;
  slipped_pipeline_arr: string | number;
  beginning_pipeline_arr: string | number;
  ending_pipeline_arr: string | number;
  cost_per_mql: string | number;
  cost_per_sql: string | number;
  pipeline_per_dollar_spend: string | number;
  marketing_cac_proxy: string | number;
  pipeline_coverage_ratio: string | number;
  win_rate_on_pipeline_created: string | number;
  source_table: string;
};

type ValidationCheck = {
  scenario: string;
  period: string;
  validation_name: string;
  status: "pass" | "warning" | "fail";
  variance?: string | number | null;
  source_tables_used: string[];
};

type MarketingResponse = {
  organization_id: string;
  scenario: string;
  start_period: string;
  end_period: string;
  rows: MarketingRow[];
  validation: ValidationCheck[];
};

const channels = [
  "All Channels",
  "Paid Search",
  "Paid Social",
  "Organic Search",
  "Partner",
  "Webinar",
  "Field Event",
  "Referral",
  "Direct",
  "Content Syndication",
  "Outbound",
  "Customer Success",
];

const drilldownGroups: Record<string, string[]> = {
  "Paid Media": ["Paid Search", "Paid Social"],
  Webinars: ["Webinar"],
  Direct: ["Direct"],
  Partner: ["Partner"],
  Organic: ["Organic Search"],
  Referral: ["Referral"],
  Outbound: ["Outbound"],
  "Customer Success": ["Customer Success"],
};

function num(value: string | number | null | undefined) {
  return Number(value ?? 0);
}

function money(value: string | number | null | undefined) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(num(value));
}

function count(value: string | number | null | undefined) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(num(value));
}

function pct(value: string | number | null | undefined) {
  return `${(num(value) * 100).toFixed(1)}%`;
}

function multiple(value: string | number | null | undefined) {
  return `${num(value).toFixed(2)}x`;
}

function labelize(key: string) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function sum(rows: MarketingRow[], key: keyof MarketingRow) {
  return rows.reduce((total, row) => total + num(row[key] as string | number), 0);
}

export function MarketingPerformanceDashboard() {
  const { organizationId, organizations, isLoading: sessionLoading } = useActiveOrganization();
  const orgs = organizations;
  const [orgId, setOrgId] = useState("");
  const [scenario, setScenario] = useState("Combined");
  const [startPeriod, setStartPeriod] = useState("2026-01");
  const [endPeriod, setEndPeriod] = useState("2026-12");
  const [channel, setChannel] = useState("All Channels");
  const [summary, setSummary] = useState<MarketingResponse | null>(null);
  const [channelPerformance, setChannelPerformance] = useState<MarketingResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);

  useEffect(() => {
    if (organizationId) {
      setOrgId(organizationId);
    }
  }, [organizationId]);

  const load = async () => {
    if (!orgId || sessionLoading) return;
    setBusy(true);
    setError(null);
    try {
      const baseParams = {
        organization_id: orgId,
        scenario,
        start_period: startPeriod,
        end_period: endPeriod,
        _: String(Date.now()),
      };
      const params = new URLSearchParams(baseParams);
      if (channel !== "All Channels") params.set("marketing_channel", channel);

      const [summaryRes, channelRes] = await Promise.all([
        fetch(`${apiBase}/api/v1/marketing/performance-summary?${params}`, {
          cache: "no-store",
          headers: { "Cache-Control": "no-cache" },
        }),
        fetch(`${apiBase}/api/v1/marketing/channel-performance?${params}`, {
          cache: "no-store",
          headers: { "Cache-Control": "no-cache" },
        }),
      ]);
      const summaryText = await summaryRes.text();
      const channelText = await channelRes.text();
      if (!summaryRes.ok) throw new Error(summaryText || `Marketing summary returned ${summaryRes.status}`);
      if (!channelRes.ok) throw new Error(channelText || `Marketing channel performance returned ${channelRes.status}`);
      setSummary(JSON.parse(summaryText) as MarketingResponse);
      setChannelPerformance(JSON.parse(channelText) as MarketingResponse);
      setLastRefresh(new Date().toLocaleString());
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

  const totalRows = summary?.rows ?? [];
  const channelRows = channelPerformance?.rows ?? [];
  const warningRows = [...(summary?.validation ?? []), ...(channelPerformance?.validation ?? [])].filter((v) => v.status !== "pass");

  const latestTotals = totalRows.at(-1);
  const funnelTotals = {
    mqls: sum(totalRows, "mqls"),
    sqls: sum(totalRows, "sqls"),
    sals: sum(totalRows, "sals"),
    opportunities_created: sum(totalRows, "opportunities_created"),
    closed_won_arr: sum(totalRows, "closed_won_arr"),
  };

  const waterfall = {
    beginning_pipeline_arr: totalRows[0]?.beginning_pipeline_arr ?? 0,
    pipeline_arr_created: sum(totalRows, "pipeline_arr_created"),
    closed_won_arr: sum(totalRows, "closed_won_arr"),
    closed_lost_arr: sum(totalRows, "closed_lost_arr"),
    slipped_pipeline_arr: sum(totalRows, "slipped_pipeline_arr"),
    ending_pipeline_arr: totalRows.at(-1)?.ending_pipeline_arr ?? 0,
  };

  return (
    <section style={card}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 20 }}>Marketing Performance</h2>
          <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.5 }}>
            Board-ready GTM view for spend, funnel, pipeline, bookings, and channel efficiency.
          </p>
        </div>
        <button type="button" onClick={load} disabled={busy || !orgId}>
          {busy ? "Loading..." : "Refresh Marketing"}
        </button>
      </div>

      {lastRefresh && <div style={{ marginTop: 8, color: "var(--muted)", fontSize: 12 }}>Last refreshed from API: {lastRefresh}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "2fr repeat(4, minmax(130px, 1fr))", gap: 10, marginTop: 16 }}>
        <label style={label}>
          Organization
          <select style={input} value={orgId} onChange={(e) => setOrgId(e.target.value)}>
            <option value={orgId}>{orgs.find((o) => o.id === orgId)?.name ?? orgId}</option>
            {orgs.filter((o) => o.id !== orgId).map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
          </select>
        </label>
        <label style={label}>
          Scenario
          <select style={input} value={scenario} onChange={(e) => setScenario(e.target.value)}>
            <option>Combined</option>
            <option>Actual</option>
            <option>Budget</option>
            <option>Forecast</option>
          </select>
        </label>
        <label style={label}>
          Start Period
          <input style={input} value={startPeriod} onChange={(e) => setStartPeriod(e.target.value)} placeholder="2026-01" />
        </label>
        <label style={label}>
          End Period
          <input style={input} value={endPeriod} onChange={(e) => setEndPeriod(e.target.value)} placeholder="2026-12" />
        </label>
        <label style={label}>
          Channel
          <select style={input} value={channel} onChange={(e) => setChannel(e.target.value)}>
            {channels.map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
      </div>

      {error && <pre style={errorBox}>{error}</pre>}

      {warningRows.length > 0 && (
        <div style={warningBox}>
          <strong>{warningRows.length} marketing validation warning(s)</strong>
          {warningRows.slice(0, 6).map((row) => (
            <div key={`${row.scenario}-${row.period}-${row.validation_name}`}>
              {row.scenario} {row.period}: {row.validation_name}
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(150px, 1fr))", gap: 10, marginTop: 16 }}>
        <Metric title="Marketing Spend" value={money(sum(totalRows, "marketing_spend"))} />
        <Metric title="Pipeline ARR Created" value={money(sum(totalRows, "pipeline_arr_created"))} />
        <Metric title="Closed Won ARR" value={money(sum(totalRows, "closed_won_arr"))} />
        <Metric title="Pipeline / $ Spend" value={multiple(latestTotals?.pipeline_per_dollar_spend ?? 0)} />
        <Metric title="MQLs" value={count(sum(totalRows, "mqls"))} />
        <Metric title="SQLs" value={count(sum(totalRows, "sqls"))} />
        <Metric title="Cost per SQL" value={money(latestTotals?.cost_per_sql ?? 0)} />
        <Metric title="Win Rate" value={pct(latestTotals?.win_rate_on_pipeline_created ?? 0)} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 12, marginTop: 16 }}>
        <div style={subCard}>
          <strong>Monthly Pipeline and Bookings Trend</strong>
          <LineChart rows={totalRows} metrics={["pipeline_arr_created", "closed_won_arr", "marketing_spend"]} />
        </div>
        <div style={subCard}>
          <strong>Funnel: MQL to Closed Won</strong>
          <FunnelChart values={funnelTotals} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 16 }}>
        <div style={subCard}>
          <strong>Pipeline Waterfall</strong>
          <Waterfall values={waterfall} />
        </div>
        <div style={subCard}>
          <strong>Pipeline by Channel</strong>
          <StackedBar rows={channelRows} />
        </div>
      </div>

      <ChannelTable rows={channelRows} />

      <div style={{ marginTop: 16 }}>
        <h3 style={{ margin: "0 0 10px", fontSize: 16 }}>Channel Drilldowns</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(170px, 1fr))", gap: 10 }}>
          {Object.entries(drilldownGroups).map(([group, groupChannels]) => (
            <DrilldownCard key={group} title={group} rows={channelRows.filter((row) => groupChannels.includes(row.marketing_channel ?? ""))} />
          ))}
        </div>
      </div>
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

function LineChart({ rows, metrics }: { rows: MarketingRow[]; metrics: (keyof MarketingRow)[] }) {
  const width = 760;
  const height = 220;
  const pad = 28;
  const points = metrics.flatMap((metric) => rows.map((row) => num(row[metric] as string | number)));
  const max = Math.max(...points, 1);
  const periods = Array.from(new Set(rows.map((row) => row.period)));
  const colors = ["#2563eb", "#16a34a", "#f97316"];
  return (
    <div style={{ overflowX: "auto" }}>
      <svg width={width} height={height} role="img" aria-label="Marketing trend chart">
        <line x1={pad} x2={width - pad} y1={height - pad} y2={height - pad} stroke="#e5e7eb" />
        {metrics.map((metric, metricIndex) => {
          const metricRows = rows;
          const path = metricRows.map((row, index) => {
            const x = pad + (index * (width - pad * 2)) / Math.max(metricRows.length - 1, 1);
            const y = height - pad - (num(row[metric] as string | number) / max) * (height - pad * 2);
            return `${index === 0 ? "M" : "L"} ${x} ${y}`;
          }).join(" ");
          return <path key={metric} d={path} fill="none" stroke={colors[metricIndex % colors.length]} strokeWidth={2.5} />;
        })}
        {periods.map((period, index) => (
          <text key={period} x={pad + (index * (width - pad * 2)) / Math.max(periods.length - 1, 1)} y={height - 6} fontSize={10} textAnchor="middle" fill="#6b7280">
            {period.slice(5)}
          </text>
        ))}
      </svg>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", fontSize: 12 }}>
        {metrics.map((metric) => <span key={metric}>{labelize(String(metric))}</span>)}
      </div>
    </div>
  );
}

function FunnelChart({ values }: { values: Record<string, number> }) {
  const entries = Object.entries(values);
  const max = Math.max(...entries.map(([, value]) => value), 1);
  return (
    <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
      {entries.map(([key, value]) => (
        <div key={key}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span>{labelize(key)}</span>
            <strong>{key.includes("arr") ? money(value) : count(value)}</strong>
          </div>
          <div style={{ background: "#e5e7eb", borderRadius: 999, height: 18, overflow: "hidden" }}>
            <div style={{ width: `${Math.max(4, (value / max) * 100)}%`, height: "100%", background: "#2563eb" }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function Waterfall({ values }: { values: Record<string, string | number> }) {
  const ordered = ["beginning_pipeline_arr", "pipeline_arr_created", "closed_won_arr", "closed_lost_arr", "slipped_pipeline_arr", "ending_pipeline_arr"];
  return (
    <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
      {ordered.map((key) => (
        <div key={key} style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: 6 }}>
          <span>{labelize(key)}</span>
          <strong>{money(values[key])}</strong>
        </div>
      ))}
    </div>
  );
}

function StackedBar({ rows }: { rows: MarketingRow[] }) {
  const byChannel = Array.from(rows.reduce((map, row) => {
    const channel = row.marketing_channel ?? "Unassigned";
    map.set(channel, (map.get(channel) ?? 0) + num(row.pipeline_arr_created));
    return map;
  }, new Map<string, number>()).entries()).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const total = byChannel.reduce((acc, [, value]) => acc + value, 0) || 1;
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: "flex", height: 28, borderRadius: 999, overflow: "hidden", background: "#e5e7eb" }}>
        {byChannel.map(([channel, value], index) => (
          <div key={channel} title={`${channel}: ${money(value)}`} style={{ width: `${(value / total) * 100}%`, background: palette[index % palette.length] }} />
        ))}
      </div>
      <div style={{ display: "grid", gap: 4, marginTop: 10, fontSize: 12 }}>
        {byChannel.map(([channel, value], index) => (
          <div key={channel} style={{ display: "flex", justifyContent: "space-between" }}>
            <span><span style={{ display: "inline-block", width: 9, height: 9, background: palette[index % palette.length], marginRight: 6 }} />{channel}</span>
            <strong>{money(value)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function ChannelTable({ rows }: { rows: MarketingRow[] }) {
  const channelRows = useMemo(() => {
    const map = new Map<string, MarketingRow[]>();
    rows.forEach((row) => {
      const key = row.marketing_channel ?? "Unassigned";
      map.set(key, [...(map.get(key) ?? []), row]);
    });
    return Array.from(map.entries()).map(([channel, items]) => ({
      channel,
      spend: sum(items, "marketing_spend"),
      mqls: sum(items, "mqls"),
      sqls: sum(items, "sqls"),
      opportunities_created: sum(items, "opportunities_created"),
      pipeline_arr_created: sum(items, "pipeline_arr_created"),
      closed_won_arr: sum(items, "closed_won_arr"),
      closed_lost_arr: sum(items, "closed_lost_arr"),
      slipped_pipeline_arr: sum(items, "slipped_pipeline_arr"),
      ending_pipeline_arr: items.at(-1)?.ending_pipeline_arr ?? 0,
      pipeline_per_dollar_spend: num(items.at(-1)?.pipeline_per_dollar_spend),
      marketing_cac_proxy: num(items.at(-1)?.marketing_cac_proxy),
      win_rate_on_pipeline_created: num(items.at(-1)?.win_rate_on_pipeline_created),
    })).sort((a, b) => b.pipeline_arr_created - a.pipeline_arr_created);
  }, [rows]);

  return (
    <div style={{ marginTop: 16, overflowX: "auto", border: "1px solid var(--border)", borderRadius: 10 }}>
      <table style={{ width: "100%", minWidth: 1200, borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#f9fafb" }}>
            {["Channel", "Spend", "MQLs", "SQLs", "Opps", "Pipeline ARR", "Closed Won ARR", "Closed Lost ARR", "Slipped ARR", "Ending Pipeline", "Pipeline / $", "CAC Proxy", "Win Rate"].map((header) => (
              <th key={header} style={th}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {channelRows.map((row) => (
            <tr key={row.channel}>
              <td style={{ ...td, fontWeight: 700 }}>{row.channel}</td>
              <td style={tdRight}>{money(row.spend)}</td>
              <td style={tdRight}>{count(row.mqls)}</td>
              <td style={tdRight}>{count(row.sqls)}</td>
              <td style={tdRight}>{count(row.opportunities_created)}</td>
              <td style={tdRight}>{money(row.pipeline_arr_created)}</td>
              <td style={tdRight}>{money(row.closed_won_arr)}</td>
              <td style={tdRight}>{money(row.closed_lost_arr)}</td>
              <td style={tdRight}>{money(row.slipped_pipeline_arr)}</td>
              <td style={tdRight}>{money(row.ending_pipeline_arr)}</td>
              <td style={tdRight}>{multiple(row.pipeline_per_dollar_spend)}</td>
              <td style={tdRight}>{multiple(row.marketing_cac_proxy)}</td>
              <td style={tdRight}>{pct(row.win_rate_on_pipeline_created)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DrilldownCard({ title, rows }: { title: string; rows: MarketingRow[] }) {
  return (
    <div style={subCard}>
      <strong>{title}</strong>
      <div style={{ marginTop: 8, display: "grid", gap: 4, fontSize: 13 }}>
        <span>Spend: <strong>{money(sum(rows, "marketing_spend"))}</strong></span>
        <span>Pipeline: <strong>{money(sum(rows, "pipeline_arr_created"))}</strong></span>
        <span>Closed Won: <strong>{money(sum(rows, "closed_won_arr"))}</strong></span>
        <span>Efficiency: <strong>{multiple(num(rows.at(-1)?.pipeline_per_dollar_spend))}</strong></span>
      </div>
      <p style={{ margin: "10px 0 0", color: "var(--muted)", fontSize: 12 }}>
        AI-ready commentary placeholder: summarize trend, conversion quality, pipeline creation, and efficiency for this channel group.
      </p>
    </div>
  );
}

const palette = ["#2563eb", "#16a34a", "#f97316", "#7c3aed", "#0891b2", "#dc2626", "#4f46e5", "#65a30d"];
const card: CSSProperties = { border: "1px solid var(--border)", borderRadius: 12, padding: 16, background: "var(--card)" };
const subCard: CSSProperties = { border: "1px solid var(--border)", borderRadius: 10, padding: 14, background: "#fff" };
const label: CSSProperties = { fontSize: 13, minWidth: 0 };
const input: CSSProperties = { display: "block", width: "100%", marginTop: 4, padding: 8 };
const th: CSSProperties = { textAlign: "left", padding: 10, borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" };
const td: CSSProperties = { padding: 10, borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" };
const tdRight: CSSProperties = { ...td, textAlign: "right" };
const errorBox: CSSProperties = { marginTop: 12, color: "#b91c1c", background: "#fef2f2", padding: 12, borderRadius: 8, whiteSpace: "pre-wrap" };
const warningBox: CSSProperties = { marginTop: 12, color: "#92400e", background: "#fffbeb", border: "1px solid #fde68a", padding: 12, borderRadius: 8, fontSize: 13 };
