/**
 * Smoke: Income Statement and Management P&L are built from one ledger (board-ledger.js).
 *  - No allocation layers → both statements identical on every line and total (spec T08).
 *  - With an allocation layer → revenue, total costs and EBITDA unchanged; cost lines move
 *    by exactly the transfer amount (spec T09).
 *  - Department / GL view sums equal the statement lines.
 *  - Board inline scripts parse.
 * Runs against the embedded demo TS_DATA in public/board/index.html.
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.join(__dirname, "..", "public");
const ledgerCode = fs.readFileSync(path.join(root, "shared", "board-ledger.js"), "utf8");
const html = fs.readFileSync(path.join(root, "board", "index.html"), "utf8");

const failures = [];
function check(name, ok, detail) {
  if (!ok) failures.push(name + (detail !== undefined ? " " + JSON.stringify(detail) : ""));
}
const near = (a, b) => Math.abs(a - b) < 0.01;

const tsStart = html.search(/TS_DATA=\{/);
check("TS_DATA present", tsStart >= 0);
let depth = 0;
let tsEnd = -1;
for (let i = html.indexOf("{", tsStart); i < html.length; i++) {
  if (html[i] === "{") depth++;
  else if (html[i] === "}") {
    depth--;
    if (depth === 0) { tsEnd = i + 1; break; }
  }
}
const TS_DATA = JSON.parse(html.slice(html.indexOf("{", tsStart), tsEnd));

function load(rules) {
  const sandbox = { console, CLOSE_MONTH: "2026-06", TS_DATA, SMPL_ALLOCATION_RULES: rules };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(ledgerCode, sandbox);
  return sandbox.SMPLLedger;
}

const scopes = (L) => [
  ["Actual month", "Actual", L.periodsFor("Actual", "month")],
  ["Actual YTD", "Actual", L.periodsFor("Actual", "ytd")],
  ["Budget month", "Budget", L.periodsFor("Budget", "month")],
  ["Budget YTD", "Budget", L.periodsFor("Budget", "ytd")],
  ["Forecast rest of year", "Forecast", L.periodsFor("Forecast", "rest_of_year")],
];

// T08 — no allocation layers: identical statements.
const L0 = load([]);
check("ledger has actual month", L0.periodsFor("Actual", "month").length === 1);
scopes(L0).forEach(([name, sc, periods]) => {
  const is = L0.rollup("is", sc, periods);
  const mg = L0.rollup("mgmt", sc, periods);
  Object.keys(is.totals).forEach((k) => check(`T08 ${name} ${k}`, near(is.totals[k], mg.totals[k]), [is.totals[k], mg.totals[k]]));
  is.order.forEach((label) => check(`T08 ${name} ${label}`, near(is.lines[label].amount, mg.lines[label].amount)));
  const br = L0.bridge(sc, periods);
  check(`T08 ${name} bridge identical`, br.ok && br.rows.every((r) => r.status === "identical"), br.rows);
});

// Ledger IS equals the source statement values.
const jun = TS_DATA.Actual.is["2026-06"];
["revenue", "cogs", "sm", "rd", "ga", "ebitda"].forEach((k) => {
  if (jun[k] != null) check(`IS ${k} = source`, near(L0.isValue("Actual", "2026-06", k), jun[k]), [L0.isValue("Actual", "2026-06", k), jun[k]]);
});

// Management P&L rows and department view agree with the ledger.
const mpl = L0.managementPl();
const ebitdaRow = mpl.find((r) => r.label === "EBITDA");
const junIs = L0.rollup("is", "Actual", ["2026-06"]);
const nearM = (m, dollars) => Math.abs(m * 1e6 - dollars) <= 1;
check("MPL EBITDA = IS EBITDA", nearM(ebitdaRow.a, junIs.totals.ebitda), [ebitdaRow.a, junIs.totals.ebitda]);
const depts = L0.byDepartment();
const deptSum = depts.reduce((s, d) => s + (d.a || 0), 0);
check("Dept sum = IS total costs", nearM(deptSum, junIs.totals.cogs + junIs.totals.opex), [deptSum, junIs.totals.cogs + junIs.totals.opex]);
const smDept = depts.find((d) => d.dept === "Sales & Marketing");
const paid = smDept && smDept.accounts.find((r) => r.name === "Paid Search");
const programs = smDept && smDept.accounts.find((r) => r.name === "Total Channel Spend");
const marketingOrder = [];
let marketing = false;
(smDept ? smDept.accounts : []).forEach((r) => {
  if (r.kind === "group") marketing = r.name === "Marketing";
  if (marketing) marketingOrder.push(r.name);
});
const at = (name) => marketingOrder.indexOf(name);
check("Marketing lists labor, then channel spend, then discretionary, then the department total", at("Labor costs") > at("Base Salaries") && at("Total Channel Spend") > at("Labor costs") && at("Paid Search") > at("Labor costs") && at("Discretionary spend") > at("Total Channel Spend") && at("Total Marketing") > at("Discretionary spend"));
check("Labor follows the chart, with each account still on its own row", at("Bonuses") > at("Base Salaries") && at("Payroll Taxes") > at("Bonuses") && at("Employee Benefits") > at("Payroll Taxes") && at("Stock-Based Compensation") > at("Employee Benefits") && at("Labor costs") > at("Stock-Based Compensation"));
const base = smDept.accounts.find((r) => r.name === "Base Salaries");
check("Base salaries show account 6100 in its own field", base && base.number === "6100");
const rd = depts.find((d) => d.dept === "R&D");
const eng = [];
let inEng = false;
(rd ? rd.accounts : []).forEach((r) => {
  if (r.kind === "group") inEng = r.name === "Engineering";
  if (r.kind === "total" && inEng) inEng = false;
  if (inEng) eng.push(r.name);
});
check("Engineering keeps severance with labor and contractor spend with discretionary", eng.indexOf("Severance") > eng.indexOf("Base Salaries") && eng.indexOf("Severance") < eng.indexOf("Labor costs") && eng.indexOf("Contractor Labor") > eng.indexOf("Labor costs") && eng.indexOf("Discretionary spend") > eng.indexOf("Contractor Labor"));
const salesOrder = [];
let sales = false;
(smDept ? smDept.accounts : []).forEach((r) => {
  if (r.kind === "group") sales = r.name === "Sales";
  if (sales) salesOrder.push(r.name);
});
check("Sales keeps commissions with labor, then discretionary, then the department total", salesOrder.indexOf("Sales Commissions") > salesOrder.indexOf("Stock-Based Compensation") && salesOrder.indexOf("Labor costs") > salesOrder.indexOf("Sales Commissions") && salesOrder.indexOf("Discretionary spend") > salesOrder.indexOf("Labor costs") && salesOrder.indexOf("Total Sales") > salesOrder.indexOf("Discretionary spend"));
const programDollars = Object.keys(TS_DATA.Actual.gl_programs["2026-06"]).filter((k) => k.startsWith("sm|")).reduce((s, k) => s + TS_DATA.Actual.gl_programs["2026-06"][k], 0);
const leafSum = smDept.accounts.filter((r) => r.kind === "account").reduce((s, r) => s + (r.a || 0), 0);
check("S&M opens to GL accounts", smDept && smDept.detail && paid && paid.program);
check("Marketing programs match the GL program accounts", programs && nearM(programs.a, programDollars), [programs && programs.a, programDollars]);
check("S&M accounts foot to the statement line", near(leafSum, smDept.a), [leafSum, smDept.a]);
check("P&L summary keeps one Sales & Marketing row", mpl.filter((r) => r.label === "Sales & Marketing").length === 1 && mpl.find((r) => r.label === "Sales & Marketing").accounts.length === 1);

// T09 — allocation layer moves cost only.
const L1 = load([
  { id: "hosting", label: "Hosting share to COGS", from: "Research & Development", to: "Cost of Revenue", pct: 0.1 },
  { id: "facilities", label: "Facilities to S&M", from: "General & Administrative", to: "Sales & Marketing", amounts: { Actual: { "2026-06": 50000 } } },
]);
scopes(L1).forEach(([name, sc, periods]) => {
  const is = L1.rollup("is", sc, periods);
  const mg = L1.rollup("mgmt", sc, periods);
  check(`T09 ${name} revenue`, near(is.totals.revenue, mg.totals.revenue));
  check(`T09 ${name} total costs`, near(is.totals.cogs + is.totals.opex, mg.totals.cogs + mg.totals.opex));
  check(`T09 ${name} EBITDA`, near(is.totals.ebitda, mg.totals.ebitda));
  const moved = mg.transfers.reduce((s, t) => s + (t.from === "Research & Development" ? t.amount : 0), 0);
  check(`T09 ${name} R&D moved by transfers`, near(is.lines["Research & Development"].amount - mg.lines["Research & Development"].amount, moved));
  const br = L1.bridge(sc, periods);
  check(`T09 ${name} bridge explained`, br.ok, br.rows);
});
const junMg = L1.rollup("mgmt", "Actual", ["2026-06"]);
check("T09 fixed amount applied", junMg.transfers.some((t) => t.id === "facilities" && near(t.amount, 50000)));
check("T09 revenue lines never allocated", load([{ id: "x", from: "Subscription Revenue", to: "Services Revenue", pct: 0.5 }]).rollup("mgmt", "Actual", ["2026-06"]).transfers.length === 0);

// Inline board scripts parse.
const scriptRe = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi;
let m;
let n = 0;
while ((m = scriptRe.exec(html))) {
  n++;
  try { new vm.Script(m[1], { filename: `board-inline-${n}.js` }); }
  catch (e) { check(`inline script ${n} parses`, false, e.message); }
}

if (failures.length) {
  console.error("FAIL\n  " + failures.join("\n  "));
  process.exit(1);
}
console.log(`ok board ledger: IS and Mgmt P&L identical with no allocation layers; allocations move cost only; ${n} inline scripts parse`);
