"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { formatFetchError, getNextApiBase, toApiDateParam } from "../../lib/apiBase";
import { fetchJson } from "../../lib/fetchJson";
import { ManagementStatementTab } from "./ManagementStatementTab";
import { OperatingSectionHeader } from "../cfo/OperatingSectionHeader";
import { statementPeriodParams } from "../FinancialStatementTable";
import {
  WorkforceValidationStrip,
  type WorkforceValidationCheck,
} from "../workforce/WorkforceValidationStrip";

const DEPARTMENTS = [
  "Total Company",
  "Sales & Marketing",
  "R&D",
  "G&A",
  "Customer Success",
  "Product",
  "Finance",
  "Operations",
];

const GL_DEPARTMENTS = [
  "Sales",
  "Marketing",
  "Engineering",
  "Product",
  "Customer Success",
  "Support",
  "G&A",
  "Finance",
];

type Tone = "pos" | "neg" | "neu";
type PeriodMode = "month" | "qtd" | "ytd" | "fy";
type SubTab = "summary" | "bridge" | "statement" | "department" | "gl" | "trend";

type MetricSlice = {
  actual: string | number;
  budget: string | number;
  forecast: string | number;
  outlook: string | number;
  variance: string | number;
  variance_pct?: string | number | null;
  pct_of_revenue?: string | number | null;
  ytd_actual?: string | number;
  ytd_budget?: string | number;
  ytd_variance?: string | number;
};

type PlLine = {
  id: string;
  label: string;
  line_type: string;
  section_key: string;
  indent: number;
  expandable: boolean;
  is_bold?: boolean;
  is_ebitda?: boolean;
  metrics: MetricSlice;
  children: PlLine[];
  driver?: string;
};

type KpiCard = {
  key: string;
  label: string;
  value: string | number;
  value_format: "currency" | "percent" | "multiple" | "text";
  compare_value?: string | number | null;
  compare_label?: string;
  delta_label?: string;
  tone: Tone;
  sparkline: (string | number)[];
};

type MonthlySeries = {
  period: string;
  label: string;
  is_closed?: boolean;
  revenue_actual: string | number;
  revenue_forecast?: string | number;
  revenue_budget: string | number;
  revenue_outlook: string | number;
  cogs_outlook?: string | number;
  cogs_budget?: string | number;
  gross_profit_actual: string | number;
  gross_profit_forecast?: string | number;
  gross_profit_budget?: string | number;
  gross_profit_outlook: string | number;
  ebitda_actual: string | number;
  ebitda_forecast?: string | number;
  ebitda_outlook: string | number;
  total_opex?: string | number;
  opex_stack_sm?: string | number;
  opex_stack_rd?: string | number;
  opex_stack_ga?: string | number;
  sm: string | number;
  rd: string | number;
  ga: string | number;
  cs: string | number;
  gm_pct_actual?: string | number;
  gm_pct_budget?: string | number;
  ebitda_margin_actual?: string | number;
  ebitda_margin_budget?: string | number;
};

type MarginTrendField = "gm_pct_actual" | "gm_pct_budget" | "ebitda_margin_actual" | "ebitda_margin_budget";

function marginTrendValue(s: MonthlySeries, field: MarginTrendField) {
  return num(s[field]);
}

type WaterfallStep = {
  label: string;
  value: string | number;
  running_total: string | number;
  step_type: string;
};

type DepartmentVariance = {
  department: string;
  outlook: string | number;
  budget: string | number;
  variance: string | number;
  variance_pct?: string | number | null;
  pct_of_opex?: string | number | null;
};

type GlAccountRow = {
  account: string;
  account_group: string;
  outlook: string | number;
  budget: string | number;
  variance: string | number;
  variance_pct?: string | number | null;
  ytd_outlook: string | number;
  ytd_variance: string | number;
  h2_forecast?: string | number;
  is_non_recurring?: boolean;
};

type DepartmentSummaryRow = {
  department: string;
  headcount: string | number;
  period_actual: string | number;
  period_budget: string | number;
  variance: string | number;
  variance_pct?: string | number | null;
  ytd_actual: string | number;
  ytd_budget: string | number;
  ytd_variance: string | number;
};

type DashboardPayload = {
  organization_id: string;
  as_of_period: string;
  period_mode: string;
  view_mode: string;
  department_filter: string;
  outlook_label: string;
  kpis: KpiCard[];
  monthly_series: MonthlySeries[];
  pl_lines: PlLine[];
  ebitda_waterfall: WaterfallStep[];
  department_variances: DepartmentVariance[];
  department_summary: DepartmentSummaryRow[];
  gl_by_department: Record<string, GlAccountRow[]>;
  commentary: { section: string; observation: string; implication: string; recommendation: string }[];
  validations: { code: string; message: string; severity: string }[];
  metadata: Record<string, unknown>;
};

function num(v: string | number | null | undefined) {
  return Number(v ?? 0);
}

const REVENUE_FAVORABLE_KEYS = ["revenue", "gross_profit", "ebitda", "operating_income", "net_income", "subscription_revenue", "services_revenue"];

function fM(v: string | number | null | undefined, d = 2) {
  if (v === null || v === undefined) return "—";
  const n = num(v);
  if (Math.abs(n) < 1000) return "—";
  const dec = Math.min(d, 2);
  const neg = n < 0;
  const abs = Math.abs(n);
  if (abs >= 1e6) return `${neg ? "-$" : "$"}${(abs / 1e6).toFixed(dec)}M`;
  if (abs >= 1e3) return `${neg ? "-$" : "$"}${(abs / 1e3).toFixed(0)}K`;
  return `${neg ? "-$" : "$"}${Math.round(abs)}`;
}

function money(v: string | number | null | undefined) {
  return fM(v);
}

function pct(v: string | number | null | undefined) {
  const n = num(v);
  if (Math.abs(n) <= 1.5) return `${(n * 100).toFixed(1)}%`;
  return `${n.toFixed(1)}%`;
}

function formatKpi(k: KpiCard) {
  if (k.value_format === "percent") return pct(k.value);
  if (k.value_format === "multiple") return num(k.value).toFixed(2);
  if (k.value_format === "text") return String(k.value);
  return money(k.value);
}

function mapPeriodMode(periodView: string): PeriodMode {
  if (periodView === "ytd") return "ytd";
  if (periodView === "fiscal_year") return "fy";
  if (periodView.startsWith("Q")) return "qtd";
  return "month";
}

function collectIds(lines: PlLine[]): string[] {
  const ids: string[] = [];
  for (const l of lines) {
    if (l.expandable && l.children.length) ids.push(l.id);
    ids.push(...collectIds(l.children));
  }
  return ids;
}

function varClass(sectionKey: string, label: string, variance: number) {
  if (variance === 0) return "";
  const isRevenue = REVENUE_FAVORABLE_KEYS.some((k) => sectionKey.includes(k) || label.includes(k));
  const favorable = isRevenue ? variance >= 0 : variance <= 0;
  return favorable ? "fav" : "unfav";
}

function monthChipLabel(period: string) {
  const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${names[parseInt(period.slice(5, 7), 10) - 1]} ${period.slice(0, 4)}`;
}

function chartMoney(v: string | number | null | undefined) {
  const n = num(v);
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function RevenueGpPathChart({
  series,
  closedThrough,
}: {
  series: MonthlySeries[];
  closedThrough?: string;
}) {
  if (!series.length) return <p className="mpl-muted">No trend data</p>;

  const w = 720;
  const h = 250;
  const padL = 40;
  const padR = 12;
  const padT = 44;
  const padB = 28;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const gpBarValues = series.map((s) =>
    s.is_closed
      ? num(s.gross_profit_actual) || num(s.gross_profit_outlook)
      : num(s.gross_profit_forecast) || num(s.gross_profit_outlook)
  );
  const revActualPts = series.map((s) =>
    s.is_closed ? num(s.revenue_actual) || num(s.revenue_outlook) : null
  );

  const maxY = Math.max(
    ...gpBarValues,
    ...revActualPts.filter((v): v is number => v != null),
    ...series.map((s) => num(s.revenue_budget)),
    1
  );

  const xCenter = (i: number) => padL + (i + 0.5) * (plotW / series.length);
  const y = (v: number) => padT + plotH - (v / maxY) * plotH;
  const barW = Math.max(10, plotW / series.length - 12);

  const linePath = (values: (number | null)[]) => {
    let d = "";
    values.forEach((v, i) => {
      if (v == null || v === 0) return;
      d += `${d ? " L" : "M"}${xCenter(i)},${y(v)}`;
    });
    return d;
  };

  return (
    <svg className="mpl-chart mpl-revenue-path" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Revenue and gross profit FY path">
      {[0.25, 0.5, 0.75, 1].map((tick) => (
        <line
          key={tick}
          x1={padL}
          x2={w - padR}
          y1={y(maxY * tick)}
          y2={y(maxY * tick)}
          stroke="var(--border)"
          strokeDasharray="2 4"
          opacity={0.5}
        />
      ))}

      {series.map((s, i) => {
        const closed = s.is_closed ?? (closedThrough ? s.period <= closedThrough : num(s.revenue_actual) > 0);
        const gpVal = gpBarValues[i];
        const gpHeight = (gpVal / maxY) * plotH;
        const x = xCenter(i) - barW / 2;
        const barY = y(gpVal);
        return (
          <g key={s.period}>
            <rect
              x={x}
              y={barY}
              width={barW}
              height={Math.max(gpHeight, 2)}
              fill="rgba(29,158,117,0.35)"
              stroke="#1D9E75"
              strokeWidth={1}
              rx="2"
            />
            <text x={xCenter(i)} y={Math.max(padT + 10, barY - 4)} fontSize="8" textAnchor="middle" fill="var(--text)">
              {chartMoney(gpVal)}
            </text>
            <text x={xCenter(i)} y={barY + Math.max(gpHeight, 2) + 10} fontSize="7" textAnchor="middle" fill="var(--muted)">
              {closed ? "GP Act" : "GP Fcst"}
            </text>
          </g>
        );
      })}

      {linePath(revActualPts) ? (
        <path d={linePath(revActualPts)!} fill="none" stroke="#1a2e44" strokeWidth="2.5" />
      ) : null}
      <path
        d={series.map((s, i) => `${i === 0 ? "M" : "L"}${xCenter(i)},${y(num(s.revenue_budget))}`).join(" ")}
        fill="none"
        stroke="#888780"
        strokeWidth="1.5"
        strokeDasharray="5 4"
      />

      {series.map((s, i) => (
        <text key={`${s.period}-lbl`} x={xCenter(i)} y={h - 8} fontSize="9" textAnchor="middle" fill="var(--muted)">
          {s.label}
        </text>
      ))}

      <text x={padL} y={14} fontSize="9" fill="#1D9E75">
        ■ Gross profit
      </text>
      <text x={padL + 100} y={14} fontSize="9" fill="#1a2e44">
        — Rev actual
      </text>
      <text x={padL + 190} y={14} fontSize="9" fill="#888780">
        --- Rev budget
      </text>
    </svg>
  );
}

const OPEX_STACKS = [
  { key: "opex_stack_sm" as const, fallback: "sm" as const, label: "S&M", color: "#1a2e44" },
  { key: "opex_stack_rd" as const, fallback: "rd" as const, label: "R&D", color: "#1D9E75" },
  { key: "opex_stack_ga" as const, fallback: "ga" as const, label: "G&A+Fin", color: "#BA7517" },
];

function stackValue(s: MonthlySeries, seg: (typeof OPEX_STACKS)[number]) {
  return num(s[seg.key]) || num(s[seg.fallback]);
}

function StackedOpexChart({ series }: { series: MonthlySeries[] }) {
  if (!series.length) return null;
  const w = 720;
  const h = 230;
  const padL = 28;
  const padR = 12;
  const padT = 36;
  const padB = 28;
  const plotH = h - padT - padB;
  const totals = series.map(
    (s) => num(s.total_opex) || OPEX_STACKS.reduce((a, seg) => a + stackValue(s, seg), 0)
  );
  const maxY = Math.max(...totals, 1);
  const barW = Math.max(10, (w - padL - padR) / series.length - 8);

  return (
    <svg className="mpl-chart mpl-opex-stack" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Stacked OpEx">
      {OPEX_STACKS.map((seg, si) => (
        <text key={seg.key} x={padL + si * 88} y={14} fontSize="9" fill={seg.color}>
          ■ {seg.label}
        </text>
      ))}
      <text x={padL + 280} y={14} fontSize="9" fill="var(--muted)">
        S&M · Eng+Product · G&A+Fin from GL detail
      </text>

      {series.map((s, i) => {
        let stack = 0;
        const x = padL + i * (barW + 8);
        const total = totals[i];
        const totalH = (total / maxY) * plotH;
        const barTop = padT + plotH - totalH;
        return (
          <g key={s.period}>
            {OPEX_STACKS.map((seg) => {
              const v = stackValue(s, seg);
              const bh = (v / maxY) * plotH;
              const yPos = padT + plotH - stack - bh;
              stack += bh;
              return (
                <g key={seg.key}>
                  <rect x={x} y={yPos} width={barW} height={Math.max(bh, v > 0 ? 1 : 0)} fill={seg.color} rx="2" />
                  {bh >= 16 && v > 0 ? (
                    <text x={x + barW / 2} y={yPos + bh / 2 + 3} fontSize="7" textAnchor="middle" fill="#fff">
                      {chartMoney(v)}
                    </text>
                  ) : null}
                </g>
              );
            })}
            <text x={x + barW / 2} y={Math.max(padT + 8, barTop - 4)} fontSize="8" textAnchor="middle" fill="var(--text)">
              {chartMoney(total)}
            </text>
            <text x={x + barW / 2} y={h - 18} fontSize="7" textAnchor="middle" fill="var(--muted)">
              {s.is_closed ? "Actual" : "Fcst"}
            </text>
            <text x={x + barW / 2} y={h - 8} fontSize="8" textAnchor="middle" fill="var(--muted)">
              {s.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function WaterfallChart({ steps }: { steps: WaterfallStep[] }) {
  if (!steps.length) return <p className="mpl-muted">No bridge data</p>;
  const w = 640;
  const h = 220;
  const padL = 36;
  const padR = 16;
  const padT = 24;
  const padB = 36;
  const plotH = h - padT - padB;
  const vals = steps.flatMap((s) => [num(s.running_total), num(s.running_total) + num(s.value)]);
  const minV = Math.min(0, ...vals);
  const maxV = Math.max(...vals, 1);
  const span = maxV - minV || 1;
  const y = (v: number) => padT + plotH - ((v - minV) / span) * plotH;
  const barW = Math.max(28, (w - padL - padR) / steps.length - 12);

  return (
    <svg className="mpl-chart mpl-waterfall" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="EBITDA waterfall">
      {steps.map((s, i) => {
        const run = num(s.running_total);
        const val = num(s.value);
        const isTotal = s.step_type === "total";
        const top = isTotal ? run : run;
        const bottom = isTotal ? 0 : run + val;
        const yTop = y(Math.max(top, bottom));
        const yBot = y(Math.min(top, bottom));
        const barH = Math.max(yBot - yTop, 2);
        const x = padL + i * (barW + 12);
        let fill = "#D85A30";
        if (isTotal) {
          fill = s.label === "EBITDA" ? (run >= 0 ? "#1D9E75" : "#D85A30") : "#1a2e44";
        } else if (val > 0) {
          fill = "#1D9E75";
        }
        const labelY = val < 0 ? yTop - 4 : yTop + barH + 12;
        return (
          <g key={`${s.label}-${i}`}>
            <rect x={x} y={yTop} width={barW} height={barH} fill={fill} rx="2" opacity={isTotal ? 1 : 0.92} />
            <text x={x + barW / 2} y={labelY} fontSize="8" textAnchor="middle" fill="var(--text)">
              {chartMoney(isTotal ? run : val)}
            </text>
            <text x={x + barW / 2} y={h - 10} fontSize="8" textAnchor="middle" fill="var(--muted)">
              {s.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function MarginTrendChart({
  series,
  fieldActual,
  fieldBudget,
  title,
  yMin = 0.7,
  yMax = 0.85,
}: {
  series: MonthlySeries[];
  fieldActual: MarginTrendField;
  fieldBudget: MarginTrendField;
  title: string;
  yMin?: number;
  yMax?: number;
}) {
  const closed = series.filter((s) => s.is_closed);
  if (!closed.length) return <p className="mpl-muted">No margin trend data</p>;
  const w = 520;
  const h = 180;
  const pad = 36;
  const plotW = w - pad * 2;
  const plotH = h - pad * 2;
  const y = (v: number) => pad + plotH - ((v - yMin) / (yMax - yMin)) * plotH;
  const x = (i: number) => pad + (i / Math.max(closed.length - 1, 1)) * plotW;
  const actualPath = closed
    .map((s, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(marginTrendValue(s, fieldActual))}`)
    .join(" ");
  const budgetPath = closed
    .map((s, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(marginTrendValue(s, fieldBudget))}`)
    .join(" ");
  return (
    <div>
      <div className="mpl-section-label">{title}</div>
      <svg className="mpl-chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={title}>
        <line x1={pad} x2={w - pad} y1={y(yMin)} y2={y(yMin)} stroke="var(--border)" strokeDasharray="2 4" />
        <line x1={pad} x2={w - pad} y1={y(yMax)} y2={y(yMax)} stroke="var(--border)" strokeDasharray="2 4" />
        <path d={actualPath} fill="none" stroke="#1D9E75" strokeWidth="2.5" />
        <path d={budgetPath} fill="none" stroke="#888780" strokeWidth="1.5" strokeDasharray="5 4" />
        {closed.map((s, i) => (
          <text key={s.period} x={x(i)} y={h - 8} fontSize="8" textAnchor="middle" fill="var(--muted)">
            {s.label}
          </text>
        ))}
      </svg>
    </div>
  );
}

function DeptVarianceChart({ rows }: { rows: DepartmentVariance[] }) {
  if (!rows.length) return null;
  const sorted = [...rows].sort((a, b) => Math.abs(num(b.variance)) - Math.abs(num(a.variance))).slice(0, 8);
  const w = 520;
  const h = 28 + sorted.length * 28;
  const padL = 100;
  const maxV = Math.max(...sorted.map((r) => Math.abs(num(r.variance))), 1);
  return (
    <svg className="mpl-chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Department variance">
      {sorted.map((r, i) => {
        const v = num(r.variance);
        const barW = (Math.abs(v) / maxV) * (w - padL - 40);
        const y = 16 + i * 28;
        const favorable = v <= 0;
        return (
          <g key={r.department}>
            <text x={padL - 8} y={y + 4} fontSize="9" textAnchor="end" fill="var(--text)">
              {r.department}
            </text>
            <rect
              x={padL}
              y={y - 8}
              width={Math.max(barW, 2)}
              height={14}
              fill={favorable ? "#15803d" : "#D85A30"}
              rx="2"
            />
            <text x={padL + barW + 6} y={y + 4} fontSize="8" fill="var(--muted)">
              {money(v)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function OpexDonutChart({ series, asOf }: { series: MonthlySeries[]; asOf: string }) {
  const row = [...series].reverse().find((s) => s.is_closed && s.period <= asOf) ?? series.find((s) => s.is_closed);
  if (!row) return null;
  const sm = num(row.opex_stack_sm) || num(row.sm);
  const rd = num(row.opex_stack_rd) || num(row.rd);
  const ga = num(row.opex_stack_ga) || num(row.ga);
  const total = sm + rd + ga;
  if (!total) return null;
  const slices = [
    { label: "S&M", value: sm, color: "#1a2e44" },
    { label: "R&D", value: rd, color: "#1D9E75" },
    { label: "G&A+Fin", value: ga, color: "#BA7517" },
  ];
  let angle = -90;
  const cx = 80;
  const cy = 80;
  const r = 56;
  const ir = 35;
  const paths = slices.map((s) => {
    const pct = s.value / total;
    const sweep = pct * 360;
    const a0 = (angle * Math.PI) / 180;
    angle += sweep;
    const a1 = (angle * Math.PI) / 180;
    const x0 = cx + r * Math.cos(a0);
    const y0 = cy + r * Math.sin(a0);
    const x1 = cx + r * Math.cos(a1);
    const y1 = cy + r * Math.sin(a1);
    const ix0 = cx + ir * Math.cos(a1);
    const iy0 = cy + ir * Math.sin(a1);
    const ix1 = cx + ir * Math.cos(a0);
    const iy1 = cy + ir * Math.sin(a0);
    const large = sweep > 180 ? 1 : 0;
    const d = `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} L ${ix0} ${iy0} A ${ir} ${ir} 0 ${large} 0 ${ix1} ${iy1} Z`;
    return { ...s, d, pct };
  });
  return (
    <div className="mpl-donut-wrap">
      <svg viewBox="0 0 160 160" className="mpl-donut">
        {paths.map((s) => (
          <path key={s.label} d={s.d} fill={s.color} />
        ))}
        <text x={cx} y={cy + 4} textAnchor="middle" fontSize="11" fill="var(--text)">
          {row.label}
        </text>
      </svg>
      <div className="mpl-donut-legend">
        {paths.map((s) => (
          <div key={s.label}>
            <span style={{ color: s.color }}>■</span> {s.label} {(s.pct * 100).toFixed(0)}%
          </div>
        ))}
      </div>
    </div>
  );
}

function PlRow({
  line,
  expanded,
  toggle,
  depth = 0,
}: {
  line: PlLine;
  expanded: Set<string>;
  toggle: (id: string) => void;
  depth?: number;
}) {
  const m = line.metrics;
  const isMargin = line.line_type === "margin";
  const isHeader = line.line_type === "header";
  const isTotal = line.line_type === "total" || line.is_bold;
  const open = expanded.has(line.id);
  const cell = (v: string | number | null | undefined, isPct = false) => (isMargin || isPct ? pct(v) : money(v));

  if (isHeader) {
    return (
      <tr className="mpl-pl-sec">
        <td colSpan={9}>{line.label}</td>
      </tr>
    );
  }

  return (
    <>
      <tr
        className={`${depth === 0 ? "mpl-row" : "mpl-pl-drill"} ${isTotal ? "mpl-pl-tot" : ""}`}
        onClick={() => line.expandable && toggle(line.id)}
        style={{ cursor: line.expandable ? "pointer" : undefined }}
      >
        <td style={{ paddingLeft: 12 + depth * 16 }}>
          {line.expandable ? (
            <span className="mpl-chevron">{open ? "▼" : "▶"}</span>
          ) : (
            <span className="mpl-chevron muted">·</span>
          )}
          <span className={line.is_bold ? "mpl-bold" : undefined}>
            {line.label}
            {line.driver === "non_recurring" ? (
              <span className="mpl-badge-one-time">One-time</span>
            ) : null}
          </span>
        </td>
        <td className="mpl-num">{cell(m.actual)}</td>
        <td className="mpl-num">{cell(m.budget)}</td>
        <td className={`mpl-num ${varClass(line.section_key, line.label, num(m.variance))}`}>{cell(m.variance)}</td>
        <td className={`mpl-num ${varClass(line.section_key, line.label, num(m.variance))}`}>
          {m.variance_pct != null ? pct(m.variance_pct) : "—"}
        </td>
        <td className="mpl-num">{cell(m.ytd_actual ?? m.outlook)}</td>
        <td className="mpl-num">{cell(m.ytd_budget ?? m.budget)}</td>
        <td className={`mpl-num ${varClass(line.section_key, line.label, num(m.ytd_variance ?? m.variance))}`}>
          {cell(m.ytd_variance ?? m.variance)}
        </td>
        <td className="mpl-num mpl-forecast-col">{cell(m.forecast)}</td>
      </tr>
      {open &&
        line.children.map((c) => (
          <PlRow key={c.id} line={c} expanded={expanded} toggle={toggle} depth={depth + 1} />
        ))}
    </>
  );
}

export function ManagementPnLDashboard({
  orgId,
  queryStart,
  queryEnd,
  asOfPeriod,
  periodView,
  scenario = "Combined",
  enabled,
  workforceValidation = [],
}: {
  orgId: string;
  globalScenario?: string;
  queryStart: string;
  queryEnd: string;
  asOfPeriod: string;
  periodView: string;
  scenario?: string;
  enabled: boolean;
  workforceValidation?: WorkforceValidationCheck[];
}) {
  const [periodMode, setPeriodMode] = useState<PeriodMode>("month");
  const [selectedMonth, setSelectedMonth] = useState("");
  const [viewMode, setViewMode] = useState<"management" | "accounting">("management");
  const [department, setDepartment] = useState("Total Company");
  const [subTab, setSubTab] = useState<SubTab>("summary");
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [glDept, setGlDept] = useState("Sales");

  useEffect(() => {
    const mapped = mapPeriodMode(periodView);
    setPeriodMode(mapped === "fy" ? "month" : mapped);
  }, [periodView]);

  useEffect(() => {
    if (!selectedMonth && asOfPeriod) {
      setSelectedMonth(asOfPeriod.slice(0, 7));
    }
  }, [asOfPeriod, selectedMonth]);

  const apiAsOf = periodMode === "month" && selectedMonth ? selectedMonth : asOfPeriod;
  const periodLabel = (data?.metadata?.period_scope_label as string) || "Selected period";

  const load = useCallback(async () => {
    if (!orgId || !enabled) return;
    setBusy(true);
    setError(null);
    try {
      const dates = statementPeriodParams(queryStart, queryEnd);
      const params = new URLSearchParams({
        organization_id: orgId,
        start_period: dates.start_period,
        end_period: dates.end_period,
        as_of_period: toApiDateParam(apiAsOf),
        period_mode: periodMode,
        view_mode: viewMode,
        department,
        _: String(Date.now()),
      });
      const url = `${getNextApiBase()}/api/v1/management-pl/dashboard?${params}`;
      setData(await fetchJson<DashboardPayload>(url, undefined, 60000));
    } catch (e) {
      const url = `${getNextApiBase()}/api/v1/management-pl/dashboard`;
      setError(formatFetchError(e, url));
      setData(null);
    } finally {
      setBusy(false);
    }
  }, [orgId, enabled, queryStart, queryEnd, apiAsOf, periodMode, viewMode, department]);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const glRows = useMemo(() => {
    if (!data?.gl_by_department) return [];
    return data.gl_by_department[glDept] ?? [];
  }, [data, glDept]);

  const closedMonths = useMemo(() => {
    const fromMeta = (data?.metadata?.closed_periods as string[]) || [];
    if (fromMeta.length) return fromMeta;
    return selectedMonth ? [selectedMonth] : [];
  }, [data, selectedMonth]);

  return (
    <div className="mpl-root">
      <OperatingSectionHeader
        title="Management P&L"
        subtitle={
          data?.outlook_label
            ? `${data.outlook_label} · compared to full-year budget${
                data.metadata?.gl_primary_mode ? " · GL detail primary" : ""
              }`
            : "Operating statement with FY outlook vs budget"
        }
      />

      <div className="mpl-toolbar">
        <div className="mpl-chips">
          {closedMonths.map((p) => (
            <button
              key={p}
              type="button"
              className={`mpl-chip ${periodMode === "month" && selectedMonth === p ? "active" : ""}`}
              onClick={() => {
                setSelectedMonth(p);
                setPeriodMode("month");
              }}
            >
              {monthChipLabel(p)}
            </button>
          ))}
          <button
            type="button"
            className={`mpl-chip ${periodMode === "qtd" ? "active" : ""}`}
            onClick={() => setPeriodMode("qtd")}
          >
            QTD
          </button>
          <button
            type="button"
            className={`mpl-chip ${periodMode === "ytd" ? "active" : ""}`}
            onClick={() => setPeriodMode("ytd")}
          >
            YTD
          </button>
        </div>
        <label className="mpl-inline">
          Department
          <select value={department} onChange={(e) => setDepartment(e.target.value)}>
            {DEPARTMENTS.map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </label>
        <label className="mpl-inline">
          View
          <select value={viewMode} onChange={(e) => setViewMode(e.target.value as "management" | "accounting")}>
            <option value="management">Management View</option>
            <option value="accounting">Accounting (incl. SBC)</option>
          </select>
        </label>
        <button type="button" className="mpl-refresh" onClick={load} disabled={busy}>
          {busy ? "Loading…" : "Refresh"}
        </button>
      </div>

      <nav className="mpl-subtabs">
        {(
          [
            ["summary", "P&L Summary"],
            ["bridge", "EBITDA Bridge"],
            ["statement", "3 - Statement"],
            ["department", "By Department"],
            ["gl", "GL Drilldown"],
            ["trend", "Trend Analysis"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={subTab === id ? "active" : ""}
            onClick={() => setSubTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {workforceValidation.length > 0 && (
        <WorkforceValidationStrip
          checks={workforceValidation}
          section="management-pl"
          title="Workforce P&L overlay · payroll"
        />
      )}

      {error && subTab !== "statement" && <pre className="mpl-error">{error}</pre>}
      {!data && !error && busy && subTab !== "statement" && (
        <p className="mpl-muted">Loading management P&L…</p>
      )}

      {subTab === "statement" && (
        <ManagementStatementTab
          orgId={orgId}
          queryStart={queryStart}
          queryEnd={queryEnd}
          scenario={scenario}
          enabled={enabled}
        />
      )}

      {data && subTab !== "statement" && (
        <>
          {data.validations.length > 0 && (
            <div className="mpl-validations">
              {data.validations.map((v) => (
                <div key={v.code} className={v.code === "gl_primary" ? "pass" : v.severity}>
                  {v.message}
                </div>
              ))}
            </div>
          )}

          <section className="mpl-kpi-strip">
            {data.kpis.map((k) => (
              <div key={k.key} className="mpl-kpi-card">
                <div className="mpl-kpi-label">{k.label}</div>
                <div className="mpl-kpi-value">{formatKpi(k)}</div>
                {k.delta_label ? <div className={`mpl-kpi-delta ${k.tone}`}>{k.delta_label} {k.compare_label}</div> : null}
                {k.compare_value != null && k.value_format === "currency" && (
                  <div className="mpl-kpi-note">Budget {money(k.compare_value)}</div>
                )}
                {k.compare_value != null && k.value_format === "percent" && (
                  <div className="mpl-kpi-note">Budget {pct(k.compare_value)}</div>
                )}
              </div>
            ))}
          </section>

          {subTab === "summary" && (
            <>
              <div className="mpl-chart-grid">
                <div className="mpl-panel">
                  <div className="mpl-section-label">Revenue & gross profit (FY path)</div>
                  <div className="mpl-chart-scroll">
                    <RevenueGpPathChart series={data.monthly_series} closedThrough={data.as_of_period} />
                  </div>
                </div>
                <div className="mpl-panel">
                  <div className="mpl-section-label">OpEx composition</div>
                  <div className="mpl-chart-scroll">
                    <StackedOpexChart series={data.monthly_series} />
                  </div>
                </div>
              </div>

              <div className="mpl-panel mpl-table-wrap">
                <div className="mpl-section-label">Management P&L · {periodLabel}</div>
                <div className="mpl-table-actions">
                  <button type="button" className="mpl-refresh" onClick={() => setExpanded(new Set(collectIds(data.pl_lines)))}>
                    Expand all
                  </button>
                  <button type="button" className="mpl-refresh" onClick={() => setExpanded(new Set())}>
                    Collapse all
                  </button>
                </div>
                <table className="mpl-table mpl-pl-table">
                  <thead>
                    <tr>
                      <th>Line item</th>
                      <th>Period Act</th>
                      <th>Period Bud</th>
                      <th>Var $</th>
                      <th>Var %</th>
                      <th>YTD Act</th>
                      <th>YTD Bud</th>
                      <th>YTD Var</th>
                      <th>H2 Forecast</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.pl_lines.map((line) => (
                      <PlRow key={line.id} line={line} expanded={expanded} toggle={toggle} />
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {subTab === "bridge" && (
            <div className="mpl-panel">
              <div className="mpl-section-label">EBITDA bridge · {periodLabel}</div>
              <WaterfallChart steps={data.ebitda_waterfall} />
              <div className="mpl-chart-grid" style={{ marginTop: 24 }}>
                <MarginTrendChart
                  series={data.monthly_series}
                  fieldActual="gm_pct_actual"
                  fieldBudget="gm_pct_budget"
                  title="Gross margin % trend"
                />
                <MarginTrendChart
                  series={data.monthly_series}
                  fieldActual="ebitda_margin_actual"
                  fieldBudget="ebitda_margin_budget"
                  title="EBITDA margin % trend"
                />
              </div>
            </div>
          )}

          {subTab === "department" && (
            <div className="mpl-panel">
              <div className="mpl-section-label">By department · {periodLabel}</div>
              <div className="mpl-chart-grid">
                <DeptVarianceChart rows={data.department_variances} />
                <OpexDonutChart series={data.monthly_series} asOf={data.as_of_period} />
              </div>
              <table className="mpl-table" style={{ marginTop: 16 }}>
                <thead>
                  <tr>
                    <th>Dept</th>
                    <th>HC</th>
                    <th>Period Act</th>
                    <th>Period Bud</th>
                    <th>Var $</th>
                    <th>Var %</th>
                    <th>YTD Act</th>
                    <th>YTD Bud</th>
                    <th>YTD Var</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.department_summary?.length ? data.department_summary : []).map((d) => (
                    <tr key={d.department} className="mpl-row">
                      <td>{d.department}</td>
                      <td className="mpl-num">{num(d.headcount) ? num(d.headcount).toFixed(0) : "—"}</td>
                      <td className="mpl-num">{money(d.period_actual)}</td>
                      <td className="mpl-num">{money(d.period_budget)}</td>
                      <td className={`mpl-num ${varClass("total_opex", d.department, num(d.variance))}`}>
                        {money(d.variance)}
                      </td>
                      <td className="mpl-num">{d.variance_pct != null ? pct(d.variance_pct) : "—"}</td>
                      <td className="mpl-num">{money(d.ytd_actual)}</td>
                      <td className="mpl-num">{money(d.ytd_budget)}</td>
                      <td className={`mpl-num ${varClass("total_opex", d.department, num(d.ytd_variance))}`}>
                        {money(d.ytd_variance)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {subTab === "gl" && (
            <div className="mpl-panel">
              <div className="mpl-dept-tabs">
                {GL_DEPARTMENTS.map((d) => (
                  <button key={d} type="button" className={glDept === d ? "active" : ""} onClick={() => setGlDept(d)}>
                    {d === "Customer Success" ? "CS" : d}
                  </button>
                ))}
              </div>
              <table className="mpl-table">
                <thead>
                  <tr>
                    <th>GL Account</th>
                    <th>Period Actual</th>
                    <th>Period Budget</th>
                    <th>Var $</th>
                    <th>Var %</th>
                    <th>YTD Actual</th>
                    <th>H2 Forecast</th>
                  </tr>
                </thead>
                <tbody>
                  {glRows.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="mpl-muted">
                        No GL rows for {glDept}. Upload Actual/Budget/Forecast GL detail CSVs.
                      </td>
                    </tr>
                  ) : (
                    glRows.map((r) => (
                      <tr key={`${r.account_group}-${r.account}`} className="mpl-row">
                        <td>
                          {r.account}
                          {r.is_non_recurring ? (
                            <span className="mpl-badge-one-time" title="Non-recurring">
                              One-time
                            </span>
                          ) : null}
                        </td>
                        <td className="mpl-num">{money(r.outlook)}</td>
                        <td className="mpl-num">{money(r.budget)}</td>
                        <td className={`mpl-num ${varClass("total_opex", r.account, num(r.variance))}`}>{money(r.variance)}</td>
                        <td className="mpl-num">{r.variance_pct != null ? pct(r.variance_pct) : "—"}</td>
                        <td className="mpl-num">{money(r.ytd_outlook)}</td>
                        <td className="mpl-num">{money(r.h2_forecast)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {subTab === "trend" && (
            <div className="mpl-panel">
              <div className="mpl-section-label">Monthly outlook path</div>
              <RevenueGpPathChart series={data.monthly_series} closedThrough={data.as_of_period} />
              <table className="mpl-table" style={{ marginTop: 16 }}>
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>Rev actual</th>
                    <th>Rev forecast</th>
                    <th>Rev budget</th>
                    <th>GP actual</th>
                    <th>GP forecast</th>
                    <th>GP budget</th>
                    <th>OpEx total</th>
                    <th>GM%</th>
                  </tr>
                </thead>
                <tbody>
                  {data.monthly_series.map((s) => {
                    const revBase = s.is_closed ? num(s.revenue_actual) : num(s.revenue_forecast) || num(s.revenue_outlook);
                    const gpBase = s.is_closed ? num(s.gross_profit_actual) : num(s.gross_profit_forecast) || num(s.gross_profit_outlook);
                    const gm = revBase ? gpBase / revBase : 0;
                    return (
                      <tr key={s.period}>
                        <td>{s.period}{s.is_closed ? " · Actual" : " · Forecast"}</td>
                        <td className="mpl-num">{s.is_closed ? money(s.revenue_actual) : "—"}</td>
                        <td className="mpl-num">{!s.is_closed ? money(s.revenue_forecast || s.revenue_outlook) : "—"}</td>
                        <td className="mpl-num">{money(s.revenue_budget)}</td>
                        <td className="mpl-num">{s.is_closed ? money(s.gross_profit_actual) : "—"}</td>
                        <td className="mpl-num">{!s.is_closed ? money(s.gross_profit_forecast || s.gross_profit_outlook) : "—"}</td>
                        <td className="mpl-num">{money(s.gross_profit_budget)}</td>
                        <td className="mpl-num">
                          {money(
                            s.total_opex ||
                              stackValue(s, OPEX_STACKS[0]) + stackValue(s, OPEX_STACKS[1]) + stackValue(s, OPEX_STACKS[2])
                          )}
                        </td>
                        <td className="mpl-num">{pct(gm * 100)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {data.commentary.length > 0 && (
            <div className="mpl-commentary-grid">
              {data.commentary.map((c) => (
                <div key={c.section} className="mpl-panel">
                  <div className="mpl-section-label">{c.section}</div>
                  <p className="mpl-lead">{c.observation}</p>
                  <p>{c.implication}</p>
                  <p className="mpl-muted">{c.recommendation}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
