/**
 * Headless check: forecast engine levers must change Dec cash / ARR / R&D.
 * Run: node frontend/scripts/verify-forecast-levers.mjs
 */
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import path from "path";
import vm from "vm";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const publicDir = path.join(root, "public");
const html = readFileSync(path.join(publicDir, "forecast-engine/index.html"), "utf8");

function extractEngineScript(source) {
  const marker = 'src="/shared/smpl-bootstrap-demo.js';
  const after = source.indexOf(marker);
  if (after < 0) return null;
  const start = source.indexOf("<script>", after);
  if (start < 0) return null;
  const end = source.indexOf("</script>", start);
  if (end < 0) return null;
  let code = source.slice(start + "<script>".length, end);
  // Drop UI boot (DOM + skin) — keep compute / levers / CFS only.
  const cutMarkers = ["buildLeverReqs();", "// ─── SKIN ENGINE", "SMPLSkin.init("];
  for (const m of cutMarkers) {
    const idx = code.indexOf(m);
    if (idx > 0) {
      code = code.slice(0, idx);
      break;
    }
  }
  return code;
}

const engineCode = extractEngineScript(html);
if (!engineCode) {
  console.error("Could not extract forecast engine script");
  process.exit(1);
}

const elStore = new Map();
function fakeEl(id) {
  if (elStore.has(id)) return elStore.get(id);
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
  const el = {
    id,
    value: sandbox._levers?.[id] ?? defaults[id] ?? "100",
    textContent: "",
    innerHTML: "",
    style: {},
    children: [],
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    getAttribute() { return null; },
    setAttribute() {},
    addEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
  };
  Object.defineProperty(el, "value", {
    get() {
      return sandbox._levers?.[id] ?? defaults[id] ?? el._value ?? "100";
    },
    set(v) {
      el._value = String(v);
    },
  });
  elStore.set(id, el);
  return el;
}

const sandbox = {
  window: {},
  document: {
    getElementById: (id) => fakeEl(id),
    querySelectorAll: () => [],
    querySelector: () => null,
    createElement: () => fakeEl("anon"),
  },
  console,
  Chart: function () {},
  SMPLSkin: { init: () => {} },
  SMPLOutlook: null,
  SMPL_BASELINE_ENGINE: null,
  SMPL_LIVE_OUTLOOK: false,
  SMPLPipeline: undefined,
  CLOSE_MONTH: undefined,
  _levers: {},
  setTimeout: (fn) => (typeof fn === "function" ? fn() : 0),
  clearTimeout: () => {},
  destroyAll: () => {},
  curTab: "overview",
  reqActive: {},
  requestAnimationFrame: (fn) => (typeof fn === "function" ? fn() : 0),
};

sandbox.window = sandbox;
sandbox.globalThis = sandbox;

// Load shared pipeline if present (optional for ARR path).
try {
  const pipe = readFileSync(path.join(publicDir, "shared/smpl-pipeline.js"), "utf8");
  vm.createContext(sandbox);
  vm.runInContext(pipe, sandbox);
} catch {
  vm.createContext(sandbox);
}

vm.runInContext(
  engineCode +
    `\n;Object.assign(this, {
  compute, getLevers, getResults, getDisplayCFS, invalidateCfsChain, buildCFSChain,
  HORIZON, FC_P, ALL_P, SRC, hz, reqActive, getEl
});\n`,
  sandbox,
);

const {
  compute,
  getLevers,
  getResults,
  getDisplayCFS,
  invalidateCfsChain,
  FC_P,
  ALL_P,
  SRC,
} = sandbox;

if (typeof compute !== "function" || typeof getResults !== "function" || !ALL_P) {
  console.error("FAIL: forecast compute/getResults/ALL_P not available after extract");
  process.exit(1);
}

if (SRC && SRC.open_reqs) {
  SRC.open_reqs.forEach((r) => {
    sandbox.reqActive[r.id] = true;
  });
}

function syncLeverDom() {
  // getLevers reads input values via getElementById — keep _levers authoritative.
  for (const [id, el] of elStore.entries()) {
    if (sandbox._levers[id] != null) el._value = String(sandbox._levers[id]);
  }
}

function decCash() {
  syncLeverDom();
  if (typeof invalidateCfsChain === "function") invalidateCfsChain();
  const dec = ALL_P[11];
  const cfs = getDisplayCFS(dec);
  return cfs?.end_cash ?? null;
}

function decArr() {
  syncLeverDom();
  const res = getResults();
  const dec = FC_P[FC_P.length - 1];
  return res[dec]?.arr?.arr_eop ?? null;
}

function julRd() {
  syncLeverDom();
  const res = getResults();
  return res["2026-07"]?.is?.rd ?? null;
}

const base = {
  cash: decCash(),
  arr: decArr(),
  rd: julRd(),
};

sandbox._levers["l-nb"] = "150";
const nb = { cash: decCash(), arr: decArr(), rd: julRd() };

sandbox._levers = { "l-rd": "25" };
const rd = { cash: decCash(), arr: decArr(), rd: julRd() };

sandbox._levers = {};
if (sandbox.reqActive) sandbox.reqActive["FREQ-001"] = false;
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
