/**
 * Regression: partial live hydrate must not leave stale demo actuals.
 * Run from frontend/: node scripts/verify-outlook-hydrate.mjs
 */
import fs from "fs";
import path from "path";
import vm from "vm";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outlookPath = path.join(__dirname, "../public/shared/smpl-outlook.js");
const code = fs.readFileSync(outlookPath, "utf8");

const sandbox = {
  console,
  URLSearchParams,
  fetch: async () => ({ ok: false, status: 500, text: async () => "" }),
  addEventListener: () => {},
  removeEventListener: () => {},
  postMessage: () => {},
  location: { origin: "http://localhost", href: "http://localhost/" },
  parent: null,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.global = sandbox;
sandbox.parent = sandbox;
vm.runInNewContext(code, sandbox);

const SMPLOutlook = sandbox.SMPLOutlook;
if (!SMPLOutlook) {
  console.error("FAIL  SMPLOutlook not exported");
  process.exit(1);
}

let failed = 0;
function check(label, ok, detail) {
  console.log((ok ? "OK  " : "FAIL") + "  " + label + (detail ? ": " + detail : ""));
  if (!ok) failed++;
}

// Demo has Jan + Jun Actual; live only sends Jun (partial production hydrate).
const demoTs = {
  Actual: {
    periods: ["2026-01", "2026-06"],
    is: {
      "2026-01": { revenue: 1_000_000, ebitda: -50_000 },
      "2026-06": { revenue: 9_999_999, ebitda: -9_999 },
    },
    bs: {
      "2026-01": { cash: 10_000_000 },
      "2026-06": { cash: 99_999_999 },
    },
    cfs: {
      "2026-01": { ending_cash: 10_000_000 },
      "2026-06": { ending_cash: 99_999_999 },
    },
  },
  Forecast: { periods: [], is: {}, bs: {}, cfs: {} },
  Budget: { periods: [], is: {}, bs: {}, cfs: {} },
};

const liveTs = {
  Actual: {
    periods: ["2026-06"],
    is: {
      "2026-06": { revenue: 7_412_000, ebitda: -1_297_000 },
    },
    bs: {
      "2026-06": { cash: 70_612_000 },
    },
    cfs: {
      "2026-06": { ending_cash: 70_612_000 },
    },
  },
};

const demoSrc = {
  "2026-01": { revenue: 1_000_000, ebitda: -50_000, demo_only: 123 },
  "2026-06": { revenue: 9_999_999, ebitda: -9_999, demo_only: 456 },
};
const liveSrc = {
  "2026-06": { revenue: 7_412_000, ebitda: -1_297_000 },
};

sandbox.SMPL_CLOSE_MONTH = "2026-06";
SMPLOutlook.mergeTsData(demoTs, liveTs, "2026-06");

check(
  "Jun IS revenue replaced by live",
  demoTs.Actual.is["2026-06"].revenue === 7_412_000,
  String(demoTs.Actual.is["2026-06"].revenue)
);
check(
  "Jun IS has no leftover demo-only ebitda mismatch",
  demoTs.Actual.is["2026-06"].ebitda === -1_297_000,
  String(demoTs.Actual.is["2026-06"].ebitda)
);
check(
  "Jan closed Actual pruned when warehouse omitted it",
  demoTs.Actual.is["2026-01"] == null,
  demoTs.Actual.is["2026-01"] == null ? "deleted" : "still present"
);
check(
  "Jan BS pruned",
  demoTs.Actual.bs["2026-01"] == null,
  demoTs.Actual.bs["2026-01"] == null ? "deleted" : "still present"
);

SMPLOutlook.mergeActuals(demoSrc, liveSrc, "2026-06");
check(
  "SRC Jun revenue replaced",
  demoSrc["2026-06"].revenue === 7_412_000,
  String(demoSrc["2026-06"].revenue)
);
check(
  "SRC Jun demo_only field removed (full row replace)",
  demoSrc["2026-06"].demo_only == null,
  String(demoSrc["2026-06"].demo_only)
);
check(
  "SRC Jan closed period pruned",
  demoSrc["2026-01"] == null,
  demoSrc["2026-01"] == null ? "deleted" : "still present"
);

// Empty live Actual must not wipe demo (offline / incomplete warehouse).
const keepDemo = {
  Actual: {
    is: { "2026-06": { revenue: 1 } },
    bs: {},
    cfs: {},
  },
};
SMPLOutlook.mergeTsData(keepDemo, { Actual: { is: {}, bs: {}, cfs: {} } }, "2026-06");
check(
  "Empty live Actual does not prune demo",
  keepDemo.Actual.is["2026-06"] && keepDemo.Actual.is["2026-06"].revenue === 1,
  JSON.stringify(keepDemo.Actual.is["2026-06"])
);

if (failed) {
  console.error("\n" + failed + " hydrate residue check(s) failed.");
  process.exit(1);
}
console.log("\nAll outlook hydrate residue checks passed.");
