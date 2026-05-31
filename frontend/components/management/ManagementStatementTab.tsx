"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { formatFetchError, getApiBase } from "../../lib/apiBase";
import { fetchJson } from "../../lib/fetchJson";
import {
  FinancialStatementTable,
  type FinancialStatementsSummary,
  statementPeriodParams,
} from "../FinancialStatementTable";

function monthRange(startPeriod: string, endPeriod: string) {
  const start = startPeriod.length >= 7 ? startPeriod.slice(0, 7) : startPeriod;
  const end = endPeriod.length >= 7 ? endPeriod.slice(0, 7) : endPeriod;
  const [startYear, startMonth] = start.split("-").map(Number);
  const [endYear, endMonth] = end.split("-").map(Number);
  const periods: string[] = [];
  let year = startYear;
  let month = startMonth;
  while (year < endYear || (year === endYear && month <= endMonth)) {
    periods.push(`${year}-${String(month).padStart(2, "0")}`);
    month += 1;
    if (month === 13) {
      month = 1;
      year += 1;
    }
  }
  return periods;
}

const STATEMENT_SECTIONS = [
  { key: "cash", title: "Cash Flow Statement", pick: (s: FinancialStatementsSummary) => s.cash_flow },
  { key: "income", title: "Income Statement", pick: (s: FinancialStatementsSummary) => s.income_statement },
  { key: "balance", title: "Balance Sheet", pick: (s: FinancialStatementsSummary) => s.balance_sheet },
] as const;

export function ManagementStatementTab({
  orgId,
  queryStart,
  queryEnd,
  scenario,
  enabled,
}: {
  orgId: string;
  queryStart: string;
  queryEnd: string;
  scenario: string;
  enabled: boolean;
}) {
  const [statements, setStatements] = useState<FinancialStatementsSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const periodsOverride = useMemo(() => monthRange(queryStart, queryEnd), [queryStart, queryEnd]);
  const apiBase = getApiBase();

  const load = useCallback(async () => {
    if (!orgId || !enabled) return;
    setBusy(true);
    setError(null);
    try {
      const dates = statementPeriodParams(queryStart, queryEnd);
      const params = new URLSearchParams({
        organization_id: orgId,
        scenario,
        start_period: dates.start_period,
        end_period: dates.end_period,
        _: String(Date.now()),
      });
      setStatements(
        await fetchJson<FinancialStatementsSummary>(
          `${apiBase}/api/v1/financial-statements/summary?${params}`,
          undefined,
          60000
        )
      );
    } catch (e) {
      setStatements(null);
      setError(formatFetchError(e, `${apiBase}/api/v1/financial-statements/summary`));
    } finally {
      setBusy(false);
    }
  }, [orgId, enabled, queryStart, queryEnd, scenario, apiBase]);

  useEffect(() => {
    load();
  }, [load]);

  const validationIssues = (statements?.validation ?? []).filter((v) => v.status !== "pass");

  return (
    <div className="mpl-statements">
      <p className="mpl-muted" style={{ marginTop: 0 }}>
        Normalized {scenario} statements from uploaded warehouse CSVs · {queryStart} through {queryEnd}
      </p>

      {error && <pre className="mpl-error">{error}</pre>}
      {busy && !statements && !error && <p className="mpl-muted">Loading financial statements…</p>}

      {validationIssues.length > 0 && (
        <div className="mpl-validations">
          {validationIssues.slice(0, 4).map((v) => (
            <div key={`${v.scenario}-${v.period}-${v.validation_name}`} className="warning">
              {v.scenario} {v.period.slice(0, 7)} · {v.validation_name} · variance{" "}
              {Number(v.variance ?? 0).toLocaleString()}
            </div>
          ))}
        </div>
      )}

      {STATEMENT_SECTIONS.map(({ key, title, pick }) => {
        const statement = statements ? pick(statements) : null;
        return (
          <div key={key} className="mpl-panel mpl-table-wrap">
            <div className="mpl-section-label">{title}</div>
            {statement && statement.periods.length > 0 ? (
              <FinancialStatementTable statement={statement} periodsOverride={periodsOverride} />
            ) : (
              !busy &&
              !error && (
                <p className="mpl-muted">
                  No {title.toLowerCase()} rows for this period. Upload Actual_, Budget_, and Forecast_ statement CSVs,
                  then refresh.
                </p>
              )
            )}
          </div>
        );
      })}
    </div>
  );
}
