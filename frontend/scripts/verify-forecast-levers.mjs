/**
 * Headless check: forecast engine levers must change Dec cash / ARR / R&D.
 * Drives fcArr/fcCost/fcHc state (not unmounted DOM inputs) and markScenarioDirty,
 * matching Sensitivity / sidebar SoT after the lever-sidebar move.
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
    value: defaults[id] ?? "100",
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
      return el._value ?? defaults[id] ?? "100";
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
  setTimeout: (fn) => (typeof fn === "function" ? fn() : 0),
  clearTimeout: () => {},
  destroyAll: () => {},
  curTab: "overview",
  reqActive: {},
  requestAnimationFrame: (fn) => (typeof fn === "function" ? fn() : 0),
  refresh: () => {},
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
  compute, getLevers, getResults, getDisplayCFS, invalidateCfsChain, markScenarioDirty, buildCFSChain,
  HORIZON, FC_P, ALL_P, SRC, hz, reqActive, getEl,
  fcArrState, fcCostState, fcWcState, fcHcState, ensureFcHcState, seedFcHcFromOpenReqs
});\n`,
  sandbox,
);

const {
  compute,
  getResults,
  getDisplayCFS,
  markScenarioDirty,
  FC_P,
  ALL_P,
  SRC,
  fcArrState,
  fcCostState,
  fcHcState,
  ensureFcHcState,
  seedFcHcFromOpenReqs,
} = sandbox;

if (typeof compute !== "function" || typeof getResults !== "function" || !ALL_P) {
  console.error("FAIL: forecast compute/getResults/ALL_P not available after extract");
  process.exit(1);
}
if (!fcArrState || !fcCostState || typeof markScenarioDirty !== "function") {
  console.error("FAIL: forecast lever state / markScenarioDirty not available after extract");
  process.exit(1);
}
if (!fcHcState || typeof ensureFcHcState !== "function" || typeof seedFcHcFromOpenReqs !== "function") {
  console.error("FAIL: forecast HC state helpers not available after extract");
  process.exit(1);
}

if (SRC && SRC.open_reqs) {
  SRC.open_reqs.forEach((r) => {
    sandbox.reqActive[r.id] = true;
  });
}

/** Levers live in fcArr/fcCost/fcHc state (sidebar DOM may be unmounted); bust results cache. */
function applyScenario(mut) {
  mut();
  markScenarioDirty();
}

function resetLeversAndHires() {
  fcArrState.nb = 100;
  fcArrState.exp = 100;
  fcArrState.churn = 100;
  fcArrState.ren = 0;
  fcCostState.cogs = 29;
  fcCostState.sm = 34;
  fcCostState.rd = 16;
  fcCostState.ga = 11;
  if (SRC && SRC.open_reqs) {
    SRC.open_reqs.forEach((r) => {
      sandbox.reqActive[r.id] = true;
    });
  }
  // Force open-req → HC reseed so prior hire edits / req toggles do not leak.
  fcHcState.hires = null;
  seedFcHcFromOpenReqs(true);
}

function decCash() {
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

resetLeversAndHires();
markScenarioDirty();
const base = {
  cash: decCash(),
  arr: decArr(),
  rd: julRd(),
};

applyScenario(() => {
  fcArrState.nb = 150;
});
const nb = { cash: decCash(), arr: decArr(), rd: julRd() };

// OpEx IS is dept/HC SoT (resolveFcPlOpex) — cost-% rd no longer drives Jul R&D.
applyScenario(() => {
  resetLeversAndHires();
  ensureFcHcState();
  if (!fcHcState.hires["2026-07"]) fcHcState.hires["2026-07"] = {};
  fcHcState.hires["2026-07"].rd = (fcHcState.hires["2026-07"].rd || 0) + 8;
});
const rd = { cash: decCash(), arr: decArr(), rd: julRd() };

// FREQ-001 starts in close month (skipped by HC seed); use Jul R&D open req instead.
applyScenario(() => {
  resetLeversAndHires();
  sandbox.reqActive["FREQ-007"] = false;
  fcHcState.hires = null;
  seedFcHcFromOpenReqs(true);
});
const hc = { cash: decCash(), arr: decArr(), rd: julRd() };

function fmt(n) {
  if (n == null) return "null";
  return "$" + (n / 1e6).toFixed(3) + "M";
}

const checks = [
  ["NB 150% changes Dec ARR", nb.arr !== base.arr],
  ["NB 150% changes Dec cash", nb.cash !== base.cash],
  ["HC +8 Jul R&D hires changes Jul R&D line", rd.rd !== base.rd],
  ["HC +8 Jul R&D hires changes Dec cash", rd.cash !== base.cash],
  ["FREQ-007 off changes Dec cash", hc.cash !== base.cash],
];

console.log("Baseline Dec cash:", fmt(base.cash), "Dec ARR:", fmt(base.arr), "Jul R&D:", fmt(base.rd));
console.log("NB 150%     Dec cash:", fmt(nb.cash), "Dec ARR:", fmt(nb.arr));
console.log("HC R&D+8    Dec cash:", fmt(rd.cash), "Jul R&D:", fmt(rd.rd));
console.log("FREQ-007 off Dec cash:", fmt(hc.cash));

let failed = 0;
for (const [label, ok] of checks) {
  console.log(ok ? "PASS" : "FAIL", "-", label);
  if (!ok) failed++;
}

process.exit(failed ? 1 : 0);
