import fs from "node:fs";
import vm from "node:vm";

const code = fs.readFileSync(new URL("../public/shared/board-commentary.js", import.meta.url), "utf8");
const context = { console };
context.window = context;
context.globalThis = context;
vm.createContext(context);
vm.runInContext(code, context);
const api = context.SMPLReportFormat;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const merged = api.mergedLabel("Engineering · Cloud Hosting · Cloud Hosting COGS");
assert(merged.text === "Engineering · Cloud Hosting COGS", merged.text);
assert(merged.title === "Engineering › Cloud Hosting › Cloud Hosting COGS", merged.title);
assert(
  api.sentenceLabel("Engineering · Cloud Hosting · Cloud Hosting COGS", true) === "Cloud Hosting COGS in Engineering",
  api.sentenceLabel("Engineering · Cloud Hosting · Cloud Hosting COGS", true)
);
assert(
  api.sentenceLabel("Product · Vendor Expense · Third Party Product Fees COGS", false) === "Third Party Product Fees COGS in Product",
  "product sentence"
);

const cogs = {
  label: "Cost of revenue",
  variance: 4560.87,
  comparison_amount: 1080108.46,
  drivers: [
    { label: "Engineering · Cloud Hosting · Cloud Hosting COGS", variance: 3811 },
    { label: "Product · Vendor Expense · Third Party Product Fees COGS", variance: 750 },
  ],
};
const text = api.reportParagraph(cogs, "May 2026");
assert(!/\d\.\d{2}\b/.test(text), "cents in " + text);
assert(text.includes("rose 4,561 (0.4%) vs May 2026"), text);
assert(text.includes("higher Cloud Hosting COGS in Engineering (+3,811)"), text);
assert(text.includes("higher Third Party Product Fees COGS in Product (+750)"), text);
assert(!text.includes(" · "), text);
assert(api.uncitedDrivers(text, cogs.drivers).length === 0, "paragraph should tie");
const dropped = text.replace("(+750)", "(+0)");
assert(api.uncitedDrivers(dropped, cogs.drivers).length === 1, "a missing driver does not tie");

assert(api.favorText({ variance: 4561, signLine: "cogs" }) === "▼ Unfav", "cost of revenue");
assert(api.favorText({ variance: 3811, signLine: "cogs" }) === "▼ Unfav", "cloud hosting");
assert(api.favorText({ variance: 750, signLine: "cogs" }) === "▼ Unfav", "product fees");
assert(api.favorText({ variance: 0.2, signLine: "cogs" }) === "", "zero variance");
assert(api.favorText({ variance: 100, signLine: "revenue" }) === "▲ Fav", "revenue");

const hosting = {
  label: "Cloud Hosting",
  variance: 3811,
  comparison_amount: 10000,
  vendor: "Northwind",
  drivers: [],
};
const hostingText = api.reportParagraph(hosting, "May 2026");
assert(hostingText.includes("on Northwind"), hostingText);
assert(!hostingText.includes("because"), hostingText);

const cloud = api.reportParagraph({
  label: "Cloud hosting",
  variance: 12000,
  comparison_amount: 100000,
  drivers: [],
  facts: [
    { label: "compute hours", current: 1200, base: 800 },
    { label: "storage GB", current: 400, base: 400 },
  ],
}, "May 2026");
assert(cloud.includes("rose 12,000"), cloud);
assert(cloud.includes("Compute hours rose from 800 to 1,200"), cloud);
assert(cloud.includes("storage GB was unchanged"), cloud);
assert(!cloud.includes("because"), cloud);

const bareCloud = api.reportParagraph({
  label: "Cloud hosting",
  variance: 12000,
  comparison_amount: 100000,
  drivers: [],
}, "May 2026");
assert(bareCloud.includes("rose 12,000"), bareCloud);
assert(!/compute|storage|usage|because/i.test(bareCloud), bareCloud);

const salaries = api.reportParagraph({
  label: "Compensation",
  variance: 10000,
  comparison_amount: 70000,
  drivers: [],
  facts: [
    { label: "Hires", amount: 12000, heads: 2 },
    { label: "Departures", amount: -3000, heads: 1 },
    { label: "GL reconciling", amount: 1000 },
  ],
}, "May 2026");
assert(salaries.includes("Hires +$12.00k (2 people)"), salaries);
assert(salaries.includes("Departures −$3.00k (1 person)"), salaries);
assert(salaries.includes("GL reconciling +$1.00k"), salaries);
assert(!salaries.includes("because"), salaries);

const counted = api.reportParagraph({
  label: "Implementation & Onboarding",
  variance: -40000,
  comparison_amount: 90000,
  facts: [
    { label: "implementations", current: 4, base: 8 },
    { label: "size of each implementation", current: 5000, base: 7000 },
  ],
}, "May 2026");
assert(counted.includes("Implementations fell from 8 to 4"), counted);
assert(counted.includes("size of each implementation fell from $7.00k to $5.00k"), counted);
assert(!counted.includes("because"), counted);

const deals = api.reportParagraph({
  label: "Subscription Revenue",
  lineKey: "sub_rev",
  variance: 10000,
  comparison_amount: 50000,
  drivers: [{ label: "Closed deal", variance: 10000, role: "opportunity", linked: false }],
}, "May 2026");
assert(!deals.includes("Closed deal"), deals);

const headcount = api.reportParagraph({
  label: "Base Salaries",
  variance: 3125,
  comparison_amount: 533750,
  drivers: [],
  facts: [
    { label: "employees", current: 52, base: 51 },
    { label: "average salary", current: 10324, base: 10466 },
    { label: "hires", current: 1, base: 0 },
    { label: "departures", current: 0, base: 0 },
  ],
}, "May 2026");
assert(headcount.includes("Employees rose from 51 to 52"), headcount);
assert(headcount.includes("average salary fell from $10.47k to $10.32k"), headcount);
assert(headcount.includes("hires rose from 0 to 1"), headcount);
assert(headcount.includes("departures was unchanged"), headcount);
assert(!headcount.includes("because"), headcount);

const subscription = api.reportParagraph({
  label: "Subscription Revenue",
  variance: 320909,
  comparison_amount: 6325455,
  drivers: [],
  facts: [
    { label: "customers", current: 756, base: 745 },
    { label: "average subscription revenue", current: 8791, base: 8491 },
    { label: "customers added", current: 13, base: 11 },
    { label: "customers ended", current: 2, base: 4 },
  ],
}, "May 2026");
assert(subscription.includes("Customers rose from 745 to 756"), subscription);
assert(subscription.includes("average subscription revenue rose from $8.49k to $8.79k"), subscription);
assert(subscription.includes("customers added rose from 11 to 13"), subscription);
assert(subscription.includes("customers ended fell from 4 to 2"), subscription);

const start = code.indexOf("function renderReport");
const end = code.indexOf("function saveReportEdit");
const grid = code.slice(start, end);
assert(!/label\s*===|label\s*==(?!=)/.test(grid), "grid compares a label to a string");
assert(grid.includes("$ Variance") && grid.includes("Fav/Unfav") && grid.includes(">Tied<"), "variance splits into dollars, percent, favor, and a Tied column");
assert(!grid.includes("Comfortable") && !grid.includes("data-about"), "info and density controls are gone");
assert(!grid.includes("✓ Ties"), "the tie mark is not repeated in the commentary footer");
assert(code.includes("/commentary/revenue-rollup"), "revenue roll-up asks for analysis");
assert(code.includes("revenueHeld"), "a loaded revenue analysis is kept when the comparison changes");
assert(code.includes("data-revenue-draft"), "the revenue row can draft the analysis again");
assert(code.includes("Updating commentary"), "a draft says commentary is updating");
assert(code.includes("if (again) render(host)"), "clicking AI draft redraws before the reply");
const loadingAt = code.indexOf('current.status === "loading"');
const heldAt = code.indexOf('held.status === "ai"');
assert(loadingAt > 0 && heldAt > loadingAt, "a draft in progress is not replaced by the saved paragraph");
assert(code.includes("Writing the analysis into the workbook"), "variance commentary shows that the workbook is being written");
assert(code.includes('["Go to market", "gtm"]'), "executive discussion includes go to market");
assert(code.includes("monthRead(item, host)"), "executive discussion reads themes instead of every line");
assert(code.includes("boardDiscussionNarrative"), "discussion sections follow the selected comparison");
assert(code.includes("On the balance sheet"), "the month gathers the balance sheet into one paragraph");
const monthFn = code.slice(code.indexOf("function proseLine"), code.indexOf("function zipNodes"));
assert(monthFn.includes("moneyPhrase") && !monthFn.includes("reportParagraph") && !monthFn.includes("row.commentary"), "the month uses one money voice");
assert(monthFn.includes("outperformed") && monthFn.includes("partly offset") && monthFn.includes("largely offset"), "the month uses the verb lexicon and names both sides of an offset");
assert(monthFn.includes("was largely flat") && monthFn.includes("driven by") && monthFn.includes("(up ") && !monthFn.includes("of which") && !monthFn.includes(", on "), "the month leads with the move and names a component once");
assert(monthFn.includes("periods[periods.length - 1]") || code.includes("key === \"ending_cash\""), "a balance uses the period-end figure");
assert(code.includes('options.mode === "read"'), "read mode does not print an internal tie note");
assert(code.includes("boardGtmSummary(windowFor(comparison()))"), "go to market follows the selected comparison");
assert(api.moneyPhrase(7400000) === "$7.40m", api.moneyPhrase(7400000));
assert(api.moneyPhrase(94650) === "$94.65k", api.moneyPhrase(94650));
assert(api.moneyPhrase(868) === "$868.00", api.moneyPhrase(868));
assert(code.includes('ebitda: [["gross_profit", 1], ["total_opex", -1]]'), "EBITDA is explained from gross profit and operating expenses");
assert(code.includes('pretax: [["op_income", 1], ["interest", -1]]'), "pretax income is explained from operating income and interest");
assert(code.includes("ebitda: 1, da: 1, interest: 1, pretax: 1"), "EBITDA and pretax income can take an AI draft");
assert(code.includes("draftSectionId"), "a department row can draft its section");
assert(!code.includes(">Calculated<"), "the revenue comment is the analysis paragraph");
assert(code.includes("history.gl_rollup"), "year-over-year and year-to-date read the prior-year accounts");
assert(!grid.includes("Current, USD"), "period columns follow the selected comparison");
assert(api.columnHeads({ id: "mom", current: ["2026-06"], base: ["2026-05"] }).current === "Jun 26", "mom current");
assert(api.columnHeads({ id: "mom", current: ["2026-06"], base: ["2026-05"] }).base === "May 26", "mom base");
assert(api.columnHeads({ id: "qoq", current: ["2026-04", "2026-05", "2026-06"], base: ["2026-01", "2026-02", "2026-03"] }).current === "Q2 26", "qoq current");
assert(api.columnHeads({ id: "qoq", current: ["2026-04", "2026-05", "2026-06"], base: ["2026-01", "2026-02", "2026-03"] }).base === "Q1 26", "qoq base");
assert(api.columnHeads({ id: "yoy", current: ["2026-06"], base: ["2025-06"] }).base === "Jun 25", "yoy base");
assert(api.columnHeads({ id: "ytd", current: ["2026-01", "2026-06"], base: ["2025-01", "2025-06"] }).current === "YTD Jun 2026", "ytd current");
assert(api.columnHeads({ id: "ytd", current: ["2026-01", "2026-06"], base: ["2025-01", "2025-06"] }).base === "YTD Jun 2025", "ytd base");
assert(api.columnHeads({ id: "budget", current: ["2026-06"], base: ["2026-06"] }).base === "Budget", "budget column");
assert(api.columnHeads({ id: "forecast", current: ["2026-06"], base: ["2026-06"] }).base === "Forecast", "forecast column");

const periodFacts = api.foldPeriodMeasures([
  [
    { label: "customers", value: 745 },
    { label: "average subscription revenue", value: 8490.54 },
    { label: "customers added", value: 13 },
    { label: "implementations", value: 8 },
    { label: "average implementation fee", value: 3500 },
    { label: "compute hours", value: 100 },
  ],
  [
    { label: "customers", value: 756 },
    { label: "average subscription revenue", value: 8791.49 },
    { label: "customers added", value: 11 },
    { label: "implementations", value: 5 },
    { label: "average implementation fee", value: 3250 },
    { label: "compute hours", value: 140 },
  ],
]);
function factValue(label) {
  const found = periodFacts.find(function (fact) { return fact.label === label; });
  return found ? found.value : null;
}
assert(factValue("customers") === 756, "ending customers stay the last month");
assert(factValue("customers added") === 24, "added customers add across the period");
assert(factValue("implementations") === 13, "implementations add across the period");
assert(factValue("average implementation fee") === 3403.85, "fee is the period average");
assert(factValue("compute hours") === null, "a usage measure is not invented for the period");
assert(api.foldPeriodMeasures([[{ label: "compute hours", value: 100 }]])[0].value === 100, "one month keeps its usage");
const gap = api.foldPeriodMeasures([
  [{ label: "implementations", value: 8 }, { label: "average implementation fee", value: 3500 }],
  [{ label: "customers", value: 756 }],
]);
assert(!gap.some(function (fact) { return fact.label === "implementations"; }), "a missing month drops the period count");

const hydrateCode = fs.readFileSync(new URL("../public/shared/board-hydrate.js", import.meta.url), "utf8");
const dataCode = fs.readFileSync(new URL("../public/shared/board-data.js", import.meta.url), "utf8");
function wfSlot(may, jun, december) {
  const row = Array(12).fill(0);
  row[4] = may;
  row[5] = jun;
  if (december != null) row[11] = december;
  return row;
}
const board = {
  console,
  document: {
    getElementById() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement() { return { style: {}, appendChild() {}, click() {} }; },
    body: { appendChild() {} },
  },
  localStorage: { getItem() { return null; } },
  addEventListener() {},
  setTimeout() {},
  CLOSE_MONTH: "2026-06",
  TS_DATA: {
    Actual: {
      periods: ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"],
      is: {
        "2026-05": { revenue: 7300000, sub_rev: 6600000, gross_profit: 6220000, total_opex: 1000000, ebitda: 981000 },
        "2026-06": { revenue: 7400000, sub_rev: 6710000, gross_profit: 6310000, total_opex: 1086540, ebitda: 984460 },
      },
      bs: { "2026-05": { cash: 28312527 }, "2026-06": { cash: 30000000 } },
    },
    Budget: {
      is: { "2026-06": { revenue: 6570000, gross_profit: 5400000, ebitda: 146000 } },
      bs: { "2026-06": { cash: 26100000 } },
    },
  },
  SMPL_DEMO_WF_TABLE: {
    Beginning: wfSlot(80000000, 81000000, 0),
    "New Business": wfSlot(937100, 741380, 0),
    Expansion: wfSlot(400000, 518000, 0),
    Reactivation: wfSlot(0, 0, 0),
    Contraction: wfSlot(0, 0, 0),
    Churn: wfSlot(-20000, -13090, 0),
    Beginning: wfSlot(82000000, 80473710, 0),
    Ending: wfSlot(82000000, 81720000, 89800000),
    Budget_Beginning: wfSlot(0, 82574000, 0),
    Budget_Ending: wfSlot(84000000, 84900000, 96100000),
    Budget_New_Business: wfSlot(0, 2100000, 0),
    Budget_Expansion: wfSlot(0, 772000, 0),
    Budget_Reactivation: wfSlot(0, 0, 0),
    Budget_Contraction: wfSlot(0, 0, 0),
    Budget_Churn: wfSlot(0, -546000, 0),
  },
  SMPL_CASH_BRIDGE: { Actual: { "2026-06": { collections: 6800000 } } },
  SMPL_DEMO_RETENTION: { Actual: { "2026-06": { nrr: 1.007 } } },
  WF_DEMO: {
    heads_total: [210, 212, 214, 216, 220, 222],
    heads_budget_total: [231, 231, 231, 231, 231, 231],
  },
  ARR_PER_EMP: [359, 360, 362, 364, 366, 368],
};
board.window = board;
board.globalThis = board;
vm.createContext(board);
vm.runInContext(dataCode, board);
vm.runInContext(hydrateCode, board);
const mom = { id: "mom", current: ["2026-06"], base: ["2026-05"], scenario: "Actual" };
const budgetWin = { id: "budget", current: ["2026-06"], base: ["2026-06"], scenario: "Budget" };
const arrMom = board.boardDiscussionNarrative("arr", mom);
const marginMom = board.boardDiscussionNarrative("revenue", mom);
const cashMom = board.boardDiscussionNarrative("cash", mom);
const peopleMom = board.boardDiscussionNarrative("headcount", mom);
const takeMom = board.boardDiscussionNarrative("risks", mom);
const arrBudget = board.boardDiscussionNarrative("arr", budgetWin);
assert(arrMom.includes("Ending ARR was $81.72m, down $280.00k from $82.00m in May 2026"), arrMom);
assert(!arrMom.includes("That ending change equals"), arrMom);
assert(arrMom.includes("New business was $741.38k"), arrMom);
assert(arrMom.includes("Churn was $13.09k"), arrMom);
assert(arrMom.includes("Net dollar retention in Jun 2026 was 100.7%"), arrMom);
assert(!arrMom.includes("budget") && !arrMom.includes("Board priorities") && !arrMom.includes("driven by"), arrMom);
assert(marginMom.includes("Gross margin was 85.3% in Jun 2026 on revenue of $7.40m"), marginMom);
assert(marginMom.includes("6 bps above 85.2% on $7.30m in May 2026"), marginMom);
assert(marginMom.includes("Subscription revenue was $6.71m, up $110.00k from $6.60m in May 2026"), marginMom);
assert(marginMom.includes("Gross profit was $6.31m, up $90.00k from $6.22m in May 2026"), marginMom);
assert(marginMom.includes("Operating expenses were $1.09m, up $86.54k from $1.00m in May 2026"), marginMom);
assert(marginMom.includes("EBITDA was $984.46k, up $3.46k from $981.00k in May 2026"), marginMom);
assert(!marginMom.includes("driving"), marginMom);
assert(cashMom.includes("Ending cash was $30.00m, up $1.69m from $28.31m in May 2026"), cashMom);
assert(cashMom.includes("Collections were $6.80m"), cashMom);
assert(peopleMom.includes("Headcount was 222 in Jun 2026, from 220 in May 2026"), peopleMom);
assert(peopleMom.includes("ARR per employee was $368.00k, from $359.00k in January"), peopleMom);
assert(takeMom.startsWith("Jun 2026 compared with May 2026."), takeMom);
assert(!takeMom.includes("Board priorities") && !takeMom.includes("vs bud"), takeMom);
assert(arrBudget.includes("Ending ARR was $81.72m, $3.18m below the budget of $84.90m"), arrBudget);
assert(arrBudget.includes("The opening balance was $2.10m below its budget, and net new ARR in Jun 2026 was $1.08m below its budget."), arrBudget);
assert(arrBudget.includes("New Business was $741.38k, $1.36m below a budget of $2.10m"), arrBudget);
assert(arrBudget.includes("Churn was $13.09k, $532.91k under a budget of $546.00k"), arrBudget);
assert(!arrBudget.includes("driven by"), arrBudget);
assert(arrBudget.includes("The year-end ARR forecast is $89.80m, $6.30m below a budget of $96.10m"), arrBudget);

console.log("ok");
