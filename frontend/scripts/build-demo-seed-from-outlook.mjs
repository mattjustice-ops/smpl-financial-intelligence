/**
 * Rebuild the embedded demo data from a saved warehouse outlook payload (GET /api/v1/reporting/outlook)
 * so the pages show the same numbers before the live load lands (or when it fails) as after it.
 *
 * Writes into public/ and canonical/:
 *   board/index.html            TS_DATA, SMPL_DEMO_WF_TABLE (ARR_WATERFALL), WF_DEMO (WORKFORCE), SD_DEMO (SD),
 *                               GTM, SMPL_CASH_BRIDGE (CASH_BRIDGE)
 *   forecast-engine/index.html  SRC
 *   shared/smpl-demo-seed.js    TS_DATA, ARR_WATERFALL, WORKFORCE, baseline_engine, CASH_BRIDGE, HISTORY,
 *                               FUNNEL, SRC.gtm
 *                               (loaded by the Forecast and Budget Engines)
 *
 * Run from frontend/: node scripts/build-demo-seed-from-outlook.mjs <outlook.json> [--write]
 * Default is a dry run that prints old vs new and the tie checks. Nothing is written when a check fails.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const write = args.includes("--write");
const payloadPath = args.find((a) => a !== "--write");
if (!payloadPath) {
  console.error("usage: node scripts/build-demo-seed-from-outlook.mjs <outlook.json> [--write]");
  process.exit(2);
}
const payload = JSON.parse(fs.readFileSync(payloadPath, "utf8"));

/** The live load sets these globals (or null); the snapshot only fills them before that. */
const BRIDGE_PREFIX = "if (window.SMPL_CASH_BRIDGE === undefined) window.SMPL_CASH_BRIDGE=";
const RETENTION_PREFIX = "var SMPL_DEMO_RETENTION=";
const WF_ROWS = ["Beginning", "New Business", "Expansion", "Contraction", "Churn", "Reactivation", "Ending"];
const TOL = 1;
const FUNNEL_KEYS = ["mqls", "opportunities_created", "pipeline_arr_created", "closed_won_arr"];

function tieChecks(d) {
  const fails = [];
  const need = (cond, msg) => { if (!cond) fails.push(msg); };
  const off = (a, b) => a == null || b == null || Math.abs(a - b) > TOL;
  const close = d.meta && d.meta.close_month;
  need(!!close, "meta.close_month missing");
  const ts = d.TS_DATA || {};
  for (const v of ["Actual", "Budget", "Forecast"]) {
    const blk = ts[v];
    if (!blk || !(blk.periods || []).length) { fails.push(`TS_DATA.${v} has no periods`); continue; }
    let prev = null;
    for (const p of blk.periods) {
      const i = (blk.is || {})[p], b = (blk.bs || {})[p], c = (blk.cfs || {})[p];
      if (!i || !b || !c) { fails.push(`${v} ${p} missing a statement`); continue; }
      if (off(b.total_assets, b.total_le)) fails.push(`${v} ${p} balance sheet off ${b.total_assets - b.total_le}`);
      if (off(c.ending_cash, b.cash)) fails.push(`${v} ${p} cash flow ending cash ${c.ending_cash} vs balance sheet ${b.cash}`);
      if (off(c.net_income, i.net_income)) fails.push(`${v} ${p} cash flow NI ${c.net_income} vs income statement ${i.net_income}`);
      if (off(c.beginning_cash + c.net_change, c.ending_cash)) fails.push(`${v} ${p} beginning + net change != ending cash`);
      if (prev != null && off(c.beginning_cash, prev)) fails.push(`${v} ${p} beginning cash ${c.beginning_cash} vs prior ending ${prev}`);
      prev = c.ending_cash;
    }
  }
  const act = ts.Actual || {}, fc = ts.Forecast || {}, bud = ts.Budget || {};
  const actP = act.periods || [];
  need(actP[actP.length - 1] === close, `Actual ends ${actP[actP.length - 1]}, close is ${close}`);
  const actEnd = actP.length ? ((act.cfs || {})[actP[actP.length - 1]] || {}).ending_cash : null;
  const fcFirst = (fc.periods || [])[0];
  if (fcFirst && off(((fc.cfs || {})[fcFirst] || {}).beginning_cash, actEnd)) fails.push(`Forecast ${fcFirst} opening cash does not equal Actual close cash`);
  const budFirst = (bud.periods || [])[0];
  if (budFirst && actP.length && off(((bud.cfs || {})[budFirst] || {}).beginning_cash, ((act.cfs || {})[actP[0]] || {}).beginning_cash)) {
    fails.push(`Budget ${budFirst} opening cash does not equal Actual ${actP[0]} opening cash`);
  }

  const wf = d.ARR_WATERFALL || {};
  for (const k of WF_ROWS) need(Array.isArray(wf[k]) && wf[k].length === 12, `ARR_WATERFALL.${k} is not 12 months`);
  if (!fails.some((f) => f.startsWith("ARR_WATERFALL"))) {
    for (let i = 0; i < 12; i++) {
      const roll = WF_ROWS.slice(0, 6).reduce((s, k) => s + wf[k][i], 0);
      if (off(roll, wf.Ending[i])) fails.push(`ARR waterfall month ${i + 1} does not roll to Ending`);
      if (i > 0 && off(wf.Beginning[i], wf.Ending[i - 1])) fails.push(`ARR waterfall month ${i + 1} Beginning != prior Ending`);
    }
  }
  const budRows = WF_ROWS.map((k) => "Budget_" + k.replace(/ /g, "_"));
  if (Object.keys(wf).some((k) => k.startsWith("Budget_"))) {
    for (const k of budRows) need(Array.isArray(wf[k]) && wf[k].length === 12 && wf[k].every((v) => v != null), `ARR_WATERFALL.${k} is not 12 loaded months`);
    if (!fails.some((f) => f.startsWith("ARR_WATERFALL.Budget_"))) {
      for (let i = 0; i < 12; i++) {
        const roll = budRows.slice(0, 6).reduce((s, k) => s + wf[k][i], 0);
        if (off(roll, wf.Budget_Ending[i])) fails.push(`Budget ARR waterfall month ${i + 1} does not roll to Ending`);
        if (i > 0 && off(wf.Budget_Beginning[i], wf.Budget_Ending[i - 1])) fails.push(`Budget ARR waterfall month ${i + 1} Beginning != prior Ending`);
      }
      if (wf.Beginning && off(wf.Budget_Beginning[0], wf.Beginning[0])) fails.push(`Budget ARR opens at ${wf.Budget_Beginning[0]}, Actual at ${wf.Beginning[0]}`);
    }
  }

  const ret = d.RETENTION || {};
  need(ret.Actual && ret.Budget && ret.Forecast, "RETENTION block missing a scenario");
  const rateOff = (a, b) => a == null || b == null || Math.abs(a - b) > 1e-9;
  actP.forEach((p) => {
    const r = (ret.Actual || {})[p];
    const s = (d.SRC && d.SRC.actuals && d.SRC.actuals[p]) || {};
    if (!r || rateOff(r.nrr, s.nrr) || rateOff(r.grr, s.grr)) fails.push(`RETENTION.Actual ${p} does not equal SRC.actuals retention`);
  });
  if (Object.keys(wf).some((k) => k.startsWith("Budget_"))) {
    const budP = (bud.periods || []).filter((p) => !(ret.Budget || {})[p] || (ret.Budget || {})[p].nrr == null);
    if (budP.length) fails.push(`RETENTION.Budget missing ${budP.join(", ")}`);
  }

  const src = d.SRC || {};
  const srcAct = src.actuals || {};
  actP.forEach((p, i) => {
    const r = srcAct[p];
    if (!r) { fails.push(`SRC.actuals ${p} missing`); return; }
    if (wf.Ending && off(r.arr_eop, wf.Ending[i])) fails.push(`SRC.actuals ${p} ARR ${r.arr_eop} vs waterfall ${wf.Ending[i]}`);
    if (off(r.revenue, ((act.is || {})[p] || {}).revenue)) fails.push(`SRC.actuals ${p} revenue vs TS_DATA`);
    if (off(r.ending_cash, ((act.bs || {})[p] || {}).cash)) fails.push(`SRC.actuals ${p} cash vs TS_DATA`);
  });

  const base = d.baseline_engine || {};
  (fc.periods || []).forEach((p) => {
    const r = base[p];
    if (!r || !r.arr || !r.cfs) { fails.push(`baseline_engine ${p} missing`); return; }
    const wi = (act.periods || []).length + (fc.periods || []).indexOf(p);
    if (wf.Ending && off(r.arr.arr_eop, wf.Ending[wi])) fails.push(`baseline_engine ${p} ARR ${r.arr.arr_eop} vs waterfall ${wf.Ending[wi]}`);
    if (off(r.cfs.end_cash, ((fc.bs || {})[p] || {}).cash)) fails.push(`baseline_engine ${p} cash vs TS_DATA Forecast`);
  });

  const bridge = (d.CASH_BRIDGE || {}).Actual || {};
  actP.forEach((p) => {
    const r = bridge[p];
    if (!r) { fails.push(`CASH_BRIDGE.Actual ${p} missing`); return; }
    if (off(r.ending_cash, ((act.bs || {})[p] || {}).cash)) fails.push(`CASH_BRIDGE ${p} ending cash ${r.ending_cash} vs balance sheet`);
    if (off(r.beginning_cash, ((act.cfs || {})[p] || {}).beginning_cash)) fails.push(`CASH_BRIDGE ${p} beginning cash vs cash flow`);
  });
  need(d.GTM && Object.keys(d.GTM).length > 0, "GTM missing");
  const funnel = d.FUNNEL || {};
  for (const v of ["Actual", "Forecast"]) {
    for (const p of (ts[v] || {}).periods || []) {
      const r = (funnel[v] || {})[p];
      const gaps = FUNNEL_KEYS.filter((k) => !r || r[k] == null);
      if (gaps.length) fails.push(`FUNNEL.${v} ${p} missing ${gaps.join(", ")}`);
    }
  }
  need(Number((src.gtm || {}).avg_acv) > 0, "SRC.gtm.avg_acv missing");

  const h = d.HISTORY || {};
  const hp = h.periods || [];
  if (!hp.length) fails.push("HISTORY has no periods");
  else {
    const last = hp[hp.length - 1];
    const [fy, fm] = (actP[0] || "0000-01").split("-").map(Number);
    const prior = fm === 1 ? `${fy - 1}-12` : `${fy}-${String(fm - 1).padStart(2, "0")}`;
    need(last === prior, `HISTORY ends ${last}, Actual starts ${actP[0]}`);
    if (off(((h.arr || {})[last] || {}).arr_eop, (wf.Beginning || [])[0])) fails.push(`HISTORY ${last} ARR does not open the ARR waterfall`);
    if (off(((h.bs || {})[last] || {}).cash, ((act.cfs || {})[actP[0]] || {}).beginning_cash)) fails.push(`HISTORY ${last} cash does not open Actual ${actP[0]}`);
    let prevCash = null, prevArr = null;
    for (const p of hp) {
      const c = (h.cfs || {})[p], b = (h.bs || {})[p], a = (h.arr || {})[p];
      if (!c || !b || !a) { fails.push(`HISTORY ${p} missing cash flow, balance sheet or ARR`); continue; }
      if (off(c.ending_cash, b.cash)) fails.push(`HISTORY ${p} cash flow ending cash vs balance sheet`);
      if (prevCash != null && off(c.beginning_cash, prevCash)) fails.push(`HISTORY ${p} beginning cash vs prior ending`);
      if (prevArr != null && off(a.arr_bop, prevArr)) fails.push(`HISTORY ${p} ARR opens off the prior month`);
      prevCash = c.ending_cash;
      prevArr = a.arr_eop;
    }
    const programs = (rows, p) => Object.values((rows || {})[p] || {}).reduce((s, v) => s + (Number(v) || 0), 0);
    let actProg = 0, actRev = 0;
    for (const p of actP) { actProg += programs(act.gl_programs, p); actRev += Number(((act.is || {})[p] || {}).revenue) || 0; }
    const ratio = actRev ? actProg / actRev : null;
    need(ratio != null && ratio > 0, "Actual has no marketing programs on revenue to size history");
    if (ratio) {
      const drift = hp.filter(p => {
        const rev = Number(((h.is || {})[p] || {}).revenue) || 0;
        return Math.abs(programs(h.gl_programs, p) - ratio * rev) > 1;
      });
      need(!drift.length, `HISTORY marketing programs off the Actual ${(ratio * 100).toFixed(2)}% of revenue: ${drift.slice(0, 3).join(", ")}`);
    }
  }

  const w = d.WORKFORCE || {};
  need(w.close_month === close, `WORKFORCE close ${w.close_month} vs ${close}`);
  const ci = (w.months || []).indexOf(close);
  need(ci >= 0 && Array.isArray(w.heads_total) && w.heads_total.length === (w.months || []).length, "WORKFORCE heads_total does not cover the months");
  if (ci >= 0 && w.summary) need(w.summary.close_hc === w.heads_total[ci], `WORKFORCE summary close heads ${w.summary.close_hc} vs heads_total ${w.heads_total[ci]}`);

  const sd = d.SD || {};
  need(sd.monthly && Object.keys(sd.monthly).length > 0, "SD.monthly missing");
  need(Array.isArray(sd.reps), "SD.reps missing");
  return fails;
}

function scriptJson(v) {
  return JSON.stringify(v).replace(/<\//g, "<\\/");
}

/** shared/smpl-demo-seed.js for the Forecast and Budget Engines (same payload as the Board's inline blocks). */
function seedFile(d) {
  return [
    "/** Generated by scripts/build-demo-seed-from-outlook.mjs from a warehouse outlook payload; do not edit by hand. */",
    "(function (g) {",
    '  "use strict";',
    "  g.SMPL_DEMO_TS_DATA = " + scriptJson(d.TS_DATA) + ";",
    "  g.SMPL_DEMO_WF_TABLE = " + scriptJson(d.ARR_WATERFALL) + ";",
    "  g.SMPL_DEMO_WORKFORCE = " + scriptJson(d.WORKFORCE) + ";",
    "  // The live load sets these (or null); the snapshot only fills them before that.",
    "  if (g.SMPL_BASELINE_ENGINE === undefined) g.SMPL_BASELINE_ENGINE = " + scriptJson(d.baseline_engine) + ";",
    "  if (g.SMPL_CASH_BRIDGE === undefined) g.SMPL_CASH_BRIDGE = " + scriptJson(d.CASH_BRIDGE) + ";",
    "  if (g.SMPL_HISTORY === undefined) g.SMPL_HISTORY = " + scriptJson(d.HISTORY) + ";",
    "  g.SMPL_DEMO_FUNNEL = " + scriptJson(d.FUNNEL) + ";",
    "  g.SMPL_DEMO_GTM_RATES = " + scriptJson(d.SRC.gtm) + ";",
    "  if (g.SMPLOutlook && g.SMPLOutlook.registerDemoData) {",
    "    g.SMPLOutlook.registerDemoData(g.SMPL_DEMO_TS_DATA, g.SMPL_DEMO_WF_TABLE);",
    "  }",
    '})(typeof window !== "undefined" ? window : globalThis);',
    "",
  ].join("\n");
}

function wfTableBlock(wf, eol) {
  const keys = Object.keys(wf).filter((k) => Array.isArray(wf[k]));
  const body = keys.map((k) => `  ${JSON.stringify(k)}:${JSON.stringify(wf[k])}`).join("," + eol);
  return `var SMPL_DEMO_WF_TABLE={${eol}${body},${eol}};`;
}

/** Replace one single-line `<prefix>{...};` statement; keeps the line's own ending. */
function replaceLine(text, prefix, value, file) {
  const lines = text.split("\n");
  const hits = lines.map((l, i) => (l.startsWith(prefix) ? i : -1)).filter((i) => i >= 0);
  if (hits.length !== 1) throw new Error(`${file}: expected one line starting '${prefix}', found ${hits.length}`);
  const cr = lines[hits[0]].endsWith("\r") ? "\r" : "";
  lines[hits[0]] = prefix + value + ";" + cr;
  return lines.join("\n");
}

/** Replace a multi-line `<prefix>{` ... `};` statement. */
function replaceBlock(text, prefix, replacement, file) {
  const lines = text.split("\n");
  const start = lines.findIndex((l) => l.startsWith(prefix));
  if (start < 0 || lines.slice(start + 1).some((l) => l.startsWith(prefix))) throw new Error(`${file}: expected one '${prefix}' block`);
  const end = lines[start].replace(/\r$/, "").endsWith("};")
    ? start
    : lines.findIndex((l, i) => i > start && l.replace(/\r$/, "") === "};");
  if (end < 0) throw new Error(`${file}: '${prefix}' block has no closing '};'`);
  const cr = lines[start].endsWith("\r") ? "\r" : "";
  lines.splice(start, end - start + 1, replacement + cr);
  return lines.join("\n");
}

function replaceCloseMonth(text, close, file) {
  const re = /^var CLOSE_MONTH = '\d{4}-\d{2}';/m;
  if (!re.test(text)) throw new Error(`${file}: CLOSE_MONTH line not found`);
  return text.replace(re, `var CLOSE_MONTH = '${close}';`);
}

function readSeed(text, prefix) {
  const line = text.split("\n").find((l) => l.startsWith(prefix));
  if (!line) return null;
  const body = line.slice(prefix.length).replace(/\r$/, "").replace(/;$/, "");
  return new Function("return (" + body + ");")();
}

function readBlock(text, prefix) {
  const lines = text.split("\n");
  const start = lines.findIndex((l) => l.startsWith(prefix));
  if (start < 0) return null;
  const end = lines.findIndex((l, i) => i >= start && l.replace(/\r$/, "").endsWith("};"));
  if (end < 0) return null;
  const src = lines.slice(start, end + 1).join("\n").slice(prefix.length).replace(/;\s*$/, "");
  return new Function("return (" + src + ");")();
}

const fails = tieChecks(payload);
const m = (v) => (v == null ? "—" : "$" + (v / 1e6).toFixed(2) + "M");
const boardPath = path.join(root, "public/board/index.html");
const fcPath = path.join(root, "public/forecast-engine/index.html");
const boardHtml = fs.readFileSync(boardPath, "utf8");
const fcHtml = fs.readFileSync(fcPath, "utf8");
const old = {
  ts: readSeed(boardHtml, "var TS_DATA="),
  wf: readBlock(boardHtml, "var SMPL_DEMO_WF_TABLE="),
  wd: readSeed(boardHtml, "var WF_DEMO="),
  sd: readBlock(boardHtml, "const SD_DEMO = "),
  src: readSeed(fcHtml, "const SRC="),
};
const close = payload.meta.close_month;
const ts = payload.TS_DATA;
const decB = ts.Budget.periods[ts.Budget.periods.length - 1];
const decF = ts.Forecast.periods[ts.Forecast.periods.length - 1];
const ci = payload.WORKFORCE.months.indexOf(close);
const rows = [
  ["Actual close cash", m(old.ts?.Actual?.bs?.[close]?.cash), m(ts.Actual.bs[close].cash)],
  ["Actual close revenue", m(old.ts?.Actual?.is?.[close]?.revenue), m(ts.Actual.is[close].revenue)],
  ["Actual close net income", m(old.ts?.Actual?.is?.[close]?.net_income), m(ts.Actual.is[close].net_income)],
  ["Budget year-end cash", m(old.ts?.Budget?.bs?.[decB]?.cash), m(ts.Budget.bs[decB].cash)],
  ["Forecast year-end cash", m(old.ts?.Forecast?.bs?.[decF]?.cash), m(ts.Forecast.bs[decF].cash)],
  ["ARR close", m(old.wf?.Ending?.[ci]), m(payload.ARR_WATERFALL.Ending[ci])],
  ["ARR year-end", m(old.wf?.Ending?.[11]), m(payload.ARR_WATERFALL.Ending[11])],
  ["Budget ARR close / year-end", `${m(old.wf?.Budget_Ending?.[ci])} / ${m(old.wf?.Budget_Ending?.[11])}`,
    `${m(payload.ARR_WATERFALL.Budget_Ending?.[ci])} / ${m(payload.ARR_WATERFALL.Budget_Ending?.[11])}`],
  ["Heads start / close / year-end", old.wd ? `${old.wd.heads_total[0]} / ${old.wd.heads_total[ci]} / ${old.wd.heads_total[11]}` : "—",
    `${payload.WORKFORCE.heads_total[0]} / ${payload.WORKFORCE.heads_total[ci]} / ${payload.WORKFORCE.heads_total[11]}`],
  ["Sales reps", old.sd ? old.sd.reps.length : "—", payload.SD.reps.length],
  ["Forecast SRC actual months", old.src ? Object.keys(old.src.actuals).length : "—", Object.keys(payload.SRC.actuals).length],
  ["Forecast SRC blocks", old.src ? Object.keys(old.src).join(",") : "—", Object.keys(payload.SRC).join(",")],
];
for (const [label, a, b] of rows) console.log(`  ${label.padEnd(32)} ${String(a).padStart(24)}  ->  ${b}`);
for (const f of fails) console.log("FAIL " + f);
if (fails.length) {
  console.log("== tie checks FAILED; nothing written");
  process.exit(1);
}
console.log("== all tie checks passed");
if (!write) {
  console.log("== dry run; nothing written");
  process.exit(0);
}

for (const base of ["public", "canonical"]) {
  const bp = path.join(root, base, "board/index.html");
  let b = fs.readFileSync(bp, "utf8");
  const eol = b.includes("\r\n") ? "\r\n" : "\n";
  b = replaceCloseMonth(b, close, bp);
  b = replaceBlock(b, "const GTM = ", "const GTM = " + scriptJson(payload.GTM) + ";", bp);
  for (const prefix of [BRIDGE_PREFIX, RETENTION_PREFIX]) {
    if (b.split("\n").some((l) => l.startsWith(prefix))) continue;
    const lines = b.split("\n");
    const at = lines.findIndex((l) => l.startsWith("var TS_DATA="));
    lines.splice(at, 0, prefix + "{};" + (lines[at].endsWith("\r") ? "\r" : ""));
    b = lines.join("\n");
  }
  b = replaceLine(b, BRIDGE_PREFIX, scriptJson(payload.CASH_BRIDGE), bp);
  b = replaceLine(b, RETENTION_PREFIX, scriptJson(payload.RETENTION), bp);
  b = replaceLine(b, "var TS_DATA=", scriptJson(payload.TS_DATA), bp);
  b = replaceBlock(b, "var SMPL_DEMO_WF_TABLE=", wfTableBlock(payload.ARR_WATERFALL, eol), bp);
  b = replaceLine(b, "var WF_DEMO=", scriptJson(payload.WORKFORCE), bp);
  b = replaceBlock(b, "const SD_DEMO = ", "const SD_DEMO = " + scriptJson(payload.SD) + ";", bp);
  fs.writeFileSync(bp, b, "utf8");
  console.log("wrote", bp);

  const fp = path.join(root, base, "forecast-engine/index.html");
  const f = replaceLine(fs.readFileSync(fp, "utf8"), "const SRC=", scriptJson(payload.SRC), fp);
  fs.writeFileSync(fp, f, "utf8");
  console.log("wrote", fp);

  const sp = path.join(root, base, "shared/smpl-demo-seed.js");
  fs.writeFileSync(sp, seedFile(payload), "utf8");
  console.log("wrote", sp);
}
