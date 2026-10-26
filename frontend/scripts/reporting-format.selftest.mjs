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

const asked = api.reportParagraph({
  label: "Implementation & Onboarding",
  lineKey: "impl_rev",
  variance: -40000,
  comparison_amount: 90000,
  drivers: [],
}, "May 2026");
assert(asked.includes("fell 40,000"), asked);
assert(asked.includes("do not say whether that was fewer implementations or smaller ones"), asked);
assert(!asked.includes("because"), asked);

const counted = api.reportParagraph({
  label: "Implementation & Onboarding",
  lineKey: "impl_rev",
  variance: -40000,
  comparison_amount: 90000,
  implementationCount: { current: 4, base: 8 },
  implementationSize: { current: 5000, base: 7000 },
}, "May 2026");
assert(counted.includes("4 fewer implementations"), counted);
assert(counted.includes("each was 2,000 smaller"), counted);
assert(!counted.includes("do not say"), counted);

const deals = api.reportParagraph({
  label: "Subscription Revenue",
  lineKey: "sub_rev",
  variance: 10000,
  comparison_amount: 50000,
  drivers: [{ label: "Closed deal", variance: 10000, role: "opportunity", linked: false }],
}, "May 2026");
assert(!deals.includes("Closed deal"), deals);

const start = code.indexOf("function renderReport");
const end = code.indexOf("function saveReportEdit");
const grid = code.slice(start, end);
assert(!/label\s*===|label\s*==(?!=)/.test(grid), "grid compares a label to a string");

console.log("ok");
