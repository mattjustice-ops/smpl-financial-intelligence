"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

import { useActiveOrganization } from "../hooks/useActiveOrganization";
import { fetchJson } from "../lib/fetchJson";
import {
  FinancialStatementTable,
  type FinancialStatementsSummary,
  statementPeriodParams,
} from "./FinancialStatementTable";

const apiBase =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";


type ValidationResult = FinancialStatementsSummary["validation"][number];

type SummaryResponse = FinancialStatementsSummary;

type Org = { id: string; name: string };

type ForecastTableRow = {
  period: string;
  period_type: string;
  values: Record<string, string | number | null>;
};

type ForecastScheduleResponse = {
  schedule_name: string;
  actual_periods: string[];
  forecast_periods: string[];
  rows: ForecastTableRow[];
};

const statementTabs = [
  ["income_statement", "Income Statement"],
  ["balance_sheet", "Balance Sheet"],
  ["cash_flow", "Cash Flow Statement"],
  ["driver_assumptions", "Driver Assumptions"],
  ["validation", "Validation"],
] as const;

function money(value: string | number | null | undefined) {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function periodLabel(period: string) {
  const d = new Date(period);
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
}

function statusColor(status: string) {
  if (status === "pass") return "#166534";
  if (status === "warning") return "#92400e";
  return "#b91c1c";
}

export function FinancialStatementsDashboard({ enabled = true }: { enabled?: boolean }) {
  const { organizationId, organizations, isLoading: sessionLoading } = useActiveOrganization();
  const orgs = organizations;
  const [orgId, setOrgId] = useState("");
  const [scenario, setScenario] = useState("Combined");
  const [startPeriod, setStartPeriod] = useState("2026-01-01");
  const [endPeriod, setEndPeriod] = useState("2026-12-31");
  const [tab, setTab] = useState<(typeof statementTabs)[number][0]>("income_statement");
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [assumptions, setAssumptions] = useState<ForecastScheduleResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);

  useEffect(() => {
    if (organizationId) {
      setOrgId(organizationId);
    }
  }, [organizationId]);

  const load = async () => {
    if (!enabled || !orgId || sessionLoading) return;
    setBusy(true);
    setError(null);
    try {
      const periodParams = statementPeriodParams(startPeriod, endPeriod);
      const params = new URLSearchParams({
        organization_id: orgId,
        scenario,
        start_period: periodParams.start_period,
        end_period: periodParams.end_period,
        _: String(Date.now()),
      });
      setSummary(
        await fetchJson<SummaryResponse>(`${apiBase}/api/v1/financial-statements/summary?${params}`)
      );

      const assumptionParams = new URLSearchParams({
        organization_id: orgId,
        scenario: scenario === "Combined" ? "Forecast" : scenario,
        start_period: startPeriod,
        end_period: endPeriod,
        _: String(Date.now()),
      });
      try {
        setAssumptions(
          await fetchJson<ForecastScheduleResponse>(
            `${apiBase}/api/v1/forecast/assumptions?${assumptionParams}`
          )
        );
      } catch {
        setAssumptions(null);
      }
      setLastRefresh(new Date().toLocaleString());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!enabled) return;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  const activeStatement =
    tab === "income_statement"
      ? summary?.income_statement
      : tab === "balance_sheet"
      ? summary?.balance_sheet
      : tab === "cash_flow"
      ? summary?.cash_flow
      : null;

  const warnings = (summary?.validation ?? []).filter((v) => v.status !== "pass");
  const failed = warnings.filter((v) => v.status === "fail");
  const warningOnly = warnings.filter((v) => v.status === "warning");

  return (
    <section style={card}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 20 }}>Financial Statements</h2>
          <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.5 }}>
            Normalized Actual, Budget, and Forecast statements sourced directly from uploaded CSV tables.
          </p>
        </div>
        <button type="button" onClick={load} disabled={busy || !orgId}>
          {busy ? "Loading..." : "Refresh Statements"}
        </button>
      </div>
      {lastRefresh && <div style={{ marginTop: 8, color: "var(--muted)", fontSize: 12 }}>Last refreshed from API: {lastRefresh}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "2fr repeat(3, 1fr)", gap: 10, marginTop: 16 }}>
        <label style={label}>
          Organization
          <select style={input} value={orgId} onChange={(e) => setOrgId(e.target.value)}>
            <option value={orgId}>{orgs.find((o) => o.id === orgId)?.name ?? orgId}</option>
            {orgs
              .filter((o) => o.id !== orgId)
              .map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
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
          Start
          <input style={input} type="date" value={startPeriod} onChange={(e) => setStartPeriod(e.target.value)} />
        </label>
        <label style={label}>
          End
          <input style={input} type="date" value={endPeriod} onChange={(e) => setEndPeriod(e.target.value)} />
        </label>
      </div>

      {error && <pre style={errorBox}>{error}</pre>}

      {warnings.length > 0 && (
        <div style={warningBox}>
          <strong>
            {failed.length} fail(s), {warningOnly.length} warning(s)
          </strong>
          <div style={{ marginTop: 6 }}>
            {warnings.slice(0, 5).map((w) => (
              <div key={`${w.scenario}-${w.period}-${w.validation_name}`}>
                {w.scenario} {w.period.slice(0, 7)}: {w.validation_name} variance {money(w.variance)}
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
        {statementTabs.map(([key, labelText]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            style={{
              borderColor: tab === key ? "var(--accent)" : "var(--border)",
              background: tab === key ? "#eff6ff" : "#fff",
            }}
          >
            {labelText}
          </button>
        ))}
      </div>

      {summary && tab !== "validation" && tab !== "driver_assumptions" && activeStatement && (
        <div style={{ marginTop: 16 }}>
          <FinancialStatementTable statement={activeStatement} />
        </div>
      )}
      {tab === "driver_assumptions" && <AssumptionsTable schedule={assumptions} />}
      {summary && tab === "validation" && <ValidationTable rows={summary.validation} />}
    </section>
  );
}

function AssumptionsTable({ schedule }: { schedule: ForecastScheduleResponse | null }) {
  const metrics = useMemo(() => {
    const keys = new Set<string>();
    schedule?.rows.forEach((row) => Object.keys(row.values).forEach((key) => keys.add(key)));
    return Array.from(keys);
  }, [schedule]);

  if (!schedule) {
    return (
      <div style={emptyBox}>
        Driver assumptions were not returned by the forecast assumptions API for this selection.
      </div>
    );
  }

  return (
    <div style={{ marginTop: 16, overflowX: "auto", border: "1px solid var(--border)", borderRadius: 10 }}>
      <table style={{ width: "100%", minWidth: 900, borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#f9fafb" }}>
            <th style={{ ...th, position: "sticky", left: 0, background: "#f9fafb", zIndex: 2 }}>Assumption</th>
            {schedule.rows.map((row) => (
              <th key={row.period} style={{ ...th, textAlign: "right" }}>
                {periodLabel(row.period)}
                <div style={{ marginTop: 4 }}>
                  <span style={scenarioPill(row.period_type)}>{row.period_type}</span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric) => (
            <tr key={metric}>
              <td style={{ ...td, position: "sticky", left: 0, background: "#fff", fontWeight: 600 }}>{labelize(metric)}</td>
              {schedule.rows.map((row) => (
                <td key={`${metric}-${row.period}`} style={{ ...td, textAlign: "right" }}>
                  {formatAssumptionValue(row.values[metric])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ValidationTable({ rows }: { rows: ValidationResult[] }) {
  const [statusFilter, setStatusFilter] = useState<"all" | "fail" | "warning" | "pass">("all");
  const visibleRows = statusFilter === "all" ? rows : rows.filter((row) => row.status === statusFilter);

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
        {(["all", "fail", "warning", "pass"] as const).map((filter) => (
          <button
            key={filter}
            type="button"
            onClick={() => setStatusFilter(filter)}
            style={{
              borderColor: statusFilter === filter ? "var(--accent)" : "var(--border)",
              background: statusFilter === filter ? "#eff6ff" : "#fff",
            }}
          >
            {filter}
          </button>
        ))}
      </div>
      <div style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: 10 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#f9fafb" }}>
            <th style={th}>Status</th>
            <th style={th}>Scenario</th>
            <th style={th}>Period</th>
            <th style={th}>Validation</th>
            <th style={th}>Expected</th>
            <th style={th}>Actual</th>
            <th style={th}>Variance</th>
            <th style={th}>Sources</th>
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row) => (
            <tr key={`${row.scenario}-${row.period}-${row.validation_name}`}>
              <td style={{ ...td, color: statusColor(row.status), fontWeight: 700 }}>{row.status}</td>
              <td style={td}>{row.scenario}</td>
              <td style={td}>{row.period.slice(0, 7)}</td>
              <td style={td}>{row.validation_name}</td>
              <td style={{ ...td, textAlign: "right" }}>{money(row.expected_value)}</td>
              <td style={{ ...td, textAlign: "right" }}>{money(row.actual_value)}</td>
              <td style={{ ...td, textAlign: "right" }}>{money(row.variance)}</td>
              <td style={td}>{row.source_tables_used.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}

function labelize(key: string) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function formatAssumptionValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return Math.abs(n) < 10 ? n.toFixed(2) : n.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

const card: CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 16,
  background: "var(--card)",
};
const label: CSSProperties = { fontSize: 13, minWidth: 0 };
const input: CSSProperties = { display: "block", width: "100%", marginTop: 4, padding: 8 };
const th: CSSProperties = { textAlign: "left", padding: 10, borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" };
const td: CSSProperties = { padding: 10, borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" };
const errorBox: CSSProperties = { marginTop: 12, color: "#b91c1c", background: "#fef2f2", padding: 12, borderRadius: 8, whiteSpace: "pre-wrap" };
const warningBox: CSSProperties = { marginTop: 12, color: "#92400e", background: "#fffbeb", border: "1px solid #fde68a", padding: 12, borderRadius: 8, fontSize: 13 };
const emptyBox: CSSProperties = { marginTop: 16, color: "var(--muted)", background: "#f9fafb", border: "1px solid var(--border)", padding: 14, borderRadius: 10 };

function scenarioPill(scenarioName: string): CSSProperties {
  const normalized = scenarioName.toLowerCase();
  const isActual = normalized === "actual";
  const isWarning = normalized === "warning";
  return {
    borderRadius: 999,
    padding: "2px 8px",
    fontSize: 11,
    background: isActual ? "#f3f4f6" : isWarning ? "#fffbeb" : "#dbeafe",
    color: isActual ? "#111827" : isWarning ? "#92400e" : "#1d4ed8",
  };
}
