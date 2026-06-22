/**
 * Cross-check validation summary CSVs against working Actual/Budget/Forecast CSVs.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const csvDir =
  process.env.SMPL_CSV_DIR ||
  path.join(process.env.USERPROFILE || "", "OneDrive", "Documents", "simple CSVS");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          cell += '"';
          i++;
        } else inQ = false;
      } else cell += c;
      continue;
    }
    if (c === '"') {
      inQ = true;
      continue;
    }
    if (c === ",") {
      row.push(cell);
      cell = "";
      continue;
    }
    if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell);
      if (row.some((x) => x !== "")) rows.push(row);
      row = [];
      cell = "";
      continue;
    }
    cell += c;
  }
  if (cell.length || row.length) {
    row.push(cell);
    if (row.some((x) => x !== "")) rows.push(row);
  }
  return rows;
}

function readCsv(name) {
  const p = path.join(csvDir, name);
  if (!fs.existsSync(p)) return null;
  return parseCsv(fs.readFileSync(p, "utf8"));
}

function rowsToObjects(rows) {
  if (!rows?.length) return [];
  const headers = rows[0];
  return rows.slice(1).map((r) => {
    const o = {};
    headers.forEach((h, i) => {
      o[h] = r[i] ?? "";
    });
    return o;
  });
}

function num(v) {
  if (v == null || v === "") return null;
  const n = Number(String(v).replace(/[$,\s"]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function near(a, b, tol = 1) {
  if (a == null || b == null) return false;
  return Math.abs(a - b) <= tol;
}

const issues = [];
const ok = [];

function check(label, pass, detail) {
  (pass ? ok : issues).push({ label, detail });
}

// --- MRR waterfall ---
const mrrSummary = rowsToObjects(readCsv("mrr_waterfall_validation_summary.csv"));
const mrrMap = Object.fromEntries(mrrSummary.map((r) => [r.metric, r.value]));

const actualMrr = rowsToObjects(readCsv("Actual_MRR_Waterfall.csv"));
const forecastMrr = rowsToObjects(readCsv("Forecast_MRR_Waterfall.csv"));
const budgetMrr = rowsToObjects(readCsv("Budget_MRR_Waterfall.csv"));

const junAct = actualMrr.find((r) => r.period === "2026-06");
const julFc = forecastMrr.find((r) => r.period === "2026-07");
const decFc = forecastMrr.find((r) => r.period === "2026-12");
const decBud = budgetMrr.find((r) => r.period === "2026-12");

const actualPeriods = new Set(actualMrr.map((r) => r.period));
const lastActual = [...actualPeriods].sort().pop();

check(
  "Starting Jan ARR (mrr summary)",
  near(
    num(rowsToObjects(readCsv("Forecast_dataset_summary.csv")).find((r) => r.metric === "Starting January 2026 ARR")?.value),
    num(actualMrr.find((r) => r.period === "2026-01")?.beginning_arr)
  ),
  `file=${actualMrr.find((r) => r.period === "2026-01")?.beginning_arr}`
);
check(
  "Jun→Jul continuity (Actual EOP = Forecast BOP)",
  near(num(junAct?.ending_arr), num(julFc?.beginning_arr)),
  `jun_eop=${num(junAct?.ending_arr)} jul_bop=${num(julFc?.beginning_arr)}`
);
check(
  "mrr summary final_ending_arr vs Forecast Dec",
  near(num(mrrMap.final_ending_arr), num(decFc?.ending_arr)),
  `summary=${mrrMap.final_ending_arr} file=${decFc?.ending_arr}`
);
check(
  "mrr summary budget_dec vs Budget Dec",
  near(num(mrrMap.budget_dec_ending_arr), num(decBud?.ending_arr)),
  `summary=${mrrMap.budget_dec_ending_arr} file=${decBud?.ending_arr}`
);
check(
  "mrr summary forecast_vs_budget_gap",
  near(num(mrrMap.forecast_vs_budget_gap), num(decFc?.ending_arr) - num(decBud?.ending_arr)),
  `summary=${mrrMap.forecast_vs_budget_gap} computed=${num(decFc?.ending_arr) - num(decBud?.ending_arr)}`
);
check(
  "actual_forecast_continuity flag",
  String(mrrMap.actual_forecast_continuity).toLowerCase() === "true" &&
    near(num(junAct?.ending_arr), num(julFc?.beginning_arr)),
  mrrMap.actual_forecast_continuity
);

for (const r of [...actualMrr, ...forecastMrr, ...budgetMrr]) {
  const wc = num(r.waterfall_check);
  if (wc != null && Math.abs(wc) > 1) {
    issues.push({
      label: `waterfall_check ${r.version} ${r.period}`,
      detail: String(wc),
    });
  }
}

// --- Dataset summary files (metadata) ---
for (const summaryName of [
  "Forecast_dataset_summary.csv",
  "Actual_dataset_summary.csv",
  "Budget_dataset_summary.csv",
]) {
  const sumRows = rowsToObjects(readCsv(summaryName));
  const sumMap = Object.fromEntries(sumRows.map((r) => [r.metric, r.value]));
  check(
    `${summaryName} Actual months includes ${lastActual}`,
    String(sumMap["Actual months"] || "").includes(lastActual),
    `summary="${sumMap["Actual months"]}" but Actual_MRR_Waterfall ends ${lastActual}`
  );
}

// --- Income statement spot checks ---
const isSummary = rowsToObjects(readCsv("income_statement_revenue_validation_summary.csv"));
const actIs = rowsToObjects(readCsv("Actual_income_statement.csv"));
const fcIs = rowsToObjects(readCsv("Forecast_income_statement.csv"));

for (const row of isSummary.filter((r) => r.scenario === "Actual" && r.period === "2026-06")) {
  const file = actIs.find((r) => r.period === "2026-06");
  const revCol = file?.revenue ?? file?.total_revenue;
  check(
    "IS validation Actual Jun revenue",
    near(num(row.revenue), num(revCol), 100),
    `summary=${row.revenue} file=${revCol}`
  );
}
const decFcIs = isSummary.find((r) => r.scenario === "Forecast" && r.period === "2026-12");
const decFcIsFile = fcIs.find((r) => r.period === "2026-12");
check(
  "IS validation Forecast Dec revenue",
  near(num(decFcIs?.revenue), num(decFcIsFile?.revenue ?? decFcIsFile?.total_revenue), 100),
  `summary=${decFcIs?.revenue} file=${decFcIsFile?.revenue ?? decFcIsFile?.total_revenue}`
);

// --- full alignment summary ---
const align = rowsToObjects(readCsv("full_alignment_validation_summary.csv"));
const decArrClaim = align.find((r) => r.metric === "arr_waterfall_ties_to_engine");
check(
  "full_alignment Dec ARR claim",
  decArrClaim?.status === "PASS" && near(num(decFc?.ending_arr), 90291802),
  decArrClaim?.notes || ""
);

console.log(JSON.stringify({
  csvDir,
  passed: ok.length,
  failed: issues.length,
  junActualArr: num(junAct?.ending_arr),
  decForecastArr: num(decFc?.ending_arr),
  decBudgetArr: num(decBud?.ending_arr),
  issues,
  ok: ok.map((x) => x.label),
}, null, 2));

const outPath = path.join(path.dirname(fileURLToPath(import.meta.url)), "validate-csv-pack-result.json");
fs.writeFileSync(outPath, JSON.stringify({ issues, ok, junActualArr: num(junAct?.ending_arr), decForecastArr: num(decFc?.ending_arr) }, null, 2));

process.exit(issues.length ? 1 : 0);
