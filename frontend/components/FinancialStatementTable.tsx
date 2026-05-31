"use client";

import { useMemo } from "react";
import type { CSSProperties } from "react";

import {
  categoryCellStyle,
  categoryHeaderStyle,
  dashboardTableStyle,
  formatDashboardPeriodHeader,
  normalizeDashboardPeriod,
  periodCellStyle,
  periodHeaderStyle,
} from "../lib/dashboardPeriodColumns";

export type StatementLine = {
  organization_id: string;
  scenario: string;
  period: string;
  line_item: string;
  line_item_order: number;
  section: string;
  amount: string | number;
  source_table: string;
  source_column: string;
};

export type StatementResponse = {
  statement_type: string;
  rows: StatementLine[];
  periods: string[];
};

export type FinancialStatementsSummary = {
  organization_id: string;
  scenario: string;
  start_period: string;
  end_period: string;
  income_statement: StatementResponse;
  balance_sheet: StatementResponse;
  cash_flow: StatementResponse;
  validation: {
    scenario: string;
    period: string;
    validation_name: string;
    status: "pass" | "warning" | "fail";
    expected_value?: string | number | null;
    actual_value?: string | number | null;
    variance?: string | number | null;
    source_tables_used: string[];
  }[];
};

export function statementPeriodParams(startPeriod: string, endPeriod: string) {
  if (/^\d{4}-\d{2}$/.test(startPeriod)) {
    const [endYear, endMonth] = endPeriod.split("-").map(Number);
    const endDay = new Date(Date.UTC(endYear, endMonth, 0)).getUTCDate();
    return {
      start_period: `${startPeriod}-01`,
      end_period: `${endPeriod}-${String(endDay).padStart(2, "0")}`,
    };
  }
  return { start_period: startPeriod, end_period: endPeriod };
}

export function FinancialStatementTable({
  statement,
  periodsOverride,
}: {
  statement: StatementResponse;
  periodsOverride?: string[];
}) {
  const periods =
    periodsOverride ??
    Array.from(new Set(statement.periods.map((period) => normalizeDashboardPeriod(period)))).sort();
  const lines = useMemo(() => {
    const byLine = new Map<string, StatementLine>();
    statement.rows.forEach((r) => {
      if (!byLine.has(r.line_item)) byLine.set(r.line_item, r);
    });
    return Array.from(byLine.values()).sort((a, b) => a.line_item_order - b.line_item_order);
  }, [statement.rows]);
  const values = useMemo(() => {
    const map = new Map<string, StatementLine>();
    statement.rows.forEach((r) =>
      map.set(`${r.line_item}-${normalizeDashboardPeriod(r.period)}`, r)
    );
    return map;
  }, [statement.rows]);

  return (
    <div style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: 10 }}>
      <table style={dashboardTableStyle(periods.length)}>
        <thead>
          <tr style={{ background: "#f9fafb" }}>
            <th style={categoryHeaderStyle(th)}>Line Item</th>
            {periods.map((p) => {
              const scenario =
                statement.rows.find((r) => normalizeDashboardPeriod(r.period) === p)?.scenario ?? "";
              return (
                <th key={p} style={periodHeaderStyle(th)}>
                  {formatDashboardPeriodHeader(p)}
                  <div style={{ marginTop: 4 }}>
                    <span style={scenarioPill(scenario)}>{scenario}</span>
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => (
            <tr key={line.line_item}>
              <td style={{ ...categoryCellStyle(td), fontWeight: isSubtotal(line.line_item) ? 700 : 500 }}>
                {line.line_item}
                <div style={{ color: "var(--muted)", fontSize: 11 }}>{line.section}</div>
              </td>
              {periods.map((p) => {
                const match = values.get(`${line.line_item}-${p}`);
                return (
                  <td
                    key={`${line.line_item}-${p}`}
                    title={match ? `${match.source_table}.${match.source_column}` : undefined}
                    style={periodCellStyle(td, { fontWeight: isSubtotal(line.line_item) ? 700 : 400 })}
                  >
                    {match ? money(match.amount) : ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function money(value: string | number | null | undefined) {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function isSubtotal(lineItem: string) {
  return (
    lineItem.startsWith("Total") ||
    lineItem.startsWith("Net") ||
    lineItem === "Gross Profit" ||
    lineItem === "EBITDA" ||
    lineItem === "Operating Income" ||
    lineItem === "Balance Check" ||
    lineItem === "Ending Cash Balance"
  );
}

const th: CSSProperties = {
  textAlign: "left",
  padding: 10,
  borderBottom: "1px solid var(--border)",
  whiteSpace: "nowrap",
};
const td: CSSProperties = { padding: 10, borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" };

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
