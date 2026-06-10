"use client";

import { Fragment, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";

import { fetchJson } from "../lib/fetchJson";
import { getApiBase, getWorkforceApiBase } from "../lib/apiBase";
import {
  categoryCellStyle,
  categoryHeaderStyle,
  dashboardTableStyle,
  formatDashboardPeriodHeader,
  normalizeDashboardPeriod,
  periodCellStyle,
  periodHeaderStyle,
} from "../lib/dashboardPeriodColumns";
import {
  FinancialStatementTable,
  type FinancialStatementsSummary,
  statementPeriodParams,
} from "./FinancialStatementTable";
import { ReportingExportToolbar } from "./ReportingExportToolbar";
import { CfoOperatingShell } from "./cfo/CfoOperatingShell";
import { ExecutiveAiCommentary } from "./cfo/ExecutiveAiCommentary";
import { ExecutiveKpiStrip } from "./cfo/ExecutiveKpiStrip";
import { OperatingSectionHeader } from "./cfo/OperatingSectionHeader";
import { deriveExecutiveKpis } from "../lib/deriveExecutiveKpis";
import { normalizePeriodKey, scenarioForPeriod } from "../lib/periodScenario";
import { ManagementPnLDashboard } from "./management/ManagementPnLDashboard";
import { WorkforcePlanningDashboard } from "./workforce/WorkforcePlanningDashboard";
import {
  WorkforceValidationStrip,
  type WorkforceValidationResponse,
} from "./workforce/WorkforceValidationStrip";

const defaultOrgId = "8571e520-0687-4516-bdee-379f37c58c1f";

type Org = { id: string; name: string };

type ValidationCheck = {
  scenario: string;
  period: string;
  validation_name: string;
  status: "pass" | "warning" | "fail";
  variance?: string | number | null;
  source_tables_used: string[];
};

function asValidationChecks(
  checks: Array<{
    scenario: string;
    period: string;
    validation_name: string;
    status: "pass" | "warning" | "fail";
    variance?: string | number | null;
    source_tables_used?: string[];
  }>,
): ValidationCheck[] {
  return checks.map((c) => ({
    scenario: c.scenario,
    period: c.period,
    validation_name: c.validation_name,
    status: c.status,
    variance: c.variance,
    source_tables_used: c.source_tables_used ?? [],
  }));
}

type WaterfallSummaryRow = {
  scenario: string;
  period: string;
  waterfall_name: string;
  waterfall_type: string;
  line_item: string;
  line_item_order: number;
  amount: string | number;
  source_table: string;
  detail_count: number;
};

type AttributionRow = {
  scenario: string;
  period: string;
  waterfall_type: string;
  customer_id?: string | null;
  customer_name?: string | null;
  opportunity_id?: string | null;
  opportunity_name?: string | null;
  owner?: string | null;
  region?: string | null;
  segment?: string | null;
  marketing_channel?: string | null;
  stage?: string | null;
  probability?: string | number;
  close_date?: string | null;
  contract_start_date?: string | null;
  billing_cadence?: string | null;
  payment_terms?: string | null;
  amount: string | number;
  arr_impact: string | number;
  mrr_impact: string | number;
  revenue_impact: string | number;
  cash_impact: string | number;
  source_table: string;
  raw: Record<string, string>;
};

type WaterfallResponse = {
  waterfall_name: string;
  rows: WaterfallSummaryRow[];
  attribution: AttributionRow[];
  validation: ValidationCheck[];
  commentary_prompts: Record<string, string>;
};

type OpportunityRow = {
  scenario: string;
  period: string;
  stage?: string | null;
  marketing_channel?: string | null;
  opportunity_count: number;
  amount_arr: string | number;
  weighted_arr: string | number;
  source_table: string;
};

type OpportunityResponse = {
  rows: OpportunityRow[];
  attribution: AttributionRow[];
};

type MarketingRow = {
  period: string;
  scenario: string;
  marketing_channel?: string | null;
  marketing_spend: string | number;
  mqls: string | number;
  sqls: string | number;
  sals: string | number;
  opportunities_created: string | number;
  pipeline_arr_created: string | number;
  closed_won_arr: string | number;
  closed_lost_arr: string | number;
  slipped_pipeline_arr: string | number;
  ending_pipeline_arr: string | number;
  cost_per_sql: string | number;
  pipeline_per_dollar_spend: string | number;
  marketing_cac_proxy: string | number;
  win_rate_on_pipeline_created: string | number;
};

type MarketingResponse = {
  rows: MarketingRow[];
  validation: ValidationCheck[];
};

type ActualBudgetForecastResponse = {
  actual: MarketingRow[];
  budget: MarketingRow[];
  forecast: MarketingRow[];
  combined: MarketingRow[];
};

type ExecutiveFlowResponse = {
  as_of_period?: string;
  marketing_summary: { rows?: MarketingRow[] };
  marketing_channel_performance?: { rows?: MarketingRow[] };
  marketing_channel_actual?: { rows?: MarketingRow[] };
  marketing_channel_budget?: { rows?: MarketingRow[] };
  marketing_abf?: ActualBudgetForecastResponse;
  waterfalls: Record<string, WaterfallResponse>;
  opportunities: Record<string, OpportunityResponse>;
  validation: ValidationCheck[];
  workforce_validation?: WorkforceValidationResponse | null;
  commentary_prompts: Record<string, string>;
};

const commentaryPrompts = {
  what_changed: "What changed?",
  variance_drivers: "What drove the variance?",
  leadership_attention: "What should leadership pay attention to?",
  movement_drivers: "Which customers/channels drove the movement?",
};

const palette = ["#2563eb", "#16a34a", "#f97316", "#7c3aed", "#0891b2", "#dc2626", "#4f46e5", "#65a30d"];

/** Fixed GTM channel colors (aligned with board reference — avoids index collisions). */
const MARKETING_CHANNEL_COLORS: Record<string, string> = {
  "Paid Search": "#888780",
  "Paid Social": "#5f5e5a",
  Webinar: "#0f6e56",
  Direct: "#3b6d11",
  Partner: "#1d9e75",
  "Organic Search": "#185fa5",
  Referral: "#534ab7",
  Outbound: "#ba7517",
  "Customer Success": "#be185d",
  "Content Syndication": "#b4b2a9",
  "Field Event": "#a32d2d",
};

function marketingChannelColor(channel: string, fallbackIndex: number) {
  return MARKETING_CHANNEL_COLORS[channel] ?? palette[fallbackIndex % palette.length]!;
}

const OPERATING_SECTIONS = [
  { id: "executive", label: "Executive Summary" },
  { id: "arr", label: "ARR Waterfall" },
  { id: "revenue", label: "Revenue" },
  { id: "management-pl", label: "Management P&L" },
  { id: "workforce", label: "Workforce" },
  { id: "gtm", label: "GTM / Marketing" },
  { id: "pipeline", label: "Pipeline" },
  { id: "cash", label: "Cash Forecast" },
  { id: "decisions", label: "Risks & Validation" },
] as const;

type OperatingSectionId = (typeof OPERATING_SECTIONS)[number]["id"];

function n(value: string | number | null | undefined) {
  return Number(value ?? 0);
}

function money(value: string | number | null | undefined) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n(value));
}

function count(value: string | number | null | undefined) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n(value));
}

function multiple(value: string | number | null | undefined) {
  return `${n(value).toFixed(2)}x`;
}

function monthRange(startPeriod: string, endPeriod: string) {
  const [startYear, startMonth] = startPeriod.split("-").map(Number);
  const [endYear, endMonth] = endPeriod.split("-").map(Number);
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

function filterMarketingRowsForDisplay(
  rows: MarketingRow[],
  selectedScenario: string,
  periods: string[],
  asOfPeriod: string
) {
  const periodSet = new Set(periods);
  return rows.filter((row) => {
    if (!periodSet.has(row.period)) return false;
    if (selectedScenario === "Combined") {
      return row.scenario === scenarioForPeriod(row.period, selectedScenario, asOfPeriod);
    }
    return row.scenario === selectedScenario;
  });
}

/** Map View control to API period range (marketing routes use start/end only). */
function resolveQueryPeriodRange(periodView: string, startPeriod: string, endPeriod: string) {
  const year = endPeriod.slice(0, 4);
  if (periodView === "ytd") {
    return { start: `${year}-01`, end: endPeriod };
  }
  if (periodView === "fiscal_year") {
    return { start: `${year}-01`, end: `${year}-12` };
  }
  if (periodView.startsWith("Q")) {
    const q = Number(periodView.replace("Q", ""));
    const startMonth = (q - 1) * 3 + 1;
    const endMonth = startMonth + 2;
    return {
      start: `${year}-${String(startMonth).padStart(2, "0")}`,
      end: `${year}-${String(endMonth).padStart(2, "0")}`,
    };
  }
  return { start: startPeriod, end: endPeriod };
}

const ATTRIBUTION_ROW_LIMIT = 250;

const PIPELINE_DRILLDOWN_TYPES = new Set(["pipeline_created", "closed_won", "closed_lost", "slipped_pipeline"]);

type PipelineDrilldownResponse = {
  organization_id: string;
  scenario: string;
  source_scenario: string;
  period: string;
  waterfall_type: string;
  line_item: string;
  opportunities: AttributionRow[];
  opportunity_count: number;
  total_arr: string | number;
  signed_total: string | number;
  expected_amount?: string | number | null;
  drilldown_available: boolean;
  message?: string | null;
  validation: ValidationCheck[];
  source_tables: string[];
};

type SelectedPipelineCell = {
  period: string;
  waterfall_type: string;
  line_item: string;
  scenario: string;
  amount: number;
  detail_count: number;
};

const CASH_DRILLDOWN_TYPES = new Set([
  "cash_collections",
  "payroll_cash_out",
  "commission_cash_out",
  "vendor_cash_out",
  "tax_cash_out",
  "capex",
  "financing",
]);

type CashFlowDrilldownLine = {
  account_number?: string | null;
  account_name?: string | null;
  account_group?: string | null;
  department?: string | null;
  vendor_name?: string | null;
  amount: string | number;
  source_table: string;
  detail_type: string;
  notes?: string | null;
};

type CashFlowDrilldownResponse = {
  organization_id: string;
  scenario: string;
  source_scenario: string;
  period: string;
  waterfall_type: string;
  line_item: string;
  lines: CashFlowDrilldownLine[];
  line_count: number;
  signed_total: string | number;
  expected_amount?: string | number | null;
  drilldown_available: boolean;
  message?: string | null;
  validation: ValidationCheck[];
  source_tables: string[];
};

type SelectedCashCell = {
  period: string;
  waterfall_type: string;
  line_item: string;
  scenario: string;
  amount: number;
  detail_count: number;
};

export function ExecutiveFlowDashboard({ enabled = true }: { enabled?: boolean }) {
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [orgId, setOrgId] = useState(defaultOrgId);
  const [scenario, setScenario] = useState("Combined");
  const [startPeriod, setStartPeriod] = useState("2026-01");
  const [endPeriod, setEndPeriod] = useState("2026-12");
  const [asOfPeriod, setAsOfPeriod] = useState("");
  const [periodView, setPeriodView] = useState("monthly");
  const [marketingChannel, setMarketingChannel] = useState("");
  const [data, setData] = useState<ExecutiveFlowResponse | null>(null);
  const [statements, setStatements] = useState<FinancialStatementsSummary | null>(null);
  const [statementsError, setStatementsError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<OperatingSectionId>("executive");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${getApiBase()}/api/v1/organizations/?_=${Date.now()}`, { cache: "no-store" });
        if (!res.ok) return;
        const rows = (await res.json()) as Org[];
        if (!cancelled) setOrgs(rows);
      } catch {
        // Manual org fallback.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const load = async () => {
    if (!enabled || !orgId) return;
    setBusy(true);
    setError(null);
    setStatementsError(null);
    try {
      const { start: queryStart, end: queryEnd } = resolveQueryPeriodRange(
        periodView,
        startPeriod,
        endPeriod
      );
      const params = new URLSearchParams({
        organization_id: orgId,
        scenario,
        start_period: queryStart,
        end_period: queryEnd,
        _: String(Date.now()),
      });
      const closeMonth = normalizePeriodKey(asOfPeriod || endPeriod);
      if (scenario === "Combined" || asOfPeriod.trim()) {
        params.set("as_of_period", closeMonth);
      }
      if (marketingChannel) params.set("marketing_channel", marketingChannel);
      if (periodView === "fiscal_year") params.set("fiscal_year", startPeriod.slice(0, 4));
      if (periodView.startsWith("Q")) {
        params.set("quarter", periodView);
        params.set("fiscal_year", startPeriod.slice(0, 4));
      }
      const query = params.toString();
      const fetchSection = <T,>(path: string) =>
        fetchJson<T>(`${getApiBase()}${path}?${query}`);

      // Load smaller dashboard sections independently instead of one very large
      // payload; this keeps expandable attribution responsive in the browser.
      const fetchWithScenario = <T,>(path: string, scenarioOverride: string) => {
        const p = new URLSearchParams(params);
        p.set("scenario", scenarioOverride);
        return fetchJson<T>(`${getApiBase()}${path}?${p.toString()}`);
      };

      const requests = {
        marketing: fetchSection<MarketingResponse>("/api/v1/marketing/performance-summary"),
        marketing_channels: fetchSection<MarketingResponse>("/api/v1/marketing/channel-performance"),
        marketing_channels_actual: fetchWithScenario<MarketingResponse>(
          "/api/v1/marketing/channel-performance",
          "Actual"
        ),
        marketing_channels_budget: fetchWithScenario<MarketingResponse>(
          "/api/v1/marketing/channel-performance",
          "Budget"
        ),
        marketing_abf: fetchSection<ActualBudgetForecastResponse>("/api/v1/marketing/actual-budget-forecast"),
        closed_by_month: fetchSection<OpportunityResponse>("/api/v1/opportunities/closed-by-month"),
        pipeline: fetchSection<WaterfallResponse>("/api/v1/waterfalls/pipeline"),
        arr: fetchSection<WaterfallResponse>("/api/v1/waterfalls/arr"),
        deferred_revenue: fetchSection<WaterfallResponse>("/api/v1/waterfalls/deferred-revenue"),
        cash_flow: fetchSection<WaterfallResponse>("/api/v1/waterfalls/cash-flow"),
        stage_summary: fetchSection<OpportunityResponse>("/api/v1/opportunities/stage-summary"),
      };
      const statementDates = statementPeriodParams(queryStart, queryEnd);
      const statementParams = new URLSearchParams({
        organization_id: orgId,
        scenario,
        start_period: statementDates.start_period,
        end_period: statementDates.end_period,
        _: String(Date.now()),
      });
      if (scenario === "Combined" || asOfPeriod.trim()) {
        statementParams.set("as_of_period", `${closeMonth}-01`);
      }
      const workforceDates = statementPeriodParams(queryStart, queryEnd);
      const workforceValidationFetches =
        scenario === "Combined"
          ? (["Actual", "Forecast"] as const).map((slice) => {
              const params = new URLSearchParams({
                organization_id: orgId,
                scenario: slice,
                start_period: workforceDates.start_period,
                end_period: workforceDates.end_period,
                _: String(Date.now()),
              });
              return fetchJson<WorkforceValidationResponse>(
                `${getWorkforceApiBase()}/api/v1/workforce/validation?${params}`
              );
            })
          : [
              fetchJson<WorkforceValidationResponse>(
                `${getWorkforceApiBase()}/api/v1/workforce/validation?${new URLSearchParams({
                  organization_id: orgId,
                  scenario: scenario === "Budget" ? "Budget" : scenario === "Actual" ? "Actual" : "Forecast",
                  start_period: workforceDates.start_period,
                  end_period: workforceDates.end_period,
                  _: String(Date.now()),
                })}`
              ),
            ];

      const entries = await Promise.all(
        [
          ...Object.entries(requests).map(async ([key, promise]) => {
            try {
              return [key, { ok: true, value: await promise }] as const;
            } catch (error) {
              const raw = error instanceof Error ? error.message : String(error);
              const hint =
                raw.toLowerCase().includes("failed to fetch")
                  ? `${raw} (check backend at ${getApiBase()}, CORS for ${typeof window !== "undefined" ? window.location.origin : "your dev port"}, and uvicorn logs for this section's API path)`
                  : raw;
              return [key, { ok: false, error: hint }] as const;
            }
          }),
          (async () => {
            try {
              const value = await fetchJson<FinancialStatementsSummary>(
                `${getApiBase()}/api/v1/financial-statements/summary?${statementParams}`
              );
              return ["financial_statements", { ok: true, value }] as const;
            } catch (error) {
              const raw = error instanceof Error ? error.message : String(error);
              return ["financial_statements", { ok: false, error: raw }] as const;
            }
          })(),
          (async () => {
            try {
              const slices = await Promise.all(workforceValidationFetches);
              const checks = slices.flatMap((slice) => slice.checks);
              const failed_count = checks.filter((c) => c.status === "fail").length;
              const warning_count = checks.filter((c) => c.status === "warning").length;
              const passed_count = checks.filter((c) => c.status === "pass").length;
              const status = failed_count ? "fail" : warning_count ? "warning" : "pass";
              const value: WorkforceValidationResponse = {
                ...slices[slices.length - 1],
                scenario: scenario === "Combined" ? "Combined" : slices[0].scenario,
                checks,
                failed_count,
                warning_count,
                passed_count,
                status,
              };
              return ["workforce_validation", { ok: true, value }] as const;
            } catch (error) {
              const raw = error instanceof Error ? error.message : String(error);
              return ["workforce_validation", { ok: false, error: raw }] as const;
            }
          })(),
        ]
      );
      const results = Object.fromEntries(entries) as Record<string, { ok: true; value: unknown } | { ok: false; error: string }>;
      const sectionErrors = Object.entries(results)
        .filter(([, result]) => !result.ok)
        .map(([key, result]) => `${key}: ${(result as { ok: false; error: string }).error}`);
      const fallbackWaterfall = (name: string): WaterfallResponse => ({
        waterfall_name: name,
        rows: [],
        attribution: [],
        validation: [],
        commentary_prompts: commentaryPrompts,
      });
      const fallbackOpportunity = (): OpportunityResponse => ({ rows: [], attribution: [] });

      const marketing = (results.marketing.ok ? results.marketing.value : { rows: [], validation: [] }) as MarketingResponse;
      const marketingChannels = (results.marketing_channels.ok ? results.marketing_channels.value : { rows: [], validation: [] }) as MarketingResponse;
      const marketingChannelsActual = (
        results.marketing_channels_actual?.ok ? results.marketing_channels_actual.value : { rows: [], validation: [] }
      ) as MarketingResponse;
      const marketingChannelsBudget = (
        results.marketing_channels_budget?.ok ? results.marketing_channels_budget.value : { rows: [], validation: [] }
      ) as MarketingResponse;
      const marketingAbf = (
        results.marketing_abf?.ok
          ? results.marketing_abf.value
          : { actual: [], budget: [], forecast: [], combined: [] }
      ) as ActualBudgetForecastResponse;
      const closedByMonth = (results.closed_by_month?.ok ? results.closed_by_month.value : { rows: [], attribution: [] }) as OpportunityResponse;
      const pipeline = (results.pipeline.ok ? results.pipeline.value : fallbackWaterfall("pipeline")) as WaterfallResponse;
      const arr = (results.arr.ok ? results.arr.value : fallbackWaterfall("arr")) as WaterfallResponse;
      const deferredRevenue = (results.deferred_revenue.ok ? results.deferred_revenue.value : fallbackWaterfall("deferred_revenue")) as WaterfallResponse;
      const cashFlow = (results.cash_flow.ok ? results.cash_flow.value : fallbackWaterfall("cash_flow")) as WaterfallResponse;
      const stageSummary = (results.stage_summary.ok ? results.stage_summary.value : fallbackOpportunity()) as OpportunityResponse;
      const statementResult = results.financial_statements;
      const workforceValidation = (
        results.workforce_validation?.ok
          ? (results.workforce_validation.value as WorkforceValidationResponse)
          : null
      );
      if (statementResult?.ok) {
        setStatements(statementResult.value as FinancialStatementsSummary);
        setStatementsError(null);
      } else {
        setStatements(null);
        setStatementsError(
          statementResult && !statementResult.ok
            ? (statementResult as { ok: false; error: string }).error
            : "Financial statements did not load."
        );
      }

      if (
        sectionErrors.length >= 5 &&
        results.marketing.ok
      ) {
        const executive = await fetchSection<ExecutiveFlowResponse>("/api/v1/dashboard/executive-flow");
        setData(executive);
        if (executive.as_of_period) {
          setAsOfPeriod(executive.as_of_period);
        }
        setError(null);
        setLastRefresh(new Date().toLocaleString());
        return;
      }

      setData({
        as_of_period: closeMonth,
        marketing_summary: { rows: marketing.rows },
        marketing_channel_performance: { rows: marketingChannels.rows },
        marketing_channel_actual: { rows: marketingChannelsActual.rows },
        marketing_channel_budget: { rows: marketingChannelsBudget.rows },
        marketing_abf: marketingAbf,
        waterfalls: {
          pipeline,
          arr,
          deferred_revenue: deferredRevenue,
          cash_flow: cashFlow,
        },
        opportunities: {
          stage_summary: stageSummary,
          closed_by_month: closedByMonth,
          remaining_pipeline: fallbackOpportunity(),
        },
        validation: [
          ...asValidationChecks(marketing.validation ?? []),
          ...asValidationChecks(marketingChannels.validation ?? []),
          ...asValidationChecks(pipeline.validation ?? []),
          ...asValidationChecks(arr.validation ?? []),
          ...asValidationChecks(deferredRevenue.validation ?? []),
          ...asValidationChecks(cashFlow.validation ?? []),
          ...asValidationChecks(
            statementResult?.ok ? (statementResult.value as FinancialStatementsSummary).validation : [],
          ),
          ...asValidationChecks(workforceValidation?.checks ?? []),
        ],
        workforce_validation: workforceValidation,
        commentary_prompts: commentaryPrompts,
      });
      setError(sectionErrors.length ? `Some Executive Flow sections did not load:\n${sectionErrors.join("\n")}` : null);
      setLastRefresh(new Date().toLocaleString());
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setError(message.toLowerCase().includes("failed to fetch")
        ? `One Executive Flow section could not fetch from ${getApiBase()}. Financial Statements may still work; check the backend terminal for the specific dashboard endpoint error.`
        : message);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!enabled) return;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, periodView, startPeriod, endPeriod, scenario, orgId, marketingChannel, asOfPeriod]);

  const queryPeriodRange = useMemo(
    () => resolveQueryPeriodRange(periodView, startPeriod, endPeriod),
    [periodView, startPeriod, endPeriod]
  );
  const queryPeriods = useMemo(
    () => monthRange(queryPeriodRange.start, queryPeriodRange.end),
    [queryPeriodRange]
  );
  const effectiveAsOf = normalizePeriodKey(asOfPeriod || data?.as_of_period || endPeriod);

  const dashboardPeriods = queryPeriods;
  const marketingRows = useMemo(
    () => filterMarketingRowsForDisplay(data?.marketing_summary.rows ?? [], scenario, queryPeriods, effectiveAsOf),
    [data?.marketing_summary.rows, scenario, queryPeriods, effectiveAsOf]
  );
  const marketingChannelRows = useMemo(
    () =>
      filterMarketingRowsForDisplay(
        data?.marketing_channel_performance?.rows ?? [],
        scenario,
        queryPeriods,
        effectiveAsOf
      ),
    [data?.marketing_channel_performance?.rows, scenario, queryPeriods, effectiveAsOf]
  );
  const marketingChannelActualRows = useMemo(
    () =>
      filterMarketingRowsForDisplay(
        data?.marketing_channel_actual?.rows ?? [],
        "Actual",
        queryPeriods,
        effectiveAsOf
      ),
    [data?.marketing_channel_actual?.rows, queryPeriods, effectiveAsOf]
  );
  const marketingChannelBudgetRows = useMemo(
    () =>
      filterMarketingRowsForDisplay(
        data?.marketing_channel_budget?.rows ?? [],
        "Budget",
        queryPeriods,
        effectiveAsOf
      ),
    [data?.marketing_channel_budget?.rows, queryPeriods, effectiveAsOf]
  );
  const warnings = data?.validation.filter((row) => row.status !== "pass") ?? [];
  const closePeriod = effectiveAsOf;

  const validationStatus = useMemo((): "ok" | "warn" | "fail" | "unknown" => {
    if (!data) return "unknown";
    if (warnings.some((w) => w.status === "fail")) return "fail";
    if (warnings.length) return "warn";
    return "ok";
  }, [data, warnings]);

  const executiveKpis = useMemo(() => {
    if (!data) return [];
    const incomeRev = statements?.income_statement.rows.find(
      (r) =>
        r.period === closePeriod &&
        /total.*revenue|^revenue$/i.test(r.line_item.trim()) &&
        r.scenario === scenarioForPeriod(closePeriod, scenario, effectiveAsOf)
    );
    return deriveExecutiveKpis({
      closePeriod,
      arrRows: data.waterfalls.arr?.rows,
      cashRows: data.waterfalls.cash_flow?.rows,
      marketingTotals: marketingRows.length
        ? {
            pipeline_arr_created: marketingRows.reduce((a, r) => a + n(r.pipeline_arr_created), 0),
            closed_won_arr: marketingRows.reduce((a, r) => a + n(r.closed_won_arr), 0),
            pipeline_per_dollar_spend: n(marketingRows.at(-1)?.pipeline_per_dollar_spend),
          }
        : undefined,
      incomeRevenue: incomeRev ? n(incomeRev.amount) : null,
      validationIssueCount: warnings.length,
    });
  }, [data, statements, closePeriod, scenario, marketingRows, warnings.length]);

  const periodLabel = `${queryPeriodRange.start.replace("-", " · ")} – ${queryPeriodRange.end.replace("-", " · ")} · ${scenario} · ${periodView === "ytd" ? "YTD" : periodView} operating review`;

  const controls = (
    <>
      <label>
        Organization
        <select value={orgId} onChange={(e) => setOrgId(e.target.value)}>
          <option value={orgId}>{orgs.find((o) => o.id === orgId)?.name ?? orgId}</option>
          {orgs.filter((o) => o.id !== orgId).map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Scenario
        <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
          <option>Combined</option>
          <option>Actual</option>
          <option>Budget</option>
          <option>Forecast</option>
        </select>
      </label>
      <label>
        View
        <select value={periodView} onChange={(e) => setPeriodView(e.target.value)}>
          <option value="monthly">Monthly</option>
          <option>Q1</option>
          <option>Q2</option>
          <option>Q3</option>
          <option>Q4</option>
          <option value="fiscal_year">Fiscal Year</option>
          <option value="ytd">YTD</option>
        </select>
      </label>
      <label>
        Close month (Combined)
        <input
          type="month"
          value={asOfPeriod || effectiveAsOf}
          onChange={(e) => setAsOfPeriod(e.target.value)}
          title="Last closed Actual month — open months use Forecast"
        />
      </label>
      <label>
        Start
        <input value={startPeriod} onChange={(e) => setStartPeriod(e.target.value)} />
      </label>
      <label>
        End
        <input value={endPeriod} onChange={(e) => setEndPeriod(e.target.value)} />
      </label>
      <label>
        Channel
        <input
          value={marketingChannel}
          onChange={(e) => setMarketingChannel(e.target.value)}
          placeholder="All"
        />
      </label>
    </>
  );

  return (
    <CfoOperatingShell
      periodLabel={periodLabel}
      sections={[...OPERATING_SECTIONS]}
      activeSection={activeSection}
      onSectionChange={(id) => setActiveSection(id as OperatingSectionId)}
      validationStatus={validationStatus}
      validationDetail={
        warnings.length
          ? `${warnings.length} check(s) — ${warnings.filter((w) => w.status === "fail").length} failed`
          : undefined
      }
      onRefresh={load}
      busy={busy}
      controls={controls}
      footer={
        orgId ? (
          <ReportingExportToolbar
            variant="footer"
            organizationId={orgId}
            scenario={scenario}
            startPeriod={startPeriod}
            endPeriod={endPeriod}
            asOfPeriod={closePeriod}
            marketingChannel={marketingChannel}
            disabled={!enabled}
          />
        ) : undefined
      }
    >
      {lastRefresh && (
        <p className="os-slide-sub" style={{ marginBottom: 12 }}>
          Last refreshed: {lastRefresh}
        </p>
      )}
      {!enabled && (
        <p style={{ color: "var(--muted)" }}>Waiting for API health check before loading operating data…</p>
      )}
      {error && <pre style={errorBox}>{error}</pre>}
      {!data && enabled && !error && (
        <p style={{ color: "var(--muted)" }}>{busy ? "Loading operating intelligence…" : "Refresh to load data."}</p>
      )}

      {data && activeSection === "executive" && (
        <>
          <OperatingSectionHeader
            title="Executive Operating Summary"
            subtitle={`${startPeriod} – ${endPeriod} · ${scenario} · Guide focus before drilldown`}
          />
          <ExecutiveKpiStrip kpis={executiveKpis} />
          <ExecutiveAiCommentary
            organizationId={orgId}
            scenario={scenario}
            startPeriod={startPeriod}
            endPeriod={endPeriod}
            asOfPeriod={closePeriod}
            marketingChannel={marketingChannel}
            disabled={!enabled}
          />
          {orgId && (
            <ReportingExportToolbar
              variant="featured"
              organizationId={orgId}
              scenario={scenario}
              startPeriod={startPeriod}
              endPeriod={endPeriod}
              asOfPeriod={closePeriod}
              marketingChannel={marketingChannel}
              disabled={!enabled}
            />
          )}
        </>
      )}

      {data && activeSection === "gtm" && (
        <>
          <OperatingSectionHeader
            title="GTM & Marketing Channel Efficiency"
            subtitle={`${queryPeriodRange.start} – ${queryPeriodRange.end} · ${scenario} · per-channel YTD rollups (compare to board channel ranking)`}
          />
          <GtmPerformanceSection
            totalRows={marketingRows}
            channelRows={marketingChannelRows}
            closedByMonth={data.opportunities.closed_by_month?.rows ?? []}
          />
          <ChannelDrilldownGrid
            title="Channel Drilldowns"
            actualRows={marketingChannelActualRows}
            budgetRows={marketingChannelBudgetRows}
          />
        </>
      )}

      {data && activeSection === "pipeline" && (
        <>
          <OperatingSectionHeader title="Pipeline & Bookings" subtitle="Waterfall movement · stage summary · CRM drilldown" />
          <PipelineWaterfallTable
            title="Pipeline waterfall"
            response={data.waterfalls.pipeline}
            selectedScenario={scenario}
            asOfPeriod={closePeriod}
            organizationId={orgId}
            marketingChannel={marketingChannel}
            periodsOverride={dashboardPeriods}
          />
          <OpportunitySummary
            title="Opportunities by stage"
            response={data.opportunities.stage_summary}
            selectedScenario={scenario}
            asOfPeriod={closePeriod}
            periodsOverride={dashboardPeriods}
          />
        </>
      )}

      {data && activeSection === "arr" && (
        <>
          <OperatingSectionHeader title="ARR / MRR Waterfall" subtitle="Net new components · retention context" />
          <ExpandableWaterfallTable
            title="MRR / ARR waterfall"
            response={data.waterfalls.arr}
            selectedScenario={scenario}
            asOfPeriod={closePeriod}
            periodsOverride={dashboardPeriods}
          />
        </>
      )}

      {data && activeSection === "revenue" && (
        <>
          <OperatingSectionHeader
            title="Revenue Performance"
            subtitle="GAAP revenue bridge · billings forecast · subscription economics"
          />
          <ExpandableWaterfallTable
            title="GAAP revenue forecast"
            response={data.waterfalls.deferred_revenue}
            filterTypes={[
              "deferred_revenue_recognized",
              "renewal_revenue",
              "new_business_revenue",
              "expansion_revenue",
              "reactivation_revenue",
              "total_gaap_revenue",
            ]}
            periodsOverride={dashboardPeriods}
            selectedScenario={scenario}
            asOfPeriod={closePeriod}
            expandable={false}
          />
          <p style={{ color: "var(--muted)", fontSize: 12, margin: "8px 0 0" }}>
            Actual months tie to income statement; forecast months use MRR waterfall bookings.
          </p>
          <ExpandableWaterfallTable
            title="Billings forecast"
            response={data.waterfalls.deferred_revenue}
            filterTypes={["new_billings"]}
            periodsOverride={dashboardPeriods}
            selectedScenario={scenario}
            asOfPeriod={closePeriod}
          />
        </>
      )}

      {data && activeSection === "management-pl" && orgId && (
        <ManagementPnLDashboard
          orgId={orgId}
          queryStart={queryPeriodRange.start}
          queryEnd={queryPeriodRange.end}
          asOfPeriod={closePeriod}
          periodView={periodView}
          scenario={scenario}
          enabled={enabled}
          workforceValidation={data.workforce_validation?.checks ?? []}
        />
      )}

      {data && activeSection === "workforce" && orgId && (
        <WorkforcePlanningDashboard
          orgId={orgId}
          queryStart={queryPeriodRange.start}
          queryEnd={queryPeriodRange.end}
          asOfPeriod={closePeriod}
          scenario={scenario}
          enabled={enabled}
          onDataChange={load}
        />
      )}

      {data && activeSection === "cash" && (
        <>
          <OperatingSectionHeader title="Cash Forecast & Liquidity" subtitle="Collections · outflows · ending cash trajectory" />
          {data.workforce_validation?.checks?.length ? (
            <WorkforceValidationStrip
              checks={data.workforce_validation.checks}
              section="cash"
              title="Workforce payroll · cash tie-outs"
            />
          ) : null}
          <CashFlowWaterfallTable
            title="Cash forecast"
            response={data.waterfalls.cash_flow}
            selectedScenario={scenario}
            asOfPeriod={closePeriod}
            organizationId={orgId}
            periodsOverride={dashboardPeriods}
          />
        </>
      )}

      {data && activeSection === "decisions" && (
        <>
          <OperatingSectionHeader
            title="Risks, Validation & Decisions"
            subtitle="Forecast trust · reconciliation · board-ready checklist"
          />
          {data.workforce_validation?.checks?.length ? (
            <WorkforceValidationStrip
              checks={data.workforce_validation.checks}
              section="decisions"
              title="Workforce operating model"
            />
          ) : null}
          <ValidationIssuesPanel issues={warnings} />
          <ValidationBanner
            title="Validation summary"
            rows={data.validation.filter((r) => r.status === "pass")}
          />
          <CommentaryPlaceholders prompts={data.commentary_prompts} />
        </>
      )}
    </CfoOperatingShell>
  );
}

function ExecutiveFinancialStatementsSection({
  statements,
  error,
  busy,
  periodsOverride,
}: {
  statements: FinancialStatementsSummary | null;
  error: string | null;
  busy: boolean;
  periodsOverride: string[];
}) {
  const sections = [
    { key: "income", title: "8. Income Statement", statement: statements?.income_statement },
    { key: "balance", title: "9. Balance Sheet", statement: statements?.balance_sheet },
    { key: "cash", title: "10. Cash Flow Statement", statement: statements?.cash_flow },
  ] as const;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {sections.map(({ key, title, statement }) => (
        <div key={key} style={subCard}>
          <h3 style={h3}>{title}</h3>
          {busy && !statement && !error && (
            <p style={{ color: "var(--muted)", margin: 0 }}>Loading financial statements…</p>
          )}
          {error && !statement && (
            <pre style={{ ...errorBox, marginTop: 8 }}>{error}</pre>
          )}
          {statement && statement.periods.length > 0 ? (
            <div style={{ marginTop: 8 }}>
              <FinancialStatementTable statement={statement} periodsOverride={periodsOverride} />
            </div>
          ) : (
            !busy &&
            !error && (
              <p style={{ color: "var(--muted)", margin: 0 }}>
                No statement rows for this period. Upload Actual_ and Forecast_ income statement, balance sheet, and cash
                flow CSVs, then refresh.
              </p>
            )
          )}
        </div>
      ))}
    </div>
  );
}

function KpiGrid({ rows }: { rows: MarketingRow[] }) {
  const totals = {
    marketing_spend: rows.reduce((a, r) => a + n(r.marketing_spend), 0),
    mqls: rows.reduce((a, r) => a + n(r.mqls), 0),
    sqls: rows.reduce((a, r) => a + n(r.sqls), 0),
    pipeline_arr_created: rows.reduce((a, r) => a + n(r.pipeline_arr_created), 0),
    closed_won_arr: rows.reduce((a, r) => a + n(r.closed_won_arr), 0),
    pipeline_per_dollar_spend: n(rows.at(-1)?.pipeline_per_dollar_spend),
  };
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(130px, 1fr))", gap: 10 }}>
      <Metric title="Spend" value={money(totals.marketing_spend)} />
      <Metric title="MQLs" value={count(totals.mqls)} />
      <Metric title="SQLs" value={count(totals.sqls)} />
      <Metric title="Pipeline ARR" value={money(totals.pipeline_arr_created)} />
      <Metric title="Closed Won ARR" value={money(totals.closed_won_arr)} />
      <Metric title="Pipeline / $" value={multiple(totals.pipeline_per_dollar_spend)} />
    </div>
  );
}

function Metric({ title, value }: { title: string; value: string }) {
  return <div style={subCard}><div style={{ color: "var(--muted)", fontSize: 12 }}>{title}</div><div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>{value}</div></div>;
}

function sumMarketing(rows: MarketingRow[], key: keyof MarketingRow) {
  return rows.reduce((total, row) => total + n(row[key] as string | number), 0);
}

function pct(value: string | number | null | undefined) {
  return `${(n(value) * 100).toFixed(1)}%`;
}

function labelize(key: string) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function GtmPerformanceSection({
  totalRows,
  channelRows,
  closedByMonth,
}: {
  totalRows: MarketingRow[];
  channelRows: MarketingRow[];
  closedByMonth: OpportunityRow[];
}) {
  const latestTotals = totalRows.at(-1);
  const oppsWonByChannel = useMemo(() => {
    const map = new Map<string, number>();
    closedByMonth.forEach((row) => {
      const channel = row.marketing_channel ?? "Unassigned";
      map.set(channel, (map.get(channel) ?? 0) + n(row.opportunity_count));
    });
    return map;
  }, [closedByMonth]);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(150px, 1fr))", gap: 10 }}>
        <Metric title="Marketing Spend" value={money(sumMarketing(totalRows, "marketing_spend"))} />
        <Metric title="Pipeline ARR Created" value={money(sumMarketing(totalRows, "pipeline_arr_created"))} />
        <Metric title="Closed Won ARR" value={money(sumMarketing(totalRows, "closed_won_arr"))} />
        <Metric title="Pipeline / $ Spend" value={multiple(latestTotals?.pipeline_per_dollar_spend ?? 0)} />
        <Metric title="MQLs" value={count(sumMarketing(totalRows, "mqls"))} />
        <Metric title="SQLs" value={count(sumMarketing(totalRows, "sqls"))} />
        <Metric title="Cost per SQL" value={money(latestTotals?.cost_per_sql ?? 0)} />
        <Metric
          title="Win Rate $%"
          value={pct(
            safeDiv(sumMarketing(totalRows, "closed_won_arr"), sumMarketing(totalRows, "pipeline_arr_created"))
          )}
        />
      </div>

      <div style={subCard}>
        <strong>GTM channel efficiency — spend vs pipeline created</strong>
        <GtmChannelBubbleChart rows={channelRows} />
      </div>

      <ChannelPerformanceTable rows={channelRows} oppsWonByChannel={oppsWonByChannel} />
    </div>
  );
}

function safeDiv(numerator: number, denominator: number) {
  return denominator === 0 ? 0 : numerator / denominator;
}

const GTM_X_AXIS_STEP = 200_000; // $0.2M on spend (x)

/** Pick a readable Y-axis step ($0.2M–$5M) from the data max so short ranges are not over-ticked. */
function chooseNiceYAxisStep(maxValue: number, targetTickCount = 6) {
  if (maxValue <= 0) return 500_000;
  const rough = maxValue / targetTickCount;
  const candidates = [
    100_000, 200_000, 250_000, 500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000, 5_000_000,
  ];
  for (const step of candidates) {
    if (step >= rough && Math.ceil(maxValue / step) <= 10) return step;
  }
  return candidates[candidates.length - 1]!;
}

function ceilToAxisStep(value: number, step: number) {
  return Math.max(step, Math.ceil(value / step) * step);
}

function axisTickValues(max: number, step: number) {
  const ticks: number[] = [];
  for (let v = 0; v <= max; v += step) ticks.push(v);
  return ticks;
}

function moneyMillionsLabel(value: number) {
  const m = value / 1_000_000;
  if (m >= 1) return `$${m.toFixed(m % 1 === 0 ? 0 : 1)}M`;
  return `$${m.toFixed(2)}M`;
}

type GtmBubbleChannel = {
  channel: string;
  spend: number;
  pipeline: number;
  closedWon: number;
  efficiency: number;
  color: string;
};

function GtmChannelBubbleChart({ rows }: { rows: MarketingRow[] }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [plotWidth, setPlotWidth] = useState(1000);
  const [hover, setHover] = useState<{ item: GtmBubbleChannel; clientX: number; clientY: number } | null>(null);

  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const update = () => setPlotWidth(Math.max(el.clientWidth, 640));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const channels = useMemo((): GtmBubbleChannel[] => {
    const map = new Map<string, MarketingRow[]>();
    rows.forEach((row) => {
      const key = row.marketing_channel ?? "Unassigned";
      map.set(key, [...(map.get(key) ?? []), row]);
    });
    return Array.from(map.entries())
      .map(([channel, items], index) => {
        const spend = sumMarketing(items, "marketing_spend");
        const pipeline = sumMarketing(items, "pipeline_arr_created");
        const closedWon = sumMarketing(items, "closed_won_arr");
        return {
          channel,
          spend,
          pipeline,
          closedWon,
          efficiency: safeDiv(pipeline, spend),
          color: marketingChannelColor(channel, index),
        };
      })
      .filter((item) => item.spend > 0 || item.pipeline > 0);
  }, [rows]);

  const height = 300;
  const padL = 56;
  const padR = 28;
  const padT = 20;
  const padB = 48;
  const plotW = plotWidth;
  const maxSpendRaw = Math.max(...channels.map((c) => c.spend), 0);
  const maxPipelineRaw = Math.max(...channels.map((c) => c.pipeline), 0);
  const yStep = chooseNiceYAxisStep(maxPipelineRaw);
  const maxSpend = ceilToAxisStep(maxSpendRaw, GTM_X_AXIS_STEP);
  const maxPipeline = ceilToAxisStep(maxPipelineRaw, yStep);
  const maxBubble = Math.max(...channels.map((c) => c.closedWon), 1);

  const xScale = (spend: number) => padL + (spend / maxSpend) * (plotW - padL - padR);
  const yScale = (pipeline: number) => height - padB - (pipeline / maxPipeline) * (height - padT - padB);
  const radius = (closedWon: number) => 10 + Math.sqrt(closedWon / maxBubble) * 28;

  const xTickValues = axisTickValues(maxSpend, GTM_X_AXIS_STEP);
  const yTickValues = axisTickValues(maxPipeline, yStep);

  const hovered = hover?.item;

  return (
    <div ref={wrapRef} style={{ width: "100%", marginTop: 12, position: "relative" }}>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${plotW} ${height}`}
        role="img"
        aria-label="GTM channel bubble chart"
        onMouseLeave={() => setHover(null)}
      >
        {xTickValues.map((value) => {
          if (value === 0) return null;
          const x = xScale(value);
          return (
            <g key={`x-${value}`}>
              <line x1={x} x2={x} y1={padT} y2={height - padB} stroke="rgba(0,0,0,0.06)" />
              <text x={x} y={height - padB + 16} fontSize={10} textAnchor="middle" fill="#6b7280">
                {moneyMillionsLabel(value)}
              </text>
            </g>
          );
        })}
        {yTickValues.map((value) => {
          if (value === 0) return null;
          const y = yScale(value);
          return (
            <g key={`y-${value}`}>
              <line x1={padL} x2={plotW - padR} y1={y} y2={y} stroke="rgba(0,0,0,0.06)" />
              <text x={padL - 8} y={y + 4} fontSize={10} textAnchor="end" fill="#6b7280">
                {moneyMillionsLabel(value)}
              </text>
            </g>
          );
        })}
        <text x={padL} y={height - padB + 16} fontSize={10} textAnchor="middle" fill="#6b7280">
          {moneyMillionsLabel(0)}
        </text>
        <line x1={padL} x2={plotW - padR} y1={height - padB} y2={height - padB} stroke="#e5e7eb" />
        <line x1={padL} x2={padL} y1={padT} y2={height - padB} stroke="#e5e7eb" />
        <text x={(plotW + padL - padR) / 2} y={height - 4} fontSize={11} textAnchor="middle" fill="#6b7280">
          Marketing Spend ($M)
        </text>
        <text
          x={14}
          y={(height + padT - padB) / 2}
          fontSize={11}
          textAnchor="middle"
          fill="#6b7280"
          transform={`rotate(-90 14 ${(height + padT - padB) / 2})`}
        >
          Pipeline Created ($M)
        </text>
        {channels.map((item) => (
          <circle
            key={item.channel}
            cx={xScale(item.spend)}
            cy={yScale(item.pipeline)}
            r={radius(item.closedWon)}
            fill={`${item.color}${hovered?.channel === item.channel ? "aa" : "55"}`}
            stroke={item.color}
            strokeWidth={hovered?.channel === item.channel ? 2.5 : 1.5}
            style={{ cursor: "pointer" }}
            onMouseEnter={(e) => setHover({ item, clientX: e.clientX, clientY: e.clientY })}
            onMouseMove={(e) => setHover({ item, clientX: e.clientX, clientY: e.clientY })}
          />
        ))}
      </svg>
      {hover && wrapRef.current
        ? (() => {
            const rect = wrapRef.current!.getBoundingClientRect();
            const left = Math.min(Math.max(hover.clientX - rect.left + 12, 8), rect.width - 220);
            const top = Math.max(hover.clientY - rect.top - 8, 8);
            const ch = hover.item;
            return (
              <div
                style={{
                  position: "absolute",
                  left,
                  top,
                  transform: "translateY(-100%)",
                  pointerEvents: "none",
                  background: "#fff",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: "10px 12px",
                  fontSize: 12,
                  lineHeight: 1.5,
                  boxShadow: "0 8px 24px rgba(28,25,23,0.12)",
                  zIndex: 5,
                  minWidth: 180,
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 4, color: "var(--text)" }}>{ch.channel}</div>
                <div style={{ color: "var(--muted)" }}>Spend: {moneyMillionsLabel(ch.spend)}</div>
                <div style={{ color: "var(--muted)" }}>Pipeline: {moneyMillionsLabel(ch.pipeline)}</div>
                <div style={{ color: "var(--muted)" }}>Efficiency: {ch.efficiency.toFixed(1)}x</div>
                <div style={{ color: "var(--muted)" }}>Closed Won: {moneyMillionsLabel(ch.closedWon)}</div>
              </div>
            );
          })()
        : null}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 10, fontSize: 12, color: "var(--muted)" }}>
        {channels.map((item) => (
          <span key={item.channel} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: item.color, display: "inline-block" }} />
            {item.channel}
          </span>
        ))}
      </div>
    </div>
  );
}

function ChannelPerformanceTable({
  rows,
  oppsWonByChannel,
}: {
  rows: MarketingRow[];
  oppsWonByChannel: Map<string, number>;
}) {
  const channelRows = useMemo(() => {
    const map = new Map<string, MarketingRow[]>();
    rows.forEach((row) => {
      const key = row.marketing_channel ?? "Unassigned";
      map.set(key, [...(map.get(key) ?? []), row]);
    });
    return Array.from(map.entries())
      .map(([channel, items]) => {
        const spend = sumMarketing(items, "marketing_spend");
        const pipeline = sumMarketing(items, "pipeline_arr_created");
        const closedWon = sumMarketing(items, "closed_won_arr");
        const closedLost = sumMarketing(items, "closed_lost_arr");
        const slipped = sumMarketing(items, "slipped_pipeline_arr");
        const oppsWon = oppsWonByChannel.get(channel) ?? 0;
        const cac = oppsWon > 0 ? spend / oppsWon : 0;
        const winRate = safeDiv(closedWon, pipeline);
        return {
          channel,
          spend,
          mqls: sumMarketing(items, "mqls"),
          sqls: sumMarketing(items, "sqls"),
          opportunities_created: sumMarketing(items, "opportunities_created"),
          opps_won: oppsWon,
          pipeline_arr_created: pipeline,
          closed_won_arr: closedWon,
          closed_lost_arr: closedLost,
          slipped_pipeline_arr: slipped,
          cac,
          win_rate: winRate,
        };
      })
      .sort((a, b) => b.pipeline_arr_created - a.pipeline_arr_created);
  }, [rows, oppsWonByChannel]);

  const headers = [
    "Channel",
    "Spend",
    "MQLs",
    "SQLs",
    "Opps",
    "Opps Won",
    "Pipeline ARR",
    "Closed Won ARR",
    "Closed Lost ARR",
    "Slipped ARR",
    "CAC",
    "Win Rate $%",
  ];

  return (
    <div style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: 10 }}>
      <table style={{ width: "100%", minWidth: 1180, borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#f9fafb" }}>
            {headers.map((header) => (
              <th key={header} style={header === "Channel" ? th : thRight}>
                {header}
              </th>
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
              <td style={tdRight}>{count(row.opps_won)}</td>
              <td style={tdRight}>{money(row.pipeline_arr_created)}</td>
              <td style={tdRight}>{money(row.closed_won_arr)}</td>
              <td style={tdRight}>{money(row.closed_lost_arr)}</td>
              <td style={tdRight}>{money(row.slipped_pipeline_arr)}</td>
              <td style={tdRight}>{row.cac > 0 ? money(row.cac) : "—"}</td>
              <td style={tdRight}>{pct(row.win_rate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PipelineWaterfallTable({
  title,
  response,
  selectedScenario,
  asOfPeriod,
  organizationId,
  marketingChannel,
  periodsOverride,
}: {
  title: string;
  response?: WaterfallResponse;
  selectedScenario: string;
  asOfPeriod: string;
  organizationId: string;
  marketingChannel: string;
  periodsOverride?: string[];
}) {
  const [selected, setSelected] = useState<SelectedPipelineCell | null>(null);
  const [drilldown, setDrilldown] = useState<PipelineDrilldownResponse | null>(null);
  const [drilldownBusy, setDrilldownBusy] = useState(false);
  const [drilldownError, setDrilldownError] = useState<string | null>(null);

  const rows = response?.rows ?? [];
  const periods =
    periodsOverride ??
    Array.from(new Set(rows.map((row) => normalizeDashboardPeriod(row.period)))).sort();
  const summaryRows = Array.from(
    rows.reduce((map, row) => {
      const existing = map.get(row.waterfall_type);
      if (!existing) {
        map.set(row.waterfall_type, row);
        return map;
      }
      if (row.detail_count > existing.detail_count) {
        map.set(row.waterfall_type, row);
      }
      return map;
    }, new Map<string, WaterfallSummaryRow>()).values()
  ).sort((a, b) => a.line_item_order - b.line_item_order);

  const amountByTypePeriod = useMemo(() => {
    const map = new Map<string, { amount: number; detail_count: number; scenario: string }>();
    for (const row of rows) {
      const key = `${row.waterfall_type}-${normalizeDashboardPeriod(row.period)}`;
      const current = map.get(key) ?? { amount: 0, detail_count: 0, scenario: row.scenario };
      map.set(key, {
        amount: current.amount + n(row.amount),
        detail_count: current.detail_count + n(row.detail_count),
        scenario: row.scenario,
      });
    }
    return map;
  }, [rows]);

  useEffect(() => {
    if (!selected) {
      setDrilldown(null);
      setDrilldownError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setDrilldownBusy(true);
      setDrilldownError(null);
      try {
        const params = new URLSearchParams({
          organization_id: organizationId,
          scenario: selectedScenario,
          period: selected.period,
          waterfall_type: selected.waterfall_type,
          expected_amount: String(selected.amount),
          _: String(Date.now()),
        });
        if (marketingChannel) params.set("marketing_channel", marketingChannel);
        if (selectedScenario === "Combined") params.set("as_of_period", asOfPeriod);
        const payload = await fetchJson<PipelineDrilldownResponse>(
          `${getApiBase()}/api/v1/waterfalls/pipeline/drilldown?${params}`
        );
        if (!cancelled) setDrilldown(payload);
      } catch (e) {
        if (!cancelled) {
          setDrilldown(null);
          setDrilldownError(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (!cancelled) setDrilldownBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected, organizationId, selectedScenario, marketingChannel, asOfPeriod]);

  const onCellClick = (row: WaterfallSummaryRow, period: string) => {
    if (!PIPELINE_DRILLDOWN_TYPES.has(row.waterfall_type)) return;
    const match = amountByTypePeriod.get(`${row.waterfall_type}-${period}`);
    if (!match || match.detail_count === 0) return;
    setSelected({
      period,
      waterfall_type: row.waterfall_type,
      line_item: row.line_item,
      scenario: match.scenario,
      amount: match.amount,
      detail_count: match.detail_count,
    });
  };

  const tieCheck = drilldown?.validation.find((v) => v.validation_name === "pipeline_cell_opportunities_tie");

  return (
    <div style={subCard}>
      <h3 style={h3}>{title}</h3>
      <p style={{ margin: "0 0 10px", color: "var(--muted)", fontSize: 13, lineHeight: 1.5 }}>
        Click a movement cell (Pipeline Created, Closed Won, Closed Lost, Slipped) to load opportunities from
        opportunity movement files. Beginning and ending pipeline are balance positions.
      </p>
      <div style={{ overflowX: "auto" }}>
        <table style={dashboardTableStyle(periods.length)}>
          <thead>
            <tr>
              <th style={categoryHeaderStyle(th)}>Category</th>
              {periods.map((period) => (
                <th key={period} style={periodHeaderStyle(th)}>
                  {formatDashboardPeriodHeader(period)}
                  <div style={{ marginTop: 4 }}>
                    <span style={scenarioPill(scenarioForPeriod(period, selectedScenario, asOfPeriod))}>
                      {scenarioForPeriod(period, selectedScenario, asOfPeriod)}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {summaryRows.map((row) => (
              <tr key={row.waterfall_type}>
                <td style={{ ...categoryCellStyle(td), fontWeight: 700 }}>{row.line_item}</td>
                {periods.map((period) => {
                  const match = amountByTypePeriod.get(`${row.waterfall_type}-${period}`);
                  const amount = match?.amount ?? 0;
                  const oppCount = match?.detail_count ?? 0;
                  const clickable = PIPELINE_DRILLDOWN_TYPES.has(row.waterfall_type) && oppCount > 0;
                  const isSelected =
                    selected?.period === period &&
                    selected?.waterfall_type === row.waterfall_type;
                  return (
                    <td
                      key={period}
                      onClick={() => onCellClick(row, period)}
                      style={{
                        ...periodCellStyle(td, {
                          color: n(amount) < 0 ? "#b91c1c" : "#166534",
                          fontWeight: 700,
                          cursor: clickable ? "pointer" : "default",
                          background: isSelected ? "#eff6ff" : undefined,
                          boxShadow: isSelected ? "inset 0 0 0 2px #2563eb" : undefined,
                        }),
                      }}
                      title={
                        clickable
                          ? `${oppCount} opportunities — click to view`
                          : PIPELINE_DRILLDOWN_TYPES.has(row.waterfall_type)
                          ? "No opportunity movements for this period"
                          : "Balance position — no opportunity drilldown"
                      }
                    >
                      {match ? (
                        <>
                          <div>{money(amount)}</div>
                          {clickable && (
                            <div style={{ color: "var(--muted)", fontSize: 11, marginTop: 2 }}>
                              {count(oppCount)} opps
                            </div>
                          )}
                        </>
                      ) : (
                        ""
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div style={{ marginTop: 14, borderTop: "1px solid var(--border)", paddingTop: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 10 }}>
            <div>
              <strong>
                {selected.line_item} · {selected.period} ({scenarioForPeriod(selected.period, selectedScenario, asOfPeriod)})
              </strong>
              <div style={{ color: "var(--muted)", fontSize: 13, marginTop: 4 }}>
                Waterfall cell {money(selected.amount)}
                {drilldown && (
                  <>
                    {" "}
                    · {count(drilldown.opportunity_count)} opportunities · sum {money(drilldown.signed_total)}
                  </>
                )}
              </div>
            </div>
            <button type="button" onClick={() => setSelected(null)} style={{ padding: "6px 10px" }}>
              Close
            </button>
          </div>

          {drilldownBusy && <div style={{ color: "var(--muted)" }}>Loading opportunities…</div>}
          {drilldownError && <div style={errorBox}>{drilldownError}</div>}
          {tieCheck && (
            <div style={tieCheck.status === "pass" ? successBox : warningBox}>
              {tieCheck.status === "pass"
                ? "Opportunity amounts tie to the waterfall cell."
                : `Opportunity sum does not tie to cell (variance ${tieCheck.variance ?? "n/a"}).`}
            </div>
          )}
          {drilldown && !drilldown.drilldown_available && drilldown.message && (
            <div style={{ color: "var(--muted)" }}>{drilldown.message}</div>
          )}
          {drilldown && drilldown.opportunities.length > 0 && (
            <div style={{ overflowX: "auto", marginTop: 10 }}>
              <table style={{ ...table, minWidth: 1100, background: "#fafafa" }}>
                <thead>
                  <tr>
                    {[
                      "Opportunity",
                      "Customer",
                      "Channel",
                      "Owner",
                      "Stage",
                      "Type",
                      "ARR",
                      "Weighted ARR",
                      "Probability",
                      "Close Date",
                    ].map((h) => (
                      <th key={h} style={th}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {drilldown.opportunities.map((row, i) => (
                    <tr key={`${row.opportunity_id ?? i}-${row.period}`}>
                      <td style={td}>{row.opportunity_name ?? row.opportunity_id ?? ""}</td>
                      <td style={td}>{row.customer_name ?? row.customer_id ?? ""}</td>
                      <td style={td}>{row.marketing_channel ?? ""}</td>
                      <td style={td}>{row.owner ?? ""}</td>
                      <td style={td}>{row.stage ?? ""}</td>
                      <td style={td}>{row.raw?.opportunity_type ?? ""}</td>
                      <td style={tdRight}>{money(row.arr_impact)}</td>
                      <td style={tdRight}>{money(row.raw?.weighted_arr ?? 0)}</td>
                      <td style={tdRight}>{pct(row.probability)}</td>
                      <td style={td}>{row.close_date ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {drilldown.source_tables.length > 0 && (
                <div style={{ marginTop: 8, fontSize: 12, color: "var(--muted)" }}>
                  Source: {drilldown.source_tables.join(", ")}
                </div>
              )}
            </div>
          )}
          {drilldown && drilldown.opportunities.length === 0 && !drilldownBusy && (
            <div style={{ color: "var(--muted)", marginTop: 8 }}>
              No opportunities found. Upload Actual_, Budget_, and Forecast_opportunity_movements.csv files.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function CashFlowWaterfallTable({
  title,
  response,
  selectedScenario,
  asOfPeriod,
  organizationId,
  periodsOverride,
}: {
  title: string;
  response?: WaterfallResponse;
  selectedScenario: string;
  asOfPeriod: string;
  organizationId: string;
  periodsOverride?: string[];
}) {
  const [selected, setSelected] = useState<SelectedCashCell | null>(null);
  const [drilldown, setDrilldown] = useState<CashFlowDrilldownResponse | null>(null);
  const [drilldownBusy, setDrilldownBusy] = useState(false);
  const [drilldownError, setDrilldownError] = useState<string | null>(null);

  const rows = response?.rows ?? [];
  const periods =
    periodsOverride ??
    Array.from(new Set(rows.map((row) => normalizeDashboardPeriod(row.period)))).sort();
  const summaryRows = Array.from(
    rows.reduce((map, row) => {
      const existing = map.get(row.waterfall_type);
      if (!existing) {
        map.set(row.waterfall_type, row);
        return map;
      }
      if (row.detail_count > existing.detail_count) {
        map.set(row.waterfall_type, row);
      }
      return map;
    }, new Map<string, WaterfallSummaryRow>()).values()
  ).sort((a, b) => a.line_item_order - b.line_item_order);

  const amountByTypePeriod = useMemo(() => {
    const map = new Map<string, { amount: number; detail_count: number; scenario: string }>();
    for (const row of rows) {
      const key = `${row.waterfall_type}-${normalizeDashboardPeriod(row.period)}`;
      const current = map.get(key) ?? { amount: 0, detail_count: 0, scenario: row.scenario };
      map.set(key, {
        amount: current.amount + n(row.amount),
        detail_count: Math.max(current.detail_count, n(row.detail_count)),
        scenario: row.scenario,
      });
    }
    return map;
  }, [rows]);

  useEffect(() => {
    if (!selected) {
      setDrilldown(null);
      setDrilldownError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setDrilldownBusy(true);
      setDrilldownError(null);
      try {
        const params = new URLSearchParams({
          organization_id: organizationId,
          scenario: selectedScenario,
          period: selected.period,
          waterfall_type: selected.waterfall_type,
          expected_amount: String(selected.amount),
          _: String(Date.now()),
        });
        if (selectedScenario === "Combined") params.set("as_of_period", asOfPeriod);
        const payload = await fetchJson<CashFlowDrilldownResponse>(
          `${getApiBase()}/api/v1/waterfalls/cash-flow/drilldown?${params}`
        );
        if (!cancelled) setDrilldown(payload);
      } catch (e) {
        if (!cancelled) {
          setDrilldown(null);
          setDrilldownError(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (!cancelled) setDrilldownBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected, organizationId, selectedScenario, asOfPeriod]);

  const onCellClick = (row: WaterfallSummaryRow, period: string) => {
    if (!CASH_DRILLDOWN_TYPES.has(row.waterfall_type)) return;
    const match = amountByTypePeriod.get(`${row.waterfall_type}-${period}`);
    if (!match || match.detail_count === 0) return;
    setSelected({
      period,
      waterfall_type: row.waterfall_type,
      line_item: row.line_item,
      scenario: match.scenario,
      amount: match.amount,
      detail_count: match.detail_count,
    });
  };

  const tieCheck = drilldown?.validation.find((v) => v.validation_name === "cash_cell_gl_lines_tie");

  return (
    <div style={subCard}>
      <h3 style={h3}>{title}</h3>
      <p style={{ margin: "0 0 10px", color: "var(--muted)", fontSize: 13, lineHeight: 1.5 }}>
        Click a movement cell (collections, payroll, vendor, tax, capex, financing) to load GL detail, workforce
        payroll, or paid invoice lines. Beginning and ending cash are balance positions.
      </p>
      <div style={{ overflowX: "auto" }}>
        <table style={dashboardTableStyle(periods.length)}>
          <thead>
            <tr>
              <th style={categoryHeaderStyle(th)}>Category</th>
              {periods.map((period) => (
                <th key={period} style={periodHeaderStyle(th)}>
                  {formatDashboardPeriodHeader(period)}
                  <div style={{ marginTop: 4 }}>
                    <span style={scenarioPill(scenarioForPeriod(period, selectedScenario, asOfPeriod))}>
                      {scenarioForPeriod(period, selectedScenario, asOfPeriod)}
                    </span>
                  </div>
                </th>
              ))}
              <th style={th}>Source</th>
            </tr>
          </thead>
          <tbody>
            {summaryRows.map((row) => (
              <tr key={row.waterfall_type}>
                <td style={{ ...categoryCellStyle(td), fontWeight: 700 }}>{row.line_item}</td>
                {periods.map((period) => {
                  const match = amountByTypePeriod.get(`${row.waterfall_type}-${period}`);
                  const amount = match?.amount ?? 0;
                  const lineCount = match?.detail_count ?? 0;
                  const clickable = CASH_DRILLDOWN_TYPES.has(row.waterfall_type) && lineCount > 0;
                  const isSelected =
                    selected?.period === period && selected?.waterfall_type === row.waterfall_type;
                  return (
                    <td
                      key={period}
                      onClick={() => onCellClick(row, period)}
                      style={{
                        ...periodCellStyle(td, {
                          color: n(amount) < 0 ? "#b91c1c" : "#166534",
                          fontWeight: 700,
                          cursor: clickable ? "pointer" : "default",
                          background: isSelected ? "#eff6ff" : undefined,
                          boxShadow: isSelected ? "inset 0 0 0 2px #2563eb" : undefined,
                        }),
                      }}
                      title={
                        clickable
                          ? `${lineCount} detail lines — click to view`
                          : CASH_DRILLDOWN_TYPES.has(row.waterfall_type)
                          ? "No GL detail for this period — upload GL detail CSVs"
                          : "Balance position — no GL drilldown"
                      }
                    >
                      {match ? (
                        <>
                          <div>{money(amount)}</div>
                          {clickable && (
                            <div style={{ color: "var(--muted)", fontSize: 11, marginTop: 2 }}>
                              {count(lineCount)} lines
                            </div>
                          )}
                        </>
                      ) : (
                        ""
                      )}
                    </td>
                  );
                })}
                <td style={td}>
                  <code>{row.source_table}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div style={{ marginTop: 14, borderTop: "1px solid var(--border)", paddingTop: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 10 }}>
            <div>
              <strong>
                {selected.line_item} · {selected.period} ({scenarioForPeriod(selected.period, selectedScenario, asOfPeriod)})
              </strong>
              <div style={{ color: "var(--muted)", fontSize: 13, marginTop: 4 }}>
                Waterfall cell {money(selected.amount)}
                {drilldown && (
                  <>
                    {" "}
                    · {count(drilldown.line_count)} lines · sum {money(drilldown.signed_total)}
                  </>
                )}
              </div>
            </div>
            <button type="button" onClick={() => setSelected(null)} style={{ padding: "6px 10px" }}>
              Close
            </button>
          </div>

          {drilldownBusy && <div style={{ color: "var(--muted)" }}>Loading GL detail…</div>}
          {drilldownError && <div style={errorBox}>{drilldownError}</div>}
          {tieCheck && (
            <div style={tieCheck.status === "pass" ? successBox : warningBox}>
              {tieCheck.status === "pass"
                ? "Detail lines tie to the waterfall cell."
                : "Detail line sum differs from the bridge cell — bridge totals come from cash_flow_bridge CSV; GL lines are indicative composition."}
            </div>
          )}
          {drilldown && !drilldown.drilldown_available && drilldown.message && (
            <div style={{ color: "var(--muted)" }}>{drilldown.message}</div>
          )}
          {drilldown && drilldown.lines.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table style={{ ...table, minWidth: 960, background: "#fafafa" }}>
                <thead>
                  <tr>
                    {["Account", "Account group", "Department", "Vendor", "Amount", "Type", "Source"].map((h) => (
                      <th key={h} style={th}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {drilldown.lines.map((line, i) => (
                    <tr key={`${line.source_table}-${i}`}>
                      <td style={td}>
                        {line.account_number ? `${line.account_number} ` : ""}
                        {line.account_name ?? ""}
                        {line.notes ? (
                          <div style={{ color: "var(--muted)", fontSize: 11 }}>{line.notes}</div>
                        ) : null}
                      </td>
                      <td style={td}>{line.account_group ?? ""}</td>
                      <td style={td}>{line.department ?? ""}</td>
                      <td style={td}>{line.vendor_name ?? ""}</td>
                      <td style={tdRight}>{money(line.amount)}</td>
                      <td style={td}>{line.detail_type}</td>
                      <td style={td}>
                        <code>{line.source_table}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {drilldown.source_tables.length > 0 && (
                <div style={{ marginTop: 8, color: "var(--muted)", fontSize: 12 }}>
                  Source: {drilldown.source_tables.join(", ")}
                </div>
              )}
            </div>
          )}
          {drilldown && drilldown.lines.length === 0 && !drilldownBusy && (
            <div style={{ color: "var(--muted)" }}>
              No detail lines found. Upload Actual_gl_detail.csv and Forecast_gl_detail.csv for GL-backed drilldown.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ExpandableWaterfallTable({
  title,
  response,
  filterTypes,
  periodsOverride,
  selectedScenario,
  asOfPeriod,
  expandable = true,
}: {
  title: string;
  response?: WaterfallResponse;
  filterTypes?: string[];
  periodsOverride?: string[];
  selectedScenario: string;
  asOfPeriod: string;
  expandable?: boolean;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const rows = (response?.rows ?? []).filter((row) => !filterTypes || filterTypes.includes(row.waterfall_type));
  const periods =
    periodsOverride ??
    Array.from(new Set(rows.map((row) => normalizeDashboardPeriod(row.period)))).sort();
  const summaryRows = Array.from(
    rows.reduce((map, row) => {
      if (!map.has(row.waterfall_type)) map.set(row.waterfall_type, row);
      return map;
    }, new Map<string, WaterfallSummaryRow>()).values()
  ).sort((a, b) => a.line_item_order - b.line_item_order);
  const amountByTypePeriod = new Map<string, WaterfallSummaryRow>();
  rows.forEach((row) =>
    amountByTypePeriod.set(`${row.waterfall_type}-${normalizeDashboardPeriod(row.period)}`, row)
  );
  const attributionByType = useMemo(() => {
    const map = new Map<string, AttributionRow[]>();
    for (const row of response?.attribution ?? []) {
      const bucket = map.get(row.waterfall_type) ?? [];
      bucket.push(row);
      map.set(row.waterfall_type, bucket);
    }
    return map;
  }, [response?.attribution]);
  return (
    <div style={subCard}>
      <h3 style={h3}>{title}</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={dashboardTableStyle(periods.length, expandable ? 2 : 1)}>
          <thead>
            <tr>
              <th style={categoryHeaderStyle(th)}>Category</th>
              {periods.map((period) => (
                <th key={period} style={periodHeaderStyle(th)}>
                  {formatDashboardPeriodHeader(period)}
                  <div style={{ marginTop: 4 }}>
                    <span style={scenarioPill(scenarioForPeriod(period, selectedScenario, asOfPeriod))}>
                      {scenarioForPeriod(period, selectedScenario, asOfPeriod)}
                    </span>
                  </div>
                </th>
              ))}
              {expandable && <th style={periodHeaderStyle(th)}>Details</th>}
              <th style={th}>Source</th>
            </tr>
          </thead>
          <tbody>
            {summaryRows.map((row) => {
              const key = `${row.waterfall_type}-${row.source_table}`;
              const detail = attributionByType.get(row.waterfall_type) ?? [];
              return (
                <WaterfallSummaryRow
                  key={key}
                  row={row}
                  periods={periods}
                  amountByTypePeriod={amountByTypePeriod}
                  detail={detail}
                  expandable={expandable}
                  expanded={expandable && expanded === key}
                  onToggle={() => setExpanded(expanded === key ? null : key)}
                />
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function WaterfallSummaryRow({
  row,
  periods,
  amountByTypePeriod,
  detail,
  expandable,
  expanded,
  onToggle,
}: {
  row: WaterfallSummaryRow;
  periods: string[];
  amountByTypePeriod: Map<string, WaterfallSummaryRow>;
  detail: AttributionRow[];
  expandable: boolean;
  expanded: boolean;
  onToggle: () => void;
}) {
  const detailColumns = expandable ? 2 : 1;
  return (
    <>
      <tr onClick={expandable ? onToggle : undefined} style={expandable ? { cursor: "pointer" } : undefined}>
        <td style={{ ...categoryCellStyle(td), fontWeight: 700 }}>
          {expandable ? `${expanded ? "▾" : "▸"} ` : ""}
          {row.line_item}
        </td>
        {periods.map((period) => {
          const match = amountByTypePeriod.get(`${row.waterfall_type}-${period}`);
          const amount = match?.amount ?? 0;
          return (
            <td
              key={period}
              style={periodCellStyle(td, {
                color: n(amount) < 0 ? "#b91c1c" : "#166534",
                fontWeight: 700,
              })}
            >
              {match ? money(amount) : ""}
            </td>
          );
        })}
        {expandable && <td style={periodCellStyle(td)}>{detail.length}</td>}
        <td style={td}><code>{row.source_table}</code></td>
      </tr>
      {expandable && expanded && (
        <tr>
          <td style={td} colSpan={periods.length + detailColumns}>
            <WaterfallAttributionTable rows={detail} />
          </td>
        </tr>
      )}
    </>
  );
}

export function WaterfallAttributionTable({ rows }: { rows: AttributionRow[] }) {
  const visibleRows = rows.slice(0, ATTRIBUTION_ROW_LIMIT);
  const truncated = rows.length > visibleRows.length;
  return (
    <div>
      {truncated && (
        <p style={{ margin: "0 0 8px", color: "var(--muted)", fontSize: 12 }}>
          Showing first {visibleRows.length} of {rows.length} attribution rows. Narrow the period or channel filter to see more in the UI.
        </p>
      )}
      <table style={{ ...table, minWidth: 1100, background: "#fafafa" }}>
        <thead><tr>{["Customer", "Opportunity", "Channel", "Owner", "Region", "Segment", "Stage", "Close Date", "ARR Impact", "MRR Impact", "Cash Impact", "Source"].map((h) => <th key={h} style={th}>{h}</th>)}</tr></thead>
        <tbody>{visibleRows.map((row, i) => <OpportunityDrilldownTable key={`${row.source_table}-${i}`} row={row} />)}</tbody>
      </table>
    </div>
  );
}

export function OpportunityDrilldownTable({ row }: { row: AttributionRow }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr onClick={() => setOpen(!open)} style={{ cursor: "pointer" }}>
        <td style={td}>{open ? "▾" : "▸"} {row.customer_name ?? row.customer_id ?? ""}</td>
        <td style={td}>{row.opportunity_name ?? row.opportunity_id ?? ""}</td>
        <td style={td}>{row.marketing_channel ?? ""}</td>
        <td style={td}>{row.owner ?? ""}</td>
        <td style={td}>{row.region ?? ""}</td>
        <td style={td}>{row.segment ?? ""}</td>
        <td style={td}>{row.stage ?? ""}</td>
        <td style={td}>{row.close_date ?? ""}</td>
        <td style={tdRight}>{money(row.arr_impact)}</td>
        <td style={tdRight}>{money(row.mrr_impact)}</td>
        <td style={tdRight}>{money(row.cash_impact)}</td>
        <td style={td}><code>{row.source_table}</code></td>
      </tr>
      {open && <tr><td style={td} colSpan={12}><pre style={rawBox}>{JSON.stringify(row.raw, null, 2)}</pre></td></tr>}
    </>
  );
}

function PipelineByChannel({ title, rows }: { title: string; rows: MarketingRow[] }) {
  const byChannel = Array.from(rows.reduce((map, row) => {
    const channel = row.marketing_channel ?? "Unassigned";
    map.set(channel, (map.get(channel) ?? 0) + n(row.pipeline_arr_created));
    return map;
  }, new Map<string, number>()).entries()).sort((a, b) => b[1] - a[1]).slice(0, 10);
  const total = byChannel.reduce((acc, [, value]) => acc + value, 0) || 1;
  return (
    <div style={subCard}>
      <h3 style={h3}>{title}</h3>
      <div style={{ display: "flex", height: 28, borderRadius: 999, overflow: "hidden", background: "#e5e7eb" }}>
        {byChannel.map(([channel, value], index) => (
          <div
            key={channel}
            title={`${channel}: ${money(value)}`}
            style={{ width: `${(value / total) * 100}%`, background: marketingChannelColor(channel, index) }}
          />
        ))}
      </div>
      <div style={{ display: "grid", gap: 4, marginTop: 10, fontSize: 12 }}>
        {byChannel.map(([channel, value], index) => (
          <div key={channel} style={{ display: "flex", justifyContent: "space-between" }}>
            <span>
              <span
                style={{
                  display: "inline-block",
                  width: 9,
                  height: 9,
                  background: marketingChannelColor(channel, index),
                  marginRight: 6,
                }}
              />
              {channel}
            </span>
            <strong>{money(value)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function ChannelDrilldownGrid({
  title,
  actualRows,
  budgetRows,
}: {
  title: string;
  actualRows: MarketingRow[];
  budgetRows: MarketingRow[];
}) {
  const groups: Record<string, string[]> = {
    "Paid Media": ["Paid Search", "Paid Social"],
    Webinars: ["Webinar"],
    Direct: ["Direct"],
    Partner: ["Partner"],
    Organic: ["Organic Search"],
    Referral: ["Referral"],
    Outbound: ["Outbound"],
    "Field Event": ["Field Event"],
    "Content Syndication": ["Content Syndication"],
    "Customer Success": ["Customer Success"],
  };
  return (
    <div style={{ marginTop: 28 }}>
      <h3 style={{ ...h3, marginTop: 0 }}>{title}</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(170px, 1fr))", gap: 10 }}>
        {Object.entries(groups).map(([group, channels]) => (
          <ChannelDrilldownCard
            key={group}
            title={group}
            actualRows={actualRows.filter((row) => channels.includes(row.marketing_channel ?? ""))}
            budgetRows={budgetRows.filter((row) => channels.includes(row.marketing_channel ?? ""))}
          />
        ))}
      </div>
    </div>
  );
}

const drilldownColHeader: CSSProperties = {
  fontWeight: 700,
  textDecoration: "underline",
  textAlign: "right",
  fontSize: 13,
  minWidth: 88,
};
const drilldownValue: CSSProperties = {
  textAlign: "right",
  fontSize: 13,
  fontWeight: 500,
  color: "var(--text)",
};
const drilldownLabel: CSSProperties = {
  fontSize: 13,
  color: "var(--text)",
  whiteSpace: "nowrap",
};

export function ChannelDrilldownCard({
  title,
  actualRows,
  budgetRows,
}: {
  title: string;
  actualRows: MarketingRow[];
  budgetRows: MarketingRow[];
}) {
  const actSpend = sumMarketing(actualRows, "marketing_spend");
  const budSpend = sumMarketing(budgetRows, "marketing_spend");
  const actPipeline = sumMarketing(actualRows, "pipeline_arr_created");
  const budPipeline = sumMarketing(budgetRows, "pipeline_arr_created");
  const actClosed = sumMarketing(actualRows, "closed_won_arr");
  const budClosed = sumMarketing(budgetRows, "closed_won_arr");
  const actEff = safeDiv(actPipeline, actSpend);
  const budEff = safeDiv(budPipeline, budSpend);

  const metrics: { label: string; actual: string; budget: string }[] = [
    { label: "Spend (YTD)", actual: money(actSpend), budget: money(budSpend) },
    { label: "Pipeline (YTD)", actual: money(actPipeline), budget: money(budPipeline) },
    { label: "Closed Won (YTD)", actual: money(actClosed), budget: money(budClosed) },
    { label: "Efficiency (YTD)", actual: `${actEff.toFixed(2)}x`, budget: `${budEff.toFixed(2)}x` },
  ];

  return (
    <div style={subCard}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) auto auto",
          columnGap: 14,
          rowGap: 6,
          alignItems: "baseline",
        }}
      >
        <strong style={{ fontSize: 15, fontWeight: 700 }}>{title}</strong>
        <span style={drilldownColHeader}>Actual</span>
        <span style={drilldownColHeader}>Budget</span>
        {metrics.map((row) => (
          <Fragment key={row.label}>
            <span style={drilldownLabel}>{row.label}:</span>
            <span style={drilldownValue}>{row.actual}</span>
            <span style={drilldownValue}>{row.budget}</span>
          </Fragment>
        ))}
      </div>
    </div>
  );
}

function OpportunitySummary({
  title,
  response,
  selectedScenario,
  asOfPeriod,
  periodsOverride,
}: {
  title: string;
  response?: OpportunityResponse;
  selectedScenario: string;
  asOfPeriod: string;
  periodsOverride?: string[];
}) {
  const rows = response?.rows ?? [];
  const periods =
    periodsOverride ??
    Array.from(new Set(rows.map((row) => normalizeDashboardPeriod(row.period)))).sort();
  const labels = Array.from(new Set(rows.map((row) => row.stage ?? row.marketing_channel ?? "All"))).sort();
  const amountByLabelPeriod = new Map<string, OpportunityRow>();
  rows.forEach((row) =>
    amountByLabelPeriod.set(
      `${row.stage ?? row.marketing_channel ?? "All"}-${normalizeDashboardPeriod(row.period)}`,
      row
    )
  );
  return (
    <div style={subCard}>
      <h3 style={h3}>{title}</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={dashboardTableStyle(periods.length, 2)}>
          <thead>
            <tr>
              <th style={categoryHeaderStyle(th)}>Stage / Channel</th>
              {periods.map((period) => (
                <th key={period} style={periodHeaderStyle(th)}>
                  {formatDashboardPeriodHeader(period)}
                  <div style={{ marginTop: 4 }}>
                    <span style={scenarioPill(scenarioForPeriod(period, selectedScenario, asOfPeriod))}>
                      {scenarioForPeriod(period, selectedScenario, asOfPeriod)}
                    </span>
                  </div>
                </th>
              ))}
              <th style={periodHeaderStyle(th)}>Total Opps</th>
              <th style={periodHeaderStyle(th)}>Total ARR</th>
            </tr>
          </thead>
          <tbody>
            {labels.map((label) => {
              const totalOpps = rows.filter((row) => (row.stage ?? row.marketing_channel ?? "All") === label).reduce((acc, row) => acc + n(row.opportunity_count), 0);
              const totalArr = rows.filter((row) => (row.stage ?? row.marketing_channel ?? "All") === label).reduce((acc, row) => acc + n(row.amount_arr), 0);
              return (
                <tr key={label}>
                  <td style={{ ...categoryCellStyle(td), fontWeight: 700 }}>{label}</td>
                  {periods.map((period) => {
                    const match = amountByLabelPeriod.get(`${label}-${period}`);
                    return (
                      <td key={period} style={periodCellStyle(td)}>
                        {match ? (
                          <>
                            <div>{money(match.amount_arr)}</div>
                            <div style={{ color: "var(--muted)", fontSize: 11 }}>{count(match.opportunity_count)} opps</div>
                          </>
                        ) : ""}
                      </td>
                    );
                  })}
                  <td style={periodCellStyle(td)}>{count(totalOpps)}</td>
                  <td style={periodCellStyle(td)}>{money(totalArr)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!rows.length && <div style={{ color: "var(--muted)", padding: 12 }}>No opportunity rows returned for this scenario and period range.</div>}
      </div>
    </div>
  );
}

function ValidationIssuesPanel({ issues }: { issues: ValidationCheck[] }) {
  if (!issues.length) {
    return (
      <div style={successBox}>
        <strong>Data quality</strong>: all visible validation checks passed for this period range.
      </div>
    );
  }
  const failed = issues.filter((r) => r.status === "fail");
  const warned = issues.filter((r) => r.status === "warning");

  const renderGroup = (title: string, rows: ValidationCheck[], tone: "fail" | "warn") => {
    if (!rows.length) return null;
    return (
      <div style={{ marginTop: 12 }}>
        <div className="os-section-label">{title}</div>
        <ul className="os-focus-list" style={{ marginTop: 6 }}>
          {rows.map((r) => (
            <li key={`${r.scenario}-${r.period}-${r.validation_name}`} style={{ marginBottom: 8 }}>
              <span
                style={{
                  fontSize: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  color: tone === "fail" ? "var(--negative)" : "var(--watch)",
                  marginRight: 8,
                }}
              >
                {r.status}
              </span>
              <strong>{r.validation_name}</strong>
              <span style={{ color: "var(--muted)" }}>
                {" "}
                · {r.period}
                {r.variance != null && r.variance !== "" ? ` · variance ${r.variance}` : ""}
              </span>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="os-panel">
      <div className="os-section-label" style={{ paddingTop: 0 }}>
        Checks requiring review ({issues.length})
      </div>
      <p style={{ margin: "6px 0 0", fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>
        Resolve failed tie-outs before board export. Warnings are informational but should be acknowledged in MD&amp;A.
      </p>
      {renderGroup("Failed", failed, "fail")}
      {renderGroup("Warnings", warned, "warn")}
    </div>
  );
}

export function ValidationBanner({ title = "Validation / Reconciliation", rows }: { title?: string; rows: ValidationCheck[] }) {
  if (!rows.length) return null;
  return (
    <div style={successBox}>
      <strong>{title}</strong>: {rows.length} check(s) passed.
    </div>
  );
}

function CommentaryPlaceholders({ prompts }: { prompts: Record<string, string> }) {
  const entries = Object.entries(prompts);
  if (!entries.length) return null;
  return (
    <div style={{ marginTop: 16 }}>
      <div className="os-section-label">Narrative prompts (AI / CFO)</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10 }}>
        {entries.map(([key, p]) => (
          <div key={key} className="os-panel" style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>
            <strong style={{ display: "block", color: "var(--text)", marginBottom: 4 }}>{labelize(key)}</strong>
            {p}
          </div>
        ))}
      </div>
    </div>
  );
}

const card: CSSProperties = { border: "1px solid var(--border)", borderRadius: 12, padding: 16, background: "var(--card)" };
const subCard: CSSProperties = { border: "1px solid var(--border)", borderRadius: 10, padding: 14, background: "#fff" };
const label: CSSProperties = { fontSize: 13, minWidth: 0 };
const input: CSSProperties = { display: "block", width: "100%", marginTop: 4, padding: 8 };
const h3: CSSProperties = { margin: "0 0 10px", fontSize: 16 };
const table: CSSProperties = { width: "100%", minWidth: 900, borderCollapse: "collapse", fontSize: 13 };
const th: CSSProperties = { textAlign: "left", padding: 9, borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" };
const thRight: CSSProperties = { ...th, textAlign: "right" };
const td: CSSProperties = { padding: 9, borderBottom: "1px solid var(--border)", whiteSpace: "nowrap", verticalAlign: "top" };
const tdRight: CSSProperties = { ...td, textAlign: "right" };
const errorBox: CSSProperties = { marginTop: 12, color: "#b91c1c", background: "#fef2f2", padding: 12, borderRadius: 8, whiteSpace: "pre-wrap" };
const warningBox: CSSProperties = { marginTop: 12, color: "#92400e", background: "#fffbeb", border: "1px solid #fde68a", padding: 12, borderRadius: 8, fontSize: 13 };
const successBox: CSSProperties = { marginTop: 12, color: "#166534", background: "#f0fdf4", border: "1px solid #bbf7d0", padding: 12, borderRadius: 8, fontSize: 13 };
const rawBox: CSSProperties = { margin: 0, maxHeight: 220, overflow: "auto", whiteSpace: "pre-wrap", fontSize: 11 };
const commentBox: CSSProperties = { border: "1px dashed var(--border)", borderRadius: 8, padding: 10, color: "var(--muted)", background: "#f9fafb", minHeight: 64 };

function scenarioPill(scenarioName: string): CSSProperties {
  const normalized = scenarioName.toLowerCase();
  const isActual = normalized === "actual";
  const isBudget = normalized === "budget";
  return {
    borderRadius: 999,
    padding: "2px 8px",
    fontSize: 11,
    background: isActual ? "#f3f4f6" : isBudget ? "#fef3c7" : "#dbeafe",
    color: isActual ? "#111827" : isBudget ? "#92400e" : "#1d4ed8",
  };
}
