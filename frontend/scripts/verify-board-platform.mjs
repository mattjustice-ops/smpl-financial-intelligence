/**
 * Board platform data + UI wiring checks — run from frontend/: npm run verify:board
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import vm from "vm";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const boardHtml = fs.readFileSync(path.join(__dirname, "../public/board/index.html"), "utf8");
const boardDataJs = fs.readFileSync(path.join(__dirname, "../public/shared/board-data.js"), "utf8");
const fcHtml = fs.readFileSync(path.join(__dirname, "../public/forecast-engine/index.html"), "utf8");

function extractBoard(name) {
  const patterns = {
    WF_TABLE: /var SMPL_DEMO_WF_TABLE=(\{[\s\S]*?\n\});/,
    TS_DATA: /var TS_DATA=(\{[\s\S]*?\});[\r\n]+if \(window\.SMPLOutlook/,
  };
  const m = boardHtml.match(patterns[name]);
  if (!m) throw new Error("Missing " + name + " in board index");
  return new Function("return (" + m[1] + ");")();
}

const wf = extractBoard("WF_TABLE");
const ts = extractBoard("TS_DATA");
const sdLine = boardHtml.split("\n").find((l) => l.startsWith("const SD_DEMO = "));
if (!sdLine) throw new Error("Missing const SD_DEMO = in board index");
const SD = new Function("return (" + sdLine.slice("const SD_DEMO = ".length).replace(/\r$/, "").replace(/;$/, "") + ");")();
const sdReps = SD.reps || [];
const sdComm = sdReps.filter((r) => r.comm != null);
const wfLine = boardHtml.split("\n").find((l) => l.trimStart().startsWith("var WF_DEMO="));
if (!wfLine) throw new Error("Missing var WF_DEMO= in board index");
const WF = new Function("return (" + wfLine.trim().slice("var WF_DEMO=".length).replace(/;$/, "") + ");")();
const wfPayrollFoots = (() => {
  const parts = WF.payroll_parts || {};
  const teams = Object.values(WF.payroll_by_team || {});
  const months = (WF.payroll || []).map((v, i) => [v, i]).filter(([v]) => v != null);
  if (!months.length || !parts.bonus) return false;
  return months.every(([v, i]) => {
    const partSum = Object.values(parts).reduce((s, series) => s + (series?.[i] || 0), 0);
    const teamSum = teams.reduce((s, t) => s + (t[i] || 0), 0);
    return Math.abs(partSum - v) < 1 && Math.abs(teamSum - v) < 1;
  });
})();
const srcLine = fcHtml.split("\n").find((l) => l.startsWith("const SRC="));
if (!srcLine) throw new Error("Missing const SRC= in forecast-engine index");
const SRC = new Function("return (" + srcLine.slice("const SRC=".length).replace(/\r$/, "").replace(/;$/, "") + ");")();
const CLOSE_MONTH = (boardHtml.match(/^var CLOSE_MONTH = '(\d{4}-\d{2})';/m) || [])[1];
const ACT_N = ts.Actual.periods.indexOf(CLOSE_MONTH) + 1;
const idx = ACT_N - 1;
const fcClose = SRC.actuals[CLOSE_MONTH] || {};

/** Dollar / float tie tolerance (CFS components can drift by sub-cent FP noise). */
function closeEnough(actual, expected, eps) {
  if (typeof actual === "number" && typeof expected === "number") {
    eps = eps == null ? 1 : eps;
    return Math.abs(actual - expected) <= eps;
  }
  return actual === expected;
}

function fmtM(v, d = 1) {
  if (v == null || Number.isNaN(v)) return "—";
  const abs = Math.abs(v);
  const neg = v < 0;
  const s = abs >= 1 ? abs.toFixed(d) + "M" : Math.round(abs * 1000) + "K";
  return (neg ? "-" : "") + "$" + s;
}

function fmtVarM(v, d) {
  if (v == null || Number.isNaN(v)) return "—";
  const abs = Math.abs(v);
  const decimals = d != null ? d : abs < 0.1 ? 2 : 1;
  return (v >= 0 ? "+" : "-") + "$" + abs.toFixed(decimals) + "M";
}

function syncSeries() {
  const actPeriods = ts.Actual.periods.slice(0, ACT_N);
  const isAct = ts.Actual.is;
  const bsAct = ts.Actual.bs;
  const cfsAct = ts.Actual.cfs;

  const ARR_ACT = wf.Ending.slice(0, ACT_N).map((v) => +(v / 1e6).toFixed(2));

  const NN_ACT = [];
  for (let i = 0; i < ACT_N; i++) {
    const nn =
      wf["New Business"][i] +
      wf.Expansion[i] +
      wf.Reactivation[i] +
      wf.Contraction[i] +
      wf.Churn[i];
    NN_ACT.push(+(nn / 1e6).toFixed(3));
  }

  const CASH_ACT = actPeriods.map((p) => {
    const cash = bsAct[p]?.cash ?? cfsAct[p]?.ending_cash;
    return cash != null ? +(cash / 1e6).toFixed(2) : 0;
  });

  const cfsBud = (ts.Budget && ts.Budget.cfs) || {};
  const bsBud = (ts.Budget && ts.Budget.bs) || {};
  // One cash spine: budget ending cash from CFS (preferred) or BS — same as board-data.js
  const CASH_BUD = actPeriods.map((p) => {
    const cash =
      (cfsBud[p] && cfsBud[p].ending_cash != null && cfsBud[p].ending_cash) ||
      (bsBud[p] && bsBud[p].cash != null && bsBud[p].cash) ||
      null;
    return cash != null ? +(cash / 1e6).toFixed(2) : 0;
  });
  const REV_ACT = actPeriods.map((p) => +((isAct[p]?.revenue || 0) / 1e6).toFixed(2));

  return { ARR_ACT, NN_ACT, CASH_ACT, CASH_BUD, REV_ACT, actPeriods };
}

function cfsBridgeRows(c) {
  const rows = [];
  if (c.cfo != null) rows.push({ label: "CFO", value: c.cfo });
  const capex = c.capex != null ? c.capex : c.cfi;
  if (capex != null) rows.push({ label: "CapEx", value: capex });
  if (c.net_change != null) rows.push({ label: "Net change in cash", value: c.net_change, cfsTie: true });
  return rows;
}

const series = syncSeries();
const junCfs = ts.Actual.cfs[CLOSE_MONTH];
const junIs = ts.Actual.is[CLOSE_MONTH];
const junBs = ts.Actual.bs[CLOSE_MONTH];
const bridge = cfsBridgeRows(junCfs);
const netBridge = bridge.find((r) => r.cfsTie);
const cfsNetFromRoll = junCfs.ending_cash - junCfs.beginning_cash;

const checks = [
  ["Close month found in TS_DATA Actual", ACT_N > 0, true],
  ["Close ending ARR ($M) = Forecast Engine SRC", series.ARR_ACT[idx], +((fcClose.arr_eop || 0) / 1e6).toFixed(2), 0.001],
  ["Close NN ARR ($M) = Ending - Beginning", series.NN_ACT[idx], +((wf.Ending[idx] - wf.Beginning[idx]) / 1e6).toFixed(3), 0.001],
  ["NN_ACT length", series.NN_ACT.length, ACT_N],
  ["Close ending cash ($M) = Forecast Engine SRC", series.CASH_ACT[idx], +((fcClose.ending_cash || 0) / 1e6).toFixed(2), 0.001],
  ["Close cash budget ($M) from CFS/BS spine", series.CASH_BUD[idx] > 0, true],
  ["CASH_ACT length", series.CASH_ACT.length, ACT_N],
  ["Board holds no typed collections series", /var COLL\s*=\s*\[\s*-?\d/.test(boardHtml), false],
  ["board-data COLL from the cash bridge", boardDataJs.includes("bridge.collections"), true],
  ["Close ending_cash ties BS", junCfs.ending_cash, junBs.cash, 0.01],
  ["Jun CFS net_change = ending - beginning", cfsNetFromRoll, junCfs.net_change, 1],
  ["Cash bridge net ties CFS", netBridge?.value, junCfs.net_change, 1],
  ["fM formats ARR with decimal", fmtM(86.1, 1), "$86.1M"],
  ["fM formats NN ARR", fmtM(2.655, 1), "$2.7M"],
  ["fV formats variance", fmtVarM(0.58, 1), "+$0.6M"],
  ["fV small variance 2 dec", fmtVarM(0.04), "+$0.04M"],
  ["Close revenue = Forecast Engine SRC", junIs.revenue, fcClose.revenue, 1],
  ["board-data exports boardFmtM", boardDataJs.includes("global.boardFmtM = boardFmtM"), true],
  ["board-data CFS bridge path", boardDataJs.includes("Net change in cash"), true],
  ["board-data CASH_ACT/CASH_BUD from the boardCashM statement spine", boardDataJs.includes('global.CASH_BUD = cashSeries("Budget")') && boardDataJs.includes('global.CASH_ACT = cashSeries("Actual")'), true],
  ["board-data does not preserve old bridge CASH_BUD", !boardDataJs.includes("Keep embedded operational cash budget"), true],
  ["board-data boardRevenueKpis", boardDataJs.includes("boardRevenueKpis"), true],
  ["HTML fM delegates boardFmtM", boardHtml.includes("boardFmtM"), true],
  ["HTML buildCharts refreshes series", /function buildCharts[\s\S]*?boardRefreshAllSeries/.test(boardHtml), true],
  ["HTML ARR KPIs use fM1", boardHtml.includes("fM1(k.eop||0)"), true],
  ["HTML cash KPIs use fM1", boardHtml.includes("fM1(cashEnd)"), true],
  ["HTML PL KPIs use boardPlKpis", boardHtml.includes("boardPlKpis()"), true],
  ["HTML revenue KPIs dynamic", boardHtml.includes("boardRevenueKpis()"), true],
  ["HTML arr table fc-col on td", boardHtml.includes('class="${colCls}"'), true],
  ["HTML skip buildCharts for pl", boardHtml.includes("name === 'pl' || name === 'threestmt'"), true],
  [
    "HTML Validation Engine via top chrome (no Board Validation tab)",
    boardHtml.includes("smpl-validated-stamp") &&
      boardHtml.includes("renderValidation") &&
      !boardHtml.includes("show('validation',this)") &&
      !boardHtml.includes("show('continuity'"),
    true,
  ],
  ["HTML loads board-continuity", boardHtml.includes("board-continuity.js"), true],
  ["HTML loads board-ledger (IS + Mgmt P&L single source)", boardHtml.includes("/shared/board-ledger.js"), true],
  [
    "Mgmt P&L built from ledger, not hardcoded rows",
    boardHtml.includes("SMPLLedger.managementPl()") && !boardHtml.includes("const PL_ROWS"),
    true,
  ],
  ["IS reads through ledger", boardHtml.includes("L.isValue(src, p, key)"), true],
  [
    "board-continuity cite-to-calc drawer",
    fs
      .readFileSync(path.join(__dirname, "../public/shared/board-continuity.js"), "utf8")
      .includes("openCiteDrawer"),
    true,
  ],
  [
    "board-continuity validated stamp + in-board engine",
    (() => {
      const js = fs.readFileSync(path.join(__dirname, "../public/shared/board-continuity.js"), "utf8");
      return (
        js.includes("smpl-validated-stamp") &&
        js.includes("renderValidationEngine") &&
        js.includes("view=validation")
      );
    })(),
    true,
  ],
  [
    "Validation Engine redirects into Board",
    fs.existsSync(path.join(__dirname, "../public/validation/index.html")) &&
      fs
        .readFileSync(path.join(__dirname, "../public/validation/index.html"), "utf8")
        .includes("view=validation"),
    true,
  ],
  ["board-hydrate saves Evidence Pack", fs.readFileSync(path.join(__dirname, "../public/shared/board-hydrate.js"), "utf8").includes("saveEvidencePack"), true],
  ["board-data operational cash bridge", boardDataJs.includes("operationalBridgeRows"), true],
  ["HTML SMPL_CASH_BRIDGE embedded", boardHtml.includes("SMPL_CASH_BRIDGE"), true],
  ["HTML MO12 on window", boardHtml.includes("window.MO12 = MO12"), true],
  ["HTML territory basemap loader", boardHtml.includes("us_emea_basemap.svg"), true],
  ["HTML territory verified pin XY", boardHtml.includes("SALES_TERRITORY_PIN_XY"), true],
  ["HTML exec summary nav links wired", boardHtml.includes("function boardExecNav") && boardHtml.includes("onclick=\"boardExecNav("), true],
  [
    "board-hydrate installs live AI on parse",
    (() => {
      const hydrate = fs.readFileSync(path.join(__dirname, "../public/shared/board-hydrate.js"), "utf8");
      return hydrate.includes("installLiveAi();") && hydrate.includes("installCommentaryCacheRestore();");
    })(),
    true,
  ],
  ["board HTML no direct Anthropic API", !boardHtml.includes("api.anthropic.com"), true],
  ["board HTML has no aiComm stub or static export fallback (board-hydrate owns both)", !/async function aiComm\(|BOARD_EXPORTS|\/board\/exports\//.test(boardHtml), true],
  ["static board exports are not published under /board/exports", fs.existsSync(path.join(__dirname, "../public/board/exports")), false],
  ["GTM narrative reconciles channel closed won to the waterfall's New Business bucket by definition, not as unattributed ARR", boardHtml.includes("is the first-year customer bucket (new logo, winback and first-year expansion, net of first-year contraction and no-starts)") && !boardHtml.includes("not attributed to a channel"), true],
  ["GTM win-rate colors compare to the blended win rate, not typed bands", boardHtml.includes("blendedWr: pipe ? keys.reduce((s, k) => s + (+ch[k].wr || 0) * (+ch[k].pipe || 0), 0) / pipe : null") && !/gtmCh\[k\]\.wr>\d/.test(boardHtml), true],
  ["Sales reps are quota carriers only (every rep has a quota type other than Non-Quota)", sdReps.length > 0 && sdReps.every((r) => r.quota_type && r.quota_type !== "Non-Quota"), true],
  ["Sales team totals are the Bookings ARR closers", SD.team_quota_type, "Bookings ARR"],
  ["Sales close-month team reps are closers on the roster", (() => {
    const n = (SD.monthly[CLOSE_MONTH] || {}).reps;
    return n > 0 && n <= sdReps.filter((r) => r.quota_type === "Bookings ARR").length;
  })(), true],
  ["Sales commission ties to quota carriers by employee ID", SD.commission_loaded === true && sdComm.some((r) => r.comm > 0) && sdComm.every((r) => r.comm >= 0), true],
  ["Workforce payroll total equals its parts (incl. bonus) and the sum of teams every month", wfPayrollFoots, true],
  ["Workforce payroll register ties to the GL payroll it posted for every team",
    WF.payroll_check?.register_loaded === true && (WF.payroll_check.rows || []).length > 0 &&
      WF.payroll_check.rows.every((r) => r.register != null && Math.abs(r.register_variance) <= 1),
    true],
  ["Workforce mix shows unsplit cost-of-revenue labor as its own slice", boardHtml.includes("['Cost-of-revenue labor (not split in GL)','labor',"), true],
  ["Sales commission card counts reps on commission, not every quota carrier", boardHtml.includes("sk.commReps+' on commission'") && !boardHtml.includes("sk.commReps+' quota carriers'"), true],
  ["Every loaded Sales region has a territory map pin", (() => {
    const pins = boardHtml.match(/const SALES_TERRITORY_PIN_XY = \{([\s\S]*?)\};/);
    return !!pins && Object.keys(SD.regions || {}).every((r) => new RegExp("\\b" + r + ":\\s*\\{ x:").test(pins[1]));
  })(), true],
  ["Sales commission empty state names no stale rep ID formats", /REP-xxx|ASALES-xxxx/.test(boardHtml), false],
  ["collections chart has no typed highlight threshold", !/collData\.map\(v=>v>\d/.test(boardHtml), true],
  ["board charts have no typed month fallback", !boardHtml.includes("['Jan','Feb','Mar','Apr','May','Jun']"), true],
  ["board HTML loads board-hydrate v42", boardHtml.includes("board-hydrate.js?v=43"), true],
  ["board-hydrate uses async export jobs", fs.readFileSync(path.join(__dirname, "../public/shared/board-hydrate.js"), "utf8").includes("pollAndDownloadExport"), true],
  ["board-hydrate MDA package uses Prompt 2 endpoint", fs.readFileSync(path.join(__dirname, "../public/shared/board-hydrate.js"), "utf8").includes("/api/v1/export/mda-package.xlsx"), true],
  ["board-hydrate MD&A deck uses Prompt 5 endpoint", fs.readFileSync(path.join(__dirname, "../public/shared/board-hydrate.js"), "utf8").includes("/api/v1/export/mda-deck.pptx"), true],
  ["board-hydrate uses same-origin live API", fs.readFileSync(path.join(__dirname, "../public/shared/board-hydrate.js"), "utf8").includes("boardLiveApiBase"), true],
  ["export_sheet_registry has requirements_prompt_block", fs.readFileSync(path.join(__dirname, "../../backend/app/services/reporting/export/export_sheet_registry.py"), "utf8").includes("def requirements_prompt_block"), true],
  ["territory basemap asset exists", fs.existsSync(path.join(__dirname, "../public/board/us_emea_basemap.svg")), true],
  ["canonical reset script", fs.existsSync(path.join(__dirname, "reset-platform.mjs")), true],
  ["package reset:platform script", fs.readFileSync(path.join(__dirname, "../package.json"), "utf8").includes('"reset:platform"'), true],
  ["prebuild runs verify:board", fs.readFileSync(path.join(__dirname, "../package.json"), "utf8").includes("verify-board-platform.mjs"), true],
];

// Operational cash bridge from board-data.js on a synthetic month: payments are stored positive and must
// show as cash out; every component is listed so the rows foot to the net change.
const bridgeBox = {
  CLOSE_MONTH: "2026-06",
  TS_DATA: { Actual: { periods: ["2026-06"], is: {}, bs: {}, cfs: { "2026-06": { beginning_cash: 50, ending_cash: 85, net_change: 35 } } } },
  SMPL_CASH_BRIDGE: {
    Actual: {
      "2026-06": { beginning_cash: 50, ending_cash: 85, collections: 100, payroll: 40, vendor: 20, commission: 5, tax: 1, interest: 2, other_operating: 3, capex: 4, financing: 10 },
    },
  },
};
vm.createContext(bridgeBox);
vm.runInContext(boardDataJs, bridgeBox);
const bRows = bridgeBox.SMPLBoardData.boardCashBridgeRows("2026-06");
const bVal = (label) => (bRows.find((r) => r.label === label) || {}).value;
const bNet = bRows.find((r) => r.total);
checks.push(
  ["Cash bridge: payroll shows as cash out", bVal("Payroll"), -40],
  ["Cash bridge: CapEx shows as cash out", bVal("CapEx"), -4],
  ["Cash bridge: collections show as cash in", bVal("Collections"), 100],
  ["Cash bridge: tax, interest, other operating and financing listed", [bVal("Tax"), bVal("Interest"), bVal("Other operating"), bVal("Financing")].join(","), "-1,-2,-3,10"],
  ["Cash bridge rows foot to net change", bRows.filter((r) => !r.total).reduce((s, r) => s + r.value, 0), bNet && bNet.value, 0.001],
  ["Cash bridge HTML prints outflows negative", /Payroll<\/span><span[^>]*>-\$40/.test(bridgeBox.SMPLBoardData.boardCashBridgeHtml("2026-06")), true],
);

let failed = 0;
for (const [label, actual, expected, eps] of checks) {
  const ok = closeEnough(actual, expected, eps);
  console.log((ok ? "OK" : "FAIL") + "  " + label + ": " + actual + (ok ? "" : " (expected " + expected + ")"));
  if (!ok) failed++;
}

if (failed) {
  console.error("\n" + failed + " board platform check(s) failed.");
  process.exit(1);
}
console.log("\nAll board platform checks passed (" + checks.length + ").");
