import fs from "node:fs";
import vm from "node:vm";

const code = fs.readFileSync(new URL("../public/shared/board-continuity.js", import.meta.url), "utf8");
const context = { console };
context.window = context;
context.globalThis = context;
vm.createContext(context);
vm.runInContext(code, context);
const built = context.SMPLContinuity.datasetBuilt;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(built("2026-11-08T00:38:48.396852+00:00") === "Nov 7, 2026, 4:38 PM", built("2026-11-08T00:38:48.396852+00:00"));
assert(built("2026-09-07T19:36:31.428955+00:00") === "Sep 7, 2026, 11:36 AM", built("2026-09-07T19:36:31.428955+00:00"));
assert(built("") === "—", built(""));
assert(code.indexOf('id="veRefreezeBtn"') > code.indexOf("<strong>Freeze</strong>"), "the dataset button sits with Freeze");
assert(code.split('id="veRefreezeBtn"').length === 2, "the dataset button is only on the Freeze row");

console.log("ok");
