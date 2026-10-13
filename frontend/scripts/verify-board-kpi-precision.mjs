/**
 * Board KPI variances subtract the loaded values, not the chart series (rounded to $10K / $1K),
 * so the headline, drivers and takeaway agree to the dollar. June 2026 production values.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import vm from "vm";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
let failures = 0;
function check(name, ok, detail = "") {
  if (ok) console.log(`OK    ${name}`);
  else {
    failures++;
    console.log(`FAIL  ${name}${detail ? `\n        ${detail}` : ""}`);
  }
}

const months = ["2026-05", "2026-06"];
const row = (bop, nb, exp, con, churn, react, eop) => ({ bop, nb, exp, con, churn, react, eop });
const act = [row(81385000, 2078407.84, 631592.16, -240000, -490000, 80000, 83445000),
  row(83445000, 1992742.03, 704087.4, -313651.94, -520156.87, 0, 85308020.62)];
const bud = [row(80997550, 2041794.79, 568905.21, -244800, -504700, 80000, 82938750),
  row(82938750, 2211135.29, 620535.61, -329334.54, -546164.71, 0, 84894922)];
const wf = {};
const keys = { Beginning: "bop", "New Business": "nb", Expansion: "exp", Contraction: "con", Churn: "churn", Reactivation: "react", Ending: "eop" };
for (const [k, f] of Object.entries(keys)) {
  wf[k] = act.map((r) => r[f]);
  wf["Budget_" + k.replace(/ /g, "_")] = bud.map((r) => r[f]);
}
const stmt = (rev, cash) => ({ is: { [months[1]]: { revenue: rev } }, bs: { [months[1]]: { cash } }, cfs: { [months[1]]: { ending_cash: cash } } });
const win = {
  console,
  CLOSE_MONTH: months[1],
  ACT_MONTHS_COUNT: 2,
  SMPL_DEMO_WF_TABLE: wf,
  TS_DATA: {
    Actual: { periods: months, ...stmt(7350000, 29985000) },
    Budget: { periods: months, ...stmt(7718000, 30640000) },
  },
  WF_DEMO: { heads_total: [240, 247] },
};
win.window = win;
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../public/shared/board-data.js"), "utf8"), win);
win.boardRefreshAllSeries();
const k = win.boardExecKpis();
const near = (a, b) => a != null && Math.abs(a - b) < 1e-9;

check("ARR variance is the loaded difference ($413,098.62), not the rounded series ($420K)",
  near(k.arrVar, (85308020.62 - 84894922) / 1e6), String(k.arrVar));
check("rounded chart series would have said $420K", Math.abs((win.ARR_ACT[1] - win.ARR_BUD[1]) - 0.42) < 1e-9);
const nnAct = 1992742.03 + 704087.4 - 313651.94 - 520156.87;
const nnBud = 2211135.29 + 620535.61 - 329334.54 - 546164.71;
check("net new ARR is the loaded component sum", near(k.nn, nnAct / 1e6), String(k.nn));
check("net new variance is exact", near(k.nnVar, (nnAct - nnBud) / 1e6), String(k.nnVar));
check("cash variance is the loaded difference", near(k.cashAct - k.cashBud, (29985000 - 30640000) / 1e6), `${k.cashAct} ${k.cashBud}`);
const a = win.boardJunArrKpis();
check("ARR tab variance matches the Executive Summary", near(a.eopVar, k.arrVar), `${a.eopVar} vs ${k.arrVar}`);
check("ARR tab net new variance matches", near(a.nnVar, k.nnVar), `${a.nnVar} vs ${k.nnVar}`);
const r = win.boardRevenueKpis();
check("Revenue tab ARR variance matches", near(r.arrVar, k.arrVar), `${r.arrVar} vs ${k.arrVar}`);

console.log(failures ? `\n${failures} KPI precision check(s) failed` : "\nAll board KPI precision checks passed");
process.exit(failures ? 1 : 0);
