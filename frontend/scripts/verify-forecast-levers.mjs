/**
 * Headless check: forecast engine levers must change Dec cash / ARR / R&D.
 * Run: node frontend/scripts/verify-forecast-levers.mjs
 */
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import path from "path";
import vm from "vm";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(path.join(root, "public/forecast-engine/index.html"), "utf8");

// Extract inline script block with SRC + engine functions (after smpl-bootstrap, before skin init)
const scriptMatch = html.match(
  /<script src="\/shared\/smpl-bootstrap-demo\.js[^"]*"><\/script>\s*<script>([\s\S]*?)<\/script>\s*<\/div>\s*<\/div>\s*\n\n<script>/,
);
if (!scriptMatch) {
  console.error("Could not extract forecast engine script");
  process.exit(1);
}

const sandbox = {
  window: {},
  document: {
    getElementById: (id) => {
      const defaults = {
        "l-nb": "100",
        "l-exp": "100",
        "l-churn": "100",
        "l-ren": "0",
        "l-cogs": "29",
        "l-sm": "34",
        "l-rd": "16",
        "l-ga": "11",
        "l-dso": "42",
        "l-dpo": "30",
        "l-capex": "220",
      };
      const val = sandbox._levers?.[id] ?? defaults[id] ?? "100";
      return { value: val };
    },
    querySelectorAll: () => [],
  },
  console,
  Chart: {},
  SMPLSkin: { init: () => {} },
  SMPLOutlook: null,
  SMPL_BASELINE_ENGINE: null,
  SMPL_LIVE_OUTLOOK: false,
  CLOSE_MONTH: undefined,
  _levers: {},
  setTimeout: (fn) => fn(),
  destroyAll: () => {},
  curTab: "overview",
  reqActive: {},
};

vm.createContext(sandbox);
vm.runInContext(scriptMatch[1], sandbox);

const {
  compute,
  getLevers,
  getResults,
  getDisplayCFS,
  invalidateCfsChain,
  buildCFSChain,
  HORIZON,
  FC_P,
  ALL_P,
  SRC,
} = sandbox;

SRC.open_reqs.forEach((r) => {
  sandbox.reqActive[r.id] = true;
});

function decCash() {
  invalidateCfsChain();
  const dec = ALL_P[11];
  const cfs = getDisplayCFS(dec);
  return cfs?.end_cash ?? null;
}

function decArr() {
  const res = getResults();
  const dec = FC_P[FC_P.length - 1];
  return res[dec]?.arr?.arr_eop ?? null;
}

function julRd() {
  const res = getResults();
  return res["2026-07"]?.is?.rd ?? null;
}

const base = {
  cash: decCash(),
  arr: decArr(),
  rd: julRd(),
};

// NB attainment 150%
sandbox._levers["l-nb"] = "150";
const nb = { cash: decCash(), arr: decArr(), rd: julRd() };

// Reset + R&D 25%
sandbox._levers = { "l-rd": "25" };
const rd = { cash: decCash(), arr: decArr(), rd: julRd() };

// Reset + toggle off first req
sandbox._levers = {};
sandbox.reqActive["FREQ-001"] = false;
const hc = { cash: decCash(), arr: decArr(), rd: julRd() };

function fmt(n) {
  if (n == null) return "null";
  return "$" + (n / 1e6).toFixed(3) + "M";
}

const checks = [
  ["NB 150% changes Dec ARR", nb.arr !== base.arr],
  ["NB 150% changes Dec cash", nb.cash !== base.cash],
  ["R&D 25% changes Jul R&D line", rd.rd !== base.rd],
  ["R&D 25% changes Dec cash", rd.cash !== base.cash],
  ["FREQ-001 off changes Dec cash", hc.cash !== base.cash],
];

console.log("Baseline Dec cash:", fmt(base.cash), "Dec ARR:", fmt(base.arr), "Jul R&D:", fmt(base.rd));
console.log("NB 150%     Dec cash:", fmt(nb.cash), "Dec ARR:", fmt(nb.arr));
console.log("R&D 25%     Dec cash:", fmt(rd.cash), "Jul R&D:", fmt(rd.rd));
console.log("HC toggle   Dec cash:", fmt(hc.cash));

let failed = 0;
for (const [label, ok] of checks) {
  console.log(ok ? "PASS" : "FAIL", "-", label);
  if (!ok) failed++;
}

process.exit(failed ? 1 : 0);
