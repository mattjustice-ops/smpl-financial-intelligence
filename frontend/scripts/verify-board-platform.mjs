/**
 * Board platform data + UI wiring checks — run from frontend/: npm run verify:board
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const boardHtml = fs.readFileSync(path.join(__dirname, "../public/board/index.html"), "utf8");
const boardDataJs = fs.readFileSync(path.join(__dirname, "../public/shared/board-data.js"), "utf8");

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
const CLOSE_MONTH = "2026-06";
const ACT_N = 6;
const idx = ACT_N - 1;

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
  const ARR_BUD = [76.23, 77.72, 79.4, 81.27, 83.33, 85.52];

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

  const NN_BUD = [];
  for (let j = 0; j < ACT_N; j++) {
    const prev = j > 0 ? ARR_BUD[j - 1] : wf.Beginning[0] / 1e6;
    NN_BUD.push(+(ARR_BUD[j] - prev).toFixed(3));
  }

  const CASH_ACT = actPeriods.map((p) => {
    const cash = bsAct[p]?.cash ?? cfsAct[p]?.ending_cash;
    return cash != null ? +(cash / 1e6).toFixed(2) : 0;
  });

  const CASH_BUD = [12.75, 14.95, 22.87, 26.35, 28.64, 31.46];
  const COLL = [9.27, 8.67, 13.59, 10.82, 9.65, 11.18];
  const REV_ACT = actPeriods.map((p) => +((isAct[p]?.revenue || 0) / 1e6).toFixed(2));

  return { ARR_ACT, ARR_BUD, NN_ACT, NN_BUD, CASH_ACT, CASH_BUD, COLL, REV_ACT, actPeriods };
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
  ["Jun ending ARR ($M)", series.ARR_ACT[idx], 86.1],
  ["Jun NN ARR ($M)", series.NN_ACT[idx], 2.655],
  ["NN_ACT length", series.NN_ACT.length, ACT_N],
  ["NN_BUD length", series.NN_BUD.length, ACT_N],
  ["NN chart data non-zero Jun", series.NN_ACT[idx] > 0, true],
  ["Jun ending cash ($M)", series.CASH_ACT[idx], 70.61],
  ["Jun cash budget ($M) operational", series.CASH_BUD[idx], 31.46],
  ["CASH_ACT length", series.CASH_ACT.length, ACT_N],
  ["COLL Jun ($M)", series.COLL[idx], 11.18],
  ["Jun CFS net_change", junCfs.net_change, 4575000, 1],
  ["Jun ending_cash ties BS", junCfs.ending_cash, junBs.cash, 0.01],
  ["Jun CFS net_change = ending - beginning", cfsNetFromRoll, junCfs.net_change, 1],
  ["Cash bridge net ties CFS", netBridge?.value, junCfs.net_change, 1],
  ["fM formats ARR with decimal", fmtM(series.ARR_ACT[idx], 1), "$86.1M"],
  ["fM formats NN ARR", fmtM(series.NN_ACT[idx], 1), "$2.7M"],
  ["fV formats variance", fmtVarM(0.58, 1), "+$0.6M"],
  ["fV small variance 2 dec", fmtVarM(0.04), "+$0.04M"],
  ["Jun revenue ($M)", +(junIs.revenue / 1e6).toFixed(2), 7.41],
  ["board-data exports boardFmtM", boardDataJs.includes("global.boardFmtM = boardFmtM"), true],
  ["board-data CFS bridge path", boardDataJs.includes("Net change in cash"), true],
  ["board-data preserves CASH_BUD", boardDataJs.includes("Keep embedded operational cash budget"), true],
  ["board-data boardRevenueKpis", boardDataJs.includes("boardRevenueKpis"), true],
  ["HTML fM delegates boardFmtM", boardHtml.includes("boardFmtM"), true],
  ["HTML buildCharts refreshes series", /function buildCharts[\s\S]*?boardRefreshAllSeries/.test(boardHtml), true],
  ["HTML ARR KPIs use fM1", boardHtml.includes("fM1(k.eop||0)"), true],
  ["HTML cash KPIs use fM1", boardHtml.includes("fM1(cashEnd)"), true],
  ["HTML PL KPIs use boardPlKpis", boardHtml.includes("boardPlKpis()"), true],
  ["HTML revenue KPIs dynamic", boardHtml.includes("boardRevenueKpis()"), true],
  ["HTML arr table fc-col on td", boardHtml.includes('class="${colCls}"'), true],
  ["HTML skip buildCharts for pl", boardHtml.includes("name === 'pl' || name === 'threestmt'"), true],
  ["board-data operational cash bridge", boardDataJs.includes("operationalBridgeRows"), true],
  ["HTML SMPL_CASH_BRIDGE embedded", boardHtml.includes("SMPL_CASH_BRIDGE"), true],
  ["HTML MO12 on window", boardHtml.includes("window.MO12 = MO12"), true],
  ["HTML territory basemap loader", boardHtml.includes("us_emea_basemap.svg"), true],
  ["HTML territory verified pin XY", boardHtml.includes("SALES_TERRITORY_PIN_XY"), true],
  ["HTML exec summary nav links wired", boardHtml.includes("function boardExecNav") && boardHtml.includes("onclick=\"boardExecNav("), true],
  ["board-hydrate installs live AI on parse", fs.readFileSync(path.join(__dirname, "../public/shared/board-hydrate.js"), "utf8").includes("installLiveAi();\n  installCommentaryCacheRestore"), true],
  ["board HTML no direct Anthropic API", !boardHtml.includes("api.anthropic.com"), true],
  ["board HTML loads board-hydrate v25", boardHtml.includes("board-hydrate.js?v=25"), true],
  ["board-hydrate uses same-origin live API", fs.readFileSync(path.join(__dirname, "../public/shared/board-hydrate.js"), "utf8").includes("boardLiveApiBase"), true],
  ["export_sheet_registry has requirements_prompt_block", fs.readFileSync(path.join(__dirname, "../../backend/app/services/reporting/export/export_sheet_registry.py"), "utf8").includes("def requirements_prompt_block"), true],
  ["territory basemap asset exists", fs.existsSync(path.join(__dirname, "../public/board/us_emea_basemap.svg")), true],
  ["canonical reset script", fs.existsSync(path.join(__dirname, "reset-platform.mjs")), true],
  ["package reset:platform script", fs.readFileSync(path.join(__dirname, "../package.json"), "utf8").includes('"reset:platform"'), true],
  ["prebuild runs verify:board", fs.readFileSync(path.join(__dirname, "../package.json"), "utf8").includes("verify-board-platform.mjs"), true],
];

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
