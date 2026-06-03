import { monthRange, normalizePeriodKey, scenarioForPeriod } from "./periodScenario";

export type WorkforcePeriodRow = {
  period: string;
  department: string;
  headcount_beginning_fte?: string | number;
  new_hires_fte?: string | number;
  attrition_fte?: string | number;
  headcount_ending_fte?: string | number;
  filled_headcount: string | number;
  planned_hire_headcount: string | number;
  total_headcount_fte: string | number;
  total_people_cost_monthly: string | number;
  productive_quota_capacity_arr: string | number;
};

export type WorkforceOperatingMetric = {
  period: string;
  filled_headcount_fte: string | number;
  planned_hire_headcount_fte: string | number;
  planned_starts_fte: string | number;
  total_headcount_fte: string | number;
  total_people_cost_monthly: string | number;
};

export type WorkforcePlanResponse = {
  organization_id: string;
  scenario: string;
  start_period: string;
  end_period: string;
  departments: string[];
  period_summary: WorkforcePeriodRow[];
  operating_metrics: WorkforceOperatingMetric[];
  validations: Array<{ scenario?: string; validation_name: string; status: string; message?: string | null }>;
  data_sources: string[];
};

export function mergeCombinedWorkforcePlans(
  actual: WorkforcePlanResponse,
  forecast: WorkforcePlanResponse,
  queryStart: string,
  queryEnd: string,
  asOfPeriod: string
): WorkforcePlanResponse {
  const periods = monthRange(queryStart, queryEnd);
  const periodSummary: WorkforcePeriodRow[] = [];
  const operatingMetrics: WorkforceOperatingMetric[] = [];

  for (const period of periods) {
    const slice = scenarioForPeriod(period, "Combined", asOfPeriod) === "Actual" ? actual : forecast;
    periodSummary.push(...slice.period_summary.filter((row) => normalizePeriodKey(row.period) === period));
    const metric = slice.operating_metrics.find((row) => normalizePeriodKey(row.period) === period);
    if (metric) operatingMetrics.push(metric);
  }

  const departments = Array.from(new Set([...actual.departments, ...forecast.departments])).sort();

  return {
    organization_id: forecast.organization_id,
    scenario: "Combined",
    start_period: forecast.start_period,
    end_period: forecast.end_period,
    departments,
    period_summary: periodSummary,
    operating_metrics: operatingMetrics,
    validations: [
      ...actual.validations.map((check) => ({ ...check, scenario: check.scenario ?? "Actual" })),
      ...forecast.validations.map((check) => ({ ...check, scenario: check.scenario ?? "Forecast" })),
    ],
    data_sources: Array.from(new Set([...actual.data_sources, ...forecast.data_sources])),
  };
}

export type PeriodRollup = {
  filled: number;
  planned: number;
  total: number;
  plannedStarts: number;
  peopleCost: number;
  quota: number;
};

export type DepartmentRollup = {
  department: string;
  beginning: number;
  newHires: number;
  attrition: number;
  ending: number;
  openReqs: number;
  totalFte: number;
  peopleCost: number;
};

/** Roll department rows to a full-range view: Jan beginning, Dec ending, summed flow columns. */
export function rollupWorkforceDepartments(
  plan: WorkforcePlanResponse | null,
  queryStart: string,
  queryEnd: string
): DepartmentRollup[] {
  const periods = monthRange(queryStart, queryEnd);
  if (!periods.length || !plan?.period_summary?.length) return [];

  const startKey = normalizePeriodKey(periods[0]);
  const endKey = normalizePeriodKey(periods[periods.length - 1]);
  const periodSet = new Set(periods.map(normalizePeriodKey));
  const byDept = new Map<string, DepartmentRollup>();

  for (const row of plan.period_summary) {
    const period = normalizePeriodKey(row.period);
    if (!periodSet.has(period)) continue;

    const dept = row.department;
    const cur =
      byDept.get(dept) ??
      ({
        department: dept,
        beginning: 0,
        newHires: 0,
        attrition: 0,
        ending: 0,
        openReqs: 0,
        totalFte: 0,
        peopleCost: 0,
      } satisfies DepartmentRollup);

    if (period === startKey) {
      cur.beginning = Number(row.headcount_beginning_fte ?? row.filled_headcount ?? 0);
    }
    if (period === endKey) {
      cur.ending = Number(row.headcount_ending_fte ?? row.filled_headcount ?? 0);
      cur.openReqs = Number(row.planned_hire_headcount ?? 0);
      cur.totalFte = Number(row.total_headcount_fte ?? 0);
      cur.peopleCost = Number(row.total_people_cost_monthly ?? 0);
    }

    cur.newHires += Number(row.new_hires_fte ?? 0);
    cur.attrition += Number(row.attrition_fte ?? 0);
    byDept.set(dept, cur);
  }

  return Array.from(byDept.values()).sort((a, b) => a.department.localeCompare(b.department));
}

export type PeriodRollupEntry = readonly [period: string, totals: PeriodRollup];

export function rollupWorkforcePeriods(plan: WorkforcePlanResponse | null): PeriodRollupEntry[] {
  const metricsByPeriod = new Map(
    (plan?.operating_metrics ?? []).map((row) => [normalizePeriodKey(row.period), row] as const)
  );
  const map = new Map<string, PeriodRollup>();

  for (const row of plan?.period_summary ?? []) {
    const period = normalizePeriodKey(row.period);
    const cur = map.get(period) ?? {
      filled: 0,
      planned: 0,
      total: 0,
      plannedStarts: 0,
      peopleCost: 0,
      quota: 0,
    };
    cur.filled += Number(row.filled_headcount ?? 0);
    cur.planned += Number(row.planned_hire_headcount ?? 0);
    cur.total += Number(row.total_headcount_fte ?? 0);
    cur.plannedStarts += Number(row.new_hires_fte ?? 0);
    cur.peopleCost += Number(row.total_people_cost_monthly ?? 0);
    cur.quota += Number(row.productive_quota_capacity_arr ?? 0);
    map.set(period, cur);
  }

  for (const [period, metric] of metricsByPeriod) {
    const hasDeptRows = (plan?.period_summary ?? []).some((row) => normalizePeriodKey(row.period) === period);
    const cur = map.get(period) ?? {
      filled: 0,
      planned: 0,
      total: 0,
      plannedStarts: 0,
      peopleCost: 0,
      quota: 0,
    };
    cur.plannedStarts = Number(metric.planned_starts_fte ?? 0);
    if (!hasDeptRows) {
      cur.filled = Number(metric.filled_headcount_fte ?? 0);
      cur.planned = Number(metric.planned_hire_headcount_fte ?? 0);
      cur.total = Number(metric.total_headcount_fte ?? 0);
      cur.peopleCost = Number(metric.total_people_cost_monthly ?? 0);
    }
    map.set(period, cur);
  }

  // Include metric-only periods (e.g. zero headcount months).
  for (const [period, metric] of metricsByPeriod) {
    if (!map.has(period)) {
      map.set(period, {
        filled: Number(metric.filled_headcount_fte ?? 0),
        planned: Number(metric.planned_hire_headcount_fte ?? 0),
        total: Number(metric.total_headcount_fte ?? 0),
        plannedStarts: Number(metric.planned_starts_fte ?? 0),
        peopleCost: Number(metric.total_people_cost_monthly ?? 0),
        quota: 0,
      });
    }
  }

  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([period, totals]) => [period, totals] as const);
}
