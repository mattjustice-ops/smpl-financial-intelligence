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
assert(code.includes("heldAnalyses"), "the workbook export sends the accepted analysis");
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

console.log("ok");
