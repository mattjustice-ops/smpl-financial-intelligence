/** Derive executive KPI strip from live dashboard payloads (not static deck data). */

export type ExecutiveKpi = {
  label: string;
  value: string;
  delta?: string;
  tone?: "pos" | "neg" | "neu";
};

type WaterfallRow = {
  period: string;
  line_item: string;
  amount: string | number;
  scenario?: string;
};

function num(v: string | number | null | undefined) {
  return Number(v ?? 0);
}

function moneyCompact(v: number) {
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v);
}

function findWaterfallAmount(rows: WaterfallRow[], period: string, match: RegExp) {
  const row = rows.find((r) => r.period === period && match.test(r.line_item.toLowerCase()));
  return row ? num(row.amount) : null;
}

export function deriveExecutiveKpis(input: {
  closePeriod: string;
  arrRows?: WaterfallRow[];
  cashRows?: WaterfallRow[];
  marketingTotals?: {
    pipeline_arr_created: number;
    closed_won_arr: number;
    pipeline_per_dollar_spend: number;
  };
  incomeRevenue?: number | null;
  validationIssueCount?: number;
}): ExecutiveKpi[] {
  const { closePeriod, arrRows = [], cashRows = [], marketingTotals, incomeRevenue, validationIssueCount = 0 } =
    input;

  const endingArr = findWaterfallAmount(arrRows, closePeriod, /ending/);
  const netNewArr = findWaterfallAmount(arrRows, closePeriod, /net\s*new|net_new/);
  const endingCash = findWaterfallAmount(cashRows, closePeriod, /ending/);

  const kpis: ExecutiveKpi[] = [];

  if (endingArr != null) {
    kpis.push({
      label: "Ending ARR",
      value: moneyCompact(endingArr),
      delta: netNewArr != null ? `${netNewArr >= 0 ? "+" : ""}${moneyCompact(netNewArr)} net new` : undefined,
      tone: netNewArr != null && netNewArr >= 0 ? "pos" : "neu",
    });
  }

  if (incomeRevenue != null) {
    kpis.push({ label: "Revenue (CM)", value: moneyCompact(incomeRevenue), tone: "neu" });
  }

  if (endingCash != null) {
    kpis.push({ label: "Ending Cash", value: moneyCompact(endingCash), tone: "pos" });
  }

  if (marketingTotals) {
    kpis.push({
      label: "Pipeline Created",
      value: moneyCompact(marketingTotals.pipeline_arr_created),
      tone: "neu",
    });
    kpis.push({
      label: "Closed Won",
      value: moneyCompact(marketingTotals.closed_won_arr),
      delta: `${marketingTotals.pipeline_per_dollar_spend.toFixed(1)}x pipe / $`,
      tone: marketingTotals.pipeline_per_dollar_spend >= 2 ? "pos" : "neu",
    });
  }

  kpis.push({
    label: "Data Trust",
    value: validationIssueCount === 0 ? "Clear" : `${validationIssueCount} watch`,
    delta: validationIssueCount === 0 ? "validation passed" : "review before board",
    tone: validationIssueCount === 0 ? "pos" : validationIssueCount > 3 ? "neg" : "neu",
  });

  return kpis.slice(0, 5);
}
