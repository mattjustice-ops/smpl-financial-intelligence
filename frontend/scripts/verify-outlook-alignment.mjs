/**
 * The embedded snapshot (Board TS_DATA / SMPL_DEMO_WF_TABLE / WF_DEMO / SD_DEMO, Forecast Engine SRC,
 * shared/smpl-demo-seed.js) ties together and across engines, and the canonical copies match.
 * Run from frontend/: node scripts/verify-outlook-alignment.mjs
 */
import fs from "fs";
import path from "path";
import vm from "vm";
import { fileURLToPath } from "url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (rel) => fs.readFileSync(path.join(root, rel), "utf8");
const boardHtml = read("public/board/index.html");
const fcHtml = read("public/forecast-engine/index.html");

function lineValue(source, prefix) {
  const line = source.split("\n").find((l) => l.startsWith(prefix));
  if (!line) throw new Error("Missing " + prefix.trim());
  return new Function("return (" + line.slice(prefix.length).replace(/\r$/, "").replace(/;$/, "") + ");")();
}

const ts = lineValue(boardHtml, "var TS_DATA=");
const wd = lineValue(boardHtml, "var WF_DEMO=");
const sd = lineValue(boardHtml, "const SD_DEMO = ");
const src = lineValue(fcHtml, "const SRC=");
const bridge = lineValue(boardHtml, "if (window.SMPL_CASH_BRIDGE === undefined) window.SMPL_CASH_BRIDGE=");
const gtm = lineValue(boardHtml, "const GTM = ");
const wfm = boardHtml.match(/var SMPL_DEMO_WF_TABLE=(\{[\s\S]*?\n\});/);
if (!wfm) throw new Error("Missing SMPL_DEMO_WF_TABLE");
const wf = new Function("return (" + wfm[1] + ");")();
const close = (boardHtml.match(/^var CLOSE_MONTH = '(\d{4}-\d{2})';/m) || [])[1];

const seedBox = {};
seedBox.window = seedBox;
vm.createContext(seedBox);
vm.runInContext(read("public/shared/smpl-demo-seed.js"), seedBox);
const baseline = seedBox.SMPL_BASELINE_ENGINE || {};
const hist = seedBox.SMPL_HISTORY || {};

const checks = [];
const eq = (label, actual, expected, tol = 1) => {
  const ok =
    typeof actual === "number" && typeof expected === "number"
      ? Math.abs(actual - expected) <= tol
      : JSON.stringify(actual) === JSON.stringify(expected);
  checks.push([ok, label, actual, expected]);
};

const actP = ts.Actual.periods;
eq("CLOSE_MONTH is the last Actual month", close, actP[actP.length - 1]);
eq("WF_DEMO close month", wd.close_month, close);
eq("smpl-demo-seed TS_DATA equals Board TS_DATA", seedBox.SMPL_DEMO_TS_DATA, ts);
eq("smpl-demo-seed ARR waterfall equals Board", seedBox.SMPL_DEMO_WF_TABLE, wf);
eq("smpl-demo-seed workforce equals Board WF_DEMO", seedBox.SMPL_DEMO_WORKFORCE, wd);
eq("smpl-demo-seed cash bridge equals Board", seedBox.SMPL_CASH_BRIDGE, bridge);

const hp = hist.periods || [];
const hLast = hp[hp.length - 1];
eq("History ends the month before Actual starts", hLast, `${Number(actP[0].slice(0, 4)) - 1}-12`);
eq(`History ${hLast} ARR opens the ARR waterfall`, hLast && hist.arr[hLast].arr_eop, wf.Beginning[0]);
eq(`History ${hLast} cash opens Actual ${actP[0]}`, hLast && hist.bs[hLast].cash, ts.Actual.cfs[actP[0]].beginning_cash);
let histBad = 0;
hp.forEach((p, i) => {
  if (Math.abs(hist.cfs[p].ending_cash - hist.bs[p].cash) > 1) histBad++;
  if (i > 0 && Math.abs(hist.cfs[p].beginning_cash - hist.cfs[hp[i - 1]].ending_cash) > 1) histBad++;
  if (i > 0 && Math.abs(hist.arr[p].arr_bop - hist.arr[hp[i - 1]].arr_eop) > 1) histBad++;
});
eq("History cash and ARR chain every month", histBad, 0, 0);

for (const v of ["Actual", "Budget", "Forecast"]) {
  let prev = null;
  let bad = 0;
  for (const p of ts[v].periods) {
    const i = ts[v].is[p], b = ts[v].bs[p], c = ts[v].cfs[p];
    if (Math.abs(b.total_assets - b.total_le) > 1) bad++;
    if (Math.abs(c.ending_cash - b.cash) > 1) bad++;
    if (Math.abs(c.net_income - i.net_income) > 1) bad++;
    if (Math.abs(c.beginning_cash + c.net_change - c.ending_cash) > 1) bad++;
    if (prev != null && Math.abs(c.beginning_cash - prev) > 1) bad++;
    prev = c.ending_cash;
  }
  eq(`${v}: balance sheet balances, cash flow ties and chains every month`, bad, 0, 0);
}
const fc0 = ts.Forecast.periods[0];
eq(`Forecast ${fc0} opening cash = Actual ${close} ending cash`, ts.Forecast.cfs[fc0].beginning_cash, ts.Actual.cfs[close].ending_cash);
eq("Budget opens from the same cash as Actual", ts.Budget.cfs[ts.Budget.periods[0]].beginning_cash, ts.Actual.cfs[actP[0]].beginning_cash);

let rollBad = 0;
for (let i = 0; i < 12; i++) {
  const roll = wf.Beginning[i] + wf["New Business"][i] + wf.Expansion[i] + wf.Contraction[i] + wf.Churn[i] + wf.Reactivation[i];
  if (Math.abs(roll - wf.Ending[i]) > 1) rollBad++;
  if (i > 0 && Math.abs(wf.Beginning[i] - wf.Ending[i - 1]) > 1) rollBad++;
}
eq("ARR waterfall rolls and chains all 12 months", rollBad, 0, 0);

actP.forEach((p, i) => {
  const a = src.actuals[p] || {};
  eq(`Forecast SRC ${p} ARR = Board waterfall`, a.arr_eop, wf.Ending[i]);
  eq(`Forecast SRC ${p} revenue = Board TS_DATA`, a.revenue, ts.Actual.is[p].revenue);
  eq(`Forecast SRC ${p} net income = Board TS_DATA`, a.net_income, ts.Actual.is[p].net_income);
  eq(`Forecast SRC ${p} cash = Board TS_DATA`, a.ending_cash, ts.Actual.bs[p].cash);
  const cb = (bridge.Actual || {})[p] || {};
  eq(`Cash bridge ${p} ending cash = balance sheet`, cb.ending_cash, ts.Actual.bs[p].cash);
  eq(`Cash bridge ${p} beginning cash = cash flow`, cb.beginning_cash, ts.Actual.cfs[p].beginning_cash);
});
eq("GTM channels carry pipeline, won and MQLs", Object.keys(gtm).length > 0 && Object.values(gtm).every((c) => c.pipe != null && c.won != null && c.mqls != null), true);
ts.Forecast.periods.forEach((p) => {
  const wi = actP.length + ts.Forecast.periods.indexOf(p);
  eq(`Forecast loaded month ${p} ARR = Board waterfall`, baseline[p] && baseline[p].arr.arr_eop, wf.Ending[wi]);
  eq(`Forecast loaded month ${p} cash = Board TS_DATA Forecast`, baseline[p] && baseline[p].cfs.end_cash, ts.Forecast.bs[p].cash);
});

const ci = wd.months.indexOf(close);
eq("WF_DEMO summary close heads = heads_total at close", wd.summary.close_hc, wd.heads_total[ci], 0);
eq("WF_DEMO summary start heads = first month", wd.summary.start_hc, wd.heads_total[0], 0);
eq("SD_DEMO has a month for every Actual month", actP.every((p) => sd.monthly && sd.monthly[p]), true);

eq("Board holds no typed ARR/revenue/cash series", /var (ARR_ACT|REV_ACT|CASH_ACT|CASH_BUD|COLL)\s*=\s*\[\s*-?\d/.test(boardHtml), false);
for (const rel of ["board/index.html", "forecast-engine/index.html", "shared/smpl-demo-seed.js"]) {
  eq(`canonical/${rel} matches public/${rel}`, read("canonical/" + rel) === read("public/" + rel), true);
}

let failed = 0;
for (const [ok, label, actual, expected] of checks) {
  const show = (v) => (typeof v === "object" ? (v == null ? "null" : "{…}") : String(v));
  console.log((ok ? "OK  " : "FAIL") + "  " + label + (ok ? "" : ": " + show(actual) + " (expected " + show(expected) + ")"));
  if (!ok) failed++;
}
if (failed) {
  console.error("\n" + failed + " outlook alignment check(s) failed.");
  process.exit(1);
}
console.log("\nAll outlook alignment checks passed (" + checks.length + ").");
