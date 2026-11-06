/**
 * Tie-out items have to name a step the user can take, or stay in the calculation.
 * Run from frontend/: node scripts/verify-tie-clearance.mjs
 */
import fs from "fs";
import path from "path";
import vm from "vm";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const code = fs.readFileSync(path.join(__dirname, "../public/shared/board-continuity.js"), "utf8");
const sandbox = { console };
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const tieClearance = sandbox.SMPLContinuity.tieClearance;

let failed = 0;
function check(name, ok, detail) {
  if (ok) console.log("OK   ", name);
  else {
    failed++;
    console.error("FAIL ", name, detail || "");
  }
}

const open = [{ status: "open", account_number: "6105", name: "AI Infrastructure", amount: 42500 }];

const b5 = [{ rule: "B5", period: "2026-01", metric: "CFO identity", expected: -468235, actual: -183463 }];
const bare = tieClearance(b5, [], []);
check("operating cash with mapping clear stays in the calculation", bare.you.length === 0 && bare.calc.length === 1, JSON.stringify(bare));
check(
  "calculation copy says there is nothing to edit",
  bare.calc[0] && bare.calc[0].how.includes("no amount"),
  bare.calc[0] && bare.calc[0].how,
);

const mapped = tieClearance(b5, [], open);
check("open accounts turn a statement miss into mapping", mapped.you.length === 1 && mapped.you[0].go === "mapping", JSON.stringify(mapped.you));

const imported = [
  { rule: "C3", period: "2026-06", metric: "revenue", expected: 100, actual: 80 },
];
const src = tieClearance(imported, [], []);
check("imported amount is the user's import", src.you.length === 1 && src.you[0].go === "import", JSON.stringify(src.you));
check(
  "the statement is the number that has to hold",
  src.you[0].rows[0].hold === 80 && src.you[0].rows[0].other === 100,
  JSON.stringify(src.you[0].rows[0]),
);

const both = tieClearance(imported, [], open);
check("an import miss with open accounts offers both steps", both.you[0] && both.you[0].go === "both", JSON.stringify(both.you));

const waterfall = [{ rule: "A3", period: "2026-06", metric: "arr ending=bop+nn", expected: 1135, actual: 1200 }];
const arr = tieClearance(waterfall, [], []);
check("a waterfall that does not add up goes to import", arr.you[0] && arr.you[0].go === "import", JSON.stringify(arr.you));

const forecast = [{ code: "C5", period: "2026-07", scenario: "Forecast", left: 10, right: 12 }];
const fc = tieClearance([], forecast, []);
check("forecast opening cash stays in the calculation", fc.you.length === 0 && fc.calc.length === 1, JSON.stringify(fc));
check("last closed cash is the number that has to hold", fc.calc[0].rows[0].hold === 12 && fc.calc[0].rows[0].other === 10, JSON.stringify(fc.calc[0].rows));

const bridge = [{ code: "C4", period: "2026-01", scenario: "Budget", left: 22135483, right: 22269818 }];
const budgetBridge = tieClearance([], bridge, open);
check(
  "a budget bridge miss is not the mapping queue",
  budgetBridge.you.length === 0 && budgetBridge.calc.length === 1 && budgetBridge.calc[0].go == null,
  JSON.stringify(budgetBridge),
);
check(
  "ending cash is the statement and the other number is the bridge total",
  budgetBridge.calc[0].holdLabel === "Ending cash" &&
    budgetBridge.calc[0].otherLabel === "Bridge total" &&
    budgetBridge.calc[0].rows[0].hold === 22269818 &&
    budgetBridge.calc[0].rows[0].other === 22135483,
  JSON.stringify(budgetBridge.calc[0]),
);

const clear = tieClearance([], [], []);
check("a clean close has nothing to clear", clear.you.length === 0 && clear.calc.length === 0);

if (failed) {
  console.error("\n" + failed + " check(s) failed");
  process.exit(1);
}
console.log("\nAll tie-clearance checks passed");
