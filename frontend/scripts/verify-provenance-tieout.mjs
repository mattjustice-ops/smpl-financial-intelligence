/**
 * Regression: DOM provenance helpers + client A–F runTieOut / HTML report / publish gate.
 * Run from frontend/: node scripts/verify-provenance-tieout.mjs
 */
import fs from "fs";
import path from "path";
import vm from "vm";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const provPath = path.join(__dirname, "../public/shared/smpl-provenance.js");
const code = fs.readFileSync(provPath, "utf8");

const fakeEls = [];
function makeEl(attrs) {
  const a = Object.assign({}, attrs || {});
  const el = {
    attributes: a,
    getAttribute(k) {
      return a[k] != null ? a[k] : null;
    },
    setAttribute(k, v) {
      a[k] = String(v);
    },
    classList: { contains: () => false },
    parentNode: null,
    nextSibling: null,
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    },
  };
  fakeEls.push(el);
  return el;
}

const kpiVal = makeEl({});
const kpiLbl = {
  textContent: "Ending ARR",
  getAttribute: () => null,
  setAttribute: () => {},
};
const kpi = {
  querySelector(sel) {
    if (sel === ".kpi-lbl") return kpiLbl;
    if (sel === ".kpi-val") return kpiVal;
    return null;
  },
};

const sandbox = {
  console,
  document: {
    body: {
      classList: {
        _on: false,
        toggle(name) {
          this._on = !this._on;
          return this._on;
        },
        remove() {
          this._on = false;
        },
        add() {
          this._on = true;
        },
      },
    },
    readyState: "complete",
    addEventListener() {},
    querySelectorAll(sel) {
      if (sel === ".kpi") return [kpi];
      if (sel === "[data-metric]") return kpiVal.getAttribute("data-metric") ? [kpiVal] : [];
      if (sel === "[data-source]") return kpiVal.getAttribute("data-source") ? [kpiVal] : [];
      if (sel === ".smpl-audit-tag") return [];
      return [];
    },
  },
  addEventListener() {},
  window: null,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.global = sandbox;
vm.runInNewContext(code, sandbox);

const P = sandbox.SMPLProvenance;
if (!P) {
  console.error("FAIL  SMPLProvenance not exported");
  process.exit(1);
}

let failed = 0;
function check(label, ok, detail) {
  console.log((ok ? "OK  " : "FAIL") + "  " + label + (detail ? ": " + detail : ""));
  if (!ok) failed++;
}

check("runTieOut alias", typeof sandbox.runTieOut === "function");

const attr = P.attrString("ending_arr", "2026-06");
check(
  "attrString ending_arr",
  attr.includes('data-source="arr_waterfall.ending_arr"') && attr.includes('data-period="2026-06"'),
  attr.slice(0, 120),
);

const gm = P.attrString("gross_margin_pct");
check("attrString COMPUTED gm", gm.includes("COMPUTED:gross_profit_div_revenue"), gm.slice(0, 100));

P.ingestOutlook({
  _sources: {
    "ts.Actual.is.2026-06.revenue": {
      source_type: "WAREHOUSE",
      table: "income_statement",
      column: "revenue",
      period: "2026-06",
      path: "ts.Actual.is.2026-06.revenue",
    },
  },
});
const fromPayload = P.attrString("revenue", "2026-06");
check(
  "prefers payload _sources",
  fromPayload.includes("income_statement.revenue"),
  fromPayload.slice(0, 120),
);

const n = P.annotateDom(sandbox.document);
check("annotateDom tags kpi-val", n >= 1 && kpiVal.getAttribute("data-source") === "arr_waterfall.ending_arr");

// Aligned TS ↔ SRC + WF + identities → pass
sandbox.SMPL_CLOSE_MONTH = "2026-06";
sandbox.SMPL_ARR_WATERFALL = {
  Beginning: [1000, 1135],
  "New Business": [100, 0],
  Expansion: [50, 0],
  Reactivation: [0, 0],
  Contraction: [-10, 0],
  Churn: [-5, 0],
  Ending: [1135, 1135],
};
sandbox.SMPL_OUTLOOK_PAYLOAD = {
  meta: { close_month: "2026-06" },
  TS_DATA: {
    Actual: {
      is: {
        "2026-06": {
          revenue: 1000,
          cogs: 200,
          gross_profit: 800,
          sm: 300,
          rd: 200,
          ga: 100,
          ebitda: 200,
          net_income: 150,
        },
      },
      bs: { "2026-06": { cash: 5000, ar: 100, deferred_rev: 50 } },
      cfs: {
        "2026-05": { ending_cash: 4000, beginning_cash: 3500, cfo: 500 },
        "2026-06": {
          beginning_cash: 4000,
          ending_cash: 5000,
          cfo: 1000,
          net_income: 150,
          da: 50,
          sbc: 20,
          chg_ar: 400,
          chg_dr: 300,
          chg_ap: 100,
          chg_prepaids: -20,
        },
      },
    },
    Forecast: {
      is: { "2026-07": { revenue: 1200, gross_profit: 900, ebitda: 250, net_income: 200 } },
      cfs: { "2026-07": { beginning_cash: 5000, ending_cash: 5200 } },
    },
  },
  SRC: {
    actuals: {
      "2026-06": {
        revenue: 1000,
        cogs: 200,
        gross_profit: 800,
        sm: 300,
        rd: 200,
        ga: 100,
        ebitda: 200,
        net_income: 150,
        cash: 5000,
        ar: 100,
        deferred_rev: 50,
        ending_cash: 5000,
        beginning_cash: 4000,
        cfo: 1000,
        arr_nb: 100,
        arr_exp: 50,
        arr_react: 0,
        arr_cont: -10,
        arr_churn: -5,
        arr_nn: 135,
        arr_bop: 1000,
        arr_eop: 1135,
      },
    },
  },
  baseline_engine: {
    "2026-07": {
      arr: { arr_bop: 1135, arr_eop: 14400 },
      is: { revenue: 1200, gross_profit: 900, ebitda: 250, net_income: 200 },
      cfs: { beg_cash: 5000, end_cash: 5200 },
    },
  },
};
sandbox.SMPL_LIVE_OUTLOOK = true;
const pass = P.runTieOut();
check("runTieOut aligned pass", pass.passed === true, JSON.stringify(pass.failures));
check(
  "runTieOut scope client-A-F",
  pass.scope === "client-A-F" && (pass.checksRun || []).includes("C1"),
  JSON.stringify(pass.checksRun),
);
const html = P.renderTieOutReportHtml(pass);
check(
  "HTML tie-out report",
  typeof html === "string" && html.includes("Client Data Tie-Out Report") && html.includes("APPROVED"),
);

// Divergence > $1 → fail
sandbox.SMPL_OUTLOOK_PAYLOAD.SRC.actuals["2026-06"].revenue = 1050;
const fail = P.runTieOut();
check("runTieOut miss fails", fail.passed === false && fail.failures.some((f) => f.includes("revenue")));
check(
  "HTML report on fail",
  (P.getLastTieOutHtml() || "").includes("BLOCKED"),
);

const gateLive = P.gatePublish({ closeMonth: "2026-06", downloadReport: false });
check("gatePublish live FAIL blocks", gateLive.blocked === true && gateLive.ok === false);
check("gatePublish attaches reportHtml", typeof gateLive.reportHtml === "string" && gateLive.reportHtml.length > 50);

sandbox.SMPL_LIVE_OUTLOOK = false;
const gateDemo = P.gatePublish({ closeMonth: "2026-06", downloadReport: false });
check("gatePublish demo FAIL warns only", gateDemo.blocked === false && gateDemo.ok === true);

if (failed) {
  console.error("\n" + failed + " check(s) failed");
  process.exit(1);
}
console.log("\nAll provenance / tie-out checks passed");
