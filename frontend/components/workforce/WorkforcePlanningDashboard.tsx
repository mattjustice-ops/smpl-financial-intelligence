"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { formatFetchError, getWorkforceApiBase } from "../../lib/apiBase";
import { fetchJson } from "../../lib/fetchJson";
import { normalizePeriodKey, scenarioForPeriod, workforceApiScenario } from "../../lib/periodScenario";
import {
  mergeCombinedWorkforcePlans,
  rollupWorkforceDepartments,
  rollupWorkforcePeriods,
  type WorkforcePlanResponse,
} from "../../lib/workforcePlan";
import { statementPeriodParams } from "../FinancialStatementTable";
import { OperatingSectionHeader } from "../cfo/OperatingSectionHeader";
import {
  WorkforceValidationStrip,
  type WorkforceValidationCheck,
  type WorkforceValidationResponse,
} from "./WorkforceValidationStrip";

const apiBase = getWorkforceApiBase();

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

function WorkforcePeriodSummaryColgroup() {
  return (
    <colgroup>
      <col style={{ width: "10%" }} />
      <col style={{ width: "10%" }} />
      <col span={6} style={{ width: "13.33%" }} />
    </colgroup>
  );
}

function WorkforceDepartmentAnnualColgroup() {
  return (
    <colgroup>
      <col style={{ width: "14%" }} />
      <col span={7} style={{ width: "12.29%" }} />
    </colgroup>
  );
}

function WorkforceDepartmentMonthlyColgroup() {
  return (
    <colgroup>
      <col style={{ width: "9%" }} />
      <col style={{ width: "14%" }} />
      <col span={7} style={{ width: "11%" }} />
    </colgroup>
  );
}

function buildWorkforceParams(orgId: string, queryStart: string, queryEnd: string, scenario: string) {
  const dates = statementPeriodParams(queryStart, queryEnd);
  return new URLSearchParams({
    organization_id: orgId,
    scenario,
    start_period: dates.start_period,
    end_period: dates.end_period,
    _: String(Date.now()),
  });
}

async function fetchWorkforcePlan(
  orgId: string,
  queryStart: string,
  queryEnd: string,
  scenario: string
): Promise<WorkforcePlanResponse> {
  if (scenario !== "Combined") {
    const params = buildWorkforceParams(orgId, queryStart, queryEnd, workforceApiScenario(scenario));
    return fetchJson<WorkforcePlanResponse>(
      `${apiBase}/api/v1/workforce/plan?${params}&persist=false`,
      undefined,
      60000
    );
  }

  const [actual, forecast] = await Promise.all(
    (["Actual", "Forecast"] as const).map((slice) => {
      const params = buildWorkforceParams(orgId, queryStart, queryEnd, slice);
      return fetchJson<WorkforcePlanResponse>(
        `${apiBase}/api/v1/workforce/plan?${params}&persist=false`,
        undefined,
        60000
      );
    })
  );
  return mergeCombinedWorkforcePlans(actual, forecast, queryStart, queryEnd);
}

async function fetchWorkforceValidation(
  orgId: string,
  queryStart: string,
  queryEnd: string,
  scenario: string
): Promise<WorkforceValidationResponse> {
  if (scenario !== "Combined") {
    const params = buildWorkforceParams(orgId, queryStart, queryEnd, workforceApiScenario(scenario));
    return fetchJson<WorkforceValidationResponse>(`${apiBase}/api/v1/workforce/validation?${params}`, undefined, 60000);
  }

  const [actual, forecast] = await Promise.all(
    (["Actual", "Forecast"] as const).map((slice) => {
      const params = buildWorkforceParams(orgId, queryStart, queryEnd, slice);
      return fetchJson<WorkforceValidationResponse>(`${apiBase}/api/v1/workforce/validation?${params}`, undefined, 60000);
    })
  );
  const checks = [...actual.checks, ...forecast.checks];
  const failed_count = checks.filter((c) => c.status === "fail").length;
  const warning_count = checks.filter((c) => c.status === "warning").length;
  const passed_count = checks.filter((c) => c.status === "pass").length;
  const status = failed_count ? "fail" : warning_count ? "warning" : "pass";
  return {
    ...forecast,
    scenario: "Combined",
    checks,
    failed_count,
    warning_count,
    passed_count,
    status,
  };
}

export function WorkforcePlanningDashboard({
  orgId,
  queryStart,
  queryEnd,
  asOfPeriod,
  scenario,
  enabled,
  onDataChange,
}: {
  orgId: string;
  queryStart: string;
  queryEnd: string;
  asOfPeriod: string;
  scenario: string;
  enabled: boolean;
  onDataChange?: () => void;
}) {
  const [plan, setPlan] = useState<WorkforcePlanResponse | null>(null);
  const [validation, setValidation] = useState<WorkforceValidationResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [recomputeBusy, setRecomputeBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAllMonths, setShowAllMonths] = useState(false);

  const load = useCallback(async () => {
    if (!orgId || !enabled) return;
    setBusy(true);
    setError(null);
    try {
      const [planResult, validationResult] = await Promise.all([
        fetchWorkforcePlan(orgId, queryStart, queryEnd, scenario),
        fetchWorkforceValidation(orgId, queryStart, queryEnd, scenario),
      ]);
      setPlan(planResult);
      setValidation(validationResult);
    } catch (e) {
      setPlan(null);
      setValidation(null);
      setError(formatFetchError(e, `${apiBase}/api/v1/workforce/plan`));
    } finally {
      setBusy(false);
    }
  }, [orgId, enabled, queryStart, queryEnd, scenario]);

  useEffect(() => {
    load();
  }, [load]);

  const recompute = async () => {
    if (!orgId || !enabled) return;
    setRecomputeBusy(true);
    setError(null);
    try {
      const slices = scenario === "Combined" ? (["Actual", "Forecast"] as const) : [workforceApiScenario(scenario) as "Actual" | "Forecast" | "Budget"];
      for (const slice of slices) {
        const params = buildWorkforceParams(orgId, queryStart, queryEnd, slice);
        await fetchJson(`${apiBase}/api/v1/workforce/recompute?${params}`, { method: "POST" }, 120000);
      }
      await load();
      onDataChange?.();
    } catch (e) {
      setError(formatFetchError(e, `${apiBase}/api/v1/workforce/recompute`));
    } finally {
      setRecomputeBusy(false);
    }
  };

  const periodTotals = useMemo(() => rollupWorkforcePeriods(plan), [plan]);
  const asOfKey = normalizePeriodKey(asOfPeriod);
  const rangeStartKey = normalizePeriodKey(queryStart);
  const rangeEndKey = normalizePeriodKey(queryEnd);
  const asOfTotals = periodTotals.find(([period]) => period === asOfKey)?.[1];
  const asOfScenario = scenarioForPeriod(asOfKey, scenario);

  const departmentAnnualRows = useMemo(
    () => rollupWorkforceDepartments(plan, queryStart, queryEnd),
    [plan, queryStart, queryEnd]
  );

  const departmentMonthlyRows = useMemo(() => {
    return [...(plan?.period_summary ?? [])].sort((a, b) => {
      const periodCmp = normalizePeriodKey(a.period).localeCompare(normalizePeriodKey(b.period));
      if (periodCmp !== 0) return periodCmp;
      return a.department.localeCompare(b.department);
    });
  }, [plan?.period_summary]);

  const status = validation?.status ?? "pass";

  return (
    <>
      <OperatingSectionHeader
        title="Workforce Planning"
        subtitle={`Headcount · derived payroll · GTM quota capacity · as of ${asOfKey} (${asOfScenario})`}
      />

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", marginBottom: 12 }}>
        <button type="button" className="mpl-refresh" onClick={() => load()} disabled={busy || recomputeBusy}>
          {busy ? "Loading…" : "Refresh plan"}
        </button>
        <button type="button" className="mpl-refresh" onClick={recompute} disabled={busy || recomputeBusy}>
          {recomputeBusy ? "Recomputing…" : "Recompute workforce"}
        </button>
        <span
          style={{
            fontSize: 12,
            padding: "4px 10px",
            borderRadius: 999,
            background:
              status === "pass" ? "#ecfdf5" : status === "warning" ? "#fffbeb" : "#fef2f2",
            color: status === "pass" ? "#065f46" : status === "warning" ? "#92400e" : "#991b1b",
            border: "0.5px solid var(--border)",
          }}
        >
          Validation: {status}
          {validation ? ` · ${validation.passed_count} pass / ${validation.warning_count} warn / ${validation.failed_count} fail` : ""}
        </span>
      </div>

      {error && <pre className="mpl-error">{error}</pre>}
      {!plan && !error && busy && <p className="mpl-muted">Loading workforce plan…</p>}

      {plan && (
        <>
          <section className="mpl-kpi-strip">
            <div className="mpl-kpi-card">
              <div className="mpl-kpi-label">Headcount (total FTE)</div>
              <div className="mpl-kpi-value">{asOfTotals ? asOfTotals.total.toFixed(1) : "—"}</div>
            </div>
            <div className="mpl-kpi-card">
              <div className="mpl-kpi-label">Filled FTE</div>
              <div className="mpl-kpi-value">{asOfTotals ? asOfTotals.filled.toFixed(1) : "—"}</div>
            </div>
            <div className="mpl-kpi-card">
              <div className="mpl-kpi-label">Planned FTE (open reqs)</div>
              <div className="mpl-kpi-value">{asOfTotals ? asOfTotals.planned.toFixed(1) : "—"}</div>
            </div>
            <div className="mpl-kpi-card">
              <div className="mpl-kpi-label">Monthly people cost</div>
              <div className="mpl-kpi-value">{asOfTotals ? money(asOfTotals.peopleCost) : "—"}</div>
            </div>
            <div className="mpl-kpi-card">
              <div className="mpl-kpi-label">Productive quota ARR</div>
              <div className="mpl-kpi-value">{asOfTotals ? money(asOfTotals.quota) : "—"}</div>
            </div>
          </section>

          {validation?.checks?.length ? (
            <WorkforceValidationStrip checks={validation.checks as WorkforceValidationCheck[]} section="all" title="Workforce validation checks" />
          ) : null}

          <div className="mpl-panel mpl-table-wrap">
            <div className="mpl-section-label">Period summary (company totals)</div>
            {periodTotals.length ? (
              <table className="mpl-table">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>Scenario</th>
                    <th className="mpl-num">Filled FTE</th>
                    <th className="mpl-num">Planned FTE</th>
                    <th className="mpl-num">Total FTE</th>
                    <th className="mpl-num">Planned starts</th>
                    <th className="mpl-num">People cost / mo</th>
                    <th className="mpl-num">Productive quota ARR</th>
                  </tr>
                </thead>
                <tbody>
                  {periodTotals.map(([period, totals]) => (
                    <tr key={period} style={period === asOfKey ? { background: "var(--surface-muted, #f8fafc)" } : undefined}>
                      <td>{period}</td>
                      <td>{scenarioForPeriod(period, scenario)}</td>
                      <td className="mpl-num">{totals.filled.toFixed(1)}</td>
                      <td className="mpl-num">{totals.planned.toFixed(1)}</td>
                      <td className="mpl-num">{totals.total.toFixed(1)}</td>
                      <td className="mpl-num">{totals.plannedStarts.toFixed(1)}</td>
                      <td className="mpl-num">{money(totals.peopleCost)}</td>
                      <td className="mpl-num">{money(totals.quota)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="mpl-muted" style={{ margin: 0 }}>
                No workforce period rows for this range. Upload workforce CSVs, then recompute.
              </p>
            )}
          </div>

          <div className="mpl-panel mpl-table-wrap" style={{ marginTop: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 8 }}>
              <div className="mpl-section-label" style={{ margin: 0 }}>
                Department detail{" "}
                {showAllMonths
                  ? "(monthly)"
                  : `(full year · beginning ${rangeStartKey} · ending ${rangeEndKey})`}
              </div>
              <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
                <input type="checkbox" checked={showAllMonths} onChange={(e) => setShowAllMonths(e.target.checked)} />
                Show monthly detail
              </label>
            </div>
            {showAllMonths ? (
              departmentMonthlyRows.length ? (
                <table className="mpl-table mpl-workforce-table">
                  <WorkforceDepartmentMonthlyColgroup />
                  <thead>
                    <tr>
                      <th>Period</th>
                      <th>Department</th>
                      <th className="mpl-num">Beginning</th>
                      <th className="mpl-num">New hires</th>
                      <th className="mpl-num">Attrition</th>
                      <th className="mpl-num">Ending FTE</th>
                      <th className="mpl-num">Open reqs</th>
                      <th className="mpl-num">Total FTE</th>
                      <th className="mpl-num">People cost / mo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {departmentMonthlyRows.map((row) => (
                      <tr key={`${row.period}-${row.department}`}>
                        <td>{normalizePeriodKey(row.period)}</td>
                        <td>{row.department}</td>
                        <td className="mpl-num">{num(row.headcount_beginning_fte).toFixed(1)}</td>
                        <td className="mpl-num">{num(row.new_hires_fte).toFixed(1)}</td>
                        <td className="mpl-num">{num(row.attrition_fte).toFixed(1)}</td>
                        <td className="mpl-num">
                          {num(row.headcount_ending_fte || row.filled_headcount).toFixed(1)}
                        </td>
                        <td className="mpl-num">{num(row.planned_hire_headcount).toFixed(1)}</td>
                        <td className="mpl-num">{num(row.total_headcount_fte).toFixed(1)}</td>
                        <td className="mpl-num">{money(row.total_people_cost_monthly)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="mpl-muted" style={{ margin: 0 }}>
                  Upload workforce employees, requisitions, comp bands, and allocation rules to derive payroll.
                </p>
              )
            ) : departmentAnnualRows.length ? (
              <table className="mpl-table mpl-workforce-table">
                <WorkforceDepartmentAnnualColgroup />
                <thead>
                  <tr>
                    <th>Department</th>
                    <th className="mpl-num">Beginning ({rangeStartKey})</th>
                    <th className="mpl-num">New hires (YTD)</th>
                    <th className="mpl-num">Attrition (YTD)</th>
                    <th className="mpl-num">Ending FTE ({rangeEndKey})</th>
                    <th className="mpl-num">Open reqs ({rangeEndKey})</th>
                    <th className="mpl-num">Total FTE ({rangeEndKey})</th>
                    <th className="mpl-num">People cost / mo ({rangeEndKey})</th>
                  </tr>
                </thead>
                <tbody>
                  {departmentAnnualRows.map((row) => (
                    <tr key={row.department}>
                      <td>{row.department}</td>
                      <td className="mpl-num">{row.beginning.toFixed(1)}</td>
                      <td className="mpl-num">{row.newHires.toFixed(1)}</td>
                      <td className="mpl-num">{row.attrition.toFixed(1)}</td>
                      <td className="mpl-num">{row.ending.toFixed(1)}</td>
                      <td className="mpl-num">{row.openReqs.toFixed(1)}</td>
                      <td className="mpl-num">{row.totalFte.toFixed(1)}</td>
                      <td className="mpl-num">{money(row.peopleCost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="mpl-muted" style={{ margin: 0 }}>
                Upload Actual and Forecast headcount plan CSVs for the selected range.
              </p>
            )}
          </div>

          <p className="mpl-muted" style={{ marginTop: 10, fontSize: 12 }}>
            Department detail rolls up the selected range: beginning FTE from the first month, ending/open
            reqs/total from the last month, and new hires and attrition summed across all months in range.
            Combined view uses Actual through May 2026 and Forecast thereafter. Sources:{" "}
            {plan.data_sources.join(", ")} · scenario {plan.scenario}
          </p>
        </>
      )}
    </>
  );
}
