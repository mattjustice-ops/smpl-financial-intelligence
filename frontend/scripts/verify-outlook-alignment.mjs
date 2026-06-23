/**
 * Verifies Board + Forecast demo constants agree (run from frontend/: node scripts/verify-outlook-alignment.mjs)
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const boardHtml = fs.readFileSync(path.join(__dirname, "../public/board/index.html"), "utf8");

function extract(name) {
  const patterns = {
    WF_TABLE: /var SMPL_DEMO_WF_TABLE=(\{[\s\S]*?\n\});/,
    TS_DATA: /var TS_DATA=(\{[\s\S]*?\});[\r\n]+if \(window\.SMPLOutlook/,
  };
  const m = boardHtml.match(patterns[name]);
  if (!m) throw new Error("Missing " + name);
  return new Function("return (" + m[1] + ");")();
}

const wf = extract("WF_TABLE");
const ts = extract("TS_DATA");

const decArr = wf.Ending[11];
const janNi = ts.Actual.is["2026-01"].net_income;
const junNi = ts.Actual.is["2026-06"].net_income;
const decRev = ts.Forecast.is["2026-12"].revenue;
const decCash = ts.Forecast.cfs["2026-12"].ending_cash;

const checks = [
  ["Dec Ending ARR", decArr, 97560000],
  ["Jan actual net income negative", janNi < 0, true],
  ["Jun actual net income negative", junNi < 0, true],
  ["Dec forecast revenue", decRev, 8578200],
  ["Dec ending cash", decCash, 72636320.96],
  ["Jun ending headcount", (() => {
    const m = boardHtml.match(/\[121,124,126,128,130,\s*137,/);
    return m ? 137 : null;
  })(), 137],
  ["Jun net new ARR (waterfall sum)", (() => {
    const wf = extract("WF_TABLE");
    const i = 5;
    return (wf["New Business"][i] + wf.Expansion[i] + wf.Reactivation[i] + wf.Contraction[i] + wf.Churn[i]) / 1e6;
  })(), 2.655],
];

let failed = 0;
for (const [label, actual, expected] of checks) {
  const ok = actual === expected;
  console.log((ok ? "OK" : "FAIL") + "  " + label + ": " + actual + (ok ? "" : " (expected " + expected + ")"));
  if (!ok) failed++;
}

if (failed) process.exit(1);
console.log("\nAll outlook alignment seed checks passed.");
