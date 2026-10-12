/**
 * Forecast Engine funnel reads the loaded data: cost per MQL, MQL→opportunity, win rate and MQLs per $ of
 * New Business come from the loaded funnel, GL program spend and booked New Business; missing months stay null.
 * Run: node frontend/scripts/verify-forecast-funnel.mjs
 */
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import path from "path";
import vm from "vm";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const files = ["public/forecast-engine/index.html", "canonical/forecast-engine/index.html"];
const html = readFileSync(path.join(root, files[0]), "utf8");

const checks = [];
const check = (label, ok) => checks.push([label, !!ok]);

check("canonical copy = public copy", readFileSync(path.join(root, files[1]), "utf8") === html);
for (const name of ["FC_GTM_ASSUMED_CPL", "FC_GTM_DEFAULT_ACV", "FC_GTM_DEFAULT_MQL_OPP", "FC_GTM_PIPE_COV", "oppClose",
  "defaultCpl", "updateFcGtmRate", "funnel required"]) {
  check(`no ${name}`, !html.includes(name));
}

function extract(name) {
  const start = html.indexOf(`function ${name}(`);
  if (start < 0) return null;
  let depth = 0;
  for (let i = html.indexOf("{", start); i < html.length; i++) {
    if (html[i] === "{") depth++;
    else if (html[i] === "}" && --depth === 0) return html.slice(start, i + 1);
  }
  return null;
}

const names = ["fcGtmPriorMonth", "fcGtmLoadedFunnel", "fcGtmBookedNb", "fcGtmFunnelRates", "fcGtmImpliedMqls"];
const code = names.map(extract);
check("funnel functions present", code.every(Boolean));
const rateMonths = html.match(/const FC_GTM_RATE_MONTHS = (\d+);/);
check("rate window defined", rateMonths);

function run(funnel, spend, nb) {
  const sandbox = {
    MO12: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    getCloseMonth: () => "2026-06",
    SRC: { actuals: {} },
    window: {},
  };
  let cache = {};
  sandbox.fcPlCache = () => cache;
  sandbox.window.SMPLOutlook = {
    getLoadedFunnel: (p) => funnel[p] || null,
    getLoadedProgramSpend: (p) => (spend[p] == null ? null : spend[p]),
  };
  sandbox.window.SMPL_HISTORY = { arr: Object.fromEntries(Object.entries(nb).map(([p, v]) => [p, { arr_nb: v }])) };
  vm.createContext(sandbox);
  vm.runInContext(`const FC_GTM_RATE_MONTHS = ${rateMonths[1]};\n` + code.join("\n") +
    "\n;this.fcGtmFunnelRates = fcGtmFunnelRates; this.fcGtmImpliedMqls = fcGtmImpliedMqls;", sandbox);
  return sandbox;
}

if (code.every(Boolean) && rateMonths) {
  const months = [];
  for (let m = 7; m <= 12; m++) months.push(`2025-${String(m).padStart(2, "0")}`);
  for (let m = 1; m <= 6; m++) months.push(`2026-${String(m).padStart(2, "0")}`);
  const funnel = {}, spend = {}, nb = {};
  months.forEach((p) => {
    funnel[p] = { mqls: 200, opportunities_created: 25, pipeline_arr_created: 1_000_000, closed_won_arr: 300_000 };
    spend[p] = 600_000;
    nb[p] = 800_000;
  });
  funnel["2025-06"] = { mqls: 1, opportunities_created: 1, pipeline_arr_created: 1, closed_won_arr: 1 };
  spend["2025-06"] = 1;
  nb["2025-06"] = 1;

  const s = run(funnel, spend, nb);
  const r = s.fcGtmFunnelRates();
  check("uses the last 12 closed months", r.months.length === 12 && r.from === "2025-07" && r.to === "2026-06");
  check("cost per MQL = program spend / loaded MQLs", Math.abs(r.cpl - 3000) < 1e-9);
  check("MQL→opportunity = loaded opportunities / MQLs", Math.abs(r.mqlOpp - 0.125) < 1e-12);
  check("win rate = loaded closed-won / pipeline", Math.abs(r.winRate - 0.3) < 1e-12);
  check("MQLs per $ of New Business = MQLs / booked New Business", Math.abs(r.mqlPerNb - 200 / 800_000) < 1e-15);
  check("implied MQLs = New Business × MQLs per $", Math.abs(s.fcGtmImpliedMqls({ wtdNb: 1_600_000 }) - 400) < 1e-9);

  const gap = { ...funnel };
  delete gap["2026-03"];
  const g = run(gap, spend, nb).fcGtmFunnelRates();
  check("a month without loaded funnel is skipped, not filled", g.months.length === 11 && !g.months.includes("2026-03"));

  const none = run({}, {}, {});
  const n = none.fcGtmFunnelRates();
  check("nothing loaded → rates null", n.cpl == null && n.mqlOpp == null && n.winRate == null && n.mqlPerNb == null);
  check("nothing loaded → implied MQLs null", none.fcGtmImpliedMqls({ wtdNb: 1_000_000 }) == null);
}

let failed = 0;
for (const [label, ok] of checks) {
  console.log(`  ${ok ? "ok  " : "FAIL"}  ${label}`);
  if (!ok) failed++;
}
console.log(failed ? `\n${failed} forecast funnel check(s) failed` : "\nall forecast funnel checks passed");
process.exit(failed ? 1 : 0);
