/**
 * Verifies Board + Forecast demo constants agree (run from frontend/: node scripts/verify-outlook-alignment.mjs)
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const boardHtml = fs.readFileSync(path.join(__dirname, "../public/board/index.html"), "utf8");

function extract(name) {
  const re =
    name === "WF_TABLE"
      ? /const WF_TABLE = (\{[\s\S]*?\n\});[\r\n]+window\.SMPL_DEMO_WF_TABLE/
      : /const TS_DATA=(\{[\s\S]*?\});[\r\n]+window\.SMPL_DEMO_TS_DATA/;
  const m = boardHtml.match(re);
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
];

let failed = 0;
for (const [label, actual, expected] of checks) {
  const ok = actual === expected;
  console.log((ok ? "OK" : "FAIL") + "  " + label + ": " + actual + (ok ? "" : " (expected " + expected + ")"));
  if (!ok) failed++;
}

if (failed) process.exit(1);
console.log("\nAll outlook alignment seed checks passed.");
